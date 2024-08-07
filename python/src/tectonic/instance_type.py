
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


class InstanceType:
    """This class encapsulates different machine sizes for different
    cloud providers.

    """
    
    def __init__(self, default_instance_type=None):
        self.default_instance_type = default_instance_type

    def get_guest_instance_type(self, memory, vcpus, monitor, monitor_type):
        """Default is to not have an instance type. Platform dependent
        subclasses will compute the correct instance type for the
        machine.

        """
        return self.default_instance_type
