
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
import packerpy
import json
import fabric
import invoke
import ansible_runner
from freezegun import freeze_time


import tectonic.ssh
from tectonic.aws import AWSClientException, Client as AWSClient
from tectonic.deployment import TerraformRunException
from tectonic.deployment_aws import *

import importlib.resources as tectonic_resources


def test_constructor(description):
    deploy_elastic = description.deploy_elastic
    description.deploy_elastic = False
    aws_deployment = AWSDeployment(
        description=description,
        gitlab_backend_url="https://gitlab.com",
        gitlab_backend_username="testuser",
        gitlab_backend_access_token="testtoken",
        packer_executable_path="/usr/bin/packer",
    )
    assert not hasattr(aws_deployment, "elastic_onprem_client")

    description.deploy_elastic = deploy_elastic


def test_create_cr_images_ok(mocker, aws_deployment, test_data_path):
    aws_deployment.description.monitor_type = "traffic"
    machines = {
        "attacker": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
            "disk": 8,
            "instance_type": "t2.medium"
        },
        "victim": {
            "base_os": "windows_srv_2022",
            "endpoint_monitoring": False,
            "disk": 8,
            "instance_type": "t2.micro"
        },
        "server": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
            "disk": 8,
            "instance_type": "t2.nano"
        },
    }
    variables = {
        "ansible_playbooks_path": aws_deployment.description.ansible_playbooks_path,
        "ansible_scp_extra_args": "'-O'" if tectonic.ssh.ssh_version() >= 9 else "",
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
        "platform": "aws",
        "remove_ansible_logs": str(not aws_deployment.description.keep_ansible_logs),
        "elastic_version": aws_deployment.description.elastic_stack_version
    }
    mock_cmd = mocker.patch.object(
        packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", "")
    )
    mock_build = mocker.patch.object(
        packerpy.PackerExecutable, "build", return_value=(0, "success", "")
    )
    mock_delete_sg = mocker.patch.object(
        aws_deployment.client, "delete_security_groups"
    )
    aws_deployment.create_cr_images()
    mock_cmd.assert_called_once_with("init", str(aws_deployment.cr_packer_path))
    mock_build.assert_called_once_with(str(aws_deployment.cr_packer_path), var=variables),
    mock_delete_sg.assert_called_once_with("Temporary group for Packer")

    aws_deployment.description.monitor_type = "endpoint"
    machines = {
        "attacker": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": False,
            "disk": 8,
            "instance_type": "t2.medium"
        },
        "victim": {
            "base_os": "windows_srv_2022",
            "endpoint_monitoring": True,
            "disk": 8,
            "instance_type": "t2.micro"
        },
        "server": {
            "base_os": "ubuntu22",
            "endpoint_monitoring": True,
            "disk": 8,
            "instance_type": "t2.nano"
        },
    }
    variables = {
        "ansible_playbooks_path": aws_deployment.description.ansible_playbooks_path,
        "ansible_scp_extra_args": "'-O'" if tectonic.ssh.ssh_version() >= 9 else "",
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
        "platform": "aws",
        "remove_ansible_logs": str(not aws_deployment.description.keep_ansible_logs),
        "elastic_version": aws_deployment.description.elastic_stack_version
    }
    mock_cmd = mocker.patch.object(
        packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", "")
    )
    mock_build = mocker.patch.object(
        packerpy.PackerExecutable, "build", return_value=(0, "success", "")
    )
    mock_delete_sg = mocker.patch.object(
        aws_deployment.client, "delete_security_groups"
    )
    aws_deployment.create_cr_images()
    mock_cmd.assert_called_once_with("init", str(aws_deployment.cr_packer_path))
    mock_build.assert_called_once_with(str(aws_deployment.cr_packer_path), var=variables),
    mock_delete_sg.assert_called_once_with("Temporary group for Packer")


def test_create_cr_images_error(mocker, aws_deployment):
    mocker.patch.object(
        packerpy.PackerExecutable, "execute_cmd", return_value=(1, b"", b"error")
    )
    with pytest.raises(TerraformRunException):
        aws_deployment.create_cr_images()

    mocker.patch.object(
        packerpy.PackerExecutable, "execute_cmd", return_value=(0, b"success", b"")
    )
    mocker.patch.object(
        packerpy.PackerExecutable, "build", return_value=(1, b"", b"error")
    )
    with pytest.raises(TerraformRunException):
        aws_deployment.create_cr_images()

    mocker.patch.object(aws_deployment, "can_delete_image", return_value=False)
    with pytest.raises(DeploymentAWSException):
        aws_deployment.create_cr_images()


