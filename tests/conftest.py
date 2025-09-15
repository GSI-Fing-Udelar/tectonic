
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
import copy
import boto3
import pytest
import docker

# from tectonic.deployment_aws import AWSDeployment
# from tectonic.deployment_libvirt import LibvirtDeployment
# from tectonic.deployment_docker import DockerDeployment
from tectonic.config import TectonicConfig
from tectonic.ansible import Ansible
from tectonic.description import Description
from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS
# from tectonic.libvirt_client import Client as LibvirtClient
from tectonic.client_aws import ClientAWS
from tectonic.client_docker import ClientDocker

from pathlib import Path
from moto import mock_ec2, mock_secretsmanager
from unittest.mock import MagicMock


test_config = """
[config]
platform = PLATFORM
lab_repo_uri = TEST_DATA_PATH/labs
network_cidr_block = 10.0.0.0/16
internet_network_cidr_block = 10.0.0.0/25
services_network_cidr_block = 10.0.0.128/25
ssh_public_key_file = ~/.ssh/id_rsa.pub
configure_dns = no
debug = yes

[ansible]
ssh_common_args = -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=3600 
keep_logs = no
forks = 5
pipelining = no
timeout = 10

[libvirt]
# uri="qemu+ssh://gsi@localhost:22222/system?no_verify=1
# uri=qemu+ssh://gsi@gsi03/system?known_hosts=/home/jdcampo/.ssh/known_hosts
#uri = qemu+ssh://gsi@tortuga:4446/system?known_hosts=/home/jdcampo/gsi/lasi/repos/tectonic/python/known_hosts
uri = test:///TEST_DATA_PATH/libvirt_config.xml
storage_pool = pool-dir
student_access = bridge
bridge = lab_ens
external_network = 192.168.44.0/25
bridge_base_ip = 10

[aws]
region = us-east-1
teacher_access = host

[docker]
uri = unix:///var/run/docker.sock
dns = 8.8.8.8

[elastic]
elastic_stack_version = 8.14.3
packetbeat_policy_name = Packetbeat
endpoint_policy_name = Endpoint
user_install_packetbeat = gsi

[caldera]
version = 5.0.0
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

@pytest.fixture(scope="session", params=["aws","libvirt", "docker"])
def tectonic_config_data(request, tmp_path_factory, test_data_path):
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

@pytest.fixture(scope="session")
def tectonic_config(tectonic_config_data):
    config = TectonicConfig.load(tectonic_config_data)

    yield config
    

@pytest.fixture(scope="session")
def labs_path(test_data_path):
    return (Path(test_data_path) / "labs").absolute().as_posix()

@pytest.fixture(scope="session")
def description(tectonic_config, labs_path):
    desc = Description(tectonic_config, Path(labs_path) / "test.yml")

    yield desc

@pytest.fixture(autouse=True)
def mock_aws_client(monkeypatch, aws_secrets, ec2_client, description):
    def patch_aws_client(self, config, description):
        self.connection = ec2_client
        self.secretsmanager_client = aws_secrets
        self.config = config
        self.description = description

    monkeypatch.setattr(ClientAWS, "__init__", patch_aws_client)

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

# Automatically use in all tests a mocked instance of the standard
# docker library DockerClient object inside the
# tectonic.client_docker.ClientDocker class.
@pytest.fixture(autouse=True)
def mock_docker_client(monkeypatch):
    mock_client = MagicMock(docker.DockerClient)
    mock_container_1 = MagicMock()
    mock_container_1.name = "udelar-lab01-1-attacker"
    mock_container_1.status = "running"
    mock_container_1.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-lan": {"IPAddress": "10.0.1.4"},
            }
        }
    }
    mock_container_2 = MagicMock()
    mock_container_2.name = "udelar-lab01-1-victim-1"
    mock_container_2.status = "stopped"
    mock_container_2.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-lan": {"IPAddress": "10.0.1.5"},
                "udelar-lab01-services": {"IPAddress": "10.0.0.130"},
            }
        }
    }
    mock_container_3 = MagicMock()
    mock_container_3.name = "udelar-lab01-1-victim-2"
    mock_container_3.status = "stopped"
    mock_container_3.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-lan": {"IPAddress": "10.0.1.6"},
                "udelar-lab01-services": {"IPAddress": "10.0.0.131"},
            }
        }
    }
    mock_container_4 = MagicMock()
    mock_container_4.name = "udelar-lab01-elastic"
    mock_container_4.status = "running"
    mock_container_4.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-internet": {"IPAddress": "10.0.0.129"},
                "udelar-lab01-services": {"IPAddress": "10.0.0.2"},
            }
        }
    }
    mock_container_5 = MagicMock()
    mock_container_5.name = "udelar-lab01-test"
    mock_container_5.attrs = {
        "NetworkSettings": {
            "Networks": {
            }
        }
    }
    mock_container_6 = MagicMock()
    mock_container_6.name = "udelar-lab01-2-attacker"
    mock_container_6.status = "running"
    mock_container_6.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-lan": {"IPAddress": "10.0.2.4"},
            }
        }
    }
    mock_container_7 = MagicMock()
    mock_container_7.name = "udelar-lab01-1-victim-1"
    mock_container_7.status = "stopped"
    mock_container_7.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-lan": {"IPAddress": "10.0.2.5"},
                "udelar-lab01-services": {"IPAddress": "10.0.0.133"},
            }
        }
    }
    mock_container_8 = MagicMock()
    mock_container_8.name = "udelar-lab01-1-victim-2"
    mock_container_8.status = "stopped"
    mock_container_8.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-lan": {"IPAddress": "10.0.2.6"},
                "udelar-lab01-services": {"IPAddress": "10.0.0.134"},
            }
        }
    }
    mock_container_9 = MagicMock()
    mock_container_9.name = "udelar-lab01-caldera"
    mock_container_9.status = "running"
    mock_container_9.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-internet": {"IPAddress": "10.0.0.130"},
                "udelar-lab01-services": {"IPAddress": "10.0.0.3"},
            }
        }
    }
    mock_container_10 = MagicMock()
    mock_container_10.name = "udelar-lab01-1-server"
    mock_container_10.status = "stopped"
    mock_container_10.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-lan": {"IPAddress": "10.0.1.6"},
            }
        }
    }
    mock_container_11 = MagicMock()
    mock_container_11.name = "udelar-lab01-2-server"
    mock_container_11.status = "stopped"
    mock_container_11.attrs = {
        "NetworkSettings": {
            "Networks": {
                "udelar-lab01-lan": {"IPAddress": "10.0.2.6"},
            }
        }
    }
    mock_client.containers.get.side_effect = lambda name: {
        "udelar-lab01-1-attacker": mock_container_1,
        "udelar-lab01-1-victim-1": mock_container_2,
        "udelar-lab01-1-victim-2": mock_container_3,
        "udelar-lab01-elastic": mock_container_4,
        "udelar-lab01-test": mock_container_5,
        "udelar-lab01-2-attacker": mock_container_6,
        "udelar-lab01-2-victim-1": mock_container_7,
        "udelar-lab01-2-victim-2": mock_container_8,
        "udelar-lab01-caldera": mock_container_9,
        "udelar-lab01-1-server": mock_container_10,
        "udelar-lab01-2-server": mock_container_11,
    }.get(name, None)

    mock_client.images.get.side_effect = lambda image_id: {
        "udelar-lab01-attacker": MagicMock(id="udelar-lab01-attacker", tags=["udelar-lab01-attacker"]),
        "udelar-lab01-victim": MagicMock(id="udelar-lab01-victim", tags=["udelar-lab01-victim"]),
        "udelar-lab01-server": MagicMock(id="udelar-lab01-server", tags=["udelar-lab01-server"]),
        "udelar-lab01-elastic": MagicMock(id="udelar-lab01-elastic", tags=["udelar-lab01-elastic"]),
        "elastic": MagicMock(id="elastic", tags=["elastic"]),
        "caldera": MagicMock(id="caldera", tags=["caldera"]),
    }.get(image_id, None)

    def patched_init(self, config, description):
        self.connection = mock_client
        self.config = config
        self.description = description
    monkeypatch.setattr(ClientDocker, "__init__", patched_init)


# @pytest.fixture()
# def docker_deployment(monkeypatch, description, docker_client):
#     # Fix description platform:
#     description_docker = copy.copy(description)
#     description_docker.platform = "docker"
    
#     def patch_docker_client(self, description):
#         self.connection = docker_client
#         self.description = description
#     monkeypatch.setattr(DockerClient, "__init__", patch_docker_client)

#     d = DockerDeployment(
#         description=description_docker,
#         gitlab_backend_url="https://gitlab.com",
#         gitlab_backend_username="testuser",
#         gitlab_backend_access_token="testtoken",
#     )
#     yield d
