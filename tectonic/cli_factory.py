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

"""Factory classes for creating deployment and instance type objects."""

from typing import Optional
from tectonic.deployment_aws import AWSDeployment
from tectonic.deployment_libvirt import LibvirtDeployment
from tectonic.deployment_docker import DockerDeployment
from tectonic.instance_type import InstanceType
from tectonic.instance_type_aws import InstanceTypeAWS
from tectonic.description import Description


class DeploymentFactory:
    """Factory for creating deployment objects based on platform."""
    
    @staticmethod
    def create_deployment(
        platform: str,
        description: Description,
        gitlab_backend_url: Optional[str] = None,
        gitlab_backend_username: Optional[str] = None,
        gitlab_backend_access_token: Optional[str] = None,
        packer_executable_path: str = "/usr/bin/packer"
    ):
        """Create a deployment object for the specified platform.
        
        Args:
            platform: The deployment platform ("aws", "libvirt", "docker")
            description: The lab description object
            gitlab_backend_url: GitLab backend URL
            gitlab_backend_username: GitLab backend username
            gitlab_backend_access_token: GitLab backend access token
            packer_executable_path: Path to packer executable
            
        Returns:
            A deployment object for the specified platform
            
        Raises:
            ValueError: If platform is not supported
        """
        deployment_kwargs = {
            "description": description,
            "gitlab_backend_url": gitlab_backend_url,
            "gitlab_backend_username": gitlab_backend_username,
            "gitlab_backend_access_token": gitlab_backend_access_token,
            "packer_executable_path": packer_executable_path,
        }
        
        if platform == "aws":
            return AWSDeployment(**deployment_kwargs)
        elif platform == "libvirt":
            return LibvirtDeployment(**deployment_kwargs)
        elif platform == "docker":
            return DockerDeployment(**deployment_kwargs)
        else:
            raise ValueError(f"Unsupported platform: {platform}")


class InstanceTypeFactory:
    """Factory for creating instance type objects."""
    
    @staticmethod
    def create_instance_type(platform: str, aws_default_instance_type: str = "t2.micro"):
        """Create an instance type object for the specified platform.
        
        Args:
            platform: The deployment platform
            aws_default_instance_type: Default AWS instance type
            
        Returns:
            An instance type object
        """
        if platform == "aws":
            return InstanceTypeAWS(aws_default_instance_type)
        else:
            return InstanceType()

