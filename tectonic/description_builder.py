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

"""Builder pattern for creating Description objects."""

from typing import Optional
from pathlib import Path
from tectonic.description import Description
from tectonic.instance_type import InstanceType


class DescriptionBuilder:
    """Builder for creating Description objects with a cleaner interface."""
    
    def __init__(self, lab_edition_file: str, platform: str, lab_repo_uri: str):
        """Initialize the builder with required parameters."""
        self.lab_edition_file = lab_edition_file
        self.platform = platform
        self.lab_repo_uri = lab_repo_uri
        
        # Set defaults
        self.teacher_access = "host"
        self.configure_dns = True
        self.ssh_public_key_file = "~/.ssh/id_rsa.pub"
        self.ansible_ssh_common_args = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=3600 "
        self.aws_region = "us-east-1"
        self.aws_default_instance_type = "t2.micro"
        self.network_cidr_block = "10.0.0.0/16"
        self.packetbeat_policy_name = "Packetbeat"
        self.packetbeat_vlan_id = "1"
        self.elastic_stack_version = "8.14.3"
        self.libvirt_uri = "qemu:///system"
        self.libvirt_storage_pool = "default"
        self.libvirt_student_access = "port_forwarding"
        self.libvirt_bridge = None
        self.libvirt_external_network = "192.168.0.0/25"
        self.libvirt_bridge_base_ip = 10
        self.proxy = None
        self.endpoint_policy_name = "Endpoint"
        self.user_install_packetbeat = "tectonic"
        self.internet_network_cidr_block = "192.168.4.0/24"
        self.services_network_cidr_block = "192.168.5.0/24"
        self.keep_ansible_logs = False
        self.docker_uri = "unix:///var/run/docker.sock"
        self.caldera_version = "latest"
        self.docker_dns = "8.8.8.8"
        self.ansible_forks = "10"
        self.ansible_pipelining = False
        self.ansible_timeout = "10"
        self.instance_type = None
    
    def with_teacher_access(self, teacher_access: str) -> 'DescriptionBuilder':
        """Set teacher access type."""
        self.teacher_access = teacher_access
        return self
    
    def with_configure_dns(self, configure_dns: bool) -> 'DescriptionBuilder':
        """Set DNS configuration."""
        self.configure_dns = configure_dns
        return self
    
    def with_ssh_config(self, ssh_public_key_file: str, ansible_ssh_common_args: str) -> 'DescriptionBuilder':
        """Set SSH configuration."""
        self.ssh_public_key_file = ssh_public_key_file
        self.ansible_ssh_common_args = ansible_ssh_common_args
        return self
    
    def with_aws_config(self, aws_region: str, aws_default_instance_type: str) -> 'DescriptionBuilder':
        """Set AWS configuration."""
        self.aws_region = aws_region
        self.aws_default_instance_type = aws_default_instance_type
        return self
    
    def with_network_config(self, network_cidr_block: str) -> 'DescriptionBuilder':
        """Set network configuration."""
        self.network_cidr_block = network_cidr_block
        return self
    
    def with_monitoring_config(self, packetbeat_policy_name: str, packetbeat_vlan_id: str) -> 'DescriptionBuilder':
        """Set monitoring configuration."""
        self.packetbeat_policy_name = packetbeat_policy_name
        self.packetbeat_vlan_id = packetbeat_vlan_id
        return self
    
    def with_elastic_config(self, elastic_stack_version: str) -> 'DescriptionBuilder':
        """Set Elastic configuration."""
        self.elastic_stack_version = elastic_stack_version
        return self
    
    def with_libvirt_config(
        self,
        libvirt_uri: str,
        libvirt_storage_pool: str,
        libvirt_student_access: str,
        libvirt_bridge: Optional[str] = None,
        libvirt_external_network: str = "192.168.0.0/25",
        libvirt_bridge_base_ip: int = 10
    ) -> 'DescriptionBuilder':
        """Set Libvirt configuration."""
        self.libvirt_uri = libvirt_uri
        self.libvirt_storage_pool = libvirt_storage_pool
        self.libvirt_student_access = libvirt_student_access
        self.libvirt_bridge = libvirt_bridge
        self.libvirt_external_network = libvirt_external_network
        self.libvirt_bridge_base_ip = libvirt_bridge_base_ip
        return self
    
    def with_docker_config(
        self,
        docker_uri: str,
        caldera_version: str,
        docker_dns: str
    ) -> 'DescriptionBuilder':
        """Set Docker configuration."""
        self.docker_uri = docker_uri
        self.caldera_version = caldera_version
        self.docker_dns = docker_dns
        return self
    
    def with_ansible_config(
        self,
        ansible_forks: str,
        ansible_pipelining: bool,
        ansible_timeout: str
    ) -> 'DescriptionBuilder':
        """Set Ansible configuration."""
        self.ansible_forks = ansible_forks
        self.ansible_pipelining = ansible_pipelining
        self.ansible_timeout = ansible_timeout
        return self
    
    def with_proxy(self, proxy: Optional[str]) -> 'DescriptionBuilder':
        """Set proxy configuration."""
        self.proxy = proxy
        return self
    
    def with_endpoint_config(self, endpoint_policy_name: str, user_install_packetbeat: str) -> 'DescriptionBuilder':
        """Set endpoint configuration."""
        self.endpoint_policy_name = endpoint_policy_name
        self.user_install_packetbeat = user_install_packetbeat
        return self
    
    def with_network_blocks(self, internet_network_cidr_block: str, services_network_cidr_block: str) -> 'DescriptionBuilder':
        """Set network CIDR blocks."""
        self.internet_network_cidr_block = internet_network_cidr_block
        self.services_network_cidr_block = services_network_cidr_block
        return self
    
    def with_logging_config(self, keep_ansible_logs: bool) -> 'DescriptionBuilder':
        """Set logging configuration."""
        self.keep_ansible_logs = keep_ansible_logs
        return self
    
    def build(self) -> Description:
        """Build and return the Description object."""
        # Create instance type based on platform
        if self.platform == "aws":
            from tectonic.instance_type_aws import InstanceTypeAWS
            self.instance_type = InstanceTypeAWS(self.aws_default_instance_type)
        else:
            self.instance_type = InstanceType()
        
        return Description(
            self.lab_edition_file,
            self.platform,
            self.lab_repo_uri,
            self.teacher_access,
            self.configure_dns,
            self.ssh_public_key_file,
            self.ansible_ssh_common_args,
            self.aws_region,
            self.aws_default_instance_type,
            self.network_cidr_block,
            self.packetbeat_policy_name,
            self.packetbeat_vlan_id,
            self.elastic_stack_version,
            self.libvirt_uri,
            self.libvirt_storage_pool,
            self.libvirt_student_access,
            self.libvirt_bridge,
            self.libvirt_external_network,
            self.libvirt_bridge_base_ip,
            self.proxy,
            self.instance_type,
            self.endpoint_policy_name,
            self.user_install_packetbeat,
            self.internet_network_cidr_block,
            self.services_network_cidr_block,
            self.keep_ansible_logs,
            self.docker_uri,
            self.caldera_version,
            self.docker_dns,
            self.ansible_forks,
            self.ansible_pipelining,
            self.ansible_timeout
        )

