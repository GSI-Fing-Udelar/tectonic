import pytest
import re
import copy
from unittest.mock import patch, MagicMock, call

import libvirt
import libvirt_qemu

from tectonic.client import Client, ClientException
from tectonic.client_aws import ClientAWS, ClientAWSException
from tectonic.client_libvirt import ClientLibvirt, ClientLibvirtException

def test_get_machine_status(client):
    assert client.get_machine_status("udelar-lab01-1-attacker") == "RUNNING"
    assert client.get_machine_status("x") == "NOT FOUND"


def test_get_machine_private_ip(client):
    attacker_ip = client.get_machine_private_ip("udelar-lab01-1-attacker")
    assert re.match(r"^10\.0\.\d+\.\d+$", attacker_ip)
    elastic_ip = client.get_machine_private_ip("udelar-lab01-elastic")
    assert re.match(r"^10\.0\.\d+\.\d+$", elastic_ip)

    assert client.get_machine_private_ip("x") == None


def test_get_machine_public_ip(client):
    if client.config.platform == "aws":
        elastic_ip = client.get_machine_public_ip("udelar-lab01-elastic")
        assert re.match(r"^\d+\.\d+\.\d+\.\d+$", elastic_ip)

    assert client.get_machine_public_ip("x") == None

def test_is_image_in_use(client):
    assert client.is_image_in_use("udelar-lab01-attacker") is True
    assert client.is_image_in_use("test2") is False
    assert client.is_image_in_use("x") is False

def test_delete_image(client):
    if client.config.platform == "aws":
        with patch.object(client.connection, "deregister_image") as mock_image:
            with patch.object(client.connection, "delete_snapshot") as mock_snapshot:
                client.delete_image("test2")
                mock_image.assert_called_once()
                mock_snapshot.assert_called_once()
    elif client.config.platform == "libvirt":
        with patch("tectonic.client_libvirt.libvirt.virStorageVol.delete") as mock_libvirt:
            client.delete_image("test2")
            mock_libvirt.assert_called_once()
    elif client.config.platform == "docker":
        client.delete_image("test2")
        client.connection.images.remove.assert_called_once()

    # Image is in use
    with pytest.raises(ClientException):
        client.delete_image("udelar-lab01-attacker")

    # Image not found
    client.delete_image("x")    # Does nothing


def test_modify_machine_state(client):
    assert client.get_machine_status("udelar-lab01-1-attacker") == "RUNNING"
    client.stop_machine("udelar-lab01-1-attacker")
    assert client.get_machine_status("udelar-lab01-1-attacker") == "STOPPED"
    client.start_machine("udelar-lab01-1-attacker")
    assert client.get_machine_status("udelar-lab01-1-attacker") == "RUNNING"
    client.restart_machine("udelar-lab01-1-attacker")
    assert client.get_machine_status("udelar-lab01-1-attacker") == "RUNNING"

    with pytest.raises(ClientException):
        client.start_machine("x")

@patch("tectonic.client_aws.interactive_shell")
@patch("tectonic.client_libvirt.interactive_shell")
@patch("tectonic.client_docker.subprocess.run")
def test_console(mock_docker, mock_libvirt, mock_aws, client):
    client.console("udelar-lab01-1-attacker", "user")
    if client.config.platform == "aws":
        mock_aws.assert_called_once()
    elif client.config.platform == "libvirt":
        mock_libvirt.assert_called_once()
    elif client.config.platform == "docker":
        mock_docker.assert_called_once()

def test_get_ssh_proxy_command(client):
    if client.config.platform == "aws":
        client.config.aws.teacher_access = "endpoint"
        assert "aws ec2-instance-connect" in client.get_ssh_proxy_command()
        client.config.aws.teacher_access = "host"
        teacher_ip = client._get_teacher_access_ip()
        user = client._get_teacher_access_username()
        assert re.match(f"^ssh.*{user}@{teacher_ip}", client.get_ssh_proxy_command())
    else:
        assert client.get_ssh_proxy_command() is None

def test_get_ssh_hostname(client):
    if client.config.platform == "aws":
        client.config.aws.teacher_access = "endpoint"
        instance_id = client._get_machine_id("udelar-lab01-1-attacker")
        assert client.get_ssh_hostname("udelar-lab01-1-attacker") == instance_id

        client.config.aws.teacher_access = "host"

    # AWS with host teacher, or libvirt or docker should return the machine private IP
    private_ip = client.get_machine_private_ip("udelar-lab01-1-attacker")
    assert client.get_ssh_hostname("udelar-lab01-1-attacker") == private_ip



# -------------------------------
# Tests for ClientAWS internals
# -------------------------------

@patch("tectonic.client_aws.boto3.client", side_effect=Exception("boom"))
def test_aws_init_fail(mock_client, description):
    if description.config.platform == "aws":
        with pytest.raises(ClientAWSException, match="boom"):
            ClientAWS(description.config, description)

def test_aws_init_success(description):
    if description.config.platform == "aws":
        ClientAWS(description.config, description)


# -------------------------------
# Tests for ClientLibvirt internals
# -------------------------------

@patch("tectonic.client_libvirt.libvirt.open", side_effect=Exception("boom"))
def test_libvirt_init_fail(mock_open, description):
    if description.config.platform == "libvirt":
        with pytest.raises(ClientLibvirtException, match="boom"):
            ClientLibvirt(description.config, description)

def test_libvirt_init_success(description):
    if description.config.platform == "libvirt":
        ClientLibvirt(description.config, description)


def test_libvirt_wait_for_agent(monkeypatch, client):
    if client.config.platform == "libvirt":
        def raise_error(domain, command, timeout, flags):
            raise libvirt.libvirtError("boom")

        monkeypatch.setattr(libvirt_qemu, "qemuAgentCommand", raise_error)
        with pytest.raises(ClientLibvirtException, match="Cannot connect to QEMU agent."):
            client._wait_for_agent(MagicMock(libvirt.virDomain), sleep=1, max_tries=2)
