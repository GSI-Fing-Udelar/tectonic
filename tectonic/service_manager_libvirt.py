
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

import json
import ipaddress
from tectonic.constants import OS_DATA

from tectonic.service_manager import ServiceManager

class ServiceManagerLibvirt(Exception):
    pass

class ServiceManagerLibvirt(ServiceManager):
    """
    ServiceManagerLibvirt class.

    Description: manages services instances for Libvirt.
    """

    def __init__(self, config, description, client):
        super().__init__(config, description, client)

    def get_resources_to_target_apply(self, instances):
        """
        Get resources name for target apply.

        Parameters:
            instances (list(int)): number of the instances to target apply.
        
        Return:
            list(str): names of resources.
        """
        resources = []
        for service in self._get_services_guest_data():
            resources.append('libvirt_volume.cloned_image["'f"{service}"'"]')
            resources.append('libvirt_cloudinit_disk.commoninit["'f"{service}"'"]')
            resources.append('libvirt_domain.machines["'f"{service}"'"]')
        for network in self._get_services_network_data():
            resources.append('libvirt_network.subnets["'f"{network}"'"]')
        return resources

    def get_resources_to_target_destroy(self, instances):
        """
        Get resources name for target destroy.

        Parameters:
            instances (list(int)): number of the instances to target destroy.
        
        Return:
            list(str): names of resources.
        """
        return []
    
    def get_terraform_variables(self):
        """
        Get variables to use in Terraform.

        Return:
            dict: variables.
        """
        return {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "ssh_public_key_file": self.description.ssh_public_key_file,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps(self._get_services_network_data()),
            "guest_data_json": json.dumps(self._get_services_guest_data()),
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.description.configure_dns,
            "libvirt_uri": self.description.libvirt_uri,
            "libvirt_storage_pool": self.description.libvirt_storage_pool,
        }
    
    def _get_services_network_data(self):
        """
        Compute the complete list of services subnetworks.

        Returns:
            dict: services network data.
        """
        #TODO: ver si se puede mejorar 
        networks = {
            f"{self.description.institution}-{self.description.lab_name}-services" : {
                "cidr" : self.description.services_network,
                "mode": "none"
            },
        }
        if self.description.deploy_elastic:
            networks[f"{self.description.institution}-{self.description.lab_name}-internet"] = {
                "cidr" : self.description.internet_network,
                "mode" : "nat",
            }
        return networks
    
    def _get_services_guest_data(self):
        """
        Compute the services guest data as expected by the deployment terraform module.

        Returns:
            dict: services guest data.
        """
        #TODO: ver si se puede mejorar 
        guest_data = {}
        if self.description.deploy_elastic:
            guest_data[self.description.get_service_name("elastic")] = {
                    "guest_name": self.description.get_service_name("elastic"),
                    "base_name": "elastic",
                    "hostname": "elastic",
                    "base_os": self.description.get_service_base_os("elastic"),
                    "interfaces": {
                        f'{self.description.get_service_name("elastic")}-1' : {
                            "name": f'{self.description.get_service_name("elastic")}-1',
                            "index": 3,
                            "guest_name": self.description.get_service_name("elastic"),
                            "network_name": "internet",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-internet",
                            "private_ip": str(ipaddress.IPv4Network(self.description.internet_network)[2]),
                            "mask": str(ipaddress.ip_network(self.description.internet_network).prefixlen),
                        },
                        f'{self.description.get_service_name("elastic")}-2' : {
                            "name": f'{self.description.get_service_name("elastic")}-2',
                            "index": 4,
                            "guest_name": self.description.get_service_name("elastic"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[2]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        }
                    },
                    "memory": self.description.services["elastic"]["memory"],
                    "vcpu": self.description.services["elastic"]["vcpu"],
                    "disk": self.description.services["elastic"]["disk"],
                }
        if self.description.deploy_caldera:
            guest_data[self.description.get_service_name("caldera")] = {
                    "guest_name": self.description.get_service_name("caldera"),
                    "base_name": "caldera",
                    "hostname": "caldera",
                    "base_os": self.description.get_service_base_os("caldera"),
                    "interfaces": {
                        f'{self.description.get_service_name("caldera")}-1' : {
                            "name": f'{self.description.get_service_name("caldera")}-1',
                            "index": 3,
                            "guest_name": self.description.get_service_name("caldera"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[4]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        }
                    },
                    "memory": self.description.services["caldera"]["memory"],
                    "vcpu": self.description.services["caldera"]["vcpu"],
                    "disk": self.description.services["caldera"]["disk"],
                }
        return guest_data