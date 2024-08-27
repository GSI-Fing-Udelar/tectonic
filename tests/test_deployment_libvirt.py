
# Tectonic - An academic Cyber Range
# Copyright (C) 2024 Grupo de Seguridad Informática, Universidad de la República,
# Uruguay
#
# This file is part of Tectonic.
#
# Tectonic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tectonic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tectonic.  If not, see <http://www.gnu.org/licenses/>.

import pytest
import json
import os
import python_terraform
import libvirt_qemu
import tectonic.ssh
import libvirt
import ansible_runner
import packerpy
import fabric
import invoke
from freezegun import freeze_time

from tectonic.libvirt_client import LibvirtClientException
from tectonic.libvirt_client import Client as LibvirtClient
from tectonic.deployment_libvirt import LibvirtDeployment, DeploymentLibvirtException
from tectonic.deployment import *
import tectonic.constants

def test_constructor(description):
    description.deploy_elastic = False
    libvirt_deployment = LibvirtDeployment(
        description=description,
        gitlab_backend_url="https://gitlab.com",
        gitlab_backend_username="testuser",
        gitlab_backend_access_token="testtoken",
    )

def test_generate_backend_config(libvirt_deployment):
    answer = libvirt_deployment.generate_backend_config(libvirt_deployment.terraform_module_path)
    assert len(answer) == 8
    assert 'address=https://gitlab.com/udelar-lab01-gsi-lab-libvirt' in answer
    assert 'lock_address=https://gitlab.com/udelar-lab01-gsi-lab-libvirt/lock' in answer
    assert 'unlock_address=https://gitlab.com/udelar-lab01-gsi-lab-libvirt/lock' in answer
    assert 'username=testuser' in answer
    assert 'password=testtoken' in answer
    assert 'lock_method=POST' in answer
    assert 'unlock_method=DELETE' in answer


def test_terraform_apply(mocker, libvirt_deployment):
    variables = {"var1": "value1", "var2": "value2"}
    resources = {'libvirt_domain.machines["udelar-lab01-1-attacker"]'}

    terraform_dir = libvirt_deployment.terraform_module_path

    mock = mocker.patch("tectonic.deployment.run_terraform_cmd")
    libvirt_deployment.terraform_apply(terraform_dir, variables, resources)
    mock.assert_has_calls([mocker.call(mocker.ANY, "init", [],
                                       reconfigure=python_terraform.IsFlagged,
                                       backend_config=libvirt_deployment.generate_backend_config(terraform_dir)
                                       ),
                           mocker.call(mocker.ANY, "plan",
                                       variables,
                                       input=False,
                                       target=resources,
                                       ),
                           mocker.call(mocker.ANY, "apply",
                                       variables,
                                       auto_approve=True,
                                       input=False,
                                       target=resources,
                                       ),
                           ])

def test_get_deploy_cr_vars(libvirt_deployment, terraform_dir, test_data_path):
    variables = libvirt_deployment.get_deploy_cr_vars()
    # do not compare authorized_keys as its order is not guaranteed
    variables.pop('authorized_keys', None)
    assert variables == {
        "institution": "udelar",
        "lab_name": "lab01",
        "instance_number": 2,
        "ssh_public_key_file": libvirt_deployment.description.ssh_public_key_file,
        "subnets_json": json.dumps(libvirt_deployment.description.subnets),
        "guest_data_json": json.dumps(libvirt_deployment.description.get_guest_data()),
        "default_os": "ubuntu22",
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "configure_dns": False,
        "libvirt_uri": f"test:///{test_data_path}/libvirt_config.xml",
        "libvirt_storage_pool": "pool-dir",
        "libvirt_student_access": "bridge",
        "libvirt_bridge": "lab_ens",
        "libvirt_external_network": "192.168.44.10/25",
        "libvirt_bridge_base_ip": 10,
        "services_network": "10.0.0.128/25",
        "services_network_base_ip": 9,
    }

def test_get_deploy_services_vars(libvirt_deployment, terraform_dir, test_data_path):
    variables = libvirt_deployment.get_deploy_services_vars()
    # do not compare authorized_keys as its order is not guaranteed
    variables.pop('authorized_keys', None)
    assert variables == {
        "institution": "udelar",
        "lab_name": "lab01",
        "ssh_public_key_file": libvirt_deployment.description.ssh_public_key_file,
        "subnets_json": json.dumps(libvirt_deployment._get_services_network_data()),
        "guest_data_json": json.dumps(libvirt_deployment._get_services_guest_data()),
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "configure_dns": False,
        "libvirt_uri": f"test:///{test_data_path}/libvirt_config.xml",
        "libvirt_storage_pool": "pool-dir",
    }


def test_deploy_cr_all_instances(mocker, libvirt_deployment):
    mock = mocker.patch.object(libvirt_deployment, "terraform_apply")
    libvirt_deployment._deploy_cr(libvirt_deployment.terraform_module_path, libvirt_deployment.get_deploy_cr_vars(), None)
    mock.assert_called_once_with(libvirt_deployment.terraform_module_path,
        variables=libvirt_deployment.get_deploy_cr_vars(),
        resources=None,
    )


def test_deploy_cr_instance_two(mocker, libvirt_deployment):
    mock = mocker.patch.object(libvirt_deployment, "terraform_apply")

    libvirt_deployment._deploy_cr(libvirt_deployment.terraform_module_path, libvirt_deployment.get_deploy_cr_vars(), [2])

    mock.assert_called_once_with(libvirt_deployment.terraform_module_path,
                                 variables=libvirt_deployment.get_deploy_cr_vars(),
                                 resources=libvirt_deployment.get_cr_resources_to_target_apply([2]),
                                 )

def test_deploy_packetbeat(mocker, libvirt_deployment, ansible_path):
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(LibvirtDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    inventory = {
        "localhost": {
            "hosts": {
                "localhost": {
                    "ansible_host": "localhost",
                    "ansible_user": "gsi",
                    "ansible_ssh_common_args": libvirt_deployment.description.ansible_ssh_common_args,
                    "become_flags":"-i",
                    "copy":1,
                    "instance":None,
                    "parameter":{},
                }
            },
            "vars": {
                "ansible_become":True,
                "basename":"localhost",
                "action": "install",
                "elastic_url": "https://10.0.0.129:8220",
                "token": "1234567890abcdef",
                "elastic_agent_version": "7.10.2",
                "institution": "udelar",
                "lab_name": "lab01",
                "instances": 2,
                'platform': 'libvirt',
            },
        }
    }
    libvirt_deployment._deploy_packetbeat()
    assert len(mock.mock_calls) == 2
    mock.assert_has_calls([
        mocker.call(inventory=inventory,
            playbook=os.path.join(ansible_path, "wait_for_connection.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=inventory,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "agent_manage.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        )
    ])


def test_terraform_destroy(mocker, libvirt_deployment):
    variables = {"var1": "value1", "var2": "value2"}
    resources = {'libvirt_domain.machines["udelar-lab01-1-attacker"]'}

    terraform_dir = libvirt_deployment.terraform_module_path

    mock = mocker.patch("tectonic.deployment.run_terraform_cmd")
    libvirt_deployment.terraform_destroy(terraform_dir, variables, resources)

    mock.assert_has_calls([mocker.call(mocker.ANY, "init", [],
                                       reconfigure=python_terraform.IsFlagged,
                                       backend_config=libvirt_deployment.generate_backend_config(terraform_dir)
                                       ),
                           mocker.call(mocker.ANY, "destroy",
                                       variables,
                                       auto_approve=True,
                                       input=False,
                                       target=resources,
                                       ),
                           ])



def test_destroy_packetbeat(mocker, libvirt_deployment):
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"elastic":"password"})
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)
    inventory = {
        "localhost": {
            "hosts": {
                "localhost": {
                    "ansible_host": "localhost",
                    "ansible_user": "gsi",
                    "ansible_ssh_common_args": libvirt_deployment.description.ansible_ssh_common_args,
                    "become_flags":"-i",
                    "copy":1,
                    "instance":None,
                    "parameter":{},
                }
            },
            "vars": {
                "ansible_become":True,
                "basename":"localhost",
                "action": "delete",
                "institution": "udelar",
                "lab_name": "lab01",
                "instances": 2,
                'platform': 'libvirt',
            },
        }
    }

    libvirt_deployment._destroy_packetbeat()

    mock.assert_called_once_with(inventory=inventory,
        playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "agent_manage.yml"),
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
    )


