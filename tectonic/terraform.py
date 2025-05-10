
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
from tectonic.constants import OS_DATA

import python_terraform
import os
import json
from abc import ABC, abstractmethod

class TerraformException(Exception):
    pass

class Terraform(ABC):
    """
    Terraform class.

    Description: manages interaction with Terraform to deploy/destroy scenarios.
    """

    BACKEND_TYPE = "FILE" # Possible values: FILE (for local files as backend), GITLAB (use gitlab as backend. You must change backend.tf of each terraform module).

    def __init__(self, config, description):
        """
        Initialize the Terraform object.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
        """
        self.config = config
        self.description = description
        self.terraform_instances_module = tectonic_resources.files('tectonic') / 'terraform' / 'modules' / f"gsi-lab-{self.config.platform}"

    def _run_terraform_cmd(self, t, cmd, variables, **args):
        """
        Run terraform command.

        Parameters:
            t (terraform): terraform object.
            cmd (str): terraform command to apply.
            variables (dict): variabls to use terraform invocation.
            **args (args): other arguments to use in terraform invocation.
        
        Return:
            str: output of the action (stdout)
        """
        return_code, stdout, stderr = t.cmd(cmd, no_color=python_terraform.IsFlagged, var=variables, **args)
        if return_code != 0:
            raise TerraformException(f"ERROR: terraform {cmd} returned an error: {stderr}")
        return stdout
    
    def _generate_backend_config(self, terraform_dir):
        """
        Generate Terraform backend configuration.

        Parameters:
            terraform_dir (str): path to the terraform module.
        """
        terraform_module_name = os.path.basename(os.path.normpath(terraform_dir))
        if self.BACKEND_TYPE == "FILE":
            return [
                f"path=terraform-states/{self.description.institution}-{self.description.lab_name}-{terraform_module_name}"
            ]
        elif self.BACKEND_TYPE == "GITLAB":
            address = f"{self.config.gitlab_url}/{self.description.institution}-{self.description.lab_name}-{terraform_module_name}"
            return [
                f"address={address}",
                f"lock_address={address}/lock",
                f"unlock_address={address}/lock",
                f"username={self.config.gitlab_username}",
                f"password={self.config.gitlab_access_token}",
                "lock_method=POST",
                "unlock_method=DELETE",
                "retry_wait_min=5",
            ]
        
    def _apply(self, terraform_dir, variables, resources=None, recreate=False):
        """
        Execute terraform apply command.

        Parameters:
            terraform_dir (str): path to the terraform module.
            variables (dict): variables of the terraform module.
            resources (list(str)): name of terraform resources for target apply. Default: None.
        """
        t = python_terraform.Terraform(working_dir=terraform_dir)
        self._run_terraform_cmd(t, "init", [], reconfigure=python_terraform.IsFlagged, backend_config=self._generate_backend_config(terraform_dir))
        if recreate:
            self._run_terraform_cmd(t, "plan", variables, input=False, replace=resources)
            self._run_terraform_cmd(t, "apply", variables, auto_approve=True, input=False, replace=resources)
        else:
            self._run_terraform_cmd(t, "plan", variables, input=False, target=resources)
            self._run_terraform_cmd(t, "apply", variables, auto_approve=True, input=False, target=resources)

    def _destroy(self, terraform_dir, variables, resources=None):
        """
        Execute terraform destroy command.

        Parameters:
            terraform_dir (str): path to the terraform module.
            variables (dict): variables of the terraform module.
            resources (list(str)): name of terraform resources for target destroy. Default: None.
        """
        t = python_terraform.Terraform(working_dir=terraform_dir)
        self._run_terraform_cmd(t, "init", [], reconfigure=python_terraform.IsFlagged, backend_config=self._generate_backend_config(terraform_dir))
        self._run_terraform_cmd(t, "destroy", variables, auto_approve=True, input=False, target=resources)

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
    def _get_resources_to_target_apply(self, instances):
        """
        Get resources name for target apply.

        Parameters:
            instances (list(int)): number of the instances to target apply.
        
        Return:
            list(str): names of resources.
        """
        pass

    @abstractmethod
    def _get_resources_to_target_destroy(self, instances):
        """
        Get resources name for target destroy.

        Parameters:
            instances (list(int)): number of the instances to target destroy.
        
        Return:
            list(str): names of resources.
        """
        pass

    def _get_resources_to_recreate(self, instances, guests, copies):
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
    def _get_terraform_variables(self):
        """
        Get variables to use in Terraform.

        Return:
            dict: variables.
        """
        pass

    def deploy(self, instances):
        """
        Deploy scenario instances.

        Parameters:
            instances (list(int)): number of the instances to recreate.
        """
        resources_to_create = None
        if instances is not None:
            resources_to_create = self._get_resources_to_target_apply(instances)
        self._apply(self.terraform_instances_module, self._get_terraform_variables(), resources_to_create)

    def destroy(self, instances):
        """
        Destroy scenario instances.

        Parameters:
            instances (list(int)): number of the instances to recreate.
        """
        resources_to_destroy = None
        if instances is not None:
            resources_to_destroy = self._get_resources_to_target_destroy(instances)
        self._destroy(self.terraform_instances_module, self._get_terraform_variables(), resources_to_destroy)

    def recreate(self, instances, guests, copies): 
        """
        Recreate scenario instances.

        Parameters:
            instances (list(int)): number of the instances to recreate.
            guests (list(str)): name of the guests to recreate.
            copies (list(int)): number of the copies to recreate.
        """
        resources_to_recreate = self._get_resources_to_recreate(instances, guests, copies)
        self._apply(self.terraform_instances_module, self._get_terraform_variables(), resources_to_recreate, True)

    def _get_guest_variables(self, guest):
        """
        Return guest variables for terraform.

        Parameters:
          guest (GuestDescription): guest to get variables.

        Returns:
          dict: variables.
        """
        return {
            "base_name": guest.base_name,
            "name": guest.name,
            "vcpu": guest.vcpu,
            "memory": guest.memory,
            "disk": guest.disk,
            "hostname": guest.hostname,
            "base_os": guest.os,
            "interfaces": {name: self._get_network_interface_variables(interface) for name, interface in guest.interfaces.items()},
            "is_in_services_network": guest.is_in_services_network,
        }

    def _get_network_interface_variables(self, interface):
        """
        Return netowkr interface variables for terraform.

        Parameters:
          interface (NetworkInterface): interface to get variables.

        Returns:
          dict: variables.
        """
        return {
            "name": interface.name,
            "subnetwork_name": interface.network.name,
            "private_ip": interface.private_ip
        }

    def _get_terraform_variables(self):
        """
        Get variables to use in Terraform.

        Return:
            dict: variables.
        """
        return {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "instance_number": self.description.instance_number,
            "ssh_public_key_file": self.config.ssh_public_key_file,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps({name: network.to_dict() for name, network in self.description.scenario_networks.items()}),
            "guest_data_json": json.dumps({name: self._get_guest_variables(guest) for name, guest in self.description.scenario_guests.items()}),
            "default_os": self.description.default_os,
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.config.configure_dns,
        }