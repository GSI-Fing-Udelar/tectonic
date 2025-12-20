
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

class TectonicConfigAnsible(object):
    """Class to store Tectonic ansible configuration."""

    def __init__(self):
        self.ssh_common_args = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=3600 "
        self.keep_logs = False
        self.forks = 5
        self.pipelining = False
        self.timeout = 10


    #----------- Getters ----------
    @property
    def ssh_common_args(self):
        return self._ssh_common_args

    @property
    def keep_logs(self):
        return self._keep_logs

    @property
    def forks(self):
        return self._forks

    @property
    def pipelining(self):
        return self._pipelining

    @property
    def timeout(self):
        return self._timeout


    #----------- Setters ----------
    @ssh_common_args.setter
    def ssh_common_args(self, value):
        self._ssh_common_args = value

    @keep_logs.setter
    def keep_logs(self, value):
        validate.boolean("keep_logs", value)
        self._keep_logs = value

    @forks.setter
    def forks(self, value):
        validate.number("forks", value, min_value=1)
        self._forks = value

    @pipelining.setter
    def pipelining(self, value):
        validate.boolean("pipelining", value)
        self._pipelining = value

    @timeout.setter
    def timeout(self, value):
        validate.number("timeout", value, min_value=1)
        self._timeout = value

    def to_dict(self):
        return {
            "ssh_common_args": self.ssh_common_args,
            "keep_logs": self.keep_logs,
        }