def test_generate_backend_config(aws_deployment):
    answer = aws_deployment.generate_backend_config(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws')
    assert len(answer) == 1
    assert "path=terraform-states/udelar-lab01-gsi-lab-aws" in answer

def test_get_deploy_cr_vars(aws_deployment):
    variables = aws_deployment.get_deploy_cr_vars()
    # do not compare authorized_keys as its order is not guaranteed
    variables.pop('authorized_keys', None)
    assert variables == {
        "institution": "udelar",
        "lab_name": "lab01",
        "instance_number": 2,
        "aws_region": "us-east-1",
        "network_cidr_block": "10.0.0.0/16",
        "services_network_cidr_block": aws_deployment.description.services_network,
        "internet_network_cidr_block": aws_deployment.description.internet_network,
        "ssh_public_key_file": aws_deployment.description.ssh_public_key_file,
        "teacher_access": "host",
        "subnets_json": json.dumps(aws_deployment.description.subnets),
        "guest_data_json": json.dumps(aws_deployment.description.get_guest_data()),
        "aws_default_instance_type": "t2.micro",
        "default_os": "ubuntu22",
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "configure_dns": False,
        "services_internet_access": aws_deployment.description.deploy_elastic,
        "monitor_type": aws_deployment.description.monitor_type,
    }


def test_delete_cr_images(mocker, aws_deployment):
    mock = mocker.patch.object(aws_deployment.client, "delete_image")
    aws_deployment.delete_cr_images()
    assert mock.call_count == 3
    mock.assert_has_calls(
        [
            mocker.call("udelar-lab01-attacker"),
            mocker.call("udelar-lab01-victim"),
            mocker.call("udelar-lab01-server"),
        ]
    )

    mocker.patch.object(aws_deployment, "can_delete_image", return_value=False)
    mock.reset_mock()
    with pytest.raises(DeploymentAWSException):
        aws_deployment.delete_cr_images()
    mock.assert_not_called()

def test_get_instance_status(
    aws_deployment, ec2_client, aws_instance_name, unexpected_instance_name
):
    aws_deployment.start_instance(aws_instance_name)
    instance = ec2_client.describe_instances(
        Filters=[{"Name": "tag:Name", "Values": [aws_instance_name]}]
    )["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"

    state = aws_deployment.get_instance_status(aws_instance_name)
    assert state == "RUNNING"
    state = aws_deployment.get_instance_status(unexpected_instance_name)
    assert state == "NOT FOUND"


def test_get_cyberrange_data(mocker, aws_deployment):
    aws_deployment.description.deploy_elastic = False
    aws_deployment.description.deploy_caldera = False
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")
    table = aws_deployment.get_cyberrange_data()
    expected = """┌───────────────────┬───────────┐
│        Name       │   Value   │
├───────────────────┼───────────┤
│ Student Access IP │ 127.0.0.1 │
│ Teacher Access IP │ 127.0.0.1 │
└───────────────────┴───────────┘"""
    assert expected == table.get_string()

    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = False
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")
    mocker.patch.object(AWSClient,"get_machine_private_ip",return_value="127.0.0.1")
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"elastic":"password"})
    table = aws_deployment.get_cyberrange_data()
    expected = """┌──────────────────────────────────┬────────────────────────┐
│               Name               │         Value          │
├──────────────────────────────────┼────────────────────────┤
│        Student Access IP         │       127.0.0.1        │
│        Teacher Access IP         │       127.0.0.1        │
│                                  │                        │
│            Kibana URL            │ https://127.0.0.1:5601 │
│ Kibana user (username: password) │   elastic: password    │
└──────────────────────────────────┴────────────────────────┘"""
    assert expected == table.get_string()

    aws_deployment.description.deploy_caldera = True
    aws_deployment.description.deploy_elastic = False
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")
    mocker.patch.object(AWSClient,"get_machine_private_ip",return_value="127.0.0.1")
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"red":"password", "blue":"password"})
    table = aws_deployment.get_cyberrange_data()
    expected = """┌───────────────────────────────────┬────────────────────────┐
│                Name               │         Value          │
├───────────────────────────────────┼────────────────────────┤
│         Student Access IP         │       127.0.0.1        │
│         Teacher Access IP         │       127.0.0.1        │
│                                   │                        │
│            Caldera URL            │ https://127.0.0.1:8443 │
│ Caldera user (username: password) │     red: password      │
│ Caldera user (username: password) │     blue: password     │
└───────────────────────────────────┴────────────────────────┘"""
    assert expected == table.get_string()
    aws_deployment.description.deploy_caldera = True
    aws_deployment.description.deploy_elastic = True


def test_get_cyberrange_data_error(mocker, aws_deployment):
    aws_deployment.description.deploy_caldera = False
    aws_deployment.description.deploy_elastic = True
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")
    mocker.patch.object(AWSClient,"get_machine_private_ip",return_value="127.0.0.1")
    mocker.patch.object(AWSClient, "get_instance_status", return_value="STOPPED")
    result = aws_deployment.get_cyberrange_data()
    assert result  == "Unable to get Elastic info right now. Please make sure de Elastic machine is running."

    aws_deployment.description.deploy_caldera = True
    aws_deployment.description.deploy_elastic = False
    result = aws_deployment.get_cyberrange_data()
    mocker.patch.object(AWSClient, "get_instance_status", return_value="STOPPED")
    assert result  == "Unable to get Caldera info right now. Please make sure de Caldera machine is running."
    

def test_connect_to_instance(monkeypatch, aws_deployment):
    def fabric_shell(connection, **kwargs):
        """Mocks fabric.Connection.shell()."""
        assert connection.original_host == "10.0.0.28"
        assert connection.user == "ubuntu"
        assert isinstance(connection.gateway, fabric.Connection)
        assert (
            connection.gateway.original_host == aws_deployment.get_teacher_access_ip()
        )
        assert connection.gateway.user == "ubuntu"

        return invoke.runners.Result()

    monkeypatch.setattr(fabric.Connection, "shell", fabric_shell)

    aws_deployment.connect_to_instance("udelar-lab01-1-attacker", None)


def test_connect_to_instance_teacher_access(monkeypatch, aws_deployment):
    def fabric_shell(connection, **kwargs):
        """Mocks fabric.Connection.shell()."""
        assert connection.original_host == aws_deployment.get_teacher_access_ip()
        assert connection.user == "ubuntu"
        assert connection.gateway is None

        return invoke.runners.Result()

    monkeypatch.setattr(fabric.Connection, "shell", fabric_shell)

    aws_deployment.connect_to_instance("udelar-lab01-teacher_access", None)


def test_connect_to_instance_endpoint(monkeypatch, aws_deployment):
    def fabric_shell(connection, **kwargs):
        """Mocks fabric.Connection.shell()."""
        assert connection.original_host == aws_deployment.client.get_instance_property(
            "udelar-lab01-1-attacker", "InstanceId"
        )
        assert connection.user == "ubuntu"
        assert connection.gateway == aws_deployment.EIC_ENDPOINT_SSH_PROXY

        return invoke.runners.Result()

    monkeypatch.setattr(fabric.Connection, "shell", fabric_shell)

    aws_deployment.description.teacher_access = "endpoint"
    aws_deployment.connect_to_instance("udelar-lab01-1-attacker", None)
    aws_deployment.description.teacher_access = "host"


def test_connect_to_instance_error(monkeypatch, aws_deployment):
    with pytest.raises(DeploymentAWSException):
        aws_deployment.connect_to_instance("not-found", None)


def test_get_ssh_proxy_command(aws_deployment):
    ssh_proxy = aws_deployment.get_ssh_proxy_command()
    teacher_ip = aws_deployment.get_teacher_access_ip()
    assert (
        ssh_proxy
        == f"ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -W %h:%p ubuntu@{teacher_ip}"
    )

    aws_deployment.description.teacher_access = "endpoint"
    ssh_proxy = aws_deployment.get_ssh_proxy_command()
    assert ssh_proxy == aws_deployment.EIC_ENDPOINT_SSH_PROXY
    aws_deployment.description.teacher_access = "host"


def test_get_ssh_hostname(aws_deployment):
    ssh_hostname = aws_deployment.get_ssh_hostname("udelar-lab01-1-attacker")
    assert ssh_hostname == "10.0.0.28"

    aws_deployment.description.teacher_access = "endpoint"
    ssh_hostname = aws_deployment.get_ssh_hostname("udelar-lab01-1-attacker")
    assert ssh_hostname == aws_deployment.client.get_instance_property(
        "udelar-lab01-1-attacker", "InstanceId"
    )
    aws_deployment.description.teacher_access = "host"


def test_start_instance(aws_deployment, aws_instance_name, unexpected_instance_name):
    aws_client = aws_deployment.client

    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "RUNNING"
    # Test starting a RUNNING instance
    aws_deployment.start_instance(aws_instance_name)
    state = aws_deployment.get_instance_status(aws_instance_name)
    assert state == "RUNNING"

    # Stop the domain
    aws_deployment.stop_instance(aws_instance_name)
    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "STOPPED"

    # Test starting a SHUTOFF instance
    aws_deployment.start_instance(aws_instance_name)
    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "RUNNING"

    # Test a non-existent domain
    with pytest.raises(AWSClientException) as exception:
        aws_deployment.start_instance(unexpected_instance_name)
    assert f"Instance {unexpected_instance_name} not found" in str(exception.value)


