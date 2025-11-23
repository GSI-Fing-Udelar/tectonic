
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
import copy
from pathlib import Path
import yaml
from tectonic.description import DescriptionException, Description
from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS
from tectonic.utils import absolute_path


def test_description_endpoint(labs_path, tectonic_config):
    lab_edition_path = Path(labs_path) / "test.yml"
    description = Description(tectonic_config, lab_edition_path)
    
    # A description has the values of the scenario description file,
    # updated with lab edition values.
    description_dict = yaml.safe_load((Path(labs_path) /
                                       "test-endpoint" /
                                       "description.yml").read_text())
    base_lab = description_dict['lab_name']
    description_dict.update(yaml.safe_load(lab_edition_path.read_text()))
    description_dict['base_lab'] = base_lab

    description_attrs = [a for a in dir(description) if isinstance(getattr(description.__class__, a, None), property) and
                         (getattr(description.__class__, a).fset is not None)]

    for key in description_attrs:
        if key in description_dict.keys():
            if key in ['student_pubkey_dir', 'teacher_pubkey_dir']:
                assert str(getattr(description, key)) == absolute_path(description_dict[key],
                                                                       base_dir=description.lab_edition_dir)
            else:
                assert getattr(description, key) == description_dict[key]
    
    assert description.lab_edition_path == str(Path(labs_path) / 'test.yml')
    if tectonic_config.platform == "aws":
        assert isinstance(description.instance_type, InstanceTypeAWS)
    else:
        assert isinstance(description.instance_type, InstanceType)
    assert description.scenario_dir == str(Path(labs_path) / 'test-endpoint')
    assert description.ansible_dir == str(Path(labs_path) / 'test-endpoint' / 'ansible')

    # Test loaded teacher pubkeys
    teacher_pubkeys = ['ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAIEAteXWtSc03gZv1F6kV1rWdJOK0Y3bCuOhFX69BIvX39p1rCn0Sf9kt3nm+tBaGo52P7+TFMcmHh0hEMD1EtIXe6IoOJsjmMLE2UF4TZPrc+8Fp2BpnNDx73RvI76ui0JHvVyHsgpsWNEtDAzLGI7U1snwtZOy6aOQcvYzfJg2g2U= fzipi@picard',
                       'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsKA/F4zXu/rspUu1KNV+8foIgmj4+LP8Cf9BK5+NSkQvUCfTKnoObJdLKaIV2crzYYIowASSu1i9GCxCYnnZP9U75dV+c6iyh3l5aYbrKfIfgCVtuBjKNz1uRuZNEdZ7nADV/lTc5BI5jnhzTPzNW++jslaTu/xS4gZ7KWgE7NA7hOMjMfY/rxvCPQm7w919NpuZmzn0V7ubf6kONh+wQoubKCm8Gb2viX/GlYsSBP6xhP/YKkkLpaGDDTZ6e/OEU8X/OdqEJSgy5eJUhEjkCc1Dei32YRV6ldbiF8vQSs3Izcq7UkOkciEDbY0vZkoeggB9+UnAcrOJu1bt5A+LT jdcampo@japeto',
                       Path(tectonic_config.ssh_public_key_file).expanduser().read_text(),
                       ]
    for k in teacher_pubkeys:
        assert k in description.authorized_keys

    assert description.parameters_files == [str(Path(description.ansible_dir) / "parameters" / "flags.txt")]

def test_description_traffic(labs_path, tectonic_config):
    lab_edition_path = Path(labs_path) / "test-traffic.yml"
    description = Description(tectonic_config, lab_edition_path)
    if tectonic_config.platform == "aws":
        assert description.packetbeat.enable
    else:
        assert not description.packetbeat.enable

def test_description_package(labs_path, tectonic_config):
    lab_edition_path = Path(labs_path) / "test-package.yml"
    description = Description(tectonic_config, lab_edition_path)
    assert description.base_lab == 'packaged'

def test_description_invalid(labs_path, tectonic_config):
    lab_edition_path = Path(labs_path) / "notfound.yml"
    with pytest.raises(DescriptionException):
        Description(tectonic_config, lab_edition_path)

    lab_edition_path = Path(labs_path) / "no_base_lab.yml"
    with pytest.raises(DescriptionException):
        Description(tectonic_config, lab_edition_path)

    lab_edition_path = Path(labs_path) / "invalid_base_lab.yml"
    with pytest.raises(DescriptionException):
        Description(tectonic_config, lab_edition_path)

    lab_edition_path = Path(labs_path) / "no_description.yml"
    with pytest.raises(DescriptionException):
        Description(tectonic_config, lab_edition_path)

    lab_edition_path = Path(labs_path) / "invalid_topology.yml"
    with pytest.raises(DescriptionException):
        Description(tectonic_config, lab_edition_path)

