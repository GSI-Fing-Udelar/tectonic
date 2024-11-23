
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
import python_terraform
import tectonic.ssh
import ansible_runner
import packerpy
from freezegun import freeze_time

from tectonic.docker_client import DockerClientException, Client as DockerClient
from tectonic.deployment_docker import DockerDeployment, DeploymentDockerException
from tectonic.deployment import *
import tectonic.constants

import importlib.resources as tectonic_resources


def test_constructor(monkeypatch, description, docker_client):
    description.deploy_elastic = False
    def patch_docker_client(self, description):
        self.connection = docker_client
        self.description = description
    monkeypatch.setattr(DockerClient, "__init__", patch_docker_client)
    docker_deployment = DockerDeployment(
        description=description,
        gitlab_backend_url="https://gitlab.com",
        gitlab_backend_username="testuser",
        gitlab_backend_access_token="testtoken",
    )

def test_generate_backend_config(docker_deployment):
    answer = docker_deployment.generate_backend_config(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker')
    assert len(answer) == 1
    assert "path=terraform-states/udelar-lab01-gsi-lab-docker" in answer

def test_terraform_apply(mocker, docker_deployment):
    variables = {"var1": "value1", "var2": "value2"}
    resources = {'docker_container.machines["udelar-lab01-1-attacker"]'}

    terraform_dir = tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker'

    mock = mocker.patch("tectonic.deployment.run_terraform_cmd")
    docker_deployment.terraform_apply(terraform_dir, variables, resources)
    mock.assert_has_calls([mocker.call(mocker.ANY, "init", [],
                                       reconfigure=python_terraform.IsFlagged,
                                       backend_config=docker_deployment.generate_backend_config(terraform_dir)
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

def test_get_deploy_cr_vars(docker_deployment):
    variables = docker_deployment.get_deploy_cr_vars()
    # do not compare authorized_keys as its order is not guaranteed
    variables.pop('authorized_keys', None)
    assert variables == {
        "institution": "udelar",
        "lab_name": "lab01",
        "instance_number": 2,
        "ssh_public_key_file": docker_deployment.description.ssh_public_key_file,
        "subnets_json": json.dumps(docker_deployment.description.subnets),
        "guest_data_json": json.dumps(docker_deployment.description.get_guest_data()),
        "default_os": "ubuntu22",
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "configure_dns": True,
        "docker_uri":"unix:///var/run/docker.sock"
    }

def test_get_deploy_services_vars(docker_deployment):
    variables = docker_deployment.get_deploy_services_vars()
    # do not compare authorized_keys as its order is not guaranteed
    variables.pop('authorized_keys', None)
    assert variables == {
        "institution": "udelar",
        "lab_name": "lab01",
        "ssh_public_key_file": docker_deployment.description.ssh_public_key_file,
        "subnets_json": json.dumps(docker_deployment._get_services_network_data()),
        "guest_data_json": json.dumps(docker_deployment._get_services_guest_data()),
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "configure_dns": True,
        "docker_uri":"unix:///var/run/docker.sock",
    }


def test_deploy_cr_all_instances(mocker, docker_deployment):
    mock = mocker.patch.object(docker_deployment, "terraform_apply")
    docker_deployment._deploy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker', docker_deployment.get_deploy_cr_vars(), None)
    mock.assert_called_once_with(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
        variables=docker_deployment.get_deploy_cr_vars(),
        resources=None,
    )


def test_deploy_cr_instance_two(mocker, docker_deployment):
    mock = mocker.patch.object(docker_deployment, "terraform_apply")

    docker_deployment._deploy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker', docker_deployment.get_deploy_cr_vars(), [2])

    mock.assert_called_once_with(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
                                 variables=docker_deployment.get_deploy_cr_vars(),
                                 resources=docker_deployment.get_cr_resources_to_target_apply([2]),
                                 )

def test_deploy_packetbeat(mocker, docker_deployment):
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(DockerDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    inventory = {'udelar-lab01-localhost': {'hosts': {'localhost': {'become_flags': '-i'}}, 'vars': {'ansible_become': True, 'ansible_user': 'gsi', 'basename': 'localhost', 'instances': 2, 'platform': 'docker', 'institution': 'udelar', 'lab_name': 'lab01', 'ansible_connection': 'local', 'action': 'install', 'elastic_url': 'https://10.0.0.129:8220', 'token': '1234567890abcdef', 'elastic_agent_version': '7.10.2', 'proxy': 'http://proxy.fing.edu.uy:3128'}}}
    docker_deployment._deploy_packetbeat()
    assert len(mock.mock_calls) == 1
    mock.assert_has_calls([
        mocker.call(inventory=inventory,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        )
    ])


def test_terraform_destroy(mocker, docker_deployment):
    variables = {"var1": "value1", "var2": "value2"}
    resources = {'docker_container.machines["udelar-lab01-1-attacker"]'}

    terraform_dir = tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker'

    mock = mocker.patch("tectonic.deployment.run_terraform_cmd")
    docker_deployment.terraform_destroy(terraform_dir, variables, resources)

    mock.assert_has_calls([mocker.call(mocker.ANY, "init", [],
                                       reconfigure=python_terraform.IsFlagged,
                                       backend_config=docker_deployment.generate_backend_config(terraform_dir)
                                       ),
                           mocker.call(mocker.ANY, "destroy",
                                       variables,
                                       auto_approve=True,
                                       input=False,
                                       target=resources,
                                       ),
                           ])



def test_destroy_packetbeat(mocker, docker_deployment):
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"elastic":"password"})
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)
    inventory = {'udelar-lab01-localhost': {'hosts': {'localhost': {'become_flags': '-i'}}, 'vars': {'ansible_become': True, 'ansible_user': 'gsi', 'basename': 'localhost', 'instances': 2, 'platform': 'docker', 'institution': 'udelar', 'lab_name': 'lab01', 'ansible_connection': 'local', 'action': 'delete' }}}

    docker_deployment._destroy_packetbeat()

    mock.assert_called_once_with(inventory=inventory,
        playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml'),
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
    )


def test_destroy_cr_all_instances(mocker, docker_deployment):
    mock = mocker.patch.object(docker_deployment, "terraform_destroy")

    docker_deployment._destroy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker', docker_deployment.get_deploy_cr_vars(), None)
    mock.assert_called_once_with(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
                                 variables=docker_deployment.get_deploy_cr_vars(),
                                 resources=None,
                                 )


def test_destroy_cr_instance_two(mocker, docker_deployment):
    mock = mocker.patch.object(docker_deployment, "terraform_destroy")

    docker_deployment._destroy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker', docker_deployment.get_deploy_cr_vars(), [2])
    mock.assert_called_once_with(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
                                 variables=docker_deployment.get_deploy_cr_vars(),
                                 resources=docker_deployment.get_cr_resources_to_target_destroy([2]),
                                 )

def test_terraform_recreate(mocker, docker_deployment):
    machines = {'docker_container.machines["udelar-lab01-1-attacker"]'}

    terraform_dir = tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker'

    mock = mocker.patch("tectonic.deployment.run_terraform_cmd")
    docker_deployment.terraform_recreate(terraform_dir, machines)
    mock.assert_has_calls([mocker.call(mocker.ANY, "init", [],
                                       reconfigure=python_terraform.IsFlagged,
                                       backend_config=docker_deployment.generate_backend_config(terraform_dir)
                                       ),
                           mocker.call(mocker.ANY, "plan",
                                       variables=docker_deployment.get_deploy_cr_vars(),
                                       input=False,
                                       replace=machines,
                                       ),
                           mocker.call(mocker.ANY, "apply",
                                       variables=docker_deployment.get_deploy_cr_vars(),
                                       auto_approve=True,
                                       input=False,
                                       replace=machines,
                                       ),
                           ])


def test_create_cr_images_ok(mocker, docker_deployment, test_data_path):
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.monitor_type = "traffic"
    machines = {
        "attacker": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
        },
        "victim": {
            "base_os": "windows_srv_2022",
            "endpoint_monitoring": False,
        },
        "server": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
        },
    }
    variables = {
        "ansible_playbooks_path": docker_deployment.description.ansible_playbooks_path,
        "ansible_scp_extra_args": "",
        "ansible_ssh_common_args": "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no",
        "aws_region": "us-east-1",
        "instance_number": 2,
        "institution": "udelar",
        "lab_name": "lab01",
        "proxy": "http://proxy.fing.edu.uy:3128",
        "libvirt_storage_pool": "pool-dir",
        "libvirt_uri": f"test:///{test_data_path}/libvirt_config.xml",
        "machines_json": json.dumps(machines),
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "platform": "docker",
        "remove_ansible_logs": str(not docker_deployment.description.keep_ansible_logs),
        "elastic_version": docker_deployment.description.elastic_stack_version,
    }

    mock_cmd = mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", ""))
    mock_build = mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(0, "success", ""))
    docker_deployment.create_cr_images()
    mock_cmd.assert_called_once_with("init", str(docker_deployment.cr_packer_path))
    mock_build.assert_called_once_with(str(docker_deployment.cr_packer_path), var=variables)

    #Test monitor_type == endpoint
    docker_deployment.description.monitor_type = "endpoint"
    docker_deployment.description.deploy_elastic = True
    machines = {
        "attacker": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
        },
        "victim": {
            "base_os": "windows_srv_2022",
            "endpoint_monitoring": True,
        },
        "server": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": True,
        },
    }
    variables['machines_json'] = json.dumps(machines)
    mock_cmd = mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", ""))
    mock_build = mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(0, "success", ""))
    docker_deployment.create_cr_images()
    mock_cmd.assert_called_once_with("init", str(docker_deployment.cr_packer_path))
    mock_build.assert_called_once_with(str(docker_deployment.cr_packer_path), var=variables),
    docker_deployment.description.monitor_type = "traffic"
    docker_deployment.description.deploy_elastic = False


