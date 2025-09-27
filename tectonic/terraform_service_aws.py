
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
        for _, guest in self.description.scenario_guests.items():
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

    def _get_resources_to_target_apply(self, instances):
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
        
    def _get_resources_to_target_destroy(self, instances):
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
            resources = self._get_session_resources_name(instances)
        return resources
 
    def _get_terraform_variables(self):
        """
        Get variables to use in Terraform.
        
        Return:
            dict: variables.
        """
        result = super()._get_terraform_variables()
        result["aws_region"] = self.config.aws.region
        result["network_cidr_block"] = self.config.network_cidr_block
        result["configure_dns"] = self.config.configure_dns
        result["monitor_type"] = self.description.elastic.monitor_type
        result["packetbeat_vlan_id"] = self.config.aws.packetbeat_vlan_id
        result["machines_to_monitor"] = [guest_name for guest_name, guest in self.description.base_guests.items() if guest.monitor]
        result["monitor"] = self.description.elastic.enable
        return result
    
    def _get_network_interface_variables(self, interface):
        """
        Return netowkr interface variables for terraform.

        Parameters:
          interface (NetworkInterface): interface to get variables.

        Returns:
          dict: variables.
        """
        result = super()._get_network_interface_variables(interface)
        result["network_name"] = interface.network.name
        result["guest_name"] = interface.guest_name
        result["index"] = interface.index
        return result
    
    def _get_service_machine_variables(self, service):
        """
        Return machines variables deploy services.

        Parameters:
            service (ServiceDescription): services to deploy.

        Returns:
            dict: machines variables.
        """
        result = super()._get_service_machine_variables(service)
        result["instance_type"] = service.instance_type
        result["internet_access"] = service.internet_access
        return result
    
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
