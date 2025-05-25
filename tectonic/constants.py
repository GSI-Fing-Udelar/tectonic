
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

OS_DATA = {
    "ubuntu22": {
        "ami_filter": "ubuntu/images/*/ubuntu-*-22.04-amd64-server*",
        "owner": "099720109477",
        "username": "ubuntu",
        "cloud_image_url": "https://cloud-images.ubuntu.com/releases/22.04/release-20230616/ubuntu-22.04-server-cloudimg-amd64.img",
        "cloud_image_checksum": "fe102bfb3d3d917d31068dd9a4bd8fcaeb1f529edda86783f8524fdc1477ee29",
        "docker_base_image": "gsitectonic/ubuntu22",
        "entrypoint": "/usr/bin/systemd",
    },
    "ubuntu22_deep_learning": {
        "ami_filter": "*Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*",
        "owner": "898082745236",
        "username": "ubuntu",
    },
    "rocky8": {
        "ami_filter": "Rocky*8.9*x86_64",
        "owner": "792107900819",
        "username": "rocky",
        #"cloud_image_url": "http://dl.rockylinux.org/pub/rocky/8/images/x86_64/Rocky-8-GenericCloud.latest.x86_64.qcow2",
        "cloud_image_url": "file:///data/isos/Rocky-8-GenericCloud.latest.x86_64.qcow2",
        "cloud_image_checksum": "e56066c58606191e96184de9a9183a3af33c59bcbd8740d8b10ca054a7a89c14",
        "docker_base_image": "gsitectonic/rocky8",
        "entrypoint": "/usr/sbin/init",
    },
    "kali": {
        "ami_filter": "kali-last-snapshot-amd64*",
        "owner": "679593333241",  # TODO: Marketplace owner id
        "username": "kali",
        # cloud-init image not provided by Kali :(
        # See https://codingpackets.com/blog/kali-linux-cloud-init-image/
            "cloud_image_url": "file:///data/isos/kali-linux-2023.3-qemu-amd64.qcow2",
        "cloud_image_checksum": "b48cc396cf91ea1f38de4dca7abfcc0175f07d7af1b7e6df89a76194e7fda3d9",
        # "cloud_image_url": "https://cdimage.kali.org/kali-2023.3/kali-linux-2023.3-qemu-amd64.7z"
        # "cloud_image_checksum": "9ebbea4abb545c8e4a56153e2b5fa0ad90658c583af2fa76ad8c0a0b4ba23e20",
        },
    "windows_srv_2022": {
        "ami_filter": "Windows_Server-2022-English-Full-Base*",
        "owner": "amazon",
        "username": "administrator",
    },
}

SERVICES_SIZE = {
    "elastic" : {
        "libvirt" : {
            "test" : {
                "vcpu":2,
                "memory":4096, #MB
                "disk":10, #GB
            },
            "small" : {
                "vcpu":4,
                "memory":8192,
                "disk":60,
            },
            "medium": {
                "vcpu":8,
                "memory":16384,
                "disk":110,
            },
            "big":{
                "vcpu":12,
                "memory":24576,
                "disk":160,
            }
        },
        "aws" : {
            "small": "t2.small",
            "medium": "t2.medium",
            "big": "t2.big",
        }
    },
    "caldera" : {
        "libvirt" : {
            "test" : {
                "vcpu":1,
                "memory":2048, #MB
                "disk":10, #GB
            },
            "small" : {
                "vcpu":2,
                "memory":2048,
                "disk":20,
            },
            "medium": {
                "vcpu":3,
                "memory":4096,
                "disk":20,
            },
            "big":{
                "vcpu":4,
                "memory":8192,
                "disk":50,
            }
        },
        "aws" : {
            "small": "t2.small",
            "medium": "t2.medium",
            "big": "t2.big",
        }
    }
}