def test_create_cr_images_error(mocker, docker_deployment):
    mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(1, b"error", b"error"))
    with pytest.raises(TerraformRunException):
        docker_deployment.create_cr_images()

    mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, b"success", b""))
    mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(1, b"error", b"error"))
    with pytest.raises(TerraformRunException):
        docker_deployment.create_cr_images()


def test_student_access(mocker, docker_deployment):
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    ansible_libvirt = tectonic.ansible.Ansible(docker_deployment)
    entry_points = [ base_name for base_name, guest in docker_deployment.description.guest_settings.items()
                     if guest.get("entry_point") ]
    machine_list = docker_deployment.description.parse_machines(guests=entry_points)

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

    docker_deployment.student_access(None)
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
                                 quiet=True,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
                                 )


def test_student_access_no_passwords(mocker, docker_deployment):
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    ansible_libvirt = tectonic.ansible.Ansible(docker_deployment)
    entry_points = [ base_name for base_name, guest in docker_deployment.description.guest_settings.items()
                     if guest.get("entry_point") ]
    machine_list = docker_deployment.description.parse_machines(guests=entry_points)
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

    docker_deployment.description.create_student_passwords = False
    docker_deployment.student_access(None)
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
                                 quiet=True,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
                                 )
    docker_deployment.description.create_student_passwords = True


