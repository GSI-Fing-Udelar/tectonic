
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
import click
import ipaddress
import datetime
import math

from tectonic.aws import Client
from tectonic.constants import *
from tectonic.deployment import Deployment
from tectonic.ssh import interactive_shell
from tectonic.utils import create_table
from tectonic.ansible import Ansible

import importlib.resources as tectonic_resources
    


class DeploymentAWSException(Exception):
    pass


class AWSDeployment(Deployment):
    """Deployment class for AWS."""

    EIC_ENDPOINT_SSH_PROXY = "aws ec2-instance-connect open-tunnel --instance-id %h"

    def __init__(
        self,
        description,
        gitlab_backend_url,
        gitlab_backend_username,
        gitlab_backend_access_token,
        packer_executable_path,
    ):
        super().__init__(
            description,
            Client(description),
            gitlab_backend_url,
            gitlab_backend_username,
            gitlab_backend_access_token,
            packer_executable_path,
        )

    def generate_backend_config(self, terraform_dir):
        return super().generate_backend_config(terraform_dir)

    def get_deploy_cr_vars(self):
        """Build the terraform variable dictionary for deployment of the CyberRange."""
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

    def delete_cr_images(self, guests=None):
        guests = guests or self.description.guest_settings.keys()
        for guest_name in guests:
            image_name = self.description.get_image_name(guest_name)
            if not self.can_delete_image(image_name):
                raise DeploymentAWSException(
                    f"Unable to delete image {image_name} because it is being used."
                )
        for guest_name in guests:
            self.client.delete_image(self.description.get_image_name(guest_name))

    def get_instance_status(self, machine):
        """Returns a dictionary with the instance status of machine ID."""
        return self.client.get_instance_status(machine)

    def get_cyberrange_data(self):
        """Get information about cyber range"""
        headers = ["Name", "Value"]
        rows = [["Student Access IP", self.client.get_machine_public_ip(f"{self.description.institution}-{self.description.lab_name}-student_access")]]
        if self.description.teacher_access == "host":
            rows.append(["Teacher Access IP", self.client.get_machine_public_ip(f"{self.description.institution}-{self.description.lab_name}-teacher_access")])
        if len(self.description.get_services_to_deploy()) > 0:
            rows.append(["",""])
            if self.description.deploy_elastic:
                if self.get_instance_status(self.description.get_service_name("elastic")) == "RUNNING":
                    elastic_ip = self.get_ssh_hostname(self.description.get_service_name("elastic"))
                    elastic_credentials = self._get_service_password("elastic")
                    rows.append(["Kibana URL", f"https://{elastic_ip}:5601"])
                    rows.append(["Kibana user (username: password)", f"elastic: {elastic_credentials['elastic']}"])
                    if self.description.deploy_caldera:
                        rows.append(["",""])
                else:
                    return "Unable to get Elastic info right now. Please make sure de Elastic machine is running."
            if self.description.deploy_caldera:
                if self.get_instance_status(self.description.get_service_name("caldera")) == "RUNNING":
                    caldera_ip = self.get_ssh_hostname(self.description.get_service_name("caldera"))
                    caldera_credentials = self._get_service_password("caldera")
                    rows.append(["Caldera URL", f"https://{caldera_ip}:8443"])
                    rows.append(["Caldera user (username: password)", f"red: {caldera_credentials['red']}"])
                    rows.append(["Caldera user (username: password)", f"blue: {caldera_credentials['blue']}"])
                else:
                    return "Unable to get Caldera info right now. Please make sure de Caldera machine is running."
        return create_table(headers,rows)

    def connect_to_instance(self, instance_name, username):
        if instance_name == self.description.get_teacher_access_name():
            interactive_shell(
                self.get_teacher_access_ip(), self.get_teacher_access_username()
            )
            return

        username = username or self.description.get_guest_username(
            self.description.get_base_name(instance_name)
        )
        if self.description.teacher_access == "host":
            hostname = self.client.get_machine_private_ip(instance_name)
            gateway = (self.get_teacher_access_ip(), self.get_teacher_access_username())
        else:
            hostname = self.client.get_instance_property(instance_name, "InstanceId")
            gateway = self.EIC_ENDPOINT_SSH_PROXY

        if not hostname:
            raise DeploymentAWSException(f"Instance {instance_name} not found.")

        interactive_shell(hostname, username, gateway)

    def get_ssh_proxy_command(self):
        if self.description.teacher_access == "endpoint":
            proxy_command = self.EIC_ENDPOINT_SSH_PROXY
        else:
            access_ip = self.get_teacher_access_ip()
            username = self.get_teacher_access_username()
            connection_string = f"{username}@{access_ip}"
            proxy_command = f"ssh {self.description.ansible_ssh_common_args} -W %h:%p {connection_string}"

        return proxy_command

    def get_ssh_hostname(self, machine):
        if self.description.teacher_access == "endpoint":
            return self.client.get_instance_property(machine, "InstanceId")
        else:
            return self.client.get_machine_private_ip(machine)

    def start_instance(self, instance_name):
        self.client.start_instance(instance_name)

    def stop_instance(self, instance_name):
        self.client.stop_instance(instance_name)

    def reboot_instance(self, instance_name):
        self.client.reboot_instance(instance_name)

    def _get_machines_resources_name(self, instances):
        """
        Returns the name of the aws_instance resource of the gsi_lab_aws module for the instances

        Parameters:
          instances (list(int)): instances to use

        Returns:
          list(str): resources name of the aws_instances for the instances
        """
        machines = self.description.parse_machines(instances, None, None, False, self.description.get_services_to_deploy())
        resources = []
        for machine in machines:
            resources.append('aws_instance.machines["' f"{machine}" '"]')
        return resources

    def _get_route_table_resources_name(self, instances):
        """
        Returns the name of the aws_route_table resource of the gsi_lab_aws module for the instances

        Parameters:
          instances (list(int)): instances to use

        Returns:
          list(str): resources name of the aws_route_table for the instances
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
        Returns the name of the aws dns resource of the gsi_lab_aws module for the instances

        Parameters:
          instances (list(str)): instances to use

        Returns:
          list(str): resources name of the aws dns resources for the instances
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
    
    def _get_services_dns_resources_name(self):
        """
        Returns the name of the aws dns resource of the services-aws module

        Returns:
          list(str): resources name of the aws dns resources for the services
        """
        resources = []
        for network in self._get_services_network_data():
            resources.append('aws_route53_zone.zones["'f"{network.split('-')[2]}"'"]')
            services_data = self._get_services_guest_data() 
            for service in services_data:
                interfaces_data = services_data[service]["interfaces"]
                for interface in interfaces_data:
                    resources.append('aws_route53_record.records["'f"{service.split('-')[2]}-{interfaces_data[interface]['network_name']}"'"]')
                    resources.append('aws_route53_record.records_reverse["'f"{service.split('-')[2]}-{interfaces_data[interface]['network_name']}"'"]')
        return resources

    def _get_security_group_resources_name(self, instances):
        """
        Returns the name of the aws_security_group resource of the gsi_lab_aws module for the instances

        Parameters:
          instances (list(str)): instances to use

        Returns:
          list(str): resources name of the aws_security_group for the instances
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
    
    def _get_services_security_group_resources_name(self):
        """
        Returns the name of the aws_security_group resource of the services-aws module for the instances

        Returns:
          list(str): resources name of the subnetworks security groups for the services-aws module
        """
        resources = []
        for network in self._get_services_network_data():
            resources.append('aws_security_group.subnet_sg["'f"{network}"'"]')
        return resources

    def _get_subnet_resources_name(self, instances):
        """
        Returns the name of the aws_subnet resource of the gsi_lab_aws module for the instances

        Parameters:
          instances (list(str)): instances to use

        Returns:
          list(str): resources name of the aws_subnet for the instances
        """
        resources = []
        for instance in filter(
            lambda i: i <= self.description.instance_number,
            instances or range(1, self.description.instance_number + 1),
        ):
            for network in self.description.topology:
                resources.append(
                    'aws_subnet.instance_subnets["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network['name']}"
                    '"]'
                )
        return resources

    def _get_interface_resources_name(self, instances):
        """
        Returns the name of the aws_network_interface resource of the gsi_lab_aws module for the instances

        Parameters:
          instances (list(str)): instances to use

        Returns:
          list(str): resources name of the aws_network_interface for the instances
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
    
    def _get_services_interface_resources_name(self):
        """
        Returns the name of the aws_network_interface resource of the services-aws module


        Returns:
          list(str): resources name of the aws_network_interface for the services
        """
        resources = []
        services_data = self._get_services_guest_data() 
        for service in services_data:
            for interface in services_data[service]["interfaces"]:
                resources.append('aws_network_interface.interfaces["'f"{interface}"'"]')
        return resources
    
    def _get_services_instances_name(self):
        """
        Returns the name of the aws_instance resource of the services-aws module

        Returns:
          list(str): resources name of the aws_instances for the services
        """
        resources = []
        for service in self._get_services_guest_data():
                resources.append('aws_instance.machines["'f"{service}"'"]')
        return resources

    def _get_sessions_resources_name(self, instances):
        """
        Returns the name of the aws_ec2_traffic_mirror_session resource of the services-aws module for the instances

        Parameters:
          instances (list(str)): instances to use

        Returns:
          list(str): resources name of the aws_ec2_traffic_mirror_session for the instances
        """
        resources = []
        for instance in filter(
            lambda i: i <= self.description.instance_number,
            instances or range(1, self.description.instance_number + 1),
        ):
            for guest in self.description.get_machines_to_monitor():
                network_index = 1
                for _ in self.description.get_guest_networks(guest):
                    if self.description.get_guest_copies(guest) == 1:
                        resources.append(
                            'aws_ec2_traffic_mirror_session.session["'
                            f"{self.description.institution}-{self.description.lab_name}-{instance}-{guest}-{network_index}"
                            '"]'
                        )
                    else:
                        for copy in self.description.get_copy_range(guest):
                            resources.append(
                                'aws_ec2_traffic_mirror_session.session["'
                                f"{self.description.institution}-{self.description.lab_name}-{instance}-{guest}-{copy}-{network_index}"
                                '"]'
                            )
                    network_index = network_index + 1
        return resources

    def get_cr_resources_to_target_apply(self, instances):
        """
        Returns the name of the aws resource of the gsi_lab_aws module to target apply base on the instances number

        Parameters:
          instances (list(int)): instances to use

        Returns:
          list(str): resources name to target apply
        """

        resources = [
            "module.vpc",
            "aws_instance.student_access",
            "aws_security_group.bastion_host_sg",
            "aws_security_group.teacher_access_sg",
            "aws_key_pair.admin_pubkey",
            "aws_security_group.entry_point_sg",
        ]
        resources = resources + self._get_interface_resources_name(instances)
        resources = resources + self._get_subnet_resources_name(instances)
        resources = resources + self._get_security_group_resources_name(instances)
        resources = resources + self._get_machines_resources_name(instances)
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

    def get_cr_resources_to_target_destroy(self, instances):
        """
        Returns the name of the aws resource of the gsi_lab_aws module to target destroy base on the instances number

        Parameters:
          instances (list(int)): instances to use

        Returns:
          list(str): resources name to target destroy
        """
        resources = self._get_machines_resources_name(instances)
        # resources = resources + self._get_interface_resources_name(instances) #TODO: fix this. If interfaces are added to be removed then all machines are removed.
        if self.description.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources

    def get_resources_to_recreate(self, instances, guests, copies):
        """
        Returns the name of the aws resource of the gsi_lab_aws module to recreate base on the machines names

        Parameters:
          instances (list(int)): instances to use

        Returns:
          list(str): resources name to recreate
        """
        machines_to_recreate = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        student_access_name = (f"{self.description.institution}-{self.description.lab_name}-student_access")
        teacher_access_name = (f"{self.description.institution}-{self.description.lab_name}-teacher_access")

        resource_to_recreate = []
        if student_access_name in machines_to_recreate:
            machines_to_recreate.remove(student_access_name)
            resource_to_recreate.append("aws_instance.student_access")
        if teacher_access_name in machines_to_recreate:
            machines_to_recreate.remove(teacher_access_name)
            resource_to_recreate.append("aws_instance.teacher_access_host[0]")
        for machine in machines_to_recreate:
            resource_to_recreate.append('aws_instance.machines["' f"{machine}" '"]')
        return resource_to_recreate

    def can_delete_image(self, image_name):
        """
        Return true if the image is not being used by any machine.

        Parameters:
          image_name (str): name of the image

        Returns:
          bool: true if the image is not being used by any machine or false otherwise
        """
        image = self.client.get_image(image_name)
        if image:
            image_id = image[0]
            instances_images_ids = self.client.get_machines_imageid()
            for instance_image_id in instances_images_ids:
                if image_id == instance_image_id:
                    return False
        return True

    def list_instances(self, instances, guests, copies):
        machines_to_list = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        headers = ["Name", "Status"]
        rows = []
        for machine in machines_to_list:
            machine_status = self.get_instance_status(machine)
            rows.append([machine,machine_status])
        return create_table(headers,rows)
    
    def shutdown(self, instances, guests, copies, stop_services):
        if stop_services:
            click.echo(f"Shutting down services...")
            for service in self.description.get_services_to_deploy():
                self.stop_instance(self.description.get_service_name(service))
        machines_to_shutdown = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy()) 
        for machine in machines_to_shutdown:
            click.echo(f"Shutting down instance {machine}...")
            self.stop_instance(machine)
            
    def start(self, instances, guests, copies, start_services):
        if start_services:
            click.echo(f"Booting up services...")
            for service in self.description.get_services_to_deploy():
                self.start_instance(self.description.get_service_name(service))
        machines_to_start = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())  
        for machine in machines_to_start:
            click.echo(f"Booting up instance {machine}...")
            self.start_instance(machine)

    def reboot(self, instances, guests, copies, reboot_services):
        if reboot_services:
            click.echo(f"Booting up services...")
            for service in self.description.get_services_to_deploy():
                self.reboot_instance(self.description.get_service_name(service))
        machines_to_reboot = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        for machine in machines_to_reboot:
            click.echo(f"Rebooting instance {machine}...")
            self.reboot_instance(machine)

    def recreate(self, instances, guests, copies, recreate_services=False):
        machines = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        resources_to_recreate = self.get_resources_to_recreate(instances, guests, copies)
        click.echo("Recreating machines...")
        self.terraform_recreate(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws', resources_to_recreate)

        click.echo("Waiting for machines to boot up...")
        ansible = Ansible(self)
        ansible.wait_for_connections(instances, guests, copies, False, self.description.get_services_to_deploy())

        click.echo("Configuring student access...")
        entry_points = []
        for m in machines:
            base_name = self.description.get_base_name(m)
            if (base_name not in entry_points and
                (self.description.get_guest_attr(base_name, "entry_point", False) or
                base_name == "student_access")):
                entry_points.append(base_name)
        self._student_access(instances, entry_points)

        click.echo("Running after-clone configuration...")
        ansible.run(instances, guests, copies, quiet=True, only_instances=False)

        if self.description.deploy_elastic and self.description.monitor_type == "endpoint":
            click.echo("Configuring elastic agents...")
            self._elastic_install_endpoint(instances)

        if self.description.deploy_caldera:
            click.echo("Configuring caldera agents...")
            self._caldera_install_agent(instances)

    def student_access(self, instances):
        """Creates users for the students in the student access host
        and in all entry points of INSTANCES.

        Generates pseudo-random passwords and/or sets public SSH keys for the users.
        Returns a dictionary of created users.

        """
        entry_points = [ base_name for base_name, guest in self.description.guest_settings.items() if guest.get("entry_point") ]
        entry_points.append("student_access")
        self._student_access(instances, entry_points)

    def deploy_infraestructure(self, instances):
        """
        Deploy cyber range infrastructure
        """

        ansible = Ansible(self)
        click.echo("Deploying Cyber Range instances...")
        self._deploy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
                        self.get_deploy_cr_vars(),
                        instances)

        if len(self.description.get_services_to_deploy()) > 0: #Deploy services
            click.echo("Deploying Cyber Range services...")
            self._deploy_services(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-aws',
                                  self.get_deploy_services_vars(),
                                  instances)

            click.echo("Waiting for services to boot up...")
            services_to_deploy = []
            for service in self.description.get_services_to_deploy():
                services_to_deploy.append(self.description.get_service_name(service))
            extra_vars = {
                "elastic" : {
                    "monitor_type": self.description.monitor_type,
                    "deploy_policy": self.description.elastic_deploy_default_policy,
                    "policy_name": self.description.packetbeat_policy_name if self.description.monitor_type == "traffic" else self.description.endpoint_policy_name,
                    "http_proxy" : self.description.proxy,
                    "description_path": self.description.description_dir,
                    "ip": self.client.get_machine_private_ip(self.description.get_service_name("elastic")),
                    "elasticsearch_memory": math.floor(self.description.services["elastic"]["memory"] / 1000 / 2)  if self.description.deploy_elastic else None,
                },
                "caldera":{
                    "ip": self.client.get_machine_private_ip(self.description.get_service_name("caldera")),
                    "description_path": self.description.description_dir,
                },
            }
            inventory = ansible.build_inventory(machine_list=services_to_deploy, extra_vars=extra_vars)
            ansible.wait_for_connections(inventory=inventory)

            click.echo("Configuring services...")
            ansible.run(inventory=inventory, playbook=self.ansible_services_path,quiet=True) 
            if self.description.deploy_elastic and self.description.monitor_type == "traffic":
                self._deploy_packetbeat()

        click.echo("Waiting for machines to boot up...")
        ansible.wait_for_connections(instances=instances)

        click.echo("Configuring student access...")
        self.student_access(instances)

        click.echo("Running after-clone configuration...")
        ansible.run(instances, quiet=True)

        if self.description.deploy_elastic and self.description.monitor_type == "endpoint":
            click.echo("Configuring elastic agents...")
            self._elastic_install_endpoint(instances)
        
        if self.description.deploy_caldera:
            click.echo("Configuring caldera agents...")
            self._caldera_install_agent(instances)

    def destroy_infraestructure(self, instances):
        """
        Destroy cyber range infrastructure
        """
        if len(self.description.get_services_to_deploy()) > 0: #Destroy services
            click.echo("Destroying Cyber Range services...")
            self._destroy_services(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-aws',
                                  self.get_deploy_services_vars(),
                                  instances)

        click.echo("Destroying Cyber Range instances...")
        self._destroy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-aws',
                         self.get_deploy_cr_vars(),
                         instances)

    def create_services_images(self, services):
        self.delete_services_images(services)
        super().create_services_images(services)
        # Delete temporary security groups created by Packer:
        self.client.delete_security_groups("Temporary group for Packer") 

    def delete_services_images(self, services):
        """
        Delete services base image.
        """
        for service in services:
            if services[service]:
                # Libvirt packer plugin fails if images exist.
                if not self.can_delete_image(service):
                    raise DeploymentAWSException(
                        f"Unable to delete image {service} because it is being used."
                    )
                self.client.delete_image(service)

    def create_cr_images(self, guests=None):
        self.delete_cr_images(guests)
        super().create_cr_images(guests)
        self.client.delete_security_groups("Temporary group for Packer")

    def get_deploy_services_vars(self):
        """Build the terraform variable dictionary for deployment of the CyberRange services."""
        return {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "aws_region": self.description.aws_region,
            "network_cidr_block": self.description.network_cidr_block,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps(self._get_services_network_data()),
            "guest_data_json": json.dumps(self._get_services_guest_data()),
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.description.configure_dns,
            "monitor_type": self.description.monitor_type,
            "packetbeat_vlan_id": self.description.packetbeat_vlan_id,
            "machines_to_monitor": self.description.get_machines_to_monitor(),
            "monitor": self.description.deploy_elastic,
        }
    
    def get_services_status(self):
        if len(self.description.get_services_to_deploy()) > 0:
            headers = ["Name", "Status"]
            rows = []
            if self.description.deploy_elastic:
                elastic_name = self.description.get_service_name("elastic")
                rows = [[elastic_name, self.get_instance_status(elastic_name)]]
                if self.description.monitor_type == "traffic":
                    packetbeat_name = self.description.get_service_name("packetbeat")
                    rows.append([packetbeat_name, self.get_instance_status(packetbeat_name)])
                else:
                    try:
                        if self.get_instance_status(elastic_name) == "RUNNING":
                            playbook = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'get_info.yml'
                            result = self._get_service_info("elastic",playbook,{"action":"agents_status"})
                            agents_status = result[0]['agents_status']
                            for key in agents_status:
                                rows.append([f"elastic-agents-{key}", agents_status[key]])
                        else:
                            click.echo(f"Unable to connect to Elastic. Check if machine is running.")
                    except Exception as e:
                        raise DeploymentAWSException(e)
                if self.description.deploy_caldera:
                    rows.append(["",""])
            if self.description.deploy_caldera:
                caldera_name = self.description.get_service_name("caldera")
                rows.append([caldera_name, self.get_instance_status(caldera_name)])
                try:
                    if self.get_instance_status(caldera_name) == "RUNNING":
                        playbook = tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'get_info.yml'
                        result = self._get_service_info("caldera",playbook,{"action":"agents_status"})
                        response = result[0]['agents_status']
                        agents_status = {"alive": 0, "dead": 0, "pending_kill":0}
                        if len(response) > 0:
                            for agent in response: #TODO: see what the response is like when there are a large number of agents. pagination?
                                #Caldera uses this logic to define the state of the agent
                                now = int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000) #Milliseconds since epoch
                                agent_last_seen = int((datetime.datetime.strptime(agent["last_seen"],"%Y-%m-%dT%H:%M:%SZ") - datetime.datetime(1970, 1, 1)).total_seconds() * 1000) #Milliseconds since epoch
                                difference = now - agent_last_seen
                                if (difference <= 60000 and agent["sleep_min"] == 3 and agent["sleep_max"] == 3 and agent["watchdog"] == 1):
                                    agents_status["pending_kill"] = agents_status["pending_kill"] + 1
                                elif (difference <= 60000 or difference <= (agent["sleep_max"] * 1000)):
                                    agents_status["alive"] = agents_status["alive"] + 1
                                else:
                                    agents_status["dead"] = agents_status["dead"] + 1
                        for key in agents_status:
                            rows.append([f"caldera-agents-{key}", agents_status[key]])
                    else:
                        click.echo(f"Unable to connect to Caldera. Check if machine is running.")
                except Exception as e:
                    raise DeploymentAWSException(e)
            return create_table(headers,rows)
        else:
            return "No services were deployed."
        
    def _get_services_network_data(self):
        """Compute the complete list of services subnetworks."""
        networks = {
            f"{self.description.institution}-{self.description.lab_name}-services" : {
                "cidr" : self.description.services_network,
                "mode": "none"
            },
        }
        return networks
    
    def _get_services_guest_data(self):
        """Compute the services guest data as expected by the deployment terraform module."""
        guest_data = {}
        if self.description.deploy_elastic:
            guest_data[self.description.get_service_name("elastic")] = {
                    "guest_name": self.description.get_service_name("elastic"),
                    "base_name": "elastic",
                    "hostname": "elastic",
                    "base_os": self.description.get_service_base_os("elastic"),
                    "internet_access": True,
                    "interfaces": {
                        f'{self.description.get_service_name("elastic")}-1' : {
                            "name": f'{self.description.get_service_name("elastic")}-1',
                            "index": 0,
                            "guest_name": self.description.get_service_name("elastic"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[4]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        }
                    },
                    "disk": self.description.services["elastic"]["disk"],
                    "instance_type": self.description.instance_type.get_guest_instance_type(self.description.services["elastic"]["memory"],self.description.services["elastic"]["vcpu"],False,self.description.monitor_type),
                }
            if self.description.monitor_type == "traffic":
                guest_data[self.description.get_service_name("packetbeat")] = {
                    "guest_name": self.description.get_service_name("packetbeat"),
                    "base_name": "packetbeat",
                    "hostname": "packetbeat",
                    "base_os": self.description.get_service_base_os("packetbeat"),
                    "internet_access": False,
                    "interfaces": {
                        f'{self.description.get_service_name("packetbeat")}-1' : {
                            "name": f'{self.description.get_service_name("packetbeat")}-1',
                            "index": 0,
                            "guest_name": self.description.get_service_name("packetbeat"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[5]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        },
                    },
                    "disk": self.description.services["packetbeat"]["disk"],
                    "instance_type": "t2.micro",
                }
        if self.description.deploy_caldera:
            guest_data[self.description.get_service_name("caldera")] = {
                    "guest_name": self.description.get_service_name("caldera"),
                    "base_name": "caldera", 
                    "hostname": "caldera",
                    "base_os": self.description.get_service_base_os("caldera"),
                    "internet_access": False,
                    "interfaces": {
                        f'{self.description.get_service_name("caldera")}-1' : {
                            "name": f'{self.description.get_service_name("caldera")}-1',
                            "index": 0,
                            "guest_name": self.description.get_service_name("caldera"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[6]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        }
                    },
                    "disk": self.description.services["caldera"]["disk"],
                    "instance_type": self.description.instance_type.get_guest_instance_type(self.description.services["caldera"]["memory"],self.description.services["caldera"]["vcpu"],False,self.description.monitor_type),
                }
        return guest_data
        
    def _deploy_packetbeat(self):
        try:
            elastic_name = self.description.get_service_name("elastic")
            if self.get_instance_status(elastic_name) == "RUNNING":
                elastic_ip = self.get_ssh_hostname(elastic_name)
                playbook = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'get_info.yml'
                result = self._get_service_info("elastic",playbook,{"action":"get_token_by_policy_name","policy_name":self.description.packetbeat_policy_name})
                agent_token = result[0]["token"]
                ansible = Ansible(deployment=self)
                inventory = ansible.build_inventory(
                    machine_list=[self.description.get_service_name("packetbeat")],
                    username=OS_DATA[self.description.get_service_base_os("packetbeat")]["username"],
                    extra_vars = {
                        "action": "install",
                        "elastic_url": f"https://{elastic_ip}:8220",
                        "token": agent_token,
                        "elastic_agent_version": self.description.elastic_stack_version,
                        "institution": self.description.institution,
                        "lab_name": self.description.lab_name,
                    },
                )
                ansible.wait_for_connections(inventory=inventory)
                ansible.run(inventory = inventory,
                            playbook = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml',
                            quiet = True)
            else:
                click.echo(f"Unable to connect to Elastic. Check if machine is running.")
        except Exception as e:
            raise DeploymentAWSException(e)
    
    def get_services_resources_to_target_destroy(self, instances):
        resources = []
        if self.description.deploy_elastic and self.description.monitor_type == "traffic":
            resources = resources + self._get_sessions_resources_name(instances)
        return resources
        
    def get_services_resources_to_target_apply(self, instances):
        """
        Returns the name of the aws resource of the services-aws module to target apply base on the instances number

        Parameters:
          instances (list(int)): instances to use

        Returns:
          list(str): resources name to target apply
        """
        resources = [
            "aws_security_group.services_internet_access_sg[0]",
            "aws_security_group.caldera_scenario_sg",
            "aws_security_group.elastic_endpoint_scenario_sg",
            "aws_security_group.elastic_traffic_scenario_sg",
        ]
        resources = resources + self._get_services_instances_name()
        resources = resources + self._get_services_security_group_resources_name()
        resources = resources + self._get_services_interface_resources_name()
        if self.description.configure_dns:
            resources = resources + self._get_services_dns_resources_name()
        if self.description.deploy_elastic and self.description.monitor_type == "traffic":
            resources = resources + [
                "aws_ec2_traffic_mirror_target.packetbeat[0]",
                "aws_ec2_traffic_mirror_filter.filter[0]",
                "aws_ec2_traffic_mirror_filter_rule.filter_all_inbound[0]",
                "aws_ec2_traffic_mirror_filter_rule.filter_all_outbound[0]",
            ]
            resources = resources + self._get_sessions_resources_name(instances)
        return resources
