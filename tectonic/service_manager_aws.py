
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


from tectonic.service_manager import ServiceManager
from tectonic.constants import OS_DATA
import importlib.resources as tectonic_resources

class ServiceManagerAWS(Exception):
    pass

class ServiceManagerAWS(ServiceManager):
    """
    ServiceManagerAWS class.

    Description: manages services instances for AWS.
    """

    def __init__(self, config, description, client):
        super().__init__(config, description, client)

    def _get_interface_resources_name(self):
        """
        Returns the name of the aws_network_interface resource of the AWS Terraform module.

        Returns:
          list(str): resources name of the aws_network_interface for the services.
        """
        resources = []
        services_data = self._get_services_guest_data() 
        for service in services_data:
            for interface in services_data[service]["interfaces"]:
                resources.append('aws_network_interface.interfaces["'f"{interface}"'"]')
        return resources
    
    def _get_machine_resources_name(self):
        """
        Returns the name of the aws_instance resource of the AWS Terraform module.

        Returns:
          list(str): resources name of the aws_instances for the services.
        """
        resources = []
        for service in self._get_services_guest_data():
                resources.append('aws_instance.machines["'f"{service}"'"]')
        return resources
    
    def _get_security_group_resources_name(self):
        """
        Returns the name of the aws_security_group resource of the AWS Terraform module.

        Returns:
          list(str): resources name of the subnetworks security groups for the services.
        """
        resources = []
        for network_name in self.decsription.auxiliary_networks:
            resources.append('aws_security_group.subnet_sg["'f"{network_name}"'"]')
        return resources
    
    def _get_dns_resources_name(self):
        """
        Returns the name of the aws dns resource of the AWS Terraform module.

        Returns:
          list(str): resources name of the aws dns resources for the services.
        """
        resources = []
        for _, network in self.description.auxiliary_networks.items():
            resources.append('aws_route53_zone.zones["'f"{network.base_name}"'"]') # TODO - Check name
            services_data = self._get_services_guest_data() 
            for service in services_data:
                interfaces_data = services_data[service]["interfaces"]
                for interface in interfaces_data:
                    resources.append('aws_route53_record.records["'f"{service.split('-')[2]}-{interfaces_data[interface]['network_name']}"'"]')
                    resources.append('aws_route53_record.records_reverse["'f"{service.split('-')[2]}-{interfaces_data[interface]['network_name']}"'"]')
        return resources
    
    def _get_session_resources_name(self, instances):
        """
        Returns the name of the aws_ec2_traffic_mirror_session resource of the AWS Terraform module.

        Parameters:
          instances (list(str)): instances to use.

        Returns:
          list(str): resources name of the aws_ec2_traffic_mirror_session for the services.
        """
        resources = []
        # TODO: Check if this is equivalent to what was before
        for guest in self.description.scenario_guests:
            if instances and guest.instance not in instances:
                continue
            for _, interface in guest.interfaces.items():
                resources.append(f"aws_ec2_traffic_mirror_session.session[\"{interface.name}\"]")

        # TODO: Here
        # for instance in filter(
        #     lambda i: i <= self.description.instance_number,
        #     instances or range(1, self.description.instance_number + 1),
        # ):
        #     for _, guest in  self.description._base_guests.items:
        #         network_index = 1
        #         for _ in self.description.get_guest_networks(guest):
        #             if self.description.get_guest_copies(guest) == 1:
        #                 resources.append(
        #                     'aws_ec2_traffic_mirror_session.session["'
        #                     f"{self.description.institution}-{self.description.lab_name}-{instance}-{guest}-{network_index}"
        #                     '"]'
        #                 )
        #             else:
        #                 for copy in self.description.get_copy_range(guest):
        #                     resources.append(
        #                         'aws_ec2_traffic_mirror_session.session["'
        #                         f"{self.description.institution}-{self.description.lab_name}-{instance}-{guest}-{copy}-{network_index}"
        #                         '"]'
        #                     )
        #             network_index = network_index + 1
        return resources

    def get_resources_to_target_apply(self, instances):
        """
        Get resources name for target apply.

        Parameters:
            instances (list(int)): number of the instances to target apply.
        
        Return:
            list(str): names of resources.
        """
        resources = [
            "aws_security_group.services_internet_access_sg[0]",
            "aws_security_group.caldera_scenario_sg",
            "aws_security_group.elastic_endpoint_scenario_sg",
            "aws_security_group.elastic_traffic_scenario_sg",
        ]
        resources = resources + self._get_machine_resources_name()
        resources = resources + self._get_security_group_resources_name()
        resources = resources + self._get_interface_resources_name()
        if self.config.configure_dns:
            resources = resources + self._get_dns_resources_name()
        if self.description.elastic.enable and self.description.elastic.monitor_type == "traffic":
            resources = resources + [
                "aws_ec2_traffic_mirror_target.packetbeat[0]",
                "aws_ec2_traffic_mirror_filter.filter[0]",
                "aws_ec2_traffic_mirror_filter_rule.filter_all_inbound[0]",
                "aws_ec2_traffic_mirror_filter_rule.filter_all_outbound[0]",
            ]
            resources = resources + self._get_session_resources_name(instances)
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
        resources = []
        if self.description.elastic.enable and self.description.elastic.monitor_type == "traffic":
            resources = resources + self._get_session_resources_name(instances)
        return resources
    
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
            "aws_region": self.config.aws.region,
            "network_cidr_block": self.config.network_cidr_block,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps(networks),
            "guest_data_json": json.dumps(self._get_services_guest_data()),
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.config.configure_dns,
            "monitor_type": self.description.elastic.monitor_type,
            "packetbeat_vlan_id": self.config.aws.packetbeat_vlan_id,
            "machines_to_monitor": [guest_name for guest_name, guest
                                    in self.description.base_guests.items()
                                    if guest.monitor],
            "monitor": self.description.elastic.enable,
        }
    
    def _get_services_guest_data(self):
        """
        Compute the services guest data as expected by the deployment terraform module.

        Returns:
            dict: services guest data.
        """
        #TODO: move to description
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
    
    def _build_packetbeat_inventory(self, ansible, variables):
        """
        Build inventory for Ansible when installing Packetbeat.

        Parameters:
            ansible (Ansible): Tectonic ansible object.
            variables: variables for Ansible playbook.
        """ 
        return ansible.build_inventory(
            machine_list=[self.description.packetbeat.name],
            username=OS_DATA[self.description.packetbeat.os]["username"],
            extra_vars=variables
        )
    
    def _destroy_packetbeat(self, ansible):
        """
        Destroy Packetbeat for Elastic service network monitoring.

        Parameters:
            ansible (Ansible): Tectonic ansible object.
        """
        return
        # It is not necessary to uninstall packetbeat as the machine containing it will be removed

        #TODO: probar a ejecutar directamente el método padre para ver si funciona en AWS 
        # en cuyo caso no sería necesario hacer esta implementación.