def test_student_access_no_pubkeys(mocker, docker_deployment):
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    ansible_libvirt = tectonic.ansible.Ansible(docker_deployment)
    entry_points = [ base_name for base_name, guest in docker_deployment.description.guest_settings.items()
                     if guest.get("entry_point") ]
    machine_list = docker_deployment.description.parse_machines(guests=entry_points)
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

    pubkey_dir = docker_deployment.description.student_pubkey_dir
    docker_deployment.description.student_pubkey_dir = None
    docker_deployment.student_access(None)
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
                                 quiet=True,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
                                 )

    docker_deployment.description.student_pubkey_dir = pubkey_dir


def test_get_instance_status(docker_deployment, docker_client):
    state = docker_deployment.get_instance_status("udelar-lab01-1-attacker")
    assert state == "RUNNING"
    
    docker_client.containers.get.side_effect = Exception("Unexpected error")
    with pytest.raises(DockerClientException) as exception:
        docker_deployment.get_instance_status("test")
    assert "Unexpected error" in str(exception.value)

def test_get_cyberrange_data_elasticup(mocker, docker_deployment):
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = False
    mocker.patch.object(DockerClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"elastic":"password"})
    table = docker_deployment.get_cyberrange_data()
    expected = """┌──────────────────────────────────┬────────────────────────┐
│               Name               │         Value          │
├──────────────────────────────────┼────────────────────────┤
│            Kibana URL            │ https://127.0.0.1:5601 │
│ Kibana user (username: password) │   elastic: password    │
└──────────────────────────────────┴────────────────────────┘"""
    assert expected == table.get_string()

def test_get_cyberrange_data_elasticdown(mocker, docker_deployment):
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = False
    mocker.patch.object(DockerClient,"get_instance_status",return_value={"udelar-lab01-elastic": {"Status": "NOT RUNNING"}})
    result = docker_deployment.get_cyberrange_data()
    expected = """Unable to get Elastic info right now. Please make sure de Elastic machine is running."""
    assert expected == result

def test_get_cyberrange_data_calderaup(mocker, docker_deployment):
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = True
    mocker.patch.object(DockerClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"red":"passwordred","blue":"passwordblue"})
    table = docker_deployment.get_cyberrange_data()
    expected = """┌───────────────────────────────────┬────────────────────────┐
│                Name               │         Value          │
├───────────────────────────────────┼────────────────────────┤
│            Caldera URL            │ https://127.0.0.1:8443 │
│ Caldera user (username: password) │    red: passwordred    │
│ Caldera user (username: password) │   blue: passwordblue   │
└───────────────────────────────────┴────────────────────────┘"""
    assert expected == table.get_string()

def test_get_cyberrange_data_calderadown(mocker, docker_deployment):
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = True
    mocker.patch.object(DockerClient,"get_instance_status",return_value={"udelar-lab01-caldera": {"Status": "NOT RUNNING"}})
    result = docker_deployment.get_cyberrange_data()
    expected = """Unable to get Caldera info right now. Please make sure de Caldera machine is running."""
    assert expected == result

def test_get_cyberrange_data_noservices(capsys, docker_deployment):
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = False
    docker_deployment.get_cyberrange_data()
    result = capsys.readouterr()
    assert "" == result.out

def test_get_cyberrange_data_error(mocker, docker_deployment):
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = True
    mocker.patch.object(DockerClient,"get_instance_status",return_value="RUNNING")

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    with pytest.raises(DeploymentDockerException):
        docker_deployment.get_cyberrange_data()

def test_connect_to_instance(mocker, docker_deployment):
    mock_run = mocker.patch("subprocess.run")
    docker_deployment.connect_to_instance("udelar-lab01-1-attacker", "ubuntu")
    mock_run.assert_called_once()

    mock_run.side_effect = Exception("Unexpected error")
    with pytest.raises(DockerClientException) as exception:
        docker_deployment.connect_to_instance("udelar-lab01-1-attacker", "ubuntu")
        mock_run.assert_called_once()
    assert "Unexpected error" in str(exception.value)

def test_get_ssh_proxy_command(docker_deployment):
    proxy = docker_deployment.get_ssh_proxy_command()
    assert proxy is None

def test_get_ssh_hostname(docker_deployment):
    hostname = docker_deployment.get_ssh_hostname("udelar-lab01-1-attacker")
    assert hostname == "10.0.1.4"

def test_start_instance(docker_deployment, docker_client):
    docker_deployment.start_instance("udelar-lab01-1-attacker")
    docker_client.containers.get("udelar-lab01-1-attacker").start.assert_called_once()

    docker_client.containers.get.side_effect = Exception("Unexpected error")
    with pytest.raises(DockerClientException) as exception:
        docker_deployment.start_instance("udelar-lab01-1-attacker")
        assert docker_client.containers.get("udelar-lab01-1-attacker").start.call_count == 0
    assert "Unexpected error" in str(exception.value)

def test_stop_instance(docker_deployment, docker_client):
    docker_deployment.stop_instance("udelar-lab01-1-attacker")
    docker_client.containers.get("udelar-lab01-1-attacker").stop.assert_called_once()

    docker_client.containers.get.side_effect = Exception("Unexpected error")
    with pytest.raises(DockerClientException) as exception:
        docker_deployment.stop_instance("udelar-lab01-1-attacker")
        assert docker_client.containers.get("udelar-lab01-1-attacker").stop.call_count == 0
    assert "Unexpected error" in str(exception.value)

