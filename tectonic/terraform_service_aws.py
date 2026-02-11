
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

from tectonic.terraform_service import TerraformService
from tectonic.constants import OS_DATA

class TerraformServiceAWSException(Exception):
    pass

class TerraformServiceAWS(TerraformService):
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
        for _, service in self.description.services_guests.items():
            for _, interface in service.interfaces.items():
                resources.append('aws_network_interface.interfaces["'f"{interface.name}"'"]')
        return resources
    
    def _get_machine_resources_name(self):
        """
        Returns the name of the aws_instance resource of the AWS Terraform module.

        Returns:
          list(str): resources name of the aws_instances for the services.
        """
        resources = []
        for service in self.description.services_guests:
                resources.append('aws_instance.machines["'f"{service}"'"]')
        return resources
    
    def _get_security_group_resources_name(self):
        """
        Returns the name of the aws_security_group resource of the AWS Terraform module.

        Returns:
          list(str): resources name of the subnetworks security groups for the services.
        """
        resources = []
        for network_name in self.description.auxiliary_networks:
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
            for _, service in self.description.services_guests.items():
                for _, interface in service.interfaces.items():
                    resources.append('aws_route53_record.records["'f"{service.name}-{interface.network.name}"'"]')
                    resources.append('aws_route53_record.records_reverse["'f"{service.name}-{interface.network.name}"'"]')
        return resources

    def _get_resources_to_target_apply(self, instances):
        """
        Get resources name for target apply.

        Parameters:
            instances (list(int)): number of the instances to target apply.
        
        Return:
            list(str): names of resources.
        """
        resources = [
            "module.vpc",
            "aws_key_pair.pub_key",
            "aws_security_group.services_internet_access_sg[0]",
            "aws_security_group.caldera_scenario_sg",
            "aws_security_group.elastic_endpoint_scenario_sg",
            "aws_security_group.elastic_traffic_scenario_sg",
            "aws_security_group.packetbeat_scenario_sg",
            "aws_security_group.guacamole_scenario_sg",
            "aws_security_group.bastion_host_scenario_sg",
            "aws_eip.bastion_host",
            "aws_eip_association.eip_assoc_bastion_host"
        ]
        resources = resources + self._get_machine_resources_name()
        resources = resources + self._get_security_group_resources_name()
        resources = resources + self._get_interface_resources_name()
        if self.config.configure_dns:
            resources = resources + self._get_dns_resources_name()
        if self.config.aws.teacher_access == "endpoint":
            resources.append("aws_ec2_instance_connect_endpoint.teacher_access[0]")
        return resources
        
    def _get_resources_to_target_destroy(self, instances):
        """
        Get resources name for target destroy.

        Parameters:
            instances (list(int)): number of the instances to target destroy.
        Return:
            list(str): names of resources.
        """
        return []

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
    
    def destroy_packetbeat(self, ansible):
        """
        Destroy Packetbeat for Elastic service network monitoring.

        Parameters:
            ansible (Ansible): Tectonic ansible object.
        """
        return