def test_stop_instance(aws_deployment, aws_instance_name, unexpected_instance_name):
    aws_client = aws_deployment.client

    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "RUNNING"
    aws_deployment.stop_instance(aws_instance_name)
    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "STOPPED"
    aws_deployment.stop_instance(aws_instance_name)
    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "STOPPED"

    # Test a non-existent instance
    with pytest.raises(AWSClientException) as exception:
        aws_deployment.stop_instance(unexpected_instance_name)
    assert f"Instance {unexpected_instance_name} not found" in str(exception.value)


def test_reboot_instance(aws_deployment, aws_instance_name, unexpected_instance_name):
    aws_client = aws_deployment.client

    # Restart a RUNNING domain
    aws_deployment.start_instance(aws_instance_name)
    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "RUNNING"
    aws_deployment.reboot_instance(aws_instance_name)
    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "RUNNING"

    # Restart a SHUTOFF domain
    aws_deployment.stop_instance(aws_instance_name)
    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "STOPPED"
    aws_deployment.reboot_instance(aws_instance_name)
    state = aws_client.get_instance_status(aws_instance_name)
    assert state == "RUNNING"

    # Test a non-existent domain
    with pytest.raises(AWSClientException) as exception:
        aws_deployment.reboot_instance(unexpected_instance_name)
    assert f"Instance {unexpected_instance_name} not found" in str(exception.value)


def test_get_cr_resources_to_target_apply(aws_deployment):
    expected_resources = []
    for i in [1, 2]:
        for guest in ["attacker", "victim-1", "victim-2", "server"]:
            expected_resources += [
                f'aws_instance.machines["udelar-lab01-{i}-{guest}"]',
                f'aws_network_interface.interfaces["udelar-lab01-{i}-{guest}-1"]',
            ]

        # Add the second server interface
        expected_resources += [
            f'aws_network_interface.interfaces["udelar-lab01-{i}-server-2"]'
        ]
        for subnet in ["internal", "dmz"]:
            expected_resources += [
                f'aws_subnet.instance_subnets["udelar-lab01-{i}-{subnet}"]',
                f'aws_security_group.subnet_sg["udelar-lab01-{i}-{subnet}"]',
            ]

    expected_resources += [
        'aws_instance.machines["udelar-lab01-student_access"]',
        'aws_instance.machines["udelar-lab01-teacher_access"]',
        "aws_security_group.bastion_host_sg",
        "aws_instance.teacher_access_host[0]",
        "aws_security_group.teacher_access_sg",
        "aws_instance.student_access[0]",
        "aws_key_pair.admin_pubkey",
        "aws_security_group.entry_point_sg",
        "module.vpc",
    ]

    expected_dns = [
        'aws_route53_zone.zones["dmz"]',
        "aws_route53_zone.reverse[0]",
        'aws_route53_zone.zones["internal"]',
    ]
    for i in [1, 2]:
        for guest in ["attacker", "victim-1", "victim-2", "server"]:
            expected_dns += [
                f'aws_route53_record.records["{guest}-{i}-internal"]',
                f'aws_route53_record.records_reverse["{guest}-{i}-internal"]',
            ]
        expected_dns += [
            f'aws_route53_record.records["server-{i}-dmz"]',
            f'aws_route53_record.records_reverse["server-{i}-dmz"]',
        ]

    resources = aws_deployment.get_cr_resources_to_target_apply(None)
    assert set(resources) == set(expected_resources)

    # DNS enabled
    aws_deployment.description.configure_dns = True
    resources = aws_deployment.get_cr_resources_to_target_apply(None)
    assert set(resources) == set(expected_resources + expected_dns)
    aws_deployment.description.configure_dns = False

    # EIC teacher access
    aws_deployment.description.teacher_access = "endpoint"
    resources = aws_deployment.get_cr_resources_to_target_apply(None)
    assert set(resources) == set(expected_resources).difference(
        [
            'aws_instance.machines["udelar-lab01-teacher_access"]',
            "aws_instance.teacher_access_host[0]",
        ]
    ).union(["aws_ec2_instance_connect_endpoint.teacher_access[0]"])
    aws_deployment.description.teacher_access = "host"

    # Internet access
    aws_deployment.description.guest_settings["server"]["internet_access"] = True
    resources = aws_deployment.get_cr_resources_to_target_apply(None)
    assert set(resources) == set(expected_resources).union(
        [
            "aws_route_table.scenario_internet_access[0]",
            "aws_security_group.internet_access_sg[0]",
            'aws_route_table_association.scenario_internet_access["udelar-lab01-1-internal"]',
            'aws_route_table_association.scenario_internet_access["udelar-lab01-1-dmz"]',
            'aws_route_table_association.scenario_internet_access["udelar-lab01-2-internal"]',
            'aws_route_table_association.scenario_internet_access["udelar-lab01-2-dmz"]',
        ]
    )
    del aws_deployment.description.guest_settings["server"]["internet_access"]


def test_get_cr_resources_to_target_destroy(aws_deployment):
    expected_resources = []
    for guest in ["attacker", "victim-1", "victim-2", "server"]:
        expected_resources += [f'aws_instance.machines["udelar-lab01-1-{guest}"]']

    expected_dns = [
        'aws_route53_zone.zones["dmz"]',
        "aws_route53_zone.reverse[0]",
        'aws_route53_zone.zones["internal"]',
    ]
    for guest in ["attacker", "victim-1", "victim-2", "server"]:
        expected_dns += [
            f'aws_route53_record.records["{guest}-1-internal"]',
            f'aws_route53_record.records_reverse["{guest}-1-internal"]',
        ]
    expected_dns += [
        'aws_route53_record.records["server-1-dmz"]',
        'aws_route53_record.records_reverse["server-1-dmz"]',
    ]

    resources = aws_deployment.get_cr_resources_to_target_destroy([1])
    assert set(resources) == set(expected_resources)

    # DNS enabled
    aws_deployment.description.configure_dns = True
    resources = aws_deployment.get_cr_resources_to_target_destroy([1])
    assert set(resources) == set(expected_resources + expected_dns)
    aws_deployment.description.configure_dns = False


