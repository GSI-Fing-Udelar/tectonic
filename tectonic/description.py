
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
from tectonic.instance_type import InstanceType
import tectonic.utils
import tectonic.validate as validate

class DescriptionException(Exception):
    pass

class MachineDescription:
    def __init__(self, name):
        self.name = name
        self.memory = 1024
        self.vcpu = 1
        self.disk = 10

    #----------- Getters ----------
    @property
    def name(self):
        return self._name

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
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid machine name {value}. Must have at least one alphanumeric symbol.")
        self._name = value

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
        super().__init__(name)
        self.entry_point = False
        self.base_os = default_os
        self.internet_access = False
        self.copies = 1
        self.monitor = False
        self.red_team_agent = False
        self.blue_team_agent = False

    @property
    def entry_point(self):
        return self._entry_point

    @property
    def base_os(self):
        return self._base_os

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

    @base_os.setter
    def base_os(self, value):
        validate.supported_value("base_os", value, OS_DATA.keys())
        self._base_os = value

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
        self.base_os = data.get("base_os", self.base_os)
        self.internet_access = data.get("internet_access", self.internet_access)
        self.copies = data.get("copies", self.copies)
        self.monitor = data.get("monitor", self.monitor)
        self.red_team_agent = data.get("red_team_agent", self.red_team_agent)
        self.blue_team_agent = data.get("blue_team_agent", self.blue_team_agent)



class NetworkDescription():

    def __init__(self, name):
        self.name = name
        self.members = []

    @property
    def name(self):
        return self._name

    @property
    def members(self):
        return self._members

    @name.setter
    def name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value).lower()
        if value == "":
            raise DescriptionException(f"Invalid network name {value}. Must have at least one alphanumeric symbol.")
        self._name = value

    @members.setter
    def members(self, value):
        try:
            if not all(isinstance(elem, str) for elem in value):
                raise ValueError
        except:
            raise DescriptionException(f"Invalid members {value}. Must be a list of guest names.")
        self._members = value

class ServiceDescription(MachineDescription):
    def __init__(self, name):
        super().__init__(name)
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
        super().__init__("elastic")
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
        super().__init__("caldera")
        self.memory = 2048
        self.vcpu = 2
        self.disk = 20
        
    def load_caldera(self, data):
        """Loads the information from the yaml structure in data."""
        self.load_service(data)

class PacketbeatDescription(ServiceDescription):
    def __init__(self):
        super().__init__("packetbeat")
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
            raise DescriptionException(f"Error loading lab edition file.") from e
            
        # Read description file
        self._required(lab_edition_data, "base_lab")
        if not lab_edition_data.get("base_lab"):
            raise DescriptionException(f"Missing required option: base_lab.")
        self._scenario_dir = self._get_scenario_path(config, lab_edition_data["base_lab"])
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
        self._guest_settings = {}
        for name, guest_data in description_data["guest_settings"].items():
            guest = BaseGuestDescription(name, self.default_os)
            guest.load_base_guest(guest_data)
            self._guest_settings[guest.name] = guest 

        self._required(description_data, "topology")
        self._topology = {}
        for network_data in description_data["topology"]:
            name = network_data["name"]
            members = network_data["members"]
            network = NetworkDescription(name)
            for member in members:
                if not member in self._guest_settings:
                    raise DescriptionException(f"Undefined member {member} in network {name}.")
            network.members = members
            self._topology[network.name] = network