def test_destroy_cr_all_instances(mocker, libvirt_deployment):
    mock = mocker.patch.object(libvirt_deployment, "terraform_destroy")

    libvirt_deployment._destroy_cr(libvirt_deployment.terraform_module_path, libvirt_deployment.get_deploy_cr_vars(), None)
    mock.assert_called_once_with(libvirt_deployment.terraform_module_path,
                                 variables=libvirt_deployment.get_deploy_cr_vars(),
                                 resources=None,
                                 )


def test_destroy_cr_instance_two(mocker, libvirt_deployment):
    mock = mocker.patch.object(libvirt_deployment, "terraform_destroy")

    libvirt_deployment._destroy_cr(libvirt_deployment.terraform_module_path, libvirt_deployment.get_deploy_cr_vars(), [2])
    mock.assert_called_once_with(libvirt_deployment.terraform_module_path,
                                 variables=libvirt_deployment.get_deploy_cr_vars(),
                                 resources=libvirt_deployment.get_cr_resources_to_target_destroy([2]),
                                 )

def test_terraform_recreate(mocker, libvirt_deployment):
    machines = {'libvirt_domain.machines["udelar-lab01-1-attacker"]'}

    terraform_dir = libvirt_deployment.terraform_module_path

    mock = mocker.patch("tectonic.deployment.run_terraform_cmd")
    libvirt_deployment.terraform_recreate(machines)
    mock.assert_has_calls([mocker.call(mocker.ANY, "init", [],
                                       reconfigure=python_terraform.IsFlagged,
                                       backend_config=libvirt_deployment.generate_backend_config(terraform_dir)
                                       ),
                           mocker.call(mocker.ANY, "plan",
                                       variables=libvirt_deployment.get_deploy_cr_vars(),
                                       input=False,
                                       replace=machines,
                                       ),
                           mocker.call(mocker.ANY, "apply",
                                       variables=libvirt_deployment.get_deploy_cr_vars(),
                                       auto_approve=True,
                                       input=False,
                                       replace=machines,
                                       ),
                           ])


def test_create_cr_images_ok(mocker, libvirt_deployment, test_data_path):
    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.monitor_type = "traffic"
    machines = {
        "attacker": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
            "vcpu": 2,
            "memory": 1024,
            "disk": 10,
        },
        "victim": {
            "base_os": "windows_srv_2022",
            "endpoint_monitoring": False,
            "vcpu": 1,
            "memory": 1024,
            "disk": 10,
        },
        "server": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
            "vcpu": 1,
            "memory": 1024,
            "disk": 10,
        },
    }
    variables = {
        "ansible_playbooks_path": libvirt_deployment.description.ansible_playbooks_path,
        "ansible_scp_extra_args": "'-O'" if tectonic.ssh.ssh_version() >= 9 else "",
        "ansible_ssh_common_args": "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no",
        "aws_region": "us-east-1",
        "instance_number": 2,
        "institution": "udelar",
        "lab_name": "lab01",
        "libvirt_proxy": "http://proxy.fing.edu.uy:3128",
        "libvirt_storage_pool": "pool-dir",
        "libvirt_uri": f"test:///{test_data_path}/libvirt_config.xml",
        "machines_json": json.dumps(machines),
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "platform": "libvirt",
        "remove_ansible_logs": str(not libvirt_deployment.description.keep_ansible_logs),
        "elastic_version": libvirt_deployment.description.elastic_stack_version,
    }

    mock_cmd = mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", ""))
    mock_build = mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(0, "success", ""))
    libvirt_deployment.create_cr_images()
    mock_cmd.assert_called_once_with("init", libvirt_deployment.cr_packer_path)
    mock_build.assert_called_once_with(libvirt_deployment.cr_packer_path, var=variables)

    #Test monitor_type == endpoint
    libvirt_deployment.description.monitor_type = "endpoint"
    libvirt_deployment.description.deploy_elastic = True
    machines = {
        "attacker": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
            "vcpu": 2,
            "memory": 1024,
            "disk": 10,
        },
        "victim": {
            "base_os": "windows_srv_2022",
            "endpoint_monitoring": True,
            "vcpu": 1,
            "memory": 1024,
            "disk": 10,
        },
        "server": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": True,
            "vcpu": 1,
            "memory": 1024,
            "disk": 10,
        },
    }
    variables = {
        "ansible_playbooks_path": libvirt_deployment.description.ansible_playbooks_path,
        "ansible_scp_extra_args": "'-O'" if tectonic.ssh.ssh_version() >= 9 else "",
        "ansible_ssh_common_args": "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no",
        "aws_region": "us-east-1",
        "instance_number": 2,
        "institution": "udelar",
        "lab_name": "lab01",
        "libvirt_proxy": "http://proxy.fing.edu.uy:3128",
        "libvirt_storage_pool": "pool-dir",
        "libvirt_uri": f"test:///{test_data_path}/libvirt_config.xml",
        "machines_json": json.dumps(machines),
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "platform": "libvirt",
        "remove_ansible_logs": str(not libvirt_deployment.description.keep_ansible_logs),
        "elastic_version": libvirt_deployment.description.elastic_stack_version,
    }
    mock_cmd = mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", ""))
    mock_build = mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(0, "success", ""))
    libvirt_deployment.create_cr_images()
    mock_cmd.assert_called_once_with("init", libvirt_deployment.cr_packer_path)
    mock_build.assert_called_once_with(libvirt_deployment.cr_packer_path, var=variables),
    libvirt_deployment.description.monitor_type = "traffic"
    libvirt_deployment.description.deploy_elastic = False


def test_create_cr_images_error(mocker, libvirt_deployment):
    mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(1, b"error", b"error"))
    with pytest.raises(TerraformRunException):
        libvirt_deployment.create_cr_images()

    mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, b"success", b""))
    mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(1, b"error", b"error"))
    with pytest.raises(TerraformRunException):
        libvirt_deployment.create_cr_images()


def test_get_teacher_access_username(libvirt_deployment):
    username = libvirt_deployment.get_teacher_access_username()
    assert username == "ubuntu"


def test_get_teacher_access_ip(libvirt_deployment):
    ipaddr = libvirt_deployment.get_teacher_access_ip()
    assert ipaddr is None

    libvirt_deployment.description.teacher_access = "endpoint"
    ipaddr = libvirt_deployment.get_teacher_access_ip()
    assert ipaddr is None
    libvirt_deployment.description.teacher_access = "host"