def test_get_resources_to_recreate(aws_deployment):
    resources = aws_deployment.get_resources_to_recreate([1], ("victim",), [2])
    assert set(resources) == set(['aws_instance.machines["udelar-lab01-1-victim-2"]'])

    resources = aws_deployment.get_resources_to_recreate(None, ("student_access", "teacher_access"), None)
    assert set(resources) == set(
        ["aws_instance.student_access[0]", "aws_instance.teacher_access_host[0]"]
    )
  
    resources = aws_deployment.get_resources_to_recreate(None, None, None)
    compare = []
    for instance in [1, 2]:
        for guest in ["attacker", "server", "victim"]:
            if guest == "victim":
                for copy in [1, 2]:
                    compare.append(
                        f'aws_instance.machines["udelar-lab01-{instance}-{guest}-{copy}"]'
                    )
            else:
                compare.append(
                    f'aws_instance.machines["udelar-lab01-{instance}-{guest}"]'
                )
    compare.append("aws_instance.student_access[0]")
    compare.append("aws_instance.teacher_access_host[0]")
    assert set(resources) == set(compare)

@pytest.mark.skip(
    reason="https://stackoverflow.com/questions/53716949/how-to-create-ami-with-specific-image-id-using-moto"
)
def test_can_delete_image(aws_deployment):
    assert not aws_deployment.can_delete_image("udelar-lab01-attacker")
    assert aws_deployment.can_delete_image("notfound")

def test_list_instances(mocker, aws_deployment):
    mocker.patch.object(AWSClient, "get_instance_status", return_value="RUNNING")
    result = aws_deployment.list_instances(None, None, None)
    expected = """┌─────────────────────────────┬─────────┐
│             Name            │  Status │
├─────────────────────────────┼─────────┤
│   udelar-lab01-1-attacker   │ RUNNING │
│   udelar-lab01-1-victim-1   │ RUNNING │
│   udelar-lab01-1-victim-2   │ RUNNING │
│    udelar-lab01-1-server    │ RUNNING │
│   udelar-lab01-2-attacker   │ RUNNING │
│   udelar-lab01-2-victim-1   │ RUNNING │
│   udelar-lab01-2-victim-2   │ RUNNING │
│    udelar-lab01-2-server    │ RUNNING │
│ udelar-lab01-student_access │ RUNNING │
│ udelar-lab01-teacher_access │ RUNNING │
└─────────────────────────────┴─────────┘""" 
    assert result.get_string() == expected

def test_shutdown(mocker, monkeypatch, aws_deployment, ec2_client, aws_secrets):
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets

    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    aws_deployment.shutdown([1],["attacker"], None, False)
    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-1-attacker"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "stopped"

    #Shutdown services
    # aws_deployment.shutdown([1],["attacker"], None, True)
    # #instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-packetbeat"]}])["Reservations"][0]["Instances"][0]
    # #assert instance["State"]["Name"] == "stopped"
    # instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-elastic"]}])["Reservations"][0]["Instances"][0]
    # print(ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-elastic"]}]))
    # assert instance["State"]["Name"] == "stopped"
    # instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-caldera"]}])["Reservations"][0]["Instances"][0]
    # assert instance["State"]["Name"] == "stopped"

def test_start(mocker, monkeypatch, aws_deployment, ec2_client, aws_secrets):
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets

    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    aws_deployment.start([1],["attacker"],None, False)

    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-1-attacker"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"

    #Start elastic
    aws_deployment.start([1],["attacker"],None, True)
    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-packetbeat"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"
    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-elastic"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"
    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-caldera"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"

def test_reboot(mocker, monkeypatch, aws_deployment, ec2_client, aws_secrets):
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets

    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    aws_deployment.reboot([1],["attacker"],None, False)

    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-1-attacker"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"

    #Reboot services
    aws_deployment.reboot([1],["attacker"],None, True)
    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-packetbeat"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"
    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-elastic"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"
    instance = ec2_client.describe_instances(Filters=[{"Name": "tag:Name", "Values": ["udelar-lab01-caldera"]}])["Reservations"][0]["Instances"][0]
    assert instance["State"]["Name"] == "running"

def test_create_services_images_ok(mocker, aws_deployment, base_tectonic_path, test_data_path):
    aws_deployment.description.monitor_type = "traffic"
    machines = {
        "caldera": {
            "base_os": "rocky8",
            "ansible_playbook": str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'base_config.yml'),
            "disk": 20,
            "instance_type": "t2.medium"
        },
        "elastic": {
            "base_os": "rocky8",
            "ansible_playbook": str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'base_config.yml'),
            "disk": 110,
            "instance_type": "t2.2xlarge"
        },
        "packetbeat": {
            "base_os": "ubuntu22",
            "ansible_playbook": str(tectonic_resources.files('tectonic') / 'services' / 'packetbeat' / 'base_config.yml'),
            "disk": 10,
            "instance_type": "t2.micro",
        }
    }
    variables = {
        "ansible_scp_extra_args": "'-O'" if tectonic.ssh.ssh_version() >= 9 else "",
        "ansible_ssh_common_args": "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no",
        "aws_region": "us-east-1",
        "proxy": "http://proxy.fing.edu.uy:3128",
        "libvirt_storage_pool": "pool-dir",
        "libvirt_uri": f"test:///{test_data_path}/libvirt_config.xml",
        "machines_json": json.dumps(machines),
        "os_data_json": json.dumps(tectonic.constants.OS_DATA),
        "platform": "aws",
        "remove_ansible_logs": str(not aws_deployment.description.keep_ansible_logs),
        "elastic_version": "7.10.2",
        'elasticsearch_memory': None,
        "elastic_latest_version": "no",
        "caldera_version": "latest",
        "packetbeat_vlan_id": "1"
    }
    mock_cmd = mocker.patch.object(
        packerpy.PackerExecutable, "execute_cmd", return_value=(0, "success", "")
    )
    mock_build = mocker.patch.object(
        packerpy.PackerExecutable, "build", return_value=(0, "success", "")
    )
    mock_delete_sg = mocker.patch.object(
        aws_deployment.client, "delete_security_groups"
    )
    aws_deployment.create_services_images({"caldera":True,"elastic":True,"packetbeat":True})
    mock_cmd.assert_called_once_with("init", str(tectonic_resources.files('tectonic') / 'services' / 'image_generation' / 'create_image.pkr.hcl'))
    mock_build.assert_called_once_with(str(tectonic_resources.files('tectonic') / 'services' / 'image_generation' / 'create_image.pkr.hcl'),
                                       var=variables),
    mock_delete_sg.assert_called_once_with("Temporary group for Packer")


def test_get_services_instances_name(aws_deployment):
    aws_deployment.description.monitor_type = "traffic"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment._get_services_instances_name()
    expected = ['aws_instance.machines["udelar-lab01-elastic"]', 'aws_instance.machines["udelar-lab01-packetbeat"]', 'aws_instance.machines["udelar-lab01-caldera"]' ]
    assert result == expected

    aws_deployment.description.monitor_type = "endpoint"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment._get_services_instances_name()
    expected = ['aws_instance.machines["udelar-lab01-elastic"]', 'aws_instance.machines["udelar-lab01-caldera"]' ]
    assert result == expected

    aws_deployment.description.deploy_elastic = False
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment._get_services_instances_name()
    expected = ['aws_instance.machines["udelar-lab01-caldera"]' ]
    assert result == expected

