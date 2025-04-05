
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
from tectonic.utils import absolute_path

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

    config_attrs = [a for a in dir(config) if isinstance(getattr(config.__class__, a, None), property) and 
                    (getattr(config.__class__, a).fset is not None)]

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
    filename = Path(test_data_path).joinpath("config", "tectonic1.ini")
    config = TectonicConfig.load(filename)

    parser = ConfigParser()
    parser.read(filename)

    default_config = TectonicConfig(parser['config']['lab_repo_uri'])
    
    def assert_attr_eq(config_obj, config_parser, key):
        if isinstance(getattr(config_obj, key), bool):
            assert getattr(config_obj, key) == config_parser.getboolean(key)
        else:
            assert str(getattr(config_obj, key)) == config_parser[key]
    for config_obj, config_parser in [(config, parser['config']),
                                      (config.ansible, parser['ansible']),
                                      (config.aws, parser['aws']),
                                      (config.libvirt, parser['libvirt']),
                                      (config.docker, parser['docker']),
                                      (config.elastic, parser['elastic']),
                                      (config.caldera, parser['caldera'])
                                      ]:
        # For each TectonicConfig attribute, test that the value is
        # equal to the ini if it exists, or the default value.
        for key in [a for a in dir(config_obj) if isinstance(getattr(config_obj.__class__, a, None), property) and 
                    (getattr(config_obj.__class__, a).fset is not None)]:
            if key in config_parser:
                # Paths are made absolute, so check that they are changed accordingly.
                if key in ["lab_repo_uri", "ssh_public_key_file"]:
                    assert str(getattr(config_obj, key)) == absolute_path(config_parser[key], base_dir=config.tectonic_dir)
                else:
                    assert_attr_eq(config_obj, config_parser, key)
            else:
                assert getattr(config_obj, key) == getattr(default_config, key)

    
def test_tectonic_unrecognized_option(test_data_path):
    config = TectonicConfig(lab_repo_uri)
    filename = Path(test_data_path).joinpath("config", "tectonic2.ini")
    with pytest.raises(ValueError) as exception:
        config = TectonicConfig.load(filename)
