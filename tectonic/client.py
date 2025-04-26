
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

from abc import ABC, abstractmethod

class Client(ABC):
    """
    Client class.

    Description: Implement API calls for each deployment technology.
    You must implement this class if you add a new platform.
    """

    def __init__(self, config, description):
        """
        Init method.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
        """
        self.config = config
        self.description = description

    def __del__(self):
        try:
            self.connection.close()
        except:
            pass

    @abstractmethod
    def get_machine_status(self, machine_name):
        """
        Return the status of an machine. 

        Parameters:
            machine_name (str): name of the machine.

        Return:
            str: status of the machine. At least it should consider the following values: 
                - RUNNING: created and running.
                - STOPPED: created but not running.
                - NOT FOUND: not found (or not created).
        """
        pass
        
    @abstractmethod
    def get_machine_private_ip(self, machine_name):
        """
        Return the private IP address of an machine.
        If the machine has more than one IP address, the first address inside network_cidr_block is returned.
        If the machine does not have a private IP None is returned.

        Parameters:
            machine_name (str): name of the machine.

        Return:
            str: IP address or None
        """
        pass

    def get_machine_public_ip(self, machine_name):
        """
        Return the public IP address of an machine.
        If the machine does not have a public IP None is returned

        Parameters:
            machine_name (str): name of the machine.

        Return:
            str: IP address or None.
        """
        return None

    @abstractmethod
    def get_image_id(self, image_name):
        """
        Return internal image identifier.

        Parameters:
            image_name (str): name of the image.

        Returns:
            str: the identifier of the image if it was found or None otherwise.
        """
        pass
    
    @abstractmethod
    def is_image_in_use(self, image_name):
        """
        Return if the image is being used.

        Parameters:
            image_name (str): name of the image.

        Return:
            bool: True if the images is being use or False otherwise.
        """
        pass

    @abstractmethod
    def delete_image(self, image_name):
        """
        Delete an image.

        Parameters:
            image_name (str): name of the image.
        """
        pass
        
    @abstractmethod
    def start_machine(self, machine_name):
        """
        Starts a stopped machine.

        Parameters:
            machine_name (str): name of the machine.
        """
        pass

    @abstractmethod
    def stop_machine(self, machine_name):
        """
        Stops a running machine.

        Parameters:
            machine_name (str): name of the machine.
        """
        pass
        
    @abstractmethod
    def restart_machine(self, machine_name):
        """
        Reboots a running machine.

        Parameters:
            machine_name (str): name of the machine.
        """
        pass

    @abstractmethod
    def console(self, machine_name, username):
        """
        Connect to a specific scenario machine.

        Parameters:
            machine_name (str): name of the machine.
            username (str): username to use.
        """
        pass

    def get_ssh_proxy_command(self):
        """
        Returns the appropriate SSH proxy configuration to access guest machines.

        Return:
            str: ssh proxy command to use.
        """
        return None
    
    def get_ssh_hostname(self, machine):
        """
        Returns the hostname to use for ssh connection to the machine.

        Parameters:
            machine (str): machine name.

        Return:
            str: ssh hostname to use.
        """
        return self.get_machine_private_ip(machine)