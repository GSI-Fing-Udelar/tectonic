
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

class TectonicConfigGuacamole(object):
    """Class to store Tectonic guacamole configuration."""

    def __init__(self):
        self._version = "1.6.0"
        self._brute_force_protection_enabled = False
        self._internal_port = 10443
        self._external_port = 443

    #----------- Getters ----------
    @property
    def version(self):
        return self._version
    
    @property
    def brute_force_protection_enabled(self):
        return self._brute_force_protection_enabled

    @property
    def internal_port(self):
        return self._internal_port
    
    @property
    def external_port(self):
        return self._external_port
    
    #----------- Setters ----------
    @version.setter
    def version(self, value):
        # Allow either latest or specific version
        if value != 'latest':
            validate.version_number("caldera version", value)
        if value == "latest":
            value = "1.6.0"
        self._version = value

    @brute_force_protection_enabled.setter
    def brute_force_protection_enabled(self, value):
        validate.boolean("Guacamole brute force protection enabled", value)
        self._brute_force_protection_enabled = value

    @internal_port.setter
    def internal_port(self, value):
        validate.number("Guacamole internal port", value)
        self._internal_port = value

    @external_port.setter
    def external_port(self, value):
        validate.number("Guacamole external port", value)
        self._external_port = value