def test_student_access(mocker, libvirt_deployment, ansible_path):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    ansible_libvirt = tectonic.ansible.Ansible(libvirt_deployment)
    entry_points = [ base_name for base_name, guest in libvirt_deployment.description.guest_settings.items()
                     if guest.get("entry_point") ]
    machine_list = libvirt_deployment.description.parse_machines(guests=entry_points)

    authorized_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsKA/F4zXu/rspUu1KNV+8foIgmj4+LP8Cf9BK5+NSkQvUCfTKnoObJdLKaIV2crzYYIowASSu1i9GCxCYnnZP9U75dV+c6iyh3l5aYbrKfIfgCVtuBjKNz1uRuZNEdZ7nADV/lTc5BI5jnhzTPzNW++jslaTu/xS4gZ7KWgE7NA7hOMjMfY/rxvCPQm7w919NpuZmzn0V7ubf6kONh+wQoubKCm8Gb2viX/GlYsSBP6xhP/YKkkLpaGDDTZ6e/OEU8X/OdqEJSgy5eJUhEjkCc1Dei32YRV6ldbiF8vQSs3Izcq7UkOkciEDbY0vZkoeggB9+UnAcrOJu1bt5A+LT jdcampo@japeto\n"
    users = {
        "student01": {
            "password": "p5bABWxM6xMm",
            "password_hash": "$6$rounds=656000$krxDZtQpILLXJNOD$OvK02knb5z8GTRM9941I4CpQaxVTx9/3ddykJaorvxnj/FsanrU41q95udci2risbzCMIFAPnzy6/JVWQDaG60",
            "authorized_keys": authorized_key,
        },
        "student02": {
            "password": "CxHYusI7nRoe",
            "password_hash": "$6$rounds=656000$n7L4DJ4ozaEY0qU6$6N3OFgFzkE0qvmfd51ZrdTaiHvkFJGWCzCpMX5isl0y89QksSjyMVI/hA109oXc7Jy1vioYevvajc9I6kav5c1",
            "authorized_keys": authorized_key,
        }
    }
    inventory = ansible_libvirt.build_inventory(machine_list,
                                                extra_vars={"users": users,
                                                            "prefix": "student",
                                                            "ssh_password_login":True}
                                                )

    libvirt_deployment.student_access(None)
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=f"{ansible_path}/trainees.yml",
                                 quiet=True,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
                                 )


def test_student_access_no_passwords(mocker, libvirt_deployment, ansible_path):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    ansible_libvirt = tectonic.ansible.Ansible(libvirt_deployment)
    entry_points = [ base_name for base_name, guest in libvirt_deployment.description.guest_settings.items()
                     if guest.get("entry_point") ]
    machine_list = libvirt_deployment.description.parse_machines(guests=entry_points)
    authorized_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsKA/F4zXu/rspUu1KNV+8foIgmj4+LP8Cf9BK5+NSkQvUCfTKnoObJdLKaIV2crzYYIowASSu1i9GCxCYnnZP9U75dV+c6iyh3l5aYbrKfIfgCVtuBjKNz1uRuZNEdZ7nADV/lTc5BI5jnhzTPzNW++jslaTu/xS4gZ7KWgE7NA7hOMjMfY/rxvCPQm7w919NpuZmzn0V7ubf6kONh+wQoubKCm8Gb2viX/GlYsSBP6xhP/YKkkLpaGDDTZ6e/OEU8X/OdqEJSgy5eJUhEjkCc1Dei32YRV6ldbiF8vQSs3Izcq7UkOkciEDbY0vZkoeggB9+UnAcrOJu1bt5A+LT jdcampo@japeto\n"
    users = {
        "student01": {
            "authorized_keys": authorized_key,
        },
        "student02": {
            "authorized_keys": authorized_key,
        }
    }
    inventory = ansible_libvirt.build_inventory(machine_list,
                                                extra_vars={"users": users,
                                                            "prefix": "student",
                                                            "ssh_password_login":False}
                                                )

    libvirt_deployment.description.create_student_passwords = False
    libvirt_deployment.student_access(None)
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=f"{ansible_path}/trainees.yml",
                                 quiet=True,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
                                 )
    libvirt_deployment.description.create_student_passwords = True


def test_student_access_no_pubkeys(mocker, libvirt_deployment, ansible_path):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    ansible_libvirt = tectonic.ansible.Ansible(libvirt_deployment)
    entry_points = [ base_name for base_name, guest in libvirt_deployment.description.guest_settings.items()
                     if guest.get("entry_point") ]
    machine_list = libvirt_deployment.description.parse_machines(guests=entry_points)
    users = {
        "student01": {
            "password": "p5bABWxM6xMm",
            "password_hash": "$6$rounds=656000$krxDZtQpILLXJNOD$OvK02knb5z8GTRM9941I4CpQaxVTx9/3ddykJaorvxnj/FsanrU41q95udci2risbzCMIFAPnzy6/JVWQDaG60",
        },
        "student02": {
            "password": "CxHYusI7nRoe",
            "password_hash": "$6$rounds=656000$n7L4DJ4ozaEY0qU6$6N3OFgFzkE0qvmfd51ZrdTaiHvkFJGWCzCpMX5isl0y89QksSjyMVI/hA109oXc7Jy1vioYevvajc9I6kav5c1",
        }
    }
    inventory = ansible_libvirt.build_inventory(machine_list,
                                                extra_vars={"users": users,
                                                            "prefix": "student",
                                                            "ssh_password_login":True}
                                                )

    pubkey_dir = libvirt_deployment.description.student_pubkey_dir
    libvirt_deployment.description.student_pubkey_dir = None
    libvirt_deployment.student_access(None)
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=f"{ansible_path}/trainees.yml",
                                 quiet=True,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
                                 )

    libvirt_deployment.description.student_pubkey_dir = pubkey_dir


def test_get_instance_status(libvirt_deployment):
    state = libvirt_deployment.get_instance_status("test")
    assert state == "RUNNING"
    state = libvirt_deployment.get_instance_status("notfound")
    assert state == "NOT FOUND"

def test_get_cyberrange_data_elasticup(mocker, libvirt_deployment):
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = False
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    table = libvirt_deployment.get_cyberrange_data()
    expected = """┌──────────────────────────────────┬─────────────────────────┐
│               Name               │          Value          │
├──────────────────────────────────┼─────────────────────────┤
│            Kibana URL            │ https://10.0.0.129:5601 │
│ Kibana user (username: password) │    elastic: password    │
└──────────────────────────────────┴─────────────────────────┘"""
    assert expected == table.get_string()

def test_get_cyberrange_data_elasticdown(mocker, capsys, libvirt_deployment):
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = False
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value={"udelar-lab01-elastic": {"Status": "NOT RUNNING"}})
    result = libvirt_deployment.get_cyberrange_data()
    expected = """Unable to get Elastic info right now. Please make sure de Elastic machine is running."""
    assert expected == result

def test_get_cyberrange_data_calderaup(mocker, capsys, libvirt_deployment):
    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.deploy_caldera = True
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"red":"passwordred","blue":"passwordblue"})
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    table = libvirt_deployment.get_cyberrange_data()
    expected = """┌───────────────────────────────────┬─────────────────────────┐
│                Name               │          Value          │
├───────────────────────────────────┼─────────────────────────┤
│            Caldera URL            │ https://10.0.0.130:8443 │
│ Caldera user (username: password) │     red: passwordred    │
│ Caldera user (username: password) │    blue: passwordblue   │
└───────────────────────────────────┴─────────────────────────┘"""
    assert expected == table.get_string()

