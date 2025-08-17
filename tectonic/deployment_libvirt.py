
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
import ipaddress
import datetime
import math
import time

from tectonic.deployment import Deployment, DeploymentException
from tectonic.libvirt_client import Client
from tectonic.ssh import interactive_shell
from tectonic.constants import OS_DATA
from tectonic.deployment_mixins import CyberRangeDataMixin, ImageManagementMixin
from tectonic.ansible import Ansible
from tectonic.utils import create_table

import importlib.resources as tectonic_resources


class DeploymentLibvirtException(DeploymentException):
    pass

class LibvirtDeployment(Deployment, CyberRangeDataMixin, ImageManagementMixin):

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
            "libvirt_uri": self.description.libvirt_uri,
            "libvirt_storage_pool": self.description.libvirt_storage_pool,
            "libvirt_student_access": self.description.libvirt_student_access,
            "libvirt_bridge": self.description.libvirt_bridge,
            "libvirt_external_network": self.description.libvirt_external_network,
            "libvirt_bridge_base_ip": self.description.libvirt_bridge_base_ip,
            "services_network": self.description.services_network,
            "services_network_base_ip": 9,
            }

    def connect_to_instance(self, instance_name, username):
        username = username or self.description.get_guest_username(
            self.description.get_base_name(instance_name)
        )
        hostname = self.client.get_machine_private_ip(instance_name)

        if not hostname:
            raise DeploymentLibvirtException(f"Instance {instance_name} not found.")

        interactive_shell(hostname, username)

    def delete_cr_images(self, guests=None):
        image_names = self._get_guest_image_names(guests)
        self._delete_images_safely(image_names, DeploymentLibvirtException)

    def create_cr_images(self, guests=None):
        # Libvirt packer plugin fails if images exist.
        self.delete_cr_images(guests)
        super().create_cr_images(guests)

    def get_instance_status(self, instance_name):
        """Returns a dictionary with the instance status."""
        return self.client.get_instance_status(instance_name)

    def get_cyberrange_data(self):
        """Get information about cyber range"""
        try:
            return self._build_cyberrange_data_table()
        except Exception as exception:
            raise DeploymentLibvirtException(f"{exception}")

    def start_instance(self, instance_name):
        """Starts a stopped instance."""
        return self.client.start_instance(instance_name)

    def stop_instance(self, instance_name):
        """Stops a running instance."""
        return self.client.stop_instance(instance_name)

    def reboot_instance(self, instance_name):
        """Reboots a running instance."""
        return self.client.reboot_instance(instance_name)

    def _get_machines_resources_name(self, instances):
        machines = self.description.parse_machines(instances, None, None, True)
        resources = []
        for machine in machines:
            resources.append('libvirt_domain.machines["' f"{machine}" '"]')
            resources.append('libvirt_volume.cloned_image["' f"{machine}" '"]')
            resources.append('libvirt_cloudinit_disk.commoninit["' f"{machine}" '"]')
        return resources

    def _get_subnet_resources_name(self, instances):
        resources = []
        for instance in filter(
            lambda i: i <= self.description.instance_number, instances or range(1, self.description.instance_number+1)
        ):
            for network in self.description.topology:
                resources.append(
                    'libvirt_network.subnets["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network['name']}"
                    '"]'
                )
        return resources

    def _get_dns_resources_name(self, instances):
        # TODO
        return []

    def get_cr_resources_to_target_apply(self, instances):
        resources = self._get_machines_resources_name(instances)
        resources = resources + self._get_subnet_resources_name(instances)
        if self.description.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources

    def get_cr_resources_to_target_destroy(self, instances):
        machines = self.description.parse_machines(instances, None, None, True)

        resources = []
        for machine in machines:
            resources.append('libvirt_domain.machines["' f"{machine}" '"]')
        if self.description.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources

    def get_resources_to_recreate(self, instances, guests, copies):
        machines_to_recreate = self.description.parse_machines(
            instances, guests, copies, True
        )
        resource_to_recreate = []
        for machine in machines_to_recreate:
            resource_to_recreate.append('libvirt_domain.machines["' f"{machine}" '"]')
            resource_to_recreate.append('libvirt_volume.cloned_image["' f"{machine}" '"]')
        return resource_to_recreate

    def _deploy_packetbeat(self):
        try:
            elastic_name = self.description.get_service_name("elastic")
            if self.get_instance_status(elastic_name) == "RUNNING":
                elastic_ip = self.get_ssh_hostname(elastic_name)
                playbook = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'get_info.yml'
                result = self._get_service_info("elastic",playbook,{"action":"get_token_by_policy_name","policy_name":self.description.packetbeat_policy_name})
                agent_token = result[0]["token"]
                ansible = Ansible(deployment=self)
                localhost_name = f"{self.description.institution}-{self.description.lab_name}-localhost"
                inventory = ansible.build_inventory(
                    machine_list=[localhost_name],
                    username=self.description.user_install_packetbeat,
                    extra_vars = {
                        "action": "install",
                        "elastic_url": f"https://{elastic_ip}:8220",
                        "token": agent_token,
                        "elastic_agent_version": self.description.elastic_stack_version,
                        "institution": self.description.institution,
                        "lab_name": self.description.lab_name,
                        "proxy": self.description.proxy,
                    },
                )
                inventory["localhost"]["hosts"]["localhost"] = inventory["localhost"]["hosts"][localhost_name]
                inventory["localhost"]["hosts"]["localhost"]["ansible_host"] = "localhost"
                del inventory["localhost"]["hosts"][localhost_name]
                ansible.wait_for_connections(inventory=inventory)
                ansible.run(inventory = inventory,
                            playbook = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml',
                            quiet = True)
            else:
                click.echo(f"Unable to connect to Elastic. Check if machine is running.")
        except Exception as e:
            raise DeploymentLibvirtException(e)

    def generate_backend_config(self, terraform_dir):
        return super().generate_backend_config(terraform_dir)

    def _destroy_packetbeat(self, instances=None):
        ansible = Ansible(deployment=self)
        localhost_name = f"{self.description.institution}-{self.description.lab_name}-localhost"
        inventory = ansible.build_inventory(
            machine_list=[localhost_name],
            username=self.description.user_install_packetbeat,
            extra_vars={
                "action": "delete",
                "institution": self.description.institution,
                "lab_name": self.description.lab_name,
            }
        )
        inventory["localhost"]["hosts"]["localhost"] = inventory["localhost"]["hosts"][localhost_name] 
        inventory["localhost"]["hosts"]["localhost"]["ansible_host"] = "localhost"
        del inventory["localhost"]["hosts"][localhost_name]
        ansible.run(inventory = inventory,
                    playbook = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml',
                    quiet=True)

    def _manage_packetbeat(self, action):
        """
        Get status of Packetbeat service.

        Returns:
          str: status of packetbeat service.
        """
        try:
            ansible = Ansible(deployment=self)
            localhost_name = f"{self.description.institution}-{self.description.lab_name}-localhost"
            inventory = ansible.build_inventory(
                machine_list=[localhost_name],
                username=self.description.user_install_packetbeat,
                extra_vars={
                    "action": action,
                    "institution": self.description.institution,
                    "lab_name": self.description.lab_name,
                }
            )
            inventory["localhost"]["hosts"]["localhost"] = inventory["localhost"]["hosts"][localhost_name]
            inventory["localhost"]["hosts"]["localhost"]["ansible_host"] = "localhost"
            del inventory["localhost"]["hosts"][localhost_name]
            ansible.run(inventory = inventory,
                        playbook = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'agent_manage.yml',
                        quiet = True)
            if action == "status":
                packetbeat_status = ansible.debug_outputs[0]["agent_status"]
                if packetbeat_status == "stopped":
                    packetbeat_status = "shutoff"
                return packetbeat_status.upper()
            else:
                return None
        except Exception as e:
            raise DeploymentLibvirtException(f"Unable to apply action {action} for Packetbeat. Error {e}")

    def list_instances(self, instances, guests, copies):
        machines_to_list = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        headers = ["Name", "Status"]
        rows = []
        for machine in machines_to_list:
            machine_status = self.get_instance_status(machine)
            rows.append([machine,machine_status])
        return create_table(headers,rows)
    
    def shutdown(self, instances, guests, copies, stop_services):
        if stop_services:
            click.echo(f"Shutting down services...")
            for service in self.description.get_services_to_deploy():
                self.stop_instance(self.description.get_service_name(service))
                if service == "elastic" and self.description.monitor_type == "traffic":
                    self._manage_packetbeat("stopped")                
        machines_to_shutdown = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy()) 
        for machine in machines_to_shutdown:
            click.echo(f"Shutting down instance {machine}...")
            self.stop_instance(machine)
            
    def start(self, instances, guests, copies, start_services):
        if start_services:
            click.echo(f"Booting up services...")
            for service in self.description.get_services_to_deploy():
                self.start_instance(self.description.get_service_name(service))
                if service == "elastic" and self.description.monitor_type == "traffic":
                    self._manage_packetbeat("started")
        machines_to_start = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())  
        for machine in machines_to_start:
            click.echo(f"Booting up instance {machine}...")
            self.start_instance(machine)

    def reboot(self, instances, guests, copies, reboot_services):
        if reboot_services:
            click.echo(f"Rebooting services...")
            for service in self.description.get_services_to_deploy():
                self.reboot_instance(self.description.get_service_name(service))
                if service == "elastic" and self.description.monitor_type == "traffic":
                    self._manage_packetbeat("restarted")
        machines_to_reboot = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        for machine in machines_to_reboot:
            click.echo(f"Rebooting instance {machine}...")
            self.reboot_instance(machine)

    def recreate(self, instances, guests, copies, recreate_services=False):
        machines = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        resources_to_recreate = self.get_resources_to_recreate(instances, guests, copies)
        click.echo("Recreating machines...")
        self.terraform_recreate(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / "gsi-lab-libvirt", resources_to_recreate)

        click.echo("Waiting for machines to boot up...")
        ansible = Ansible(self)
        ansible.wait_for_connections(instances, guests, copies, False, self.description.get_services_to_deploy())

        click.echo("Configuring student access...")
        entry_points = []
        for m in machines:
            base_name = self.description.get_base_name(m)
            if (base_name not in entry_points and
                (self.description.get_guest_attr(base_name, "entry_point", False) or
                base_name == "student_access")):
                entry_points.append(base_name)
        self._student_access(instances, entry_points)

        click.echo("Running after-clone configuration...")
        ansible.run(instances, guests, copies, quiet=True, only_instances=False)

        if self.description.deploy_elastic and self.description.monitor_type == "endpoint":
            click.echo("Configuring elastic agents...")
            self._elastic_install_endpoint(instances)

        if self.description.deploy_caldera:
            click.echo("Configuring caldera agents...")
            self._caldera_install_agent(instances)

    def deploy_infraestructure(self, instances):
        """
        Deploy cyber range infraestructure
        """
        ansible = Ansible(self)

        if len(self.description.get_services_to_deploy()) > 0: #Deploy services
            click.echo("Deploying Cyber Range services...")
            self._deploy_services(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-libvirt',
                                  self.get_deploy_services_vars(),
                                  instances)

            click.echo("Waiting for services to boot up...")
            services_to_deploy = []
            for service in self.description.get_services_to_deploy():
                services_to_deploy.append(self.description.get_service_name(service))
            extra_vars = {
                "elastic" : {
                    "monitor_type": self.description.monitor_type,
                    "deploy_policy": self.description.elastic_deploy_default_policy,
                    "policy_name": self.description.packetbeat_policy_name if self.description.monitor_type == "traffic" else self.description.endpoint_policy_name,
                    "http_proxy" : self.description.proxy,
                    "description_path": self.description.description_dir,
                    "ip": str(ipaddress.IPv4Network(self.description.services_network)[2]),
                    "elasticsearch_memory": math.floor(self.description.services["elastic"]["memory"] / 1000 / 2)  if self.description.deploy_elastic else None,
                },
                "caldera":{
                    "ip": str(ipaddress.IPv4Network(self.description.services_network)[4]),
                    "description_path": self.description.description_dir,
                },
            }
            inventory = ansible.build_inventory(machine_list=services_to_deploy, extra_vars=extra_vars)
            ansible.wait_for_connections(inventory=inventory)

            click.echo("Configuring services...")
            ansible.run(
                inventory=inventory,
                playbook=self.ansible_services_path,
                quiet=True,
            )
            if self.description.deploy_elastic and self.description.monitor_type == "traffic":
                self._deploy_packetbeat()

        click.echo("Deploying Cyber Range instances...")
        self._deploy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-libvirt',
                        self.get_deploy_cr_vars(),
                        instances)

        click.echo("Waiting for machines to boot up...")
        ansible.wait_for_connections(instances=instances)

        click.echo("Configuring student access...")
        self.student_access(instances)

        click.echo("Running after-clone configuration...")
        ansible.run(instances, quiet=True)

        if self.description.deploy_elastic and self.description.monitor_type == "endpoint":
            click.echo("Configuring elastic agents...")
            self._elastic_install_endpoint(instances)
        
        if self.description.deploy_caldera:
            click.echo("Configuring caldera agents...")
            self._caldera_install_agent(instances)

    def destroy_infraestructure(self, instances):
        """
        Destroy cyber range infraestructure
        """
        click.echo("Destroying Cyber Range instances...")
        self._destroy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-libvirt',
                         self.get_deploy_cr_vars(),
                         instances)
        if instances is not None:
            #Destroy disks
            machines = self.description.parse_machines(instances, None, None, True)
            for machine in machines:
                self.client.delete_image(
                    self.description.libvirt_storage_pool,
                    machine,
                )
                self.client.delete_image(
                    self.description.libvirt_storage_pool,
                    f"guestinit-{machine}.iso",
                )
        else:
            if len(self.description.get_services_to_deploy()) > 0:
                click.echo("Destroying Cyber Range services...")
                self._destroy_services(tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-libvirt',
                                       self.get_deploy_services_vars(),
                                       instances)
                if self.description.deploy_elastic and self.description.monitor_type == "traffic":
                    self._destroy_packetbeat()
        
    def create_services_images(self, services):
        self.delete_services_images(services)
        super().create_services_images(services) 

    def delete_services_images(self, services):
        """
        Delete services base image.
        """
        for service in services:
            if services[service]:
                if self.client.is_image_in_use(service):
                    raise DeploymentLibvirtException(f"Unable to delete image {service} because it is being used.")
                self.client.delete_image(self.description.libvirt_storage_pool, service)
    
    def get_deploy_services_vars(self):
        """Build the terraform variable dictionary for deployment of the CyberRange services."""
        return {
            "institution": self.description.institution,
            "lab_name": self.description.lab_name,
            "ssh_public_key_file": self.description.ssh_public_key_file,
            "authorized_keys": self.description.authorized_keys,
            "subnets_json": json.dumps(self._get_services_network_data()),
            "guest_data_json": json.dumps(self._get_services_guest_data()),
            "os_data_json": json.dumps(OS_DATA),
            "configure_dns": self.description.configure_dns,
            "libvirt_uri": self.description.libvirt_uri,
            "libvirt_storage_pool": self.description.libvirt_storage_pool,
        }
    
    def _get_services_network_data(self):
        """Compute the complete list of services subnetworks."""
        networks = {
            f"{self.description.institution}-{self.description.lab_name}-services" : {
                "cidr" : self.description.services_network,
                "mode": "none"
            },
        }
        if self.description.deploy_elastic:
            networks[f"{self.description.institution}-{self.description.lab_name}-internet"] = {
                "cidr" : self.description.internet_network,
                "mode" : "nat",
            }
        return networks
    
    def get_services_status(self):
        if len(self.description.get_services_to_deploy()) > 0:
            headers = ["Name", "Status"]
            rows = []
            if self.description.deploy_elastic:
                elastic_name = self.description.get_service_name("elastic")
                elastic_status = self.get_instance_status(elastic_name)
                rows = [[elastic_name, elastic_status]]
                if self.description.monitor_type == "traffic":
                    rows.append([self.description.get_service_name("packetbeat"), self._manage_packetbeat("status")])
                if self.description.monitor_type == "endpoint":
                    try:
                        if elastic_status == "RUNNING":
                            playbook = tectonic_resources.files('tectonic') / 'services' / 'elastic' / 'get_info.yml'
                            result = self._get_service_info("elastic",playbook,{"action":"agents_status"})
                            agents_status = result[0]['agents_status']
                            for key in agents_status:
                                rows.append([f"elastic-agents-{key}", agents_status[key]])
                        else:
                            click.echo(f"Unable to connect to Elastic. Check if machine is running.")
                    except Exception as e:
                        raise DeploymentLibvirtException(e)
                if self.description.deploy_caldera:
                    rows.append(["",""])
            if self.description.deploy_caldera:
                caldera_name = self.description.get_service_name("caldera")
                rows.append([caldera_name, self.get_instance_status(caldera_name)])
                try:
                    if self.get_instance_status(caldera_name) == "RUNNING":
                        playbook = tectonic_resources.files('tectonic') / 'services' / 'caldera' / 'get_info.yml'
                        result = self._get_service_info("caldera",playbook,{"action":"agents_status"})
                        response = result[0]['agents_status']
                        agents_status = {"alive": 0, "dead": 0, "pending_kill":0}
                        if len(response) > 0:
                            for agent in response: #TODO: see what the response is like when there are a large number of agents. pagination?
                                #Caldera uses this logic to define the state of the agent
                                now = int(time.time() * 1000) #Milliseconds since epoch
                                agent_last_seen = int((datetime.datetime.strptime(agent["last_seen"],"%Y-%m-%dT%H:%M:%SZ") - datetime.datetime(1970, 1, 1)).total_seconds() * 1000) #Milliseconds since epoch
                                difference = now - agent_last_seen
                                if (difference <= 60000 and agent["sleep_min"] == 3 and agent["sleep_max"] == 3 and agent["watchdog"] == 1):
                                    agents_status["pending_kill"] = agents_status["pending_kill"] + 1
                                elif (difference <= 60000 or difference <= (agent["sleep_max"] * 1000)):
                                    agents_status["alive"] = agents_status["alive"] + 1
                                else:
                                    agents_status["dead"] = agents_status["dead"] + 1
                        for key in agents_status:
                            rows.append([f"caldera-agents-{key}", agents_status[key]])
                    else:
                        click.echo(f"Unable to connect to Caldera. Check if machine is running.")
                except Exception as e:
                    raise DeploymentLibvirtException(e)
            return create_table(headers,rows)
        else:
            return "No services were deployed."
        
    def _get_services_guest_data(self):
        """Compute the services guest data as expected by the deployment terraform module."""
        guest_data = {}
        if self.description.deploy_elastic:
            guest_data[self.description.get_service_name("elastic")] = {
                    "guest_name": self.description.get_service_name("elastic"),
                    "base_name": "elastic",
                    "hostname": "elastic",
                    "base_os": self.description.get_service_base_os("elastic"),
                    "interfaces": {
                        f'{self.description.get_service_name("elastic")}-1' : {
                            "name": f'{self.description.get_service_name("elastic")}-1',
                            "index": 3,
                            "guest_name": self.description.get_service_name("elastic"),
                            "network_name": "internet",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-internet",
                            "private_ip": str(ipaddress.IPv4Network(self.description.internet_network)[2]),
                            "mask": str(ipaddress.ip_network(self.description.internet_network).prefixlen),
                        },
                        f'{self.description.get_service_name("elastic")}-2' : {
                            "name": f'{self.description.get_service_name("elastic")}-2',
                            "index": 4,
                            "guest_name": self.description.get_service_name("elastic"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[2]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        }
                    },
                    "memory": self.description.services["elastic"]["memory"],
                    "vcpu": self.description.services["elastic"]["vcpu"],
                    "disk": self.description.services["elastic"]["disk"],
                }
        if self.description.deploy_caldera:
            guest_data[self.description.get_service_name("caldera")] = {
                    "guest_name": self.description.get_service_name("caldera"),
                    "base_name": "caldera",
                    "hostname": "caldera",
                    "base_os": self.description.get_service_base_os("caldera"),
                    "interfaces": {
                        f'{self.description.get_service_name("caldera")}-1' : {
                            "name": f'{self.description.get_service_name("caldera")}-1',
                            "index": 3,
                            "guest_name": self.description.get_service_name("caldera"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[4]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        }
                    },
                    "memory": self.description.services["caldera"]["memory"],
                    "vcpu": self.description.services["caldera"]["vcpu"],
                    "disk": self.description.services["caldera"]["disk"],
                }
        return guest_data
    
    def get_services_resources_to_target_destroy(self, instances):
        """
        Returns the name of the libvirt resource of the services-libvirt module to target destroy base on the instances number

        Parameters:
          instances (list(int)): instances to use

        Returns:
          list(str): resources name to target destroy
        """
        return []
        
    def get_services_resources_to_target_apply(self, instances):
        """
        Returns the name of the libvirt resource of the services-libvirt module to target apply base on the instances number

        Parameters:
          instances (list(int)): instances to use

        Returns:
          list(str): resources name to target apply
        """
        resources = []
        for service in self._get_services_guest_data():
            resources.append('libvirt_volume.cloned_image["'f"{service}"'"]')
            resources.append('libvirt_cloudinit_disk.commoninit["'f"{service}"'"]')
            resources.append('libvirt_domain.machines["'f"{service}"'"]')
        for network in self._get_services_network_data():
            resources.append('libvirt_network.subnets["'f"{network}"'"]')
        return resources
