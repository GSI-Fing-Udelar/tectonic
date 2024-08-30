
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

import json
import random
from passlib.hash import sha512_crypt
import string
import os
from pathlib import Path
import click
from bs4 import BeautifulSoup
import requests
import re

import packerpy
import python_terraform
from tectonic.ssh import ssh_version
from tectonic.ansible import Ansible
from tectonic.constants import OS_DATA
from tectonic.utils import create_table

import importlib.resources as tectonic_resources
import playbooks
import image_generation
import services as services_resources
import services.ansible
import services.elastic
import services.image_generation as services_image_resources


class DeploymentException(Exception):
    pass


class TerraformRunException(Exception):
    pass


def run_terraform_cmd(t, cmd, variables, **args):
    return_code, stdout, stderr = t.cmd(
        cmd, no_color=python_terraform.IsFlagged, var=variables, **args
    )  # TODO: unused variables stdout
    if return_code != 0:
        error = f"ERROR: terraform {cmd} returned an error: {stderr}"
        raise TerraformRunException(error)
    return stdout


class Deployment:
    """Deployment class."""

    # These will be instantiated by the subclass.
    client = None
    ansible_services_path = tectonic_resources.files(services.ansible) / 'configure_services.yml'
    cr_packer_path = tectonic_resources.files(image_generation) / 'create_image.pkr.hcl'

    def __init__(
        self,
        description,
        client,
        gitlab_backend_url,
        gitlab_backend_username,
        gitlab_backend_access_token,
        packer_executable_path,
    ):
        """Initialize the deployment object.

        Attributes:
            description: Description object with the CyberRange description.
            client: The client to use.
            gitlab_backend_url: URL of the GitLab backend.
            gitlab_backend_username: Username of the GitLab backend.
            gitlab_backend_access_token: Access token of the GitLab backend.
            packer_executable_path: Path to the Packer executable.
        """
        self.description = description
        self.client = client
        self.gitlab_backend_url = gitlab_backend_url
        self.gitlab_backend_username = gitlab_backend_username
        self.gitlab_backend_access_token = gitlab_backend_access_token
        self.packer_executable_path = packer_executable_path

    def generate_backend_config(self, terraform_dir):
        """
        Generate Gitlab backend configuration to store Terraform states.

        Parameters:
            terraform_dir (str): path to the terraform module.
        """
        tf_mod_name = os.path.basename(os.path.normpath(terraform_dir))
        address = f"{self.gitlab_backend_url}/{self.description.institution}-{self.description.lab_name}-{tf_mod_name}"

        return [
            f"address={address}",
            f"lock_address={address}/lock",
            f"unlock_address={address}/lock",
            f"username={self.gitlab_backend_username}",
            f"password={self.gitlab_backend_access_token}",
            "lock_method=POST",
            "unlock_method=DELETE",
            "retry_wait_min=5",
        ]

    def terraform_apply(self, terraform_dir, variables, resources=None):
        """
        Execute terraform apply command.

        Parameters:
            terraform_dir (str): path to the terraform module.
            variables (dict): variables of the terraform module.
            resources (list(str)): name of terraform resources for target apply.
        """
        t = python_terraform.Terraform(working_dir=terraform_dir)
        run_terraform_cmd(
            t,
            "init",
            [],
            reconfigure=python_terraform.IsFlagged,
            backend_config=self.generate_backend_config(terraform_dir),
        )
        run_terraform_cmd(t, "plan", variables, input=False, target=resources)
        run_terraform_cmd(
            t, "apply", variables, auto_approve=True, input=False, target=resources
        )


    def get_deploy_cr_vars(self):
        """Build the terraform variable dictionary for deployment of the CyberRange."""
        raise NotImplementedError

    def _deploy_cr(self, terraform_module, terraform_variable, instances):
        """
        Deploy cyber range infrastructure.

        Parameters:
            terraform_module (str): Path to the terraform module to use
            terraform_variable (json): json with variables for terraform module.
            instances (list(int)): instances ids. If the list is not empty only the specified instances are created, otherwise all instances are generated.

        """
        resources_to_create = None
        if instances is not None:
            resources_to_create = self.get_cr_resources_to_target_apply(instances)
        self.terraform_apply(
            terraform_module,
            variables=terraform_variable,
            resources=resources_to_create,
        )

    def terraform_destroy(self, terraform_dir, variables, resources=None):
        """
        Execute terraform destroy command.

        Parameters:
            terraform_dir (str): path to the terraform module.
            variables (dict): variables of the terraform module.
            resources (list(str)): name of terraform resources for target destroy.
        """
        t = python_terraform.Terraform(working_dir=terraform_dir)
        run_terraform_cmd(
            t,
            "init",
            [],
            reconfigure=python_terraform.IsFlagged,
            backend_config=self.generate_backend_config(terraform_dir),
        )
        run_terraform_cmd(
            t, "destroy", variables, auto_approve=True, input=False, target=resources
        )

    def _destroy_cr(self, terraform_path, terraform_variables, instances):
        """
        Destroy cyber range infraestructure.

        Parameters:
            terraform_path (str): path to the terraform module
            terraform_variables (json): json with variables for terraform
            instances (list(int)): instances ids. If the list is not empty only the specified instances are destroyed, otherwise all instances are destroyed.
        """
        resources_to_destroy = None
        if instances is not None:  # Target destroy
            resources_to_destroy = self.get_cr_resources_to_target_destroy(instances)
        self.terraform_destroy(
            terraform_path,
            variables=terraform_variables,
            resources=resources_to_destroy,
        )

    def terraform_recreate(self, terraform_dir, machines):
        """
        Recreate instances machines.

        Parameters:
            machines (list(str)): names of the terraform resources associated with the machines to be recreated.
        """
        t = python_terraform.Terraform(working_dir=terraform_dir)
        run_terraform_cmd(
            t,
            "init",
            [],
            reconfigure=python_terraform.IsFlagged,
            backend_config=self.generate_backend_config(terraform_dir),
        )
        run_terraform_cmd(
            t,
            "plan",
            variables=self.get_deploy_cr_vars(),
            input=False,
            replace=machines,
        )
        run_terraform_cmd(
            t,
            "apply",
            variables=self.get_deploy_cr_vars(),
            auto_approve=True,
            input=False,
            replace=machines,
        )

    def _create_packer_images(self, packer_path, variables):
        """
        Build images using Packer.

        Parameters:
            packer_path (str): path to the Packer module.
            variables (dict): variables of the Packer module.
        """
        p = packerpy.PackerExecutable(executable_path=self.packer_executable_path)
        return_code, stdout, stderr = p.execute_cmd("init", str(packer_path))
        if return_code != 0:
            raise TerraformRunException(
                f"ERROR: packer init returned an error:\n{stdout.decode()}"
            )

        return_code, stdout, stderr = p.build(str(packer_path), var=variables)
        # return_code, stdout, stderr = p.build(packer_path, var=variables, on_error="abort")
        if return_code != 0:
            raise TerraformRunException(
                f"ERROR: packer build returned an error:\n{stdout.decode()}"
            )

    def create_cr_images(self, guests=None):
        """
        Create scenario base images.

        Parameters:
            guests (list(str)): guests names. If the list is not empty only the base images of the specified guests are generated, otherwise all the base images are generated.
        """
        machines = {}
        for guest_name in guests or self.description.guest_settings.keys():
            monitor = True if self.description.deploy_elastic and self.description.get_guest_attr(guest_name, "monitor", False) and self.description.monitor_type == "endpoint" else False
            machines[guest_name] = {
                "base_os": self.description.get_guest_attr(
                    guest_name, "base_os", self.description.default_os
                ),
                "endpoint_monitoring" : monitor,
            }
            if self.description.platform == "libvirt":
                machines[guest_name]["vcpu"] = self.description.get_guest_attr(guest_name, "vcpu", 1)
                machines[guest_name]["memory"] = self.description.get_guest_attr(guest_name, "memory", 1024)
                machines[guest_name]["disk"] = self.description.get_guest_attr(guest_name, "disk", 10)
            elif self.description.platform == "aws":
                machines[guest_name]["disk"] = self.description.get_guest_attr(guest_name, "disk", 8)
                machines[guest_name]["instance_type"] = self.description.instance_type.get_guest_instance_type(
                    self.description.get_guest_attr(guest_name, "memory", 1),
                    self.description.get_guest_attr(guest_name, "vcpu", 1),
                    monitor,
                    self.description.monitor_type,
                )
        args = {
            "ansible_playbooks_path": self.description.ansible_playbooks_path,
            "ansible_scp_extra_args": "'-O'" if ssh_version() >= 9 else "",
            "ansible_ssh_common_args": self.description.ansible_ssh_common_args,
            "aws_region": self.description.aws_region,
            "instance_number": self.description.instance_number,
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "libvirt_proxy": self.description.libvirt_proxy,
            "libvirt_storage_pool": self.description.libvirt_storage_pool,
            "libvirt_uri": self.description.libvirt_uri,
            "machines_json": json.dumps(machines),
            "os_data_json": json.dumps(OS_DATA),
            "platform": self.description.platform,
            "remove_ansible_logs": str(not self.description.keep_ansible_logs),
            "elastic_version": self.description.elastic_stack_version
        }
        self._create_packer_images(self.cr_packer_path, args)

    def get_teacher_access_username(self):
        """
        Get username for connection to teacher access host.
        """
        return OS_DATA[self.description.default_os]["username"]

    def get_teacher_access_ip(self):
        """
        Returns the public IP assigned to the teacher access host.
        """
        if self.description.teacher_access == "host":
            return self.client.get_machine_public_ip(
                self.description.get_teacher_access_name()
            )
        return None

    def get_student_access_users(self):
        """Returns a dictionary of users with username, password, password_hash and authorized_keys.
        """
        users = {}
        random.seed(self.description.random_seed)
        for i in self.description.get_instance_range():
            username = f"{self.description.student_prefix}{i:02d}"
            users[username] = {}
            if self.description.create_student_passwords:
                (password, salt) = self._generate_password()
                users[username]["password"] = password
                users[username]["password_hash"] = sha512_crypt.using(salt=salt).hash(
                    password
                )

            if self.description.student_pubkey_dir:
                users[username]["authorized_keys"] = self.description.read_pubkeys(
                    os.path.join(self.description.student_pubkey_dir, username)
                )

        return users
        

    def _student_access(self, instances, guests):
        """Creates users for the students in all GUESTS of INSTANCES.

        Generates pseudo-random passwords and/or sets public SSH keys for the users.
        Returns a dictionary of created users.
        """
        playbook = tectonic_resources.files(playbooks) / "trainees.yml"
        
        users = self.get_student_access_users()
        only_instances = True
        if guests and "student_access" in guests:
            only_instances = False
        ansible = Ansible(self)
        ansible.run(
            instances=instances,
            guests=guests,
            copies=None,  # Apply playbook to all copies
            playbook=playbook,
            only_instances=only_instances,
            extra_vars={"users": users, "prefix": self.description.student_prefix, "ssh_password_login": self.description.create_student_passwords},
            quiet=True,
        )
        return users

    def student_access(self, instances):
        """Creates users for the students in all entry points of INSTANCES.

        Generates pseudo-random passwords and/or sets public SSH keys for the users.
        Returns a dictionary of created users.
        """
        entry_points = [ base_name for base_name, guest in self.description.guest_settings.items()
                         if guest and guest.get("entry_point") ]
        self._student_access(instances, entry_points)


    def _generate_password(self):
        """Generate a pseudo random password and salt."""
        characters = string.ascii_letters + string.digits
        password = "".join(random.choice(characters) for _ in range(12))
        salt = "".join(random.choice(characters) for _ in range(16))
        return password, salt

    # Abstract methods to be implemented by platform dependent sub-classes:

    def delete_cr_images(self, guests=None):
        """Delete guests scenario images."""
        raise NotImplementedError

    def get_instance_status(self, machine):
        """
        Returns a dictionary with the instance status of machine ID.

        Parameters:
            machine (str): machine identifier

        Returns:
            dict: instance status information
        """
        raise NotImplementedError

    def get_cyberrange_data(self):
        """Returns a dictionary with Cyber Range data."""
        raise NotImplementedError

    def connect_to_instance(self, instance_name, username):
        """
        Interactively connects to a running instance.

        Parameters:
            instance_name (str): name for the instance.
            username: (str): username
        """
        raise NotImplementedError

    def get_ssh_proxy_command(self):
        """Returns the appropriate SSH proxy configuration to access guest machines."""
        return None

    def get_ssh_hostname(self, machine):
        """Returns the appropriate SSH hostname to access guest machines."""
        return self.client.get_machine_private_ip(machine)

    def start_instance(self, instance_name):
        """
        Starts a stopped instance.

        Parameters:
            instance_name (str): name of the instance.
        """
        raise NotImplementedError

    def stop_instance(self, instance_name):
        """
        Stops a running instance.

        Parameters:
            instance_name (str): name of the instance.
        """
        raise NotImplementedError

    def reboot_instance(self, instance_name):
        """
        Reboots a running instance.

        Parameters:
            instance_name (str): name of the instance.
        """
        raise NotImplementedError

    def can_delete_image(self, image_name):
        """
        Return true if the image is not being used by any machine.

        Parameters:
            image_name (str): name of the image.

        Returns:
            bool: true if the image is not being used by any machine, false otherwise.
        """
        raise NotImplementedError

    def get_cr_resources_to_target_apply(self, instances):
        """
        Returns the name of the resources to target apply based on the instance numbers.

        Parameters:
          instances (list(int)): instances to use.

        Returns:
          list(str): resources name to target apply.
        """
        raise NotImplementedError

    def get_cr_resources_to_target_destroy(self, instances):
        """
        Returns the name of the resource to target destroy based on the instance numbers.

        Parameters:
          instances (list(int)): instances to use.

        Returns:
          list(str): resources name to target destroy.
        """
        raise NotImplementedError

    def get_resources_to_recreate(self, instances, guests, copies):
        """
        Returns the name of the terraform resources to recreate based on the machines names.

        Parameters:
          instances (list(int)): instances to use.

        Returns:
          list(str): resource names to recreate.
        """
        raise NotImplementedError

    def get_elastic_latest_version(self):
        """
        Return latest version of elastic stack available

        Returns:
          str: elastic stack version
        """
        try:
            elastic_url = 'https://www.elastic.co/guide/en/elasticsearch/reference/current/es-release-notes.html'
            html_text = requests.get(elastic_url).text
            soup = BeautifulSoup(html_text, 'html.parser')
            versions = soup.find_all('a', attrs={"title": re.compile("Elasticsearch version \\d+\\.\\d+\\.\\d+")})
            latest_version = versions[0].get("title").split(" ")[2]
            return latest_version
        except Exception as e:
            raise DeploymentException(e)

    def get_guest_instance_type(self, base_name):
        """
        Return the guest instance type.

        Parameters:
            base_name (str): guests base name
        """
        return None

    def list_instances(self, instances, guests, copies):
        """
        Get info about Cyber range

        Returns table containing information about cyber range
        """
        raise NotImplementedError
    
    def shutdown(self, instances, guests, copies, stop_services):
        """
        Shutdown cyber range machines.
        """
        raise NotImplementedError
    
    def start(self, instances, guests, copies, start_services):
        """
        Start cyber range machines.
        """
        raise NotImplementedError
    
    def reboot(self, instances, guests, copies, reboot_services):
        """
        Reboot cyber range machines.
        """
        raise NotImplementedError
    
    def recreate(self, instances, guests, copies, recreate_services=False): #TODO: add support for recreating services
        """
        Recreate cyber range machines.
        """
        raise NotImplementedError
    
    def deploy_infraestructure(self, instances):
        """
        Deploy cyber range infraestructure
        """
        raise NotImplementedError

    def destroy_infraestructure(self, instances):
        """
        Destroy cyber range infraestructure
        """
        raise NotImplementedError
    
    def get_elastic_agent_status(self):
        """
        Get elastic agent status
        """
        raise NotImplementedError
    
    def get_parameters(self, instances, directory):
        self.description.parse_machines(instances)
        parameters = self.description.get_parameters(instances)
        headers = ["Instance","Parameters"]
        rows = []
        for parameter in parameters:
            rows.append([parameter,parameters[parameter]])
        if directory:
            if Path(directory).is_dir():
                try:
                    filename = os.path.join(directory, f"{self.description.institution}-{self.description.lab_name}-parameters.json")
                    with open(filename, "w") as parameters_file:
                        parameters_file.write(json.dumps(parameters, indent=4))
                        parameters_file.write("\n")
                        
                        print(f"File {filename} created")
                except Exception as exception:
                    raise TerraformRunException(f"{exception}")
            else:
                raise TerraformRunException(f"ERROR: directory {directory} does not exist.")
        else:
            click.echo(create_table(headers,rows))

    def create_services_images(self, services):
        """
        Create services base images.

        Parameters:
            services (dict(bool)): services images to create.
        """
        machines = {}
        for service in services:
            if services[service]:
                machines[service] = {
                    "base_os": self.description.get_service_base_os(service),
                    "ansible_playbook": str(tectonic_resources.files(services_resources) / service / 'base_config.yml'),
                }
                if self.description.platform == "libvirt":
                        machines[service]["vcpu"] = self.description.services[service]["vcpu"]
                        machines[service]["memory"] = self.description.services[service]["memory"]
                        machines[service]["disk"] = self.description.services[service]["disk"]
                elif self.description.platform == "aws":
                    machines[service]["disk"] = self.description.services[service]["disk"]
                    if service in ["caldera", "elastic"]:
                        machines[service]["instance_type"] = self.description.instance_type.get_guest_instance_type(self.description.services[service]["memory"], self.description.services[service]["vcpu"], False, self.description.monitor_type)
                    elif service == "packetbeat":
                        machines[service]["instance_type"] = "t2.micro"
        args = {
            "ansible_scp_extra_args": "'-O'" if ssh_version() >= 9 else "",
            "ansible_ssh_common_args": self.description.ansible_ssh_common_args,
            "aws_region": self.description.aws_region,
            "libvirt_proxy": self.description.libvirt_proxy,
            "libvirt_storage_pool": self.description.libvirt_storage_pool,
            "libvirt_uri": self.description.libvirt_uri,
            "machines_json": json.dumps(machines),
            "os_data_json": json.dumps(OS_DATA),
            "platform": self.description.platform,
            "remove_ansible_logs": str(not self.description.keep_ansible_logs),
            #TODO: pass variables as a json as part of each host
            "elastic_version": self.description.elastic_stack_version, 
            "elastic_latest_version": "yes" if self.description.is_elastic_stack_latest_version else "no",
            "caldera_version": "master",
            "packetbeat_vlan_id": self.description.packetbeat_vlan_id,
        }
        self._create_packer_images(tectonic_resources.files(services_image_resources) / 'create_image.pkr.hcl', args)

    def delete_services_images(self, services):
        """Delete services images."""
        raise NotImplementedError

    def get_deploy_services_vars(self):
        """Build the terraform variable dictionary for deployment of the CyberRange services."""
        raise NotImplementedError

    def get_services_status(self):
        """Get services status"""
        raise NotImplementedError
    
    def _elastic_install_endpoint(self, instances=None):
        """
        Install elastic endpoint on instances

        Parameters:
            instances(list(int)): instances number
        """
        elastic_name = self.description.get_service_name("elastic")
        if self.get_instance_status(elastic_name) == "RUNNING":
            elastic_ip = self.get_ssh_hostname(elastic_name)
            playbook = tectonic_resources.files(services.elastic) / 'get_info.yml',
            result = self._get_service_info("elastic",playbook,{"action":"get_token_by_policy_name","policy_name":self.description.endpoint_policy_name})
            endpoint_token = result[0]["token"]
            extra_vars = {
                "institution": self.description.institution,
                "lab_name": self.description.lab_name,
                "token": endpoint_token,
                "elastic_url": f"https://{elastic_ip}:8220",
            }
            ansible = Ansible(deployment=self)
            guests_to_monitor = self.description.get_machines_to_monitor()
            machines = self.description.parse_machines(instances=instances, guests=guests_to_monitor)
            inventory = ansible.build_inventory(machine_list=machines, extra_vars=extra_vars)
            ansible.wait_for_connections(inventory=inventory)
            ansible.run(inventory=inventory,playbook=tectonic_resources.files(services.elastic) / "endpoint_install.yml",quiet=True)
        else:
            raise DeploymentException("Elastic machine is not running. Unable to install endpoints.")

    def _caldera_install_agent(self, instances=None):
        """
        Install caldera agent on instances

        Parameters:
            instances(list(int)): instances number
        
        """
        extra_vars = {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "caldera_ip": self.get_ssh_hostname(self.description.get_service_name("caldera")),
            "caldera_agent_type": "red",
        }
        ansible = Ansible(deployment=self)
        red_team_machines = self.description.get_red_team_machines()
        if len(red_team_machines) > 0:
            machines_red = self.description.parse_machines(instances=instances, guests=red_team_machines)
            inventory_red = ansible.build_inventory(machine_list=machines_red, extra_vars=extra_vars)
            ansible.wait_for_connections(inventory=inventory_red)
            ansible.run(inventory = inventory_red,
                        playbook = tectonic_resources.files(services.caldera) / 'agent_install.yml',
                        quiet = True)

        extra_vars["caldera_agent_type"] = "blue"
        blue_team_machines = self.description.get_blue_team_machines()
        if len(blue_team_machines) > 0:
            machines_blue = self.description.parse_machines(instances=instances, guests=blue_team_machines)
            inventory_blue = ansible.build_inventory(machine_list=machines_blue, extra_vars=extra_vars)
            ansible.wait_for_connections(inventory=inventory_blue)
            ansible.run(inventory = inventory_blue,
                        playbook = tectonic_resources.files(services.caldera) / 'agent_install.yml',
                        quiet = True)

    def _get_services_guest_data(self):
        """
        Build the terraform variable dictionary for deployment of the CyberRange services.
        """
        raise NotImplementedError
    
    def _get_services_network_data(self):
        """Compute the complete list of services subnetworks."""
        raise NotImplementedError
    
    def _get_service_password(self, service_base_name):
        """
        Get service credentials. Use Ansible to connect to machine and get the credentials.

        Parameters:
            service_base_name (str): service name (example: caldera).
        """
        try:
            ansible = Ansible(self)
            ansible.run(
                instances=None,
                guests=[service_base_name],
                playbook = tectonic_resources.files(playbooks) / 'services_get_password.yml',
                only_instances=False,
                username=OS_DATA[self.description.get_service_base_os(service_base_name)]["username"],
                quiet=True
            )
            credentials = ansible.debug_outputs[0]["password.stdout"].split("\n")
            result = {}
            for credential in credentials:
                credential_split = credential.split(" ")
                result[credential_split[0]] = credential_split[1]
            return result
        except Exception as e:
            raise TerraformRunException(f"{e}")
        
    def _destroy_services(self, terraform_path, terraform_variables, instances):
        """
        Destroy cyber range services infraestructure.

        Parameters:
            terraform_path (str): path to the terraform module
            terraform_variables (json): json with variables for terraform
            instances (list(int)): instances ids. If the list is not empty only the specified instances are destroyed, otherwise all instances are destroyed.
        """
        resources_to_destroy = None
        if instances is not None:  # Target destroy
            resources_to_destroy = self.get_services_resources_to_target_destroy(instances)
        self.terraform_destroy(terraform_path, variables=terraform_variables, resources=resources_to_destroy)

    def get_services_resources_to_target_destroy(self, instances):
        """
        Returns the name of the services resources to target destroy based on the instance numbers.

        Parameters:
          instances (list(int)): instances to use.

        Returns:
          list(str): resources name to target destroy.
        """
        raise NotImplementedError
    
    def _deploy_services(self, terraform_module, terraform_variable, instances):
        """
        Deploy cyber range infrastructure.

        Parameters:
            terraform_module (str): Path to the terraform module to use
            terraform_variable (json): json with variables for terraform module.
            instances (list(int)): instances ids. If the list is not empty only the specified instances are created, otherwise all instances are generated.

        """
        resources_to_create = None
        if instances is not None:
            resources_to_create = self.get_services_resources_to_target_apply(instances)
        self.terraform_apply(terraform_module, variables=terraform_variable, resources=resources_to_create)

    def get_sevices_resources_to_target_apply(self, instances):
        """
        Returns the name of the services resources to target apply based on the instance numbers.

        Parameters:
          instances (list(int)): instances to use.

        Returns:
          list(str): resources name to target apply.
        """
        raise NotImplementedError
    
    def _get_service_info(self, service_base_name, playbook, ansible_vars):
        """
        Get service info. Use Ansible to execute action against service and get specific info.

        Parameters:
            service_base_name (str): service name (example: caldera).
            playbook (Path): Ansible playbook to apply.
            ansible_vars (dict): Ansible variables to use.
        """
        try:
            ansible = Ansible(self)
            ansible.run(
                instances=None,
                guests=[service_base_name],
                playbook=playbook,
                only_instances=False,
                username=OS_DATA[self.description.get_service_base_os(service_base_name)]["username"],
                quiet=True,
                extra_vars=ansible_vars,
            )
            return ansible.debug_outputs
        except Exception as e:
            raise TerraformRunException(f"{e}")
