
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
import click

from tectonic.deployment import Deployment, DeploymentException
from tectonic.docker_client import Client
from tectonic.constants import OS_DATA
from tectonic.utils import create_table
from tectonic.ansible import Ansible

import importlib.resources as tectonic_resources

import terraform.modules



class DeploymentDockerException(DeploymentException):
    pass

class DockerDeployment(Deployment):

    def __init__(
        self,
        description,
        gitlab_backend_url,
        gitlab_backend_username,
        gitlab_backend_access_token,
        packer_executable_path="/usr/bin/packer",
    ):
        super().__init__(
            description,
            Client(description),
            gitlab_backend_url,
            gitlab_backend_username,
            gitlab_backend_access_token,
            packer_executable_path
        )

    def get_deploy_cr_vars(self):
        """Build the terraform variable dictionary for deployment of the CyberRange."""
        return {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "instance_number": self.description.instance_number,
            "ssh_public_key_file": self.description.ssh_public_key_file,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps(self.description.subnets),
            "guest_data_json": json.dumps(self.description.get_guest_data()),
            "default_os": self.description.default_os,
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.description.configure_dns,
            "docker_uri": self.description.docker_uri,
            }

    def can_delete_image(self, image_name):
        """
        Return true if the image is not being used by any machine.

        Parameters:
          image_name (str): name of the image

        Returns:
          bool: true if the image is not being used by any machine or false otherwise
        """
        image = self.client.get_image(image_name)
        if image:
            image_id = image[0]
            instances_images_ids = self.client.get_machines_imageid()
            for instance_image_id in instances_images_ids:
                if image_id == instance_image_id:
                    return False
        return True

    def delete_cr_images(self, guests=None):
        guests = guests or self.description.guest_settings.keys()
        for guest_name in guests:
            try: 
                print(self.description.get_image_name(guest_name))
                self.client.delete_image(self.description.get_image_name(guest_name))
            except Exception as exception:
                raise DeploymentDockerException(f"{exception}")

    def create_cr_images(self, guests=None):
        #self.delete_cr_images(guests)
        super().create_cr_images(guests)

    def deploy_infraestructure(self, instances):
        """
        Deploy cyber range infraestructure
        """
        ansible = Ansible(self)

        click.echo("Deploying Cyber Range instances...")
        self._deploy_cr(tectonic_resources.files(terraform.modules) / 'gsi-lab-docker',
                        self.get_deploy_cr_vars(),
                        instances)
        
        click.echo("Waiting for machines to boot up...")
        ansible.wait_for_connections(instances=instances)

        click.echo("Configuring student access...")
        self.student_access(instances)

        click.echo("Running after-clone configuration...")
        ansible.run(instances, quiet=True)

    def destroy_infraestructure(self, instances):
        """
        Destroy cyber range infraestructure
        """
        click.echo("Destroying Cyber Range instances...")
        self._destroy_cr(tectonic_resources.files(terraform.modules) / 'gsi-lab-docker',
                         self.get_deploy_cr_vars(),
                         instances)
        
    def get_cyberrange_data(self):
        """Get information about cyber range"""
        try:
            if len(self.description.get_services_to_deploy()) > 0:
                #TODO
                return
        except Exception as exception:
            raise DeploymentDockerException(f"{exception}")
        
    def get_instance_status(self, instance_name):
        """Returns a dictionary with the instance status."""
        return self.client.get_instance_status(instance_name)
        
    def list_instances(self, instances, guests, copies):
        machines_to_list = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        headers = ["Name", "Status"]
        rows = []
        for machine in machines_to_list:
            machine_status = self.get_instance_status(machine)
            rows.append([machine,machine_status])
        return create_table(headers,rows)
    
    def get_services_status(self):
        if len(self.description.get_services_to_deploy()) > 0:
            #TODO
            return
        else:
            return "No services were deployed."
        
    def start_instance(self, instance_name):
        self.client.start_instance(instance_name)

    def stop_instance(self, instance_name):
        self.client.stop_instance(instance_name)

    def reboot_instance(self, instance_name):
        self.client.reboot_instance(instance_name)

    def shutdown(self, instances, guests, copies, stop_services):
        if stop_services:
            click.echo(f"Shutting down services...")
            #TODO             
        machines_to_shutdown = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy()) 
        for machine in machines_to_shutdown:
            click.echo(f"Shutting down instance {machine}...")
            self.stop_instance(machine)
            
    def start(self, instances, guests, copies, start_services):
        if start_services:
            click.echo(f"Booting up services...")
            #TODO
        machines_to_start = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())  
        for machine in machines_to_start:
            click.echo(f"Booting up instance {machine}...")
            self.start_instance(machine)

    def reboot(self, instances, guests, copies, reboot_services):
        if reboot_services:
            click.echo(f"Rebooting services...")
            #TODO
        machines_to_reboot = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        for machine in machines_to_reboot:
            click.echo(f"Rebooting instance {machine}...")
            self.reboot_instance(machine)

    def connect_to_instance(self, instance_name, username):
        username = username or self.description.get_guest_username(self.description.get_base_name(instance_name))
        self.client.connect(instance_name, username)