def test_description_setters(description):
    description = copy.deepcopy(description)

    with pytest.raises(DescriptionException):
        description.base_lab = "$#()"
    with pytest.raises(DescriptionException):
        description.institution = "$#()"
    with pytest.raises(DescriptionException):
        description.lab_name = "$#()"

    description.teacher_pubkey_dir = None
    teacher_pubkeys = Path(description.config.ssh_public_key_file).expanduser().read_text()
    teacher_pubkeys += "\n"
    assert description.authorized_keys == teacher_pubkeys

    description.student_pubkey_dir = None
    assert not description.student_pubkey_dir
    


#############################
# Test parse_machines method
#############################

base_machines = [
    'udelar-lab01-1-attacker',
    'udelar-lab01-1-victim-1',
    'udelar-lab01-1-victim-2',
    'udelar-lab01-1-server',
    'udelar-lab01-2-attacker',
    'udelar-lab01-2-victim-1',
    'udelar-lab01-2-victim-2',
    'udelar-lab01-2-server',
]

def test_parse_machines_basic_only_instances(description):
    description = copy.deepcopy(description)

    description.elastic.enable = False
    description.caldera.enable = False
    machine_list = description.parse_machines()
    expected_machines = base_machines.copy()

    assert set(machine_list) == set(expected_machines)

def test_parse_machines_elastic_endpoint(description):
    description = copy.deepcopy(description)

    description.elastic.enable = True
    description.elastic.monitor_type = "endpoint"
    description.caldera.enable = False
    machine_list = description.parse_machines(only_instances=False)
    expected_machines = base_machines.copy() + [
        'udelar-lab01-elastic',
        'udelar-lab01-bastion_host'
    ]
    if description.config.platform == "aws":
        expected_machines.append('udelar-lab01-teacher_access_host')
    assert set(machine_list) == set(expected_machines)


def test_parse_machines_teacher_endpoint(description):
    description = copy.deepcopy(description)

    description.config.aws.teacher_access = "endpoint"
    description.elastic.enable = False
    description.caldera.enable = False
    description.guacamole.enable = False
    description.bastion_host.enable = False
    description.teacher_access_host.enable = False
    machine_list = description.parse_machines(only_instances=False)
    expected_machines = base_machines.copy()
    assert set(machine_list) == set(expected_machines)


def test_parse_machines_teacher_host(description):
    description = copy.deepcopy(description)

    description.config.aws.teacher_access = "host"
    description.elastic.enable = True
    description.caldera.enable = True
    description.guacamole.enable = True
    description.elastic.monitor_type = "traffic"
    machine_list = description.parse_machines(only_instances=False)
    expected_machines = base_machines.copy() + [
        'udelar-lab01-elastic',
        'udelar-lab01-caldera',
        'udelar-lab01-guacamole',
        'udelar-lab01-bastion_host'
    ]
    if description.config.platform == "aws":
        expected_machines += ['udelar-lab01-packetbeat', 'udelar-lab01-teacher_access_host']
    assert set(machine_list) == set(expected_machines)

def test_parse_machines_filter_guests_with_services(description):
    description = copy.deepcopy(description)

    description.config.aws.teacher_access = "host"
    description.elastic.enable = True
    description.caldera.enable = True
    description.elastic.monitor_type = "traffic"
    description.guacamole.enable = True
    machine_list = description.parse_machines(guests=["attacker"], only_instances=False)
    assert set(machine_list) == set([
        'udelar-lab01-1-attacker',
        'udelar-lab01-2-attacker',
    ])

def test_parse_machines_exclude_service(description):
    description = copy.deepcopy(description)
    description.bastion_host.enabe = True
    description.guacamole.enable = True
    description.caldera.enable = True
    if description.config.platform == "aws":
        description.bastion_host.enable = True
    machine_list = description.parse_machines(exclude=['elastic'], only_instances=False)
    expected_machines = base_machines.copy() + [
        'udelar-lab01-caldera',
        'udelar-lab01-guacamole',
        'udelar-lab01-bastion_host'
    ]
    if description.config.platform == "aws":
        expected_machines.append('udelar-lab01-teacher_access_host')
    assert set(machine_list) == set(expected_machines)

def test_parse_machines_services(description):
    description = copy.deepcopy(description)

    description.config.aws.teacher_access = "host"
    description.elastic.enable = True
    description.elastic.monitor_type = "traffic"
    description.caldera.enable = True
    description.guacamole.enable = True
    machine_list = description.parse_machines(only_instances=False)
    expected_machines = base_machines.copy() + [
        'udelar-lab01-elastic',
        'udelar-lab01-caldera',
        'udelar-lab01-guacamole',
        'udelar-lab01-bastion_host',
    ]
    if description.config.platform == "aws":
        expected_machines += [
            'udelar-lab01-packetbeat', 
            'udelar-lab01-teacher_access_host'  
        ]
    assert set(machine_list) == set(expected_machines)

