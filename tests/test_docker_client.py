
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

from tectonic.docker_client import DockerClientException, Client as DockerClient
from unittest.mock import patch, MagicMock
import docker

class MockDescription:
    def __init__(self, description):
        self.docker_uri = description.docker_uri

def test_client_constructor(description):
    original_uri = description.docker_uri
    description.docker_uri = "/invalid/"
    mock_description = MockDescription(description)
    with patch('docker.DockerClient', side_effect=Exception("Docker connection failed")):
        with pytest.raises(DockerClientException) as exception:
            DockerClient(description)
    assert "Cannot connect to docker server" in str(exception.value)

    description.docker_uri = original_uri
    mock_description = MockDescription(description)
    mock_docker_client = MagicMock()
    with patch('docker.DockerClient', return_value=mock_docker_client):
        client = DockerClient(mock_description)
    assert client.connection == mock_docker_client

def test_get_machine_private_ip(mock_docker_client, mocker, description):
    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    client = DockerClient(description)
    ip = client.get_machine_private_ip("udelar-lab01-1-attacker")
    assert ip == "10.0.1.4"

    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    client = DockerClient(description)
    ip = client.get_machine_private_ip("udelar-lab01-1-victim")
    assert ip == "10.0.1.5"

    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    client = DockerClient(description)
    ip = client.get_machine_private_ip("udelar-lab01-elastic")
    assert ip == "10.0.0.129"

    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    client = DockerClient(description)
    ip = client.get_machine_private_ip("udelar-lab01-test")
    assert ip == None

    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    mock_docker_client.containers.get.side_effect = Exception("Unexpected error")
    client = DockerClient(description)
    with pytest.raises(DockerClientException) as exception:
        client.get_instance_status("test")
    assert "Unexpected error" in str(exception.value)

def test_get_instance_status(mock_docker_client, mocker, description):
    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    client = DockerClient(description)
    status = client.get_instance_status("udelar-lab01-1-attacker")
    assert status == "RUNNING"

    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    client = DockerClient(description)
    status = client.get_instance_status("udelar-lab01-1-victim")
    assert status == "STOPPED"

    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    mock_docker_client.containers.get.side_effect = docker.errors.NotFound("Container not found")
    client = DockerClient(description)
    status = client.get_instance_status("no-exists")
    assert status == "UNKNOWN"

    mocker.patch("docker.DockerClient", return_value=mock_docker_client)
    mock_docker_client.containers.get.side_effect = Exception("Unexpected error")
    client = DockerClient(description)
    with pytest.raises(DockerClientException) as exception:
        client.get_instance_status("test")
    assert "Unexpected error" in str(exception.value)