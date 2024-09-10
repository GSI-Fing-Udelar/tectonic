
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

import docker


class DockerClientException(Exception):
    pass

class Client:
    
    def __init__(self, description):
        self.description = description
        self.connection = docker.DockerClient(base_url=self.description.docker_uri)

    def get_instance_status(self, instance_name):
        try:
            container = self.connection.containers.get(instance_name)
            return container.status
        except docker.errors.NotFound:
            return "UNKNOWN"
        except Exception as exception:
            raise DockerClientException(f"{exception}")
        
    def get_machine_private_ip(self, name):
        """Returns the private IP address of a domain.

           If the domain has more than one IP address, the first
           address inside network_cidr_block is returned.

        """
        try:
            container = self.connection.containers.get(name)
            for network in container.attrs["NetworkSettings"]["Networks"]:
                return container.attrs["NetworkSettings"]["Networks"][network]["IPAddress"]
            return None #Raise exception?
        except Exception as exception:
            raise DockerClientException(f"{exception}")
        
        

    
