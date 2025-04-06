
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
# along with Tectonic. If not, see <http://www.gnu.org/licenses/>.

import ipaddress
import math
import tempfile
import random
import yaml
from zipfile import ZipFile
from pathlib import Path
import re
import os
import json

from tectonic.constants import OS_DATA
import tectonic.utils
import tectonic.validate as validate

class DescriptionException(Exception):
    pass


class NetworkDescription():

    def __init__(self, name):
        self.name = name
        self.index = 0
        self.members = []

    @property
    def name(self):
        return self._name

    @property
    def index(self):
        return self._index

    @property
    def members(self):
        return self._members

    @name.setter
    def name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid network name {value}. Must have at least one alphanumeric symbol.")
        self._name = value

    @index.setter
    def index(self, value):
        validate.number("index", value, min_value=0)
        self._index = value

    @members.setter
    def members(self, value):
        try:
            if not all(isinstance(elem, str) for elem in value):
                raise ValueError
        except:
            raise DescriptionException(f"Invalid members {value}. Must be a list of guest names.")
        self._members = value

class ScenarioNetwork(NetworkDescription):

    def __init__(self, description, base_network, instance_num, ip_network):
        super().__init__(base_network.name)
        self.index = base_network.index
        self.members = base_network.members

        self.base_name = base_network.name
        self.name = description.institution + "-" + \
            description.lab_name + "-" + str(instance_num) + "-" + base_network.name
        self.instance = instance_num
        self.ip_network = ip_network
        self.mode = "none"

    @property
    def name(self):
        return self._name

    @property
    def base_name(self):
        return self._base_name

    @property
    def instance(self):
        return self._instance

    @property
    def ip_network(self):
        return self._ip_network

    @property
    def mode(self):
        return self._mode

    @name.setter
    def name(self, value):
        self._name = value

    @base_name.setter
    def base_name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid network name {value}. Must have at least one alphanumeric symbol.")
        self._base_name = value

    @instance.setter
    def instance(self, value):
        if value is not None:
            validate.number("instance", value, min_value=1)
        self._instance = value

    @ip_network.setter
    def ip_network(self, value):
        if value is not None:
            validate.ip_network("ip_network", value)
        self._ip_network = value

    @mode.setter
    def mode(self, value):
        validate.supported_value("mode", value, ["none", "nat"])
        self._mode = value





class MachineDescription:
    def __init__(self, name, default_os):
        self.name = name
        self.os = default_os
        self.memory = 1024
        self.vcpu = 1
        self.disk = 10

    #----------- Getters ----------
    @property
    def name(self):
        return self._name

    @property
    def os(self):
        return self._os

    @property
    def admin_username(self):
        return OS_DATA[self.os]["username"]

    @property
    def memory(self):
        return self._memory

    @property
    def vcpu(self):
        return self._vcpu

    @property
    def disk(self):
        return self._disk

    #----------- Setters ----------
    @name.setter
    def name(self, value):
        self._name = value

    @os.setter
    def os(self, value):
        validate.supported_value("os", value, OS_DATA.keys())
        self._os = value

    @memory.setter
    def memory(self, value):
        validate.number("memory", value, min_value=500)
        self._memory = value

    @vcpu.setter
    def vcpu(self, value):
        validate.number("vcpu", value, min_value=1)
        self._vcpu = value

    @disk.setter
    def disk(self, value):
        validate.number("disk", value, min_value=5)
        self._disk = value

    def load_machine(self, data):
        """Loads the information from the yaml structure in data."""
        self.memory = data.get("memory", self.memory)
        self.vcpu = data.get("vcpu", self.vcpu)
        self.disk = data.get("disk", self.disk)


