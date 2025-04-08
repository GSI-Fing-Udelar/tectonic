
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
import math
import ipaddress
import random
from passlib.hash import sha512_crypt
import string
import os

import tectonic.utils
from tectonic.config import TectonicConfig
from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS
from tectonic.description import Description
from tectonic.ansible import Ansible
from tectonic.packer import Packer
from tectonic.terraform import Terraform
from tectonic.ssh import ssh_version
from tectonic.constants import OS_DATA
import importlib.resources as tectonic_resources
from tectonic.client import Client
from tectonic.client_aws import ClientAWS
from tectonic.client_libvirt import ClientLibvirt
from tectonic.client_docker import ClientDocker
from tectonic.instance_manager import InstanceManager
from tectonic.instance_manager_aws import InstanceManagerAWS
from tectonic.instance_manager_libvirt import InstanceManagerLibvirt
from tectonic.instance_manager_docker import InstanceManagerDocker
from tectonic.service_manager import ServiceManager
from tectonic.service_manager_aws import ServiceManagerAWS
from tectonic.service_manager_libvirt import ServiceManagerLibvirt
from tectonic.service_manager_docker import ServiceManagerDocker

class CoreException(Exception):
    pass

class Core:
    """
    Core class.

    Description: orchestrate Tectonic main functionalities using InstanceManagement and ServiceManagement.
    """
    TECHNOLOGY = "docker" # TODO: obtener esto

    INSTANCES_PACKER_MODULE = tectonic_resources.files('tectonic') / 'image_generation' / 'create_image.pkr.hcl'
    SERVICES_PACKER_MODULE = tectonic_resources.files('tectonic') / 'services' / 'image_generation' / 'create_image.pkr.hcl'
    ANSIBLE_SERVICE_PLAYBOOK = tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'
    ANSIBLE_TRAINEES_PLAYBOOK = tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'

    def __init__(self, config_path, lab_edition_path):
        """
        Initialize the core object.
        """
        self.config = TectonicConfig.load(config_path)
        if self.config.platform == "aws":
            instance_type = InstanceTypeAWS()
        else:
            instance_type = InstanceType()
        self.description = Description(self.config, instance_type, lab_edition_path)
        self.ansible = Ansible(None)
        terraform_backend_info = {
            "gitlab_url": self.config.gitlab_backend_url,
            "gitlab_username": self.config.gitlab_backend_username,
            "gitlab_access_token": self.config.gitlab_backend_access_token
        }
        self.terraform = Terraform(self.description.institution, self.description.lab_name, terraform_backend_info)
        self.instances_terraform_module = tectonic_resources.files('tectonic') / 'terraform' / 'modules' / f"gsi-lab-{self.config.platform}"
        self.services_terraform_module = tectonic_resources.files('tectonic') / 'services' / 'terraform' / f"services-{self.config.platform}"

        if self.TECHNOLOGY == "aws": #TODO: fix initialization
            self.client = ClientAWS(self.config, self.description)
            self.instance_manager = InstanceManagerAWS(self.config, self.description, self.client)
            self.service_manager = ServiceManagerAWS(self.config, self.description, self.client)
        elif self.TECHNOLOGY == "libvirt":
            self.client = ClientLibvirt(self.config, self.description)
            self.instance_manager = InstanceManagerLibvirt(self.config, self.description, self.client)
            self.service_manager = ServiceManagerLibvirt(self.config, self.description, self.client)
        elif self.TECHNOLOGY == "docker":
            self.client = ClientDocker(self.config, self.description)
            self.instance_manager = InstanceManagerDocker(self.config, self.description, self.client)
            self.service_manager = ServiceManagerDocker(self.config, self.description, self.client)
        else:
            raise CoreException("Unknown technology.")
        self.packer = Packer(self.config, self.description, self.client)
        
    def __del__(self):
        del self.service_manager
        del self.instance_manager
        del self.client
        del self.description
        del self.config

    def create_images(self, create_guests, create_services):
        """
        Create base images.

        Parameters:
            create_guests (bool): whether to create images for guests
            create_services (bool): whether to create images for services
        """
        # Create instances images
        if create_guests:
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
                "machines_json": json.dumps(self.description.base_guests),
                "os_data_json": json.dumps(OS_DATA),
                "platform": self.config.platform,
                "remove_ansible_logs": str(not self.config.ansible.keep_logs),
                "elastic_version": self.config.elastic.elastic_stack_version
            }
            if self.config.proxy:
                args["proxy"] = self.config.proxy
            self._destroy_image(self.description.base_guests)
            self.instance_manager.create_image(self.packer, self.INSTANCES_PACKER_MODULE, args)

        # Create services images
        if create_services:
            args = {
                "ansible_scp_extra_args": "'-O'" if ssh_version() >= 9 and self.description.platform != "docker" else "",
                "ansible_ssh_common_args": self.config.ansible.ssh_common_args,
                "aws_region": self.config.aws.region,
                "libvirt_storage_pool": self.config.libvirt.storage_pool,
                "libvirt_uri": self.config.libvirt.uri,
                "machines_json": json.dumps(self.description.services),
                "os_data_json": json.dumps(OS_DATA),
                "platform": self.config.platform,
                "remove_ansible_logs": str(not self.config.ansible.keep_logs),
                #TODO: pass variables as a json as part of each host
                "elastic_version": self.config.elastic.elastic_stack_version, 
                "elastic_latest_version": str(self.config.elastic.elastic_stack_version == "latest"), # TODO: Check this
                "elasticsearch_memory": math.floor(self.description.elastic.memory / 1000 / 2)  if self.description.elastic.enable else None,
                "caldera_version": self.config.caldera.version,
                "packetbeat_vlan_id": self.config.aws.packetbeat_vlan_id,
            }
            if self.config.proxy:
                args["proxy"] = self.config.proxy
            # TODO: lo de arriba de generar el args lo pasaría al description? así no hay que poner if con la tecnología acá.
            self._destroy_image(self.description.services)
            self.packer.create_image(self.SERVICES_PACKER_MODULE, args)


    def _destroy_image(self, guests):
        """
        Destroy base images.

        Parameters:
            names (list(str)): names of the machines for which to destroy images. 
        """
        for guest in guests:
            if self.client.is_image_in_use(guest.image_name):
                raise CoreException(f"Unable to delete image {guest.image_name} because it is being used.")
        for guest in guests:
            self.client.delete_image(guest.image_name)

    
    def deploy(self, instances, create_instances_images, create_services_images):
        """
        Create scenario.

        Parameters:
            instances (list(int)): numbers of the instances to deploy.
            create_instances_images: whether to create instances images.
            create_services_images: whether to create services images.
        """
        self.create_images(create_instances_images, create_services_images)

        # Deploy instances
        instances_resources_to_create = None
        services_resources_to_create = None
        if instances is not None:
            instances_resources_to_create = self.instance_manager.get_resources_to_target_apply(instances)
            services_resources_to_create = self.service_manager.get_resources_to_target_apply(instances)

        # Deploy instances
        self.terraform.apply(self.instances_terraform_module, self.instance_manager.get_terraform_variables(), instances_resources_to_create)
            
        # Deploy services
        self.terraform.apply(self.services_terraform_module, self.service_manager.get_terraform_variables(), services_resources_to_create)
        
        # Wait for services to bootup
        services_to_deploy = [service.name for service in self.description.services]
        extra_vars = {
            "elastic" : {
                "monitor_type": self.description.elastic.monitor_type,
                "deploy_policy": self.description.elastic.deploy_default_policy,
                "policy_name": self.config.elastic.packetbeat_policy_name if self.description.elastic.monitor_type == "traffic" else self.config.elastic.endpoint_policy_name,
                "http_proxy" : self.config.proxy,
                "description_path": self.description.scenario_dir,
                "ip": str(ipaddress.IPv4Network(self.config.services_network_cidr_block)[2]),
                "elasticsearch_memory": math.floor(self.description.elastic.memory / 1000 / 2)  if self.description.elastic.enable else None,
                "dns": self.config.docker.dns,
            },
            "caldera":{
                "ip": str(ipaddress.IPv4Network(self.config.services_network_cidr_block)[4]),
                "description_path": self.description.scenario_dir,
            },
        }
        #TODO: mejorar la creación de este inventario para servicios pensando en que se agreguen otros servicios.
        inventory = self.ansible.build_inventory(machine_list=services_to_deploy, extra_vars=extra_vars)
        self.ansible.wait_for_connections(inventory=inventory)

        # Configure services
        self.ansible.run(inventory=inventory, playbook=self.ANSIBLE_SERVICE_PLAYBOOK, quiet=True)

        # Wait for instances to bootup
        self.ansible.wait_for_connections(instances=instances)

        # Run instances post clone configuration
        self.ansible.run(instances, quiet=True)

        # Configure student access on instances
        self.instance_manager.configure_students_access(instances)  

        # Configure Elastic monitoring
        if self.description.elastic.enable:
            if self.description.elastic.monitor_type == "traffic":
                self.service_manager.deploy_packetbeat(self.ansible)
            elif self.description.elastic.monitor_type == "endpoint":
                self.service_manager.install_elastic_agent(self.ansible, instances)

        # Configure Caldera agents
        if self.description.caldera.enable:
            self.service_manager.install_caldera_agent(self.ansible, instances)

    def destroy(self, instances, destroy_instances_images, destroy_services_images):
        """
        Destroy scenario.

        Parameters:
            instances (list(int)): numbers of the instances to deploy.
            destroy_instances_images: whether to destroy instances images.
            destroy_services_images: whether to destroy services images.
        """
        services_resources_to_destroy = None
        instances_resources_to_destroy = None
        if instances is not None:
            services_resources_to_destroy = self.service_manager.get_resources_to_target_destroy(instances)
            instances_resources_to_destroy = self.instance_manager.get_resources_to_target_destroy(instances)

        # Destroy services
        self.terraform.destroy(self.services_terraform_module, self.service_manager.get_terraform_variables(), services_resources_to_destroy)

        # Destrot instances
        self.terraform.destroy(self.instances_terraform_module, self.instance_manager.get_terraform_variables(), instances_resources_to_destroy)

        if instances is None:
            # Destroy Packetbeat
            if self.description.elastic.enable and self.description.elastic.monitor_type == "traffic":
                self.instance_manager.destroy_packetbeat(self.ansible)
                
            # Destroy images
            if destroy_instances_images:
                self._destroy_image(self.description.base_guests)
            if destroy_services_images:
                self._destroy_image(self.description.services)
    
    def recreate(self, instances, guests, copies):
        """
        Recreate scenario machines.

        Parameters:
            instances (list(int)): number of the instances to start.
            guests (list(str)): name of the guests to start.
            copies (list(int)): number of the copies to start.
        """
        # Recreate instances
        resources_to_recreate = self.instance_manager.get_resources_to_recreate(instances, guests, copies)
        self.terraform.apply(self.instances_terraform_module, self.instance_manager.get_terraform_variables(), resources_to_recreate)

        # Wait for instances to bootup
        self.ansible.wait_for_connections(instances, guests, copies, False, self.description.services)
        
        # Run instances post clone configuration
        self.ansible.run(instances, guests, copies, quiet=True, only_instances=False)

        # Configure student access on instances
        self.instance_manager.configure_students_access(instances)

        # Configure Elastic monitoring
        if self.description.elastic.enable and self.description.elastic.monitor_type == "endpoint":
            self.service_manager.install_elastic_agent(self.ansible, instances)

        # Configure Caldera agents
        if self.description.caldera.enable:
            self.service_manager.install_caldera_agent(self.ansible, instances)

    def start(self, instances, guests, copies, start_services):
        """
        Start scenario machines.

        Parameters:
            instances (list(int)): number of the instances to start.
            guests (list(str)): name of the guests to start.
            copies (list(int)): number of the copies to start.
            start_services (bool): whether the services should be started.
        """
        #Start instances
        machines_to_start = self.description.parse_machines(instances, guests, copies, False,
                                                            [service.base_name for service in self.description.services])
        for machine in machines_to_start:
            self.client.start_machine(machine)

        #Start services
        if start_services:
            for service in self.description.services:
                self.client.start_machine(service.name)
            if self.description.elastic.enable and self.description.elastic.monitor_type == "traffic":
                self.service_manager.manage_packetbeat(self.ansible, "started") # TODO: ver que pasa en AWS con start, stop, restart del servicio de packetbeat 
                                                                                # ya que la máquina donde se instala también sufre esta acción. En libvirt y docker esto no pasa. 

    def stop(self, instances, guests, copies, stop_services):
        """
        Stop scenario machines.

        Parameters:
            instances (list(int)): number of the instances to stop.
            guests (list(str)): name of the guests to stop.
            copies (list(int)): number of the copies to stop.
            stop_services (bool): whether the services should be stopped.
        """
        #Stop instances
        machines_to_stop = self.description.parse_machines(instances, guests, copies, False,
                                                           [service.base_name for service in self.description.services])
        for machine in machines_to_stop:
            self.client.stop_machine(machine)

        #Stop services
        if stop_services:
            for service in self.description.services:
                self.client.stop_machine(service.name)
            if self.description.elastic.enable and self.description.elastic.monitor_type == "traffic":
                self.service_manager.manage_packetbeat(self.ansible, "stopped")

    def restart(self, instances, guests, copies, restart_services):
        """
        Restart scenario machines.
        
        Parameters:
            instances (list(int)): number of the instances to restart.
            guests (list(str)): name of the guests to restart.
            copies (list(int)): number of the copies to restart.
            restart_services (bool): whether the services should be restarted.
        """
        #Stop instances
        machines_to_restart = self.description.parse_machines(instances, guests, copies, False,
                                                              [service.base_name for service in self.description.services])
        for machine in machines_to_restart:
            self.client.restart_machine(machine)

        #Stop services
        if restart_services:
            for service in self.description.services:
                self.client.restart_machine(service.name)
            if self.description.elastic.enable and self.description.elastic.monitor_type == "traffic":
                self.service_manager.manage_packetbeat(self.ansible, "restarted")

        raise NotImplementedError

    def info(self):
        """
        Get scenario connection information.

        Return:
            dict: scenario information.
        """
        instances_info = {}
        if self.description.student_access_required:
            student_access_ip = self.client.get_machine_public_ip(f"{self.description.institution}-{self.description.lab_name}-student_access")
            if student_access_ip is not None:
                instances_info["Student Access IP"] = student_access_ip
        if self.config.aws.teacher_access == "host":
            teacher_access_ip = self.client.get_machine_public_ip(f"{self.description.institution}-{self.description.lab_name}-teacher_access")
            if teacher_access_ip is not None:
                instances_info["Teacher Access IP"] = teacher_access_ip

        service_info = {}
        for service in self.description.services:
            credentials = self.service_manager.get_service_credentials(service, self.ansible)
            ip = self.client.get_machine_private_ip(service.name) # En docker tiene que ser 127.0.0.1 ver como arreglar.
            service_info[service.name] = {
                "ip": ip,
                "credentials": credentials,
            }

        return {
            "instances_info": instances_info,
            "services_info": service_info,
            "student_access_password": self.get_students_password(),
        }

    def list(self, instances, guests, copies):
        """
        List scenario status.

        Parameters:
            instances (list(int)): number of the instances to list.
            guests (list(str)): name of the guests to list.
            copies (list(int)): number of the copies to list.

        Return:
            dict: status of instances.
        """
        instances_status = {}
        machines_to_list = self.description.parse_machines(instances, guests, copies, False, 
                                                           [service.base_name for service in self.description.services])
        for machine in machines_to_list:
            instances_status[machine] = self.client.get_machine_status(machine)

        services_status = {}
        for service in self.description.services:
            services_status[service.name] = self.client.get_machine_status(service.name)
        if self.description.elastic.monitor_type == "traffic":
            packetbeat_status = self.service_manager.manage_packetbeat(self.ansible,"status")
            if packetbeat_status is not None:
                services_status[f"{self.description.institution}-{self.description.lab_name}-packetbeat"] = packetbeat_status
        return {
            "instances_status" : instances_status,
            "services_status" : services_status
        }

    def get_parameters(self, instances):
        """
        Get parameters used for the individualization of the instances.

        Parameters:
            instances (list(int)): number of instances.

        Return:
            dict: parameters.
        """
        self.description.parse_machines(instances)
        return self.description.get_parameters(instances)
    
    def run_automation(self, instances, guests, copies, username, playbook):
        """
        Run an automation (Ansible playbook) on the scenario machines.

        Parameters:
            instances (int): number of the instances to run automation.
            guest (str): name of the guest to run automation.
            copy (int): number of the copy to run automation.
            username (str): username to use.
            playbook (str): path to Ansible playbook.
        """
        self.description.parse_machines(instances, guests, copies, False)
        self.ansible.run(instances, guests, copies, False, username, playbook)
    
    def console(self, instance, guest, copy, username=None):
        """
        Connect to a specific scenario machine.

        Parameters:
            instance (int): number of the instance to connect.
            guest (str): name of the guest to connect.
            copy (int): number of the copy to connect.
            username (str): username to use. Default: None.
        """
        machine_to_connect = self.description.parse_machines(instance, guest, copy, False)
        if len(machine_to_connect) != 1:
            raise CoreException("You must specify only one machine to connect.")
        machine_name = machine_to_connect[0]
        username = username or self.description.scenario_guests[machine_name].admin_username
        self.instance_manager.connect(machine_name, username)

    def configure_students_access(self, instances):
        """
        Configure students users to access instances.
        Users are created on all entry points (and the student access host, if appropriate). 
        Credentials can be public SSH keys and/or autogenerated passwords.
        """
        only_instances = True
        entry_points = [guest for _, guest in self.description.scenario_guests.items() if guest.entry_point]
        if self.config.platform == "aws" and entry_points:
            entry_points.append("student_access")
            only_instances = False
        users = self._generate_students_credentials()
        self.ansible.run(
            instances=instances,
            guests=entry_points,
            copies=None,
            playbook=self.ANSIBLE_TRAINEES_PLAYBOOK,
            only_instances=only_instances,
            extra_vars={"users": users, "prefix": self.description.student_prefix,
                        "ssh_password_login": self.description.create_students_passwords},
            quiet=True,
        )

    def _generate_students_credentials(self):
        """
        Generates student credentials to access the cyber range.
        
        Return:
            dict: password and hash or public key for each user.
        """
        credentials = {}
        random.seed(self.description.random_seed)
        for i in range(1, self.description.instance_number+1):
            username = f"{self.description.student_prefix}{i:02d}"
            credentials[username] = {}
            if self.description.create_students_passwords:
                characters = string.ascii_letters + string.digits
                password = "".join(random.choice(characters) for _ in range(12))
                salt = "".join(random.choice(characters) for _ in range(16))
                credentials[username]["password"] = password
                credentials[username]["password_hash"] = sha512_crypt.using(salt=salt).hash(password)
            if self.description.student_pubkey_dir:
                credentials[username]["authorized_keys"] = tectonic.utils.read_all_files_in_dir(self.description.student_pubkey_dir)
        return credentials

    def get_students_password(self):
        """
        Get the generated students password.

        Return:
            dic: the password for each user.
        """
        passwords = {}
        if self.description.create_students_passwords:
            users = self._generate_students_credentials()
            for username, user in users.items():
                passwords[username] = user['password']
        return passwords
    

#TODO: manejo de excepciones
#Logging con patron observer?