def test_reboot_instance(docker_deployment, docker_client):
    docker_deployment.reboot_instance("udelar-lab01-1-attacker")
    docker_client.containers.get("udelar-lab01-1-attacker").restart.assert_called_once()

    docker_client.containers.get.side_effect = Exception("Unexpected error")
    with pytest.raises(DockerClientException) as exception:
        docker_deployment.reboot_instance("udelar-lab01-1-attacker")
        assert docker_client.containers.get("udelar-lab01-1-attacker").restart.call_count == 0
    assert "Unexpected error" in str(exception.value)

def test_delete_cr_images(mocker, docker_deployment, docker_client):
    docker_deployment.delete_cr_images()
    assert docker_client.images.remove.call_count == 3
    docker_client.images.remove.assert_has_calls([mocker.call("udelar-lab01-attacker"),
                           mocker.call("udelar-lab01-victim"),
                           mocker.call("udelar-lab01-server"),
                           ])

    docker_client.reset_mock()
    docker_client.images.remove.side_effect = Exception("Unexpected error")
    with pytest.raises(DeploymentDockerException):
        docker_deployment.delete_cr_images()
    docker_client.images.remove.assert_called_once_with("udelar-lab01-attacker")


def test_get_cr_resources_to_target_apply(docker_deployment):
    expected_resources = ['docker_container.machines["udelar-lab01-1-attacker"]',
                          'docker_container.machines["udelar-lab01-1-victim-1"]',
                          'docker_container.machines["udelar-lab01-1-victim-2"]',
                          'docker_container.machines["udelar-lab01-1-server"]',
                          'docker_container.machines["udelar-lab01-1-server"]',
                          'docker_container.machines["udelar-lab01-2-attacker"]',
                          'docker_container.machines["udelar-lab01-2-victim-1"]',
                          'docker_container.machines["udelar-lab01-2-victim-2"]',
                          'docker_container.machines["udelar-lab01-2-server"]',
                          'docker_network.subnets["udelar-lab01-1-dmz"]',
                          'docker_network.subnets["udelar-lab01-2-internal"]',
                          'docker_network.subnets["udelar-lab01-1-internal"]',
                          'docker_network.subnets["udelar-lab01-2-dmz"]',
                          ]
    resources = docker_deployment.get_cr_resources_to_target_apply(None)
    assert set(resources) == set(expected_resources)

def test_get_cr_resources_to_target_destroy(docker_deployment):
    expected_resources = ['docker_container.machines["udelar-lab01-1-attacker"]',
                          'docker_container.machines["udelar-lab01-1-victim-1"]',
                          'docker_container.machines["udelar-lab01-1-victim-2"]',
                          'docker_container.machines["udelar-lab01-1-server"]',
                          'docker_container.machines["udelar-lab01-1-server"]',
                          ]
    resources = docker_deployment.get_cr_resources_to_target_destroy([1])
    assert set(resources) == set(expected_resources)


def test_get_resources_to_recreate(docker_deployment):
    expected_resources = ['docker_container.machines["udelar-lab01-1-victim-2"]']
    resources = docker_deployment.get_resources_to_recreate([1], ("victim", ), [2])
    assert set(resources) == set(expected_resources)

def test_get_guest_instance_type(docker_deployment):
    instance_type = docker_deployment.get_guest_instance_type("attacker")
    assert instance_type is None

