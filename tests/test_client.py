import pytest
import re
import copy


from unittest.mock import patch, MagicMock, call, Mock
import docker
import boto3
import libvirt
import libvirt_qemu

from tectonic.client import Client
from tectonic.client_docker import ClientDocker, ClientDockerException
from tectonic.client_aws import ClientAWS, ClientAWSException
from tectonic.client_libvirt import ClientLibvirt, ClientLibvirtException, libvirt_callback

def test_docker_init_success(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    assert c.connection.images.get('udelar-lab01-attacker').id == 'udelar-lab01-attacker'

# @patch("tectonic.client_docker.docker.DockerClient", side_effect=Exception("fail"))
# def test_docker_init_fail(mock_client, description):
#     if description.config.platform != "docker":
#         pytest.skip("Docker test")

#     with pytest.raises(ClientDockerException):
#         ClientDocker(description.config, description)

def test_docker_get_machine_status_found(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    assert c.get_machine_status("udelar-lab01-1-attacker") == "RUNNING"

def test_docker_get_machine_status_notfound(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    c.connection.containers.get.side_effect = docker.errors.NotFound("x")
    assert c.get_machine_status("x") == "NOT FOUND"

def test_docker_get_machine_status_exception(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    c.connection.containers.get.side_effect = Exception("boom")
    with pytest.raises(ClientDockerException):
        c.get_machine_status("x")

def test_docker_get_machine_private_ip_from_services(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    assert c.get_machine_private_ip("udelar-lab01-1-server") == "10.0.1.6"

def test_docker_get_machine_private_ip_from_container(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    assert c.get_machine_private_ip("udelar-lab01-elastic") == "10.0.0.133"

def test_docker_get_image_id_found(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    assert c.get_image_id("udelar-lab01-victim") == "udelar-lab01-victim"

def test_docker_get_image_id_notfound(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    c.connection.images.get.side_effect = docker.errors.ImageNotFound("x")
    assert c.get_image_id("x") is None

def test_docker_is_image_in_use_true_false(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    cont1 = MagicMock()
    cont1.image.tags = ["imgx:latest"]
    cont2 = MagicMock()
    cont2.image.tags = []
    c.connection.containers.list.return_value = [cont1, cont2]
    assert c.is_image_in_use("imgx") is True
    c.connection.containers.list.return_value = [cont2]
    assert c.is_image_in_use("imgx") is False

@patch("tectonic.client_docker.subprocess.run")
def test_docker_console(mock_run, description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    cont = MagicMock()
    cont.id = "cid"
    c.connection.containers.get.return_value = cont
    c.console("udelar-lab01-2-attacker", "user")
    mock_run.assert_called_once()

def test_docker_start_stop_restart_delete_image(description):
    if description.config.platform != "docker":
        pytest.skip("Docker test")

    c = ClientDocker(description.config, description)
    c.start_machine("udelar-lab01-2-server")
    c.stop_machine("udelar-lab01-2-server")
    c.restart_machine("udelar-lab01-2-server")
    c.delete_image("udelar-lab01-server")
    c.connection.images.remove.assert_called_once()




# -------------------------------
# Tests for ClientAWS
# -------------------------------

def test_aws_init_success(description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

# @patch("tectonic.client_aws.boto3.client", side_effect=Exception("boom"))
# def test_aws_init_fail(mock_client, description):
#     with pytest.raises(ClientAWSException):
#         ClientAWS(DummyConfig(), DummyDescription())


def test_aws_delete_security_groups(mocker, description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    c.connection.delete_security_group = MagicMock()
    c.delete_security_groups("Public Security Group")
    c.connection.delete_security_group.assert_called_once()

def test_aws_get_machine_status_found_and_notfound(description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)
    assert c.get_machine_status("udelar-lab01-1-attacker") == "STOPPED"
    assert c.get_machine_status("x") == "NOT FOUND"

def test_aws_get_machine_private_ip_public_ip(description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)
    private_ip = c.get_machine_private_ip("udelar-lab01-elastic")
    public_ip = c.get_machine_public_ip("udelar-lab01-elastic")
    assert re.match(r"^10\.0\.\d+\.\d+$", private_ip)
    assert re.match(r"^\d+\.\d+\.\d+\.\d+", public_ip)

def test_aws_get_image_id_and_none(description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    assert re.match(r"^ami-.+$", c.get_image_id("udelar-lab01-attacker"))
    assert c.get_image_id("x") is None

def test_aws_is_image_in_use_true_false(description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    # TODO - Check how to set up mocked ec2_client so that this returns true
    # assert c.is_image_in_use("udelar-lab01-1-attacker") is True
    assert c.is_image_in_use("x") is False

def test_aws_delete_image_with_snapshot_and_id(description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)
    c.connection.deregister_image = MagicMock()
    c.connection.delete_snapshot = MagicMock()

    c.delete_image("udelar-lab01-attacker")
    c.connection.deregister_image.assert_called_once()
    c.connection.delete_snapshot.assert_called_once()

def test_aws_start_stop_restart_machine_found_and_notfound(description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    assert c.get_machine_status("udelar-lab01-1-attacker") == "STOPPED"
    c.start_machine("udelar-lab01-1-attacker")
    assert c.get_machine_status("udelar-lab01-1-attacker") == "RUNNING"
    c.stop_machine("udelar-lab01-1-attacker")
    assert c.get_machine_status("udelar-lab01-1-attacker") == "STOPPED"
    c.restart_machine("udelar-lab01-1-attacker")
    assert c.get_machine_status("udelar-lab01-1-attacker") == "RUNNING"
    with pytest.raises(ClientAWSException):
        c.start_machine("x")

def test_aws_get_machine_id(description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    assert re.match(r"^i-.+$", c.get_machine_id("udelar-lab01-1-attacker"))

@patch("tectonic.client_aws.interactive_shell")
def test_aws_console_host_and_endpoint(mock_shell, description):
    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    c.console("udelar-lab01-1-attacker", "user")
    mock_shell.assert_called_once()

def test_aws_get_ssh_proxy_command(description):
    description = copy.deepcopy(description)

    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    c.config.aws.teacher_access = "endpoint"
    assert "aws ec2-instance-connect" in c.get_ssh_proxy_command()

    c.config.aws.teacher_access = "host"
    teacher_ip = c._get_teacher_access_ip()
    user = c._get_teacher_access_username()

    s = c.get_ssh_proxy_command()
    assert re.match(f"^ssh.*{user}@{teacher_ip}", s)

def test_aws_get_ssh_hostname_endpoint_vs_host(description):
    description = copy.deepcopy(description)

    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    c.config.aws.teacher_access = "endpoint"
    instance_id = c.get_machine_id("udelar-lab01-1-attacker")
    assert c.get_ssh_hostname("udelar-lab01-1-attacker") == instance_id

    c.config.aws.teacher_access = "host"
    private_ip = c.get_machine_private_ip("udelar-lab01-1-attacker")
    assert c.get_ssh_hostname("udelar-lab01-1-attacker") == private_ip

def test_aws_teacher_access_methods(description):
    description = copy.deepcopy(description)

    if description.config.platform != "aws":
        pytest.skip("AWS test")

    c = ClientAWS(description.config, description)

    c.description.default_os = "ubuntu22"
    from tectonic.constants import OS_DATA
    assert c._get_teacher_access_username() == OS_DATA["ubuntu22"]["username"]
    c.config.aws.teacher_access = "host"

    teacher_ip = c._get_teacher_access_ip()
    assert "udelar-lab01-teacher_access" in c._get_teacher_access_name()

    c.config.aws.teacher_access = "endpoint"
    assert c._get_teacher_access_ip() is None
    assert c._get_teacher_access_name() is None

    
