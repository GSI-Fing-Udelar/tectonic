
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

class TectonicConfigLibvirt(object):
    """Class to store Tectonic libvirt configuration."""

    # supported_student_access = ["bridge", "port_forwarding"]
    supported_student_access = ["bridge"]

    def __init__(self):
        self.uri = "qemu:///system"
        self.storage_pool = "default"
        self.student_access = self.supported_student_access[0]
        self.bridge = "tectonic"
        self.external_network = "192.168.0.0/25"
        self.bridge_base_ip = 10
        self.routing = False


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

    @property
    def routing(self):
        return self._routing

    #----------- Setters ----------
    @uri.setter
    def uri(self, value):
        self._uri = value

    @storage_pool.setter
    def storage_pool(self, value):
        self._storage_pool = value

    @student_access.setter
    def student_access(self, value):
        validate.supported_value("student_access", value, self.supported_student_access)
        self._student_access = value

    @bridge.setter
    def bridge(self, value):
        self._bridge = value

    @external_network.setter
    def external_network(self, value):
        validate.ip_network("external_network", value)
        self._external_network = value

    @bridge_base_ip.setter
    def bridge_base_ip(self, value):
        validate.number("bridge_base_ip", value, min_value=5, max_value=254)
        self._bridge_base_ip = value

    @routing.setter
    def routing(self, value):
        validate.boolean("routing", value)
        self._routing = value

    def to_dict(self):
        return {
            "uri": self.uri,
            "storage_pool" : self.storage_pool,
            "external_network": self.external_network,
            "bridge": self.bridge,
            "bridge_base_ip": self.bridge_base_ip,
            "routing": self.routing
        }
