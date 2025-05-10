
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

import importlib.resources as tectonic_resources

from tectonic.packer import Packer

class PackerLibvirtException(Exception):
    pass

class PackerLibvirt(Packer):
    """
    Packer class.

    Description: manages interaction with Packer to build images.
    """

    def __init__(self, config, description, client):
        """
        Initialize the packer object.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
            client (Client): Tectonic client object
        """
        super().__init__(config, description, client)
    
    def _get_service_machine_variables(self, service):
        """
        Return machines for creating services images.

        Parameters:
            service (ServiceDescription): services for which to create images.

        Returns:
            dict: machines variables.
        """
        result = super()._get_service_machine_variables(service)
        result["vcpu"] = service.vcpu
        result["memory"] = service.memory
        result["disk"] = service.disk
        return result