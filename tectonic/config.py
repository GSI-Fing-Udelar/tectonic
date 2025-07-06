
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
from configparser import ConfigParser
import tectonic.validate as validate
from tectonic.utils import absolute_path

from tectonic.config_ansible import TectonicConfigAnsible
from tectonic.config_aws import TectonicConfigAWS
from tectonic.config_libvirt import TectonicConfigLibvirt
from tectonic.config_docker import TectonicConfigDocker
from tectonic.config_elastic import TectonicConfigElastic
from tectonic.config_caldera import TectonicConfigCaldera

class TectonicConfig(object):
    """Class to store Tectonic configuration."""

    supported_platforms = ["aws", "libvirt", "docker"]

    def __init__(self, lab_repo_uri):
        self._tectonic_dir = os.path.realpath(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), "../")
        )

        # Set default config values
        self.lab_repo_uri = lab_repo_uri
        self.platform = self.supported_platforms[0]
        self.network_cidr_block = "10.0.0.0/16"
        self.internet_network_cidr_block = "192.168.4.0/24"
        self.services_network_cidr_block = "192.168.5.0/24"
        self.ssh_public_key_file = "~/.ssh/id_rsa.pub"
        self.configure_dns = False
        self.debug = False
        self.proxy = None
        self.gitlab_backend_url = None
        self.gitlab_backend_username = None
        self.gitlab_backend_access_token = None
        self.packer_executable_path = "packer"
        self.routing = False

        self._ansible = TectonicConfigAnsible()
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
    def tectonic_dir(self):
        return self._tectonic_dir

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
    def configure_dns(self):
        return self._configure_dns

    @property
    def debug(self):
        return self._debug

    @property
    def proxy(self):
        return self._proxy

    @property
    def gitlab_backend_url(self):
        return self._gitlab_backend_url

    @property
    def gitlab_backend_username(self):
        return self._gitlab_backend_username

    @property
    def gitlab_backend_access_token(self):
        return self._gitlab_backend_access_token

    @property
    def packer_executable_path(self):
        return self._packer_executable_path

    @property
    def routing(self):
        return self._routing

    @property
    def ansible(self):
        return self._ansible

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
        validate.supported_value("platform", value, self.supported_platforms)
        self._platform = value

    @lab_repo_uri.setter
    def lab_repo_uri(self, value):
        # This must be a local path to a directory for now. In the
        # future, it might be a uri to a scenario repository.
        value = absolute_path(value, base_dir=self.tectonic_dir)
        validate.path_to_dir("lab_repo_uri", value)
        self._lab_repo_uri = value

    @network_cidr_block.setter
    def network_cidr_block(self, value):
        validate.ip_network("network_cidr_block", value)
        self._network_cidr_block = value

    @internet_network_cidr_block.setter
    def internet_network_cidr_block(self, value):
        validate.ip_network("internet_network_cidr_block", value)
        self._internet_network_cidr_block = value

    @services_network_cidr_block.setter
    def services_network_cidr_block(self, value):
        validate.ip_network("services_network_cidr_block", value)
        self._services_network_cidr_block = value

    @ssh_public_key_file.setter
    def ssh_public_key_file(self, value):
        value = absolute_path(value, base_dir=self.tectonic_dir)
        validate.path_to_file("ssh_public_key_file", value)
        self._ssh_public_key_file = value

    @configure_dns.setter
    def configure_dns(self, value):
        validate.boolean("configure_dns", value)
        self._configure_dns = value

    @debug.setter
    def debug(self, value):
        validate.boolean("debug", value)
        self._debug = value

    @proxy.setter
    def proxy(self, value):
        if value:
            validate.url("proxy", value)
        else:
            value = None
        self._proxy = value


    @gitlab_backend_url.setter
    def gitlab_backend_url(self, value):
        if value is not None:
            validate.url("gitlab_backend_url", value)
        self._gitlab_backend_url = value

    @gitlab_backend_username.setter
    def gitlab_backend_username(self, value):
        self._gitlab_backend_username = value

    @gitlab_backend_access_token.setter
    def gitlab_backend_access_token(self, value):
        self._gitlab_backend_access_token = value

    @packer_executable_path.setter
    def packer_executable_path(self, value):
        # validate.path_to_file("packer_executable_path", value)
        self._packer_executable_path = value

    @routing.setter
    def routing(self, value):
        validate.boolean("routing", value)
        self._routing = value

    @classmethod
    def _assign_attribute(cls, config_obj, config_parser, key):
        """Assign the value of name key in the parser object to the corresponding config attribute."""
        # Fail if the option is not a valid TectonicConfig attribute
        config_attrs = [a for a in dir(config_obj) if isinstance(getattr(config_obj.__class__, a, None), property) and 
                        (getattr(config_obj.__class__, a).fset is not None)]
        if key not in config_attrs:
            raise ValueError(f"Unrecognized configuration option {key}.")

        if isinstance(getattr(config_obj, key), bool):
            setattr(config_obj, key, config_parser.getboolean(key))
        else:
            setattr(config_obj, key, config_parser.get(key))

    @classmethod
    def load(cls, filename):
        """Creates a TectonicConfig object from an ini configuration in filename."""

        f = open(filename, "r")
        parser = ConfigParser()
        parser.read_file(f)
        config = TectonicConfig(parser['config']['lab_repo_uri'])

        for key in parser['config'].keys():
            TectonicConfig._assign_attribute(config, parser['config'], key)
        for key in parser['ansible'].keys():
            TectonicConfig._assign_attribute(config.ansible, parser['ansible'], key)
        for key in parser['aws'].keys():
            TectonicConfig._assign_attribute(config.aws, parser['aws'], key)
        for key in parser['libvirt'].keys():
            TectonicConfig._assign_attribute(config.libvirt, parser['libvirt'], key)
        for key in parser['docker'].keys():
            TectonicConfig._assign_attribute(config.docker, parser['docker'], key)
        for key in parser['elastic'].keys():
            TectonicConfig._assign_attribute(config.elastic, parser['elastic'], key)
        for key in parser['caldera'].keys():
            TectonicConfig._assign_attribute(config.caldera, parser['caldera'], key)

        return config