#         self._expand_topology()
#         self.subnets = self._compute_subnetworks()


        self._elastic = ElasticDescription()
        self._elastic.load_elastic(description_data.get("elastic", {}))
        self._caldera = CalderaDescription()
        self._caldera.load_caldera(description_data.get("caldera", {}))

        # Load lab edition data
        self.institution = lab_edition_data.get("institution", self.institution)
        self.lab_edition_name = lab_edition_data.get("lab_edition_name", self.base_lab)
        self._required(lab_edition_data, "instance_number")
        self.instance_number = lab_edition_data["instance_number"]
        self.teacher_pubkey_dir = lab_edition_data.get("teacher_pubkey_dir")
        self.student_prefix = lab_edition_data.get("student_prefix", "trainee")
        self.student_pubkey_dir = lab_edition_data.get("student_pubkey_dir")
        self.create_students_passwords = lab_edition_data.get("create_students_passwords", False)
        self._required(lab_edition_data, "random_seed")
        self.random_seed = lab_edition_data["random_seed"]

        enable_elastic = self._elastic.enable and lab_edition_data.get("elastic", {}).get("enable", True)
        self._elastic.load_elastic(lab_edition_data.get("elastic", {}))
        self._elastic.enable = enable_elastic
        if enable_elastic and config.platform == "aws":
            self._packetbeat = PacketbeatDescription()
            self._packetbeat.enable = True

        enable_caldera = self._caldera.enable and lab_edition_data.get("caldera", {}).get("enable", True)
        self._caldera.load_caldera(lab_edition_data.get("caldera", {}))
        self._caldera.enable = enable_caldera
        

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
    def lab_edition_name(self):
        return self._lab_edition_name

    @property
    def instance_number(self):
        return self._instance_number

    @property
    def teacher_pubkey_dir(self):
        return self._teacher_pubkey_dir

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
    def guest_settings(self):
        return self._guest_settings

    @property
    def topology(self):
        return self._topology

    @property
    def elastic(self):
        return self._elastic

    @property
    def caldera(self):
        return self._caldera

    @property
    def services(self):
        return [service for service in [self._elastic, self._packetbeat, self._caldera] if service.enable]

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

    @lab_edition_name.setter
    def lab_edition_name(self, value):
        value = re.sub("[^a-zA-Z0-9]+", "", value)
        if value == "":
            raise DescriptionException(f"Invalid lab_edition_name {value}. Must have at least one alphanumeric symbol.")
        self._lab_edition_name = value

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


    def _get_scenario_path(self, config, base_lab):
        """Constructs a path to search for the scenario specification.
        
        If lab_repo_uri is a path to a directory, this will return the
        <base_lab> subdirectory if it exists. If not, and a
        <base_lab>.cft scenario package file exists, it is extracted
        to a temporary directory, which is returned.
        """
        # Open the lab directory if it exists, otherwise use a CTF package file
        if Path(config.lab_repo_uri).joinpath(base_lab).is_dir():
            return Path(config.lab_repo_uri).joinpath(base_lab)
        else:
            lab_pkg_file = Path(config.lab_repo_uri).joinpath(f"{base_lab}.ctf")
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


    def _compute_subnetworks(self):
        """Compute the complete list of subnetworks.
        
        This method divides the IP block defined in network_cidr_block
        into enough subnetworks for the defined networks in the
        topology.
        """
        subnets = {}

        new_subnet_bits = math.ceil(math.log2(len(self.topology)))
        for instance_num in range(1, self.instance_number + 1):
            instance_network = list(
                # network_cidr_block is a /16 network. So each
                # instance gets a /24 network, divided into the number
                # of networks deifined in the topology
                ipaddress.ip_network(self.network_cidr_block).subnets(prefixlen_diff=8)
            )[instance_num]
            instance_subnets = list(instance_network.subnets(new_subnet_bits))
            for name, network in self.topology.items()
                subnet_name = self.get_subnetwork_name(instance_num, n["name"])
                subnets[subnet_name] = str(instance_subnets[i])

        return subnets


# class Description:
#     """Class to represent a lab description."""

#     institution = ""
#     lab_name = ""
#     instance_number = 0
#     default_os = "ubuntu22"
#     deploy_elastic = False
#     elastic_deployment = {}
#     guest_settings = {}
#     topology = []

#     def __init__(
#         self,
#         config,
#         path,
#     ):
#         """Create a Description object.

#         The description object is created from a lab edition file that
#         references a scenario description in the configured
#         lab_repo_uri.

#         Parameters:
#             config: A TectonicConfig object.
#             path: Path to a lab edition file.
        
#         Returns:
#              A Description object.

#         """
#         self.config = config

#         # Load base lab name from lab edition file
#         self.lab_edition_file = Path(path).resolve().as_posix()
#         try:
#             stream = open(self.lab_edition_file, "r")
#             lab_edition_data = yaml.safe_load(stream)
#         except Exception as e:
#             raise DescriptionException("Error loading lab edition file.") from e
#         self._validate_lab_edition(lab_edition_data)
#         self.base_lab = lab_edition_data["base_lab"]
#         self.scenario_path = self._get_scenario_path()
#         self.description_file = Path(self.scenario_path).joinpath("description.yml")
#         if not Path(self.description_file).is_file():
#             raise DescriptionException(f"Description file not found inside {self.base_lab} lab.")
#         self.parameters_files = tectonic.utils.read_files_in_directory(
#             Path(self.scenario_path).joinpath("ansible", "parameters")
#         )

#         # Read scenario description
#         stream = open(self.description_file, "r")
#         description_data = yaml.safe_load(stream)
#         self._validate_description(description_data)

