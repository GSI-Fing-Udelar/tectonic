
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

    def __init__(self, config, description, client, packer_executable_path="packer"):
        """
        Initialize the packer object.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
            client (Client): Tectonic client object
            packer_executable_path (str): Path to the packer executable on the S.O. Default: packer
        """
        self.config = config
        self.description = description
        self.client = client
        self.packer_executable_path = packer_executable_path
    
    def _invoke_packer(self, packer_module, variables):
        """
        Create images using Packer.

        Parameters: 
            packer_module (str): path to the Packer module.
            variables (dict): variables of the Packer module.
        """
        p = packerpy.PackerExecutable(executable_path=self.packer_executable_path)
        return_code, stdout, _ = p.execute_cmd("init", str(packer_module))
        if return_code != 0:
            raise PackerException(f"Packer init returned an error:\n{stdout.decode()}")
        return_code, stdout, _ = p.build(str(packer_module), var=variables)
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
        self._invoke_packer(self.INSTANCES_PACKER_MODULE, self._get_service_variables(services))

    def destroy_image(self, names):
        """
        Destroy base images.

        Parameters:
            name (list(str)): names of the machines for which to destroy images.
        """
        for guest_name in names:
            image_name = self.description.get_image_name(guest_name)
            if self.client.is_image_in_use(image_name):
                raise PackerException(f"Unable to delete image {image_name} because it is being used.")
        for guest_name in names:
            self.client.delete_image(self.description.get_image_name(guest_name))

    @abstractmethod
    def _get_instance_machines(self, guests):
        """
        Return machines for creating instances images.

        Parameters:
            guests (list(str)): names of the guests for which to create images.

        Returns:
            dict: machines dictionary.
        """
        pass

    @abstractmethod
    def _get_service_machines(self, services):
        """
        Return machines for creating services images.

        Parameters:
            services (list(str)): names of the services for which to create images.

        Returns:
            dict: machines dictionary.
        """
        pass

    def _get_instance_variables(self, guests):
        """
        Return variables for creating instances images.

        Parameters:
            guests (list(str)): names of the guests for which to create images.

        Returns:
            dict: variables of the Packer module.
        """
        machines = self._get_instance_machines(guests)
        args = {
            "ansible_playbooks_path": self.description.ansible_playbooks_path,
            "ansible_scp_extra_args": "'-O'" if ssh_version() >= 9 and self.config.platform != "docker" else "",
            "ansible_ssh_common_args": self.description.ansible_ssh_common_args,
            "aws_region": self.description.aws_region,
            "instance_number": self.description.instance_number,
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "libvirt_storage_pool": self.description.libvirt_storage_pool,
            "libvirt_uri": self.description.libvirt_uri,
            "machines_json": json.dumps(machines),
            "os_data_json": json.dumps(OS_DATA),
            "platform": self.config.platform,
            "remove_ansible_logs": str(not self.description.keep_ansible_logs),
            "elastic_version": self.description.elastic_stack_version
        }
        if self.description.proxy is not None and self.description.proxy != "":
            args["proxy"] = self.description.proxy
        return args

    def _get_service_variables(self, services):
        """
        Return variables for creating instances images.

        Parameters:
            services (list(str)): names of the services for which to create images.

        Returns:
            dict: variables of the Packer module.
        """
        machines = self._get_service_machines(services)
        args = {
            "ansible_scp_extra_args": "'-O'" if ssh_version() >= 9 and self.config.platform != "docker" else "",
            "ansible_ssh_common_args": self.description.ansible_ssh_common_args,
            "aws_region": self.description.aws_region,
            "proxy": self.description.proxy,
            "libvirt_storage_pool": self.description.libvirt_storage_pool,
            "libvirt_uri": self.description.libvirt_uri,
            "machines_json": json.dumps(machines),
            "os_data_json": json.dumps(OS_DATA),
            "platform": self.config.platform,
            "remove_ansible_logs": str(not self.description.keep_ansible_logs),
            #TODO: pass variables as a json as part of each host
            "elastic_version": self.description.elastic_stack_version, 
            "elastic_latest_version": "yes" if self.description.is_elastic_stack_latest_version else "no",
            "elasticsearch_memory": math.floor(self.description.services["elastic"]["memory"] / 1000 / 2)  if self.description.deploy_elastic else None,
            "caldera_version": self.description.caldera_version,
            "packetbeat_vlan_id": self.description.packetbeat_vlan_id,
        }
        return args