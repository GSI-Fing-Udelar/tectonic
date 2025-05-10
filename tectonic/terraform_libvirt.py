
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

class TerraformLibvirtException(Exception):
    pass

class TerraformLibvirt(Terraform):
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
        for instance in filter(lambda i: i <= self.description.instance_number, instances or range(1, self.description.instance_number+1)):
            for network in self.description.topology.keys():
                resources.append(
                    'libvirt_network.subnets["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network}"
                    '"]'
                )
        return resources

    def _get_dns_resources_name(self, instances):
        # TODO
        return []

    def _get_resources_to_target_apply(self, instances):
        """
        Returns the name of the docker resource of the Docker Terraform module to target apply base on the instances number.

        Parameters:
            instances (list(int)): instances to use.
        
        Return:
            list(str): names of resources.
        """
        resources = self._get_machine_resources_name(instances, None, None)
        resources = resources + self._get_subnet_resources_name(instances)
        if self.config.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources

    def _get_resources_to_target_destroy(self, instances):
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
        if self.description.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources

    def _get_resources_to_recreate(self, instances, guests, copies):
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

    def _get_terraform_variables(self):
        """
        Get variables to use in Terraform.

        Return:
            dict: variables.
        """
        result = super()._get_terraform_variables()
        result["libvirt_uri"] = self.config.libvirt.uri
        result["libvirt_storage_pool"] = self.config.libvirt.storage_pool
        result["libvirt_student_access"] = self.config.libvirt.student_access
        result["libvirt_bridge"] = self.config.libvirt.bridge
        result["libvirt_external_network"] = self.config.libvirt.external_network
        result["libvirt_bridge_base_ip"] = self.config.libvirt.bridge_base_ip
        result["services_network"] = self.config.services_network_cidr_block
        result["services_network_base_ip"] = len(self.description.services_guests.keys())+1
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
        result["entry_point_index"] = guest.entry_point_index
        result["internet_access"] = guest.internet_access
        result["services_network_index"] = guest.services_network_index
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
        result["index"] = interface.index
        return result