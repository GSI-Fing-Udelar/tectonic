
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
from tectonic.utils import read_files_in_directory

class DescriptionException(Exception):
    pass


class Description(object):
    """Class to represent a lab description."""

    institution = ""
    lab_name = ""
    instance_number = 0
    default_os = "ubuntu22"
    deploy_elastic = False
    elastic_deployment = {}
    guest_settings = {}
    topology = []

    def __init__(
        self,
        path,
        platform,
        lab_repo_uri,
        teacher_access,
        configure_dns,
        ssh_public_key_file,
        ansible_ssh_common_args,
        aws_region,
        aws_default_instance_type,
        network_cidr_block,
        packetbeat_policy_name,
        packetbeat_vlan_id,
        elastic_stack_version,
        libvirt_uri,
        libvirt_storage_pool,
        libvirt_student_access,
        libvirt_bridge,
        libvirt_external_network,
        libvirt_bridge_base_ip,
        proxy,
        instance_type,
        endpoint_policy_name,
        internet_network_cidr_block,
        services_network_cidr_block,
        keep_ansible_logs,
        docker_uri,
        caldera_version
    ):
        """Create a Description object.

        Description object is created from a lab description file. The lab description file is a YAML file with the following structure.

        Parameters:
            path: Path to the lab edition file.
            platform: Platform to deploy the lab. Valid values are "aws" and "libvirt".
            lab_repo_uri: URI of the lab repository.
            teacher_access: Type of access to the teacher machine. Valid values are "host" and "instance".
            configure_dns: Whether to configure DNS or not.
            ssh_public_key_file: Path to the SSH public key file.
            ansible_ssh_common_args: Ansible SSH common arguments.
            aws_region: AWS region to deploy the lab.
            aws_default_instance_type: Default instance type for AWS.
            network_cidr_block: CIDR block for the lab network.
            packetbeat_policy_name: Name of the Packetbeat policy.
            packetbeat_vlan_id: VLAN ID for Packetbeat.
            elastic_stack_version: Elastic Stack version.
            libvirt_uri: URI for libvirt.
            libvirt_storage_pool: Storage pool for libvirt.
            libvirt_student_access: Type of access to the student machines. Valid values are "bridge" and "nat".
            libvirt_bridge: Name of the bridge for libvirt.
            libvirt_external_network: External network for libvirt.
            libvirt_bridge_base_ip: Base IP for the libvirt bridge.
            proxy: Proxy for libvirt.
            instance_type: An InstanceType object to compute the correct size of machine.
            endpoint_policy_name: Name of the Agent policy.
            internet_network_cidr_block: CIDR of internet network.
            services_network_cidr_block: CIDR of services network.
            keep_ansible_logs: Keep Ansible logs on managed hosts.
            docker_uri: URI for docker.
            caldera_version: Caldera version.

        Returns:
             A Description object.
        """
        self.lab_edition_file = Path(path).resolve().as_posix()
        base_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))
        
        self.lab_repo_uri = lab_repo_uri
        if self.lab_repo_uri and not Path(self.lab_repo_uri).is_absolute():
            self.lab_repo_uri = Path(base_dir).joinpath(
                self.lab_repo_uri
            )
        self.platform = platform
        self.teacher_access = teacher_access
        self.configure_dns = configure_dns
        self.ansible_ssh_common_args = ansible_ssh_common_args
        self.aws_region = aws_region
        self.aws_default_instance_type = aws_default_instance_type
        self.network_cidr_block = network_cidr_block
        self.packetbeat_policy_name = packetbeat_policy_name
        self.packetbeat_vlan_id = packetbeat_vlan_id
        self.elastic_stack_version = elastic_stack_version
        self.is_elastic_stack_latest_version = False
        self.libvirt_uri = libvirt_uri
        self.libvirt_storage_pool = libvirt_storage_pool
        self.libvirt_student_access = libvirt_student_access
        self.libvirt_bridge = libvirt_bridge
        self.libvirt_external_network = libvirt_external_network
        self.libvirt_bridge_base_ip = libvirt_bridge_base_ip
        self.proxy = proxy
        self.instance_type = instance_type
        self.endpoint_policy_name = endpoint_policy_name
        self.internet_network = internet_network_cidr_block
        self.services_network = services_network_cidr_block
        self.keep_ansible_logs = keep_ansible_logs
        self.docker_uri = docker_uri
        self.caldera_version = caldera_version
        self.services = {}
        self._load_lab_edition(path)
        self.description_dir = Path(self.description_file).parent.resolve().as_posix()
        self.ansible_playbooks_path = (
            Path(self.description_dir).joinpath("ansible").resolve().as_posix()
        )

        self.advanced_options_path = Path(self.description_dir).joinpath("advanced").joinpath(platform).resolve().as_posix()

        self.ssh_public_key_file = ssh_public_key_file
        self.authorized_keys = self.read_pubkeys(
            self.teacher_pubkey_dir, ssh_public_key_file
        )

    def read_pubkeys(self, ssh_dir, default_pubkey=None):
        """
        Reads all public keys in the ssh directory of the description folder.

        Parameters:
            ssh_dir (str): Directory to search for public keys.
            default_pubkey (str): Pubkey to use if there are no keys in ssh_dir.

        Returns:
            str: string with the contents of the ssh public keys.
        """
        keys = ""
        if ssh_dir and Path(ssh_dir).is_dir():
            for child in Path(ssh_dir).iterdir():
                if child.is_file():
                    key = child.read_text()
                    if key[-1] != "\n":
                        key += "\n"
                    keys += key

        if default_pubkey is not None:
            p = Path(default_pubkey).expanduser()
            if p.is_file():
                key = p.read_text()
                if key[-1] != "\n":
                    key += "\n"
                keys += key

        return keys

    def _required(self, description, field):
        """
        Check if the field is in the description.

        Parameters:
            description (obj): description.
            field (str): field to be searched.
        """
        if not description.get(field):
            raise DescriptionException(f"{field} not defined.")

    def _validate_value(self, field, value, values):
        if not value in values:
            raise DescriptionException(f'Error in {field} field. The possible values are "{values}" but "{value}" value was assigned.')
        
    def _validate_description(self, description):
        """
        Apply validations to lab description.

        Parameters:
            description (obj): lab description.
        """
        self._required(description, "institution")
        self._required(description, "lab_name")
        self._required(description, "guest_settings")
        self._required(description, "topology")

        self._validate_value("elastic_settings.enable", description.get("elastic_settings",{}).get("enable",False), [True, False])
        self._validate_value("elastic_settings.monitor_type", description.get("elastic_settings",{}).get("monitor_type","traffic"), ["traffic", "endpoint"])
        self._validate_value("caldera_settings.enable", description.get("caldera_settings",{}).get("enable",False), [True, False])

    def _validate_lab_edition(self, lab_edition_info):
        """
        Apply validations to lab edition specification.

        Parameters:
            lab_edition_info (obj): lab edition specification.
        """
        self._required(lab_edition_info, "base_lab")
        self._required(lab_edition_info, "instance_number")
        if lab_edition_info.get("create_student_passwords"):
            self._required(lab_edition_info, "random_seed")
        self._validate_value("elastic_settings.enable", lab_edition_info.get("elastic_settings",{}).get("enable",False), [True, False])
        self._validate_value("caldera_settings.enable", lab_edition_info.get("caldera_settings",{}).get("enable",False), [True, False])


    def _load_description(self, description_file):
        """
        Load lab description file.

        Parameters:
            description_file (str): path to lab description file.
        """
        stream = open(description_file, "r")
        description = yaml.safe_load(stream)
        self._validate_description(description)

        self.base_institution = re.sub("[^a-zA-Z0-9]+", "", description["institution"])
        self.base_lab_name = re.sub("[^a-zA-Z0-9]+", "", description["lab_name"])
        self.default_os = description.get("default_os", self.default_os)
        self.guest_settings = description.get("guest_settings", self.guest_settings)
        self.topology = description.get("topology", self.topology)

        self._load_elastic_settings(description)
        self._load_caldera_settings(description)

    def _load_lab_edition(self, path):
        """
        Load lab edition specification file.

        Parameters:
            path (str): path to lab edition specification file.
        """
        stream = open(path, "r")
        lab_edition_info = yaml.safe_load(stream)
        self._validate_lab_edition(lab_edition_info)

        self.instance_number = lab_edition_info["instance_number"]
        self.base_lab = lab_edition_info["base_lab"]

        self.student_prefix = lab_edition_info.get("student_prefix", "trainee")
        self.student_pubkey_dir = lab_edition_info.get("student_pubkey_dir")
        if self.student_pubkey_dir and not Path(self.student_pubkey_dir).is_absolute():
            self.student_pubkey_dir = (
                Path(self.lab_edition_file)
                .parent.joinpath(self.student_pubkey_dir)
                .resolve()
                .as_posix()
            )

        self.create_student_passwords = lab_edition_info.get(
            "create_student_passwords", False
        )
        self.random_seed = lab_edition_info.get("random_seed")

        # Open the lab directory if it exists, otherwise use a CTF package file
        if Path(self.lab_repo_uri).joinpath(self.base_lab).is_dir():
            self.description_file = Path(self.lab_repo_uri).joinpath(
                self.base_lab, "description.yml"
            )
            self.parameters_files = read_files_in_directory(Path(self.lab_repo_uri).joinpath(self.base_lab,"ansible","parameters"))
        else:
            lab_pkg_file = Path(self.lab_repo_uri).joinpath(f"{self.base_lab}.ctf")
            if Path(lab_pkg_file).is_file():
                pkg = ZipFile(lab_pkg_file)
                # Extract the package to temporary directory
                self.extract_tmpdir = tempfile.TemporaryDirectory(
                    prefix="tectonic", suffix=self.base_lab
                )
                pkg.extractall(path=self.extract_tmpdir.name)
                self.description_file = Path(self.extract_tmpdir.name).joinpath(
                    "description.yml"
                )
                self.parameters_files = read_files_in_directory(Path(self.extract_tmpdir.name,"ansible","parameters"))
            else:
                raise DescriptionException(f"{self.base_lab} not found in {self.lab_repo_uri}.")
        self._load_description(self.description_file)

        self.institution = re.sub(
            "[^a-zA-Z0-9]+",
            "",
            lab_edition_info.get("institution", self.base_institution),
        )
        self.lab_name = re.sub(
            "[^a-zA-Z0-9]+",
            "",
            lab_edition_info.get("lab_edition_name", self.base_lab_name),
        )

        self.teacher_pubkey_dir = lab_edition_info.get("teacher_pubkey_dir")
        if self.teacher_pubkey_dir and not Path(self.teacher_pubkey_dir).is_absolute():
            self.teacher_pubkey_dir = Path(self.lab_edition_file).parent.joinpath(
                self.teacher_pubkey_dir
            )

        self.deploy_elastic = self.deploy_elastic and lab_edition_info.get("elastic_settings",{}).get("enable", True)
        if self.deploy_elastic:
            self.services["elastic"] = {
                "vcpu": lab_edition_info.get("elastic_settings",{}).get("vcpu", 4),
                "memory": lab_edition_info.get("elastic_settings",{}).get("memory", 8192),
                "disk": lab_edition_info.get("elastic_settings",{}).get("disk", 50)
            }
            if self.platform == "aws":
                self.services["packetbeat"] = {
                    "vcpu": 1,
                    "memory": 512,
                    "disk": 10,
                }
        self.deploy_caldera = self.deploy_caldera and lab_edition_info.get("caldera_settings",{}).get("enable", True)
        if self.deploy_caldera:
            self.services["caldera"] = {
                "vcpu": lab_edition_info.get("caldera_settings",{}).get("vcpu", 2),
                "memory": lab_edition_info.get("caldera_settings",{}).get("memory", 2048),
                "disk": lab_edition_info.get("caldera_settings",{}).get("disk", 20)
            }

        self._expand_topology()
        self.subnets = self._compute_subnetworks()

    def _load_elastic_settings(self, description):
        settings = description.get("elastic_settings", {})
        self.deploy_elastic = settings.get("enable",False)
        self.monitor_type = settings.get("monitor_type","traffic")
        self.elastic_deploy_default_policy = settings.get("deploy_default_policy",True)

    def _load_caldera_settings(self, description):
        settings = description.get("caldera_settings", {})
        self.deploy_caldera = settings.get("enable",False)

    def get_instance_range(self):
        """
        Get range for instances.

        Returns:
            range: instance range.
        """
        return range(1, self.instance_number + 1)

    def get_guest_attr(self, guest_name, attr, default=None):
        """
        Get guest specific attribute

        Parameters:
            guest_name (str): machine guest name.
            attr (str): attribute to return.
            default (str, None): default value to return in case attribute is not found.

        Returns:
            any: attribute value for the guest.
        """
        if self.guest_settings.get(guest_name):
            return self.guest_settings[guest_name].get(attr, default)
        else:
            return default

    def get_guest_copies(self, guest_name):
        """
        Get guest number of copies

        Parameters:
            guest_name (str): machine guest name.

        Returns:
            int: copies number.
        """
        return self.get_guest_attr(guest_name, "copies", 1)

    def get_copy_range(self, guest_name):
        """
        Get range for guest instance.

        Parameters:
            guest_name (str): machine guest name.

        Returns:
            range: copy range.
        """
        return range(1, self.get_guest_copies(guest_name) + 1)

    def get_image_name(self, guest_name):
        """
        Get image full name.

        Parameters:
            guest_name (str): machine guest name.

        Returns:
            str: full name.
        """
        return f"{self.institution}-{self.lab_name}-{guest_name}"

    def get_instance_name(self, instance_num, guest_name, copy=1):
        """
        Get machine full name.

        Parameters:
            instance_num (int): machine instance number.
            guest_name (str): machine guest name.
            copy (int): machine copy number.

        Returns:
            str: full name.
        """
        return f"{self.institution}-{self.lab_name}-{instance_num}-{guest_name}" + (
            ("-" + str(copy)) if self.get_guest_copies(guest_name) > 1 else ""
        )

    def get_hostname(self, instance_num, guest_name, copy=1):
        """
        Get hostname.

        Parameters:
            instance_num (int): machine instance number.
            guest_name (str): machine guest name.
            copy (int): machine copy number.

        Returns:
            str: hostname.
        """
        return f"{guest_name}-{instance_num}" + (
            ("-" + str(copy)) if self.get_guest_copies(guest_name) > 1 else ""
        )

    def get_instance_number(self, instance_name):
        """
        Get instance number.

        Parameters:
            instance_name (str): full name of the instance.

        Returns:
            int: instance number.
        """
        tokens = instance_name.split("-")
        if len(tokens) >= 3 and tokens[2].isdigit():
            return int(tokens[2])
        else:
            return None

    def get_base_name(self, instance_name):
        """
        Get instance base name (guest).

        Parameters:
            instance_name (str): full name of the instance.

        Returns:
            str: instance guest name.
        """
        tokens = instance_name.split("-")
        if len(tokens) == 3:
            return tokens[2]
        elif len(tokens) >= 4:
            return tokens[3]
        else:
            return None

    def get_copy(self, instance_name):
        """
        Get instance copy.

        Parameters:
            instance_name (str): full name of the instance.

        Returns:
            int: instance copy number.
        """
        tokens = instance_name.split("-")
        if len(tokens) >= 5 and tokens[4].isdigit():
            return int(tokens[4])
        else:
            return 1

    def get_student_access_name(self):
        """
        Returns student access machine full name.

        Returns:
            str: student access machine name.
        """
        return f"{self.institution}-{self.lab_name}-student_access"

    def get_teacher_access_name(self):
        """
        Returns teacher access machine full name.

        Returns:
            str: teacher access machine name.
        """
        return f"{self.institution}-{self.lab_name}-teacher_access"

    def get_service_name(self, service):
        """
        Returns service machine full name.

        Returns:
            str: service machine name.
        """
        return f"{self.institution}-{self.lab_name}-{service}"

    def get_services_to_deploy(self):
        "Return services name to be deploy"
        services = []
        if self.deploy_elastic:
            services.append("elastic")
            if self.monitor_type == "traffic" and self.platform == "aws":
                services.append("packetbeat")
        if self.deploy_caldera:
            services.append("caldera")
        return services
    
    def parse_machines(self, instances=None, guests=(), copies=None, only_instances=True, exclude=[]):
        """
        Return machines names based on instance number, guest name and number of copy.

        Parameters:
            instances (list(int)): numbers of instances.
            guests (tuple(str)): guest name of machines.
            copies (list(int)): number of copy of the machines.
            only_instances (bool): if true return only scenario machines. Otherwise also return aux machines.
            exclude (list(str)): full name of machines to exclude.

        Returns:
            list(str): full name of machines.
        """
        if instances is None:
            instances = []
        infrastructure_guests_names = []
        if self.platform == "aws":
            infrastructure_guests_names = ["student_access"]
            if self.teacher_access == "host":
                infrastructure_guests_names.append("teacher_access")
        for service in self.get_services_to_deploy():
            infrastructure_guests_names.append(service)

        if guests is None:
            guests = ()
        guests_aux = list(self.guest_settings.keys())
        if not only_instances:
            guests_aux = guests_aux + infrastructure_guests_names
        if instances and max(instances) > self.instance_number:
            raise DescriptionException("Invalid instance number specified.")
        if not set(guests).issubset(set(guests_aux)):
            raise DescriptionException("Invalid guests names specified.")
        max_guest_copy = 0
        for guest in guests or guests_aux:
            guest_copies = self.get_guest_attr(guest, "copies", 0)
            if guest_copies > max_guest_copy:
                max_guest_copy = guest_copies
        if copies and max_guest_copy > 0 and max(copies) > max_guest_copy:
            raise DescriptionException("Invalid copies specified.")

        if max_guest_copy == 0 and copies and copies != [1]:
            # The user specified a copy number other than one, but
            # no guest has copies defined.
            raise DescriptionException(
                "No machines with the specified characteristics were found."
            )

        result = []
        for instance_num in self.get_instance_range():
            for guest_name in self.guest_settings.keys():
                for copy in self.get_copy_range(guest_name):
                    result.append(self.get_instance_name(instance_num, guest_name, copy))

        if not only_instances :
            if self.platform == "aws":
                result.append(self.get_student_access_name())
                if self.teacher_access == "host":
                    result.append(self.get_teacher_access_name())

            services = self.get_services_to_deploy()
            for service in services:
                result.append(self.get_service_name(service))

        if instances is not None and instances != []:
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
                        if (self.get_guest_copies(self.get_base_name(machine)) > 1)
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

    def get_machines_to_monitor(self):
        """Returns the list of machines that have the monitor attribute set."""
        monitor = []
        for guest_name, guest in self.guest_settings.items():
            if guest and guest.get("monitor"):
                monitor.append(guest_name)
        return monitor

    def get_red_team_machines(self):
        """Returns the list of machines that have the red_team_agent set."""
        red_team = []
        for guest_name, guest in self.guest_settings.items():
            if guest and guest.get("red_team_agent", False):
                red_team.append(guest_name)
        return red_team

    def get_blue_team_machines(self):
        """Returns the list of machines that have the blue_team_agent set."""
        blue_team = []
        for guest_name, guest in self.guest_settings.items():
            if guest and guest.get("blue_team_agent", False):
                blue_team.append(guest_name)
        return blue_team

    def get_guest_username(self, guest_name):
        """
        Returns username to connect to guest.

        Parameters:
            guest_name (str): guest name.

        Returns:
            str: username
        """
        if guest_name in self.get_services_to_deploy():
            base_os = self.get_service_base_os(guest_name)
        else:
            base_os = self.get_guest_attr(guest_name, "base_os", self.default_os)
        os_data = OS_DATA.get(base_os)
        if not os_data:
            raise DescriptionException(f"Invalid operating system {base_os}.")

        return os_data["username"]

    def get_guest_networks(self, guest_name):
        """
        Returns the name of all the networks the guest is connected to.

        Parameters:
            guest_name (str): name of the guest

        Returns:
            list(str): networks for the guest
        """
        networks = []
        for network in self.topology:
            if guest_name in network["members"]:
                networks.append(network["name"])
        return networks

    def is_internet_access(self):
        """
        Return if internet access is required

        Returns:
            bool: True if internet access is required for any guest; False otherwhise.
        """
        for guest in self.guest_settings.values():
            if guest and guest.get("internet_access"):
                return True
        return False

    def get_subnetwork_name(self, instance_num, network_name):
        """Returns the name of the instance subnetwork."""
        return f"{self.institution}-{self.lab_name}-{instance_num}-{network_name}"

    def _compute_subnetworks(self):
        """Compute the complete list of subnetworks."""
        subnets = {}

        new_subnet_bits = math.ceil(math.log2(len(self.topology)))
        for instance_num in self.get_instance_range():
            instance_network = list(
                ipaddress.ip_network(self.network_cidr_block).subnets(prefixlen_diff=8)
            )[instance_num]
            instance_subnets = list(instance_network.subnets(new_subnet_bits))
            for i, n in enumerate(self.topology):
                subnet_name = self.get_subnetwork_name(instance_num, n["name"])
                subnets[subnet_name] = str(instance_subnets[i])

        return subnets

    def _expand_topology(self):
        """Expand network members with copies"""
        for n in self.topology:
            n["members"] = [
                member
                for member in n["members"]
                for copy in range(self.get_guest_copies(member))
            ]

    def get_topology_network(self, network_name):
        """Returns the topology information of the network."""
        for n in self.topology:
            if n["name"] == network_name:
                return n
        return None

    def _get_ipv4_subnet(self, instance_num, network_name):
        """Returns an IPv4Network object for an instance network."""
        return ipaddress.ip_network(
            self.subnets[self.get_subnetwork_name(instance_num, network_name)]
        )

    def get_instance_ip_address(self, instance_num, guest_name, copy, network):
        """Compute the IP address of the given instance in the network."""
        hostnum = network["members"].index(guest_name) + (copy - 1) + 3
        return str(
            list(self._get_ipv4_subnet(instance_num, network["name"]).hosts())[hostnum]
        )

    def get_guest_data(self):
        """Compute the guest data as expected by the deployment terraform module."""

        guest_data = {}
        entry_point_index = 1
        services_network_index = 1
        for instance_num in self.get_instance_range():
            for base_name, guest in self.guest_settings.items():
                for copy in self.get_copy_range(base_name):
                    guest_name = self.get_instance_name(instance_num, base_name, copy)
                    interfaces = {}
                    for index, network in enumerate([n for n in self.topology if base_name in n["members"]]):
                        private_ip = self.get_instance_ip_address(instance_num, base_name, copy, network)
                        interface = {
                            "name": f"{guest_name}-{index + 1}",
                            "index": index + self._get_interface_index_to_sum(base_name),
                            "guest_name": guest_name,
                            "network_name": network["name"],
                            "subnetwork_name": f"{self.institution}-{self.lab_name}-{instance_num}-{network['name']}",
                            "private_ip": private_ip,
                            "mask": self._get_ipv4_subnet(instance_num, network["name"]).prefixlen,
                        }
                        interfaces[interface["name"]] = interface

                    memory = self.get_guest_attr(base_name, "memory", 1024)
                    vcpus = self.get_guest_attr(base_name, "vcpu", 1)
                    monitor = self.get_guest_attr(base_name, "monitor", False)
                    is_in_services_network = self.is_in_services_network(base_name)
                    is_entry_point = self.get_guest_attr(base_name, "entry_point", False)
                    guest_data[guest_name] = {
                        "guest_name": guest_name,
                        "base_name": base_name,
                        "instance": instance_num,
                        "copy": copy,
                        "hostname": self.get_hostname(instance_num, base_name, copy),
                        "entry_point": is_entry_point,
                        "entry_point_index": entry_point_index,
                        "internet_access": self.get_guest_attr(base_name, "internet_access", False),
                        "base_os": self.get_guest_attr(base_name, "base_os", self.default_os),
                        "interfaces": interfaces,
                        "memory": memory,
                        "vcpu": vcpus,
                        "disk": self.get_guest_attr(base_name, "disk", 10),
                        "instance_type": self.instance_type.get_guest_instance_type(memory,
                                                                                    vcpus,
                                                                                    monitor,
                                                                                    self.monitor_type
                                                                                    ),
                        "advanced_options_file": self._get_guest_advanced_options_file(base_name),
                        "is_in_services_network" : is_in_services_network,
                        "services_network_index": services_network_index
                    }
                    if is_entry_point:
                        entry_point_index += 1
                    if is_in_services_network:
                        services_network_index += 1

        return guest_data
    
    def is_in_services_network(self, base_name):
        return (
            (self.deploy_elastic and self.monitor_type == "endpoint" and self.get_guest_attr(base_name, "monitor", False)) or 
            (self.deploy_caldera and (self.get_guest_attr(base_name, "red_team_agent", False) or self.get_guest_attr(base_name, "blue_team_agent", False)))
        )

    def _get_interface_index_to_sum(self, base_name):
        """
        Returns number to be added to interface index
        """
        is_in_services_network = self.is_in_services_network(base_name)
        if self.platform == "libvirt":
            base = 3
            if self.get_guest_attr(base_name, "entry_point", False):
                if is_in_services_network:
                    return base + 2
                else:
                    return base + 1
            else:
                if is_in_services_network:
                    return base + 1
                else:
                    return base
        elif self.platform == "aws" or self.platform == "docker":
            return 0


    def set_elastic_stack_version(self, version):
        """
        Set Elastic Stack version

        Parameters:
            version (str): Elastic Stack version
        """
        self.elastic_stack_version = version
        self.is_elastic_stack_latest_version = True

    def set_caldera_version(self, version):
        """
        Set Caldera version

        Parameters:
            version (str): Caldera version
        """
        self.caldera_version = version

    def _get_guest_advanced_options_file(self, base_name):
        """
        Return path to advanced options for the guest if exists or /dev/null otherwise.

        Parameters:
            base_name (str): Machine base name
        """
        if self.platform == "libvirt":
            if (Path(self.advanced_options_path).joinpath(f'{base_name}.xsl')).is_file():
                return Path(self.advanced_options_path).joinpath(f'{base_name}.xsl').resolve().as_posix()
            else:
                return "/dev/null" 
        else:
                return "/dev/null"
    
    def get_parameters(self, instances=None):
        if not instances:
            instances = list(range(1,self.instance_number+1))
        random.seed(self.random_seed)
        choices = {}
        for file in self.parameters_files:
            choices[Path(file).stem] = random.choices(open(file).readlines(),k=self.instance_number)
        parameters = {}
        for instance in instances:
            parameter = {}
            for choice in choices:
                parameter[choice] = json.loads(choices[choice][instance-1])
            parameters[instance] = parameter
        return parameters

    def get_service_base_os(self, service_name):
        if service_name == "elastic" or service_name == "caldera":
            return "rocky8"
        elif service_name == "packetbeat":
            return "ubuntu22"
        