def test_get_services_dns_resources_name(aws_deployment):
    aws_deployment.description.monitor_type = "endpoint"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment._get_services_dns_resources_name()
    expected = ['aws_route53_zone.zones["services"]', 'aws_route53_record.records["elastic-services"]','aws_route53_record.records_reverse["elastic-services"]','aws_route53_record.records["caldera-services"]','aws_route53_record.records_reverse["caldera-services"]']
    assert result == expected

def test_get_services_security_group_resources_name(aws_deployment):
    aws_deployment.description.monitor_type = "endpoint"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment._get_services_security_group_resources_name()
    expected = ['aws_security_group.subnet_sg["udelar-lab01-services"]']
    assert result == expected

def test_get_services_interface_resources_name(aws_deployment):
    aws_deployment.description.monitor_type = "endpoint"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment._get_services_interface_resources_name()
    expected = ['aws_network_interface.interfaces["udelar-lab01-elastic-1"]', 'aws_network_interface.interfaces["udelar-lab01-caldera-1"]']
    assert result == expected

def test_get_sessions_resources_name(aws_deployment):
    aws_deployment.description.monitor_type = "endpoint"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment._get_sessions_resources_name([1])
    expected = ['aws_ec2_traffic_mirror_session.session["udelar-lab01-1-victim-1-1"]', 'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-victim-2-1"]', 'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-server-1"]', 'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-server-2"]']
    assert result == expected

def test_get_services_resources_to_target_destroy(aws_deployment):
    aws_deployment.description.monitor_type = "traffic"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment.get_services_resources_to_target_destroy([1])
    expected = ['aws_ec2_traffic_mirror_session.session["udelar-lab01-1-victim-1-1"]', 'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-victim-2-1"]', 'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-server-1"]', 'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-server-2"]']
    assert result == expected

def test_get_services_resources_to_target_apply(aws_deployment):
    aws_deployment.description.configure_dns = True
    aws_deployment.description.monitor_type = "traffic"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True
    result = aws_deployment.get_services_resources_to_target_apply([1])
    expected = [
        "aws_security_group.services_internet_access_sg[0]",
        "aws_security_group.caldera_scenario_sg",
        "aws_security_group.elastic_endpoint_scenario_sg",
        "aws_security_group.elastic_traffic_scenario_sg",
        'aws_instance.machines["udelar-lab01-elastic"]',
        'aws_instance.machines["udelar-lab01-packetbeat"]',
        'aws_instance.machines["udelar-lab01-caldera"]',
        'aws_security_group.subnet_sg["udelar-lab01-services"]',
        'aws_network_interface.interfaces["udelar-lab01-elastic-1"]',
        'aws_network_interface.interfaces["udelar-lab01-packetbeat-1"]',
        'aws_network_interface.interfaces["udelar-lab01-caldera-1"]',
        'aws_route53_zone.zones["services"]',
        'aws_route53_record.records["elastic-services"]',
        'aws_route53_record.records_reverse["elastic-services"]',
        'aws_route53_record.records["packetbeat-services"]',
        'aws_route53_record.records_reverse["packetbeat-services"]',
        'aws_route53_record.records["caldera-services"]',
        'aws_route53_record.records_reverse["caldera-services"]',
        "aws_ec2_traffic_mirror_target.packetbeat[0]",
        "aws_ec2_traffic_mirror_filter.filter[0]",
        "aws_ec2_traffic_mirror_filter_rule.filter_all_inbound[0]",
        "aws_ec2_traffic_mirror_filter_rule.filter_all_outbound[0]",
        'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-victim-1-1"]',
        'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-victim-2-1"]',
        'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-server-1"]',
        'aws_ec2_traffic_mirror_session.session["udelar-lab01-1-server-2"]'
    ]
    assert result == expected

def test_get_services_network_data(aws_deployment):
    assert aws_deployment._get_services_network_data() == {
        "udelar-lab01-services" : {
                "cidr" : "10.0.0.128/25",
                "mode": "none"
            },
    }

def test_get_services_guest_data(aws_deployment):
    aws_deployment.description.monitor_type = "endpoint"
    aws_deployment.description.deploy_caldera = True
    aws_deployment.description.deploy_elastic = True
    assert aws_deployment._get_services_guest_data() == {
        "udelar-lab01-elastic" : {
            "guest_name": "udelar-lab01-elastic",
            "base_name": "elastic",
            "hostname": "elastic",
            "base_os": "rocky8",
            'internet_access': True,
            "interfaces": {
                "udelar-lab01-elastic-1" : {
                    "name": "udelar-lab01-elastic-1",
                    "index": 0,
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.132",
                    "mask": "25",
                },
            },
            "disk": aws_deployment.description.services["elastic"]["disk"],
            "instance_type": "t2.2xlarge",
        },
        "udelar-lab01-caldera" : {
            "guest_name": "udelar-lab01-caldera",
            "base_name": "caldera",
            "hostname": "caldera",
            "base_os": "rocky8",
            'internet_access': False,
            "interfaces": {
                "udelar-lab01-caldera-1" : {
                    "name": "udelar-lab01-caldera-1",
                    "index": 0,
                    "guest_name": "udelar-lab01-caldera",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.134",
                    "mask": "25",
                }
            },
            "disk": aws_deployment.description.services["caldera"]["disk"],
            "instance_type": "t2.medium",
        }
    }
    aws_deployment.description.monitor_type = "traffic"
    aws_deployment.description.deploy_caldera = False
    assert aws_deployment._get_services_guest_data() == {
        "udelar-lab01-elastic" : {
            "guest_name": "udelar-lab01-elastic",
            "base_name": "elastic",
            "hostname": "elastic",
            "base_os": "rocky8",
            'internet_access': True,
            "interfaces": {
                "udelar-lab01-elastic-1" : {
                    "name": "udelar-lab01-elastic-1",
                    "index": 0,
                    "guest_name": "udelar-lab01-elastic",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.132",
                    "mask": "25",
                },
            },
            "disk": aws_deployment.description.services["elastic"]["disk"],
            "instance_type": "t2.2xlarge",
        },
        "udelar-lab01-packetbeat" : {
            "guest_name": "udelar-lab01-packetbeat",
            "base_name": "packetbeat",
            "hostname": "packetbeat",
            "base_os": "ubuntu22",
            'internet_access': False,
            "interfaces": {
                "udelar-lab01-packetbeat-1" : {
                    "name": "udelar-lab01-packetbeat-1",
                    "index": 0,
                    "guest_name": "udelar-lab01-packetbeat",
                    "network_name": "services",
                    "subnetwork_name": "udelar-lab01-services",
                    "private_ip": "10.0.0.133",
                    "mask": "25",
                },
            },
            "disk": 10,
            "instance_type": "t2.micro",
        }
    }

