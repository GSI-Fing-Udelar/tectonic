
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

import logging

import re
from pathlib import Path

import libvirt_qemu
import pytest
import ansible_runner

from tectonic.libvirt_client import Client as LibvirtClient
from tectonic.aws import Client as AWSClient
import tectonic.ansible

def test_ansible_callback_appends_output_test(ansible_libvirt):
    event = {'stdout': "my text"}
    ret = ansible_libvirt._ansible_callback(event_data=event)
    assert ret is True
    assert ansible_libvirt.output == "\nmy text"

    event2 = {'stdout': "more text"}
    ret2 = ansible_libvirt._ansible_callback(event_data=event2)
    assert ret2 is True
    assert ansible_libvirt.output == "\nmy text\nmore text"

    event3 = {'stdout': ""}
    ret3 = ansible_libvirt._ansible_callback(event_data=event3)
    assert ret3 is True
    assert ansible_libvirt.output == "\nmy text\nmore text"

def test_build_empty_inventory(ansible_libvirt):
    inventory = ansible_libvirt.build_inventory(machine_list=None)
    assert inventory == {}


def test_build_inventory_libvirt(mocker, ansible_libvirt):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    assert isinstance(ansible_libvirt.deployment.client, LibvirtClient) is True

    inventory = ansible_libvirt.build_inventory(machine_list=["udelar-lab01-1-attacker",
                                                              "udelar-lab01-2-attacker",
                                                              "udelar-lab01-2-victim"],
                                                extra_vars={"extra_var": "extra_value"})
    assert inventory["attacker"]["vars"]["ansible_become"] == True
    assert inventory["attacker"]["vars"]["basename"] == "attacker"
    assert inventory["attacker"]["vars"]["instances"] == 2
    assert inventory["attacker"]["vars"]["extra_var"] == "extra_value"

    assert inventory["attacker"]["hosts"]["udelar-lab01-1-attacker"]["ansible_host"] == "10.0.1.25"
    assert inventory["attacker"]["hosts"]["udelar-lab01-1-attacker"]["ansible_user"] == "ubuntu"
    assert (inventory["attacker"]["hosts"]["udelar-lab01-1-attacker"]["ansible_ssh_common_args"] ==
            "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no")
    assert inventory["attacker"]["hosts"]["udelar-lab01-1-attacker"]["instance"] == 1
    assert inventory["attacker"]["hosts"]["udelar-lab01-1-attacker"]["copy"] == 1
    assert inventory["attacker"]["hosts"]["udelar-lab01-1-attacker"]["become_flags"] == "-i"
    assert inventory["attacker"]["hosts"]["udelar-lab01-2-attacker"]["instance"] == 2
    assert inventory["attacker"]["hosts"]["udelar-lab01-2-attacker"]["copy"] == 1

    # Test windows victim
    assert inventory["victim"]["vars"]["ansible_become"] == True
    assert inventory["victim"]["vars"]["basename"] == "victim"
    assert inventory["victim"]["vars"]["instances"] == 2
    assert inventory["victim"]["vars"]["extra_var"] == "extra_value"
    assert inventory["victim"]["hosts"]["udelar-lab01-2-victim"]["instance"] == 2
    assert inventory["victim"]["hosts"]["udelar-lab01-2-victim"]["copy"] == 1
    assert inventory["victim"]["hosts"]["udelar-lab01-2-victim"]["ansible_shell_type"] == "powershell"
    assert inventory["victim"]["hosts"]["udelar-lab01-2-victim"]["ansible_become_method"] == "runas"
    assert inventory["victim"]["hosts"]["udelar-lab01-2-victim"]["ansible_become_user"] == "administrator"


