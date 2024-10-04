
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

  # Compute cloud init network config.
  # Configure one static IP if the guest is an entry point, and 
  # the necessary internal interfaces with dhcp.
  network_config = { for k, g in local.guest_data :
    k => join("\n", flatten(["version: 2", "ethernets:",
      g.entry_point ? [
	"  ens3:", 
	format("    addresses: [%s/%s]", cidrhost(var.libvirt_external_network, var.libvirt_bridge_base_ip+g.entry_point_index), split("/", var.libvirt_external_network)[1]),
	format("    gateway4: %s", cidrhost(var.libvirt_external_network, 1)),
      ] : [],
      g.is_in_services_network ? [
  "  ens${g.entry_point ? 4 : 3}:", 
	format("    addresses: [%s/%s]", cidrhost(var.services_network, var.services_network_base_ip+g.services_network_index), split("/", var.services_network)[1])
      ] : [],
      [ for interface in g.interfaces:
	[ "  ens${interface.index}:",
	  "    dhcp4: yes",
	]
      ]]))
  }


  internet_access = length([for g in local.guest_data : g if g.internet_access]) > 0

  dns_data = { for record in flatten(
    [for guest in local.guest_data :
      [for network_interface in guest.interfaces :
        {
          name    = guest.hostname
          network = network_interface.network_name
          ip      = network_interface.private_ip
        }
      ]
    ]) :
    format("%s-%s", record.name, record.network) => record
  }

}
