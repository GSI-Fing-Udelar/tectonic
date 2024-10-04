
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

  network_interfaces = { for interface in flatten(
    [for g in local.guest_data :
      [for key, value in g.interfaces : value]
    ]) :
    interface.name => interface
  }

  network_names = distinct(
    [for key, interface in local.network_interfaces :
      interface.network_name
  ])

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

  interfaces_to_mirror = { for interface_data in flatten(
    [for i, interface in data.aws_network_interface.interface : {
      interface_name : interface.tags.Name,
      interface_id : interface.id
      }
      if can(regex("^${var.institution}-${var.lab_name}-\\d+-(${join("|", var.machines_to_monitor)})(-\\d+)?-\\d+$", interface.tags.Name)) && var.monitor && var.monitor_type == "traffic"
    ]) : interface_data.interface_name => interface_data
  }

}
