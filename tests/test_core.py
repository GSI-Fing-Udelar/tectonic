
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
import builtins
import datetime
from unittest.mock import MagicMock, patch
from tectonic.core import Core, CoreException


import tectonic.terraform_aws
import tectonic.terraform_libvirt
import tectonic.terraform_docker
import tectonic.terraform_service_aws
import tectonic.terraform_service_libvirt
import tectonic.terraform_service_docker
import tectonic.client_aws
import tectonic.client_libvirt
import tectonic.client_docker
import tectonic.packer_aws
import tectonic.packer_libvirt
import tectonic.packer_docker
import tectonic.ansible


def test_core_init(description):
    core = Core(description)
    assert isinstance(core, Core)
    if description.config.platform == "aws":
        assert isinstance(core.client, tectonic.client_aws.ClientAWS)
        assert isinstance(core.terraform, tectonic.terraform_aws.TerraformAWS)
        assert isinstance(core.packer, tectonic.packer_aws.PackerAWS)
        assert isinstance(core.terraform_service, tectonic.terraform_service_aws.TerraformServiceAWS)
    elif description.config.platform == "libvirt":
        assert isinstance(core.client, tectonic.client_libvirt.ClientLibvirt)
        assert isinstance(core.terraform, tectonic.terraform_libvirt.TerraformLibvirt)
        assert isinstance(core.packer, tectonic.packer_libvirt.PackerLibvirt)
        assert isinstance(core.terraform_service, tectonic.terraform_service_libvirt.TerraformServiceLibvirt)
    elif description.config.platform == "docker":
        assert isinstance(core.client, tectonic.client_docker.ClientDocker)
        assert isinstance(core.terraform, tectonic.terraform_docker.TerraformDocker)
        assert isinstance(core.packer, tectonic.packer_docker.PackerDocker)
        assert isinstance(core.terraform_service, tectonic.terraform_service_docker.TerraformServiceDocker)
    assert isinstance(core.ansible, tectonic.ansible.Ansible)

def test_core_init_invalid_platform(description):
    platform = description.config.platform

    description.config._platform = "unknown"
    with pytest.raises(CoreException):
        Core(description)

    description.config.platform = platform

def test_create_instances_images(core):
    core.packer.destroy_instance_image = MagicMock()
    core.packer.create_instance_image = MagicMock()
    core.create_instances_images(["guest1"])
    core.packer.destroy_instance_image.assert_called_once()
    core.packer.create_instance_image.assert_called_once()

    core.packer.destroy_instance_image.reset_mock()
    core.packer.create_instance_image.reset_mock()

    core.create_instances_images([])
    core.packer.destroy_instance_image.assert_not_called()
    core.packer.create_instance_image.assert_not_called()
    


def test_create_services_images(core):
    core.packer.destroy_service_image = MagicMock()
    core.packer.create_service_image = MagicMock()
    core.create_services_images(["svc"])
    core.packer.destroy_service_image.assert_called_once()
    core.packer.create_service_image.assert_called_once()

    core.packer.destroy_service_image.reset_mock()
    core.packer.create_service_image.reset_mock()

    core.create_services_images([])
    core.packer.destroy_service_image.assert_not_called()
    core.packer.create_service_image.assert_not_called()


def test_deploy(core):
    core.create_instances_images = MagicMock()
    core.create_services_images = MagicMock()
    core.terraform.deploy = MagicMock()
    core.terraform_service.deploy = MagicMock()
    core.ansible.configure_services = MagicMock()
    core.ansible.wait_for_connections = MagicMock()
    core.ansible.run = MagicMock()
    core.configure_access = MagicMock(return_value={})
    core.description.elastic.enable = True
    core.description.elastic.monitor_type = "traffic"
    core.description.caldera.enable = True
    core.description.guacamole.enable = True
    core.description.moodle.enable = True
    core.description.bastion_host.enable = True
    core.terraform_service.deploy_packetbeat = MagicMock()
    core.terraform_service.install_elastic_agent = MagicMock()
    core.terraform_service.install_caldera_agent = MagicMock()

    core.deploy([1], True, [])

    core.ansible.wait_for_connections.assert_called_once()
    core.ansible.run.assert_called_once()
    core.configure_access.assert_called_once()


def test_destroy(core):
    core.terraform.destroy = MagicMock()
    core.ansible.run = MagicMock()
    core.terraform_service.destroy = MagicMock()
    core.packer.destroy_instance_image = MagicMock()
    core.packer.destroy_service_image = MagicMock()
    core.description.elastic.enable = True
    core.description.elastic.monitor_type = "traffic"
    core.description._base_guests = {"guest": MagicMock(base_name="g", entry_point=True)}
    core.description.caldera.enable = True
    core.description.guacamole.enable = True
    core.description.moodle.enable = True
    core.description.bastion_host.enable = True


    core.destroy(None, False, True, ["svc"])

    core.terraform.destroy.assert_called()
    core.terraform_service.destroy.assert_called()


def test_recreate(core):
    core.terraform.recreate = MagicMock()
    core.ansible.wait_for_connections = MagicMock()
    core.ansible.run = MagicMock()
    core.configure_access = MagicMock()
    core.description.elastic.enable = True
    core.description.elastic.monitor_type = "endpoint"
    core.description.caldera.enable = True
    core.description.guacamole.enable = True
    core.description.moodle.enable = True
    core.description.bastion_host.enable = True
    core.terraform_service.install_elastic_agent = MagicMock()
    core.terraform_service.install_caldera_agent = MagicMock()

    core.recreate([1], ["g"], [1])
    core.terraform.recreate.assert_called_once()


