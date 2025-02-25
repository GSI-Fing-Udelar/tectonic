
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

import responses
import tectonic.deployment
import python_terraform


def test_run_terraform_cmd(mocker, terraform_dir):
    t = python_terraform.Terraform(working_dir=terraform_dir)

    mocker.patch.object(t, "cmd", return_value=(0, "Success", ""))
    spy = mocker.spy(t, "cmd")
    output = tectonic.deployment.run_terraform_cmd(t, cmd="test", variables={"var1": "value1"}, input=False)
    assert output == "Success"
    spy.assert_called_once_with("test", no_color=python_terraform.IsFlagged, var={"var1": "value1"}, input=False)

    mocker.patch.object(t, "cmd", return_value=(1, "", "Invalid command"))
    with pytest.raises(tectonic.deployment.TerraformRunException) as exception:
        tectonic.deployment.run_terraform_cmd(t, cmd="error", variables=())
    assert "ERROR: terraform error returned an error: Invalid command" in str(exception.value)


def test_abstract_methods(description):
    d = tectonic.deployment.Deployment(
        description=description,
        client=None,
        gitlab_backend_url="https://gitlab.com",
        gitlab_backend_username="testuser",
        gitlab_backend_access_token="testtoken",
        packer_executable_path="/usr/bin/packer",
    )
    with pytest.raises(NotImplementedError):
        d.get_deploy_cr_vars()
    with pytest.raises(NotImplementedError):
        d.get_deploy_services_vars()
    with pytest.raises(NotImplementedError):
        d.delete_cr_images()
    with pytest.raises(NotImplementedError):
        d.get_instance_status(None)
    with pytest.raises(NotImplementedError):
        d.get_cyberrange_data()
    with pytest.raises(NotImplementedError):
        d.connect_to_instance("instance name", "username")
    with pytest.raises(NotImplementedError):
        d.start_instance("instance name")
    with pytest.raises(NotImplementedError):
        d.stop_instance("instance name")
    with pytest.raises(NotImplementedError):
        d.reboot_instance("instance name")
    with pytest.raises(NotImplementedError):
        d.get_cr_resources_to_target_apply(None)
    with pytest.raises(NotImplementedError):
        d.get_cr_resources_to_target_destroy(None)
    with pytest.raises(NotImplementedError):
        d.get_resources_to_recreate(None, (), None)
    with pytest.raises(NotImplementedError):
        d.get_services_resources_to_target_destroy(None)
    with pytest.raises(NotImplementedError):
        d.get_services_resources_to_target_destroy(None)
    with pytest.raises(NotImplementedError):
        d.list_instances(None,None,None)
    with pytest.raises(NotImplementedError):
        d.shutdown(None,None,None,True)
    with pytest.raises(NotImplementedError):
        d.start(None,None,None,True)
    with pytest.raises(NotImplementedError):
        d.reboot(None,None,None,True)
    with pytest.raises(NotImplementedError):
        d.recreate(None,None,None,True)
    with pytest.raises(NotImplementedError):
        d.deploy_infraestructure(None)
    with pytest.raises(NotImplementedError):
        d.destroy_infraestructure(None)
    with pytest.raises(NotImplementedError):
        d.delete_services_images({})
    with pytest.raises(NotImplementedError):
        d.get_services_status()
    with pytest.raises(NotImplementedError):
        d._get_services_guest_data()
    with pytest.raises(NotImplementedError):
        d._get_services_network_data()

@responses.activate
def test_get_elastic_latest_version(description):
    deployment = tectonic.deployment.Deployment(description, None, None, None, None, None)
    responses.add(responses.GET,
        'https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html',
        body='<html><body></body><a class="xref" href="release-notes-8.12.2.html" title="Elasticsearch version 8.12.2"><em>Elasticsearch version 8.12.2</em></a><a class="xref" href="release-notes-8.12.1.html" title="Elasticsearch version 8.12.1"><em>Elasticsearch version 8.12.1</em></a></html>',
    )
    version = deployment.get_elastic_latest_version()
    assert version == "8.12.2"

    responses.add(responses.GET,
        'https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html',
        body='Error',
    )
    with pytest.raises(tectonic.deployment.DeploymentException):
        version = deployment.get_elastic_latest_version()