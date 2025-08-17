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

"""Mixin classes to reduce code duplication in deployment classes."""

from typing import Dict, List, Optional
from tectonic.utils import create_table


class CyberRangeDataMixin:
    """Mixin providing common cyber range data functionality."""
    
    def _build_cyberrange_data_table(self):
        """Build a table with cyber range information."""
        headers = ["Name", "Value"]
        rows = []
        
        # Add student access information if applicable
        if self.description.is_student_access():
            student_ip = self._get_student_access_ip()
            if student_ip:
                rows.append(["Student Access IP", student_ip])
        
        # Add teacher access information
        if self.description.teacher_access == "host":
            teacher_ip = self._get_teacher_access_ip()
            if teacher_ip:
                rows.append(["Teacher Access IP", teacher_ip])
        
        # Add services information
        if len(self.description.get_services_to_deploy()) > 0:
            # Add empty row if we have access IPs and services
            has_access_ips = False
            if self.description.is_student_access():
                student_ip = self._get_student_access_ip()
                if student_ip:
                    has_access_ips = True
            if self.description.teacher_access == "host":
                teacher_ip = self._get_teacher_access_ip()
                if teacher_ip:
                    has_access_ips = True
            
            if has_access_ips:
                rows.append(["", ""])  # Empty row for spacing
            
            # Elastic service information
            if self.description.deploy_elastic:
                elastic_data = self._get_elastic_service_data()
                if elastic_data:
                    rows.extend(elastic_data)
                    if self.description.deploy_caldera:
                        rows.append(["", ""])  # Spacing between services
                else:
                    return "Unable to get Elastic info right now. Please make sure de Elastic machine is running."
            
            # Caldera service information
            if self.description.deploy_caldera:
                caldera_data = self._get_caldera_service_data()
                if caldera_data:
                    rows.extend(caldera_data)
                else:
                    return "Unable to get Caldera info right now. Please make sure de Caldera machine is running."
        
        # Return empty string if no data to display (for Docker compatibility)
        if not rows:
            return ""
        
        return create_table(headers, rows)
    
    def _get_elastic_service_data(self) -> Optional[List[List[str]]]:
        """Get Elastic service data for the table."""
        elastic_name = self.description.get_service_name("elastic")
        if self.get_instance_status(elastic_name) == "RUNNING":
            # Docker uses 127.0.0.1 for service IPs
            if hasattr(self.description, 'platform') and self.description.platform == 'docker':
                elastic_ip = "127.0.0.1"
            else:
                elastic_ip = self.get_ssh_hostname(elastic_name)
            elastic_credentials = self._get_service_password("elastic")
            return [
                ["Kibana URL", f"https://{elastic_ip}:5601"],
                ["Kibana user (username: password)", f"elastic: {elastic_credentials['elastic']}"]
            ]
        return None
    
    def _get_caldera_service_data(self) -> Optional[List[List[str]]]:
        """Get Caldera service data for the table."""
        caldera_name = self.description.get_service_name("caldera")
        if self.get_instance_status(caldera_name) == "RUNNING":
            # Docker uses 127.0.0.1 for service IPs
            if hasattr(self.description, 'platform') and self.description.platform == 'docker':
                caldera_ip = "127.0.0.1"
            else:
                caldera_ip = self.get_ssh_hostname(caldera_name)
            caldera_credentials = self._get_service_password("caldera")
            return [
                ["Caldera URL", f"https://{caldera_ip}:8443"],
                ["Caldera user (username: password)", f"red: {caldera_credentials['red']}"],
                ["Caldera user (username: password)", f"blue: {caldera_credentials['blue']}"]
            ]
        return None
    
    def _get_student_access_ip(self) -> Optional[str]:
        """Get student access IP address."""
        try:
            return self.client.get_machine_public_ip(
                f"{self.description.institution}-{self.description.lab_name}-student_access"
            )
        except Exception:
            return None
    
    def _get_teacher_access_ip(self) -> Optional[str]:
        """Get teacher access IP address."""
        try:
            return self.client.get_machine_public_ip(
                f"{self.description.institution}-{self.description.lab_name}-teacher_access"
            )
        except Exception:
            return None


class ImageManagementMixin:
    """Mixin providing common image management functionality."""
    
    def _delete_images_safely(self, image_names: List[str], exception_class) -> None:
        """Safely delete images, checking if they are in use first."""
        # First check if any images are in use
        for image_name in image_names:
            if self.client.is_image_in_use(image_name):
                raise exception_class(
                    f"Unable to delete image {image_name} because it is being used."
                )
        
        # Then delete all images
        for image_name in image_names:
            # Handle different client interfaces based on client type
            # Check platform type to determine the correct client interface
            if hasattr(self.description, 'platform'):
                if self.description.platform == 'libvirt':
                    # Libvirt client requires storage pool parameter
                    self.client.delete_image(self.description.libvirt_storage_pool, image_name)
                elif self.description.platform == 'docker':
                    # Docker client - check if image exists before deleting
                    if self.client.get_image(image_name) is not None:
                        self.client.delete_image(image_name)
                else:
                    # Standard client interface (AWS)
                    self.client.delete_image(image_name)
            else:
                # Fallback: try to detect by client type
                if hasattr(self.client, 'get_image'):
                    # Docker client - check if image exists before deleting
                    if self.client.get_image(image_name) is not None:
                        self.client.delete_image(image_name)
                else:
                    # Standard client interface (AWS)
                    self.client.delete_image(image_name)
    
    def _get_guest_image_names(self, guests: Optional[List[str]] = None) -> List[str]:
        """Get image names for the specified guests."""
        if guests is None:
            guests = list(self.description.guest_settings.keys())
        
        return [self.description.get_image_name(guest_name) for guest_name in guests]


class ServiceManagementMixin:
    """Mixin providing common service management functionality."""
    
    def _get_services_network_data(self) -> Dict:
        """Get network data for services."""
        return {
            "elastic": {
                "network": self.description.services_network,
                "ip": self.description.services_network_base_ip + 1,
            },
            "caldera": {
                "network": self.description.services_network,
                "ip": self.description.services_network_base_ip + 2,
            }
        }
    
    def _get_services_guest_data(self) -> Dict:
        """Get guest data for services."""
        return {
            "elastic": {
                "base_os": "ubuntu22",
                "vcpu": self._get_service_vcpu("elastic"),
                "memory": self._get_service_memory("elastic"),
                "disk": self._get_service_disk("elastic"),
            },
            "caldera": {
                "base_os": "ubuntu22",
                "vcpu": self._get_service_vcpu("caldera"),
                "memory": self._get_service_memory("caldera"),
                "disk": self._get_service_disk("caldera"),
            }
        }
    
    def _get_service_vcpu(self, service: str) -> int:
        """Get VCPU count for a service."""
        # This would need to be implemented based on the specific service configuration
        # For now, returning default values
        defaults = {"elastic": 2, "caldera": 1}
        return defaults.get(service, 1)
    
    def _get_service_memory(self, service: str) -> int:
        """Get memory size for a service."""
        # This would need to be implemented based on the specific service configuration
        # For now, returning default values
        defaults = {"elastic": 4096, "caldera": 2048}
        return defaults.get(service, 1024)
    
    def _get_service_disk(self, service: str) -> int:
        """Get disk size for a service."""
        # This would need to be implemented based on the specific service configuration
        # For now, returning default values
        defaults = {"elastic": 10, "caldera": 10}
        return defaults.get(service, 10)
