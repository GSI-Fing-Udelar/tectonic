
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

from tectonic.description import DescriptionException, Description
from tectonic.config import TectonicConfig
from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS


def test_description():
    config = TectonicConfig.load("./tectonic.ini")
    if config.platform == "aws":
        instance_type = InstanceTypeAWS()
    else:
        instance_type = InstanceType()
    description = Description(config, instance_type, config.tectonic_dir+"/examples/password_cracking.yml")



# def test_description(description):
#     assert description.aws_region == "us-east-1"
#     assert description.aws_default_instance_type == "t2.micro"


# def test_read_pubkeys(description, tmp_path_factory):
#     pubkey="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsKA/F4zXu/rspUu1KNV+8foIgmj4+LP8Cf9BK5+NSkQvUCfTKnoObJdLKaIV2crzYYIowASSu1i9GCxCYnnZP9U75dV+c6iyh3l5aYbrKfIfgCVtuBjKNz1uRuZNEdZ7nADV/lTc5BI5jnhzTPzNW++jslaTu/xS4gZ7KWgE7NA7hOMjMfY/rxvCPQm7w919NpuZmzn0V7ubf6kONh+wQoubKCm8Gb2viX/GlYsSBP6xhP/YKkkLpaGDDTZ6e/OEU8X/OdqEJSgy5eJUhEjkCc1Dei32YRV6ldbiF8vPSs3Izcq7UkOkciEDbY0vZkoeggB9+UnAcrOJu1bt5A+LT test"
#     pubkey_file = tmp_path_factory.mktemp('pubkey') / "id_rsa.pub"
#     pubkey_file.write_text(pubkey)

#     read_keys = description.read_pubkeys(ssh_dir=None, default_pubkey=pubkey_file.resolve().as_posix())
#     assert read_keys == pubkey + "\n"
    
#     pubkey_file.write_text(pubkey+"\n")
    
#     read_keys = description.read_pubkeys(ssh_dir=None, default_pubkey=pubkey_file.resolve().as_posix())
#     assert read_keys == pubkey + "\n"

#     read_keys = description.read_pubkeys(ssh_dir=None, default_pubkey=None)
#     assert read_keys == ""


# def test_get_guest_attr(description):
#     assert description.get_guest_attr("attacker", "vcpu") == 2
#     assert description.get_guest_attr("victim", "memory") == 1024
#     assert description.get_guest_attr("victim", "monitor") == True


# def test_get_guest_username(description):
#     username = description.get_guest_username("lab1")
#     assert username == "ubuntu"


# def test_get_guest_username_not_found(description):
#     """ Test that an exception is raised when the guest username is not found """
#     old_default_os = description.default_os
#     description.default_os = "windows_1234"
#     with pytest.raises(DescriptionException):
#         description.get_guest_username("lab2")
#     description.default_os = old_default_os

# def test_authorized_keys(description):
#     """ Test that the authorized_pubkeys read are correct"""
#     authorized_keys = description.authorized_keys
#     for k in ["ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAIEAteXWtSc03gZv1F6kV1rWdJOK0Y3bCuOhFX69BIvX39p1rCn0Sf9kt3nm+tBaGo52P7+TFMcmHh0hEMD1EtIXe6IoOJsjmMLE2UF4TZPrc+8Fp2BpnNDx73RvI76ui0JHvVyHsgpsWNEtDAzLGI7U1snwtZOy6aOQcvYzfJg2g2U= fzipi@picard",
#               "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsKA/F4zXu/rspUu1KNV+8foIgmj4+LP8Cf9BK5+NSkQvUCfTKnoObJdLKaIV2crzYYIowASSu1i9GCxCYnnZP9U75dV+c6iyh3l5aYbrKfIfgCVtuBjKNz1uRuZNEdZ7nADV/lTc5BI5jnhzTPzNW++jslaTu/xS4gZ7KWgE7NA7hOMjMfY/rxvCPQm7w919NpuZmzn0V7ubf6kONh+wQoubKCm8Gb2viX/GlYsSBP6xhP/YKkkLpaGDDTZ6e/OEU8X/OdqEJSgy5eJUhEjkCc1Dei32YRV6ldbiF8vQSs3Izcq7UkOkciEDbY0vZkoeggB9+UnAcrOJu1bt5A+LT jdcampo@japeto"
#               ]:
#         assert k in authorized_keys

