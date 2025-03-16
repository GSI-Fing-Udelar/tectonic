
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

import python_terraform
import os

class TerraformException(Exception):
    pass

class Terraform:
    """
    Terraform class.

    Description: manages interaction with Terraform to deploy/destroy scenarios.
    """

    BACKEND_TYPE = "FILE" # Possible values: FILE (for local files as backend), GITLAB (use gitlab as backend. You must change backend.tf of each terraform module).

    def __init__(self, institution, lab_name, backend_info):
        self.institution = institution
        self.lab_name = lab_name
        self.backend_info = backend_info

    def _run_terraform_cmd(t, cmd, variables, **args):
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
                f"path=terraform-states/{self.institution}-{self.lab_name}-{terraform_module_name}"
            ]
        elif self.BACKEND_TYPE == "GITLAB":
            address = f"{self.backend_info.get("gitlab_url")}/{self.institution}-{self.lab_name}-{terraform_module_name}"
            return [
                f"address={address}",
                f"lock_address={address}/lock",
                f"unlock_address={address}/lock",
                f"username={self.backend_info.get("gitlab_username")}",
                f"password={self.backend_info.get("gitlab_access_token")}",
                "lock_method=POST",
                "unlock_method=DELETE",
                "retry_wait_min=5",
            ]
        
    def apply(self, terraform_dir, variables, resources=None):
        """
        Execute terraform apply command.

        Parameters:
            terraform_dir (str): path to the terraform module.
            variables (dict): variables of the terraform module.
            resources (list(str)): name of terraform resources for target apply. Default: None.
        """
        t = python_terraform.Terraform(working_dir=terraform_dir)
        self._run_terraform_cmd(t, "init", [], reconfigure=python_terraform.IsFlagged, backend_config=self._generate_backend_config(terraform_dir))
        self._run_terraform_cmd(t, "plan", variables, input=False, target=resources)
        self._run_terraform_cmd(t, "apply", variables, auto_approve=True, input=False, target=resources)

    def destroy(self, terraform_dir, variables, resources=None):
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