def test_get_cyberrange_data_calderadown(mocker, libvirt_deployment):
    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.deploy_caldera = True
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value={"udelar-lab01-caldera": {"Status": "NOT RUNNING"}})
    result = libvirt_deployment.get_cyberrange_data()
    expected = """Unable to get Caldera info right now. Please make sure de Caldera machine is running."""
    assert expected == result

def test_get_cyberrange_data_noservices(capsys, libvirt_deployment):
    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.deploy_caldera = False
    libvirt_deployment.get_cyberrange_data()
    result = capsys.readouterr()
    assert "" == result.out

def test_get_cyberrange_data_error(mocker, libvirt_deployment):
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    with pytest.raises(DeploymentLibvirtException):
        libvirt_deployment.get_cyberrange_data()

def test_connect_to_instance(monkeypatch, mocker, libvirt_deployment):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    def fabric_shell(connection, **kwargs):
        """ Mocks fabric.Connection.shell()."""
        assert connection.original_host == "10.0.1.25"
        assert connection.user == "root"
        assert connection.gateway is None
        return invoke.runners.Result()
    monkeypatch.setattr(fabric.Connection, "shell", fabric_shell)

    libvirt_deployment.connect_to_instance("udelar-lab01-1-attacker", "root")

def test_connect_to_instance_error(libvirt_deployment):
    with pytest.raises(DeploymentLibvirtException):
        libvirt_deployment.connect_to_instance("notfound", None)


def test_get_ssh_proxy_command(libvirt_deployment):
    proxy = libvirt_deployment.get_ssh_proxy_command()
    assert proxy is None

def test_get_ssh_hostname(mocker, libvirt_deployment):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    hostname = libvirt_deployment.get_ssh_hostname("udelar-lab01-1-attacker")
    assert hostname == "10.0.1.25"

def test_start_instance(libvirt_deployment):
    libvirt_client = libvirt_deployment.client

    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    # Test starting a RUNNING instance
    libvirt_deployment.start_instance("test")
    state = libvirt_deployment.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Stop the domain
    libvirt_deployment.stop_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]

    # Test starting a SHUTOFF instance
    libvirt_deployment.start_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Test a non-existent domain
    with pytest.raises(LibvirtClientException) as exception:
        libvirt_deployment.start_instance("notfound")
    assert "Domain notfound not found." in str(exception.value)

def test_stop_instance(libvirt_deployment):
    libvirt_client = libvirt_deployment.client

    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    libvirt_deployment.stop_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    libvirt_deployment.stop_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]

    # Test a non-existent domain
    with pytest.raises(LibvirtClientException) as exception:
        libvirt_deployment.stop_instance("notfound")
    assert "Domain notfound not found." in str(exception.value)

def test_reboot_instance(libvirt_deployment):
    libvirt_client = libvirt_deployment.client

    # Restart a RUNNING domain
    libvirt_deployment.start_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    libvirt_deployment.reboot_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Restart a SHUTOFF domain
    libvirt_deployment.stop_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    libvirt_deployment.reboot_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Restart a PAUSED domain
    dom = libvirt_client.conn.lookupByName('test')
    dom.suspend()
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_PAUSED]
    libvirt_deployment.reboot_instance("test")
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_PAUSED]
    dom.resume()
    state = libvirt_client.get_instance_status("test")
    assert state == libvirt_client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    # Test a non-existent domain
    with pytest.raises(LibvirtClientException) as exception:
        libvirt_deployment.reboot_instance("notfound")
    assert "Domain notfound not found." in str(exception.value)


def test_can_delete_image(libvirt_deployment):
    can_delete = libvirt_deployment.can_delete_image("udelar-lab01-1-attacker")
    assert can_delete

def test_delete_cr_images(mocker, libvirt_deployment):
    mock = mocker.patch.object(libvirt_deployment.client, "delete_image")
    libvirt_deployment.delete_cr_images()
    assert mock.call_count == 3
    mock.assert_has_calls([mocker.call("pool-dir", "udelar-lab01-attacker"),
                           mocker.call("pool-dir", "udelar-lab01-victim"),
                           mocker.call("pool-dir", "udelar-lab01-server"),
                           ])

    mocker.patch.object(libvirt_deployment, "can_delete_image", return_value=False)
    mock.reset_mock()
    with pytest.raises(DeploymentLibvirtException):
        libvirt_deployment.delete_cr_images()
    mock.assert_not_called()


def test_get_cr_resources_to_target_apply(libvirt_deployment):
    expected_resources = ['libvirt_domain.machines["udelar-lab01-1-attacker"]',
                          'libvirt_volume.cloned_image["udelar-lab01-1-attacker"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-1-attacker"]',
                          'libvirt_domain.machines["udelar-lab01-1-victim-1"]',
                          'libvirt_volume.cloned_image["udelar-lab01-1-victim-1"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-1-victim-1"]',
                          'libvirt_domain.machines["udelar-lab01-1-victim-2"]',
                          'libvirt_volume.cloned_image["udelar-lab01-1-victim-2"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-1-victim-2"]',
                          'libvirt_domain.machines["udelar-lab01-1-server"]',
                          'libvirt_volume.cloned_image["udelar-lab01-1-server"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-1-server"]',
                          'libvirt_domain.machines["udelar-lab01-1-server"]',
                          'libvirt_volume.cloned_image["udelar-lab01-1-server"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-1-server"]',
                          'libvirt_domain.machines["udelar-lab01-2-attacker"]',
                          'libvirt_volume.cloned_image["udelar-lab01-2-attacker"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-2-attacker"]',
                          'libvirt_domain.machines["udelar-lab01-2-victim-1"]',
                          'libvirt_volume.cloned_image["udelar-lab01-2-victim-1"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-2-victim-1"]',
                          'libvirt_domain.machines["udelar-lab01-2-victim-2"]',
                          'libvirt_volume.cloned_image["udelar-lab01-2-victim-2"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-2-victim-2"]',
                          'libvirt_domain.machines["udelar-lab01-2-server"]',
                          'libvirt_volume.cloned_image["udelar-lab01-2-server"]',
                          'libvirt_cloudinit_disk.commoninit["udelar-lab01-2-server"]',
                          'libvirt_network.subnets["udelar-lab01-1-dmz"]',
                          'libvirt_network.subnets["udelar-lab01-2-internal"]',
                          'libvirt_network.subnets["udelar-lab01-1-internal"]',
                          'libvirt_network.subnets["udelar-lab01-2-dmz"]',
                          ]
    resources = libvirt_deployment.get_cr_resources_to_target_apply(None)
    assert set(resources) == set(expected_resources)

    libvirt_deployment.description.configure_dns = True
    resources = libvirt_deployment.get_cr_resources_to_target_apply(None)
    assert set(resources) == set(expected_resources)
    libvirt_deployment.description.configure_dns = False