class BaseGuestDescription(MachineDescription):
    def __init__(self, name, default_os):
        super().__init__(name, default_os)
        self.entry_point = False
        self.internet_access = False
        self.copies = 1
        self.monitor = False
        self.red_team_agent = False
        self.blue_team_agent = False

    # Redefine the name property, for stronger validation
    @property
    def name(self):
        return self._name

    @property
    def entry_point(self):
        return self._entry_point

    @property
    def internet_access(self):
        return self._internet_access

    @property
    def copies(self):
        return self._copies

    @property
    def monitor(self):
        return self._monitor

    @property
    def red_team_agent(self):
        return self._red_team_agent

    @property
    def blue_team_agent(self):
        return self._blue_team_agent

    @name.setter
    def name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(
                f"Invalid machine name {value}. Must have at least one alphanumeric symbol."
            )
        self._name = value

    @entry_point.setter
    def entry_point(self, value):
        validate.boolean("entry_point", value)
        self._entry_point = value

    @internet_access.setter
    def internet_access(self, value):
        validate.boolean("internet_access", value)
        self._internet_access = value

    @copies.setter
    def copies(self, value):
        validate.number("copies", value, min_value=0)
        self._copies = value

    @monitor.setter
    def monitor(self, value):
        validate.boolean("monitor", value)
        self._monitor = value

    @red_team_agent.setter
    def red_team_agent(self, value):
        validate.boolean("red_team_agent", value)
        self._red_team_agent = value

    @blue_team_agent.setter
    def blue_team_agent(self, value):
        validate.boolean("blue_team_agent", value)
        self._blue_team_agent = value

    def load_base_guest(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_machine(data)

        self.name = data.get("name", self.name)
        self.entry_point = data.get("entry_point", self.entry_point)
        self.os = data.get("os", self.os)
        self.internet_access = data.get("internet_access", self.internet_access)
        self.copies = data.get("copies", self.copies)
        self.monitor = data.get("monitor", self.monitor)
        self.red_team_agent = data.get("red_team_agent", self.red_team_agent)
        self.blue_team_agent = data.get("blue_team_agent", self.blue_team_agent)

class NetworkInterface():
    def __init__(self, description, guest, network, interface_num):
        self.name = f"{guest.name}-{interface_num+1}"
        self.index = interface_num + self._get_interface_index_to_sum(description, guest)
        self.guest_name = guest.name
        self.network = network
        self.private_ip = self._get_guest_ip_address(guest, network)
        self.mask = ipaddress.ip_network(network.ip_network).prefixlen

    @property
    def name(self):
        return self._name

    @property
    def index(self):
        return self._index

    @property
    def guest_name(self):
        return self._guest_name

    @property
    def network(self):
        return self._network

    @property
    def private_ip(self):
        return self._private_ip

    @property
    def mask(self):
        return self._mask

    @name.setter
    def name(self, value):
        self._name = value

    @index.setter
    def index(self, value):
        self._index = value

    @index.setter
    def guest_name(self, value):
        self._guest_name = value

    @network.setter
    def network(self, value):
        self._network = value

    @network.setter
    def private_ip(self, value):
        self._private_ip = value

    @mask.setter
    def mask(self, value):
        self._mask = value

        
    def _get_interface_index_to_sum(self, description, guest):
        """Returns number to be added to interface index.

        Libvirt requires a higher index, depending if guest is entry
        point and if it has an interface in the services network.

        """
        base = 0
        if description.config.platform == "libvirt":
            base = 3
            if guest.is_in_services_network:
                base += 1
            if guest.entry_point:
                base += 1
        return base

    def _get_guest_ip_address(self, guest, network):
        """Compute the IP address of the given guest in the network."""
        if guest.base_name not in network.members:
            raise DescriptionException(f"Cannot find {guest.base_name} in network {network.base_name}.")
        hostnum = network.members.index(guest.base_name) + (guest.copy - 1) + 3
        ip_network = ipaddress.ip_network(network.ip_network)
        return str(list(ip_network.hosts())[hostnum])



class GuestDescription(BaseGuestDescription):
    def __init__(self, description, base_guest, instance_num, copy,
                 is_in_services_network=False):
        # Copy base_guest data
        self.base_name = base_guest.name
        self.os = base_guest.os
        self.memory = base_guest.memory
        self.vcpu = base_guest.vcpu
        self.disk = base_guest.disk
        self.gpu = base_guest.disk
        self.entry_point = base_guest.entry_point
        self.internet_access = base_guest.internet_access
        self.copies = base_guest.copies
        self.monitor = base_guest.monitor
        self.red_team_agent = base_guest.red_team_agent
        self.blue_team_agent = base_guest.blue_team_agent

        copy_suffix = ("-" + str(copy)) if self.copies > 1 else ""
        self._name = description.institution + "-" + description.lab_name + "-" + \
            str(instance_num) + "-" + base_guest.name + copy_suffix
        self.instance = instance_num
        self.copy = copy
        self.hostname = base_guest.name + "-" + str(instance_num) + copy_suffix
        self.is_in_services_network = is_in_services_network

        self._interfaces = {}
        interface_num = 1
        for network in [n for _ , n in description.scenario_networks.items()
                        if base_guest.name in n.members]:
            interface = NetworkInterface(description, self, network, interface_num)
            self._interfaces[interface.name] = interface
            interface_num += 1

        self.entry_point_index = 0
        self.services_network_index = 0
        self.advanced_options_file = None


    @property
    def name(self):
        return self._name

    @property
    def base_name(self):
        return self._base_name

    @property
    def instance(self):
        return self._instance

    @property
    def copy(self):
        return self._copy

    @property
    def hostname(self):
        return self._hostname

    @property
    def is_in_services_network(self):
        return self._is_in_services_network

    @property
    def interfaces(self):
        return self._interfaces

    @property
    def entry_point_index(self):
        return self._entry_point_index

    @property
    def services_network_index(self):
        return self._services_network_index

    @property
    def advanced_options_file(self):
        return self._advanced_options_file

    @property
    def networks(self):
        return [i.network.base_name for _, i in self.interfaces.items]

    @base_name.setter
    def base_name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid guest name {value}. Must have at least one alphanumeric symbol.")
        self._base_name = value

    @name.setter
    def name(self, value):
        self._name = value

    @instance.setter
    def instance(self, value):
        validate.number("instance", value, min_value=1)
        self._instance = value

    @copy.setter
    def copy(self, value):
        validate.number("copy", value, min_value=0)
        self._copy = value

    @hostname.setter
    def hostname(self, value):
        validate.hostname("hostname", value)
        self._hostname = value

    @is_in_services_network.setter
    def is_in_services_network(self, value):
        validate.boolean("is_in_services_network", value)
        self._is_in_services_network = value

    @entry_point_index.setter
    def entry_point_index(self, value):
        self._entry_point_index = value

    @services_network_index.setter
    def services_network_index(self, value):
        self._services_network_index = value

    @advanced_options_file.setter
    def advanced_options_file(self, value):
        self._advanced_options_file = value



class ServiceDescription(MachineDescription):
    def __init__(self, name, default_os):
        super().__init__(name, default_os)
        self.enable = False

    @property
    def enable(self):
        return self._enable

    @enable.setter
    def enable(self, value):
        validate.boolean("enable", value)
        self._enable = value

    def load_service(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_machine(data)
        self.enable = data.get("enable", self.enable)


class ElasticDescription(ServiceDescription):
    supported_monitor_types = ["traffic", "endpoint"]

    def __init__(self):
        super().__init__("elastic", "rocky8")
        self.memory = 8192
        self.vcpu = 4
        self.disk = 50

        self.monitor_type = self.supported_monitor_types[0]
        self.deploy_default_policy = True

    @property
    def monitor_type(self):
        return self._monitor_type

    @property
    def deploy_default_policy(self):
        return self._deploy_default_policy

    @monitor_type.setter
    def monitor_type(self, value):
        validate.supported_value("monitor_type", value,
                                 self.supported_monitor_types,
                                 case_sensitive=False)
        self._monitor_type = value

    @deploy_default_policy.setter
    def deploy_default_policy(self, value):
        validate.boolean("deploy_default_policy", value)
        self._deploy_default_policy = value

    def load_elastic(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_service(data)
        self.monitor_type = data.get("monitor_type", self.monitor_type)
        self.deploy_default_policy = data.get("deploy_default_policy", 
                                              self.deploy_default_policy)


class CalderaDescription(ServiceDescription):
    def __init__(self):
        super().__init__("caldera", "rocky8")
        self.memory = 2048
        self.vcpu = 2
        self.disk = 20
        
    def load_caldera(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_service(data)

class PacketbeatDescription(ServiceDescription):
    def __init__(self):
        super().__init__("packetbeat", "ubuntu22")
        self.memory = 512
        self.vcpu = 1
        self.disk = 10
        
    def load_packetbeat(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_service(data)


class Description:

    def __init__(self, config, lab_edition_path):
        """Create a Description object.

        The description object is created from a lab edition file that
        references a scenario description in the configured
        lab_repo_uri.

        Parameters:
            config: A TectonicConfig object.
            lab_edition_path: Path to a lab edition file.
        
        Returns:
             A Description object.
        """

        self._config = config
        
        # Read lab edition file
        try:
            self._lab_edition_path = tectonic.utils.absolute_path(lab_edition_path)
            stream = open(self._lab_edition_path, "r")
            lab_edition_data = yaml.safe_load(stream)
            self._lab_edition_dir = str(Path(lab_edition_path).parent)
        except Exception as e:
            raise DescriptionException(f"Error loading lab edition file {self._lab_edition_path}.") from e
            
        # Read description file
        self._required(lab_edition_data, "base_lab")
        if not lab_edition_data.get("base_lab"):
            raise DescriptionException("Missing required option: base_lab.")
        self._scenario_dir = self._get_scenario_path(lab_edition_data["base_lab"])
        try:
            description_path = Path(self._scenario_dir).joinpath("description.yml")
            stream = open(description_path, "r")
            description_data = yaml.safe_load(stream)
        except Exception as e:
            raise DescriptionException(f"Error loading {lab_edition_data["base_lab"]} description file.") from e

        # Load description data
        self._required(description_data, "institution")
        self.institution = description_data["institution"]
        self._required(description_data, "lab_name")
        self.base_lab = description_data["lab_name"]
        self.default_os = description_data.get("default_os", "ubuntu22")

        self._required(description_data, "guest_settings")
        self._base_guests = {}
        for name, guest_data in description_data["guest_settings"].items():
            guest = BaseGuestDescription(name, self.default_os)
            guest.load_base_guest(guest_data)
            self._base_guests[guest.name] = guest

        self._required(description_data, "topology")
        self._topology = {}
        network_index = 0
        for network_data in description_data["topology"]:
            name = network_data["name"]
            # Repeat members for each copy
            members = [member for member in network_data["members"]
                       for copy in range(self._base_guests[member].copies)
                       ]
            network = NetworkDescription(name)
            network.index = network_index
            network_index += 1
            for member in members:
                if not member in self._base_guests:
                    raise DescriptionException(f"Undefined member {member} in network {name}.")
            network.members = members
            self._topology[network.name] = network
        self._elastic = ElasticDescription()
        self._elastic.load_elastic(description_data.get("elastic", {}))
        self._caldera = CalderaDescription()
        self._caldera.load_caldera(description_data.get("caldera", {}))

        # Load lab edition data
        self.institution = lab_edition_data.get("institution", self.institution)
        self.lab_name = lab_edition_data.get("lab_edition_name", self.base_lab)
        self._required(lab_edition_data, "instance_number")
        self.instance_number = lab_edition_data["instance_number"]
        self.teacher_pubkey_dir = lab_edition_data.get("teacher_pubkey_dir")
        self.student_prefix = lab_edition_data.get("student_prefix", "trainee")
        self.student_pubkey_dir = lab_edition_data.get("student_pubkey_dir")
        self.create_students_passwords = lab_edition_data.get("create_students_passwords", False)
        self._required(lab_edition_data, "random_seed")
        self.random_seed = lab_edition_data["random_seed"]

        # Elastic is enabled if it is enabled in the description and
        # not disabled in the lab edition.
        enable_elastic = self._elastic.enable and lab_edition_data.get("elastic", {}).get("enable", True)
        self._elastic.load_elastic(lab_edition_data.get("elastic", {}))
        self._elastic.enable = enable_elastic
        self._packetbeat = PacketbeatDescription()
        if enable_elastic and config.platform == "aws":
            self._packetbeat.enable = True

        # Caldera is enabled if it is enabled in the description and
        # not disabled in the lab edition.
        enable_caldera = self._caldera.enable and lab_edition_data.get("caldera", {}).get("enable", True)
        self._caldera.load_caldera(lab_edition_data.get("caldera", {}))
        self._caldera.enable = enable_caldera

        self._scenario_networks = self._compute_scenario_networks()
        self._scenario_guests = self._compute_scenario_guests()
        self._parameters_files = tectonic.utils.read_files_in_directory(
            Path(self._scenario_dir).joinpath("ansible","parameters")
        )


    def parse_machines(self, instances=[], guests=[], copies=[], only_instances=True, exclude=[]):
        """
        Return machines names based on instance number, guest name and number of copy.

        Parameters:
            instances (list(int)): numbers of instances.
            guests (tuple(str)): guest name of machines.
            copies (list(int)): number of copy of the machines.
            only_instances (bool): Whether to return only scenario machines or include aux machines.
            exclude (list(str)): base name of machines to exclude.

        Returns:
            list(str): full name of machines.
        """
        # Validate filters    
        infrastructure_guests_names = []
        if self.config.platform == "aws":
            if self.student_access_required:
                infrastructure_guests_names.append("student_access")
            if self.config.aws.teacher_access == "host":
                infrastructure_guests_names.append("teacher_access")
        for service in self.services:
            infrastructure_guests_names.append(service)

        guests_aux = list(self.base_guests.keys())
        if not only_instances:
            guests_aux = guests_aux + infrastructure_guests_names
        if max(instances, default=0) > self.instance_number:
            raise DescriptionException("Invalid instance numbers specified.")
        if guests is not None and not set(guests).issubset(set(guests_aux)):
            raise DescriptionException("Invalid guests names specified.")
        max_guest_copy = max([guest.copies for _, guest in self._base_guests.items() 
                              if not guests or guest.name in guests], 
                             default=1)
        if max(copies, default=0) > max_guest_copy:
            raise DescriptionException("Invalid copies specified.")

        # Compute all machine names
        result = []
        for guest_name in self.scenario_guests:
            result.append(guest_name)

        if not only_instances:
            if self.config.platform == "aws":
                result.append(f"{self.institution}-{self.lab_name}-student_access")
                if self.config.aws.teacher_access == "host":
                    result.append(f"{self.institution}-{self.lab_name}-teacher_access")

            for service in self.services:
                result.append(f"{self.institution}-{self.lab_name}-{service}")

        # Filter the result
        if instances:
            instance_re = f"^{self.institution}-{self.lab_name}-({'|'.join(str(instance) for instance in instances)})-"
            result = list(
                filter(
                    lambda machine: re.search(instance_re, machine) is not None, result
                )
            )

        if guests:
            guest_re = (
                rf"^{self.institution}-{self.lab_name}(-\d+)?-({'|'.join(guests)})(-|$)"
            )
            result = list(
                filter(lambda machine: re.search(guest_re, machine) is not None, result)
            )

        if copies:
            one_copy_re = rf"^{self.institution}-{self.lab_name}-\d+-[^-]+$"
            many_copies_re = rf"^{self.institution}-{self.lab_name}-\d+-[^-]+-({'|'.join(str(copy) for copy in copies)})$"
            result = list(
                filter(
                    lambda machine: re.search(
                        many_copies_re
                        if (self.scenario_guests[machine].copies > 1)
                        or (1 not in copies)
                        else one_copy_re,
                        machine,
                    )
                    is not None,
                    result,
                )
            )

        for machine in exclude:
            guest_re = (
                rf"^{self.institution}-{self.lab_name}(-\d+)?-{machine}(-|$)"
            )
            result = list(
                filter(lambda machine: re.search(guest_re, machine) is None, result)
            )

        if len(result) == 0:
            raise DescriptionException(
                "No machines with the specified characteristics were found."
            )
        else:
            return result


    #----------- Getters ----------
    @property
    def config(self):
        return self._config

    @property
    def lab_edition_path(self):
        return self._lab_edition_path

    @property
    def lab_edition_dir(self):
        return self._lab_edition_dir

    @property
    def scenario_dir(self):
        return self._scenario_dir

    @property
    def base_lab(self):
        return self._base_lab

    @property
    def institution(self):
        return self._institution

    @property
    def lab_name(self):
        return self._lab_name

    @property
    def instance_number(self):
        return self._instance_number

    @property
    def teacher_pubkey_dir(self):
        return self._teacher_pubkey_dir

    @property
    def authorized_keys(self):
        """Returns the configured ssh pubkeys for teacher access.

        Concatenates the contents of all the pubkeys in
        teacher_pubkey_dir plus config option ssh_public_key_file.
        """
        keys = ""
        if self.teacher_pubkey_dir and Path(self.teacher_pubkey_dir).is_dir():
            for child in Path(self.teacher_pubkey_dir).iterdir():
                if child.is_file():
                    key = child.read_text()
                    if key[-1] != "\n":
                        key += "\n"
                    keys += key

        if self.config.ssh_public_key_file is not None:
            p = Path(self.config.ssh_public_key_file).expanduser()
            if p.is_file():
                key = p.read_text()
                if key[-1] != "\n":
                    key += "\n"
                keys += key

        return keys


    @property
    def student_prefix(self):
        return self._student_prefix

    @property
    def student_pubkey_dir(self):
        return self._student_pubkey_dir

    @property
    def create_students_passwords(self):
        return self._create_students_passwords

    @property
    def random_seed(self):
        return self._random_seed

    @property
    def default_os(self):
        return self._default_os

    @property
    def base_guests(self):
        return self._base_guests

    @property
    def topology(self):
        return self._topology

    @property
    def student_access_required(self):
        any(guest.entry_point for _, guest in self._base_guests.items())

    @property
    def internet_access_required(self):
        any(guest.internet_access for _, guest in self._base_guests.items())


    @property
    def parameters_files(self):
        return self._parameters_files

    @property
    def scenario_networks(self):
        return self._scenario_networks

    @property
    def scenario_guests(self):
        return self._scenario_guests


    @property
    def elastic(self):
        return self._elastic

    @property
    def caldera(self):
        return self._caldera

    @property
    def services(self):
        return [service.name for service in [self._elastic, self._packetbeat, self._caldera] if service.enable]

    #----------- Setters ----------
    @base_lab.setter
    def base_lab(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value)
        if value == "":
            raise DescriptionException(f"Invalid base_lab {value}. Must have at least one alphanumeric symbol.")
        self._base_lab = value

    @institution.setter
    def institution(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value)
        if value == "":
            raise DescriptionException(f"Invalid institution {value}. Must have at least one alphanumeric symbol.")
        self._institution = value

    @lab_name.setter
    def lab_name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value)
        if value == "":
            raise DescriptionException(f"Invalid lab_edition_name {value}. Must have at least one alphanumeric symbol.")
        self._lab_name = value

    @instance_number.setter
    def instance_number(self, value):
        validate.number("instance_number", value, min_value=0)
        self._instance_number = value

    @teacher_pubkey_dir.setter
    def teacher_pubkey_dir(self, value):
        if value is not None:
            value = tectonic.utils.absolute_path(value, base_dir=self.lab_edition_dir)
            validate.path_to_dir("teacher_pubkey_dir", value)
        self._teacher_pubkey_dir = value

    @student_prefix.setter
    def student_prefix(self, value):
        self._student_prefix = value

    @student_pubkey_dir.setter
    def student_pubkey_dir(self, value):
        if value is not None:
            value = tectonic.utils.absolute_path(value, base_dir=self.lab_edition_dir)
            validate.path_to_dir("student_pubkey_dir", value)
        self._student_pubkey_dir = value

    @create_students_passwords.setter
    def create_students_passwords(self, value):
        validate.boolean("create_students_passwords", value)
        self._create_students_passwords = value

    @random_seed.setter
    def random_seed(self, value):
        self._random_seed = value

    @default_os.setter
    def default_os(self, value):
        validate.supported_value("default_os", value, OS_DATA.keys())
        self._default_os = value


    def _required(self, description_data, field):
        """
        Check if the field is in the description data.

        Parameters:
            description (obj): description data.
            field (str): field to be searched.
        """
        if not description_data.get(field):
            raise DescriptionException(f"Missing required option: {field} not defined.")


    def _get_scenario_path(self, base_lab):
        """Constructs a path to search for the scenario specification.
        
        If lab_repo_uri is a path to a directory, this will return the
        <base_lab> subdirectory if it exists. If not, and a
        <base_lab>.cft scenario package file exists, it is extracted
        to a temporary directory, which is returned.
        """
        # Open the lab directory if it exists, otherwise use a CTF package file
        if Path(self.config.lab_repo_uri).joinpath(base_lab).is_dir():
            return Path(self.config.lab_repo_uri).joinpath(base_lab)
        else:
            lab_pkg_file = Path(self.config.lab_repo_uri).joinpath(f"{base_lab}.ctf")
            if Path(lab_pkg_file).is_file():
                pkg = ZipFile(lab_pkg_file)
                # Extract the package to temporary directory
                self.extract_tmpdir = tempfile.TemporaryDirectory(
                    prefix="tectonic", suffix=base_lab
                )
                pkg.extractall(path=self.extract_tmpdir.name)
                return Path(self.extract_tmpdir.name)
            else:
                raise DescriptionException(f"{base_lab} not found in {config.lab_repo_uri}.")


    def _compute_scenario_networks(self):
        """Compute the complete list of scenario networks.
        
        This method divides the IP block defined in network_cidr_block
        into enough subnetworks for the defined networks in the
        topology.
        """
        networks = {}

        new_subnet_bits = math.ceil(math.log2(len(self.topology)))
        for instance_num in range(1, self.instance_number + 1):
            ip_network = list(
                # network_cidr_block is a /16 network. So each
                # instance gets a /24 network, divided into the number
                # of networks deifined in the topology
                ipaddress.ip_network(self.config.network_cidr_block).subnets(prefixlen_diff=8)
            )[instance_num]
            instance_subnets = list(ip_network.subnets(new_subnet_bits))
            for _, network in self.topology.items():
                scenario_network = ScenarioNetwork(self, network, instance_num, str(instance_subnets[network.index]))
                networks[network.name] = scenario_network
        return networks


    def _compute_scenario_guests(self):
        """Compute the scenario guest data."""

        guests = {}
        entry_point_index = 1
        services_network_index = 1
        for instance_num in range(1, self.instance_number + 1):
            for base_name, base_guest in self.base_guests.items():
                for copy in range(1, base_guest.copies+1):
                    is_in_services_network = (
                        self.elastic.enable and self.elastic.monitor_type == "endpoint" and not base_guest.monitor
                    ) or (
                        self.caldera.enable and (not base_guest.red_team_agent or not base_guest.blue_team_agent)
                    )
                    guest = GuestDescription(self, base_guest, instance_num, copy, is_in_services_network)
                    guest.entry_point_index = entry_point_index
                    guest.services_network_index = services_network_index
                    guest.advanced_options_file = self._get_guest_advanced_options_file(base_name)
                    guests[guest.name] = guest

                    if base_guest.entry_point:
                        entry_point_index += 1
                    if is_in_services_network:
                        services_network_index += 1

        return guests


    def _get_guest_advanced_options_file(self, base_name):
        """
        Return path to advanced options for the guest if exists or /dev/null otherwise.

        Parameters:
            base_name (str): Machine base name
        """
        if self.config.platform == "libvirt":
            advanced_options_path = Path(self._scenario_dir).joinpath("advanced", self.config.platform)
            advanced_options_file = Path(advanced_options_path).joinpath(f'{base_name}.xsl')
            if advanced_options_file.is_file():
                return advanced_options_file.resolve().as_posix()
        return "/dev/null"
