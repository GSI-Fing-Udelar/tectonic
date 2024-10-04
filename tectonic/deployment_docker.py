
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

from tectonic.deployment import Deployment, DeploymentException
from tectonic.docker_client import Client
from tectonic.constants import OS_DATA
from tectonic.utils import create_table
from tectonic.ansible import Ansible

import importlib.resources as tectonic_resources



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
            "docker_uri": self.description.docker_uri
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
        """
        Delete guests base image.
        """
        guests = guests or self.description.guest_settings.keys()
        for guest_name in guests:
            try: 
                self.client.delete_image(self.description.get_image_name(guest_name))
            except Exception as exception:
                raise DeploymentDockerException(f"{exception}")
            
    def delete_services_images(self, services):
        """
        Delete services base image.
        """
        for service in services:
            if services[service]:
                try: 
                    self.client.delete_image(service)
                except Exception as exception:
                    raise DeploymentDockerException(f"{exception}")
            
    def create_cr_images(self, guests=None):
        super().create_cr_images(guests)

    def create_services_images(self, services):
        super().create_services_images(services) 

    def deploy_infraestructure(self, instances):
        """
        Deploy cyber range infraestructure
        """
        ansible = Ansible(self)

        if len(self.description.get_services_to_deploy()) > 0: #Deploy services
            click.echo("Deploying Cyber Range services...")
            self._deploy_services(
                tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-docker',
                self.get_deploy_services_vars(),
                instances
            )

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
        self._deploy_cr(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
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
        self._destroy_cr(
            tectonic_resources.files('tectonic') / 'terraform' / 'modules' / 'gsi-lab-docker',
            self.get_deploy_cr_vars(),
            instances
        )

        if instances is None and len(self.description.get_services_to_deploy()) > 0:
            click.echo("Destroying Cyber Range services...")
            self._destroy_services(
                tectonic_resources.files('tectonic') / 'services' / 'terraform' / 'services-docker',
                self.get_deploy_services_vars(),
                instances
            )
            if self.description.deploy_elastic and self.description.monitor_type == "traffic":
                self._destroy_packetbeat()
    
    def get_cyberrange_data(self):
        """Get information about cyber range"""
        try:
            if len(self.description.get_services_to_deploy()) > 0:
                headers = ["Name", "Value"]
                rows = []
                if self.description.deploy_elastic:
                    elastic_name = self.description.get_service_name("elastic")
                    if self.get_instance_status(elastic_name) == "RUNNING":
                        elastic_credentials = self._get_service_password("elastic")
                        #elastic_ip = self.get_ssh_hostname(elastic_name)
                        elastic_ip = "127.0.0.1"
                        rows.append(["Kibana URL", f"https://{elastic_ip}:5601"])
                        rows.append(["Kibana user (username: password)", f"elastic: {elastic_credentials['elastic']}"])
                        if self.description.deploy_caldera:
                            rows.append(["",""])
                    else:
                        return "Unable to get Elastic info right now. Please make sure de Elastic machine is running."
                if self.description.deploy_caldera:
                    caldera_name = self.description.get_service_name("caldera")
                    if self.get_instance_status(caldera_name) == "RUNNING":
                        caldera_credentials = self._get_service_password("caldera")
                        #caldera_ip = self.get_ssh_hostname(caldera_name)
                        caldera_ip = "127.0.0.1"
                        rows.append(["Caldera URL", f"https://{caldera_ip}:8443"])
                        rows.append(["Caldera user (username: password)", f"red: {caldera_credentials['red']}"])
                        rows.append(["Caldera user (username: password)", f"blue: {caldera_credentials['blue']}"])
                    else:
                        return "Unable to get Caldera info right now. Please make sure de Caldera machine is running."
                return create_table(headers,rows)
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
            for service in self.description.get_services_to_deploy():
                self.stop_instance(self.description.get_service_name(service))
                if service == "elastic" and self.description.monitor_type == "traffic":
                    #TODO
                    pass             
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
                    #TODO
                    pass
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
                    #TODO
                    pass
        machines_to_reboot = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        for machine in machines_to_reboot:
            click.echo(f"Rebooting instance {machine}...")
            self.reboot_instance(machine)

    def connect_to_instance(self, instance_name, username):
        username = username or self.description.get_guest_username(self.description.get_base_name(instance_name))
        self.client.connect(instance_name, username)

    def _get_services_network_data(self):
        """Compute the complete list of services subnetworks."""
        networks = {
            f"{self.description.institution}-{self.description.lab_name}-services" : {
                "cidr" : self.description.services_network,
                "mode": "none"
            },
        }
        if self.description.deploy_elastic or self.description.deploy_caldera :
            networks[f"{self.description.institution}-{self.description.lab_name}-internet"] = {
                "cidr" : self.description.internet_network,
                "mode" : "nat",
            }
        return networks
    
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
                            "guest_name": self.description.get_service_name("elastic"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[2]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        },
                        f'{self.description.get_service_name("elastic")}-2' : {
                            "name": f'{self.description.get_service_name("elastic")}-2',
                            "guest_name": self.description.get_service_name("elastic"),
                            "network_name": "internet",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-internet",
                            "private_ip": str(ipaddress.IPv4Network(self.description.internet_network)[2]),
                            "mask": str(ipaddress.ip_network(self.description.internet_network).prefixlen),
                        },
                    },
                    "memory": self.description.services["elastic"]["memory"],
                    "vcpu": self.description.services["elastic"]["vcpu"],
                    "disk": self.description.services["elastic"]["disk"],
                    "port": 5601,
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
                            "guest_name": self.description.get_service_name("caldera"),
                            "network_name": "services",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-services",
                            "private_ip": str(ipaddress.IPv4Network(self.description.services_network)[4]),
                            "mask": str(ipaddress.ip_network(self.description.services_network).prefixlen),
                        },
                        f'{self.description.get_service_name("caldera")}-2' : {
                            "name": f'{self.description.get_service_name("caldera")}-2',
                            "guest_name": self.description.get_service_name("caldera"),
                            "network_name": "internet",
                            "subnetwork_name": f"{self.description.institution}-{self.description.lab_name}-internet",
                            "private_ip": str(ipaddress.IPv4Network(self.description.internet_network)[4]),
                            "mask": str(ipaddress.ip_network(self.description.internet_network).prefixlen),
                        },
                    },
                    "memory": self.description.services["caldera"]["memory"],
                    "vcpu": self.description.services["caldera"]["vcpu"],
                    "disk": self.description.services["caldera"]["disk"],
                    "port": 8443,
                }
        return guest_data
    
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
                else:
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
                        raise DeploymentDockerException(e)
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
                                now = int((datetime.datetime.now(datetime.timezone.utc) - datetime.datetime(1970, 1, 1)).total_seconds() * 1000) #Milliseconds since epoch
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
                    raise DeploymentDockerException(e)
            return create_table(headers,rows)
        else:
            return "No services were deployed."
        
    def recreate(self, instances, guests, copies, recreate_services=False):
        machines = self.description.parse_machines(instances, guests, copies, False, self.description.get_services_to_deploy())
        resources_to_recreate = self.get_resources_to_recreate(instances, guests, copies)
        click.echo("Recreating machines...")
        self.terraform_recreate(tectonic_resources.files('tectonic') / 'terraform' / 'modules' / "gsi-lab-docker", resources_to_recreate)

        click.echo("Waiting for machines to boot up...")
        ansible = Ansible(self)
        ansible.wait_for_connections(instances, guests, copies, False, self.description.get_services_to_deploy())

        click.echo("Configuring student access...")
        entry_points = []
        for m in machines:
            base_name = self.description.get_base_name(m)
            if (base_name not in entry_points and (self.description.get_guest_attr(base_name, "entry_point", False) or base_name == "student_access")):
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

    def get_resources_to_recreate(self, instances, guests, copies):
        machines_to_recreate = self.description.parse_machines(instances, guests, copies, True)
        resource_to_recreate = []
        for machine in machines_to_recreate:
            resource_to_recreate.append('docker_container.machines["' f"{machine}" '"]')
        return resource_to_recreate
    
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
            resources.append('docker_container.machines["' f"{machine}" '"]')
        if self.description.configure_dns:
            resources = resources + self._get_dns_resources_name(instances)
        return resources
    
    def _get_machines_resources_name(self, instances):
        machines = self.description.parse_machines(instances, None, None, True)
        resources = []
        for machine in machines:
            resources.append('docker_container.machines["' f"{machine}" '"]')
        return resources

    def _get_subnet_resources_name(self, instances):
        resources = []
        for instance in filter(
            lambda i: i <= self.description.instance_number, instances or range(1, self.description.instance_number+1)
        ):
            for network in self.description.topology:
                resources.append(
                    'docker_network.subnets["'
                    f"{self.description.institution}-{self.description.lab_name}-{str(instance)}-{network['name']}"
                    '"]'
                )
        return resources

    def _get_dns_resources_name(self, instances):
        # TODO
        return []
    
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
            resources.append('docker_container.machines["'f"{service}"'"]')
            resources.append('docker_image.base_images["'f"{service}"'"]')
        for network in self._get_services_network_data():
            resources.append('docker_network.subnets["'f"{network}"'"]')
        return resources