def test_get_cr_resources_to_target_destroy(libvirt_deployment):
    expected_resources = ['libvirt_domain.machines["udelar-lab01-1-attacker"]',
                          'libvirt_domain.machines["udelar-lab01-1-victim-1"]',
                          'libvirt_domain.machines["udelar-lab01-1-victim-2"]',
                          'libvirt_domain.machines["udelar-lab01-1-server"]',
                          'libvirt_domain.machines["udelar-lab01-1-server"]',
                          ]
    resources = libvirt_deployment.get_cr_resources_to_target_destroy([1])
    assert set(resources) == set(expected_resources)

    libvirt_deployment.description.configure_dns = True
    resources = libvirt_deployment.get_cr_resources_to_target_destroy([1])
    assert set(resources) == set(expected_resources)
    libvirt_deployment.description.configure_dns = False


def test_get_resources_to_recreate(libvirt_deployment):
    expected_resources = ['libvirt_domain.machines["udelar-lab01-1-victim-2"]',
                          'libvirt_volume.cloned_image["udelar-lab01-1-victim-2"]']
    resources = libvirt_deployment.get_resources_to_recreate([1], ("victim", ), [2])
    assert set(resources) == set(expected_resources)

def test_get_guest_instance_type(libvirt_deployment):
    instance_type = libvirt_deployment.get_guest_instance_type("attacker")
    assert instance_type is None

@freeze_time("2022-01-01")
def test_get_services_status(mocker, libvirt_deployment):
    #Only ELastic with monitor_type traffic
    libvirt_deployment.description.deploy_caldera = False
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.monitor_type = "traffic"
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"_manage_packetbeat",return_value="RUNNING")

    table = libvirt_deployment.get_services_status()
    expected = """┌─────────────────────────┬─────────┐
│           Name          │  Status │
├─────────────────────────┼─────────┤
│   udelar-lab01-elastic  │ RUNNING │
│ udelar-lab01-packetbeat │ RUNNING │
└─────────────────────────┴─────────┘"""
    assert expected == table.get_string()

    #Only Elastic with monitor_type endpoint
    libvirt_deployment.description.deploy_caldera = False
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.monitor_type = "endpoint"
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(LibvirtDeployment,"_get_service_info",return_value=[{"agents_status": {"online": 2,"error": 0,"inactive": 0,"offline": 0,"updating": 0,"unenrolled": 0,"degraded": 0,"enrolling": 0,"unenrolling": 0 }}])

    table = libvirt_deployment.get_services_status()
    expected = """┌────────────────────────────┬─────────┐
│            Name            │  Status │
├────────────────────────────┼─────────┤
│    udelar-lab01-elastic    │ RUNNING │
│   elastic-agents-online    │    2    │
│    elastic-agents-error    │    0    │
│  elastic-agents-inactive   │    0    │
│   elastic-agents-offline   │    0    │
│  elastic-agents-updating   │    0    │
│ elastic-agents-unenrolled  │    0    │
│  elastic-agents-degraded   │    0    │
│  elastic-agents-enrolling  │    0    │
│ elastic-agents-unenrolling │    0    │
└────────────────────────────┴─────────┘"""
    assert expected == table.get_string()
    #Only caldera
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.deploy_elastic = False
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"red":"passwordred","blue":"passwordblue"})
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(LibvirtDeployment,"_get_service_info",return_value=[{"agents_status":[{"sleep_min":3,"sleep_max":3,"watchdog":1,"last_seen":"2024-05-05T14:43:17Z"},{"sleep_min":3,"sleep_max":3,"watchdog":1,"last_seen":"2024-05-04T14:43:17Z"}]}])
    table = libvirt_deployment.get_services_status()
    expected = """┌─────────────────────────────┬─────────┐
│             Name            │  Status │
├─────────────────────────────┼─────────┤
│     udelar-lab01-caldera    │ RUNNING │
│     caldera-agents-alive    │    0    │
│     caldera-agents-dead     │    0    │
│ caldera-agents-pending_kill │    2    │
└─────────────────────────────┴─────────┘"""
    assert expected == table.get_string()

def test_list_instances(mocker, libvirt_deployment):
    mocker.patch.object(LibvirtClient, "get_instance_status", return_value="RUNNING")
    result = libvirt_deployment.list_instances(None, None, None)
    expected = """┌─────────────────────────┬─────────┐
│           Name          │  Status │
├─────────────────────────┼─────────┤
│ udelar-lab01-1-attacker │ RUNNING │
│ udelar-lab01-1-victim-1 │ RUNNING │
│ udelar-lab01-1-victim-2 │ RUNNING │
│  udelar-lab01-1-server  │ RUNNING │
│ udelar-lab01-2-attacker │ RUNNING │
│ udelar-lab01-2-victim-1 │ RUNNING │
│ udelar-lab01-2-victim-2 │ RUNNING │
│  udelar-lab01-2-server  │ RUNNING │
└─────────────────────────┴─────────┘"""
    assert result.get_string() == expected

def test_start(mocker, libvirt_deployment):
    #No services
    libvirt_deployment.start([1], ["attacker"], None, False)
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    #Start services with monitor type traffic
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.monitor_type = "traffic"
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    libvirt_deployment.start([1], ["attacker"], None, True)

    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-elastic")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-caldera")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    mock.call(inventory=mocker.ANY,
        playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "agent_manage.yml"),
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
    )

    #Start services with monitor type endpoint
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.monitor_type = "endpoint"

    libvirt_deployment.start([1], ["attacker"], None, True)

    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-elastic")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-caldera")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

def test_shutdown(mocker, libvirt_deployment):
    #No services
    libvirt_deployment.shutdown([1], ["attacker"], None, False)
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]

    #Shutdown services with monitor type traffic
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.monitor_type = "traffic"
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    libvirt_deployment.shutdown([1], ["attacker"], None, True)

    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-elastic")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-caldera")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    mock.call(inventory=mocker.ANY,
        playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "agent_manage.yml"),
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
    )

    #Shutdown services with monitor type endpoint
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.monitor_type = "endpoint"

    libvirt_deployment.shutdown([1], ["attacker"], None, True)

    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-elastic")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-caldera")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_SHUTOFF]

def test_reboot(mocker, libvirt_deployment):
    #No services
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.reboot([1], ["attacker"], None, False)
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]

    #Reboot services with monitor type traffic
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.monitor_type = "traffic"
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    libvirt_deployment.reboot([1], ["attacker"], None, True)

    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-elastic")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-caldera")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    mock.call(inventory=mocker.ANY,
        playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "agent_manage.yml"),
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
    )

    #Reboot services with monitor type endpoint
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.monitor_type = "endpoint"
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    libvirt_deployment.reboot([1], ["attacker"], None, True)

    state = libvirt_deployment.client.get_instance_status("udelar-lab01-1-attacker")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-elastic")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]
    state = libvirt_deployment.client.get_instance_status("udelar-lab01-caldera")
    assert state == libvirt_deployment.client.STATES_MSG[libvirt.VIR_DOMAIN_RUNNING]


def test_recreate(mocker, capsys, libvirt_deployment, ansible_path, labs_path):
    libvirt_deployment.description.monitor_type = "endpoint"
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(LibvirtDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mock_terraform = mocker.patch.object(tectonic.deployment.Deployment, "terraform_recreate")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    libvirt_deployment.recreate([1],["attacker"], None, False)

    mock_terraform.assert_called_once_with(mocker.ANY)

    # Test ansible got run with correct playbooks
    assert len(mock_ansible.mock_calls) == 9
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/trainees.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{labs_path}/test-endpoint/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "endpoint_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "caldera", "agent_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "caldera", "agent_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
    ])

    assert (capsys.readouterr().out == (
        "Recreating machines...\n"
        "Waiting for machines to boot up...\n"
        "Configuring student access...\n"
        "Running after-clone configuration...\n"
        "Configuring elastic agents...\n"
        "Configuring caldera agents...\n"
    ))

