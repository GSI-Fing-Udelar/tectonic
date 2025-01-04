
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
import pprint
from pathlib import Path
import ansible_runner
import importlib.resources as tectonic_resources


logger = logging.getLogger(__name__)

class AnsibleException(Exception):
    """ AnsibleException class """
    pass


class Ansible:
    """ Class for managing Ansible connections. """

    def __init__(self, deployment):
        self.output = ""
        self.debug_outputs = []
        self.deployment = deployment

    def _ansible_callback(self, event_data):
        if event_data['stdout']:
            self.output += f"\n{event_data['stdout']}"
            event_data = event_data.get("event_data",None)
            if event_data:
                resolved_action = event_data.get("resolved_action",None)
                if resolved_action == "ansible.builtin.debug" and event_data.get("res",None):
                    debug_output = event_data["res"]
                    if debug_output.get("_ansible_verbose_always",None):
                        del debug_output["_ansible_verbose_always"]
                    if debug_output.get("_ansible_no_log",None):
                        del debug_output["_ansible_no_log"]
                    if debug_output.get("changed",None):
                        del debug_output["changed"]
                    self.debug_outputs.append(debug_output)
        return True

    def build_inventory(self, machine_list=None, username=None, extra_vars=None):
        if extra_vars is None:
            extra_vars = {}
        if machine_list is None:
            machine_list = []
        inventory = {}

        deployment = self.deployment
        description = deployment.description
        parameters = deployment.description.get_parameters()

        ssh_args = description.ansible_ssh_common_args

        proxy_command = deployment.get_ssh_proxy_command()
        if proxy_command:
            ssh_args += f' -o ProxyCommand="{proxy_command}"'

        networks = {}
        for machine in description.parse_machines():
            instance = description.get_instance_number(machine)
            base_name = description.get_base_name(machine)
            if instance not in networks:
                networks[instance] = {}
            for _, interface in (description.get_guest_data())[machine]["interfaces"].items():
                if interface["network_name"] not in networks[instance]:
                    networks[instance][interface["network_name"]] = {}
                networks[instance][interface["network_name"]][base_name] = interface

        for machine in machine_list:
            base_name = description.get_base_name(machine)
            ansible_username = username or description.get_guest_username(base_name)
            hostname = deployment.get_ssh_hostname(machine)

            if not inventory.get(base_name):
                inventory[base_name] = {
                    "hosts": {},
                    "vars": {
                                "ansible_become": True,
                                "basename": base_name,
                                "instances": description.instance_number,
                                "platform": description.platform,
                                "institution": description.institution,
                                "lab_name": description.lab_name,
                                "ansible_connection" : "community.docker.docker_api" if description.platform == "docker" else "ssh", #export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES on macos
                                "docker_host": description.docker_uri,
                            } | extra_vars,
                }

            instance = description.get_instance_number(machine)
            inventory[base_name]["hosts"][machine] = {
                "ansible_host": hostname if description.platform != "docker" else machine,
                "ansible_user": ansible_username,
                "ansible_ssh_common_args": ssh_args,
                "machine_name": machine,
                "instance": instance,
                "copy": description.get_copy(machine),
                "networks": networks[instance] if instance else networks,
                "parameter": parameters[description.get_instance_number(machine)] if description.get_instance_number(machine) else {},
                "random_seed": description.random_seed,
            }

            if description.get_guest_attr(
                    base_name, "base_os", description.default_os
            ) == "windows_srv_2022":
                inventory[base_name]["hosts"][machine]["ansible_shell_type"] = "powershell"
                inventory[base_name]["hosts"][machine]["ansible_become_method"] = "runas"
                inventory[base_name]["hosts"][machine]["ansible_become_user"] = \
                    description.get_guest_username(base_name)
            else:
                # Make sure we load environment variables within sudo shell
                inventory[base_name]["hosts"][machine]["become_flags"] = "-i"
        return inventory
    
    def build_inventory_localhost(self, username=None, extra_vars=None):
        if extra_vars is None:
            extra_vars = {}
        return {
            f"{self.deployment.description.institution}-{self.deployment.description.lab_name}-localhost" : {
                "hosts": {
                    "localhost": {
                        "become_flags": "-i",
                    }
                },
                "vars": {
                    "ansible_become": True,
                    "ansible_user": username or self.deployment.description.user_install_packetbeat,
                    "basename": "localhost",
                    "instances": self.deployment.description.instance_number,
                    "platform": self.deployment.description.platform,
                    "institution": self.deployment.description.institution,
                    "lab_name": self.deployment.description.lab_name,
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
            instances (list): List of instances to run the playbook on.
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
        default_playbook = (Path(self.deployment.description.ansible_playbooks_path).
                            joinpath("after_clone.yml"))

        if not playbook:
            if default_playbook.is_file():
                playbook = default_playbook.resolve().as_posix()
            else:
                if not quiet:
                    print("No playbook to run")
                return
        else:
            playbook = Path(playbook).resolve().as_posix()
        if not inventory:
            machine_list = self.deployment.description.parse_machines(
                instances, guests, copies, only_instances, exclude
            )
            inventory = self.build_inventory(
                machine_list=machine_list,
                username=username,
                extra_vars=extra_vars
            )
        self.output = ""
        self.debug_outputs = []
        extravars = { "ansible_no_target_syslog" : not self.deployment.description.keep_ansible_logs }
        envvars = { 
            "ANSIBLE_FORKS": self.deployment.description.ansible_forks,
            "ANSIBLE_HOST_KEY_CHECKING": False,
            "ANSIBLE_PIPELINING": self.deployment.description.ansible_pipelining,
            "ANSIBLE_GATHERING": "explicit",
            "ANSIBLE_TIMEOUT": self.deployment.description.ansible_timeout,
        }
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

        playbook = tectonic_resources.files('tectonic') / 'playbooks' / 'wait_for_connection.yml'
        return self.run(
            instances=instances, guests=guests, copies=copies,
            only_instances=only_instances,
            playbook=playbook, quiet=True,
            exclude=exclude, username=username, inventory=inventory
        )
