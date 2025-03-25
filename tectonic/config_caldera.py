
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

class TectonicConfigCaldera(object):
    """Class to store Tectonic caldera configuration."""

    def __init__(self):
        self._version = "latest"


    #----------- Getters ----------
    @property
    def version(self):
        return self._version


    #----------- Setters ----------
    @version.setter
    def version(self, value):
        # TODO - validate
        self._version = value

    def __eq__(self, other): 
        if not isinstance(other, TectonicConfigCaldera):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self._version == other._version