def test_manage_packetbeat(mocker,libvirt_deployment):
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)
    inventory = {
        "localhost": {
            "hosts": {
                "localhost" : {
                    "ansible_host": "localhost",
                    "ansible_user": "gsi",
                    "ansible_ssh_common_args": libvirt_deployment.description.ansible_ssh_common_args,
                    "instance": None,
                    "copy": 1,
                    "parameter": {},
                    "become_flags": "-i",
                }
            },
            "vars": {
                "ansible_become": True,
                "basename": "localhost",
                "instances": 2,
                "action": "restarted",
                "institution": libvirt_deployment.description.institution,
                "lab_name": libvirt_deployment.description.lab_name,
                "platform": "libvirt",
            },
        }
    }
    playbook = os.path.join(libvirt_deployment.base_dir, "services", "elastic", "agent_manage.yml")
    libvirt_deployment._manage_packetbeat("restarted")
    mock_ansible.assert_called_once_with(
        inventory=inventory,
        playbook=playbook,
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
    )

    mock_ansible.reset_mock()
    inventory["localhost"]["vars"]["action"] = "started"
    libvirt_deployment._manage_packetbeat("started")
    mock_ansible.assert_called_once_with(
        inventory=inventory,
        playbook=playbook,
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
    )

    mock_ansible.reset_mock()
    inventory["localhost"]["vars"]["action"] = "stopped"
    libvirt_deployment._manage_packetbeat("stopped")
    mock_ansible.assert_called_once_with(
        inventory=inventory,
        playbook=playbook,
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
    )

    mock_ansible.reset_mock()
    inventory["localhost"]["vars"]["action"] = "status"
    with pytest.raises(DeploymentLibvirtException) as exception:
        libvirt_deployment._manage_packetbeat("status")
    assert "Unable to apply action status for Packetbeat." in str(exception.value)

def test_elastic_install_endpoint(mocker, libvirt_deployment, ansible_path):
    libvirt_deployment.description.monitor_type = "endpoint"
    libvirt_deployment.description.deploy_elastic = True
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(LibvirtDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mocker.patch.object(LibvirtClient,"get_instance_status",return_value="RUNNING")
    inventory = {
        "server": {
            "hosts": {
                "udelar-lab01-1-server" : {
                    "ansible_host": "10.0.0.129",
                    "ansible_user": "ubuntu",
                    "ansible_ssh_common_args": libvirt_deployment.description.ansible_ssh_common_args,
                    "become_flags": "-i",
                    "copy": 1,
                    "instance": 1,
                    "parameter" : {'flags': 'Flag 2'}
                }
            },
            "vars": {
                "ansible_become": True,
                "basename": "server",
                "elastic_url": "https://10.0.0.129:8220",
                "instances": libvirt_deployment.description.instance_number,
                "token": "1234567890abcdef",
                "institution": libvirt_deployment.description.institution,
                "lab_name": libvirt_deployment.description.lab_name,
                "platform": "libvirt",
            },
        },
        "victim": {
            "hosts": {
                "udelar-lab01-1-victim-1" : {
                    "ansible_host": "10.0.0.129",
                    "ansible_user": "administrator",
                    "ansible_ssh_common_args": libvirt_deployment.description.ansible_ssh_common_args,
                    "copy": 1,
                    "instance": 1,
                    "ansible_become_method": "runas",
                    "ansible_become_user": "administrator",
                    "ansible_shell_type": "powershell",
                    "parameter" : {'flags': 'Flag 2'}

                },
                "udelar-lab01-1-victim-2" : {
                    "ansible_host": "10.0.0.129",
                    "ansible_user": "administrator",
                    "ansible_ssh_common_args": libvirt_deployment.description.ansible_ssh_common_args,
                    "copy": 2,
                    "instance": 1,
                    "ansible_become_method": "runas",
                    "ansible_become_user": "administrator",
                    "ansible_shell_type": "powershell",
                    "parameter" : {'flags': 'Flag 2'}
                }
            },
            "vars": {
                "ansible_become": True,
                "basename": "victim",
                "elastic_url": "https://10.0.0.129:8220",
                "instances": libvirt_deployment.description.instance_number,
                "token": "1234567890abcdef",
                "institution": libvirt_deployment.description.institution,
                "lab_name": libvirt_deployment.description.lab_name,
                "platform": "libvirt",
            },
        }
    }
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)
    libvirt_deployment._elastic_install_endpoint([1])
    assert mock_ansible.call_count == 2
    mock_ansible.assert_has_calls([
        mocker.call(
            inventory=inventory,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(
            inventory=inventory,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "endpoint_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        )
    ],any_order=False)
    libvirt_deployment.description.monitor_type = "traffic"


def test_deploy_infraestructure(mocker, capsys, libvirt_deployment, ansible_path, test_data_path):
    # Deploy only instances
    libvirt_deployment.description.monitor_type = "traffic"
    libvirt_deployment.description.deploy_caldera = False
    libvirt_deployment.description.ansible_playbooks_path = libvirt_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(libvirt_deployment.description, "get_services_to_deploy", return_value=[])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_deployment = mocker.patch.object(libvirt_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    libvirt_deployment.deploy_infraestructure(None)

    mock_deployment.assert_called_once_with(
        libvirt_deployment.terraform_module_path,
        variables=libvirt_deployment.get_deploy_cr_vars(),
        resources=None,
    )
    assert len(mock_ansible.mock_calls) == 3
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/trainees.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\n"

    # Deploy elastic services using traffic as monitor_type
    libvirt_deployment.description.monitor_type = "traffic"
    libvirt_deployment.description.deploy_caldera = False
    libvirt_deployment.description.ansible_playbooks_path = libvirt_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(libvirt_deployment.description, "get_services_to_deploy", return_value=["elastic"])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_deployment = mocker.patch.object(libvirt_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(LibvirtDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])

    libvirt_deployment.deploy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(libvirt_deployment.terraform_services_module_path,
            variables=libvirt_deployment.get_deploy_services_vars(),
            resources=None,
        ),
        mocker.call(libvirt_deployment.terraform_module_path,
            variables=libvirt_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
    ])
    assert len(mock_ansible.mock_calls) == 7
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=libvirt_deployment.ansible_services_path,
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "agent_manage.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/trainees.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nDeploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\n"

    # Deploy elastic services using endpoint as monitor_type
    libvirt_deployment.description.monitor_type = "endpoint"
    libvirt_deployment.description.ansible_playbooks_path = libvirt_deployment.description.ansible_playbooks_path.replace("traffic","endpoint")
    mocker.patch.object(libvirt_deployment.description, "get_services_to_deploy", return_value=["elastic"])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_deployment = mocker.patch.object(libvirt_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(LibvirtDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(LibvirtDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])

    libvirt_deployment.deploy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(libvirt_deployment.terraform_services_module_path,
            variables=libvirt_deployment.get_deploy_services_vars(),
            resources=None,
        ),
        mocker.call(libvirt_deployment.terraform_module_path,
            variables=libvirt_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
    ])
    assert len(mock_ansible.mock_calls) == 7
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=libvirt_deployment.ansible_services_path,
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/trainees.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-endpoint/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "endpoint_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nDeploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\nConfiguring elastic agents...\n"

    # Deploy caldera services using endpoint as monitor_type
    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.deploy_caldera = True
    mocker.patch.object(libvirt_deployment.description, "get_services_to_deploy", return_value=["caldera"])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_deployment = mocker.patch.object(libvirt_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")

    libvirt_deployment.deploy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(libvirt_deployment.terraform_services_module_path,
            variables=libvirt_deployment.get_deploy_services_vars(),
            resources=None,
        ),
        mocker.call(libvirt_deployment.terraform_module_path,
            variables=libvirt_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
    ])
    assert len(mock_ansible.mock_calls) == 9
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=libvirt_deployment.ansible_services_path,
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/trainees.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-endpoint/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "caldera", "agent_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "caldera", "agent_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nDeploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\nConfiguring caldera agents...\n"

def test_deploy_infraestructure_specific_instance(mocker, capsys, libvirt_deployment, ansible_path, test_data_path):
    # Deploy caldera services using endpoint as monitor_type
    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.deploy_caldera = True
    mocker.patch.object(libvirt_deployment.description, "get_services_to_deploy", return_value=["caldera"])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_deployment = mocker.patch.object(libvirt_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(LibvirtDeployment,"get_ssh_hostname",return_value="10.0.0.130")

    libvirt_deployment.deploy_infraestructure([1])

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(libvirt_deployment.terraform_services_module_path,
            variables=libvirt_deployment.get_deploy_services_vars(),
            resources=libvirt_deployment.get_services_resources_to_target_apply([1]),
        ),
        mocker.call(libvirt_deployment.terraform_module_path,
            variables=libvirt_deployment.get_deploy_cr_vars(),
            resources=libvirt_deployment.get_cr_resources_to_target_apply([1]),
        ),
    ])
    assert len(mock_ansible.mock_calls) == 9
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=libvirt_deployment.ansible_services_path,
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/trainees.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-endpoint/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "caldera", "agent_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{ansible_path}/wait_for_connection.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=os.path.join(libvirt_deployment.base_dir, "services", "caldera", "agent_install.yml"),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nDeploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\nConfiguring caldera agents...\n"    
    
def test_destroy_infraestructure(mocker, capsys, libvirt_deployment):
    #Destroy only infraestructure
    libvirt_deployment.description.monitor_type = "traffic"
    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.deploy_caldera = False
    libvirt_deployment.description.ansible_playbooks_path = libvirt_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(libvirt_deployment.description, "get_services_to_deploy", return_value=[])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_deployment = mocker.patch.object(libvirt_deployment, "terraform_destroy")

    libvirt_deployment.destroy_infraestructure(None)

    mock_deployment.assert_called_once_with(
        libvirt_deployment.terraform_module_path,
        variables=libvirt_deployment.get_deploy_cr_vars(),
        resources=None,
    )
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\n"

    # Deploy all services using traffic as monitor_type
    libvirt_deployment.description.monitor_type = "traffic"
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.ansible_playbooks_path = libvirt_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(libvirt_deployment.description, "get_services_to_deploy", return_value=["elastic","caldera"])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_deployment = mocker.patch.object(libvirt_deployment, "terraform_destroy")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    libvirt_deployment.destroy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(libvirt_deployment.terraform_module_path,
            variables=libvirt_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
        mocker.call(libvirt_deployment.terraform_services_module_path,
            variables=libvirt_deployment.get_deploy_services_vars(),
            resources=None,
        ),
    ])
    mock_ansible.assert_called_once_with(inventory=mocker.ANY,
        playbook=os.path.join(libvirt_deployment.base_dir, "services", "elastic", "agent_manage.yml"),
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
    ),
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\nDestroying Cyber Range services...\n"

    # Destroy all services using endpoint as monitor_type
    libvirt_deployment.description.monitor_type = "endpoint"
    libvirt_deployment.description.ansible_playbooks_path = libvirt_deployment.description.ansible_playbooks_path.replace("traffic","endpoint")
    mocker.patch.object(libvirt_deployment.description, "get_services_to_deploy", return_value=["elastic","caldera"])
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    mock_deployment = mocker.patch.object(libvirt_deployment, "terraform_destroy")

    libvirt_deployment.destroy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(libvirt_deployment.terraform_module_path,
            variables=libvirt_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
        mocker.call(libvirt_deployment.terraform_services_module_path,
            variables=libvirt_deployment.get_deploy_services_vars(),
            resources=None,
        ),
    ])
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\nDestroying Cyber Range services...\n"

