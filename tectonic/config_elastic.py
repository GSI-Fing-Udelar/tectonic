
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

class TectonicConfigElastic(object):
    """Class to store Tectonic elastic configuration."""

    def __init__(self):
        self.elastic_stack_version = "8.14.3"
        self.packetbeat_policy_name = "Packetbeat"
        self.endpoint_policy_name = "Endpoint"
        self.user_install_packetbeat = "tectonic"


    #----------- Getters ----------
    @property
    def elastic_stack_version(self):
        return self._elastic_stack_version

    @property
    def packetbeat_policy_name(self):
        return self._packetbeat_policy_name

    @property
    def endpoint_policy_name(self):
        return self._endpoint_policy_name

    @property
    def user_install_packetbeat(self):
        return self._user_install_packetbeat


    #----------- Setters ----------
    @elastic_stack_version.setter
    def elastic_stack_version(self, value):
        validate.version_number("elastic_stack_version", value)
        self._elastic_stack_version = value

    @packetbeat_policy_name.setter
    def packetbeat_policy_name(self, value):
        self._packetbeat_policy_name = value

    @endpoint_policy_name.setter
    def endpoint_policy_name(self, value):
        self._endpoint_policy_name = value

    @user_install_packetbeat.setter
    def user_install_packetbeat(self, value):
        self._user_install_packetbeat = value

    def __eq__(self, other): 
        if not isinstance(other, TectonicConfigElastic):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (self._elastic_stack_version == other._elastic_stack_version and 
                self._packetbeat_policy_name == other._packetbeat_policy_name and 
                self._endpoint_policy_name == other._endpoint_policy_name and 
                self._user_install_packetbeat == other._user_install_packetbeat
                )