#         self.base_institution = re.sub("[^a-zA-Z0-9]+", "", description["institution"])
#         self.base_lab_name = re.sub("[^a-zA-Z0-9]+", "", description["lab_name"])
#         self.default_os = description.get("default_os", self.default_os)
#         self.guest_settings = {key.lower(): value for key, value in description.get("guest_settings", self.guest_settings).items()}
#         self.topology = description.get("topology", self.topology)

#         self._load_elastic_settings(description)
#         self._load_caldera_settings(description)

        


#         self.services = {}
#         self._load_lab_edition(path)
#         self.description_dir = Path(self.description_file).parent.resolve().as_posix()
#         self.ansible_playbooks_path = (
#             Path(self.description_dir).joinpath("ansible").resolve().as_posix()
#         )

#         self.advanced_options_path = Path(self.description_dir).joinpath("advanced", platform).resolve().as_posix()

#         self.authorized_keys = self.read_pubkeys(
#             self.teacher_pubkey_dir, self.config.ssh_public_key_file
#         )

#     def read_pubkeys(self, ssh_dir, default_pubkey=None):

#         """
#         Reads all public keys in the ssh directory of the description folder.

#         Parameters:
#             ssh_dir (str): Directory to search for public keys.
#             default_pubkey (str): Pubkey to use if there are no keys in ssh_dir.

#         Returns:
#             str: string with the contents of the ssh public keys.
#         """
#         keys = ""
#         if ssh_dir and Path(ssh_dir).is_dir():
#             for child in Path(ssh_dir).iterdir():
#                 if child.is_file():
#                     key = child.read_text()
#                     if key[-1] != "\n":
#                         key += "\n"
#                     keys += key

#         if default_pubkey is not None:
#             p = Path(default_pubkey).expanduser()
#             if p.is_file():
#                 key = p.read_text()
#                 if key[-1] != "\n":
#                     key += "\n"
#                 keys += key

#         return keys

#     def _required(self, description, field):
#         """
#         Check if the field is in the description.

#         Parameters:
#             description (obj): description.
#             field (str): field to be searched.
#         """
#         if not description.get(field):
#             raise DescriptionException(f"{field} not defined.")

#     def _validate_value(self, field, value, values):
#         if not value in values:
#             raise DescriptionException(f'Error in {field} field. The possible values are "{values}" but "{value}" value was assigned.')
        
#     def _validate_description(self, description):
#         """
#         Apply validations to lab description.

#         Parameters:
#             description (obj): lab description.
#         """
#         self._required(description, "institution")
#         self._required(description, "lab_name")
#         self._required(description, "guest_settings")
#         self._required(description, "topology")

#         self._validate_value("elastic_settings.enable", description.get("elastic_settings",{}).get("enable",False), [True, False])
#         self._validate_value("elastic_settings.monitor_type", description.get("elastic_settings",{}).get("monitor_type","traffic"), ["traffic", "endpoint"])
#         self._validate_value("caldera_settings.enable", description.get("caldera_settings",{}).get("enable",False), [True, False])

#     def _validate_lab_edition(self, lab_edition_data):
#         """
#         Apply validations to lab edition specification.

#         Parameters:
#             lab_edition_data (obj): lab edition specification.
#         """
#         self._required(lab_edition_data, "base_lab")
#         self._required(lab_edition_data, "instance_number")
#         if lab_edition_data.get("create_student_passwords"):
#             self._required(lab_edition_data, "random_seed")
#         self._validate_value("elastic_settings.enable", lab_edition_data.get("elastic_settings",{}).get("enable",False), [True, False])
#         self._validate_value("caldera_settings.enable", lab_edition_data.get("caldera_settings",{}).get("enable",False), [True, False])


#     def _load_description(self, description_file):
#         """
#         Load lab description file.

#         Parameters:
#             description_file (str): path to lab description file.
#         """
#         stream = open(description_file, "r")
#         description = yaml.safe_load(stream)
#         self._validate_description(description)

#         self.base_institution = re.sub("[^a-zA-Z0-9]+", "", description["institution"])
#         self.base_lab_name = re.sub("[^a-zA-Z0-9]+", "", description["lab_name"])
#         self.default_os = description.get("default_os", self.default_os)
#         self.guest_settings = {key.lower(): value for key, value in description.get("guest_settings", self.guest_settings).items()}
#         self.topology = description.get("topology", self.topology)

#         self._load_elastic_settings(description)
#         self._load_caldera_settings(description)

#     def _load_lab_edition(self, path):
#         """
#         Load lab edition specification file.