def test_get_subnet_resources_name(aws_deployment):
    result = aws_deployment._get_subnet_resources_name([1])
    expected = ['aws_subnet.instance_subnets["udelar-lab01-1-internal"]', 'aws_subnet.instance_subnets["udelar-lab01-1-dmz"]' ]
    assert result == expected   

def test_get_security_group_resources_name(aws_deployment):
    result = aws_deployment._get_security_group_resources_name([1])
    expected = ['aws_security_group.subnet_sg["udelar-lab01-1-internal"]', 'aws_security_group.subnet_sg["udelar-lab01-1-dmz"]' ]
    assert result == expected   

def test_get_interface_resources_name(aws_deployment):
    result = aws_deployment._get_interface_resources_name([1])
    expected = ['aws_network_interface.interfaces["udelar-lab01-1-attacker-1"]', 'aws_network_interface.interfaces["udelar-lab01-1-victim-1-1"]', 'aws_network_interface.interfaces["udelar-lab01-1-victim-2-1"]', 'aws_network_interface.interfaces["udelar-lab01-1-server-1"]', 'aws_network_interface.interfaces["udelar-lab01-1-server-2"]']
    assert result == expected  

def test_get_dns_resources_name(aws_deployment):
    result = aws_deployment._get_dns_resources_name([1])
    expected = [
        'aws_route53_zone.reverse[0]',
        'aws_route53_zone.zones["internal"]',
        'aws_route53_zone.zones["dmz"]',
        'aws_route53_record.records["attacker-1-internal"]',
        'aws_route53_record.records_reverse["attacker-1-internal"]',
        'aws_route53_record.records["victim-1-1-internal"]',
        'aws_route53_record.records_reverse["victim-1-1-internal"]',
        'aws_route53_record.records["victim-2-1-internal"]',
        'aws_route53_record.records_reverse["victim-2-1-internal"]',
        'aws_route53_record.records["server-1-internal"]',
        'aws_route53_record.records_reverse["server-1-internal"]',
        'aws_route53_record.records["server-1-dmz"]',
        'aws_route53_record.records_reverse["server-1-dmz"]'
    ]
    assert result == expected  

def test_get_route_table_resources_name(aws_deployment):
    result = aws_deployment._get_route_table_resources_name([1])
    expected = [
        'aws_route_table_association.scenario_internet_access["udelar-lab01-1-internal"]',
        'aws_route_table_association.scenario_internet_access["udelar-lab01-1-dmz"]'
    ]
    assert result == expected 

def test_get_machines_resources_name(aws_deployment):
    result = aws_deployment._get_machines_resources_name([1])
    expected = [
        'aws_instance.machines["udelar-lab01-1-attacker"]',
        'aws_instance.machines["udelar-lab01-1-victim-1"]',
        'aws_instance.machines["udelar-lab01-1-victim-2"]',
        'aws_instance.machines["udelar-lab01-1-server"]',
    ]
    assert result == expected 

def test_get_deploy_services_vars(aws_deployment):
    aws_deployment.description.deploy_caldera = True
    aws_deployment.description.deploy_elastic = True
    result = aws_deployment.get_deploy_services_vars()
    expected = {
        "institution": aws_deployment.description.institution,
        "lab_name": aws_deployment.description.lab_name,
        "aws_region": aws_deployment.description.aws_region,
        "network_cidr_block": aws_deployment.description.network_cidr_block,
        "authorized_keys": aws_deployment.description.authorized_keys,
        "subnets_json": json.dumps(aws_deployment._get_services_network_data()),
        "guest_data_json": json.dumps(aws_deployment._get_services_guest_data()),
        "os_data_json": json.dumps(OS_DATA),
        "configure_dns": aws_deployment.description.configure_dns,
        "monitor_type": aws_deployment.description.monitor_type,
        "packetbeat_vlan_id": aws_deployment.description.packetbeat_vlan_id,
        "machines_to_monitor": aws_deployment.description.get_machines_to_monitor(),
        "monitor": aws_deployment.description.deploy_elastic,
    }
    assert expected == result

def test_delete_services_images(mocker, aws_deployment):
    mock = mocker.patch.object(aws_deployment.client, "delete_image")
    aws_deployment.delete_services_images({"elastic":True,"packetbeat":True,"caldera":True})
    assert mock.call_count == 3
    mock.assert_has_calls(
        [
            mocker.call("elastic"),
            mocker.call("packetbeat"),
            mocker.call("caldera"),
        ]
    )

    mocker.patch.object(aws_deployment, "can_delete_image", return_value=False)
    mock.reset_mock()
    with pytest.raises(DeploymentAWSException):
        aws_deployment.delete_services_images({"elastic":True,"packetbeat":True,"caldera":True})
    mock.assert_not_called()

def test_student_access(mocker, aws_deployment, base_tectonic_path):
    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)

    ansible_aws = tectonic.ansible.Ansible(aws_deployment)
    entry_points = [ base_name for base_name, guest in aws_deployment.description.guest_settings.items()
                     if guest.get("entry_point") ]
    machine_list = aws_deployment.description.parse_machines(guests=entry_points)
    machine_list.append("udelar-lab01-student_access")
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
    inventory = ansible_aws.build_inventory(
        machine_list,
        extra_vars={
            "users": users,
            "prefix": "student",
            "ssh_password_login":True
        }
    )

    aws_deployment.student_access(None)
    mock.assert_called_once_with(
        inventory=inventory,
        playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
        quiet=True,
        verbosity=0,
        event_handler=mocker.ANY,
        extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
    )

