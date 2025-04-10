
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

class ServiceManagerDocker(Exception):
    pass

class ServiceManagerDocker(ServiceManager):
    """
    ServiceManagerDocker class.

    Description: manages services instances for Docker.
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
            resources.append('docker_container.machines["'f"{service}"'"]')
            resources.append('docker_image.base_images["'f"{service}"'"]')
        for network in self.description.auxiliary_networks:
            resources.append('docker_network.subnets["'f"{network}"'"]')
        return resources

    def get_resources_to_target_destroy(self, instances, services):
        """
        Get resources name for target destroy.

        Parameters:
            instances (list(int)): number of the instances to target destroy.
            services (list(str)): list of services to destroy
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
        networks = {name: network.to_dict()                    
                    for name, network in self.description.auxiliary_networks}

        return {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "ssh_public_key_file": self.config.ssh_public_key_file,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps(networks),
            "guest_data_json": json.dumps(self._get_services_guest_data()),
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.config.configure_dns,
            "docker_uri": self.config.docker.uri
        }
    
    def _get_services_guest_data(self):
        """
        Compute the services guest data as expected by the deployment terraform module.

        Returns:
            dict: services guest data.
        """
        #TODO: ver si se puede mejorar 
        guest_data = {}
        if self.description.elastic.enable:
            guest_data[self.description.elastic.name] = {
                    "guest_name": self.description.elastic.name,
                    "base_name": "elastic",
                    "hostname": "elastic",
                    "base_os": self.description.elastic.os,
                    "interfaces": {
                        f'{self.description.elastic.name}-1' : {
                            "name": f'{self.description.elastic.name}-1',
                            "guest_name": self.description.elastic.name,
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.config.services_network_cidr_block)[2]),
                            "mask": str(ipaddress.ip_network(self.config.services_network_cidr_block).prefixlen),
                        },
                        f'{self.description.elastic.name}-2' : {
                            "name": f'{self.description.elastic.name}-2',
                            "guest_name": self.description.elastic.name,
                            "network_name": "internet",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-internet",
                            "private_ip": str(ipaddress.IPv4Network(self.config.internet_network_cidr_block)[2]),
                            "mask": str(ipaddress.ip_network(self.config.internet_network_cidr_block).prefixlen),
                        },
                    },
                    "memory": self.description.elastic.memory,
                    "vcpu": self.description.elastic.vcpu,
                    "disk": self.description.elastic.disk,
                    "port": 5601,
                }
        if self.description.caldera.enable:
            guest_data[self.description.caldera.name] = {
                    "guest_name": self.description.caldera.name,
                    "base_name": "caldera",
                    "hostname": "caldera",
                    "base_os": self.description.caldera.os,
                    "interfaces": {
                        f'{self.description.caldera.name}-1' : {
                            "name": f'{self.description.caldera.name}-1',
                            "guest_name": self.description.caldera.name,
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.config.services_network_cidr_block)[4]),
                            "mask": str(ipaddress.ip_network(self.config.services_network_cidr_block).prefixlen),
                        },
                        f'{self.description.caldera.name}-2' : {
                            "name": f'{self.description.caldera.name}-2',
                            "guest_name": self.description.caldera.name,
                            "network_name": "internet",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-internet",
                            "private_ip": str(ipaddress.IPv4Network(self.config.internet_network_cidr_block)[4]),
                            "mask": str(ipaddress.ip_network(self.config.internet_network_cidr_block).prefixlen),
                        },
                    },
                    "memory": self.description.caldera.memory,
                    "vcpu": self.description.caldera.vcpu,
                    "disk": self.description.caldera.disk,
                    "port": 8443,
                }
        return guest_data