#         Parameters:
#             path (str): path to lab edition specification file.
#         """
#         stream = open(path, "r")
#         lab_edition_data = yaml.safe_load(stream)
#         self._validate_lab_edition(lab_edition_data)

#         self.instance_number = lab_edition_data["instance_number"]
#         self.base_lab = lab_edition_data["base_lab"]

#         self.student_prefix = lab_edition_data.get("student_prefix", "trainee")
#         self.student_pubkey_dir = lab_edition_data.get("student_pubkey_dir")
#         if self.student_pubkey_dir and not Path(self.student_pubkey_dir).is_absolute():
#             self.student_pubkey_dir = (
#                 Path(self.lab_edition_file)
#                 .parent.joinpath(self.student_pubkey_dir)
#                 .resolve()
#                 .as_posix()
#             )

#         self.create_student_passwords = lab_edition_data.get(
#             "create_student_passwords", False
#         )
#         self.random_seed = lab_edition_data.get("random_seed")

#         # Open the lab directory if it exists, otherwise use a CTF package file
#         if Path(self.lab_repo_uri).joinpath(self.base_lab).is_dir():
#             self.description_file = Path(self.lab_repo_uri).joinpath(
#                 self.base_lab, "description.yml"
#             )
#             self.parameters_files = read_files_in_directory(Path(self.lab_repo_uri).joinpath(self.base_lab,"ansible","parameters"))
#         else:
#             lab_pkg_file = Path(self.lab_repo_uri).joinpath(f"{self.base_lab}.ctf")
#             if Path(lab_pkg_file).is_file():
#                 pkg = ZipFile(lab_pkg_file)
#                 # Extract the package to temporary directory
#                 self.extract_tmpdir = tempfile.TemporaryDirectory(
#                     prefix="tectonic", suffix=self.base_lab
#                 )
#                 pkg.extractall(path=self.extract_tmpdir.name)
#                 self.description_file = Path(self.extract_tmpdir.name).joinpath(
#                     "description.yml"
#                 )
#                 self.parameters_files = read_files_in_directory(Path(self.extract_tmpdir.name,"ansible","parameters"))
#             else:
#                 raise DescriptionException(f"{self.base_lab} not found in {self.lab_repo_uri}.")
#         self._load_description(self.description_file)

#         self.institution = str.lower(re.sub(
#             "[^a-zA-Z0-9]+",
#             "",
#             lab_edition_data.get("institution", self.base_institution),
#         ))
#         self.lab_name = str.lower(re.sub(
#             "[^a-zA-Z0-9]+",
#             "",
#             lab_edition_data.get("lab_edition_name", self.base_lab_name),
#         ))

#         self.teacher_pubkey_dir = lab_edition_data.get("teacher_pubkey_dir")
#         if self.teacher_pubkey_dir and not Path(self.teacher_pubkey_dir).is_absolute():
#             self.teacher_pubkey_dir = Path(self.lab_edition_file).parent.joinpath(
#                 self.teacher_pubkey_dir
#             )

#         self.deploy_elastic = self.deploy_elastic and lab_edition_data.get("elastic_settings",{}).get("enable", True)
#         if self.deploy_elastic:
#             self.services["elastic"] = {
#                 "vcpu": lab_edition_data.get("elastic_settings",{}).get("vcpu", 4),
#                 "memory": lab_edition_data.get("elastic_settings",{}).get("memory", 8192),
#                 "disk": lab_edition_data.get("elastic_settings",{}).get("disk", 50)
#             }
#             if self.platform == "aws":
#                 self.services["packetbeat"] = {
#                     "vcpu": 1,
#                     "memory": 512,
#                     "disk": 10,
#                 }
#         self.deploy_caldera = self.deploy_caldera and lab_edition_data.get("caldera_settings",{}).get("enable", True)
#         if self.deploy_caldera:
#             self.services["caldera"] = {
#                 "vcpu": lab_edition_data.get("caldera_settings",{}).get("vcpu", 2),
#                 "memory": lab_edition_data.get("caldera_settings",{}).get("memory", 2048),
#                 "disk": lab_edition_data.get("caldera_settings",{}).get("disk", 20)
#             }

#         self._expand_topology()
#         self.subnets = self._compute_subnetworks()

#     def _load_elastic_settings(self, description):
#         settings = description.get("elastic_settings", {})
#         self.deploy_elastic = settings.get("enable",False)
#         self.monitor_type = settings.get("monitor_type","traffic")
#         self.elastic_deploy_default_policy = settings.get("deploy_default_policy",True)

#     def _load_caldera_settings(self, description):
#         settings = description.get("caldera_settings", {})
#         self.deploy_caldera = settings.get("enable",False)