# def test_get_copy_range(description):
#     copy_range = description.get_copy_range("attacker")
#     assert list(copy_range) == [1]
#     copy_range = description.get_copy_range("victim")
#     assert list(copy_range) == [1, 2]

# def test_get_image_name(description):
#     image_name = description.get_image_name("attacker")
#     assert image_name == "udelar-lab01-attacker"

# def test_get_instance_name(description):
#     instance_name = description.get_instance_name(2, "attacker")
#     assert instance_name == "udelar-lab01-2-attacker"
#     instance_name = description.get_instance_name(1, "victim", 2)
#     assert instance_name == "udelar-lab01-1-victim-2"

# def test_get_hostname(description):
#     instance_name = description.get_hostname(2, "attacker")
#     assert instance_name == "attacker-2"
#     instance_name = description.get_hostname(1, "victim", 2)
#     assert instance_name == "victim-1-2"

# def test_get_instance_number(description):
#     instance_number = description.get_instance_number("udelar-lab01-2-attacker")
#     assert instance_number == 2
#     instance_number = description.get_instance_number("udelar-lab01-1-victim-2")
#     assert instance_number == 1
#     instance_number = description.get_instance_number("udelar-lab01-student_access")
#     assert instance_number is None

# def test_get_base_name(description):
#     base_name = description.get_base_name("udelar-lab01-2-attacker")
#     assert base_name == "attacker"
#     base_name = description.get_base_name("udelar-lab01-1-victim-2")
#     assert base_name == "victim"
#     base_name = description.get_base_name("udelar-lab01-student_access")
#     assert base_name == "student_access"
#     base_name = description.get_base_name("broken-name")
#     assert base_name is None


# def test_get_copy(description):
#     copy = description.get_copy("udelar-lab01-2-attacker")
#     assert copy == 1
#     copy = description.get_copy("udelar-lab01-1-victim-2")
#     assert copy == 2
#     copy = description.get_copy("udelar-lab01-student_access")
#     assert copy == 1

# def test_get_student_access_name(description):
#     student_access_name = description.get_student_access_name()
#     assert student_access_name == "udelar-lab01-student_access"

# def test_get_teacher_access_name(description):
#     teacher_access_name = description.get_teacher_access_name()
#     assert teacher_access_name == "udelar-lab01-teacher_access"

# def test_get_service_name(description):
#     assert description.get_service_name("elastic") == "udelar-lab01-elastic"
#     assert description.get_service_name("packetbeat") == "udelar-lab01-packetbeat"
#     assert description.get_service_name("caldera") == "udelar-lab01-caldera"

# def test_get_services_to_deploy(description):
#     description.deploy_caldera = True
#     description.deploy_elastic = True
#     assert description.get_services_to_deploy() == ["elastic", "caldera"]
#     description.deploy_caldera = False
#     assert description.get_services_to_deploy() == ["elastic"]
#     description.deploy_elastic = False
#     assert description.get_services_to_deploy() == []
#     description.deploy_caldera = True
#     assert description.get_services_to_deploy() == ["caldera"]
#     description.deploy_elastic = True

