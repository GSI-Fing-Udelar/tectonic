
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

from tectonic.config import ConfigException

class TectonicConfigAWS(object):
    """Class to store Tectonic AWS configuration."""

    def __init__(self):
        self._region = "us-east-1"
        self._default_instance_type = "t2.micro"
        self._teacher_access = "host"
        self._packetbeat_vlan_id = 1

    #----------- Getters ----------
    @property
    def region(self):
        return self._region

    @property
    def default_instance_type(self):
        return self._default_instance_type

    @property
    def teacher_access(self):
        return self._teacher_access

    @property
    def packetbeat_vlan_id(self):
        return self._packetbeat_vlan_id

    #----------- Setters ----------
    @region.setter
    def region(self, value):
        self._region = value

    @default_instance_type.setter
    def default_instance_type(self, value):
        self._default_instance_type = value

    @teacher_access.setter
    def teacher_access(self, value):
        if value.lower() not in ["host", "endpoint"]: 
            raise ConfigException(f"Invalid teacher_access {value}. Must be 'host' or 'endpoint'.")
        self._teacher_access = value

    @packetbeat_vlan_id.setter
    def packetbeat_vlan_id(self, value):
        try:
            if int(value) <= 0 or int(value) > 4094: 
                raise ValueError()
        except ValueError:
            raise ConfigException(f"Invalid ansible_forks {value}. Must be a number between 1 and 4094.")
        self._packetbeat_vlan_id = value

