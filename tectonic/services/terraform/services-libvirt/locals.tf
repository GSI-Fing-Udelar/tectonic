
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
  guest_data  = jsondecode(var.guest_data_json)
  subnetworks = jsondecode(var.subnets_json)
  os_data = jsondecode(var.os_data_json)
  guest_basenames = distinct([for g in local.guest_data : g.base_name])
  network_config = { for k, g in local.guest_data :
    k => join("\n", flatten(["version: 2", "ethernets:",
      [ for interface in g.interfaces:
	[ "  ens${interface.index}:",
	  "    dhcp4: yes",
    #"    nameserver:\n    addresses: [ ${cidrhost(local.subnetworks[interface.subnetwork_name]["cidr"],1)} ]"
	]
      ]]))
  }
  #network_config = "  ens3:\n    dhcp: yes\n    nameservers:\n    addresses: [ ${cidrhost(var.internet_network,1)} ]\n  ens4:\n    dhcp: yes"
  #format("    addresses: [%s/%s]", cidrhost(var.libvirt_external_network, var.libvirt_bridge_base_ip+g.entry_point_index), split("/", var.libvirt_external_network)[1]),
	#format("    gateway4: %s", cidrhost(var.libvirt_external_network, 1)),
  #    ] : [],
}
