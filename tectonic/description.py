
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
import string
from passlib.hash import sha512_crypt
import yaml
from zipfile import ZipFile
from pathlib import Path
import re
import json

from tectonic.constants import OS_DATA
import tectonic.utils
import tectonic.validate as validate
from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS


class DescriptionException(Exception):
    pass
class NetworkDescription():

    def __init__(self, description, base_name):
        self._institution = description.institution
        self._lab_name = description.lab_name
        self.base_name = base_name
        self.index = 0
        self.members = []

    @property
    def base_name(self):
        return self._base_name

    @property
    def index(self):
        return self._index

    @property
    def members(self):
        return self._members

    @base_name.setter
    def base_name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid network name {value}. Must have at least one alphanumeric symbol.")
        self._base_name = value

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

class AuxiliaryNetwork(NetworkDescription):

    def __init__(self, description, network_name, ip_network, mode):
        super().__init__(description, network_name)
        self.ip_network = ip_network
        self.mode = mode
        self.instance = None

    @property
    def name(self):
        if self.instance is not None:
            return self._institution + "-" + self._lab_name + "-" + str(self.instance) + "-" + self.base_name
        else:
            return self._institution + "-" + self._lab_name + "-" + self.base_name

    @property
    def ip_network(self):
        return self._ip_network

    @property
    def mode(self):
        return self._mode

    @ip_network.setter
    def ip_network(self, value):
        if value is not None:
            validate.ip_network("ip_network", value)
        self._ip_network = value

    @mode.setter
    def mode(self, value):
        validate.supported_value("mode", value, ["none", "nat"])
        self._mode = value

    def to_dict(self):
        """Convert an AuxiliaryNetwork object to the dictionary expected by terraform."""
        result = {}
        result["base_name"] = self.base_name
        result["name"] = self.name
        result["cidr"] = self.ip_network
        result["mode"] = self.mode
        return result

class ScenarioNetwork(NetworkDescription):

    def __init__(self, description, base_network, instance_num, ip_network):
        super().__init__(description, base_network.base_name)
        self.index = base_network.index
        self.members = base_network.members
        self.instance = instance_num
        self.ip_network = ip_network
        self.mode = "none"

    @property
    def name(self):
        return self._institution + "-" + \
            self._lab_name + "-" + str(self.instance) + "-" + self.base_name

    @property
    def instance(self):
        return self._instance

    @property
    def ip_network(self):
        return self._ip_network

    @property
    def mode(self):
        return self._mode

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

    def to_dict(self):
        """Convert a ScenarioNetwork object to the dictionary expected by terraform."""
        result = {}
        result["name"] = self.name
        result["ip_network"] = self.ip_network
        return result

class MachineDescription:
    def __init__(self, description, base_name, os=None):
        self._description = description
        self.base_name = base_name
        self.os = os or description.default_os
        self.memory = 1024
        self.vcpu = 1
        self.disk = 10
        self.gpu = False

    #----------- Getters ----------
    @property
    def institution(self):
        return self._description.institution

    @property
    def lab_name(self):
        return self._description.lab_name

    @property
    def base_name(self):
        return self._base_name

    @property
    def image_name(self):
        return f"{self._description.institution}-{self._description.lab_name}-{self.base_name}"

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
    def gpu(self):
        return self._gpu

    @property
    def disk(self):
        return self._disk

    @property
    def instance_type(self):
        return self._description.instance_type.get_guest_instance_type(self.memory,
                                                                       self.vcpu,
                                                                       self.gpu,
                                                                       self.monitor,
                                                                       self._description.elastic.monitor_type)
    
    @property
    def access_protocols(self): #TODO: Maybe this should be specific in the scenario description.
        if self.os in ["ubuntu22", "kali", "rocky8", "rocky9"]:
            return {"ssh":{"port":22}}
        elif self.os in ["windows_srv_2022"]:
            return {"ssh":{"port":22}, "rdp":{"port":3389,"ftp_port":22}}

    #----------- Setters ----------
    @institution.setter
    def institution(self, value):
        self._institution = value

    @lab_name.setter
    def lab_name(self, value):
        self._lab_name = value

    @base_name.setter
    def base_name(self, value):
        value = re.sub("[^a-zA-Z0-9_]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid machine name {value}. Must have at least one alphanumeric symbol.")
        self._base_name = value

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

    @gpu.setter
    def gpu(self, value):
        validate.boolean("gpu", value)
        self._gpu = value

    @disk.setter
    def disk(self, value):
        validate.number("disk", value, min_value=5)
        self._disk = value

    def load_machine(self, data):
        """Loads the information from the yaml structure in data."""
        if not data:
            return
        self.memory = data.get("memory", self.memory)
        self.vcpu = data.get("vcpu", self.vcpu)
        self.disk = data.get("disk", self.disk)
        self.gpu = data.get("gpu", self.gpu)

    def toJSON(self):
        "{}"