@freeze_time("2022-01-01")
def test_get_services_status(mocker, docker_deployment):
    #Only ELastic with monitor_type traffic
    docker_deployment.description.deploy_caldera = False
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.monitor_type = "traffic"
    mocker.patch.object(DockerClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(DockerDeployment,"_manage_packetbeat",return_value="RUNNING")

    table = docker_deployment.get_services_status()
    expected = """┌─────────────────────────┬─────────┐
│           Name          │  Status │
├─────────────────────────┼─────────┤
│   udelar-lab01-elastic  │ RUNNING │
│ udelar-lab01-packetbeat │ RUNNING │
└─────────────────────────┴─────────┘"""
    assert expected == table.get_string()

    #Only Elastic with monitor_type endpoint
    docker_deployment.description.deploy_caldera = False
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.monitor_type = "endpoint"
    mocker.patch.object(DockerClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(DockerDeployment,"_get_service_info",return_value=[{"agents_status": {"online": 2,"error": 0,"inactive": 0,"offline": 0,"updating": 0,"unenrolled": 0,"degraded": 0,"enrolling": 0,"unenrolling": 0 }}])

    table = docker_deployment.get_services_status()
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
    docker_deployment.description.deploy_caldera = True
    docker_deployment.description.deploy_elastic = False
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.130")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"red":"passwordred","blue":"passwordblue"})
    mocker.patch.object(DockerClient,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(DockerDeployment,"_get_service_info",return_value=[{"agents_status":[{"sleep_min":3,"sleep_max":3,"watchdog":1,"last_seen":"2024-05-05T14:43:17Z"},{"sleep_min":3,"sleep_max":3,"watchdog":1,"last_seen":"2024-05-04T14:43:17Z"}]}])
    table = docker_deployment.get_services_status()
    expected = """┌─────────────────────────────┬─────────┐
│             Name            │  Status │
├─────────────────────────────┼─────────┤
│     udelar-lab01-caldera    │ RUNNING │
│     caldera-agents-alive    │    0    │
│     caldera-agents-dead     │    0    │
│ caldera-agents-pending_kill │    2    │
└─────────────────────────────┴─────────┘"""
    assert expected == table.get_string()

def test_list_instances(mocker, docker_deployment):
    mocker.patch.object(DockerClient, "get_instance_status", return_value="RUNNING")
    result = docker_deployment.list_instances(None, None, None)
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

def test_start(docker_deployment, docker_client):
    docker_deployment.start([1], ["attacker"], None, False)
    docker_client.containers.get("udelar-lab01-1-attacker").start.assert_called_once()

def test_start_services(docker_deployment, docker_client):
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = True

    docker_deployment.start([1], ["attacker"], None, True)

    docker_client.containers.get("udelar-lab01-elastic").start.assert_called_once()
    docker_client.containers.get("udelar-lab01-caldera").start.assert_called_once()
    docker_client.containers.get("udelar-lab01-1-attacker").start.assert_called_once()

def test_shutdown(docker_deployment, docker_client):
    docker_deployment.shutdown([1], ["attacker"], None, False)
    docker_client.containers.get("udelar-lab01-1-attacker").stop.assert_called_once()

def test_shutdown_services(docker_deployment, docker_client):
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = True

    docker_deployment.shutdown([1], ["attacker"], None, True)

    docker_client.containers.get("udelar-lab01-elastic").stop.assert_called_once()
    docker_client.containers.get("udelar-lab01-caldera").stop.assert_called_once()
    docker_client.containers.get("udelar-lab01-1-attacker").stop.assert_called_once()

def test_reboot(docker_deployment, docker_client):
    docker_deployment.reboot([1], ["attacker"], None, False)
    docker_client.containers.get("udelar-lab01-1-attacker").restart.assert_called_once()

def test_reboot_services(docker_deployment, docker_client):
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = True

    docker_deployment.reboot([1], ["attacker"], None, True)

    docker_client.containers.get("udelar-lab01-elastic").restart.assert_called_once()
    docker_client.containers.get("udelar-lab01-caldera").start.assert_not_called()
    docker_client.containers.get("udelar-lab01-1-attacker").start.assert_not_called()


def test_recreate(mocker, capsys, docker_deployment, labs_path):
    docker_deployment.description.ansible_playbooks_path = docker_deployment.description.ansible_playbooks_path.replace("traffic","endpoint")
    docker_deployment.description.monitor_type = "endpoint"
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = True
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(DockerDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mock_terraform = mocker.patch.object(tectonic.deployment.Deployment, "terraform_recreate")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    docker_deployment.recreate([1],["attacker"], None, False)

    mock_terraform.assert_called_once_with(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
                                           mocker.ANY)

    # Test ansible got run with correct playbooks
    assert len(mock_ansible.mock_calls) == 9
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{labs_path}/test-endpoint/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'endpoint_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
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

def test_manage_packetbeat(mocker, docker_deployment):
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)
    inventory = {'udelar-lab01-localhost': {'hosts': {'localhost': {'become_flags': '-i'}}, 'vars': {'ansible_become': True, 'ansible_user': 'gsi', 'basename': 'localhost', 'instances': 2, 'platform': 'docker', 'institution': 'udelar', 'lab_name': 'lab01', 'ansible_connection': 'local', 'action': 'restarted' }}}
    playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml')
    docker_deployment._manage_packetbeat("restarted")
    mock_ansible.assert_called_once_with(
        inventory=inventory,
        playbook=playbook,
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
    )

    mock_ansible.reset_mock()
    inventory["udelar-lab01-localhost"]["vars"]["action"] = "started"
    docker_deployment._manage_packetbeat("started")
    mock_ansible.assert_called_once_with(
        inventory=inventory,
        playbook=playbook,
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
    )

    mock_ansible.reset_mock()
    inventory["udelar-lab01-localhost"]["vars"]["action"] = "stopped"
    docker_deployment._manage_packetbeat("stopped")
    mock_ansible.assert_called_once_with(
        inventory=inventory,
        playbook=playbook,
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
    )

    mock_ansible.reset_mock()
    inventory["udelar-lab01-localhost"]["vars"]["action"] = "status"
    with pytest.raises(DeploymentDockerException) as exception:
        docker_deployment._manage_packetbeat("status")
    assert "Unable to apply action status for Packetbeat." in str(exception.value)

def test_elastic_install_endpoint(mocker, docker_deployment):
    docker_deployment.description.monitor_type = "endpoint"
    docker_deployment.description.deploy_elastic = True
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(DockerDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mocker.patch.object(DockerClient,"get_instance_status",return_value="RUNNING")
    inventory = {
        "server": {
            "hosts": {
                "udelar-lab01-1-server" : {
                    "ansible_host": "udelar-lab01-1-server",
                    "ansible_user": "ubuntu",
                    "ansible_ssh_common_args": docker_deployment.description.ansible_ssh_common_args,
                    "become_flags": "-i",
                    "copy": 1,
                    "instance": 1,
                    'networks': mocker.ANY, 
                    'machine_name': 'udelar-lab01-1-server',
                    "parameter" : {'flags': 'Flag 2'},
                    'random_seed': 'Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941',
                }
            },
            "vars": {
                "ansible_become": True,
                'ansible_connection': 'community.docker.docker_api',
                "basename": "server",
                'docker_host': 'unix:///var/run/docker.sock',
                "elastic_url": "https://10.0.0.129:8220",
                "instances": docker_deployment.description.instance_number,
                "token": "1234567890abcdef",
                "institution": docker_deployment.description.institution,
                "lab_name": docker_deployment.description.lab_name,
                "platform": "docker",
            },
        },
        "victim": {
            "hosts": {
                "udelar-lab01-1-victim-1" : {
                    "ansible_host": "udelar-lab01-1-victim-1",
                    "ansible_user": "administrator",
                    "ansible_ssh_common_args": docker_deployment.description.ansible_ssh_common_args,
                    "copy": 1,
                    "instance": 1,
                    "ansible_become_method": "runas",
                    "ansible_become_user": "administrator",
                    "ansible_shell_type": "powershell",
                    'networks': mocker.ANY,
                    'machine_name': 'udelar-lab01-1-victim-1',
                    "parameter" : {'flags': 'Flag 2'},
                    'random_seed': 'Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941'

                },
                "udelar-lab01-1-victim-2" : {
                    "ansible_host": "udelar-lab01-1-victim-2",
                    "ansible_user": "administrator",
                    "ansible_ssh_common_args": docker_deployment.description.ansible_ssh_common_args,
                    "copy": 2,
                    "instance": 1,
                    "ansible_become_method": "runas",
                    "ansible_become_user": "administrator",
                    "ansible_shell_type": "powershell",
                    'networks': mocker.ANY, 
                    'machine_name': 'udelar-lab01-1-victim-2',
                    "parameter" : {'flags': 'Flag 2'},
                    'random_seed': 'Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941'
                }
            },
            "vars": {
                "ansible_become": True,
                'ansible_connection': 'community.docker.docker_api',
                "basename": "victim",
                "docker_host": "unix:///var/run/docker.sock",
                "elastic_url": "https://10.0.0.129:8220",
                "instances": docker_deployment.description.instance_number,
                "token": "1234567890abcdef",
                "institution": docker_deployment.description.institution,
                "lab_name": docker_deployment.description.lab_name,
                "platform": "docker",
            },
        }
    }
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)
    docker_deployment._elastic_install_endpoint([1])
    assert mock_ansible.call_count == 2
    mock_ansible.assert_has_calls([
        mocker.call(
            inventory=inventory,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(
            inventory=inventory,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'endpoint_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        )
    ],any_order=False)


def test_deploy_infraestructure(mocker, capsys, docker_deployment, test_data_path):
    # Deploy only instances
    docker_deployment.description.ansible_playbooks_path = docker_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    docker_deployment.description.deploy_caldera = False
    docker_deployment.description.deploy_elastic = False
    mocker.patch.object(docker_deployment.description, "get_services_to_deploy", return_value=[])
    mock_deployment = mocker.patch.object(docker_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    docker_deployment.deploy_infraestructure(None)

    mock_deployment.assert_called_once_with(
        tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
        variables=docker_deployment.get_deploy_cr_vars(),
        resources=None,
    )
    assert len(mock_ansible.mock_calls) == 3
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\n"

    # Deploy elastic services using traffic as monitor_type
    docker_deployment.description.monitor_type = "traffic"
    docker_deployment.description.deploy_caldera = False
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.ansible_playbooks_path = docker_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(docker_deployment.description, "get_services_to_deploy", return_value=["elastic"])
    mock_deployment = mocker.patch.object(docker_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(DockerDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])

    docker_deployment.deploy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-docker',
            variables=docker_deployment.get_deploy_services_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
            variables=docker_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
    ])
    assert len(mock_ansible.mock_calls) == 6
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nDeploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\n"

    # Deploy elastic services using endpoint as monitor_type
    docker_deployment.description.monitor_type = "endpoint"
    docker_deployment.description.ansible_playbooks_path = docker_deployment.description.ansible_playbooks_path.replace("traffic","endpoint")
    mocker.patch.object(docker_deployment.description, "get_services_to_deploy", return_value=["elastic"])
    mock_deployment = mocker.patch.object(docker_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.129")
    mocker.patch.object(DockerDeployment, "_get_service_password", return_value={"elastic":"password"})
    mocker.patch.object(DockerDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])

    docker_deployment.deploy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-docker',
            variables=docker_deployment.get_deploy_services_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
            variables=docker_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
    ])
    assert len(mock_ansible.mock_calls) == 7
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-endpoint/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'endpoint_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nDeploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\nConfiguring elastic agents...\n"

    # Deploy caldera services using endpoint as monitor_type
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = True
    mocker.patch.object(docker_deployment.description, "get_services_to_deploy", return_value=["caldera"])
    mock_deployment = mocker.patch.object(docker_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.130")

    docker_deployment.deploy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-docker',
            variables=docker_deployment.get_deploy_services_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
            variables=docker_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
    ])
    assert len(mock_ansible.mock_calls) == 9
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-endpoint/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nDeploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\nConfiguring caldera agents...\n"

def test_deploy_infraestructure_specific_instance(mocker, capsys, docker_deployment, test_data_path):
    # Deploy caldera services using endpoint as monitor_type
    docker_deployment.description.ansible_playbooks_path = docker_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = True
    mocker.patch.object(docker_deployment.description, "get_services_to_deploy", return_value=["caldera"])
    mock_deployment = mocker.patch.object(docker_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(DockerDeployment,"get_ssh_hostname",return_value="10.0.0.130")

    docker_deployment.deploy_infraestructure([1])

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-docker',
            variables=docker_deployment.get_deploy_services_vars(),
            resources=docker_deployment.get_services_resources_to_target_apply([1]),
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
            variables=docker_deployment.get_deploy_cr_vars(),
            resources=docker_deployment.get_cr_resources_to_target_apply([1]),
        ),
    ])
    assert len(mock_ansible.mock_calls) == 9
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nDeploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\nConfiguring caldera agents...\n"    
    