#     def get_instance_range(self):
#         """
#         Get range for instances.

#         Returns:
#             range: instance range.
#         """
#         return range(1, self.instance_number + 1)

#     def get_guest_attr(self, guest_name, attr, default=None):
#         """
#         Get guest specific attribute

#         Parameters:
#             guest_name (str): machine guest name.
#             attr (str): attribute to return.
#             default (str, None): default value to return in case attribute is not found.

#         Returns:
#             any: attribute value for the guest.
#         """
#         if self.guest_settings.get(guest_name):
#             return self.guest_settings[guest_name].get(attr, default)
#         else:
#             return default

#     def get_guest_copies(self, guest_name):
#         """
#         Get guest number of copies

#         Parameters:
#             guest_name (str): machine guest name.

#         Returns:
#             int: copies number.
#         """
#         return self.get_guest_attr(guest_name, "copies", 1)

#     def get_copy_range(self, guest_name):
#         """
#         Get range for guest instance.

#         Parameters:
#             guest_name (str): machine guest name.

#         Returns:
#             range: copy range.
#         """
#         return range(1, self.get_guest_copies(guest_name) + 1)

#     def get_image_name(self, guest_name):
#         """
#         Get image full name.

#         Parameters:
#             guest_name (str): machine guest name.

#         Returns:
#             str: full name.
#         """
#         return f"{self.institution}-{self.lab_name}-{guest_name}"

#     def get_instance_name(self, instance_num, guest_name, copy=1):
#         """
#         Get machine full name.

#         Parameters:
#             instance_num (int): machine instance number.
#             guest_name (str): machine guest name.
#             copy (int): machine copy number.

#         Returns:
#             str: full name.
#         """
#         return f"{self.institution}-{self.lab_name}-{instance_num}-{guest_name}" + (
#             ("-" + str(copy)) if self.get_guest_copies(guest_name) > 1 else ""
#         )

#     def get_hostname(self, instance_num, guest_name, copy=1):
#         """
#         Get hostname.

#         Parameters:
#             instance_num (int): machine instance number.
#             guest_name (str): machine guest name.
#             copy (int): machine copy number.

#         Returns:
#             str: hostname.
#         """
#         return f"{guest_name}-{instance_num}" + (
#             ("-" + str(copy)) if self.get_guest_copies(guest_name) > 1 else ""
#         )

#     def get_instance_number(self, instance_name):
#         """
#         Get instance number.

#         Parameters:
#             instance_name (str): full name of the instance.

#         Returns:
#             int: instance number.
#         """
#         tokens = instance_name.split("-")
#         if len(tokens) >= 3 and tokens[2].isdigit():
#             return int(tokens[2])
#         else:
#             return None

#     def get_base_name(self, instance_name):
#         """
#         Get instance base name (guest).

#         Parameters:
#             instance_name (str): full name of the instance.

#         Returns:
#             str: instance guest name.
#         """
#         tokens = instance_name.split("-")
#         if len(tokens) == 3:
#             return tokens[2]
#         elif len(tokens) >= 4:
#             return tokens[3]
#         else:
#             return None

#     def get_copy(self, instance_name):
#         """
#         Get instance copy.

#         Parameters:
#             instance_name (str): full name of the instance.

#         Returns:
#             int: instance copy number.
#         """
#         tokens = instance_name.split("-")
#         if len(tokens) >= 5 and tokens[4].isdigit():
#             return int(tokens[4])
#         else:
#             return 1

#     def get_student_access_name(self):
#         """
#         Returns student access machine full name.

#         Returns:
#             str: student access machine name.
#         """
#         return f"{self.institution}-{self.lab_name}-student_access"

#     def get_teacher_access_name(self):
#         """
#         Returns teacher access machine full name.

#         Returns:
#             str: teacher access machine name.
#         """
#         return f"{self.institution}-{self.lab_name}-teacher_access"

#     def get_service_name(self, service):
#         """
#         Returns service machine full name.

#         Returns:
#             str: service machine name.
#         """
#         return f"{self.institution}-{self.lab_name}-{service}"

#     def get_services_to_deploy(self):
#         "Return services name to be deploy"
#         services = []
#         if self.deploy_elastic:
#             services.append("elastic")
#             if self.monitor_type == "traffic" and self.platform == "aws":
#                 services.append("packetbeat")
#         if self.deploy_caldera:
#             services.append("caldera")
#         return services
    
#     def parse_machines(self, instances=None, guests=(), copies=None, only_instances=True, exclude=[]):
#         """
#         Return machines names based on instance number, guest name and number of copy.