class BaseGuestDescription(MachineDescription):
    def __init__(self, description, base_name):
        super().__init__(description, base_name)
        self.entry_point = False
        self.internet_access = False
        self.copies = 1
        self.monitor = False
        self.red_team_agent = False
        self.blue_team_agent = False

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
        self._monitor = self._description.elastic.enable and value

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
        if not data:
            return
        self.load_machine(data)
        self.base_name = data.get("name", self.base_name)
        self.entry_point = data.get("entry_point", self.entry_point)
        self.os = data.get("base_os", self.os)
        self.internet_access = data.get("internet_access", self.internet_access)
        self.copies = data.get("copies", self.copies)
        self.monitor = data.get("monitor", self.monitor)
        self.red_team_agent = data.get("red_team_agent", self.red_team_agent)
        self.blue_team_agent = data.get("blue_team_agent", self.blue_team_agent)

    def to_dict(self):
        """Convert BaseGuestDescription object to the dictionary expected by packer."""
        result = {}
        result["base_os"] = self.os
        result["endpoint_monitoring"] = self.monitor
        result["instance_type"] = self.instance_type
        result["vcpu"] = self.vcpu
        result["memory"] = self.memory
        result["disk"] = self.disk        
        return result

class NetworkInterface():
    def __init__(self, description, guest, network, interface_num, private_ip=None):
        self.name = f"{guest.name}-{interface_num+1}"
        self.index = interface_num + self._get_interface_index_to_sum(description, guest)
        self._guest_name = f"{guest.name}"
        self.network = network
        self.private_ip = self._get_guest_ip_address(guest, network) if private_ip is None else private_ip
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

    # @index.setter
    # def guest_name(self, value):
    #     self._guest_name = value

    @network.setter
    def network(self, value):
        self._network = value

    @private_ip.setter
    def private_ip(self, value):
        self._private_ip = value

    @mask.setter
    def mask(self, value):
        self._mask = value

    def to_dict(self):
        """Convert a NetworkInterface object to the dictionary expected by terraform."""
        result = {}
        result["name"] = self.name
        result["subnetwork_name"] = self.network.name
        result["private_ip"] = self.private_ip
        return result
        
    def _get_interface_index_to_sum(self, description, guest):
        """Returns number to be added to interface index.

        Libvirt requires a higher index, depending if guest is entry
        point and if it has an interface in the services network.

        """
        base = 0
        if description.config.platform == "libvirt":
            base = 2
            if guest.is_in_services_network:
                base += 1
            if guest.entry_point and not description.guacamole.enable:
                base += 1
        elif description.config.platform == "aws":
            base = -1
        return base

    def _get_guest_ip_address(self, guest, network):
        """Compute the IP address of the given guest in the network."""
        if guest.base_name not in network.members:
            raise DescriptionException(f"Cannot find {guest.base_name} in network {network.base_name}.")
        hostnum = network.members.index(guest.base_name) + (guest.copy - 1) + 3
        ip_network = ipaddress.ip_network(network.ip_network)
        return str(list(ip_network.hosts())[hostnum])

