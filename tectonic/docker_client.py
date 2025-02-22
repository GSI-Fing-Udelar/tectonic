
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
import subprocess
from ipaddress import ip_network, ip_address


class DockerClientException(Exception):
    pass

class Client:
    
    def __init__(self, description):
        self.description = description
        try:
            self.connection = docker.DockerClient(base_url=self.description.docker_uri)
        except:
            self.connection = None
            raise DockerClientException(f"Cannot connect to docker server at {self.description.docker_uri}")

    def __del__(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except:
                pass

    def get_instance_status(self, instance_name):
        try:
            container = self.connection.containers.get(instance_name)
            return container.status.upper()
        except docker.errors.NotFound:
            return "UNKNOWN"
        except Exception as exception:
            raise DockerClientException(f"{exception}")
        
    def get_machine_private_ip(self, name):
        """
        Returns the private IP address of a domain.

        If the domain has more than one IP address, the first
        address inside network_cidr_block is returned.

        """
        try:
            lab_network = ip_network(self.description.network_cidr_block)
            services_network = ip_network(self.description.services_network)
            services_list = []
            for service in self.description.get_services_to_deploy():
                services_list.append(self.description.get_service_name(service))

            container = self.connection.containers.get(name)
            for network in container.attrs["NetworkSettings"]["Networks"]:
                ip_addr = container.attrs["NetworkSettings"]["Networks"][network]["IPAddress"]
                if name in services_list:
                    if ip_address(ip_addr) in services_network:
                        return ip_addr
                else:
                    if ip_address(ip_addr) in lab_network:
                        return ip_addr
            return None #Raise exception?
        except Exception as exception:
            raise DockerClientException(f"{exception}")
        
    def delete_image(self, image_name):
        """
        Delete base image
        """
        try:
            self.connection.images.remove(image_name)
        except Exception as exception:
            raise DockerClientException(f"{exception}")
        
    def start_instance(self, instance_name):
        """
        Starts a stopped instance.
        """
        try:
            container = self.connection.containers.get(instance_name)
            container.start()
        except Exception as exception:
            raise DockerClientException(f"{exception}")

    def stop_instance(self, instance_name):
        """
        Stops a running instance.
        """
        try:
            container = self.connection.containers.get(instance_name)
            container.stop()
        except Exception as exception:
            raise DockerClientException(f"{exception}")
        
    def reboot_instance(self, instance_name):
        """
        Reboots a running instance.
        """
        try:
            container = self.connection.containers.get(instance_name)
            container.restart()
        except Exception as exception:
            raise DockerClientException(f"{exception}")   

    def connect(self, instance_name, username):
        """
        Connect to contaienr
        """
        try:
            container = self.connection.containers.get(instance_name)
            subprocess.run([f"docker exec -u {username} -it {container.id} /bin/bash"], shell=True)
            # TODO: Fix terminal using sockets
            # container = self.connection.containers.get(instance_name)
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
            raise DockerClientException(f"{exception}")  
        
    def is_image_in_use(self, image_name):
        """
        Returns true if the image is in use for some container.

        Parameters:
            image_name(str): the image name to check
        """
        try:
            for container in self.connection.containers.list():
                if f"{image_name}:latest" in container.image.tags:
                    return True
            return False
        except Exception as exception:
            raise DockerClientException(f"{exception}")
        
    
    def get_image(self, image_name):
        """
        Get the image given its name.

        Parameters:
            image_name (str): name of the image (<institution>-<lab_name>-<image_name>).

        Returns:
            str: the identifier of the image if it was found or None otherwise.
        """
        try:
            return self.connection.images.get(image_name)
        except docker.errors.ImageNotFound as exception:
            return None
        except Exception as exception:
            raise DockerClientException(f"{exception}")

    
