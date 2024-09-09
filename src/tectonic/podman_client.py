
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

import podman


class PodmanClientException(Exception):
    pass

class Client:
    
    def __init__(self, description):
        self.description = description
        self.connection = podman.PodmanClient(base_url=self.description.podman_uri)

    def get_instance_status(self, instance_name):
        try:
            container_info = self.connection.containers.get(instance_name)
            return container_info.status
        except Exception as exception:
            raise PodmanClientException(f"{exception}")

    
