
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
        "cloud_image_url": "https://cloud-images.ubuntu.com/releases/22.04/release-20260515/ubuntu-22.04-server-cloudimg-amd64.img",
        "cloud_image_checksum": "f6729b53d930d7f0c6691eb553cfa6be7109de9412125bf1bf2dc6747de8a44d",
        "docker_base_image": "gsitectonic/ubuntu22",
        "entrypoint": "/usr/bin/systemd",
        "interface_base_name": "ens"
    },
    "ubuntu22_deep_learning": {
        "ami_filter": "*Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)*",
        "owner": "898082745236",
        "username": "ubuntu",
        "interface_base_name": "ens"
    },
    "ubuntu24": {
        "ami_filter": "ubuntu/images/*/ubuntu-*-24.04-amd64-server*",
        "owner": "099720109477",
        "username": "ubuntu",
        "cloud_image_url": "https://cloud-images.ubuntu.com/releases/noble/release-20260518/ubuntu-24.04-server-cloudimg-amd64.img",
        "cloud_image_checksum": "53fdde898feed8b027d94baa9cfe8229867f330a1d9c49dc7d84465ee7f229f7",
        "docker_base_image": "gsitectonic/ubuntu24",
        "entrypoint": "/usr/bin/systemd",
        "interface_base_name": "ens"
    },
    "rocky8": {
        "ami_filter": "Rocky-8-EC2-Base-8.*x86_64",
        "owner": "792107900819",
        "username": "rocky",
        "cloud_image_url": "http://dl.rockylinux.org/pub/rocky/8/images/x86_64/Rocky-8-GenericCloud.latest.x86_64.qcow2",
        #"cloud_image_url": "file:///data/isos/Rocky-8-GenericCloud.latest.x86_64.qcow2",
        "cloud_image_checksum": "e56066c58606191e96184de9a9183a3af33c59bcbd8740d8b10ca054a7a89c14",
        "docker_base_image": "gsitectonic/rocky8",
        "entrypoint": "/usr/sbin/init",
        "interface_base_name": "eth"
    },
    "rocky9": {
        "ami_filter": "Rocky-9-EC2-Base-9.*x86_64",
        "owner": "792107900819",
        "username": "rocky",
        "cloud_image_url": "https://dl.rockylinux.org/pub/rocky/9/images/x86_64/Rocky-9-GenericCloud.latest.x86_64.qcow2",
        #"cloud_image_url": "file:///data/isos/Rocky-9-GenericCloud.latest.x86_64.qcow2",
        "cloud_image_checksum": "92c206cc6f790c61583247eefe87890f8828420662c17cacf247cec78ab4eec8",
        "docker_base_image": "gsitectonic/rocky9",
        "entrypoint": "/usr/sbin/init",
        "interface_base_name": "eth"
    },
    "kali": {
        "ami_filter": "kali-last-snapshot-amd64*",
        "owner": "679593333241",
        "username": "kali",
        #"cloud_image_url": "https://kali.download/cloud-images/kali-2026.1/kali-linux-2026.1-cloud-genericcloud-amd64.tar.xz",
        "cloud_image_url": "file:///data/isos/kali-linux-2026.1-cloud-genericcloud-amd64.qcow2",
        "cloud_image_checksum": "94ce481ccb48661bb17c8283ac32d8be2f15a4b8ce9201743a466079be27664e",
        "docker_base_image": "gsitectonic/kali",
        "entrypoint": "/usr/sbin/init",
        "interface_base_name": "ens"
        },
    "windows_srv_2022": {
        "ami_filter": "Windows_Server-2022-English-Full-Base*",
        "owner": "amazon",
        "username": "administrator",
    },
}
