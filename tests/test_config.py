
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

import pytest
from pathlib import Path
from configparser import ConfigParser

from tectonic.config import TectonicConfig

lab_repo_uri = "./examples"

valid_options = [
    { 
    },
    { 
        "proxy": None,
    },
    { 
        "platform": "docker",
        "network_cidr_block": "10.0.0.0/16",
        "internet_network_cidr_block": "10.0.0.0/25",
        "services_network_cidr_block": "10.0.0.128/25",
        "ssh_public_key_file": "~/.ssh/id_rsa.pub",
        "configure_dns": False,
        "debug": True,
        "proxy": "http://proxy.example.com:3128",
    },
]

invalid_options = [
    { 
        "platform": "invalid",
    },
    { 
        "network_cidr_block": "invalid",
    },
    { 
        "internet_network_cidr_block": "invalid",
    },
    { 
        "services_network_cidr_block": "invalid",
    },
    {
        "ssh_public_key_file": "invalid",
    },
    { 
        "proxy": "invalid",
    },
]


valid_aws_options = [
    {
    },
    { 
        "region": "eu-nowhere-1",
        "default_instance_type": "t2.huuuuge",
        "teacher_access": "endpoint",
        "packetbeat_vlan_id": "2",
    },
]


valid_libvirt_options = [
    {
    },
    { 
        "uri": "qemu+ssh://root@127.0.0.1/system", 
        "storage_pool": "tectonic",
        "student_access": "bridge",
        "bridge": "tectonic",
        "external_network": "192.168.128.0/25",
        "bridge_base_ip": 100,
    },
]

def test_tectonic_valid_lab_repo_uri():
    config = TectonicConfig(lab_repo_uri)
    assert config.lab_repo_uri == str(Path(config.tectonic_dir).joinpath(lab_repo_uri))
    config.lab_repo_uri = './tectonic'
    assert config.lab_repo_uri == str(Path(config.tectonic_dir).joinpath('./tectonic'))

def test_tectonic_invalid_lab_repo_uri():
    with pytest.raises(ValueError) as exception:
        config = TectonicConfig(None)


@pytest.mark.parametrize("option", valid_options)
def test_tectonic_valid_config(option):
    default_config = TectonicConfig(lab_repo_uri)

    config = TectonicConfig(lab_repo_uri)
    for key, value in option.items():
        setattr(config, key, value)

    config_attrs = [a for a in dir(config) if not a.startswith('_') and not callable(getattr(config, a))]

    assert config.lab_repo_uri == default_config.lab_repo_uri
    for key in config_attrs:
        if key in option.keys():
            if key == "ssh_public_key_file":
                assert getattr(config, key) == str(Path(option[key]).expanduser())
            else:
                assert getattr(config, key) == option[key]
        else:
            assert getattr(config, key) == getattr(default_config, key)


@pytest.mark.parametrize("option", invalid_options)
def test_tectonic_invalid_config(option):
    config = TectonicConfig(lab_repo_uri)
    with pytest.raises(ValueError) as exception:
        for key, value in option.items():
            setattr(config, key, value)

@pytest.mark.parametrize("option", valid_aws_options)
def test_tectonic_valid_aws_config(option):
    config = TectonicConfig(lab_repo_uri)
    for key, value in option.items():
        setattr(config.aws, key, value)

    for key, value in option.items():
        assert getattr(config.aws, key) == value


@pytest.mark.parametrize("option", valid_libvirt_options)
def test_tectonic_valid_libvirt_config(option):
    config = TectonicConfig(lab_repo_uri)
    for key, value in option.items():
        setattr(config.libvirt, key, value)

    for key, value in option.items():
        assert getattr(config.libvirt, key) == value


def test_load_config(test_data_path):
    filename = f"{test_data_path}/config/tectonic1.ini"
    config = TectonicConfig.load(filename)

    parser = ConfigParser()
    parser.read(filename)

    for key, value in parser['config'].items():
        if key == "lab_repo_uri":
            assert str(getattr(config, key)) == str(Path(config.tectonic_dir).joinpath(value))
        elif key in ["configure_dns", "debug"]:
            assert getattr(config, key) == (True if value == "yes" else False)
        else:
            assert str(getattr(config, key)) == value
    for key, value in parser['aws'].items():
        assert str(getattr(config.aws, key)) == value
    for key, value in parser['libvirt'].items():
        assert str(getattr(config.libvirt, key)) == value
    for key, value in parser['docker'].items():
        assert str(getattr(config.docker, key)) == value
    for key, value in parser['elastic'].items():
        assert str(getattr(config.elastic, key)) == value
    for key, value in parser['caldera'].items():
        assert str(getattr(config.caldera, key)) == value
    
