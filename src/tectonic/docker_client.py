
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


class DockerClientException(Exception):
    pass

class Client:
    
    def __init__(self, description):
        self.description = description
        self.connection = docker.DockerClient(base_url=self.description.docker_uri)

    def __del__(self):
        if self.connection is not None:
            try:
                self.connection.close()
            except:
                pass

    def get_instance_status(self, instance_name):
        try:
            container = self.connection.containers.get(instance_name)
            return container.status
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
            container = self.connection.containers.get(name)
            for network in container.attrs["NetworkSettings"]["Networks"]:
                return container.attrs["NetworkSettings"]["Networks"][network]["IPAddress"]
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
    

    
