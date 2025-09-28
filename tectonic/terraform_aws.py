
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

from tectonic.terraform import Terraform
import json

class TerraformAWSException(Exception):
    pass

class TerraformAWS(Terraform):
    """
    Terraform class.

    Description: manages interaction with Terraform to deploy/destroy scenarios.
    """

    def __init__(self, config, description):
        """
        Initialize the Terraform object.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
        """
        super().__init__(config, description)

    def _get_machine_resources_name(self, instances, guests, copies):
        """
        Returns the name of the aws_instance resource of the AWS Terraform module for the instances.

        Parameters:
          instances (list(int)): instances to use.
          guests (list(str)): guests names to use.
          copies (list(int)): copies numbers to use.

        Returns:
          list(str): resources name of the aws_instances for the instances.
        """
        exclude = []
        for _, service in self.description.services_guests.items():
            exclude.append(service.base_name)
        for _, extra in self.description.extra_guests.items():
            exclude.append(extra.base_name)
        machines = self.description.parse_machines(instances, guests, copies, False, exclude)
        resources = []
        for machine in machines:
            resources.append('aws_instance.machines["' f"{machine}" '"]')
        # student_access_name = f"{self.description.institution}-{self.description.lab_name}-student_access"
        # teacher_access_name = f"{self.description.institution}-{self.description.lab_name}-teacher_access"
        # if student_access_name in machines:
        #     resources.remove('aws_instance.machines["' f"{student_access_name}" '"]')
        #     resources.append("aws_instance.student_access[0]")
        # if teacher_access_name in machines:
        #     resources.remove('aws_instance.machines["' f"{teacher_access_name}" '"]')
        #     resources.append("aws_instance.teacher_access_host[0]")
        return resources

    def _get_route_table_resources_name(self, instances):
        """
        Returns the name of the aws_route_table resource of the AWS Terraform module for the instances.

        Parameters:
          instances (list(int)): instances to use.

        Returns:
          list(str): resources name of the aws_route_table for the instances.
        """
        resources = []
        for instance in filter(
            lambda i: i <= self.description.instance_number,
            instances or range(1, self.description.instance_number + 1),
        ):
            for network in self.description.topology.keys():
                resources.append(
                    'aws_route_table_association.scenario_internet_access["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network}"
                    '"]'
                )
        return resources

    def _get_dns_resources_name(self, instances):
        """
        Returns the name of the aws dns resource of the AWS Terraform module for the instances.

        Parameters:
          instances (list(str)): instances to use.

        Returns:
          list(str): resources name of the aws dns resources for the instances.
        """
        resources = ["aws_route53_zone.reverse[0]"]
        for network in self.description.topology.keys():
            resources.append(
                'aws_route53_zone.zones["{name}"]'.format(name=network)
            )
        for instance in filter(
            lambda i: i <= self.description.instance_number,
            instances or range(1, self.description.instance_number + 1),
        ):
            for _, guest in self.description.scenario_guests.items():
                for _, interface in guest.interfaces.items():
                    if guest.copies == 1:
                        resources.append(
                            'aws_route53_record.records["'
                            f"{guest.name}-{str(instance)}-{interface.network.name}"
                            '"]'
                        )
                        resources.append(
                            'aws_route53_record.records_reverse["'
                            f"{guest.name}-{str(instance)}-{interface.network.name}"
                            '"]'
                        )
                    else:
                        for copy in range(1, guest.copies + 1):
                            resources.append(
                                'aws_route53_record.records["'
                                f"{guest.name}-{str(copy)}-{str(instance)}-{interface.network.name}"
                                '"]'
                            )
                            resources.append(
                                'aws_route53_record.records_reverse["'
                                f"{guest.name}-{str(copy)}-{str(instance)}-{interface.network.name}"
                                '"]'
                            )
        return resources

    def _get_security_group_resources_name(self, instances):
        """
        Returns the name of the aws_security_group resource of the AWS Terraform module for the instances.

        Parameters:
          instances (list(str)): instances to use.

        Returns:
          list(str): resources name of the aws_security_group for the instances.
        """
        resources = []
        instances = instances or range(1, self.description.instance_number + 1)
        for _, guest in self.description.scenario_guests.items():
            if guest.instance in instances:
                for _, interface in guest.interfaces.items():
                    resources.append(
                        'aws_security_group.interface_traffic["'
                        f"{interface.name}"
                        '"]'
                    )
            # for network in self.description.topology.keys():
            #     resources.append(
            #         'aws_security_group.interface_traffic["'
            #         f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network}"
            #         '"]'
            #     )
        return resources

    def _get_subnet_resources_name(self, instances):
        """
        Returns the name of the aws_subnet resource of the AWS Terraform module for the instances.

        Parameters:
          instances (list(str)): instances to use.

        Returns:
          list(str): resources name of the aws_subnet for the instances.
        """
        resources = []
        for instance in filter(lambda i: i <= self.description.instance_number, instances or range(1, self.description.instance_number + 1)):
            for network in self.description.topology.keys():
                resources.append(
                    'aws_subnet.instance_subnets["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network}"
                    '"]'
                )
        return resources

    def _get_interface_resources_name(self, instances):
        """
        Returns the name of the aws_network_interface resource of the AWS Terraform module for the instances.

        Parameters:
          instances (list(str)): instances to use.

        Returns:
          list(str): resources name of the aws_network_interface for the instances.
        """
        resources = []
        for _, guest in self.description.scenario_guests.items():
            if instances and guest.instance not in instances:
                continue
            for _, interface in guest.interfaces.items():
                resources.append(f"aws_network_interface.interfaces[\"{interface.name}\"]")

        return resources
    
    def _get_resources_to_target_apply(self, instances):
        """
        Returns the name of the aws resource of the AWS Terraform module to target apply base on the instances number.

        Parameters:
            instances (list(int)): instances to use.
        
        Return:
            list(str): names of resources.
        """
        resources = [
            "module.vpc",
            "aws_instance.student_access[0]",
            "aws_security_group.bastion_host_sg",
            "aws_security_group.teacher_access_sg",
            "aws_key_pair.admin_pubkey",
            "aws_security_group.entry_point_sg",
        ]
        resources = resources + self._get_interface_resources_name(instances)
        resources = resources + self._get_subnet_resources_name(instances)
        resources = resources + self._get_security_group_resources_name(instances)
        resources = resources + self._get_machine_resources_name(instances, None, None)
        if self.config.aws.teacher_access == "endpoint":
            resources.append("aws_ec2_instance_connect_endpoint.teacher_access[0]")
        else:
            resources.append("aws_instance.teacher_access_host[0]")
        if self.description.internet_access_required:
            resources.append("aws_route_table.scenario_internet_access[0]")
            resources.append("aws_security_group.internet_access_sg[0]")
            resources = resources + self._get_route_table_resources_name(instances)
        if self.config.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources
    
    def _get_resources_to_target_destroy(self, instances):
        """
        Returns the name of the aws resource of the AWS Terraform module to target destroy base on the instances number.

        Parameters:
            instances (list(int)): instances to use.
        
        Return:
            list(str): names of resources.
        """
        resources = self._get_machine_resources_name(instances, None, None)
        # resources = resources + self._get_interface_resources_name(instances) #TODO: fix this. If interfaces are added to be removed then all machines are removed.
        if self.config.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources

    def _get_resources_to_recreate(self, instances, guests, copies):
        """
        Returns the name of the aws resource of the AWS Terraform module to recreate base on the machines names.

        Parameters:
          instances (list(int)): instances number to use.
          guests (list(str)): guests names to use.
          copies (list(int)): copies numbers to use.

        Returns:
          list(str): resources name to recreate.
        """
        resources = self._get_machine_resources_name(instances, guests, copies)
        if "student_access" in guests:
            resources.append("aws_instance.student_access[0]")
        if "teacher_access" in guests and self.config.aws.teacher_access == "host":
            resources.append("aws_instance.teacher_access_host[0]")
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
        result["services_network_cidr_block"] = self.config.services_network_cidr_block
        result["internet_network_cidr_block"] = self.config.internet_network_cidr_block
        result["teacher_access"] = self.config.aws.teacher_access
        result["services_internet_access"] = self.description.elastic.enable
        result["monitor_type"] = self.description.elastic.monitor_type
        return result
    
    def _get_guest_variables(self, guest):
        """
        Return guest variables for terraform.

        Parameters:
          guest (GuestDescription): guest to get variables.

        Returns:
          dict: variables.
        """
        result = super()._get_guest_variables(guest)
        result["entry_point"] = guest.entry_point
        result["instance_type"] = guest.instance_type
        result["internet_access"] = guest.internet_access
        result["instance"] = guest.instance
        return result

    def _get_network_interface_variables(self, interface):
        """
        Return network interface variables for terraform.

        Parameters:
          interface (NetworkInterface): interface to get variables.

        Returns:
          dict: variables.
        """
        result = super()._get_network_interface_variables(interface)
        result["network_name"] = interface.network.name
        result["guest_name"] = interface.guest_name
        result["index"] = interface.index
        result["traffic_rules"] = [self._get_traffic_rules(rule) for rule in interface.traffic_rules]
        result["instance"] = interface.network.instance
        return result
    
    def _get_traffic_rules(self, traffic_rule):
        """
        Return rule of security group for terraform.

        Parameters:
          fw_rule (TrafficRule): traffic rule to get variables.

        Returns:
          dict: variables.
        """
        result = {}
        result["name"] = traffic_rule.name
        result["description"] = traffic_rule.description
        result["network_cidr"] = traffic_rule.network_cidr
        result["from_port"] = traffic_rule.from_port
        result["to_port"] = traffic_rule.to_port
        result["protocol"] = traffic_rule.protocol
        return result