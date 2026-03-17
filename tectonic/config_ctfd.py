
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

class TectonicConfigCtfd(object):
    """Class to store Tectonic Ctfd configuration."""

    def __init__(self):
        self.version = "3.8.2"
        self.internal_port = 8443
        self.external_port = 8090
        self.admin_email = "admin@tectonic.local"

    @property
    def version(self):
        return self._version
    
    @property
    def internal_port(self):
        return self._internal_port
    
    @property
    def external_port(self):
        return self._external_port

    @property
    def admin_email(self):
        return self._admin_email
    
    @version.setter
    def version(self, value):
        validate.version_number("Ctfd version", value)
        if value == "latest":
            value = "master"
        self._version = value

    @internal_port.setter
    def internal_port(self, value):
        validate.number("Ctfd internal port", value)
        self._internal_port = value

    @external_port.setter
    def external_port(self, value):
        validate.number("Ctfd external port", value)
        self._external_port = value

    @admin_email.setter
    def admin_email(self, value):
        self._admin_email = value

    def to_dict(self):
        return {
            "version": self.version,
            "internal_port": self.internal_port,
            "external_port": self.external_port,
        }