@freeze_time("2022-01-01")
def test_get_services_status(mocker, capsys, aws_deployment):
    aws_deployment.description.deploy_elastic = False
    aws_deployment.description.deploy_caldera = False
    result = aws_deployment.get_services_status()
    assert "No services were deployed." == result

    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = False
    aws_deployment.description.monitor_type = "endpoint"
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="STOPPED")
    result = aws_deployment.get_services_status()
    expected = """┌──────────────────────┬─────────┐
│         Name         │  Status │
├──────────────────────┼─────────┤
│ udelar-lab01-elastic │ STOPPED │
└──────────────────────┴─────────┘"""
    assert expected == result.get_string()
    assert "Unable to connect to Elastic. Check if machine is running.\n" in capsys.readouterr().out

    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = False
    aws_deployment.description.monitor_type = "traffic"
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="STOPPED")
    result = aws_deployment.get_services_status()
    expected = """┌─────────────────────────┬─────────┐
│           Name          │  Status │
├─────────────────────────┼─────────┤
│   udelar-lab01-elastic  │ STOPPED │
│ udelar-lab01-packetbeat │ STOPPED │
└─────────────────────────┴─────────┘"""
    assert expected == result.get_string()

    aws_deployment.description.deploy_elastic = False
    aws_deployment.description.deploy_caldera = True
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="STOPPED")
    result = aws_deployment.get_services_status()
    expected = """┌──────────────────────┬─────────┐
│         Name         │  Status │
├──────────────────────┼─────────┤
│ udelar-lab01-caldera │ STOPPED │
└──────────────────────┴─────────┘"""
    assert expected == result.get_string()
    assert "Unable to connect to Caldera. Check if machine is running.\n" in capsys.readouterr().out

    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = False
    aws_deployment.description.monitor_type = "traffic"
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    result = aws_deployment.get_services_status()
    expected = """┌─────────────────────────┬─────────┐
│           Name          │  Status │
├─────────────────────────┼─────────┤
│   udelar-lab01-elastic  │ RUNNING │
│ udelar-lab01-packetbeat │ RUNNING │
└─────────────────────────┴─────────┘"""
    assert expected == result.get_string()

    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = False
    aws_deployment.description.monitor_type = "endpoint"
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"elastic":"password"})
    mocker.patch.object(AWSDeployment,"_get_service_info",return_value=[{"agents_status": {"online": 2,"error": 0,"inactive": 0,"offline": 0,"updating": 0,"unenrolled": 0,"degraded": 0,"enrolling": 0,"unenrolling": 0 }}])
    result = aws_deployment.get_services_status()
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
    assert expected == result.get_string()

    aws_deployment.description.deploy_elastic = False
    aws_deployment.description.deploy_caldera = True
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"red":"passwordred","blue":"passwordblue", "red_api":"apikeyred", "blue_api": "apikeyblue"})
    mocker.patch.object(AWSDeployment,"_get_service_info",return_value=[{"agents_status":[{"sleep_min":3,"sleep_max":3,"watchdog":1,"last_seen":"2024-05-05T14:43:17Z"},{"sleep_min":3,"sleep_max":3,"watchdog":1,"last_seen":"2024-05-04T14:43:17Z"}]}])
    result = aws_deployment.get_services_status()
    expected = """┌─────────────────────────────┬─────────┐
│             Name            │  Status │
├─────────────────────────────┼─────────┤
│     udelar-lab01-caldera    │ RUNNING │
│     caldera-agents-alive    │    0    │
│     caldera-agents-dead     │    0    │
│ caldera-agents-pending_kill │    2    │
└─────────────────────────────┴─────────┘"""
    assert expected == result.get_string()

def test_deploy_packetbeat(mocker, aws_deployment, base_tectonic_path):
    aws_deployment.description.teacher_access = "host"
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"elastic":"password"})
    mocker.patch.object(AWSDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)
    inventory = {
        "packetbeat":{
            "hosts":{
                "udelar-lab01-packetbeat": {
                    'ansible_host': '10.0.0.33',
                    'ansible_ssh_common_args': '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ProxyCommand="ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -W %h:%p ubuntu@127.0.0.1"',
                    'ansible_user': 'ubuntu',
                    'become_flags': '-i',
                    'copy': 1,
                    'instance': None,
                    'networks': mocker.ANY, 
                    'machine_name': 'udelar-lab01-packetbeat',
                    'parameter': {},
                    'random_seed': "Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941",
                }
            },
            'vars': {
                'action': 'install',
                'ansible_become': True,
                'ansible_connection': 'ssh',
                'basename': 'packetbeat',
                'docker_host': 'unix:///var/run/docker.sock',
                'elastic_agent_version': '7.10.2',
                'elastic_url': 'https://10.0.0.31:8220',
                'instances': 2,
                'institution': 'udelar',
                'lab_name': 'lab01',
                'platform': 'aws',
                'token': '1234567890abcdef',
                'proxy': 'http://proxy.fing.edu.uy:3128',
            },
        }
    }
    aws_deployment._deploy_packetbeat()
    assert len(mock_ansible.mock_calls) == 2
    mock_ansible.assert_has_calls([
        mocker.call(inventory=inventory,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(
            inventory=inventory,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
    ])

def test_elastic_install_endpoint(mocker, aws_deployment, base_tectonic_path):
    aws_deployment.description.teacher_access = "host"
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"elastic":"password"})
    mocker.patch.object(AWSDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")

    result_ok = ansible_runner.Runner(config=None)
    result_ok.rc = 0
    result_ok.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result_ok)
    inventory = {'victim': {'hosts': {'udelar-lab01-1-victim-1': {'ansible_host': None, 'ansible_user': 'administrator', 'ansible_ssh_common_args': '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ProxyCommand="ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -W %h:%p ubuntu@127.0.0.1"', 'instance': 1, 'copy': 1, 'networks': mocker.ANY, 'machine_name':'udelar-lab01-1-victim-1', 'parameter': {'flags': 'Flag 2'}, 'random_seed': 'Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941', 'ansible_shell_type': 'powershell', 'ansible_become_method': 'runas', 'ansible_become_user': 'administrator'}, 'udelar-lab01-1-victim-2': {'ansible_host': None, 'ansible_user': 'administrator', 'ansible_ssh_common_args': '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ProxyCommand="ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -W %h:%p ubuntu@127.0.0.1"', 'instance': 1, 'copy': 2, 'networks': mocker.ANY, 'machine_name':'udelar-lab01-1-victim-2', 'parameter': {'flags': 'Flag 2'}, 'random_seed': 'Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941', 'ansible_shell_type': 'powershell', 'ansible_become_method': 'runas', 'ansible_become_user': 'administrator'}}, 'vars': {'ansible_become': True, 'ansible_connection': 'ssh', 'basename': 'victim', 'docker_host': 'unix:///var/run/docker.sock', 'instances': 2, 'platform': 'aws', 'institution': 'udelar', 'lab_name': 'lab01', 'token': '1234567890abcdef', 'elastic_url': 'https://10.0.0.31:8220'}}, 'server': {'hosts': {'udelar-lab01-1-server': {'ansible_host': None, 'ansible_user': 'ubuntu', 'ansible_ssh_common_args': '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ProxyCommand="ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -W %h:%p ubuntu@127.0.0.1"', 'instance': 1, 'copy': 1, 'networks': mocker.ANY, 'machine_name':'udelar-lab01-1-server', 'parameter': {'flags': 'Flag 2'}, 'random_seed': 'Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941', 'become_flags': '-i'}}, 'vars': {'ansible_become': True, 'ansible_connection': 'ssh', 'basename': 'server', 'docker_host': 'unix:///var/run/docker.sock', 'instances': 2, 'platform': 'aws', 'institution': 'udelar', 'lab_name': 'lab01', 'token': '1234567890abcdef', 'elastic_url': 'https://10.0.0.31:8220'}}}
    aws_deployment._elastic_install_endpoint([1])
    assert len(mock_ansible.mock_calls) == 2
    mock_ansible.assert_has_calls([
        mocker.call(inventory=inventory,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(
            inventory=inventory,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'endpoint_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
    ])

def test_recreate(mocker, monkeypatch, capsys, aws_deployment, base_tectonic_path, labs_path, ec2_client, aws_secrets):
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets
    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"elastic":"password"})
    mocker.patch.object(AWSDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")
    mock_terraform = mocker.patch.object(tectonic.deployment.Deployment, "terraform_recreate")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    
    aws_deployment.description.teacher_access = "host"
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.deploy_caldera = True

    aws_deployment.recreate([1],["attacker"], None, False)

    mock_terraform.assert_called_once_with(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws', mocker.ANY)

    assert len(mock_ansible.mock_calls) == 9
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{labs_path}/test-endpoint/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'endpoint_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
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

def test_destroy_infraestructure(mocker, capsys, aws_deployment, base_tectonic_path):
    #Destroy only infraestructure
    aws_deployment.description.monitor_type = "traffic"
    aws_deployment.description.ansible_playbooks_path = aws_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(aws_deployment.description, "get_services_to_deploy", return_value=[])
    mock_deployment = mocker.patch.object(aws_deployment, "terraform_destroy")

    aws_deployment.destroy_infraestructure(None)

    mock_deployment.assert_called_once_with(
        tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
        variables=aws_deployment.get_deploy_cr_vars(),
        resources=None,
    )
    assert capsys.readouterr().out == "Destroying Cyber Range instances...\n"

    # Deploy all infraestructure and services
    aws_deployment.description.monitor_type = "traffic"
    aws_deployment.description.ansible_playbooks_path = aws_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(aws_deployment.description, "get_services_to_deploy", return_value=["elastic","caldera"])
    mock_deployment = mocker.patch.object(aws_deployment, "terraform_destroy")
    aws_deployment.destroy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-aws',
            variables=aws_deployment.get_deploy_services_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
            variables=aws_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
    ])
    assert capsys.readouterr().out == "Destroying Cyber Range services...\nDestroying Cyber Range instances...\n"

    # Destroy instance 1 and services
    mock_deployment = mocker.patch.object(aws_deployment, "terraform_destroy")
    aws_deployment.destroy_infraestructure([1])
    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
            mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-aws',
            variables=aws_deployment.get_deploy_services_vars(),
            resources=aws_deployment.get_services_resources_to_target_destroy([1]),
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
            variables=aws_deployment.get_deploy_cr_vars(),
            resources=aws_deployment.get_cr_resources_to_target_destroy([1]),
        ),
    ])
    assert capsys.readouterr().out == "Destroying Cyber Range services...\nDestroying Cyber Range instances...\n"