def test_get_parameters(capsys, libvirt_deployment):
    libvirt_deployment.get_parameters(instances=[1],directory=None)
    captured = capsys.readouterr()
    assert "┌──────────┬─────────────────────┐" in captured.out
    assert "│ Instance │      Parameters     │" in captured.out
    assert "├──────────┼─────────────────────┤" in captured.out
    assert "│    1     │ {'flags': 'Flag 2'} │" in captured.out
    assert "└──────────┴─────────────────────┘" in captured.out  

def test_destroy_infraestructure_specific_instance(mocker, capsys, libvirt_deployment):
    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.deploy_caldera = False
    mock_terraform = mocker.patch.object(libvirt_deployment, "terraform_destroy")
    mock_libvirt = mocker.patch.object(libvirt_deployment.client, "delete_image")
    libvirt_deployment.destroy_infraestructure(instances=[1])
    mock_terraform.assert_called_once_with(
        libvirt_deployment.terraform_module_path,
        variables=libvirt_deployment.get_deploy_cr_vars(),
        resources=['libvirt_domain.machines["udelar-lab01-1-attacker"]', 
                   'libvirt_domain.machines["udelar-lab01-1-victim-1"]', 
                   'libvirt_domain.machines["udelar-lab01-1-victim-2"]', 
                   'libvirt_domain.machines["udelar-lab01-1-server"]'
                   ],
    )
    mock_libvirt.assert_has_calls([
        mocker.call(
            "pool-dir",
            "udelar-lab01-1-attacker"
        ),
        mocker.call(
            "pool-dir",
            "guestinit-udelar-lab01-1-attacker.iso"
        ),
        mocker.call(
            "pool-dir",
            "udelar-lab01-1-victim-1"
        ),
        mocker.call(
            "pool-dir",
            "guestinit-udelar-lab01-1-victim-1.iso"
        ),
        mocker.call(
            "pool-dir",
            "udelar-lab01-1-victim-2"
        ),
        mocker.call(
            "pool-dir",
            "guestinit-udelar-lab01-1-victim-2.iso"
        ),
        mocker.call(
            "pool-dir",
            "udelar-lab01-1-server"
        ),
        mocker.call(
            "pool-dir",
            "guestinit-udelar-lab01-1-server.iso"
        ),
    ],any_order=False)
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\n"