def test_destroy_infraestructure(mocker, capsys, docker_deployment):
    #Destroy only infraestructure
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = False
    mocker.patch.object(docker_deployment.description, "get_services_to_deploy", return_value=[])
    mock_deployment = mocker.patch.object(docker_deployment, "terraform_destroy")

    docker_deployment.destroy_infraestructure(None)

    mock_deployment.assert_called_once_with(
        tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
        variables=docker_deployment.get_deploy_cr_vars(),
        resources=None,
    )
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\n"

    # Deploy all services using traffic as monitor_type
    docker_deployment.description.monitor_type = "traffic"
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = True
    docker_deployment.description.ansible_playbooks_path = docker_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(docker_deployment.description, "get_services_to_deploy", return_value=["elastic","caldera"])
    mock_deployment = mocker.patch.object(docker_deployment, "terraform_destroy")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    docker_deployment.destroy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
            variables=docker_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-docker',
            variables=docker_deployment.get_deploy_services_vars(),
            resources=None,
        ),
    ])
    mock_ansible.assert_called_once_with(inventory=mocker.ANY,
        playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml'),
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
    ),
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\nDestroying Cyber Range services...\n"

    # Destroy all services using endpoint as monitor_type
    docker_deployment.description.monitor_type = "endpoint"
    docker_deployment.description.ansible_playbooks_path = docker_deployment.description.ansible_playbooks_path.replace("traffic","endpoint")
    mocker.patch.object(docker_deployment.description, "get_services_to_deploy", return_value=["elastic","caldera"])
    mock_deployment = mocker.patch.object(docker_deployment, "terraform_destroy")

    docker_deployment.destroy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
            variables=docker_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-docker',
            variables=docker_deployment.get_deploy_services_vars(),
            resources=None,
        ),
    ])
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\nDestroying Cyber Range services...\n"