def test_start_stop_restart(core):
    core.description.parse_machines = MagicMock(return_value=["m1"])
    core.client.start_machine = MagicMock()
    core.client.stop_machine = MagicMock()
    core.client.restart_machine = MagicMock()
    core.description.elastic.enable = True
    core.description.elastic.monitor_type = "traffic"
    core.terraform_service.manage_packetbeat = MagicMock()

    core.start([1], ["g"], [1])
    core.start([1], ["g"], [1])
    core.stop([1], ["g"], [1])
    core.stop([1], ["g"], [1])
    core.restart([1], ["g"], [1])
    core.restart([1], ["g"], [1])

    core.client.start_machine.assert_any_call("m1")
    core.client.stop_machine.assert_any_call("m1")
    core.client.restart_machine.assert_any_call("m1")


def test_info(core):
    core.client.get_machine_public_ip = MagicMock(return_value="1.2.3.4")
    svc = MagicMock()
    svc.base_name = "svc"
    svc.service_ip = "ip"
    svc.port = 1234
    core.description.elastic.enabled = True
    core.description.caldera.enabled = True
    core.description.guacamole.enable = True
    core.description.moodle.enable = True
    core.description.bastion_host.enable = True
    core.terraform_service.get_service_credentials = MagicMock(return_value="creds")
    core._get_students_passwords = MagicMock(return_value={"u": "p"})

    info = core.info()
    assert "instances_info" in info
    assert "services_info" in info
    assert "student_access_password" in info


@pytest.mark.parametrize('monitor_type', ['traffic', 'endpoint'])
def test_list_instances_with_elastic(core, monitor_type):
    core.client.get_machine_status = MagicMock(return_value="running")
    core.description.elastic.enable = True
    core.description.elastic.monitor_type = monitor_type
    core.description.caldera.enable = False
    core.terraform_service.manage_packetbeat = MagicMock(return_value="ok")
    agents_status = {'last_seen': '2024-12-10T09:36:24Z', 'sleep_min': '3', 'sleep_max': '3', 'watchdog': '1'}
    core.terraform_service.get_service_info =  MagicMock(return_value=[{'agents_status': agents_status}])

    status = core.list_instances([1], ["attacker"], [1])

    assert "instances_info" in status
    assert "services_status" in status

def test_list_instances_with_caldera(core):
    core.description.elastic.enable = False
    core.description.caldera.enable = True
    last_seen = (datetime.datetime.now() - datetime.timedelta(seconds=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    agents_status = [
        {'last_seen': last_seen, 'sleep_min': 3, 'sleep_max': 3, 'watchdog': 1},
        {'last_seen': '2025-10-24T06:13:10Z', 'sleep_min': 1, 'sleep_max': 2, 'watchdog': 5},
    ]
    core.terraform_service.get_service_info =  MagicMock(return_value=[{'agents_status': agents_status}])

    status = core.list_instances([1], ["attacker"], [1])
    assert "instances_info" in status
    assert "services_status" in status
    

def test_get_parameters_without_directory(core):
    core.description.parse_machines = MagicMock()
    core.description.get_parameters = MagicMock(return_value={"a": 1})
    result = core.get_parameters([1])
    assert result == {"a": 1}


def test_get_parameters_with_directory(core, tmp_path):
    core.description.parse_machines = MagicMock()
    core.description.get_parameters = MagicMock(return_value={"a": 1})
    directory = tmp_path / "params"
    result = core.get_parameters([1], str(directory))
    assert "Parameters file created" in result


def test_run_automation(core):
    core.description.parse_machines = MagicMock()
    core.ansible.run = MagicMock()
    core.run_automation([1], ["g"], [1], "u", "play.yml")
    core.ansible.run.assert_called_once()


def test_console(core):
    print(f"guests: {core.description.scenario_guests}")
    core.description.parse_machines = MagicMock(return_value=["udelar-lab01-1-attacker"])
    core.description.caldera.enable = True
    core.client.console = MagicMock()
    core.console(1, "g", 1)
    core.client.console.assert_called_once()


def test_console_invalid(core):
    core.description.parse_machines = MagicMock(return_value=["m1", "m2"])
    with pytest.raises(CoreException):
        core.console(1, "g", 1)


def test_configure_access(core):
    core.description._base_guests = {"g": MagicMock(base_name="g", entry_point=True)}
    core.description.guacamole.enable = True
    core.terraform_service.get_service_credentials = MagicMock(return_value={"trainer": "password"})
    core.description.generate_student_access_credentials = MagicMock(return_value={"u": {"password": "p"}})
    core.ansible.run = MagicMock()
    users = core.configure_access([1])
    assert "u" in users


def test_get_students_passwords(core):
    core.description.create_students_passwords = True
    core.description.generate_student_access_credentials = MagicMock(return_value={"u": {"password": "p"}})
    pwds = core._get_students_passwords()
    assert pwds == {"u": "p"}

    core.description.create_students_passwords = False
    core.description.moodle.enable = False
    assert core._get_students_passwords() == {}
















