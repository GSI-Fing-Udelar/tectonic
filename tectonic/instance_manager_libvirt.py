
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
from tectonic.constants import OS_DATA

from tectonic.instance_manager import InstanceManager
from tectonic.ssh import interactive_shell

class InstanceManagerLibvirtException(Exception):
    pass

class InstanceManagerLibvirt(InstanceManager):
    """
    InstanceManagerLibvirt class.

    Description: manages scenario instances for Libvirt.
    """

    def __init__(self, config, description, client):
        super().__init__(config, description, client)

    def _get_machine_resources_name(self, instances, guests, copies):
        """
        Returns the name of the docker_container resource of the Docker Terraform module for the instances.

        Parameters:
          instances (list(int)): instances number to use.
          guests (list(str)): guests names to use.
          copies (list(int)): copies numbers to use.

        Returns:
          list(str): resources name of the aws_instances for the instances.
        """
        machines = self.description.parse_machines(instances, guests, copies, True)
        resources = []
        for machine in machines:
            resources.append('libvirt_domain.machines["' f"{machine}" '"]')
            resources.append('libvirt_volume.cloned_image["' f"{machine}" '"]')
            resources.append('libvirt_cloudinit_disk.commoninit["' f"{machine}" '"]')
        return resources

    def _get_subnet_resources_name(self, instances):
        """
        Returns the name of the docker_network resource of the Docker Terraform module for the instances.

        Parameters:
          instances (list(str)): instances to use.

        Returns:
          list(str): resources name of the aws_subnet for the instances.
        """
        resources = []
        for instance in filter(
            lambda i: i <= self.description.instance_number, instances or range(1, self.description.instance_number+1)
        ):
            for network in self.description.topology.keys:
                resources.append(
                    'libvirt_network.subnets["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network}"
                    '"]'
                )
        return resources

    def _get_dns_resources_name(self, instances):
        # TODO
        return []

    def get_resources_to_target_apply(self, instances):
        """
        Returns the name of the docker resource of the Docker Terraform module to target apply base on the instances number.

        Parameters:
            instances (list(int)): instances to use.
        
        Return:
            list(str): names of resources.
        """
        resources = self._get_machine_resources_name(instances, None, None)
        resources = resources + self._get_subnet_resources_name(instances)
        return resources

    def get_resources_to_target_destroy(self, instances):
        """
        Returns the name of the docker resource of the Docker Terraform module to target destroy base on the instances number.

        Parameters:
            instances (list(int)): instances to use.
        
        Return:
            list(str): names of resources.
        """
        machines = self.description.parse_machines(instances, None, None, True)
        resources = []
        for machine in machines:
            resources.append('libvirt_domain.machines["' f"{machine}" '"]')
        if self.config.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources

    def get_resources_to_recreate(self, instances, guests, copies):
        """
        Returns the name of the docker resource of the Docker Terraform module to recreate base on the machines names.

        Parameters:
          instances (list(int)): instances number to use.
          guests (list(str)): guests names to use.
          copies (list(int)): copies numbers to use.

        Returns:
          list(str): resources name to recreate.
        """
        machines = self.description.parse_machines(instances, guests, copies, True)
        resources = []
        for machine in machines:
            resources.append('libvirt_domain.machines["' f"{machine}" '"]')
            resources.append('libvirt_volume.cloned_image["' f"{machine}" '"]')
        return resources

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
            "ssh_public_key_file": self.config.ssh_public_key_file,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps(self.description.scenario_networks), # TODO: Fix json
            "guest_data_json": json.dumps(self.description.scenario_guests), # TODO: Fix json
            "default_os": self.description.default_os,
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.config.configure_dns,
            "libvirt_uri": self.config.libvirt.uri,
            "libvirt_storage_pool": self.config.storage_pool,
            "libvirt_student_access": self.config.libvirt.student_access,
            "libvirt_bridge": self.config.libvirt.bridge,
            "libvirt_external_network": self.config.external_network,
            "libvirt_bridge_base_ip": self.config.libvirt.bridge_base_ip,
            "services_network": self.config.services_network_cidr_block,
            "services_network_base_ip": 9,
            }

    
    def console(self, machine_name, username):
        """
        Connect to a specific scenario machine.

        Parameters:
            machine_name (str): name of the machine.
            username (str): username to use. Default: None
        """
        hostname = self.client.get_machine_private_ip(machine_name)
        if not hostname:
            raise InstanceManagerLibvirtException(f"Instance {machine_name} not found.")
        interactive_shell(hostname, username)
