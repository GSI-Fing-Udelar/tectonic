
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

from tectonic.client import Client

import docker
import subprocess
from ipaddress import ip_network, ip_address

class ClientDockerException(Exception):
    pass

class ClientDocker(Client):
    """
    ClientDocker class.

    Description: Implement Client for Docker.
    """

    STATE_MSG = {
        "created": "CREATED",
        "running": "RUNNING",
        "paused": "STOPPED",
        "restarting": "RESTARTING",
        "exited": "STOPPED",
        "removing": "REMOVING",
        "dead": "DEAD",
    }

    def __init__(self, config, description):
        """
        Init method.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
        """
        super().__init__(config, description)
        try:
            self.connection = docker.DockerClient(base_url=config.docker.uri)
        except:
            self.connection = None
            raise ClientDockerException(f"Cannot connect to docker server at {config.docker.uri}")
        
    def get_machine_status(self, machine_name):
        try:
            container = self.connection.containers.get(machine_name)
            return self.STATE_MSG.get(container.status, "NOT FOUND")
        except docker.errors.NotFound:
            return "NOT FOUND"
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
        
    def get_machine_private_ip(self, machine_name):
        try:
            if machine_name in self.description.services_guests.keys():
                return self.description.services_guests[machine_name].service_ip
            else:
                container = self.connection.containers.get(machine_name)
                for network in container.attrs["NetworkSettings"]["Networks"]:
                    ip_addr = container.attrs["NetworkSettings"]["Networks"][network]["IPAddress"]
                    if ip_address(ip_addr) in ip_network(self.config.network_cidr_block):
                        return ip_addr
                return None
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
        
    def get_image_id(self, image_name):
        try:
            return self.connection.images.get(image_name).id
        except docker.errors.ImageNotFound as exception:
            return None
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
                 
    def is_image_in_use(self, image_name):
        try:
            for container in self.connection.containers.list():
                if f"{image_name}:latest" in container.image.tags:
                    return True
            return False
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
        
    def delete_image(self, image_name):
        try:
            if self.get_image_id(image_name):
                self.connection.images.remove(image_name)
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
        
    def start_machine(self, machine_name):
        try:
            container = self.connection.containers.get(machine_name)
            container.start()
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
        
    def stop_machine(self, machine_name):
        try:
            container = self.connection.containers.get(machine_name)
            container.stop()
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
        
    def restart_machine(self, machine_name):
        try:
            container = self.connection.containers.get(machine_name)
            container.restart()
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
        
    def console(self, machine_name, username):
        try:
            container = self.connection.containers.get(machine_name)
            subprocess.run([f"docker exec -u {username} -it {container.id} /bin/bash"], shell=True)
            # TODO: Fix terminal using sockets
            # container = self.connection.containers.get(machine_name)
            # (_,s) = container.exec_run("/bin/bash", stdin=True, socket=True, user=username)
            # while True:
            #     original_text_to_send = input("$") + '\n'
            #     if(original_text_to_send == "exit\n"):
            #         s.close()
            #         break
            #     else:
            #         s._sock.send(original_text_to_send.encode('utf-8'))
            #         msg = s._sock.recv(1024)
            #         print(msg.decode()[8:])
        except Exception as exception:
            raise ClientDockerException(f"{exception}")
        
    