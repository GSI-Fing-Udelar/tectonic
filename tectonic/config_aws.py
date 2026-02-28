
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

import tectonic.validate as validate

class TectonicConfigAWS(object):
    """Class to store Tectonic AWS configuration."""

    def __init__(self):
        self.region = "us-east-1"
        self.teacher_access = "host"
        self.access_host_instance_type = "t2.micro"
        self.packetbeat_vlan_id = 1

    #----------- Getters ----------
    @property
    def region(self):
        return self._region

    @property
    def teacher_access(self):
        return self._teacher_access

    @property
    def access_host_instance_type(self):
        return self._access_host_instance_type

    @property
    def packetbeat_vlan_id(self):
        return self._packetbeat_vlan_id

    #----------- Setters ----------
    @region.setter
    def region(self, value):
        validate.regex("region", value, r"^[a-z]{2}-[a-z]+-[0-9]+$")
        self._region = value

    @teacher_access.setter
    def teacher_access(self, value):
        validate.supported_value("teacher_access", value, ["host", "endpoint"])
        self._teacher_access = value

    @access_host_instance_type.setter
    def access_host_instance_type(self, value):
        validate.regex("access_host_instance_type", value, r"[a-zA-Z0-9-]+.[a-zA-Z0-9-]+")
        self._access_host_instance_type = value


    @packetbeat_vlan_id.setter
    def packetbeat_vlan_id(self, value):
        validate.number("packetbeat_vlan_id", value, min_value=1, max_value=4094)
        self._packetbeat_vlan_id = value

    def to_dict(self):
        return {
            "region": self.region,
            "teacher_access": self.teacher_access,
            "access_host_instance_type": self.access_host_instance_type,
            "packetbeat_vlan_id": self.packetbeat_vlan_id,
        }