
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

from tectonic.constants import OS_DATA
from tectonic.terraform_service import TerraformService

class TerraformServiceLibvirtException(Exception):
    pass

class TerraformServiceLibvirt(TerraformService):
    """
    TerraformServiceLibvirt class.

    Description: manages services instances for Libvirt.
    """

    def __init__(self, config, description, client):
        super().__init__(config, description, client)

    def _get_resources_to_target_apply(self, instances):
        """
        Get resources name for target apply.

        Parameters:
            instances (list(int)): number of the instances to target apply.
        
        Return:
            list(str): names of resources.
        """
        resources = []
        machines = [service for _, service in self.description.services_guests.items() if service.enable]
        for service in machines:
            resources.append('libvirt_volume.cloned_image["'f"{service.name}"'"]')
            resources.append('libvirt_cloudinit_disk.commoninit["'f"{service.name}"'"]')
            resources.append('libvirt_domain.machines["'f"{service.name}"'"]')
        for network in self.description.auxiliary_networks:
            resources.append('libvirt_network.subnets["'f"{network}"'"]')
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
        return []

    def _get_terraform_variables(self):
        """
        Get variables to use in Terraform.
        
        Return:
            dict: variables.
        """
        result = super()._get_terraform_variables()
        result["libvirt_uri"] = self.config.libvirt.uri
        result["libvirt_storage_pool"] = self.config.libvirt.storage_pool
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
        result["subnetwork_name"] = interface.network.name
        result["index"] = interface.index
        return result