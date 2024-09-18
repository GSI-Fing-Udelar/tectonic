
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

#Create subnetworks
resource "docker_network" "subnets" {
  for_each = local.subnetworks

  name = "${each.key}"
  driver = "bridge"
  internal = true
  ipam_config {
    subnet = each.value
  }

}

# Create the machines
resource "docker_container" "machines" {
  for_each = local.guest_data

  name  = each.key
  image = data.docker_image.base_images[each.value.base_name].id
  
  memory = lookup(each.value, "memory", "1024")
  memory_swap = 2048
  # TODO: limit cpu resources
  # cpu_set = "0-${lookup(each.value, "vcpu", "1")}"
  # TODO: not working for all filesystems, see https://github.com/moby/moby/issues/46823 (not working on MacOS)
  # storage_opts = {
  #   "size":"${lookup(each.value, "disk", 10)}G"
  # }

  hostname = each.value.hostname

  upload {
    file = "/home/${local.os_data[each.value.base_os]["username"]}/.ssh/authorized_keys"
    content = var.authorized_keys
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

#TODO: DNS