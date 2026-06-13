
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

class TectonicConfigBastionHost(object):
    """Class to store Tectonic bastion host configuration."""

    def __init__(self):
        self.domain = "tectonic.cyberrange.com"
        self.external_port = 443

    #----------- Getters ----------
    @property
    def domain(self):
        return self._domain

    @property
    def external_port(self):
        return self._external_port
    
    #----------- Setters ----------
    @domain.setter
    def domain(self, value):
        self._domain = value

    @external_port.setter
    def external_port(self, value):
        validate.number("Bastion Host external port", value)
        self._external_port = value

    def to_dict(self):
        return {
            "domain": self.domain,
            "external_port": self.external_port,
        }