def test_parse_machines(description):
    description.deploy_elastic=False
    description.deploy_caldera=False
    machine_list = description.parse_machines()
    expected_machines = [
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-victim-2',
        'udelar-lab01-1-server',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
        'udelar-lab01-2-victim-2',
        'udelar-lab01-2-server',
    ]
    assert set(machine_list) == set(expected_machines)

    description.elastic.enable = True
    description.elastic.monitor_type = "endpoint"
    description.caldera.enable = True
    machine_list = description.parse_machines(only_instances=False)
    expected_machines = [
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-victim-2',
        'udelar-lab01-1-server',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
        'udelar-lab01-2-victim-2',
        'udelar-lab01-2-server',
        'udelar-lab01-elastic',
        'udelar-lab01-caldera',
    ]
    if description.config.platform == "aws":
        expected_machines += ['udelar-lab01-student_access',
                              'udelar-lab01-teacher_access']
    assert set(machine_list) == set(expected_machines)
    
    description.config.aws.teacher_access = "endpoint"
    description.elastic.enable = False
    description.caldera.enable = False
    machine_list = description.parse_machines(only_instances=False)
    expected_machines = [
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-victim-2',
        'udelar-lab01-1-server',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
        'udelar-lab01-2-victim-2',
        'udelar-lab01-2-server',
    ]
    if description.config.platform == "aws":
        expected_machines += ['udelar-lab01-student_access']
    assert set(machine_list) == set(expected_machines)

    description.config.aws.teacher_access = "host"
    description.elastic.enable = True
    description.caldera.enable = True
    description.elastic.monitor_type = "traffic"
    machine_list = description.parse_machines(only_instances=False)
    expected_machines = [
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-victim-2',
        'udelar-lab01-1-server',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
        'udelar-lab01-2-victim-2',
        'udelar-lab01-2-server',
        'udelar-lab01-elastic',
        'udelar-lab01-caldera',
    ]
    if description.config.platform == "aws":
        expected_machines += ['udelar-lab01-student_access',
                              'udelar-lab01-teacher_access']
    assert set(machine_list) == set(expected_machines)

    description.config.aws.teacher_access = "host"
    description.elastic.enable = True
    description.elastic.monitor_type = "traffic"
    description.caldera.enable = True
    machine_list = description.parse_machines(only_instances=False)
    expected_machines == [
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-victim-2',
        'udelar-lab01-1-server',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
        'udelar-lab01-2-victim-2',
        'udelar-lab01-2-server',
        'udelar-lab01-elastic',
        'udelar-lab01-packetbeat',
        'udelar-lab01-caldera',
    ]
    if description.config.platform == "aws":
        expected_machines += [ 'udelar-lab01-student_access',
                               'udelar-lab01-teacher_access']
    assert set(machine_list) == set(expected_machines)

    machine_list = description.parse_machines(instances=[1], guests=None)
    assert machine_list == [
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-victim-2',
        'udelar-lab01-1-server',
    ]
    machine_list = description.parse_machines(guests=["victim", "server"])
    assert machine_list == [
        'udelar-lab01-1-victim-1', 
        'udelar-lab01-1-victim-2', 
        'udelar-lab01-1-server',
        'udelar-lab01-2-victim-1', 
        'udelar-lab01-2-victim-2', 
        'udelar-lab01-2-server',
    ]
    machine_list = description.parse_machines(copies=[1])
    assert machine_list == [
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-1-server',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
        'udelar-lab01-2-server',
    ]
    machine_list = description.parse_machines(copies=[2])
    assert machine_list == [
        'udelar-lab01-1-victim-2',
        'udelar-lab01-2-victim-2',
    ]
    machine_list = description.parse_machines(guests=["attacker",], copies=[1])
    assert machine_list == [
        'udelar-lab01-1-attacker',
        'udelar-lab01-2-attacker',
    ]
    machine_list = description.parse_machines(guests=["attacker", "victim"], copies=[1])
    assert machine_list == [
        'udelar-lab01-1-attacker',
        'udelar-lab01-1-victim-1',
        'udelar-lab01-2-attacker',
        'udelar-lab01-2-victim-1',
    ]
    machine_list = description.parse_machines(guests=["attacker", "victim"], copies=[2])
    assert machine_list == [
        'udelar-lab01-1-victim-2',
        'udelar-lab01-2-victim-2',
    ]

    with pytest.raises(DescriptionException):
        description.parse_machines(instances=[2,3,1])
    with pytest.raises(DescriptionException):
        description.parse_machines(guests=["attacker", "invalid"])
    with pytest.raises(DescriptionException):
        description.parse_machines(copies=[2,1,3])
    with pytest.raises(DescriptionException):
        description.parse_machines(guests=["attacker",], copies=[1,2])

# def test_get_machines_to_monitor(description):
#     machines_to_monitor = description.get_machines_to_monitor()
#     assert set(machines_to_monitor) == set(["victim", "server"])