def test_create_services_images_ok(mocker, libvirt_deployment, base_tectonic_path, services_packer, test_data_path):
    machines = {
        "caldera": {
            "base_os": "rocky8",
            "ansible_playbook": os.path.join(base_tectonic_path, "services", "caldera", "base_config.yml"),
            "vcpu": 2,
            "memory": 2048,
            "disk": 20,
        },
        "elastic": {
            "base_os": "rocky8",
            "ansible_playbook": os.path.join(base_tectonic_path, "services", "elastic", "base_config.yml"),
            "vcpu": 8,
            "memory": 16384,
            "disk": 110,
        },
    }
    variables = {
        "ansible_scp_extra_args": "'-O'" if tectonic.ssh.ssh_version() >= 9 else "",
        "ansible_ssh_common_args": "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no",
        "aws_region": "us-east-1",
        "libvirt_proxy": "http://proxy.fing.edu.uy:3128",
        "libvirt_storage_pool": "pool-dir",
        "libvirt_uri": f"test:///{test_data_path}/libvirt_config.xml",
        "machines_json": json.dumps(machines),
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "platform": "libvirt",
        "remove_ansible_logs": str(not libvirt_deployment.description.keep_ansible_logs),
        "elastic_version": "7.10.2",
        "elastic_latest_version": "no",
        "caldera_version": "master",
        "packetbeat_vlan_id": "1"
    }
    mock_cmd = mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", ""))
    mock_build = mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(0, "success", ""))
    libvirt_deployment.create_services_images({"caldera":True,"elastic":True, "packetbeat":False})
    mock_cmd.assert_called_once_with("init", services_packer)
    mock_build.assert_called_once_with(services_packer, var=variables)

def test_get_services_network_data(libvirt_deployment):
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.deploy_elastic = True
    assert libvirt_deployment._get_services_network_data() == {
        "udelar-lab01-services" :{
            "cidr" : libvirt_deployment.description.services_network,
            "mode": "none",
        },
        "udelar-lab01-internet" :{
            "cidr" : libvirt_deployment.description.internet_network,
            "mode": "nat",
        },
    }
    libvirt_deployment.description.deploy_elastic = False
    assert libvirt_deployment._get_services_network_data() == {
        "udelar-lab01-services" :{
            "cidr" : libvirt_deployment.description.services_network,
            "mode": "none",
        },
    }
    libvirt_deployment.description.deploy_elastic = True

def test_get_services_guest_data(libvirt_deployment):
    libvirt_deployment.description.deploy_caldera = True
    libvirt_deployment.description.deploy_elastic = True
    assert libvirt_deployment._get_services_guest_data() == {
        "udelar-lab01-elastic" : {
            "guest_name": "udelar-lab01-elastic",
            "base_name": "elastic",
            "hostname": "elastic",
            "base_os": "rocky8",
            "interfaces": {
                "udelar-lab01-elastic-1" : {
                    "name": "udelar-lab01-elastic-1",
                    "index": 3,
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "internet",
                    "subnetwork_name": "udelar-lab01-internet",
                    "private_ip": "10.0.0.2",
                    "mask": "25",
                },
                "udelar-lab01-elastic-2" : {
                    "name": "udelar-lab01-elastic-2",
                    "index": 4,
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.130",
                    "mask": "25",
                }
            },
            "memory": libvirt_deployment.description.services["elastic"]["memory"],
            "vcpu": libvirt_deployment.description.services["elastic"]["vcpu"],
            "disk": libvirt_deployment.description.services["elastic"]["disk"],
        },
        "udelar-lab01-caldera" : {
            "guest_name": "udelar-lab01-caldera",
            "base_name": "caldera",
            "hostname": "caldera",
            "base_os": "rocky8",
            "interfaces": {
                "udelar-lab01-caldera-1" : {
                    "name": "udelar-lab01-caldera-1",
                    "index": 3,
                    "guest_name": "udelar-lab01-caldera",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.132",
                    "mask": "25",
                }
            },
            "memory": libvirt_deployment.description.services["caldera"]["memory"],
            "vcpu": libvirt_deployment.description.services["caldera"]["vcpu"],
            "disk": libvirt_deployment.description.services["caldera"]["disk"],
        }
    }
    libvirt_deployment.description.monitor_type = "traffic"
    libvirt_deployment.description.deploy_caldera = False
    assert libvirt_deployment._get_services_guest_data() == {
        "udelar-lab01-elastic" : {
            "guest_name": "udelar-lab01-elastic",
            "base_name": "elastic",
            "hostname": "elastic",
            "base_os": "rocky8",
            "interfaces": {
                "udelar-lab01-elastic-1" : {
                    "name": "udelar-lab01-elastic-1",
                    "index": 3,
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "internet",
                    "subnetwork_name": "udelar-lab01-internet",
                    "private_ip": "10.0.0.2",
                    "mask": "25",
                },
                "udelar-lab01-elastic-2" : {
                    "name": "udelar-lab01-elastic-2",
                    "index": 4,
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.130",
                    "mask": "25",
                }
            },
            "memory": libvirt_deployment.description.services["elastic"]["memory"],
            "vcpu": libvirt_deployment.description.services["elastic"]["vcpu"],
            "disk": libvirt_deployment.description.services["elastic"]["disk"],
        },
    }

def test_get_services_resources_to_target_apply(libvirt_deployment):
    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = True
    result = libvirt_deployment.get_services_resources_to_target_apply([1])
    expected = [
        'libvirt_volume.cloned_image["udelar-lab01-elastic"]',
        'libvirt_cloudinit_disk.commoninit["udelar-lab01-elastic"]',
        'libvirt_domain.machines["udelar-lab01-elastic"]',
        'libvirt_volume.cloned_image["udelar-lab01-caldera"]',
        'libvirt_cloudinit_disk.commoninit["udelar-lab01-caldera"]',
        'libvirt_domain.machines["udelar-lab01-caldera"]',
        'libvirt_network.subnets["udelar-lab01-services"]',
        'libvirt_network.subnets["udelar-lab01-internet"]',
    ]
    assert result == expected

    libvirt_deployment.description.deploy_elastic = False
    libvirt_deployment.description.deploy_caldera = True
    result = libvirt_deployment.get_services_resources_to_target_apply([1])
    expected = [
        'libvirt_volume.cloned_image["udelar-lab01-caldera"]',
        'libvirt_cloudinit_disk.commoninit["udelar-lab01-caldera"]',
        'libvirt_domain.machines["udelar-lab01-caldera"]',
        'libvirt_network.subnets["udelar-lab01-services"]',
    ]
    assert result == expected

    libvirt_deployment.description.deploy_elastic = True
    libvirt_deployment.description.deploy_caldera = False
    result = libvirt_deployment.get_services_resources_to_target_apply([1])
    expected = [
        'libvirt_volume.cloned_image["udelar-lab01-elastic"]',
        'libvirt_cloudinit_disk.commoninit["udelar-lab01-elastic"]',
        'libvirt_domain.machines["udelar-lab01-elastic"]',
        'libvirt_network.subnets["udelar-lab01-services"]',
        'libvirt_network.subnets["udelar-lab01-internet"]',
    ]
    assert result == expected

def test_get_services_resources_to_target_destroy(libvirt_deployment):
    assert libvirt_deployment.get_services_resources_to_target_destroy([1]) == []

def test_get_service_info(mocker, libvirt_deployment):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    playbook = os.path.join(Deployment.base_dir, "services", "elastic", "get_info.yml")
    inventory = {'elastic': {'hosts': {'udelar-lab01-elastic': {'ansible_host': None, 'ansible_user': 'rocky', 'ansible_ssh_common_args': '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no', 'instance': None, 'copy': 1, 'parameter': {}, 'become_flags': '-i'}}, 'vars': {'ansible_become': True, 'basename': 'elastic', 'instances': 2, 'platform': 'libvirt', 'institution': 'udelar', 'lab_name': 'lab01', 'action': 'agents_status'}}}
    libvirt_deployment._get_service_info("elastic",playbook,{"action":"agents_status"})
    mock_ansible.assert_called_once_with(
        inventory=inventory,
        playbook=playbook,
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not libvirt_deployment.description.keep_ansible_logs }
    )