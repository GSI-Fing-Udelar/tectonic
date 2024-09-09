
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
        "podman_base_image": "ubuntu:22.04",
        "podman_entrypoint": [ "ENTRYPOINT [ \"/usr/bin/systemd\", \"--system\" ]" ]
    },
    "rocky8": {
        "ami_filter": "Rocky*8.8*x86_64",
        "owner": "792107900819",
        "username": "rocky",
        #"cloud_image_url": "http://dl.rockylinux.org/pub/rocky/8/images/x86_64/Rocky-8-GenericCloud.latest.x86_64.qcow2",
        "cloud_image_url": "file:///data/isos/Rocky-8-GenericCloud.latest.x86_64.qcow2",
        "cloud_image_checksum": "d17f15a7649dd064795306c114b90fc5062e7d5fefa9e9f0bd6b7ce1aeac3ae5",
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

ELASTICCLOUD_PRIVATELINK_MAPPING = {
    "af-south-1": {
        "vpc_service_name": "com.amazonaws.vpce.af-south-1.vpce-svc-0d3d7b74f60a6c32c",
        "private_domain_name": "vpce.af-south-1.aws.elastic-cloud.com",
        "az_names": ["af-south-1a", "af-south-1b", "af-south-1c"],
    },
    "ap-east-1": {
        "vpc_service_name": "com.amazonaws.vpce.ap-east-1.vpce-svc-0f96fbfaf55558d5c",
        "private_domain_name": "vpce.ap-east-1.aws.elastic-cloud.com",
        "az_names": ["ap-east-1a", "ap-east-1b", "ap-east-1c"],
    },
    "ap-northeast-1": {
        "vpc_service_name": "com.amazonaws.vpce.ap-northeast-1.vpce-svc-0e1046d7b48d5cf5f",
        "private_domain_name": "vpce.ap-northeast-1.aws.elastic-cloud.com",
        "az_names": ["ap-northeast-1b", "ap-northeast-1c", "ap-northeast-1d"],
    },
    "ap-northeast-2": {
        "vpc_service_name": "com.amazonaws.vpce.ap-northeast-2.vpce-svc-0d90cf62dae682b84",
        "private_domain_name": "vpce.ap-northeast-2.aws.elastic-cloud.com",
        "az_names": ["ap-northeast-2a", "ap-northeast-2b", "ap-northeast-2c"],
    },
    "ap-south-1": {
        "vpc_service_name": "com.amazonaws.vpce.ap-south-1.vpce-svc-0e9c1ae5caa269d1b",
        "private_domain_name": "vpce.ap-south-1.aws.elastic-cloud.com",
        "az_names": ["ap-south-1a", "ap-south-1b", "ap-south-1c"],
    },
    "ap-southeast-1": {
        "vpc_service_name": "com.amazonaws.vpce.ap-southeast-1.vpce-svc-0cbc6cb9bdb683a95",
        "private_domain_name": "vpce.ap-southeast-1.aws.elastic-cloud.com",
        "az_names": ["ap-southeast-1a", "ap-southeast-1b", "ap-southeast-1c"],
    },
    "ap-southeast-2": {
        "vpc_service_name": "com.amazonaws.vpce.ap-southeast-2.vpce-svc-0cde7432c1436ef13",
        "private_domain_name": "vpce.ap-southeast-2.aws.elastic-cloud.com",
        "az_names": ["ap-southeast-2a", "ap-southeast-2b", "ap-northeast-2c"],
    },
    "ca-central-1": {
        "vpc_service_name": "com.amazonaws.vpce.ca-central-1.vpce-svc-0d3e69dd6dd336c28",
        "private_domain_name": "vpce.ca-central-1.aws.elastic-cloud.com",
        "az_names": ["ca-central-1a", "ca-central-1b", "ca-central-1d"],
    },
    "eu-central-1": {
        "vpc_service_name": "com.amazonaws.vpce.eu-central-1.vpce-svc-081b2960e915a0861",
        "private_domain_name": "vpce.eu-central-1.aws.elastic-cloud.com",
        "az_names": ["eu-central-1a", "eu-central-1b", "eu-central-1c"],
    },
    "eu-south-1": {
        "vpc_service_name": "com.amazonaws.vpce.eu-south-1.vpce-svc-03d8fc8a66a755237",
        "private_domain_name": "vpce.eu-south-1.aws.elastic-cloud.com",
        "az_names": ["eu-south-1a", "eu-south-1b", "eu-south-1c"],
    },
    "eu-west-1": {
        "vpc_service_name": "com.amazonaws.vpce.eu-west-1.vpce-svc-01f2afe87944eb12b",
        "private_domain_name": "vpce.eu-west-1.aws.elastic-cloud.com",
        "az_names": ["eu-west-1a", "eu-west-1b", "eu-west-1c"],
    },
    "eu-west-2": {
        "vpc_service_name": "com.amazonaws.vpce.eu-west-2.vpce-svc-0e42a2c194c97a1d0",
        "private_domain_name": "vpce.eu-west-2.aws.elastic-cloud.com",
        "az_names": ["eu-west-2a", "eu-west-2b", "eu-west-2c"],
    },
    "eu-west-3": {
        "vpc_service_name": "com.amazonaws.vpce.eu-west-3.vpce-svc-0d6912d10db9693d1",
        "private_domain_name": "vpce.eu-west-3.aws.elastic-cloud.com",
        "az_names": ["eu-west-3a", "eu-west-3b", "eu-west-3c"],
    },
    "me-south-1": {
        "vpc_service_name": "com.amazonaws.vpce.me-south-1.vpce-svc-0381de3eb670dcb48",
        "private_domain_name": "vpce.me-south-1.aws.elastic-cloud.com",
        "az_names": ["me-south-3a", "me-south-3b", "me-south-3c"],
    },
    "sa-east-1": {
        "vpc_service_name": "com.amazonaws.vpce.sa-east-1.vpce-svc-0b2dbce7e04dae763",
        "private_domain_name": "vpce.sa-east-1.aws.elastic-cloud.com",
        "az_names": ["sa-east-1a", "sa-east-1b", "sa-east-1c"],
    },
    "us-east-1": {
        "vpc_service_name": "com.amazonaws.vpce.us-east-1.vpce-svc-0e42e1e06ed010238",
        "private_domain_name": "vpce.us-east-1.aws.elastic-cloud.com",
        "az_names": ["us-east-1a", "us-east-1b", "us-east-1e"],
    },
    "us-east-2": {
        "vpc_service_name": "com.amazonaws.vpce.us-east-2.vpce-svc-02d187d2849ffb478",
        "private_domain_name": "vpce.us-east-2.aws.elastic-cloud.com",
        "az_names": ["us-east-2a", "us-east-2b", "us-east-2c"],
    },
    "us-west-1": {
        "vpc_service_name": "com.amazonaws.vpce.us-west-1.vpce-svc-00def4a16a26cb1b4",
        "private_domain_name": "vpce.us-west-1.aws.elastic-cloud.com",
        "az_names": ["us-west-1a", "us-west-1b", "us-west-1c"],
    },
    "us-west-2": {
        "vpc_service_name": "com.amazonaws.vpce.us-west-2.vpce-svc-0e69febae1fb91870",
        "private_domain_name": "vpce.us-west-2.aws.elastic-cloud.com",
        "az_names": ["us-west-2a", "us-west-2b", "us-west-2c"],
    },
}

ELASTIC_SERVICE_BASE_URL = "https://api.elastic-cloud.com/api/v1"


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