# def test_get_red_team_machines(description):
#     assert set(description.get_red_team_machines()) == set(["attacker"])

# def test_get_blue_team_machines(description):
#     assert set(description.get_blue_team_machines()) == set(["victim", "server"])

# def test_get_guest_networks(description):
#     guest_networks = description.get_guest_networks("server")
#     assert guest_networks == ["internal", "dmz"]
#     guest_networks = description.get_guest_networks("victim")
#     assert guest_networks == ["internal"]

# def test_is_internet_access(description):
#     description.guest_settings["server"]["internet_access"] = True
#     assert description.is_internet_access()
#     del description.guest_settings["server"]["internet_access"]
#     assert not description.is_internet_access()

# def test_is_in_service_network(description):
#     assert True == description.is_in_services_network("attacker")
#     description.deploy_elastic = False
#     description.deploy_caldera = False
#     assert False == description.is_in_services_network("attacker")
#     description.deploy_elastic = True
#     description.monitor_type = "traffic"
#     assert False == description.is_in_services_network("attacker")
#     assert False == description.is_in_services_network("victim")
#     description.deploy_elastic = True
#     description.monitor_type = "endpoint"
#     assert False == description.is_in_services_network("attacker")
#     assert True == description.is_in_services_network("victim")
#     description.deploy_elastic = False
#     description.deploy_caldera = True
#     assert True == description.is_in_services_network("attacker")
#     assert True == description.is_in_services_network("victim")
#     description.deploy_elastic = True
#     description.deploy_caldera = True

# def test_get_topology_network(description):
#     internal_network = description.get_topology_network("internal")
#     assert internal_network["name"] == "internal"
#     assert set(internal_network["members"]) == set(["attacker", "victim", "server"])
#     dmz_network = description.get_topology_network("dmz")
#     assert dmz_network["name"] == "dmz"
#     assert set(dmz_network["members"]) == set(["server"])
#     none_network = description.get_topology_network("notfound")
#     assert none_network is None

# def test_get_instance_ip_address(description):
#     internal_network = description.get_topology_network("internal")
#     dmz_network = description.get_topology_network("dmz")
#     ipaddr = description.get_instance_ip_address(1, "attacker", 1, internal_network)
#     assert str(ipaddr) == "10.0.1.4"
#     ipaddr = description.get_instance_ip_address(2, "victim", 2, internal_network)
#     assert str(ipaddr) == "10.0.2.6"
#     ipaddr = description.get_instance_ip_address(1, "server", 1, dmz_network)
#     assert str(ipaddr) == "10.0.1.132"

# def test_get_guest_data(description):
#     description.monitor_type = "traffic"
#     guest_data = description.get_guest_data()

#     assert guest_data["udelar-lab01-1-attacker"]["guest_name"] == "udelar-lab01-1-attacker"
#     assert guest_data["udelar-lab01-1-attacker"]["base_name"] == "attacker"
#     assert guest_data["udelar-lab01-2-victim-1"]["instance"] == 2
#     assert guest_data["udelar-lab01-1-victim-2"]["copy"] == 2
#     assert guest_data["udelar-lab01-2-server"]["hostname"] == "server-2"
#     assert guest_data["udelar-lab01-1-attacker"]["entry_point"]
#     assert not guest_data["udelar-lab01-2-server"]["entry_point"]
#     assert guest_data["udelar-lab01-1-attacker"]["entry_point_index"] == 1
#     assert guest_data["udelar-lab01-1-victim-1"]["entry_point_index"] == 2
#     assert guest_data["udelar-lab01-1-victim-2"]["entry_point_index"] == 3
#     assert guest_data["udelar-lab01-2-attacker"]["entry_point_index"] == 4
#     assert not guest_data["udelar-lab01-1-attacker"]["internet_access"]
#     assert guest_data["udelar-lab01-1-attacker"]["base_os"] == "ubuntu22"
#     assert guest_data["udelar-lab01-1-attacker"]["memory"] == 1024
#     assert guest_data["udelar-lab01-1-victim-1"]["memory"] == 1024
#     assert guest_data["udelar-lab01-1-attacker"]["vcpu"] == 2
#     assert guest_data["udelar-lab01-1-server"]["vcpu"] == 1
#     assert guest_data["udelar-lab01-1-victim-2"]["instance_type"] == "t3.micro"
#     # TODO: This should return t2.medium:
#     assert guest_data["udelar-lab01-1-server"]["instance_type"] == "t3.micro"

