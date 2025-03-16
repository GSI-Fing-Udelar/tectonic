
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

from tectonic.instance_manager import InstanceManager
from tectonic.ssh import interactive_shell
import importlib.resources as tectonic_resources
from tectonic.constants import OS_DATA

class InstanceManagerAWSException(Exception):
    pass

class InstanceManagerAWS(InstanceManager):
    """
    InstanceManagerAWS class.

    Description: manages scenario instances for AWS.
    """

    EIC_ENDPOINT_SSH_PROXY = "aws ec2-instance-connect open-tunnel --instance-id %h"
    
    def __init__(self, config, description, client):
        super().__init__(config, description, client)

    def create_image(self, packer, packer_module, variables):
        """
        Create images using Packer.

        Parameters:
            packer (Packer): Tectonic packer object.
            packer_module (str): path to the Packer module.
            variables (dict): variables of the Packer module.
        """
        super().create_image(packer, packer_module, variables)
        self.client.delete_security_groups("Temporary group for Packer")

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
        machines = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        resources = []
        for machine in machines:
            resources.append('aws_instance.machines["' f"{machine}" '"]')
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
            for network in self.description.topology:
                resources.append(
                    'aws_route_table_association.scenario_internet_access["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network['name']}"
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
        for network in self.description.topology:
            resources.append(
                'aws_route53_zone.zones["{name}"]'.format(name=network["name"])
            )
        for instance in filter(
            lambda i: i <= self.description.instance_number,
            instances or range(1, self.description.instance_number + 1),
        ):
            for guest in self.description.guest_settings.keys():
                for network in self.description.get_guest_networks(guest):
                    if self.description.get_guest_copies(guest) == 1:
                        resources.append(
                            'aws_route53_record.records["'
                            f"{guest}-{str(instance)}-{network}"
                            '"]'
                        )
                        resources.append(
                            'aws_route53_record.records_reverse["'
                            f"{guest}-{str(instance)}-{network}"
                            '"]'
                        )
                    else:
                        for copy in self.description.get_copy_range(guest):
                            resources.append(
                                'aws_route53_record.records["'
                                f"{guest}-{str(copy)}-{str(instance)}-{network}"
                                '"]'
                            )
                            resources.append(
                                'aws_route53_record.records_reverse["'
                                f"{guest}-{str(copy)}-{str(instance)}-{network}"
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
        for instance in filter(
            lambda i: i <= self.description.instance_number,
            instances or range(1, self.description.instance_number + 1),
        ):
            for network in self.description.topology:
                resources.append(
                    'aws_security_group.subnet_sg["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network['name']}"
                    '"]'
                )
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
            for network in self.description.topology:
                resources.append(
                    'aws_subnet.instance_subnets["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network['name']}"
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
        for instance in filter(
            lambda i: i <= self.description.instance_number,
            instances or range(1, self.description.instance_number + 1),
        ):
            for guest in self.description.guest_settings.keys():
                network_index = 1
                for _ in self.description.get_guest_networks(guest):
                    if self.description.get_guest_copies(guest) == 1:
                        resources.append(
                            'aws_network_interface.interfaces["'
                            f"{self.description.institution}-{self.description.lab_name}-{instance}-{guest}-{network_index}"
                            '"]'
                        )
                    else:
                        for copy in self.description.get_copy_range(guest):
                            resources.append(
                                'aws_network_interface.interfaces["'
                                f"{self.description.institution}-{self.description.lab_name}-{instance}-{guest}-{copy}-{network_index}"
                                '"]'
                            )
                    network_index = network_index + 1
        return resources
    
    def get_resources_to_target_apply(self, instances):
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
        if self.description.teacher_access == "endpoint":
            resources.append("aws_ec2_instance_connect_endpoint.teacher_access[0]")
        else:
            resources.append("aws_instance.teacher_access_host[0]")
        if self.description.is_internet_access():
            resources.append("aws_route_table.scenario_internet_access[0]")
            resources.append("aws_security_group.internet_access_sg[0]")
            resources = resources + self._get_route_table_resources_name(instances)
        if self.description.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources
    
    def get_resources_to_target_destroy(self, instances):
        """
        Returns the name of the aws resource of the AWS Terraform module to target destroy base on the instances number.

        Parameters:
            instances (list(int)): instances to use.
        
        Return:
            list(str): names of resources.
        """
        resources = self._get_machine_resources_name(instances, None, None)
        # resources = resources + self._get_interface_resources_name(instances) #TODO: fix this. If interfaces are added to be removed then all machines are removed.
        if self.description.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources

    def get_resources_to_recreate(self, instances, guests, copies):
        """
        Returns the name of the aws resource of the AWS Terraform module to recreate base on the machines names.

        Parameters:
          instances (list(int)): instances number to use.
          guests (list(str)): guests names to use.
          copies (list(int)): copies numbers to use.

        Returns:
          list(str): resources name to recreate.
        """
        machines_to_recreate = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        student_access_name = f"{self.description.institution}-{self.description.lab_name}-student_access"
        teacher_access_name = f"{self.description.institution}-{self.description.lab_name}-teacher_access"
        resource_to_recreate = []
        if student_access_name in machines_to_recreate:
            machines_to_recreate.remove(student_access_name)
            resource_to_recreate.append("aws_instance.student_access[0]")
        if teacher_access_name in machines_to_recreate:
            machines_to_recreate.remove(teacher_access_name)
            resource_to_recreate.append("aws_instance.teacher_access_host[0]")
        for machine in machines_to_recreate:
            resource_to_recreate.append('aws_instance.machines["' f"{machine}" '"]')
        return resource_to_recreate #TODO: use self._get_machine_resources_name()

    def get_terraform_variables(self):
        """
        Get variables to use in Terraform.

        Return:
            dict: variables.
        """
        return {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "instance_number": self.description.instance_number,
            "aws_region": self.description.aws_region,
            "network_cidr_block": self.description.network_cidr_block,
            "services_network_cidr_block": self.description.services_network,
            "internet_network_cidr_block": self.description.internet_network,
            "ssh_public_key_file": self.description.ssh_public_key_file,
            "teacher_access": self.description.teacher_access,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps(self.description.subnets),
            "guest_data_json": json.dumps(self.description.get_guest_data()),
            "aws_default_instance_type": self.description.aws_default_instance_type,
            "default_os": self.description.default_os,
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.description.configure_dns,
            "services_internet_access": self.description.deploy_elastic,
            "monitor_type": self.description.monitor_type,
        }
    
    def console(self, machine_name, username):
        """
        Connect to a specific scenario machine.

        Parameters:
            machine_name (str): name of the machine.
            username (str): username to use. Default: None
        """
        if machine_name == self.description.get_teacher_access_name():
            interactive_shell(self._get_teacher_access_ip(), self._get_teacher_access_username())
        else:
            hostname = self.get_ssh_hostname(machine_name)
            username = username or self.description.get_guest_username(self.description.get_base_name(machine_name))
            if self.description.teacher_access == "host":
                gateway = (self._get_teacher_access_ip(), self._get_teacher_access_username())
            else:
                gateway = self.EIC_ENDPOINT_SSH_PROXY
            if not hostname:
                raise InstanceManagerAWSException(f"Instance {machine_name} not found.")
            interactive_shell(hostname, username, gateway)

    def get_ssh_proxy_command(self):
        """
        Returns the appropriate SSH proxy configuration to access guest machines.

        Return:
            str: ssh proxy command to use.
        """
        if self.description.teacher_access == "endpoint":
            proxy_command = self.EIC_ENDPOINT_SSH_PROXY
        else:
            access_ip = self._get_teacher_access_ip()
            username = self._get_teacher_access_username()
            connection_string = f"{username}@{access_ip}"
            proxy_command = f"ssh {self.description.ansible_ssh_common_args} -W %h:%p {connection_string}"
        return proxy_command
    
    def get_ssh_hostname(self, machine):
        """
        Returns the hostname to use for ssh connection to the machine.

        Parameters:
            machine (str): machine name.

        Return:
            str: ssh hostname to use.
        """
        if self.description.teacher_access == "endpoint":
            return self.client.get_instance_property(machine, "InstanceId")
        else:
            return self.client.get_machine_private_ip(machine)
        
    def _get_teacher_access_username(self):
        """
        Returns username for connection to teacher access host.

        Return:
            str: username to use.
        """
        return OS_DATA[self.description.default_os]["username"]
    
    def _get_teacher_access_ip(self):
        """
        Returns the public IP assigned to the teacher access host.

        Return:
            str: public IP for teacher access.
        """
        if self.description.teacher_access == "host":
            return self.client.get_machine_public_ip(self.description.get_teacher_access_name())
        return None