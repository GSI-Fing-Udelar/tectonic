
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

class TectonicConfigCaldera(object):
    """Class to store Tectonic caldera configuration."""

    def __init__(self):
        self.version = "latest"
        self.ot_enabled = False
        self.internal_port = 8443
        self.external_port = 8443


    #----------- Getters ----------
    @property
    def version(self):
        return self._version
    
    @property
    def ot_enabled(self):
        return self._ot_enabled
    
    @property
    def internal_port(self):
        return self._internal_port
    
    @property
    def external_port(self):
        return self._external_port

    #----------- Setters ----------
    @version.setter
    def version(self, value):
        # Allow either master or latest
        if value != 'master':
            validate.version_number("caldera version", value)
        if value == "latest":
            value = "master"
        self._version = value

    @ot_enabled.setter
    def ot_enabled(self, value):
        validate.boolean("caldera ot enabled", value)
        self._ot_enabled = value

    @internal_port.setter
    def internal_port(self, value):
        validate.number("Caldera internal port", value)
        self._internal_port = value

    @external_port.setter
    def external_port(self, value):
        validate.number("Caldera external port", value)
        self._external_port = value

    def to_dict(self):
        return {
            "version": self.version,
            "ot_enabled": self.ot_enabled,
            "internal_port": self.internal_port,
            "external_port": self.external_port,
        }
