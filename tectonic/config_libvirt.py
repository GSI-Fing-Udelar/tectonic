
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

class TectonicConfigLibvirt(object):
    """Class to store Tectonic libvirt configuration."""

    def __init__(self):
        self._uri = "qemu:///system"
        self._storage_pool = "default"
        self._student_access = "port_forwarding"
        self._bridge = "tectonic"
        self._external_network = "192.168.0.0/25"
        self._bridge_base_ip = 10


    #----------- Getters ----------
    @property
    def uri(self):
        return self._uri

    @property
    def storage_pool(self):
        return self._storage_pool

    @property
    def student_access(self):
        return self._student_access

    @property
    def bridge(self):
        return self._bridge

    @property
    def external_network(self):
        return self._external_network

    @property
    def bridge_base_ip(self):
        return self._bridge_base_ip



    #----------- Setters ----------
    @uri.setter
    def uri(self, value):
        self._uri = value

    @storage_pool.setter
    def storage_pool(self, value):
        self._storage_pool = value

    @student_access.setter
    def student_access(self, value):
        self._student_access = value

    @bridge.setter
    def bridge(self, value):
        self._bridge = value

    @external_network.setter
    def external_network(self, value):
        self._external_network = value

    @bridge_base_ip.setter
    def bridge_base_ip(self, value):
        self._bridge_base_ip = value


    def __eq__(self, other): 
        if not isinstance(other, TectonicConfigLibvirt):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return (self._uri == other._uri and 
                self._storage_pool == other._storage_pool and 
                self._bridge == other._bridge and 
                self._external_network == other._external_network and
                self._bridge_base_ip == other._bridge_base_ip
                )
