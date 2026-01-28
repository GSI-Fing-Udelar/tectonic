
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

  # Compute cloud init network config.
  # Configure one static IP if the guest is an entry point, and 
  # the necessary internal interfaces with dhcp.
  network_config = { for k, g in local.guest_data :
    k => join("\n", flatten(["version: 2", "ethernets:",
      g.entry_point && local.tectonic.enable_ssh_access ? 
      [
	      format("  %s%s:", local.os_data[g.base_os]["interface_base_name"], local.os_data[g.base_os]["interface_base_name"] == "eth" ? 0 : 3 ), 
	      format("    addresses: [%s/%s]", 
          cidrhost(local.tectonic.config.platforms.libvirt.external_network, local.tectonic.config.platforms.libvirt.bridge_base_ip+g.entry_point_index), 
          split("/", local.tectonic.config.platforms.libvirt.external_network)[1]
        ),
      ] : [],
      g.internet_access ?
      [
	      format("  %s%s:", local.os_data[g.base_os]["interface_base_name"], 
        g.entry_point && local.tectonic.enable_ssh_access 
        ? 
          (local.os_data[g.base_os]["interface_base_name"] == "eth" ? 1 : 4)
        : 
          (local.os_data[g.base_os]["interface_base_name"] == "eth" ? 0 : 3)
        ), 
        "    dhcp4: yes",
        "    dhcp4-overrides:",
        "      use-routes: false",
        "    routes:",
        "      - to: 0.0.0.0/0",
        format("        via: %s", cidrhost(local.tectonic.config.internet_network_cidr_block, 1)),
      ] : [],
      g.is_in_services_network ?
      [
        format("  %s%s:", local.os_data[g.base_os]["interface_base_name"], 
        g.entry_point && local.tectonic.enable_ssh_access 
        ? 
          (
            g.internet_access
            ?
              (local.os_data[g.base_os]["interface_base_name"] == "eth" ? 2 : 5)
            :
              (local.os_data[g.base_os]["interface_base_name"] == "eth" ? 1 : 4)
          ) 
        : 
          (
            g.internet_access
            ?
              (local.os_data[g.base_os]["interface_base_name"] == "eth" ? 1 : 4)
            :
              (local.os_data[g.base_os]["interface_base_name"] == "eth" ? 0 : 3)
          )
        ),
        "    dhcp4: yes",
        "    dhcp4-overrides:",
        "      use-routes: false",
        "    routes:",
        format("      - to: %s", local.tectonic.config.services_network_cidr_block),
        format("        via: %s", cidrhost(local.tectonic.config.services_network_cidr_block, 1)),
      ] : [],
      [ for interface in g.interfaces:
        [ format("  %s%s:", local.os_data[g.base_os]["interface_base_name"], interface.index),
          "    dhcp4: yes",
          "    dhcp4-overrides:",
          "      use-routes: false",
          "    routes:",
          format("      - to: %s", local.tectonic.config.network_cidr_block),
          format("        via: %s", cidrhost(interface.subnetwork_cidr,1)),
        ]
      ]
    ]))
  }


  internet_access = length([for g in local.guest_data : g if g.internet_access]) > 0

  dns_data = { for record in flatten(
    [for guest in local.guest_data :
      [for network_interface in guest.interfaces :
        {
          name    = guest.hostname
          network = network_interface.subnetwork_name
          ip      = network_interface.private_ip
        }
      ]
    ]) :
    format("%s-%s", record.name, record.network) => record
  }

}
