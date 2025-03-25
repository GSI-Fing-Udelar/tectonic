
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

import os
from pathlib import Path
from urllib.parse import urlparse
import ipaddress
from configparser import ConfigParser


class ConfigException(Exception):
    pass

from tectonic.config_aws import TectonicConfigAWS
from tectonic.config_libvirt import TectonicConfigLibvirt
from tectonic.config_docker import TectonicConfigDocker
from tectonic.config_elastic import TectonicConfigElastic
from tectonic.config_caldera import TectonicConfigCaldera


class TectonicConfig(object):
    """Class to store Tectonic configuration."""

    supported_platforms = ["aws", "libvirt", "docker"]

    def __init__(self, lab_repo_uri):
        if lab_repo_uri is None:
            raise ConfigException("lab_repo_uri is required.")

        # Set default config values
        self._platform = self.supported_platforms[0]
        self._lab_repo_uri = lab_repo_uri
        self._network_cidr_block = "10.0.0.0/16"
        self._internet_network_cidr_block = "192.168.4.0/24"
        self._services_network_cidr_block = "192.168.5.0/24"
        self._ssh_public_key_file = "~/.ssh/id_rsa.pub"
        self._ansible_ssh_common_args = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=3600"
        self._configure_dns = True
        self._debug = False
        self._proxy = None
        self._keep_ansible_logs = False
        self._ansible_forks = 10
        self._ansible_pipelining = False
        self._ansible_timeout = 10

        self._aws = TectonicConfigAWS()
        self._libvirt = TectonicConfigLibvirt()
        self._docker = TectonicConfigDocker()
        self._elastic = TectonicConfigElastic()
        self._caldera = TectonicConfigCaldera()


    #----------- Getters ----------
    @property
    def platform(self):
        return self._platform

    @property
    def lab_repo_uri(self):
        return self._lab_repo_uri

    @property
    def network_cidr_block(self):
        return self._network_cidr_block

    @property
    def internet_network_cidr_block(self):
        return self._internet_network_cidr_block

    @property
    def services_network_cidr_block(self):
        return self._services_network_cidr_block

    @property
    def ssh_public_key_file(self):
        return self._ssh_public_key_file

    @property
    def ansible_ssh_common_args(self):
        return self._ansible_ssh_common_args

    @property
    def configure_dns(self):
        return self._configure_dns

    @property
    def debug(self):
        return self._debug

    @property
    def keep_ansible_logs(self):
        return self._keep_ansible_logs

    @property
    def proxy(self):
        return self._proxy

    @property
    def ansible_forks(self):
        return self._ansible_forks

    @property
    def ansible_pipelining(self):
        return self._ansible_pipelining

    @property
    def ansible_timeout(self):
        return self._ansible_timeout


    @property
    def aws(self):
        return self._aws

    @property
    def libvirt(self):
        return self._libvirt

    @property
    def docker(self):
        return self._docker

    @property
    def elastic(self):
        return self._elastic

    @property
    def caldera(self):
        return self._caldera


    #----------- Setters ----------
    @platform.setter
    def platform(self, value):
        if value.lower() not in self.supported_platforms:
            raise ConfigException(f"Invalid platform {value}. Must be one of {self.supported_platforms}.")
        self._platform = value

    @lab_repo_uri.setter
    def lab_repo_uri(self, value):
        self._lab_repo_uri = value      

    @network_cidr_block.setter
    def network_cidr_block(self, value):
        try:
            ipaddress.ip_network(value)
        except ValueError:
            raise ConfigException(f"Invalid network_cidr_block {value}.")
        self._network_cidr_block = value

    @internet_network_cidr_block.setter
    def internet_network_cidr_block(self, value):
        try:
            ipaddress.ip_network(value)
        except ValueError:
            raise ConfigException(f"Invalid internet_network_cidr_block {value}.")
        self._internet_network_cidr_block = value
    @services_network_cidr_block.setter
    def services_network_cidr_block(self, value):
        try:
            ipaddress.ip_network(value)
        except ValueError:
            raise ConfigException(f"Invalid services_network_cidr_block {value}.")
        self._services_network_cidr_block = value

    @ssh_public_key_file.setter
    def ssh_public_key_file(self, value):
        p = Path(value).expanduser()
        if not p.is_file():
            raise ConfigException(f"Invalid ssh_public_key_file {value}. Must be a path to a file.")
        self._ssh_public_key_file = value

    @ansible_ssh_common_args.setter
    def ansible_ssh_common_args(self, value):
        self._ansible_ssh_common_args = value

    @configure_dns.setter
    def configure_dns(self, value):
        self._configure_dns = value

    @debug.setter
    def debug(self, value):
        self._debug = value

    @keep_ansible_logs.setter
    def keep_ansible_logs(self, value):
        self._keep_ansible_logs = value

    @proxy.setter
    def proxy(self, value):
        if value is not None:
            try:
                result = urlparse(value)
                if not all([result.scheme, result.netloc]):
                    raise AttributeError
            except AttributeError:
                raise ConfigException(f"Invalid proxy {value}. Must be a valid url.")
        self._proxy = value

    @ansible_forks.setter
    def ansible_forks(self, value):
        try:
            if int(value) <= 0: 
                raise ValueError()
        except ValueError:
            raise ConfigException(f"Invalid ansible_forks {value}. Must be a number greater than 0.")
        self._ansible_forks = value

    @ansible_pipelining.setter
    def ansible_pipelining(self, value):
        self._ansible_pipelining = value

    @ansible_timeout.setter
    def ansible_timeout(self, value):
        try:
            if int(value) <= 0: 
                raise ValueError()
        except ValueError:
            raise ConfigException(f"Invalid ansible_timeout {value}. Must be a number greater than 0.")
        self._ansible_timeout = value        
        


    def load(filename):
        f = open(filename, "r")
        parser = ConfigParser()
        parser.read_file(f)
        config = TectonicConfig(parser['config']['lab_repo_uri'])

        for key, value in parser['config'].items():
            setattr(config, key, value)
        for key, value in parser['aws'].items():
            setattr(config.aws, key, value)
        for key, value in parser['libvirt'].items():
            setattr(config.libvirt, key, value)
        for key, value in parser['docker'].items():
            setattr(config.docker, key, value)
        for key, value in parser['elastic'].items():
            setattr(config.elastic, key, value)
        for key, value in parser['caldera'].items():
            setattr(config.caldera, key, value)

        return config