def test_parse_machines_filter_instances(description):
    description = copy.deepcopy(description)

    machine_list = description.parse_machines(instances=[1], guests=None)
    assert set(machine_list) == set([
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-victim-2',
        'udelar-lab01-1-server',
    ])

def test_parse_machines_filter_guests(description):
    description = copy.deepcopy(description)

    machine_list = description.parse_machines(guests=["victim", "server"])
    assert set(machine_list) == set([
        'udelar-lab01-1-victim-1', 
        'udelar-lab01-1-victim-2', 
        'udelar-lab01-1-server',
        'udelar-lab01-2-victim-1', 
        'udelar-lab01-2-victim-2', 
        'udelar-lab01-2-server',
    ])

def test_parse_machines_filter_copies_1(description):
    description = copy.deepcopy(description)

    machine_list = description.parse_machines(copies=[1])
    assert set(machine_list) == set([
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-server',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
        'udelar-lab01-2-server',
    ])

def test_parse_machines_filter_copies_2(description):
    description = copy.deepcopy(description)

    machine_list = description.parse_machines(copies=[2])
    assert set(machine_list) == set([
        'udelar-lab01-1-victim-2',
        'udelar-lab01-2-victim-2',
    ])

def test_parse_machines_filter_guests_and_copies_attacker(description):
    description = copy.deepcopy(description)

    machine_list = description.parse_machines(guests=["attacker",], copies=[1])
    assert set(machine_list) == set([
        'udelar-lab01-1-attacker',
        'udelar-lab01-2-attacker',
    ])

def test_parse_machines_filter_guests_and_copies_attacker_victim(description):
    description = copy.deepcopy(description)

    machine_list = description.parse_machines(guests=["attacker", "victim"], copies=[1])
    assert set(machine_list) == set([
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
    ])

def test_parse_machines_filter_guests_and_copies_2(description):
    description = copy.deepcopy(description)

    machine_list = description.parse_machines(guests=["attacker", "victim"], copies=[2])
    assert set(machine_list) == set([
        'udelar-lab01-1-victim-2',
        'udelar-lab01-2-victim-2',
    ])

def test_parse_machines_exclude_guests(description):
    description = copy.deepcopy(description)

    machine_list = description.parse_machines(exclude=["attacker", "victim"])
    assert set(machine_list) == set([
        'udelar-lab01-1-server',
        'udelar-lab01-2-server',
    ])

def test_parse_machines_invalid(description):
    description = copy.deepcopy(description)

    with pytest.raises(DescriptionException):
        description.parse_machines(instances=[2,3,1])
    with pytest.raises(DescriptionException):
        description.parse_machines(guests=["attacker", "invalid"])
    with pytest.raises(DescriptionException):
        description.parse_machines(copies=[2,1,3])
    with pytest.raises(DescriptionException):
        description.parse_machines(guests=["attacker",], copies=[1,2])
    with pytest.raises(DescriptionException):
        description.parse_machines(guests=["attacker",], exclude=["attacker"])


def test_generate_student_access_credentials(description):
    description = copy.deepcopy(description)

    users = description.generate_student_access_credentials()

    usernames = ['student1', 'student2']
    assert set(users.keys()) == set(usernames)

    for _, u in users.items():
        assert 'password' in u
        assert 'password_hash' in u
        assert 'authorized_keys' in u

def test_generate_student_access_credentials_only_pubkeys(description):
    description = copy.deepcopy(description)

    description.create_students_passwords = False
    users = description.generate_student_access_credentials()
    usernames = ['student1', 'student2']
    assert set(users.keys()) == set(usernames)

    for _, u in users.items():
        assert 'password' not in u
        assert 'password_hash' not in u
        assert 'authorized_keys' in u

def test_generate_student_access_credentials_no_pubkeys(description):
    description = copy.deepcopy(description)

    description.student_pubkey_dir = None
    users = description.generate_student_access_credentials()
    usernames = ['student1', 'student2']
    assert set(users.keys()) == set(usernames)
    
    for _, u in users.items():
        assert 'password' in u
        assert 'password_hash' in u
        assert 'authorized_keys' not in u

def test_get_parameters(description):
    description = copy.deepcopy(description)
      
    flags = [
        "Flag 1",
        "Flag 2",
        "Flag 3",
        "Flag 4",
        "Flag 5",
    ]

    params = description.get_parameters()
    for instance in [1,2]:
        assert params[instance]['flags'] in flags

    params = description.get_parameters(instances=[2])
    assert 1 not in params
    assert params[2]['flags'] in flags
