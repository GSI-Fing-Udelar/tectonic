
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

import os
from pprint import pprint

import copy
import boto3
import pytest

from tectonic.deployment_aws import AWSDeployment
from tectonic.deployment_libvirt import LibvirtDeployment
from tectonic.ansible import Ansible
from tectonic.description import Description
from tectonic.instance_type_aws import InstanceTypeAWS
from tectonic.libvirt_client import Client as LibvirtClient
from tectonic.aws import Client as AWSClient

from pathlib import Path

from moto import mock_ec2, mock_secretsmanager


test_config = """
[config]
platform = PLATFORM
lab_repo_uri = TEST_DATA_PATH/labs
network_cidr_block = 10.0.0.0/16
internet_network_cidr_block = 10.0.0.0/25
services_network_cidr_block = 10.0.0.128/25
ssh_public_key_file = ~/.ssh/id_rsa.pub
ansible_ssh_common_args = -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no
configure_dns = no
gitlab_backend_url = https://gitlab.fing.edu.uy/api/v4/projects/9886/terraform/state
debug = yes
keep_ansible_logs = no


[libvirt]
# libvirt_uri="qemu+ssh://gsi@localhost:22222/system?no_verify=1
# libvirt_uri=qemu+ssh://gsi@gsi03/system?known_hosts=/home/jdcampo/.ssh/known_hosts
#libvirt_uri = qemu+ssh://gsi@tortuga:4446/system?known_hosts=/home/jdcampo/gsi/lasi/repos/tectonic/python/known_hosts
libvirt_uri = test:///TEST_DATA_PATH/libvirt_config.xml
libvirt_storage_pool = pool-dir

 # TODO: allow `port_forwarding'
libvirt_student_access = bridge
libvirt_bridge = lab_ens
libvirt_external_network = 192.168.44.10/25
libvirt_bridge_base_ip = 10
libvirt_proxy=http://proxy.fing.edu.uy:3128

[aws]
aws_region = us-east-1
aws_default_instance_type = t2.micro
teacher_access = host

[elastic]
elastic_stack_version = latest
packetbeat_policy_name = Packetbeat
endpoint_policy_name = Endpoint
packetbeat_vlan_id = 1
"""

@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="session")
def ec2_client(aws_credentials, aws_instance_name, example_image_id, example_lab_names,
               example_institutions):
    with mock_ec2():
        client = boto3.client("ec2", region_name="us-east-1")
        # Create Public VPC
        public_vpc_id = client.create_vpc(
            CidrBlock='10.0.0.0/16',
        )['Vpc']['VpcId']
        # # Create Private VPC
        # private_vpc_id = client.create_vpc(CidrBlock='10.1.0.0/16', InstanceTenancy='default')['Vpc']['VpcId']
        # # Create subnet
        public_subnet_id = client.create_subnet(
            VpcId=public_vpc_id,
            CidrBlock='10.0.0.0/24',
            AvailabilityZone='us-east-1b',
        )['Subnet']['SubnetId']
        # private_subnet_id = client.create_subnet(
        #     VpcId=private_vpc_id,
        #     CidrBlock='10.1.0.0/24',
        #     AvailabilityZone='us-east-1b'
        # )['Subnet']['SubnetId']
        # # Create Internet Gateway
        # internet_gateway_id = client.create_internet_gateway()['InternetGateway']['InternetGatewayId']
        # # Attach Internet Gateway to VPC
        # client.attach_internet_gateway(VpcId=public_vpc_id,InternetGatewayId=internet_gateway_id)
        # # Create route table
        # public_route_table_id = client.create_route_table(VpcId=public_vpc_id)['RouteTable']['RouteTableId']
        # # Associate route table with subnet
        # client.create_route(
        #     RouteTableId=public_route_table_id,
        #     DestinationCidrBlock='0.0.0.0/0',
        #     GatewayId=internet_gateway_id
        # )
        # # Create security group
        # private_security_group_id = client.create_security_group(
        #     GroupName="private_sg",
        #     Description="Private Security Group",
        #     VpcId=private_vpc_id
        # )['GroupId']
        public_security_group_id = client.create_security_group(
            GroupName="public_sg",
            Description="Public Security Group",
            VpcId=public_vpc_id
        )['GroupId']
        for institution in example_institutions:
            for lab_name in example_lab_names:
                for instance_name in ["1-attacker", "student_access", "teacher_access", "elastic", "caldera", "packetbeat"]:
                    aws_instance_name = f"{institution}-{lab_name}-{instance_name}"
                    tags_name = [{"Key": "Name", "Value": aws_instance_name}]
                    instance = client.run_instances(
                        ImageId=example_image_id,
                        MinCount=1, MaxCount=1,
                        TagSpecifications=[{"ResourceType": "instance", "Tags": tags_name}],
                        NetworkInterfaces=[
                            {"DeviceIndex": 0, "SubnetId": public_subnet_id,
                             "AssociatePublicIpAddress": True},
                        ])["Instances"][0]
                    assert instance["State"]["Name"] == "pending"

                    image_name = instance_name
                    if instance_name == "1-attacker":
                        image_name = "attacker"
                    tags_name = [{"Key": "Name", "Value": f"{institution}-{lab_name}-{image_name}"}]
                    image = client.create_image(
                        Name=f"{institution}-{lab_name}-{image_name}",
                        TagSpecifications=[{"ResourceType": "image", "Tags": tags_name}],
                        BlockDeviceMappings=[
                            {
                                'DeviceName': '/dev/sdh',
                                'Ebs': {
                                    'VolumeSize': 100,
                                },
                            },
                            {
                                'DeviceName': '/dev/sdc',
                                'VirtualName': 'ephemeral1',
                            },
                        ],
                        InstanceId=instance["InstanceId"],
                        Description=f'{aws_instance_name} test image',
                        NoReboot=True
                    )
                    assert image["ImageId"] is not None
                    if instance_name not in ["student_access", "teacher_access", "elastic", "packetbeat", "caldera"]:
                        client.stop_instances(InstanceIds=[instance["InstanceId"]])
        yield client