#     # Test interfaces
#     victim_interfaces = guest_data["udelar-lab01-1-victim-2"]["interfaces"]
#     print(victim_interfaces)
#     assert victim_interfaces["udelar-lab01-1-victim-2-1"]["name"] == "udelar-lab01-1-victim-2-1"
#     assert victim_interfaces["udelar-lab01-1-victim-2-1"]["index"] == 0
#     server_interfaces = guest_data["udelar-lab01-2-server"]["interfaces"]
#     print(server_interfaces)
#     assert server_interfaces["udelar-lab01-2-server-1"]["network_name"] == "internal"
#     assert server_interfaces["udelar-lab01-2-server-2"]["network_name"] == "dmz"
#     assert server_interfaces["udelar-lab01-2-server-2"]["subnetwork_name"] == "udelar-lab01-2-dmz"
#     assert server_interfaces["udelar-lab01-2-server-2"]["private_ip"] == "10.0.2.132"
#     assert server_interfaces["udelar-lab01-2-server-2"]["mask"] == 25


# def test_set_elastic_stack_version(description):
#     description.set_elastic_stack_version("1.33.7")
#     assert description.elastic_stack_version == "1.33.7"

# def test_get_interface_index_to_sum(description):
#     description.deploy_elastic = False
#     description.deploy_caldera = False
#     description.platform = "libvirt"
#     result = description._get_interface_index_to_sum("attacker")
#     assert result == 4
#     result = description._get_interface_index_to_sum("victim")
#     assert result == 4
#     result = description._get_interface_index_to_sum("server")
#     assert result == 3

#     description.deploy_elastic = True
#     description.monitor_type = "endpoint"
#     result = description._get_interface_index_to_sum("attacker")
#     assert result == 4
#     result = description._get_interface_index_to_sum("victim")
#     assert result == 5
#     result = description._get_interface_index_to_sum("server")
#     assert result == 4

#     description.monitor_type = "traffic"
#     description.deploy_elastic = False
#     result = description._get_interface_index_to_sum("attacker")
#     assert result == 4
#     result = description._get_interface_index_to_sum("victim")
#     assert result == 4
#     result = description._get_interface_index_to_sum("server")
#     assert result == 3
#     description.deploy_elastic = True

#     description.deploy_caldera = True
#     description.deploy_elastic = False
#     result = description._get_interface_index_to_sum("attacker")
#     assert result == 5
#     result = description._get_interface_index_to_sum("victim")
#     assert result == 5
#     result = description._get_interface_index_to_sum("server")
#     assert result == 4
#     description.deploy_elastic = True

#     description.platform = "aws"
#     result = description._get_interface_index_to_sum("attacker")
#     assert result == 0
#     result = description._get_interface_index_to_sum("victim")
#     assert result == 0
#     result = description._get_interface_index_to_sum("server")
#     assert result == 0

# def test_get_guest_advanced_options_file(description):
#     path = description._get_guest_advanced_options_file("attacker")
#     assert path == "/dev/null"
#     path = description._get_guest_advanced_options_file("victim")
#     assert path == "/dev/null"

#     description.platform = "libvirt"
#     description.advanced_options_path = description.advanced_options_path.replace("aws","libvirt")
#     path = description._get_guest_advanced_options_file("attacker")
#     print(path)
#     assert path == f"{description.advanced_options_path}/attacker.xsl"
#     path = description._get_guest_advanced_options_file("victim")
#     assert path == "/dev/null"
#     description.platform = "aws"
#     description.advanced_options_path = description.advanced_options_path.replace("libvirt","aws")

# def test_get_parameters(description):
#     parameters = description.get_parameters(instances=[1])
#     assert parameters == {1:{'flags':'Flag 2'}}

#     parameters = description.get_parameters(instances=None)
#     assert parameters == {1:{'flags':'Flag 2'},2:{'flags':'Flag 1'}}
