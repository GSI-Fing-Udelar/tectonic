
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

import packerpy
from abc import ABC, abstractmethod
import json
import math

import importlib.resources as tectonic_resources
from tectonic.ssh import ssh_version
from tectonic.constants import OS_DATA

class PackerException(Exception):
    pass

class Packer(ABC):
    """
    Packer class.

    Description: manages interaction with Packer to build images.
    """

    INSTANCES_PACKER_MODULE = tectonic_resources.files('tectonic') / 'image_generation' / 'create_image.pkr.hcl'
    SERVICES_PACKER_MODULE = tectonic_resources.files('tectonic') / 'services' / 'image_generation' / 'create_image.pkr.hcl'

    def __init__(self, config, description, client):
        """
        Initialize the packer object.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
            client (Client): Tectonic client object
        """
        self.config = config
        self.description = description
        self.client = client
    
    def _invoke_packer(self, packer_module, variables):
        """
        Create images using Packer.

        Parameters: 
            packer_module (str): path to the Packer module.
            variables (dict): variables of the Packer module.
        """
        p = packerpy.PackerExecutable(executable_path=self.config.packer_executable_path)
        return_code, stdout, _ = p.execute_cmd("init", str(packer_module))
        if return_code != 0:
            raise PackerException(f"Packer init returned an error:\n{stdout.decode()}")
        return_code, stdout, _ = p.build(str(packer_module), var=variables)
        # return_code, stdout, _ = p.build(str(packer_module), var=variables, on_error="abort")
        if return_code != 0:
            raise PackerException(f"Packer build returned an error:\n{stdout.decode()}")
        
    def create_instance_image(self, guests):
        """
        Create instances images.

        Parameters:
            guests (list(str)): names of the guests for which to create images. 
        """
        self._invoke_packer(self.INSTANCES_PACKER_MODULE, self._get_instance_variables(guests))

    def create_service_image(self, services):
        """
        Create services images.

        Parameters:
            services (list(str)): names of the services for which to create images. 
        """
        enabled_services = [service.base_name for _, service in self.description.services_guests.items()]
        if list(set(enabled_services).intersection(set(services))):
           self._invoke_packer(self.SERVICES_PACKER_MODULE, self._get_service_variables(services))

    def destroy_instance_image(self, guests):
        """
        Destroy base images.

        Parameters:
            guests (list(str)): names of the guests for which to destroy images.
        """
        machines = []
        machines = [guest for _, guest in self.description.base_guests.items() if not guests or guest.base_name in guests]
        for machine in machines:
            if self.client.is_image_in_use(machine.image_name):
                raise PackerException(f"Unable to delete image {machine.base_name} because it is being used.")
        for machine in machines:
            self.client.delete_image(machine.image_name)

    def destroy_service_image(self, services):
        """
        Destroy base images.

        Parameters:
            services (list(str)): names of the services for which to destroy images.
        """
        machines = []
        machines = [guest for _, guest in self.description.services_guests.items() if services is None or guest.base_name in services]
        for machine in machines:
            if self.client.is_image_in_use(machine.image_name):
                raise PackerException(f"Unable to delete image {machine.base_name} because it is being used.")
        for machine in machines:
            self.client.delete_image(machine.image_name)

    def _get_instance_variables(self, guests):
        """
        Return variables for creating instances images.

        Parameters:
            guests (list(str)): names of the guests for which to create images.

        Returns:
            dict: variables of the Packer module.
        """
        machines = [guest for _, guest in self.description.base_guests.items() if not guests or guest.base_name in guests]
        args = {
            "ansible_playbooks_path": self.description.ansible_dir,
            "ansible_scp_extra_args": "'-O'" if ssh_version() >= 9 and self.config.platform != "docker" else "",
            "ansible_ssh_common_args": self.config.ansible.ssh_common_args,
            "aws_region": self.config.aws.region,
            "instance_number": self.description.instance_number,
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "libvirt_storage_pool": self.config.libvirt.storage_pool,
            "libvirt_uri": self.config.libvirt.uri,
            "machines_json": json.dumps({guest.base_name: guest.to_dict() for guest in machines}),
            "os_data_json": json.dumps(OS_DATA),
            "platform": self.config.platform,
            "remove_ansible_logs": str(not self.config.ansible.keep_logs),
            "elastic_version": self.config.elastic.elastic_stack_version
        }
        if self.config.proxy:
            args["proxy"] = self.config.proxy
        return args

    def _get_service_variables(self, services):
        """
        Return variables for creating instances images.

        Parameters:
            services (list(str)): names of the services for which to create images.

        Returns:
            dict: variables of the Packer module.
        """
        machines = [guest for _, guest in self.description.services_guests.items() if services is None or guest.base_name in services]
        args = {
            "ansible_scp_extra_args": "'-O'" if ssh_version() >= 9 and self.config.platform != "docker" else "",
            "ansible_ssh_common_args": self.config.ansible.ssh_common_args,
            "aws_region": self.config.aws.region,
            "libvirt_storage_pool": self.config.libvirt.storage_pool,
            "libvirt_uri": self.config.libvirt.uri,
            "machines_json": json.dumps({guest.base_name: self._get_service_machine_variables(guest) for guest in machines}),
            "os_data_json": json.dumps(OS_DATA),
            "platform": self.config.platform,
            "remove_ansible_logs": str(not self.config.ansible.keep_logs),
            #TODO: pass variables as a json as part of each host
            "elastic_version": self.config.elastic.elastic_stack_version, 
            "elastic_latest_version": str(self.config.elastic.elastic_stack_version == "latest"), # TODO: Check this
            "elasticsearch_memory": math.floor(self.description.elastic.memory / 1000 / 2)  if self.description.elastic.enable else None,
            "caldera_version": self.config.caldera.version,
            "packetbeat_vlan_id": self.config.aws.packetbeat_vlan_id,
            "caldera_ot_enabled": str(self.config.caldera.ot_enabled),
        }
        if self.config.proxy:
            args["proxy"] = self.config.proxy
        return args
    
    def _get_service_machine_variables(self, service):
        """
        Return machines variables creating services images.

        Parameters:
            service (ServiceDescription): services for which to create images.

        Returns:
            dict: machines variables.
        """
        return {
            "base_os": service.os,
            "ansible_playbook": str(tectonic_resources.files('tectonic') / 'services' / service.base_name / 'base_config.yml')
        }
