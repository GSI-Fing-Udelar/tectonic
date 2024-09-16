
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

from tectonic.instance_type import InstanceType

class InstanceTypeAWS(InstanceType):

    instance_type_details = {
        "t2": [
            {"instance_type": "t2.nano", "vcpus": 1, "memory": 512},
            {"instance_type": "t2.micro", "vcpus": 1, "memory": 1024},
            {"instance_type": "t2.small", "vcpus": 1, "memory": 2048},
            {"instance_type": "t2.medium", "vcpus": 2, "memory": 4096},
            {"instance_type": "t2.large", "vcpus": 2, "memory": 8192},
            {"instance_type": "t2.xlarge", "vcpus": 4, "memory": 16384},
            {"instance_type": "t2.2xlarge", "vcpus": 8, "memory": 32768},
        ],
        "t3": [
            {"instance_type": "t3.nano", "vcpus": 2, "memory": 512},
            {"instance_type": "t3.micro", "vcpus": 2, "memory": 1024},
            {"instance_type": "t3.small", "vcpus": 2, "memory": 2048},
            {"instance_type": "t3.medium", "vcpus": 2, "memory": 4096},
            {"instance_type": "t3.large", "vcpus": 2, "memory": 8192},
            {"instance_type": "t3.xlarge", "vcpus": 4, "memory": 16384},
            {"instance_type": "t3.2xlarge", "vcpus": 8, "memory": 32768},
        ],
    }

    def get_guest_instance_type(self, memory, vcpus, monitor, monitor_type):
        """Returns a big enough AWS instance type for the given memory
        and cpus.

        A t2 instance will be used, unless monitor traffic is true, in
        which case a t3 instance will be used.

        If no suitable instance type can be used, None is returned.

        """
        if (
            not memory
            and not vcpus
        ):
            if monitor and monitor_type == "traffic":
                return self.default_instance_type.replace("t2.", "t3.")
            else:
                return self.default_instance_type

        if monitor and monitor_type == "traffic":
            instances = self.instance_type_details["t3"]
            selected_type = "t3"
        else:
            instances = self.instance_type_details["t2"]
            selected_type = "t2"

        for i in instances:
            if memory is None or memory <= i.get("memory"):
                if vcpus is None or vcpus <= i.get("vcpus"):
                    return i.get("instance_type")
        return f"{selected_type}.2xlarge"