#         Parameters:
#             instances (list(int)): numbers of instances.
#             guests (tuple(str)): guest name of machines.
#             copies (list(int)): number of copy of the machines.
#             only_instances (bool): if true return only scenario machines. Otherwise also return aux machines.
#             exclude (list(str)): full name of machines to exclude.

#         Returns:
#             list(str): full name of machines.
#         """
#         if instances is None:
#             instances = []
#         infrastructure_guests_names = []
#         if self.platform == "aws":
#             infrastructure_guests_names = []
#             if self.is_student_access():
#                 infrastructure_guests_names.append("student_access")
#             if self.teacher_access == "host":
#                 infrastructure_guests_names.append("teacher_access")
#         for service in self.get_services_to_deploy():
#             infrastructure_guests_names.append(service)

#         if guests is None:
#             guests = ()
#         guests_aux = list(self.guest_settings.keys())
#         if not only_instances:
#             guests_aux = guests_aux + infrastructure_guests_names
#         if instances and max(instances) > self.instance_number:
#             raise DescriptionException("Invalid instance number specified.")
#         if not set(guests).issubset(set(guests_aux)):
#             raise DescriptionException("Invalid guests names specified.")
#         max_guest_copy = 0
#         for guest in guests or guests_aux:
#             guest_copies = self.get_guest_attr(guest, "copies", 0)
#             if guest_copies > max_guest_copy:
#                 max_guest_copy = guest_copies
#         if copies and max_guest_copy > 0 and max(copies) > max_guest_copy:
#             raise DescriptionException("Invalid copies specified.")

#         if max_guest_copy == 0 and copies and copies != [1]:
#             # The user specified a copy number other than one, but
#             # no guest has copies defined.
#             raise DescriptionException(
#                 "No machines with the specified characteristics were found."
#             )

#         result = []
#         for instance_num in self.get_instance_range():
#             for guest_name in self.guest_settings.keys():
#                 for copy in self.get_copy_range(guest_name):
#                     result.append(self.get_instance_name(instance_num, guest_name, copy))

#         if not only_instances :
#             if self.platform == "aws":
#                 result.append(self.get_student_access_name())
#                 if self.teacher_access == "host":
#                     result.append(self.get_teacher_access_name())

#             services = self.get_services_to_deploy()
#             for service in services:
#                 result.append(self.get_service_name(service))

#         if instances is not None and instances != []:
#             instance_re = f"^{self.institution}-{self.lab_name}-({'|'.join(str(instance) for instance in instances)})-"
#             result = list(
#                 filter(
#                     lambda machine: re.search(instance_re, machine) is not None, result
#                 )
#             )

#         if guests:
#             guest_re = (
#                 rf"^{self.institution}-{self.lab_name}(-\d+)?-({'|'.join(guests)})(-|$)"
#             )
#             result = list(
#                 filter(lambda machine: re.search(guest_re, machine) is not None, result)
#             )

#         if copies:
#             one_copy_re = rf"^{self.institution}-{self.lab_name}-\d+-[^-]+$"
#             many_copies_re = rf"^{self.institution}-{self.lab_name}-\d+-[^-]+-({'|'.join(str(copy) for copy in copies)})$"
#             result = list(
#                 filter(
#                     lambda machine: re.search(
#                         many_copies_re
#                         if (self.get_guest_copies(self.get_base_name(machine)) > 1)
#                         or (1 not in copies)
#                         else one_copy_re,
#                         machine,
#                     )
#                     is not None,
#                     result,
#                 )
#             )

#         for machine in exclude:
#             guest_re = (
#                 rf"^{self.institution}-{self.lab_name}(-\d+)?-{machine}(-|$)"
#             )
#             result = list(
#                 filter(lambda machine: re.search(guest_re, machine) is None, result)
#             )

#         if len(result) == 0:
#             raise DescriptionException(
#                 "No machines with the specified characteristics were found."
#             )
#         else:
#             return result

#     def get_machines_to_monitor(self):
#         """Returns the list of machines that have the monitor attribute set."""
#         monitor = []
#         for guest_name, guest in self.guest_settings.items():
#             if guest and guest.get("monitor"):
#                 monitor.append(guest_name)
#         return monitor

#     def get_red_team_machines(self):
#         """Returns the list of machines that have the red_team_agent set."""
#         red_team = []
#         for guest_name, guest in self.guest_settings.items():
#             if guest and guest.get("red_team_agent", False):
#                 red_team.append(guest_name)
#         return red_team

