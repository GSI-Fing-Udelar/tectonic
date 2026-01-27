
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

from abc import abstractmethod

from tectonic.terraform import Terraform
from tectonic.constants import OS_DATA
import importlib.resources as tectonic_resources

class TerraformServiceException(Exception):
    pass

class TerraformService(Terraform):
    """
    TerraformService class.

    Description: manages interaction with Terraform to deploy/destroy services.
    """

    PACKETBEAT_PLAYBOOK = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml'
    ELASTIC_INFO_PLAYBOOK = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'get_info.yml'
    ELASTIC_AGENT_INSTALL_PLAYBOOK = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'endpoint_install.yml'
    CALDERA_AGENT_INSTALL_PLAYBOOK = tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'agent_install.yml'

    def __init__(self, config, description, client):
        """
        Init method.

        Parameters:
            config (Config): Tectonic config object.
            description (Description): Tectonic description object.
            client (Client): Tectonic client object
        """
        super().__init__(config, description)
        self.client = client
        self.terraform_services_module = tectonic_resources.files('tectonic') / 'services' / 'terraform' / f"services-{self.config.platform}"

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

    def get_service_credentials(self, service, ansible):
        """
        Get service credentials. Use Ansible to connect to machine and get the credentials.

        Parameters:
            service (ServiceDescription): A service description object.
            ansible (Ansible): Tectonic Ansible object.
        """
        ansible.run(
            instances=None,
            guests=[service.base_name],
            playbook = tectonic_resources.files('tectonic') / 'playbooks' / 'services_get_password.yml',
            only_instances=False,
            username=OS_DATA[service.os]["username"],
            quiet=True
        )
        credentials = ansible.debug_outputs[0]["password.stdout"].split("\n")
        result = {}
        for credential in credentials:
            credential_split = credential.split(" ")
            result[credential_split[0]] = credential_split[1]
        return result
        
    def get_service_info(self, service, ansible, playbook, ansible_vars=None):
        """
        Get service info. Use Ansible to execute action against service and get specific info.

        Parameters:
            service (ServiceDescription): A service description object.
            ansible (Ansible): Tectonic Ansible object.
            playbook (Path): Ansible playbook to apply.
            ansible_vars (dict): Ansible variables to use.

        Returns:
            dict: service information.
        """
        ansible.run(
            instances=None,
            guests=[service.base_name],
            playbook=playbook,
            only_instances=False,
            username=OS_DATA[service.os]["username"],
            quiet=True,
            extra_vars=ansible_vars,
        )
        return ansible.debug_outputs
    
    def install_elastic_agent(self, ansible, instances=None):
        """
        Install elastic agent on instances.

        Parameters:
            ansible (Ansible): Tectonic Ansible object.
            instances (list(int)): instances number. Default: None.
        """
        if self.client.get_machine_status(self.description.elastic.name) == "RUNNING":
            result = self.get_service_info(self.description.elastic, ansible, self.ELASTIC_INFO_PLAYBOOK, {
                "action": "get_token_by_policy_name", "policy_name": self.config.elastic.endpoint_policy_name
            })
            endpoint_token = result[0]["token"]
            extra_vars = {
                "token": endpoint_token,
                "elastic_url": f"https://{self.description.elastic.service_ip}:8220",
            }
            guests_to_monitor = [guest_name for guest_name, guest in self.description.base_guests.items() if guest.monitor]
            machines = self.description.parse_machines(instances, guests_to_monitor)
            inventory = ansible.build_inventory(machine_list=machines, extra_vars=extra_vars)
            ansible.run(inventory=inventory, playbook=self.ELASTIC_AGENT_INSTALL_PLAYBOOK, quiet=True)

    def install_caldera_agent(self, ansible, instances=None):
        """
        Install caldera agent on instances.

        Parameters:
            ansible (Ansible): Tectonic Ansible object.
            instances (list(int)): instances number. Default: None
        """
        if self.client.get_machine_status(self.description.caldera.name) == "RUNNING":
            extra_vars = {
                "caldera_ip": self.description.caldera.service_ip,
                "caldera_agent_type": "red",
            }
            red_team_machines = [guest_name for guest_name, guest in self.description._base_guests.items() if guest.red_team_agent]
            if len(red_team_machines) > 0:
                machines_red = self.description.parse_machines(instances=instances, guests=red_team_machines)
                inventory_red = ansible.build_inventory(machine_list=machines_red, extra_vars=extra_vars)
                ansible.run(inventory=inventory_red, playbook=self.CALDERA_AGENT_INSTALL_PLAYBOOK, quiet=True)

            extra_vars["caldera_agent_type"] = "blue"
            blue_team_machines = [guest_name for guest_name, guest in self.description._base_guests.items() if guest.blue_team_agent]
            if len(blue_team_machines) > 0:
                machines_blue = self.description.parse_machines(instances=instances, guests=blue_team_machines)
                inventory_blue = ansible.build_inventory(machine_list=machines_blue, extra_vars=extra_vars)
                ansible.run(inventory=inventory_blue, playbook=self.CALDERA_AGENT_INSTALL_PLAYBOOK, quiet=True)
    
    def _build_packetbeat_inventory(self, ansible, variables):
        """
        Build inventory for Ansible when installing Packetbeat.

        Parameters:
            ansible (Ansible): Tectonic ansible object.
            variables: variables for Ansible playbook.
        """
        return ansible.build_inventory_localhost(username=self.config.elastic.user_install_packetbeat, extra_vars=variables)
    
    def manage_packetbeat(self, ansible, action):
        """
        Manage Packetbeat service.

        Parameters:
            ansible (Ansible): Tectonic Ansible object.
            action (str): action to apply to Packetbeat (status, started, stopped, restarted)

        Returns:
          str: status of packetbeat service if action was status or None otherwise.
        """
        variables = {
            "action": action,
        }
        inventory = self._build_packetbeat_inventory(ansible, variables)
        ansible.run(inventory=inventory, playbook=self.PACKETBEAT_PLAYBOOK, quiet=True)
        if action == "status":
            packetbeat_status = ansible.debug_outputs[0]["agent_status"]
            return packetbeat_status.upper()
        else:
            return None

    def deploy_packetbeat(self, ansible):
        """
        Deploy Packetbeat for Elastic service network monitoring.

        Parameters:
            ansible (Ansible): Tectonic ansible object.
        """
        elastic_name = self.description.elastic.name
        if self.client.get_machine_status(elastic_name) == "RUNNING":
            result = self.get_service_info(self.description.elastic, ansible, self.ELASTIC_INFO_PLAYBOOK, {"action":"get_token_by_policy_name","policy_name":self.config.elastic.packetbeat_policy_name})
            agent_token = result[0]["token"]
            elastic_ip = self.description.elastic.service_ip
            variables = {
                "action": "install",
                "elastic_url": f"https://{elastic_ip}:8220",
                "token": agent_token,
            }
            inventory = self._build_packetbeat_inventory(ansible, variables)
            ansible.wait_for_connections(inventory=inventory)
            ansible.run(inventory=inventory, playbook=self.PACKETBEAT_PLAYBOOK, quiet=True)

    def destroy_packetbeat(self, ansible):
        """
        Destroy Packetbeat for Elastic service network monitoring.

        Parameters:
            ansible (Ansible): Tectonic ansible object.
        """
        variables = {
            "action": "delete",
        }
        inventory = self._build_packetbeat_inventory(ansible, variables)
        ansible.run(inventory=inventory, playbook=self.PACKETBEAT_PLAYBOOK, quiet=True)

    def deploy(self, instances):
        """
        Deploy scenario services.

        Parameters:
            instances (list(int)): number of the instances to deploy.
        """
        resources_to_create = None
        if instances is not None:
            resources_to_create = self._get_resources_to_target_apply(instances)
        self._apply(self.terraform_services_module, self._get_terraform_variables(), resources_to_create)

    def destroy(self, instances):
        """
        Destroy scenario services.

        Parameters:
            instances (list(int)): number of the instances to destroy.
        """
        if instances is None:
            # Destroy everything
            resources_to_destroy = None
        else:
            resources_to_destroy = self._get_resources_to_target_destroy(instances)
        self._destroy(self.terraform_services_module, self._get_terraform_variables(), resources_to_destroy)

    def recreate(self, instances, guests, copies): 
        """
        Recreate scenario services.

        Parameters:
            instances (list(int)): number of the instances to recreate
            guests (list(str)): name of the guests to recreate.
            copies (list(int)): number of the copies to recreate.
        """
        resources_to_recreate = self._get_resources_to_recreate(instances, guests, copies)
        self._apply(self.terraform_services_module, self._get_terraform_variables(), resources_to_recreate, True)

    def _get_service_machine_variables(self, service):
        """
        Return machines variables deploy services.

        Parameters:
            service (ServiceDescription): services to deploy.

        Returns:
            dict: machines variables.
        """
        return {
            "guest_name": service.name,
            "base_name": service.base_name,
            "hostname": service.base_name,
            "base_os": service.os,
            "interfaces": {name : self._get_network_interface_variables(interface) for name, interface in service.interfaces.items()},
            "vcpu": service.vcpu,
            "memory": service.memory,
            "disk": service.disk,
        }

    def _get_terraform_variables(self):
        """
        Get variables to use in Terraform.
        
        Return:
            dict: variables.
        """
        machines = [service for _, service in self.description.services_guests.items()]
        return {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "ssh_public_key_file": self.config.ssh_public_key_file,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps({name: network.to_dict() for name, network in self.description.auxiliary_networks.items()}),
            "guest_data_json": json.dumps({service.name: self._get_service_machine_variables(service) for service in machines}),
            "os_data_json": json.dumps(OS_DATA),
        }