@pytest.fixture(scope="session")
def example_institutions():
    return ["fing", "cyberlac", "udelar"]


@pytest.fixture(scope="session")
def example_lab_names():
    return ["lab01", "lab02"]


@pytest.fixture(scope="session")
def aws_secrets(example_institutions, example_lab_names):
    with mock_secretsmanager():
        sm = boto3.client("secretsmanager", region_name="us-east-1")
        for institution in example_institutions:
            for lab_name in example_lab_names:
                sm.create_secret(Name=f"elastic-credentials-{institution}-{lab_name}",
                                 SecretString='{"username": "foo", "password": "bar"}')
        yield sm


@pytest.fixture(scope="session")
def aws_instance_name():
    return "udelar-lab01-1-attacker"


@pytest.fixture(scope="session")
def unexpected_instance_name():
    return "udelar-lab99-something"


@pytest.fixture(scope="session")
def example_image_id():
    return "ami-03cf127a"

@pytest.fixture(scope="session")
def terraform_dir():
    return "tests/terraform"


@pytest.fixture(scope="session")
def base_tests_path():
    return Path(__file__).parent.absolute().as_posix()

@pytest.fixture(scope="session")
def base_tectonic_path():
    return Path(__file__).parent.parent.absolute()

@pytest.fixture(scope="session")
def test_data_path(base_tests_path):
    return Path(base_tests_path).joinpath("test_data/").absolute().as_posix()


@pytest.fixture(scope="session")
def labs_path(test_data_path):
    return Path(test_data_path).joinpath("labs/").absolute().as_posix()

@pytest.fixture(scope="session")
def description(labs_path, terraform_dir, test_data_path):
    desc = Description(
        path=Path(labs_path).joinpath("test.yml"),
        platform="aws",
        lab_repo_uri=labs_path,
        teacher_access="host",
        configure_dns=False,
        ssh_public_key_file=f"{terraform_dir}/id_rsa.pub",
        ansible_ssh_common_args="-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no",
        aws_region="us-east-1",
        aws_default_instance_type="t2.micro",
        network_cidr_block="10.0.0.0/16",
        packetbeat_policy_name="Packetbeat",
        packetbeat_vlan_id="1",
        elastic_stack_version="7.10.2",
        libvirt_uri=f"test:///{test_data_path}/libvirt_config.xml",
        libvirt_storage_pool="pool-dir",
        libvirt_student_access="bridge",
        libvirt_bridge="lab_ens",
        libvirt_external_network="192.168.44.10/25",
        libvirt_bridge_base_ip=10,
        libvirt_proxy="http://proxy.fing.edu.uy:3128",
        instance_type=InstanceTypeAWS("t2.micro"),
        endpoint_policy_name="Endpoint",
        internet_network_cidr_block="10.0.0.0/25",
        services_network_cidr_block="10.0.0.128/25",
        keep_ansible_logs=False
    )
    yield desc


@pytest.fixture()
def aws_deployment(monkeypatch, description, aws_secrets, ec2_client):
    def patch_aws_client(self, region):
        self.ec2_client = ec2_client
        self.secretsmanager_client = aws_secrets

    monkeypatch.setattr(AWSClient, "__init__", patch_aws_client)

    d = AWSDeployment(
        description=description,
        gitlab_backend_url="https://gitlab.com",
        gitlab_backend_username="testuser",
        gitlab_backend_access_token="testtoken",
        packer_executable_path="/usr/bin/packer",
    )
    yield d

@pytest.fixture(scope="session")
def libvirt_deployment(description):
    # Fix description platform:
    description_libvirt = copy.copy(description)
    description_libvirt.platform = "libvirt"

    d = LibvirtDeployment(
        description=description_libvirt,
        gitlab_backend_url="https://gitlab.com",
        gitlab_backend_username="testuser",
        gitlab_backend_access_token="testtoken",
    )
    yield d


@pytest.fixture(scope="session")
def ansible_libvirt(libvirt_deployment):
    a = Ansible(libvirt_deployment)
    yield a

@pytest.fixture()
def ansible_aws(aws_deployment):
    b = Ansible(aws_deployment)
    yield b

@pytest.fixture(scope="session", params=["aws","libvirt"])
def tectonic_config(request, tmp_path_factory, test_data_path):
    config_file = tmp_path_factory.mktemp('data') / f"{request.param}-config.ini"
    config_ini = test_config.replace(
        "TEST_DATA_PATH",
        test_data_path
    ).replace(
        "PLATFORM",
        request.param
    )
    config_file.write_text(config_ini)
    return config_file.resolve().as_posix()


@pytest.fixture(scope="session",params=["traffic", "endpoint"])
def lab_edition_file(request, tmp_path_factory, test_data_path):
    config_file = tmp_path_factory.mktemp('data') / "lab_edition.yml"
    config_file.write_text(f"""
---
base_lab: test-{request.param}
teacher_pubkey_dir: {test_data_path}/teacher_pubkeys
instance_number: 1

create_student_passwords: yes
random_seed: Yjfz1mwpCISi868b329da9893e34099c7d8ad5cb9c941

caldera_settings:
    enable: no
""")
    return config_file.resolve().as_posix()

@pytest.fixture(scope="session")
def libvirt_client(description):
    client = LibvirtClient(description)
    yield client

@pytest.fixture(scope="session")
def aws_client(description, ec2_client, aws_secrets):
    client = AWSClient(description=description, connection=ec2_client, secrets_manager=aws_secrets)
    yield client
