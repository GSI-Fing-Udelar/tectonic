
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

class InstanceManagerException(Exception):
    pass

class InstanceManager(ABC):
    """
    InstanceManager class.

    Description: manages scenario instances.
    You must implement this class if you add a new platform.
    """
    def __init__(self, config, description, client):
        """
        Init method.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
            client (Client): Tectonic client object.
        """
        self.config = config
        self.description = description
        self.client = client

    def create_image(self, packer, packer_module, variables):
        """
        Create images using Packer.

        Parameters:
            packer (Packer): Tectonic packer object.
            packer_module (str): path to the Packer module.
            variables (dict): variables of the Packer module.
        """
        packer.create_image(packer_module, variables)

    @abstractmethod
    def _get_machine_resources_name(self, instances, guests, copies):
        """
        Returns the name of the aws_instance resource of the AWS Terraform module for the instances.

        Parameters:
          instances (list(int)): instances to use.
          guests (list(str)): guests names to use.
          copies (list(int)): copies numbers to use.

        Returns:
          list(str): resources name of the aws_instances for the instances.
        """
        pass

    @abstractmethod
    def _get_subnet_resources_name(self, instances):
        """
        Returns the name of the aws_subnet resource of the AWS Terraform module for the instances.

        Parameters:
          instances (list(str)): instances to use.

        Returns:
          list(str): resources name of the aws_subnet for the instances.
        """
        pass

    @abstractmethod
    def get_resources_to_target_apply(self, instances):
        """
        Get resources name for target apply.

        Parameters:
            instances (list(int)): number of the instances to target apply.
        
        Return:
            list(str): names of resources.
        """
        pass

    @abstractmethod
    def get_resources_to_target_destroy(self, instances):
        """
        Get resources name for target destroy.

        Parameters:
            instances (list(int)): number of the instances to target destroy.
        
        Return:
            list(str): names of resources.
        """
        pass

    @abstractmethod
    def get_resources_to_recreate(self, instances, guests, copies):
        """
        Get resources name to recreate.

        Parameters:
            instances (list(int)): number of the instances to recreate.
            guests (list(str)): guests names to use.
            copies (list(int)): copies numbers to use.
        
        Return:
            list(str): names of resources.
        """
        pass
    
    @abstractmethod
    def get_terraform_variables(self):
        """
        Get variables to use in Terraform.

        Return:
            dict: variables.
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
        return self.client.get_machine_private_ip(machine)