class GuestDescription(BaseGuestDescription):
    def __init__(self, description, base_guest, instance_num, copy, is_in_services_network=False):
        super().__init__(description, base_guest.base_name)
        # Copy base_guest data
        self.base_name = base_guest.base_name
        self.os = base_guest.os
        self.memory = base_guest.memory
        self.vcpu = base_guest.vcpu
        self.disk = base_guest.disk
        self.gpu = base_guest.gpu
        self.entry_point = base_guest.entry_point
        self.internet_access = base_guest.internet_access
        self.copies = base_guest.copies
        self.monitor = base_guest.monitor
        self.red_team_agent = base_guest.red_team_agent
        self.blue_team_agent = base_guest.blue_team_agent

        self.instance = instance_num
        self.copy = copy
        self.is_in_services_network = is_in_services_network

        self._interfaces = {}
        interface_num = 1
        for network in [n for _ , n in description.scenario_networks.items() if base_guest.base_name in n.members and self.instance == n.instance ]:
            interface = NetworkInterface(description, self, network, interface_num)
            self._interfaces[interface.name] = interface
            interface_num += 1
        self.entry_point_index = 0
        self.services_network_index = 0
        self.advanced_options_file = None

    @property
    def name(self):
        copy_suffix = ("-" + str(self.copy)) if self.copies > 1 else ""
        return self.institution + "-" + self.lab_name + "-" + \
            str(self.instance) + "-" + self.base_name + copy_suffix

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
        copy_suffix = ("-" + str(self.copy)) if self.copies > 1 else ""
        return self.base_name + "-" + str(self.instance) + copy_suffix
        
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
        value = re.sub("[^a-zA-Z0-9_]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid guest name {value}. Must have at least one alphanumeric symbol.")
        self._base_name = value

    @instance.setter
    def instance(self, value):
        validate.number("instance", value, min_value=1)
        self._instance = value

    @copy.setter
    def copy(self, value):
        validate.number("copy", value, min_value=0)
        self._copy = value

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

    def to_dict(self):
        """Convert a GuestDescription object to the dictionary expected by packer."""
        result = {}
        result["base_name"] = self.base_name
        result["name"] = self.name
        result["vcpu"] = self.vcpu
        result["memory"] = self.memory
        result["disk"] = self.disk
        result["hostname"] = self.hostname
        result["base_os"] = self.os
        result["is_in_services_network"] = self.is_in_services_network
        result["interfaces"] = {name: interface.to_dict() for name, interface in self.interfaces.items()}
        return result

