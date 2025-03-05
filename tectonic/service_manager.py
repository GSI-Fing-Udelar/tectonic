
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

from tectonic.constants import OS_DATA
import importlib.resources as tectonic_resources

class ServiceManager(Exception):
    pass

class ServiceManager(ABC):
    """
    ServiceManager class.

    Description: manages services instances.
    You must implement this class if you add a new platform
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
        self.config = config
        self.description = description
        self.client = client

    def get_service_credentials(self, service_base_name, ansible):
        """
        Get service credentials. Use Ansible to connect to machine and get the credentials.

        Parameters:
            service_base_name (str): service name (example: caldera).
            ansible (Ansible): Tectonic Ansible object.
        """
        ansible.run(
            instances=None,
            guests=[service_base_name],
            playbook = tectonic_resources.files('tectonic') / 'playbooks' / 'services_get_password.yml',
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
        
    def _get_service_info(self, service_base_name, ansible, playbook, ansible_vars):
        """
        Get service info. Use Ansible to execute action against service and get specific info.

        Parameters:
            service_base_name (str): service name (example: caldera).
            ansible (Ansible): Tectonic Ansible object.
            playbook (Path): Ansible playbook to apply.
            ansible_vars (dict): Ansible variables to use.

        Returns:
            dict: service information.
        """
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
    
    def install_elastic_agent(self, ansible, instances=None):
        """
        Install elastic agent on instances.

        Parameters:
            ansible (Ansible): Tectonic Ansible object.
            instances (list(int)): instances number. Default: None.
        """
        elastic_name = self.description.get_service_name("elastic")
        if self.client.get_machine_status(elastic_name) == "RUNNING":
            elastic_ip = self.client.get_machine_private_ip(elastic_name)
            result = self._get_service_info("elastic", ansible, self.ELASTIC_INFO_PLAYBOOK, {"action":"get_token_by_policy_name","policy_name":self.description.endpoint_policy_name})
            endpoint_token = result[0]["token"]
            extra_vars = {
                "institution": self.description.institution,
                "lab_name": self.description.lab_name,
                "token": endpoint_token,
                "elastic_url": f"https://{elastic_ip}:8220",
            }
            guests_to_monitor = self.description.get_machines_to_monitor()
            machines = self.description.parse_machines(instances, guests_to_monitor)
            inventory = ansible.build_inventory(machines, extra_vars)
            ansible.run(inventory, self.ELASTIC_AGENT_INSTALL_PLAYBOOK, True)

    def install_caldera_agent(self, ansible, instances=None):
        """
        Install caldera agent on instances.

        Parameters:
            ansible (Ansible): Tectonic Ansible object.
            instances (list(int)): instances number. Default: None
        """
        caldera_name = self.description.get_service_name("caldera")
        if self.client.get_machine_status(caldera_name) == "RUNNING":
            extra_vars = {
                "institution": self.description.institution,
                "lab_name": self.description.lab_name,
                "caldera_ip": self.client.get_machine_private_ip(caldera_name),
                "caldera_agent_type": "red",
            }
            red_team_machines = self.description.get_red_team_machines()
            if len(red_team_machines) > 0:
                machines_red = self.description.parse_machines(instances, red_team_machines)
                inventory_red = ansible.build_inventory(machines_red, extra_vars)
                ansible.run(inventory_red, self.CALDERA_AGENT_INSTALL_PLAYBOOK, True)

            extra_vars["caldera_agent_type"] = "blue"
            blue_team_machines = self.description.get_blue_team_machines()
            if len(blue_team_machines) > 0:
                machines_blue = self.description.parse_machines(instances, blue_team_machines)
                inventory_blue = ansible.build_inventory(machines_blue, extra_vars)
                ansible.run(inventory_blue, self.CALDERA_AGENT_INSTALL_PLAYBOOK, True)

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
    def get_terraform_variables(self):
        """
        Get variables to use in Terraform.

        Return:
            dict: variables.
        """
        pass

    @abstractmethod
    def _get_services_guest_data(self):
        """
        Compute the services guest data as expected by the deployment terraform module.

        Returns:
            dict: services guest data.
        """
        pass

    @abstractmethod
    def _get_services_network_data(self):
        """
        Compute the complete list of services subnetworks.

        Returns:
            dict: services network data.
        """
        pass

    def _build_packetbeat_inventory(self, ansible, variables):
        """
        Build inventory for Ansible when installing Packetbeat.

        Parameters:
            ansible (Ansible): Tectonic ansible object.
            variables: variables for Ansible playbook.
        """ 
        return ansible.build_inventory_localhost(
            username=self.description.user_install_packetbeat,
            extra_vars=variables
        )
    
    def manage_packetbeat(self, ansible, action):
        """
        Get status of Packetbeat service.

        Parameters:
            ansible (Ansible): Tectonic Ansible object.
            action (str): action to apply to Packetbeat.

        Returns:
          str: status of packetbeat service if action was status or None otherwise.
        """
        variables = {
            "action": action,
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
        }
        inventory = self._build_packetbeat_inventory(variables)
        ansible.run(inventory, self.PACKETBEAT_PLAYBOOK, True)
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
        elastic_name = self.description.get_service_name("elastic")
        if self.get_instance_status(elastic_name) == "RUNNING":
            result = self._get_service_info("elastic", ansible, self.ELASTIC_INFO_PLAYBOOK, {"action":"get_token_by_policy_name","policy_name":self.description.packetbeat_policy_name})
            agent_token = result[0]["token"]
            elastic_ip = self.client.get_machine_private_ip(self.description.get_service_name("elastic"))
            variables = {
                "action": "install",
                "elastic_url": f"https://{elastic_ip}:8220",
                "token": agent_token,
                "elastic_agent_version": self.description.elastic_stack_version,
                "institution": self.description.institution,
                "lab_name": self.description.lab_name,
                "proxy": self.description.proxy,
            }
            inventory = self._build_packetbeat_inventory(ansible, variables)
            ansible.wait_for_connections(inventory=inventory)
            ansible.run(inventory, self.PACKETBEAT_PLAYBOOK, True)

    def destroy_packetbeat(self, ansible):
        """
        Destroy Packetbeat for Elastic service network monitoring.

        Parameters:
            ansible (Ansible): Tectonic ansible object.
        """
        variables = {
            "action": "delete",
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
        }
        inventory = self._build_packetbeat_inventory(ansible, variables)
        ansible.run(inventory, self.PACKETBEAT_PLAYBOOK, True)