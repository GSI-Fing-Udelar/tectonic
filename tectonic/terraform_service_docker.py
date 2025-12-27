
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

class TerraformServiceDockerException(Exception):
    pass

class TerraformServiceDocker(TerraformService):
    """
    TerraformServiceDocker class.

    Description: manages services instances for Docker.
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
            resources.append('docker_container.machines["'f"{service.name}"'"]')
            resources.append('docker_image.base_images["'f"{service.name}"'"]')
        for network in self.description.auxiliary_networks:
            resources.append('docker_network.subnets["'f"{network}"'"]')
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

    def _get_service_machine_variables(self, service):
        """
        Return machines variables deploy services.

        Parameters:
            service (ServiceDescription): services to deploy.

        Returns:
            dict: machines variables.
        """
        result = super()._get_service_machine_variables(service)
        result["ports"] =  service.ports if service.base_name == "bastion_host" else {}
        return result