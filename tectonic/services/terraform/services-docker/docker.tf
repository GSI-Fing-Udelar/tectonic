
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

# Base images already exist, here we create a volume for each
# guest, using the base image as a template

#Create services networks
resource "docker_network" "subnets" {
  for_each = local.subnetworks

  name = "${each.key}"
  driver = "bridge"
  internal = false # The correct approach would be to use the following: "${lookup(each.value, "mode")}" != "nat" so that only the internet network has internet access. But port forwarding does not work with internal networks. Therefore, the service network cannot be internal.
  ipam_config {
    subnet = lookup(each.value, "cidr")
  }

}

# Create services machines
resource "docker_container" "machines" {
  for_each = local.guest_data

  name  = each.key
  image = data.docker_image.base_images[each.value.base_name].id
  
  memory = lookup(each.value, "memory", "1024")
  
  hostname = each.value.base_name

  dynamic "ports" {
    for_each = each.value.ports
    content {
      internal = ports.value
      external = ports.value
      ip = "127.0.0.1"
      protocol = "tcp"
    }
  }

  upload {
    file = "/home/${local.os_data[each.value.base_os]["username"]}/.ssh/authorized_keys"
    content = local.tectonic.authorized_keys
  }
  
  privileged = true
  
  network_mode = "bridge"
  dynamic "networks_advanced" {
    for_each = each.value.interfaces
    content {
      name = docker_network.subnets[networks_advanced.value.subnetwork_name].id
      ipv4_address = networks_advanced.value.private_ip
    }
  }
}