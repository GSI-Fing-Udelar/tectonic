
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

import logging
import math
from pathlib import Path
import ansible_runner
import importlib.resources as tectonic_resources

from tectonic.config import TectonicConfig
from tectonic.description import MachineDescription, Description, DescriptionException
from tectonic.client import Client

logger = logging.getLogger(__name__)

class AnsibleException(Exception):
    """ AnsibleException class """
    pass


class Ansible:
    """ Class for managing Ansible connections. """
    ANSIBLE_SERVICE_PLAYBOOK = tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'

    def __init__(self, config, description, client):
        self.config = config
        self.description = description
        self.client = client

        self.output = ""
        self.debug_outputs = []


    def _ansible_callback(self, event_data):
        if event_data['stdout']:
            self.output += f"\n{event_data['stdout']}"
            event_data = event_data.get("event_data")
            if event_data:
                resolved_action = event_data.get("resolved_action")
                if resolved_action == "ansible.builtin.debug" and event_data.get("res"):
                    debug_output = event_data["res"]
                    if debug_output.get("_ansible_verbose_always"):
                        del debug_output["_ansible_verbose_always"]
                    if debug_output.get("_ansible_no_log"):
                        del debug_output["_ansible_no_log"]
                    if debug_output.get("changed"):
                        del debug_output["changed"]
                    self.debug_outputs.append(debug_output)
        return True

    def build_inventory(self, machine_list=None, username=None, extra_vars=None):
        if extra_vars is None:
            extra_vars = {}
        if machine_list is None:
            machine_list = []
        inventory = {}

        parameters = self.description.get_parameters()

        ssh_args = self.config.ansible.ssh_common_args

        proxy_command = self.client.get_ssh_proxy_command()
        if proxy_command:
            ssh_args += f' -o ProxyCommand="{proxy_command}"'

        networks = {}
        for _, guest in self.description.scenario_guests.items():
            if guest.instance not in networks:
                networks[guest.instance] = {}
            for _, interface in guest.interfaces.items():
                if interface.network.name not in networks[guest.instance]:
                    networks[guest.instance][interface.network.name] = {}
                networks[guest.instance][interface.network.name][guest.base_name] = interface.name

        for machine_name in machine_list:
            if machine_name in self.description.services_guests:
                machine = self.description.services_guests[machine_name]
            elif machine_name in self.description.scenario_guests:
                machine = self.description.scenario_guests[machine_name]
            elif machine_name in self.description.extra_guests:
                machine = self.description.extra_guests[machine_name]
            else:
                raise AnsibleException(f"Machine name {machine_name} not found.")

            ansible_username = username or machine.admin_username
            hostname = self.client.get_ssh_hostname(machine_name)

            if not inventory.get(machine.base_name):
                inventory[machine.base_name] = {
                    "hosts": {},
                    "vars": {
                                "ansible_become": True,
                                "basename": machine.base_name,
                                "instances": self.description.instance_number,
                                "platform": self.config.platform,
                                "institution": self.description.institution,
                                "lab_name": self.description.lab_name,
                                "ansible_connection" : "community.docker.docker_api" if self.config.platform == "docker" else "ssh", #export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES on macos
                                "docker_host": self.config.docker.uri,
                            } | extra_vars,
                }

            inventory[machine.base_name]["hosts"][machine.name] = {
                "ansible_host": hostname if self.config.platform != "docker" else machine.name,
                "ansible_user": ansible_username,
                "ansible_ssh_common_args": ssh_args,
                "machine_name": machine.name,
                "instance": machine.instance,
                "copy": machine.copy,
                "networks": networks[machine.instance],
                "parameter": parameters[machine.instance] if machine.instance else {},
                "random_seed": self.description.random_seed,
            }

            if machine.os == "windows_srv_2022":
                inventory[machine.base_name]["hosts"][machine.name]["ansible_shell_type"] = "powershell"
                inventory[machine.base_name]["hosts"][machine.name]["ansible_become_method"] = "runas"
                inventory[machine.base_name]["hosts"][machine.name]["ansible_become_user"] = machine.admin_username
            else:
                # Make sure we load environment variables within sudo shell
                inventory[machine.base_name]["hosts"][machine.name]["become_flags"] = "-i"
        return inventory
    
    def build_inventory_localhost(self, username=None, extra_vars=None):
        if extra_vars is None:
            extra_vars = {}
        return {
            f"{self.description.institution}-{self.description.lab_name}-localhost" : {
                "hosts": {
                    "localhost": {
                        "become_flags": "-i",
                    }
                },
                "vars": {
                    "ansible_become": True,
                    "ansible_user": username or self.config.elastic.user_install_packetbeat,
                    "basename": "localhost",
                    "instances": self.description.instance_number,
                    "platform": self.config.platform,
                    "institution": self.description.institution,
                    "lab_name": self.description.lab_name,
                    "ansible_connection" : "local",
                } | extra_vars,
            }
        }

    def run(self,
            instances=None,
            guests=None,
            copies=None,
            only_instances=True,
            username=None,
            inventory=None,
            playbook=None,
            extra_vars=None,
            quiet=False,
            verbosity=0,
            exclude=[]
            ):
        """ Run Ansible playbook.

        Args:
            instances (list(int)): List of instances to run the playbook on.
            guests (list): List of guests to run the playbook on.
            copies (list(int)): List of copies to run the playbook on.
            only_instances (bool): If True, only run the playbook on instances.
            username (str): Username to use for Ansible connections.
            inventory (dict): Ansible inventory dictionary.
            playbook (str): Ansible playbook to run.
            extra_vars (dict): Extra variables to pass to Ansible.
            quiet (bool): If True, suppress ansible output, and raise an exception on error.
            verbosity (int): Ansible verbosity level.
            exclude (list): guest name of machines to exclude from applying playbook

        Raises:
            AnsibleException: If the playbook fails and quiet is False.
        """
        default_playbook = Path(self.description.scenario_dir) / "ansible" / "after_clone.yml"

        if not playbook:
            if default_playbook.is_file():
                playbook = default_playbook.resolve().as_posix()
            else:
                if not quiet:
                    print("No playbook to run") #TODO: raise exception?
                return
        else:
            playbook = Path(playbook).resolve().as_posix()
            if not Path(playbook).is_file():
                raise AnsibleException(f"Playbook {playbook} not found.")
        if not inventory:
            machine_list = self.description.parse_machines(
                instances, guests, copies, only_instances, exclude
            )
            inventory = self.build_inventory(
                machine_list=machine_list,
                username=username,
                extra_vars=extra_vars
            )
        self.output = ""
        self.debug_outputs = []
        extravars = { "ansible_no_target_syslog" : not self.config.ansible.keep_logs }
        
        # ============================================================================
        # CUSTOM ANSIBLE COMPONENTS INTEGRATION
        # ============================================================================
        # Tectonic supports custom Ansible modules, roles, and filter plugins by
        # setting environment variables that Ansible automatically recognizes.
        # 
        # Two-tier component discovery:
        #   1. Core components (tectonic/ansible/):
        #      - tectonic/ansible/library/        -> Global modules (e.g., encrypt_files_aes.py)
        #      - tectonic/ansible/filter_plugins/ -> Global Jinja2 filters
        #      - tectonic/ansible/module_utils/   -> Shared utilities for modules
        #   
        #
        # Path priority (uses colon-separated paths):
        #   - ANSIBLE_LIBRARY: tectonic_library
        #   - ANSIBLE_FILTER_PLUGINS: tectonic_filter_plugins
        #
        # This approach:
        #   ✓ Provides global components for all scenarios
        #   ✓ Allows scenario-specific overrides
        #   ✓ Maintains backward compatibility
        #   ✓ Works seamlessly with ansible_runner
        # ============================================================================
        
        # Core Tectonic components (always available)
        tectonic_ansible_dir = tectonic_resources.files('tectonic') / 'ansible'
        tectonic_library_path = tectonic_ansible_dir / "library"
        tectonic_filter_plugins_path = tectonic_ansible_dir / "filter_plugins"
        tectonic_module_utils_path = tectonic_ansible_dir / "module_utils"
        
        envvars = { 
            "ANSIBLE_FORKS": self.config.ansible.forks,
            "ANSIBLE_HOST_KEY_CHECKING": False,
            "ANSIBLE_PIPELINING": self.config.ansible.pipelining,
            "ANSIBLE_GATHERING": "explicit",
            "ANSIBLE_TIMEOUT": self.config.ansible.timeout,
        }
        
        # Build ANSIBLE_LIBRARY path
        library_paths = []
        if tectonic_library_path.exists() and tectonic_library_path.is_dir():
            library_paths.append(tectonic_library_path.as_posix())
            logger.info(f"Using core Ansible library: {tectonic_library_path}")
        if library_paths:
            envvars["ANSIBLE_LIBRARY"] = ":".join(library_paths)
        # Build ANSIBLE_FILTER_PLUGINS path
        filter_paths = []
        if tectonic_filter_plugins_path.exists() and tectonic_filter_plugins_path.is_dir():
            filter_paths.append(tectonic_filter_plugins_path.as_posix())
            logger.info(f"Using core Ansible filter plugins: {tectonic_filter_plugins_path}")
        if filter_paths:
            envvars["ANSIBLE_FILTER_PLUGINS"] = ":".join(filter_paths)
        # Set ANSIBLE_MODULE_UTILS (required for custom module_utils)
        if tectonic_module_utils_path.exists() and tectonic_module_utils_path.is_dir():
            envvars["ANSIBLE_MODULE_UTILS"] = tectonic_module_utils_path.as_posix()
            logger.info(f"Using core Ansible module_utils: {tectonic_module_utils_path}")
        
        r = ansible_runner.interface.run(
            inventory=inventory,
            playbook=playbook,
            quiet=quiet,
            verbosity=verbosity,
            event_handler=self._ansible_callback,
            extravars=extravars,
            envvars=envvars,
        )
        logger.info(self.output)

        if (r.rc != 0 or r.status != "successful") and quiet:
            raise AnsibleException(self.output)

    def wait_for_connections(self, instances=None, guests=None, copies=None, only_instances=True, exclude=[], username=None, inventory=None):
        """Wait for machines to respond to ssh connections for ansible."""
        playbook = tectonic_resources.files('tectonic') / 'ansible' / 'playbooks' / 'wait_for_connection.yml'

        return self.run(
            instances=instances, guests=guests, copies=copies,
            only_instances=only_instances,
            playbook=playbook, quiet=True,
            exclude=exclude, username=username, inventory=inventory
        )

    def configure_services(self):
        services = [service.name for _, service in self.description.services_guests.items()]
        if services:
            extra_vars = {
                "elastic" : {
                    "monitor_type": self.description.elastic.monitor_type,
                    "deploy_policy": self.description.elastic.deploy_default_policy,
                    "policy_name": self.config.elastic.packetbeat_policy_name if self.description.elastic.monitor_type == "traffic" else self.config.elastic.endpoint_policy_name,
                    "http_proxy" : self.config.proxy if self.config.proxy is not None else "",
                    "description_path": str(self.description.scenario_dir),
                    "ip": self.description.elastic.service_ip,
                    "elasticsearch_memory": math.floor(self.description.elastic.memory / 1000 / 2)  if self.description.elastic.enable else None,
                    "dns": self.config.docker.dns,
                },
                "caldera":{
                    "ip": self.description.caldera.service_ip,
                    "description_path": str(self.description.scenario_dir),
                    "ot_enabled": str(self.config.caldera.ot_enabled)
                },
            }
            inventory = self.build_inventory(machine_list=services, extra_vars=extra_vars)
            self.wait_for_connections(inventory=inventory)
            self.run(inventory=inventory, playbook=self.ANSIBLE_SERVICE_PLAYBOOK, quiet=True)