def test_build_inventory_aws(ansible_aws, ec2_client, aws_secrets):
    assert isinstance(ansible_aws.deployment.client, AWSClient) is True

    # Test host teacher_access
    inventory = ansible_aws.build_inventory(machine_list=["udelar-lab01-student_access"])
    assert inventory["student_access"]["hosts"]["udelar-lab01-student_access"]["ansible_host"] == "10.0.0.29"
    assert inventory["student_access"]["hosts"]["udelar-lab01-student_access"]["ansible_user"] == "ubuntu"
    assert re.match(r"-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ProxyCommand=\"ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -W %h:%p ubuntu@\d+\.\d+.\d+.\d+\"",
                    inventory["student_access"]["hosts"]["udelar-lab01-student_access"]["ansible_ssh_common_args"])

    # Test endpoint teacher_access
    ansible_aws.deployment.description.teacher_access = "endpoint"
    inventory = ansible_aws.build_inventory(machine_list=["udelar-lab01-1-attacker"])
    # ansible_host should be an AWS instance ID
    assert re.match(r"i-[0-9a-f]{17}",
                    inventory["attacker"]["hosts"]["udelar-lab01-1-attacker"]["ansible_host"])
    assert (inventory["attacker"]["hosts"]["udelar-lab01-1-attacker"]["ansible_ssh_common_args"] ==
            '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ProxyCommand="aws ec2-instance-connect open-tunnel --instance-id %h"'
            )
    ansible_aws.deployment.description.teacher_access = "host"


def test_run_libvirt(mocker, capsys, ansible_libvirt, test_data_path):
    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    inventory = {
        "udelar": {
            "vars": {
                "var1": "value1",
            },
            "hosts": {
                "host1": {},
                "host2": {}
            }
        }
    }

    ansible_libvirt.run(inventory=inventory)
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=f"{test_data_path}/labs/test-endpoint/ansible/after_clone.yml",
                                 quiet=False,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not ansible_libvirt.deployment.description.keep_ansible_logs }
                                )

    # Test non-existent default playbook path
    mock.reset_mock()
    old_path = ansible_libvirt.deployment.description.ansible_playbooks_path
    ansible_libvirt.deployment.description.ansible_playbooks_path = "/not/found"
    ansible_libvirt.run(inventory=inventory)
    mock.assert_not_called()
    assert "No playbook to run" in capsys.readouterr().out
    
    ansible_libvirt.run(inventory=inventory, quiet=True)
    mock.assert_not_called()
    assert capsys.readouterr().out == ""

    ansible_libvirt.deployment.description.ansible_playbooks_path = old_path

def test_run_custom_playbook(mocker, ansible_libvirt):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    machine_list = ansible_libvirt.deployment.description.parse_machines()
    inventory = ansible_libvirt.build_inventory(machine_list=machine_list)

    custom_playbook = Path("some_playbook.yml").resolve().as_posix()
    ansible_libvirt.run(playbook=custom_playbook)
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=custom_playbook,
                                 quiet=False,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not ansible_libvirt.deployment.description.keep_ansible_logs }
                                )


def test_run_error(mocker, ansible_libvirt):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result = ansible_runner.Runner(config=None)
    result.rc = 1
    result.status = "error"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    # No exception if quiet is False
    ansible_libvirt.run()
    assert True

    # Rise exception if quiet is True
    with pytest.raises(tectonic.ansible.AnsibleException) as exception:
        ansible_libvirt.run(quiet=True)

def test_wait_for_connections(mocker, ansible_libvirt, ansible_path):
    mocker.patch.object(libvirt_qemu, "qemuAgentCommand", return_value='{"return": {"ping": "pong"}}')

    result = ansible_runner.Runner(config=None)
    result.rc = 0
    result.status = "successful"
    mock = mocker.patch.object(ansible_runner.interface, "run", return_value=result)

    machine_list = ansible_libvirt.deployment.description.parse_machines()
    inventory = ansible_libvirt.build_inventory(machine_list)

    ansible_libvirt.wait_for_connections()
    mock.assert_called_once_with(inventory=inventory,
                                 playbook=f"{ansible_path}/wait_for_connection.yml",
                                 quiet=True,
                                 verbosity=0,
                                 event_handler=mocker.ANY,
                                 extravars={"ansible_no_target_syslog" : not ansible_libvirt.deployment.description.keep_ansible_logs }
                                )