class ServiceDescription(MachineDescription):
    def __init__(self, description, base_name, os, internet_access = False):
        super().__init__(description, base_name, os)
        self.base_name = base_name
        self.enable = False
        self._interfaces = {}
        self.monitor = False
        self.instance = 1
        self.copy = 1
        self.is_in_services_network = False
        self.entry_point = False
        self.internet_access = internet_access

    @property
    def base_name(self):
        return self._base_name

    @property
    def name(self):
        return f"{self.institution}-{self.lab_name}-{self.base_name}"
    
    @property
    def image_name(self):
        return self.base_name

    @property
    def enable(self):
        return self._enable
    
    @property
    def internet_access(self):
        return self._internet_access

    @base_name.setter
    def base_name(self, value):
        self._base_name = value

    @enable.setter
    def enable(self, value):
        validate.boolean("enable", value)
        self._enable = value

    @internet_access.setter
    def internet_access(self, value):
        validate.boolean("internet_access", value)
        self._internet_access = value

    def load_service(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_machine(data)
        self.enable = data.get("enable", self.enable)

    @property
    def interfaces(self):
        return self._interfaces
    
    def load_interfaces(self, auxiliary_networks):
        interface_num = 1
        for _, network in auxiliary_networks.items():
            if self._base_name in network.members:
                ip_network = ipaddress.ip_network(network.ip_network)
                private_ip = str(list(ip_network.hosts())[network.members.index(self._base_name)+4])
                interface = NetworkInterface(self._description, self, network, interface_num, private_ip)
                self._interfaces[interface.name] = interface
                interface_num += 1

    @property
    def service_ip(self):
        for _, interface in self.interfaces.items():
            if interface.network.base_name == "services":
                return interface.private_ip

class ElasticDescription(ServiceDescription):
    supported_monitor_types = ["traffic", "endpoint"]

    def __init__(self, description):
        super().__init__(description, "elastic", "rocky9", True)
        self.memory = 8192
        self.vcpu = 4
        self.disk = 50
        self.monitor_type = self.supported_monitor_types[0]
        self.deploy_default_policy = True
        self.port = 5601

    @property
    def monitor_type(self):
        return self._monitor_type

    @property
    def deploy_default_policy(self):
        return self._deploy_default_policy

    @monitor_type.setter
    def monitor_type(self, value):
        validate.supported_value("monitor_type", value, self.supported_monitor_types, case_sensitive=False)
        self._monitor_type = value

    @deploy_default_policy.setter
    def deploy_default_policy(self, value):
        validate.boolean("deploy_default_policy", value)
        self._deploy_default_policy = value

    def load_elastic(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_service(data)
        self.monitor_type = data.get("monitor_type", self.monitor_type)
        self.deploy_default_policy = data.get("deploy_default_policy", self.deploy_default_policy)
        
class CalderaDescription(ServiceDescription):
    def __init__(self, description):
        super().__init__(description, "caldera", "rocky9")
        self.memory = 2048
        self.vcpu = 2
        self.disk = 20
        self.port = 10443
        
    def load_caldera(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_service(data)

class PacketbeatDescription(ServiceDescription):
    def __init__(self, description):
        super().__init__(description, "packetbeat", "ubuntu22")
        self.memory = 512
        self.vcpu = 1
        self.disk = 10

class GuacamoleDescription(ServiceDescription):
    def __init__(self, description):
        super().__init__(description, "guacamole", "ubuntu22")
        self.memory = 1024
        self.vcpu = 2
        self.disk = 20
        self.port = 10443

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
        if config.platform == "aws":
            self._instance_type = InstanceTypeAWS()
        else:
            self._instance_type = InstanceType()

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
        base_lab = lab_edition_data["base_lab"]
        self._scenario_dir = str(self._get_scenario_path(base_lab))
        try:
            description_path = Path(self._scenario_dir) / "description.yml"
            stream = open(description_path, "r")
            description_data = yaml.safe_load(stream)
        except Exception as e:
            raise DescriptionException(f"Error loading {base_lab} description file.") from e

        # Load description data
        self._required(description_data, "institution")
        self.institution = description_data["institution"]
        self._required(description_data, "lab_name")
        self.base_lab = description_data["lab_name"]
        self._elastic = ElasticDescription(self)
        self._elastic.load_elastic(description_data.get("elastic_settings", {}))
        self._caldera = CalderaDescription(self)
        self._caldera.load_caldera(description_data.get("caldera_settings", {}))

        # Load lab edition data
        self._required(lab_edition_data, "instance_number")
        self.institution = lab_edition_data.get("institution", self.institution)
        self.lab_name = lab_edition_data.get("lab_edition_name", self.base_lab)
        self.instance_number = lab_edition_data["instance_number"]
        self.default_os = description_data.get("default_os", "ubuntu22")
        self.teacher_pubkey_dir = lab_edition_data.get("teacher_pubkey_dir")
        self.student_prefix = lab_edition_data.get("student_prefix", "trainee")
        self.student_pubkey_dir = lab_edition_data.get("student_pubkey_dir")
        self.create_students_passwords = lab_edition_data.get("create_students_passwords", False)
        self._required(lab_edition_data, "random_seed")
        self.random_seed = lab_edition_data["random_seed"]
        self.student_access_type = lab_edition_data.get("student_access_type", "ssh")
        validate.supported_value("student_access_type", self.student_access_type, ["ssh", "guacamole"])
        if self.student_access_type == "guacamole":
            self.student_pubkey_dir = None
            self.create_students_passwords = True

        # Guacamole is enable if student access type is guacamole
        self._guacamole = GuacamoleDescription(self)
        self._guacamole.enable = self.student_access_type == "guacamole"

        # Elastic is enabled if it is enabled in the description and
        # not disabled in the lab edition.
        enable_elastic = self._elastic.enable and lab_edition_data.get("elastic_settings", {}).get("enable", True)
        self._elastic.load_elastic(lab_edition_data.get("elastic_settings", {}))
        self._elastic.enable = enable_elastic
        self._packetbeat = PacketbeatDescription(self)
        if enable_elastic and config.platform == "aws" and self._elastic.monitor_type == "traffic":
            self._packetbeat.enable = True

        # Caldera is enabled if it is enabled in the description and
        # not disabled in the lab edition.
        enable_caldera = self._caldera.enable and lab_edition_data.get("caldera_settings", {}).get("enable", True)
        self._caldera.load_caldera(lab_edition_data.get("caldera_settings", {}))
        self._caldera.enable = enable_caldera

        # Load base guests and topology
        self._required(description_data, "guest_settings")
        self._base_guests = {}
        for name, guest_data in description_data["guest_settings"].items():
            guest = BaseGuestDescription(self, name)
            guest.load_base_guest(guest_data)
            self._base_guests[guest.base_name] = guest

        self._required(description_data, "topology")
        self._topology = {}
        network_index = 0
        for network_data in description_data["topology"]:
            base_name = network_data["name"]
            for member in network_data["members"]:
                if not member in self._base_guests:
                    raise DescriptionException(f"Undefined member {member} in network {base_name}.")
            # Repeat members for each copy
            members = [member for member in network_data["members"]
                       for copy in range(self._base_guests[member].copies)
                       ]
            network = NetworkDescription(self, base_name)
            network.index = network_index
            network_index += 1
            network.members = members
            self._topology[network.base_name] = network

        self._scenario_networks = self._compute_scenario_networks()
        self._parameters_files = tectonic.utils.list_files_in_directory(Path(self._scenario_dir) / "ansible" / "parameters")

        # Load auxiliary networks
        self._auxiliary_networks = {}
        if self._elastic.enable or self._caldera.enable or self._guacamole.enable:
            auxiliary_network_name = f"{self.institution}-{self.lab_name}-services"
            self._auxiliary_networks[auxiliary_network_name] = AuxiliaryNetwork(self, "services", self.config.services_network_cidr_block, "none")
            if self.config.platform == "aws" and self._elastic.monitor_type == "traffic":
                self._auxiliary_networks[auxiliary_network_name].members = ["elastic", "packetbeat", "caldera", "guacamole"]
            else:
                self._auxiliary_networks[auxiliary_network_name].members = ["elastic", "caldera", "guacamole"]

        if self._elastic.enable or self._caldera.enable or self.internet_access_required:
            auxiliary_network_name = f"{self.institution}-{self.lab_name}-internet"
            self._auxiliary_networks[auxiliary_network_name] = AuxiliaryNetwork(self, "internet", self.config.internet_network_cidr_block, "nat")
            if self.config.platform != "aws":
                self._auxiliary_networks[auxiliary_network_name].members = ["elastic"]

        #Load services interfaces
        self._elastic.load_interfaces(self._auxiliary_networks)
        self._packetbeat.load_interfaces(self._auxiliary_networks)
        self._caldera.load_interfaces(self._auxiliary_networks)
        self._guacamole.load_interfaces(self.auxiliary_networks)

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
        infrastructure_guests = self.extra_guests
        infrastructure_guests.update(self.services_guests)

        # Validate filters
        infrastructure_guests_names = []
        for _, guest in infrastructure_guests.items():
            infrastructure_guests_names.append(guest.base_name)

        guests_aux = list(self.base_guests.keys())
        if not only_instances:
            guests_aux = guests_aux + infrastructure_guests_names
        if max(instances or [], default=0) > self.instance_number:
            raise DescriptionException("Invalid instance numbers specified.")
        if guests is not None and not set(guests).issubset(set(guests_aux)):
            raise DescriptionException("Invalid guests names specified.")
        max_guest_copy = max((guest.copies for _, guest in self._base_guests.items()
                              if not guests or guest.base_name in guests) or [],
                             default=1)
        if max(copies or [], default=0) > max_guest_copy:
            raise DescriptionException("Invalid copies specified.")

        result = []
        for _, guest in self.scenario_guests.items():
            if instances and guest.instance not in instances:
                continue
            if guests and guest.base_name not in guests:
                continue
            if copies and guest.copy not in copies:
                continue
            if exclude and guest.base_name in exclude:
                continue
            result.append(guest.name)

        if not only_instances:
            for _, infra_guest in infrastructure_guests.items():
                if guests and infra_guest.base_name not in guests:
                    continue
                if exclude and infra_guest.base_name in exclude:
                    continue
                result.append(infra_guest.name)

        if len(result) == 0:
            raise DescriptionException(
                "No machines with the specified characteristics were found."
            )

        return result

    def get_parameters(self, instances=None):
        if not instances:
            instances = list(range(1,self.instance_number+1))
        random.seed(self.random_seed)
        choices = {}
        for file in self.parameters_files:
            with open(file, "r") as f:
                choices[Path(file).stem] = random.choices(f.readlines(),k=self.instance_number)
        parameters = {}
        for instance in instances:
            parameter = {}
            for choice in choices:
                parameter[choice] = json.loads(choices[choice][instance-1])
            parameters[instance] = parameter
        return parameters

    def generate_student_access_credentials(self):
        """
        Returns a dictionary of users with username, password, password_hash and authorized_keys.
        """
        users = {}
        random.seed(self.random_seed)
        digits = len(str(self.instance_number))
        for i in range(1,self.instance_number+1):
            username = f"{self.student_prefix}{i:0{digits}d}"
            users[username] = {}
            users[username]["instance"] = i
            if self.create_students_passwords:
                (password, salt) = self._generate_password()
                users[username]["password"] = password
                users[username]["password_hash"] = sha512_crypt.using(salt=salt).hash(password)
            if self.student_pubkey_dir:
                users[username]["authorized_keys"] = tectonic.utils.read_files_in_dir(
                    Path(self.student_pubkey_dir) / username)
        return users

    #----------- Getters ----------
    @property
    def config(self):
        return self._config

    @property
    def instance_type(self):
        return self._instance_type

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
    def ansible_dir(self):
        return str(Path(self._scenario_dir) / 'ansible')

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
        keys += tectonic.utils.read_files_in_dir(self.teacher_pubkey_dir)

        key = Path(self.config.ssh_public_key_file).expanduser().read_text()
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
        return (self.config.platform == "aws" and
                any(guest.entry_point for _, guest in self._base_guests.items()))

    @property
    def internet_access_required(self):
        return any(guest.internet_access for _, guest in self._base_guests.items())

    @property
    def parameters_files(self):
        return self._parameters_files

    @property
    def scenario_networks(self):
        return self._scenario_networks

    @property
    def scenario_guests(self):
        """Compute the scenario guest data."""

        guests = {}
        entry_point_index = 1
        services_network_index = 1
        for instance_num in range(1, self.instance_number + 1):
            for base_name, base_guest in self.base_guests.items():
                for copy in range(1, base_guest.copies+1):
                    is_in_services_network = (
                        self.elastic.enable and self.elastic.monitor_type == "endpoint" and base_guest.monitor
                    ) or (
                        self.caldera.enable and (base_guest.red_team_agent or base_guest.blue_team_agent)
                    ) or (
                        self.guacamole.enable and base_guest.entry_point
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
        
        
    @property
    def services_guests(self):
        """Compute the scenario services data."""

        services = {}
        if self.elastic.enable:
            services[self.elastic.name] = self.elastic
            if self.config.platform == "aws" and self.elastic.monitor_type == "traffic":
                services[self._packetbeat.name] = self._packetbeat
        if self.caldera.enable:
            services[self.caldera.name] = self.caldera
        if self.guacamole.enable:
            services[self.guacamole.name] = self.guacamole
        return services

    @property
    def extra_guests(self):
        """Compute the scenario extra data."""

        extra = {}
        if self.config.platform == "aws":
            if self.student_access_required:
                student_access = ServiceDescription(self, 'student_access', 'ubuntu22')
                extra[student_access.name] = student_access
            if self.config.aws.teacher_access == "host":
                teacher_access = ServiceDescription(self, 'teacher_access', 'ubuntu22')
                extra[teacher_access.name] = teacher_access
        return extra


    @property
    def elastic(self):
        return self._elastic

    @property
    def caldera(self):
        return self._caldera
    
    @property
    def packetbeat(self):
        return self._packetbeat
    
    @property
    def guacamole(self):
        return self._guacamole

    @property
    def auxiliary_networks(self):
        return self._auxiliary_networks

    #----------- Setters ----------
    @base_lab.setter
    def base_lab(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid base_lab {value}. Must have at least one alphanumeric symbol.")
        self._base_lab = value

    @institution.setter
    def institution(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid institution {value}. Must have at least one alphanumeric symbol.")
        self._institution = value

    @lab_name.setter
    def lab_name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid lab_edition_name {value}. Must have at least one alphanumeric symbol.")
        self._lab_name = value

    @instance_number.setter
    def instance_number(self, value):
        validate.number("instance_number", value, min_value=0)
        self._instance_number = value

    @scenario_dir.setter
    def scenario_dir(self, value):
        self._scenario_dir = value

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
                raise DescriptionException(f"{base_lab} not found in {self.config.lab_repo_uri}.")

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
                networks[scenario_network.name] = scenario_network
        return networks

    def _get_guest_advanced_options_file(self, base_name):
        """
        Return path to advanced options for the guest if exists or /dev/null otherwise.

        Parameters:
            base_name (str): Machine base name
        """
        if self.config.platform == "libvirt":
            advanced_options_path = Path(self._scenario_dir) / "advanced" / self.config.platform
            advanced_options_file = Path(advanced_options_path) / f'{base_name}.xsl'
            if advanced_options_file.is_file():
                return advanced_options_file.resolve().as_posix()
        return "/dev/null"

    def _generate_password(self):
        """Generate a pseudo random password and salt."""
        characters = string.ascii_letters + string.digits
        password = "".join(random.choice(characters) for _ in range(12))
        salt = "".join(random.choice(characters) for _ in range(16))
        return password, salt
