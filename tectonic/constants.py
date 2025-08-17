
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

"""Constants used by Tectonic."""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class OSConfig:
    """Configuration for an operating system."""
    ami_filter: str
    owner: str
    username: str
    cloud_image_url: str = None
    cloud_image_checksum: str = None
    docker_base_image: str = None
    entrypoint: str = None


@dataclass
class ServiceSize:
    """Configuration for service sizing."""
    vcpu: int
    memory: int  # MB
    disk: int    # GB


@dataclass
class ServiceConfig:
    """Configuration for a service."""
    libvirt: Dict[str, ServiceSize]
    aws: Dict[str, str]


class OSData:
    """Operating system configurations."""
    
    UBUNTU22 = OSConfig(
        ami_filter="ubuntu/images/*/ubuntu-*-22.04-amd64-server*",
        owner="099720109477",
        username="ubuntu",
        cloud_image_url="https://cloud-images.ubuntu.com/releases/22.04/release-20230616/ubuntu-22.04-server-cloudimg-amd64.img",
        cloud_image_checksum="fe102bfb3d3d917d31068dd9a4bd8fcaeb1f529edda86783f8524fdc1477ee29",
        docker_base_image="gsitectonic/ubuntu22",
        entrypoint="/usr/bin/systemd",
    )
    
    UBUNTU22_DEEP_LEARNING = OSConfig(
        ami_filter="*Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*",
        owner="898082745236",
        username="ubuntu",
    )
    
    ROCKY8 = OSConfig(
        ami_filter="Rocky*8.8*x86_64",
        owner="792107900819",
        username="rocky",
        cloud_image_url="file:///data/isos/Rocky-8-GenericCloud.latest.x86_64.qcow2",
        cloud_image_checksum="d17f15a7649dd064795306c114b90fc5062e7d5fefa9e9f0bd6b7ce1aeac3ae5",
        docker_base_image="gsitectonic/rocky8",
        entrypoint="/usr/sbin/init",
    )
    
    KALI = OSConfig(
        ami_filter="kali-last-snapshot-amd64*",
        owner="679593333241",
        username="kali",
        cloud_image_url="file:///data/isos/kali-linux-2023.3-qemu-amd64.qcow2",
        cloud_image_checksum="b48cc396cf91ea1f38de4dca7abfcc0175f07d7af1b7e6df89a76194e7fda3d9",
    )
    
    WINDOWS_SRV_2022 = OSConfig(
        ami_filter="Windows_Server-2022-English-Full-Base*",
        owner="amazon",
        username="administrator",
    )


class ServiceSizes:
    """Service size configurations."""
    
    ELASTIC = ServiceConfig(
        libvirt={
            "test": ServiceSize(vcpu=2, memory=4096, disk=10),
            "small": ServiceSize(vcpu=4, memory=8192, disk=60),
            "medium": ServiceSize(vcpu=8, memory=16384, disk=110),
            "big": ServiceSize(vcpu=12, memory=24576, disk=160),
        },
        aws={
            "small": "t2.small",
            "medium": "t2.medium",
            "big": "t2.big",
        }
    )
    
    CALDERA = ServiceConfig(
        libvirt={
            "test": ServiceSize(vcpu=1, memory=2048, disk=10),
            "small": ServiceSize(vcpu=2, memory=2048, disk=20),
            "medium": ServiceSize(vcpu=3, memory=4096, disk=20),
            "big": ServiceSize(vcpu=4, memory=8192, disk=50),
        },
        aws={
            "small": "t2.small",
            "medium": "t2.medium",
            "big": "t2.big",
        }
    )


# Legacy compatibility - maintain the old dictionary structure
def _os_config_to_dict(os_config: OSConfig) -> Dict[str, Any]:
    """Convert OSConfig to dictionary for backward compatibility."""
    result = {
        "ami_filter": os_config.ami_filter,
        "owner": os_config.owner,
        "username": os_config.username,
    }
    
    if os_config.cloud_image_url:
        result["cloud_image_url"] = os_config.cloud_image_url
    if os_config.cloud_image_checksum:
        result["cloud_image_checksum"] = os_config.cloud_image_checksum
    if os_config.docker_base_image:
        result["docker_base_image"] = os_config.docker_base_image
    if os_config.entrypoint:
        result["entrypoint"] = os_config.entrypoint
    
    return result


def _service_config_to_dict(service_config: ServiceConfig) -> Dict[str, Any]:
    """Convert ServiceConfig to dictionary for backward compatibility."""
    return {
        "libvirt": {
            size: {"vcpu": config.vcpu, "memory": config.memory, "disk": config.disk}
            for size, config in service_config.libvirt.items()
        },
        "aws": service_config.aws
    }


# Maintain backward compatibility with existing code
OS_DATA = {
    "ubuntu22": _os_config_to_dict(OSData.UBUNTU22),
    "ubuntu22_deep_learning": _os_config_to_dict(OSData.UBUNTU22_DEEP_LEARNING),
    "rocky8": _os_config_to_dict(OSData.ROCKY8),
    "kali": _os_config_to_dict(OSData.KALI),
    "windows_srv_2022": _os_config_to_dict(OSData.WINDOWS_SRV_2022),
}

SERVICES_SIZE = {
    "elastic": _service_config_to_dict(ServiceSizes.ELASTIC),
    "caldera": _service_config_to_dict(ServiceSizes.CALDERA),
}