def test_deploy_infraestructure(mocker, capsys, aws_deployment, base_tectonic_path, test_data_path):
    # Deploy only instances
    aws_deployment.description.monitor_type = "traffic"
    aws_deployment.description.deploy_caldera = False
    aws_deployment.description.deploy_elastic = False
    aws_deployment.description.ansible_playbooks_path = aws_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(aws_deployment.description, "get_services_to_deploy", return_value=[])
    mock_deployment = mocker.patch.object(aws_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    aws_deployment.deploy_infraestructure(None)

    mock_deployment.assert_called_once_with(
        tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
        variables=aws_deployment.get_deploy_cr_vars(),
        resources=None,
    )
    assert len(mock_ansible.mock_calls) == 3
    mock_ansible.assert_has_calls([
        mocker.call(inventory=mocker.ANY,
                    playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
                    quiet=True,
                    verbosity=0,
                    event_handler=mocker.ANY,
                    extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range instances...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\n"

    # Deploy elastic using traffic as monitor_type
    aws_deployment.description.monitor_type = "traffic"
    aws_deployment.description.deploy_caldera = False
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.ansible_playbooks_path = aws_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(aws_deployment.description, "get_services_to_deploy", return_value=["elastic"])
    mock_deployment = mocker.patch.object(aws_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"elastic":"password"})
    mocker.patch.object(AWSDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")

    aws_deployment.deploy_infraestructure(None)
    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
            variables=aws_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-aws',
            variables=aws_deployment.get_deploy_services_vars(),
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
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range instances...\nDeploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\n"

    # Deploy elastic using endpoint as monitor_type
    aws_deployment.description.monitor_type = "endpoint"
    aws_deployment.description.deploy_caldera = False
    aws_deployment.description.deploy_elastic = True
    aws_deployment.description.ansible_playbooks_path = aws_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(aws_deployment.description, "get_services_to_deploy", return_value=["elastic"])
    mock_deployment = mocker.patch.object(aws_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"elastic":"password"})
    mocker.patch.object(AWSDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")

    aws_deployment.deploy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
            variables=aws_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-aws',
            variables=aws_deployment.get_deploy_services_vars(),
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
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'endpoint_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range instances...\nDeploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\nConfiguring elastic agents...\n"

    # Deploy caldera
    aws_deployment.description.deploy_caldera = True
    aws_deployment.description.deploy_elastic = False
    aws_deployment.description.ansible_playbooks_path = aws_deployment.description.ansible_playbooks_path.replace("endpoint","traffic")
    mocker.patch.object(aws_deployment.description, "get_services_to_deploy", return_value=["caldera"])
    mock_deployment = mocker.patch.object(aws_deployment, "terraform_apply")
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock_ansible = mocker.patch.object(ansible_runner.interface, "run", return_value=result)
    mocker.patch.object(AWSDeployment,"get_instance_status",return_value="RUNNING")
    mocker.patch.object(AWSDeployment,"_get_service_password",return_value={"elastic":"password"})
    mocker.patch.object(AWSDeployment,"_get_service_info",return_value=[{"token" : "1234567890abcdef"}])
    mocker.patch.object(AWSClient,"get_machine_public_ip",return_value="127.0.0.1")

    aws_deployment.deploy_infraestructure(None)

    assert len(mock_deployment.mock_calls) == 2
    mock_deployment.assert_has_calls([
        mocker.call(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
            variables=aws_deployment.get_deploy_cr_vars(),
            resources=None,
        ),
        mocker.call(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-aws',
            variables=aws_deployment.get_deploy_services_vars(),
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
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=f"{test_data_path}/labs/test-traffic/ansible/after_clone.yml",
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
        mocker.call(inventory=mocker.ANY,
            playbook=str(tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'),
            quiet=True,
            verbosity=0,
            event_handler=mocker.ANY,
            extravars={"ansible_no_target_syslog" : not aws_deployment.description.keep_ansible_logs }
        ),
    ])
    assert capsys.readouterr().out == "Deploying Cyber Range instances...\nDeploying Cyber Range services...\nWaiting for services to boot up...\nConfiguring services...\nWaiting for machines to boot up...\nConfiguring student access...\nRunning after-clone configuration...\nConfiguring caldera agents...\n"
