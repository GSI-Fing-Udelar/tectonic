
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

class TectonicConfigDocker(object):
    """Class to store Tectonic docker configuration."""

    def __init__(self):
        self.uri = "unix:///var/run/docker.sock"
        self.dns = "8.8.8.8"


    #----------- Getters ----------
    @property
    def uri(self):
        return self._uri

    @property
    def dns(self):
        return self._dns


    #----------- Setters ----------
    @uri.setter
    def uri(self, value):
        self._uri = value

    @dns.setter
    def dns(self, value):
        validate.ip_address_or_hostname("dns", value)
        self._dns = value