#     def get_blue_team_machines(self):
#         """Returns the list of machines that have the blue_team_agent set."""
#         blue_team = []
#         for guest_name, guest in self.guest_settings.items():
#             if guest and guest.get("blue_team_agent", False):
#                 blue_team.append(guest_name)
#         return blue_team

#     def get_guest_username(self, guest_name):
#         """
#         Returns username to connect to guest.

#         Parameters:
#             guest_name (str): guest name.

#         Returns:
#             str: username
#         """
#         if guest_name in self.get_services_to_deploy():
#             base_os = self.get_service_base_os(guest_name)
#         else:
#             base_os = self.get_guest_attr(guest_name, "base_os", self.default_os)
#         os_data = OS_DATA.get(base_os)
#         if not os_data:
#             raise DescriptionException(f"Invalid operating system {base_os}.")

#         return os_data["username"]

#     def get_guest_networks(self, guest_name):
#         """
#         Returns the name of all the networks the guest is connected to.

#         Parameters:
#             guest_name (str): name of the guest

#         Returns:
#             list(str): networks for the guest
#         """
#         networks = []
#         for network in self.topology:
#             if guest_name in network["members"]:
#                 networks.append(network["name"])
#         return networks

#     def is_internet_access(self):
#         """
#         Return if internet access is required

#         Returns:
#             bool: True if internet access is required for any guest; False otherwhise.
#         """
#         for guest in self.guest_settings.values():
#             if guest and guest.get("internet_access"):
#                 return True
#         return False
    
#     def is_student_access(self):
#         """
#         Return if student access is required

#         Returns:
#             bool: True if student access is required for any guest; False otherwhise.
#         """
#         for guest in self.guest_settings.values():
#             if guest and guest.get("entry_point"):
#                 return True
#         return False

#     def get_subnetwork_name(self, instance_num, network_name):
#         """Returns the name of the instance subnetwork."""
#         return f"{self.institution}-{self.lab_name}-{instance_num}-{network_name}"

#     def _compute_subnetworks(self):
#         """Compute the complete list of subnetworks."""
#         subnets = {}

#         new_subnet_bits = math.ceil(math.log2(len(self.topology)))
#         for instance_num in self.get_instance_range():
#             instance_network = list(
#                 ipaddress.ip_network(self.network_cidr_block).subnets(prefixlen_diff=8)
#             )[instance_num]
#             instance_subnets = list(instance_network.subnets(new_subnet_bits))
#             for i, n in enumerate(self.topology):
#                 subnet_name = self.get_subnetwork_name(instance_num, n["name"])
#                 subnets[subnet_name] = str(instance_subnets[i])

#         return subnets

#     def _expand_topology(self):
#         """Expand network members with copies"""
#         for n in self.topology:
#             n["members"] = [
#                 member
#                 for member in n["members"]
#                 for copy in range(self.get_guest_copies(member))
#             ]

#     def get_topology_network(self, network_name):
#         """Returns the topology information of the network."""
#         for n in self.topology:
#             if n["name"] == network_name:
#                 return n
#         return None

#     def _get_ipv4_subnet(self, instance_num, network_name):
#         """Returns an IPv4Network object for an instance network."""
#         return ipaddress.ip_network(
#             self.subnets[self.get_subnetwork_name(instance_num, network_name)]
#         )

#     def get_instance_ip_address(self, instance_num, guest_name, copy, network):
#         """Compute the IP address of the given instance in the network."""
#         hostnum = network["members"].index(guest_name) + (copy - 1) + 3
#         return str(
#             list(self._get_ipv4_subnet(instance_num, network["name"]).hosts())[hostnum]
#         )

#     def get_guest_data(self):
#         """Compute the guest data as expected by the deployment terraform module."""

#         guest_data = {}
#         entry_point_index = 1
#         services_network_index = 1
#         for instance_num in self.get_instance_range():
#             for base_name, guest in self.guest_settings.items():
#                 for copy in self.get_copy_range(base_name):
#                     guest_name = self.get_instance_name(instance_num, base_name, copy)
#                     interfaces = {}
#                     for index, network in enumerate([n for n in self.topology if base_name in n["members"]]):
#                         private_ip = self.get_instance_ip_address(instance_num, base_name, copy, network)
#                         interface = {
#                             "name": f"{guest_name}-{index + 1}",
#                             "index": index + self._get_interface_index_to_sum(base_name),
#                             "guest_name": guest_name,
#                             "network_name": network["name"],
#                             "subnetwork_name": f"{self.institution}-{self.lab_name}-{instance_num}-{network['name']}",
#                             "private_ip": private_ip,
#                             "mask": self._get_ipv4_subnet(instance_num, network["name"]).prefixlen,
#                         }
#                         interfaces[interface["name"]] = interface

