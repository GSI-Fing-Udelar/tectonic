
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

import importlib.resources as tectonic_resources

from tectonic.packer import Packer

class PackerAWSException(Exception):
    pass

class PackerAWS(Packer):
    """
    Packer class.

    Description: manages interaction with Packer to build images.
    """

    def __init__(self, config, description, client, packer_executable_path="packer"):
        """
        Initialize the packer object.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
            client (Client): Tectonic client object
            packer_executable_path (str): Path to the packer executable on the S.O. Default: packer
        """
        super().__init__(config, description, client, packer_executable_path)

    def create_instance_image(self, guests):
        """
        Create instances images.

        Parameters:
            guests (list(str)): names of the guests for which to create images. 
        """
        super().create_instance_image(guests)
        self.client.delete_security_groups("Temporary group for Packer")

    def create_service_image(self, services):
        """
        Create services images.

        Parameters:
            services (list(str)): names of the services for which to create images. 
        """
        super().create_instance_image(services)
        self.client.delete_security_groups("Temporary group for Packer")

    def _get_instance_machines(self, guests):
        """
        Return machines for creating instances images.

        Parameters:
            guests (list(str)): names of the guests for which to create images.

        Returns:
            dict: machines dictionary.
        """
        machines = {}
        for guest_name in guests:
            monitor = True if self.description.deploy_elastic and self.description.get_guest_attr(guest_name, "monitor", False) and self.description.monitor_type == "endpoint" else False
            machines[guest_name] = {
                "base_os": self.description.get_guest_attr(guest_name, "base_os", self.description.default_os),
                "endpoint_monitoring" : monitor,
            }
            machines[guest_name]["disk"] = self.description.get_guest_attr(guest_name, "disk", 8)
            machines[guest_name]["instance_type"] = self.description.instance_type.get_guest_instance_type(
                self.description.get_guest_attr(guest_name, "memory", 1),
                self.description.get_guest_attr(guest_name, "vcpu", 1),
                self.description.get_guest_attr(guest_name, "gpu", False),
                monitor,
                self.description.monitor_type,
            )
        return machines
    
    def _get_service_machines(self, services):
        """
        Return machines for creating services images.

        Parameters:
            services (list(str)): names of the services for which to create images.

        Returns:
            dict: machines dictionary.
        """
        machines = {}
        for service in services:
            machines[service] = {
                "base_os": self.description.get_service_base_os(service),
                "ansible_playbook": str(tectonic_resources.files('tectonic') / 'services' / service / 'base_config.yml'),
            }
            machines[service]["disk"] = self.description.services[service]["disk"]
            if service in ["caldera", "elastic"]:
                machines[service]["instance_type"] = self.description.instance_type.get_guest_instance_type(self.description.services[service]["memory"], self.description.services[service]["vcpu"], False, False, self.description.monitor_type)
            elif service == "packetbeat":
                machines[service]["instance_type"] = "t2.micro"
        return machines