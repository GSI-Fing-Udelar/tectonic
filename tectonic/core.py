
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

import os
import json

from tectonic.ansible import Ansible
from tectonic.constants import OS_DATA
import importlib.resources as tectonic_resources
from tectonic.client_aws import ClientAWS
from tectonic.client_libvirt import ClientLibvirt
from tectonic.client_docker import ClientDocker
from tectonic.packer_aws import PackerAWS
from tectonic.packer_libvirt import PackerLibvirt
from tectonic.packer_docker import PackerDocker
from tectonic.terraform_aws import TerraformAWS
from tectonic.terraform_libvirt import TerraformLibvirt
from tectonic.terraform_docker import TerraformDocker
from tectonic.terraform_service_aws import TerraformServiceAWS
from tectonic.terraform_service_docker import TerraformServiceDocker
from tectonic.terraform_service_libvirt import TerraformServiceLibvirt

class CoreException(Exception):
    pass

class Core:
    """
    Core class.

    Description: orchestrate Tectonic main functionalities using InstanceManagement and ServiceManagement.
    """
    ANSIBLE_SERVICE_PLAYBOOK = tectonic_resources.files('tectonic') / 'services' / 'ansible' / 'configure_services.yml'
    ANSIBLE_TRAINEES_PLAYBOOK = tectonic_resources.files('tectonic') / 'playbooks' / 'trainees.yml'

    def __init__(self, config, description):
        """
        Initialize the core object.
        """
        self.config = config
        self.description = description

        if self.config.platform == "aws":
            self.terraform = TerraformAWS(self,config, self.description)
            self.client = ClientAWS(self.config, self.description)
            self.packer = PackerAWS(self.config, self.description, self.client)
            self.terraform_service = TerraformServiceAWS(self.config, self.description, self.client)
        elif self.config.platform == "libvirt":
            self.terraform = TerraformLibvirt(self.config, self.description)
            self.client = ClientLibvirt(self.config, self.description)
            self.packer = PackerLibvirt(self.config, self.description, self.client)
            self.terraform_service = TerraformServiceLibvirt(self.config, self.description, self.client)
        elif self.config.platform == "docker":
            self.terraform = TerraformDocker(self.config, self.description)
            self.client = ClientDocker(self.config, self.description)
            self.packer = PackerDocker(self.config, self.description, self.client)
            self.terraform_service = TerraformServiceDocker(self.config, self.description, self.client)
        else:
            raise CoreException("Unknown platform.")
        self.ansible = Ansible(self.config, self.description, self.client)
        
    def __del__(self):
        del self.terraform_service
        del self.packer
        del self.client
        del self.terraform
        del self.ansible
        del self.description

    def create_cr_images(self, guests=()):
        """
        Create base images.

        Parameters:
            guests (list(str)): names of the guests for which to create images. 
        """
        if guests is not None:
            self.packer.destroy_image(guests)
            self.packer.create_instance_image(guests)

    def create_services_images(self, services=None):
        """
        Create base images.

        Parameters:
            services (list(str)): List of services to create.
        """
        if services is not None:
            self.packer.destroy_image(services)
            self.packer.create_service_image(services)
    
    def deploy(self, instances, create_instances_images, create_services_images):
        """
        Create scenario.

        Parameters:
            instances (list(int)): numbers of the instances to deploy.
            create_instances_images: whether to create instances images.
            create_services_images: whether to create services images.
        """
        if create_instances_images:
            self.create_cr_images()
        if create_services_images:
            self.create_services_images()

        if self.config.platform in ["docker", "libvirt"]:
            self.terraform_service.deploy(instances)

            self.ansible.configure_services()

            self.terraform.deploy(instances)

        elif self.config.platform in ["aws"]:
            self.terraform.deploy(instances)
                
            self.terraform_service.deploy(instances)
            
            self.ansible.configure_services()

        # Wait for instances to bootup
        self.ansible.wait_for_connections(instances=instances)

        # Run instances post clone configuration
        self.ansible.run(instances, quiet=True)

        # Configure student access on instances
        self.configure_students_access(instances)  

        # Configure Elastic monitoring
        if self.description.elastic.enable:
            if self.description.elastic.monitor_type == "traffic":
                self.terraform_service.deploy_packetbeat(self.ansible)
            elif self.description.elastic.monitor_type == "endpoint":
                self.terraform_service.install_elastic_agent(self.ansible, instances)

        # Configure Caldera agents
        if self.description.caldera.enable:
            self.terraform_service.install_caldera_agent(self.ansible, instances)

    def destroy(self, instances, machines, services, destroy_images):
        """
        Destroy scenario.

        Parameters:
            instances (list(int)): numbers of the instances to destroy, if None destroy all.
            machines (bool): whether to destroy scenario machines.
            services (list(str)): list of services to destroy
            destroy_images (bool): whether to destroy instances images.
        """
        if self.config.platform in ["docker", "libvirt"]:
            self.terraform.destroy(instances)
            self.terraform_service.destroy(instances)
        elif self.config.platform in ["aws"]:
            self.terraform_service.destroy(instances)
            self.terraform.destroy(instances)
        
        if instances is None:
            # Destroy Packetbeat
            if self.description.elastic.enable and self.description.elastic.monitor_type == "traffic":
                self.terraform_service.destroy_packetbeat(self.ansible)
                
            # Destroy images
            if destroy_images:
                self.packer.destroy_image(self.description.base_guests.keys())
                #self.packer.destroy_image(self.description.get_services_to_deploy())
    
    def recreate(self, instances, guests, copies):
        """
        Recreate scenario machines.

        Parameters:
            instances (list(int)): number of the instances to start.
            guests (list(str)): name of the guests to start.
            copies (list(int)): number of the copies to start.
        """
        # Recreate instances
        self.terraform.recreate(instances, guests, copies)

        # Wait for instances to bootup
        self.ansible.wait_for_connections(instances, guests, copies, False, self.description.services)
        
        # Run instances post clone configuration
        self.ansible.run(instances, guests, copies, quiet=True, only_instances=False)

        # Configure student access on instances
        self.configure_students_access(instances)

        # Configure Elastic monitoring
        if self.description.elastic.enable and self.description.elastic.monitor_type == "endpoint":
            self.terraform_service.install_elastic_agent(self.ansible, instances)

        # Configure Caldera agents
        if self.description.caldera.enable:
            self.terraform_service.install_caldera_agent(self.ansible, instances)

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
                self.terraform_service.manage_packetbeat(self.ansible, "started") # TODO: ver que pasa en AWS con start, stop, restart del servicio de packetbeat 
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
                self.terraform_service.manage_packetbeat(self.ansible, "stopped")

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
                self.terraform_service.manage_packetbeat(self.ansible, "restarted")

    def info(self):
        """
        Get scenario connection information.

        Return:
            dict: scenario information.
        """
        instances_info = {}
        if self.config.platform == "aws":
            if self.description.student_access_required:
                student_access_ip = self.client.get_machine_public_ip(f"{self.description.institution}-{self.description.lab_name}-student_access")
                if student_access_ip is not None:
                    instances_info["Student Access IP"] = student_access_ip
            if self.config.aws.teacher_access == "host":
                teacher_access_ip = self.client.get_machine_public_ip(f"{self.description.institution}-{self.description.lab_name}-teacher_access")
                if teacher_access_ip is not None:
                    instances_info["Teacher Access IP"] = teacher_access_ip

        service_info = {}
        for service_name, service in self.description.services_guests.items():
            credentials = self.terraform_service.get_service_credentials(service, self.ansible)
            ip = self.client.get_machine_private_ip(service.name) # En docker tiene que ser 127.0.0.1 ver como arreglar.
            service_info[service.base_name] = {
                "ip": ip,
                "credentials": credentials,
            }
        return {
            "instances_info": instances_info,
            "services_info": service_info,
            "student_access_password": self._get_students_passwords(),
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
        if self.description.elastic.enable and self.description.elastic.monitor_type == "traffic":
            packetbeat_status = self.terraform_service.manage_packetbeat(self.ansible,"status")
            if packetbeat_status is not None:
                services_status[f"{self.description.institution}-{self.description.lab_name}-packetbeat"] = packetbeat_status
        return {
            "instances_status" : instances_status,
            "services_status" : services_status
        }

    def get_parameters(self, instances, directory=None):
        """
        Get parameters used for the individualization of the instances.

        Parameters:
            instances (list(int)): number of instances.
            directory (str): the directory where to create parameters

        Return:
            dict: parameters.
        """
        self.description.parse_machines(instances)
        parameters = self.description.get_parameters(instances)
        if directory:
            try:
                os.makedirs(directory, exist_ok=True)
                file_path = os.path.join(directory, f"{self.description.institution}-{self.description.lab_name}-parameters.json")
                with open(file_path, "w") as file:
                    json.dump(parameters, file, indent=4)
            except Exception as exception:
                raise CoreException(f"{exception}")
            return f"Parameters file created in: {file_path}"
        else:
            return parameters
    
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
        self.client.console(machine_name, username)

    def configure_students_access(self, instances):
        """
        Configure students users to access instances.
        Users are created on all entry points (and the student access host, if appropriate). 
        Credentials can be public SSH keys and/or autogenerated passwords.
        """
        only_instances = True
        entry_points = [guest.base_name for _, guest in self.description.base_guests.items() if guest.entry_point]
        if self.config.platform == "aws" and entry_points:
            entry_points.append("student_access")
            only_instances = False
        users = self.description.generate_student_access_credentials()
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
        return users
    
    def _get_students_passwords(self):
        """
        Get the generated students password.

        Return:
            dic: the password for each user.
        """
        if not self.description.create_students_passwords:
            return {}
        credentials = self.description.generate_student_access_credentials()
        return {username: user['password'] for username, user in credentials.items()}