#                     memory = self.get_guest_attr(base_name, "memory", 1024)
#                     vcpus = self.get_guest_attr(base_name, "vcpu", 1)
#                     gpu = self.get_guest_attr(base_name, "gpu", False)
#                     monitor = self.get_guest_attr(base_name, "monitor", False)
#                     is_in_services_network = self.is_in_services_network(base_name)
#                     is_entry_point = self.get_guest_attr(base_name, "entry_point", False)
#                     guest_data[guest_name] = {
#                         "guest_name": guest_name,
#                         "base_name": base_name,
#                         "instance": instance_num,
#                         "copy": copy,
#                         "hostname": self.get_hostname(instance_num, base_name, copy),
#                         "entry_point": is_entry_point,
#                         "entry_point_index": entry_point_index,
#                         "internet_access": self.get_guest_attr(base_name, "internet_access", False),
#                         "base_os": self.get_guest_attr(base_name, "base_os", self.default_os),
#                         "interfaces": interfaces,
#                         "memory": memory,
#                         "vcpu": vcpus,
#                         "disk": self.get_guest_attr(base_name, "disk", 10),
#                         "instance_type": self.instance_type.get_guest_instance_type(memory,
#                                                                                     vcpus,
#                                                                                     gpu,
#                                                                                     monitor,
#                                                                                     self.monitor_type
#                                                                                     ),
#                         "advanced_options_file": self._get_guest_advanced_options_file(base_name),
#                         "is_in_services_network" : is_in_services_network,
#                         "services_network_index": services_network_index
#                     }
#                     if is_entry_point:
#                         entry_point_index += 1
#                     if is_in_services_network:
#                         services_network_index += 1

#         return guest_data
    
#     def is_in_services_network(self, base_name):
#         return (
#             (self.deploy_elastic and self.monitor_type == "endpoint" and self.get_guest_attr(base_name, "monitor", False)) or 
#             (self.deploy_caldera and (self.get_guest_attr(base_name, "red_team_agent", False) or self.get_guest_attr(base_name, "blue_team_agent", False)))
#         )

#     def _get_interface_index_to_sum(self, base_name):
#         """
#         Returns number to be added to interface index
#         """
#         is_in_services_network = self.is_in_services_network(base_name)
#         if self.platform == "libvirt":
#             base = 3
#             if self.get_guest_attr(base_name, "entry_point", False):
#                 if is_in_services_network:
#                     return base + 2
#                 else:
#                     return base + 1
#             else:
#                 if is_in_services_network:
#                     return base + 1
#                 else:
#                     return base
#         elif self.platform == "aws" or self.platform == "docker":
#             return 0


#     def set_elastic_stack_version(self, version):
#         """
#         Set Elastic Stack version

#         Parameters:
#             version (str): Elastic Stack version
#         """
#         self.elastic_stack_version = version
#         self.is_elastic_stack_latest_version = True

#     def set_caldera_version(self, version):
#         """
#         Set Caldera version

#         Parameters:
#             version (str): Caldera version
#         """
#         self.caldera_version = version

#     def _get_guest_advanced_options_file(self, base_name):
#         """
#         Return path to advanced options for the guest if exists or /dev/null otherwise.

#         Parameters:
#             base_name (str): Machine base name
#         """
#         if self.platform == "libvirt":
#             if (Path(self.advanced_options_path).joinpath(f'{base_name}.xsl')).is_file():
#                 return Path(self.advanced_options_path).joinpath(f'{base_name}.xsl').resolve().as_posix()
#             else:
#                 return "/dev/null" 
#         else:
#                 return "/dev/null"
    
#     def get_parameters(self, instances=None):
#         if not instances:
#             instances = list(range(1,self.instance_number+1))
#         random.seed(self.random_seed)
#         choices = {}
#         for file in self.parameters_files:
#             choices[Path(file).stem] = random.choices(open(file).readlines(),k=self.instance_number)
#         parameters = {}
#         for instance in instances:
#             parameter = {}
#             for choice in choices:
#                 parameter[choice] = json.loads(choices[choice][instance-1])
#             parameters[instance] = parameter
#         return parameters

#     def get_service_base_os(self, service_name):
#         if service_name == "elastic" or service_name == "caldera":
#             return "rocky8"
#         elif service_name == "packetbeat":
#             return "ubuntu22"
        
#     def __del__(self):
#         try:
#             self.extract_tmpdir.cleanup()
#         except:
#             pass





