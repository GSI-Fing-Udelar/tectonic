
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

locals {
  tectonic = jsondecode(var.tectonic_json)
  guest_data  = jsondecode(var.guest_data_json)
  subnetworks = jsondecode(var.subnets_json)
  os_data = jsondecode(var.os_data_json)
  guest_basenames = distinct([for g in local.guest_data : g.base_name])
  network_config = { for k, g in local.guest_data :
    k => join("\n", flatten(["version: 2", "ethernets:",
      [ for interface in g.interfaces:
	[ "  ens${interface.index}:",
	  "    dhcp4: yes",
	]
      ]]))
  }
}