def test_get_parameters(capsys, docker_deployment):
    docker_deployment.get_parameters(instances=[1],directory=None)
    captured = capsys.readouterr()
    assert "┌──────────┬─────────────────────┐" in captured.out
    assert "│ Instance │      Parameters     │" in captured.out
    assert "├──────────┼─────────────────────┤" in captured.out
    assert "│    1     │ {'flags': 'Flag 2'} │" in captured.out
    assert "└──────────┴─────────────────────┘" in captured.out  

def test_destroy_infraestructure_specific_instance(mocker, capsys, docker_deployment, docker_client):
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = False
    mock_terraform = mocker.patch.object(docker_deployment, "terraform_destroy")
    docker_deployment.destroy_infraestructure(instances=[1])
    mock_terraform.assert_called_once_with(
        tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
        variables=docker_deployment.get_deploy_cr_vars(),
        resources=['docker_container.machines["udelar-lab01-1-attacker"]', 
                   'docker_container.machines["udelar-lab01-1-victim-1"]', 
                   'docker_container.machines["udelar-lab01-1-victim-2"]', 
                   'docker_container.machines["udelar-lab01-1-server"]'
                   ],
    )
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\n"

def test_create_services_images_ok(mocker, docker_deployment, test_data_path):
    docker_deployment.description.deploy_caldera = True
    docker_deployment.description.deploy_elastic = True
    machines = {
        "caldera": {
            "base_os": "rocky8",
            "ansible_playbook": str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'base_config.yml'),
        },
        "elastic": {
            "base_os": "rocky8",
            "ansible_playbook": str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'base_config.yml'),
        },
    }
    variables = {
        "ansible_scp_extra_args": "",
        "ansible_ssh_common_args": "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no",
        "aws_region": "us-east-1",
        "proxy": "http://proxy.fing.edu.uy:3128",
        "libvirt_storage_pool": "pool-dir",
        "libvirt_uri": f"test:///{test_data_path}/libvirt_config.xml",
        "machines_json": json.dumps(machines),
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "platform": "docker",
        "remove_ansible_logs": str(not docker_deployment.description.keep_ansible_logs),
        "elastic_version": "7.10.2",
        'elasticsearch_memory': 8,
        "elastic_latest_version": "no",
        "caldera_version": "latest",
        "packetbeat_vlan_id": "1"
    }
    mock_cmd = mocker.patch.object(packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", ""))
    mock_build = mocker.patch.object(packerpy.PackerExecutable, "build", return_value=(0, "success", ""))
    docker_deployment.create_services_images({"caldera":True,"elastic":True, "packetbeat":False})
    packer_script = tectonic_resources.files('tectonic') / 'services' / 'image_generation' / 'create_image.pkr.hcl'
    mock_cmd.assert_called_once_with("init", str(packer_script))
    mock_build.assert_called_once_with(str(packer_script), var=variables)

def test_get_services_network_data(docker_deployment):
    docker_deployment.description.deploy_caldera = True
    docker_deployment.description.deploy_elastic = True
    assert docker_deployment._get_services_network_data() == {
        "udelar-lab01-services" :{
            "cidr" : docker_deployment.description.services_network,
            "mode": "none",
        },
        "udelar-lab01-internet" :{
            "cidr" : docker_deployment.description.internet_network,
            "mode": "nat",
        },
    }
    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = False
    assert docker_deployment._get_services_network_data() == {
        "udelar-lab01-services" :{
            "cidr" : docker_deployment.description.services_network,
            "mode": "none",
        },
    }
    docker_deployment.description.deploy_elastic = True

def test_get_services_guest_data(docker_deployment):
    docker_deployment.description.deploy_caldera = True
    docker_deployment.description.deploy_elastic = True
    assert docker_deployment._get_services_guest_data() == {
        "udelar-lab01-elastic" : {
            "guest_name": "udelar-lab01-elastic",
            "base_name": "elastic",
            "hostname": "elastic",
            "base_os": "rocky8",
            "interfaces": {
                "udelar-lab01-elastic-1" : {
                    "name": "udelar-lab01-elastic-1",
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.130",
                    "mask": "25",
                },
                "udelar-lab01-elastic-2" : {
                    "name": "udelar-lab01-elastic-2",
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "internet",
                    "subnetwork_name": "udelar-lab01-internet",
                    "private_ip": "10.0.0.2",
                    "mask": "25",
                }
            },
            "memory": docker_deployment.description.services["elastic"]["memory"],
            "vcpu": docker_deployment.description.services["elastic"]["vcpu"],
            "disk": docker_deployment.description.services["elastic"]["disk"],
            "port": 5601,
        },
        "udelar-lab01-caldera" : {
            "guest_name": "udelar-lab01-caldera",
            "base_name": "caldera",
            "hostname": "caldera",
            "base_os": "rocky8",
            "interfaces": {
                "udelar-lab01-caldera-1" : {
                    "name": "udelar-lab01-caldera-1",
                    "guest_name": "udelar-lab01-caldera",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.132",
                    "mask": "25",
                },
                "udelar-lab01-caldera-2" : {
                    "name": "udelar-lab01-caldera-2",
                    "guest_name": "udelar-lab01-caldera",
                    "network_name": "internet",
                    "subnetwork_name": "udelar-lab01-internet",
                    "private_ip": "10.0.0.4",
                    "mask": "25",
                }
            },
            "memory": docker_deployment.description.services["caldera"]["memory"],
            "vcpu": docker_deployment.description.services["caldera"]["vcpu"],
            "disk": docker_deployment.description.services["caldera"]["disk"],
            "port": 8443,
        }
    }
    docker_deployment.description.monitor_type = "traffic"
    docker_deployment.description.deploy_caldera = False
    assert docker_deployment._get_services_guest_data() == {
        "udelar-lab01-elastic" : {
            "guest_name": "udelar-lab01-elastic",
            "base_name": "elastic",
            "hostname": "elastic",
            "base_os": "rocky8",
            "interfaces": {
                "udelar-lab01-elastic-1" : {
                    "name": "udelar-lab01-elastic-1",
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.130",
                    "mask": "25",
                },
                "udelar-lab01-elastic-2" : {
                    "name": "udelar-lab01-elastic-2",
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "internet",
                    "subnetwork_name": "udelar-lab01-internet",
                    "private_ip": "10.0.0.2",
                    "mask": "25",
                }
            },
            "memory": docker_deployment.description.services["elastic"]["memory"],
            "vcpu": docker_deployment.description.services["elastic"]["vcpu"],
            "disk": docker_deployment.description.services["elastic"]["disk"],
            "port": 5601,
        },
    }

def test_get_services_resources_to_target_apply(docker_deployment):
    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = True
    result = docker_deployment.get_services_resources_to_target_apply([1])
    expected = [
        'docker_container.machines["udelar-lab01-elastic"]',
        'docker_image.base_images["udelar-lab01-elastic"]',
        'docker_container.machines["udelar-lab01-caldera"]',
        'docker_image.base_images["udelar-lab01-caldera"]',
        'docker_network.subnets["udelar-lab01-services"]',
        'docker_network.subnets["udelar-lab01-internet"]',
    ]
    assert result == expected

    docker_deployment.description.deploy_elastic = False
    docker_deployment.description.deploy_caldera = True
    result = docker_deployment.get_services_resources_to_target_apply([1])
    expected = [
        'docker_container.machines["udelar-lab01-caldera"]',
        'docker_image.base_images["udelar-lab01-caldera"]',
        'docker_network.subnets["udelar-lab01-services"]',
        'docker_network.subnets["udelar-lab01-internet"]',
    ]
    assert result == expected

    docker_deployment.description.deploy_elastic = True
    docker_deployment.description.deploy_caldera = False
    result = docker_deployment.get_services_resources_to_target_apply([1])
    expected = [
        'docker_container.machines["udelar-lab01-elastic"]',
        'docker_image.base_images["udelar-lab01-elastic"]',
        'docker_network.subnets["udelar-lab01-services"]',
        'docker_network.subnets["udelar-lab01-internet"]',
    ]
    assert result == expected

def test_get_services_resources_to_target_destroy(docker_deployment):
    assert docker_deployment.get_services_resources_to_target_destroy([1]) == []

def test_get_service_info(mocker, docker_deployment):
    docker_deployment.description.deploy_caldera = False
    docker_deployment.description.deploy_elastic = True
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    playbook = str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'get_info.yml')
    inventory = {
        'elastic': {
            'hosts': {
                'udelar-lab01-elastic': {
                    'ansible_host': 'udelar-lab01-elastic', 
                    'ansible_user': 'rocky',
                    'ansible_ssh_common_args':'-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no',
                    'instance': None,
                    'copy': 1,
                    'networks': mocker.ANY,
                    'machine_name': 'udelar-lab01-elastic',
                    'parameter': {},
                    'random_seed': 'Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941',
                    'become_flags': '-i'
                }
            },
            'vars': {
                'ansible_become': True,
                'ansible_connection': 'community.docker.docker_api',
                'basename': 'elastic',
                'docker_host': 'unix:///var/run/docker.sock',
                'instances': 2,
                'platform': 'docker',
                'institution': 'udelar',
                'lab_name': 'lab01',
                'action': 'agents_status'
            }
        }
    }
    docker_deployment._get_service_info("elastic",playbook,{"action":"agents_status"})
    mock_ansible.assert_called_once_with(
        inventory=inventory,
        playbook=playbook,
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not docker_deployment.description.keep_ansible_logs }
    )
