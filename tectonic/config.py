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

"""Configuration classes for Tectonic CLI parameters."""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class TectonicConfig:
    """Configuration object for Tectonic CLI parameters."""
    
    # Platform configuration
    platform: str = "aws"
    lab_repo_uri: str = ""
    
    # AWS configuration
    aws_region: str = "us-east-1"
    aws_default_instance_type: str = "t2.micro"
    
    # SSH configuration
    ssh_public_key_file: str = "~/.ssh/id_rsa.pub"
    ansible_ssh_common_args: str = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=3600 "
    
    # Network configuration
    network_cidr_block: str = "10.0.0.0/16"
    internet_network_cidr_block: str = "192.168.4.0/24"
    services_network_cidr_block: str = "192.168.5.0/24"
    
    # Monitoring configuration
    packetbeat_vlan_id: str = "1"
    packetbeat_policy_name: str = "Packetbeat"
    endpoint_policy_name: str = "Endpoint"
    user_install_packetbeat: str = "tectonic"
    
    # General configuration
    configure_dns: bool = True
    teacher_access: str = "host"
    elastic_stack_version: str = "8.14.3"
    keep_ansible_logs: bool = False
    
    # GitLab backend configuration
    gitlab_backend_url: Optional[str] = None
    gitlab_backend_username: Optional[str] = None
    gitlab_backend_access_token: Optional[str] = None
    packer_executable_path: str = "packer"
    
    # Libvirt configuration
    libvirt_uri: str = "qemu:///system"
    libvirt_storage_pool: str = "default"
    libvirt_student_access: str = "port_forwarding"
    libvirt_bridge: Optional[str] = None
    libvirt_external_network: str = "192.168.0.0/25"
    libvirt_bridge_base_ip: int = 10
    
    # Docker configuration
    docker_uri: str = "unix:///var/run/docker.sock"
    caldera_version: str = "latest"
    docker_dns: str = "8.8.8.8"
    
    # Ansible configuration
    ansible_forks: str = "10"
    ansible_pipelining: bool = False
    ansible_timeout: str = "10"
    
    # Proxy configuration
    proxy: Optional[str] = None
    
    # Lab file
    lab_edition_file: Optional[Path] = None
    
    def to_description_kwargs(self) -> dict:
        """Convert config to keyword arguments for Description constructor."""
        return {
            "path": str(self.lab_edition_file),
            "platform": self.platform,
            "lab_repo_uri": self.lab_repo_uri,
            "teacher_access": self.teacher_access,
            "configure_dns": self.configure_dns,
            "ssh_public_key_file": self.ssh_public_key_file,
            "ansible_ssh_common_args": self.ansible_ssh_common_args,
            "aws_region": self.aws_region,
            "aws_default_instance_type": self.aws_default_instance_type,
            "network_cidr_block": self.network_cidr_block,
            "packetbeat_policy_name": self.packetbeat_policy_name,
            "packetbeat_vlan_id": self.packetbeat_vlan_id,
            "elastic_stack_version": self.elastic_stack_version,
            "libvirt_uri": self.libvirt_uri,
            "libvirt_storage_pool": self.libvirt_storage_pool,
            "libvirt_student_access": self.libvirt_student_access,
            "libvirt_bridge": self.libvirt_bridge,
            "libvirt_external_network": self.libvirt_external_network,
            "libvirt_bridge_base_ip": self.libvirt_bridge_base_ip,
            "proxy": self.proxy,
            "endpoint_policy_name": self.endpoint_policy_name,
            "user_install_packetbeat": self.user_install_packetbeat,
            "internet_network_cidr_block": self.internet_network_cidr_block,
            "services_network_cidr_block": self.services_network_cidr_block,
            "keep_ansible_logs": self.keep_ansible_logs,
            "docker_uri": self.docker_uri,
            "caldera_version": self.caldera_version,
            "docker_dns": self.docker_dns,
            "ansible_forks": self.ansible_forks,
            "ansible_pipelining": self.ansible_pipelining,
            "ansible_timeout": self.ansible_timeout,
        }
    
    def to_deployment_kwargs(self) -> dict:
        """Convert config to keyword arguments for deployment creation."""
        return {
            "gitlab_backend_url": self.gitlab_backend_url,
            "gitlab_backend_username": self.gitlab_backend_username,
            "gitlab_backend_access_token": self.gitlab_backend_access_token,
            "packer_executable_path": self.packer_executable_path,
        }

