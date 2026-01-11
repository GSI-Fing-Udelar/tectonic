
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

resource "libvirt_volume" "cloned_image" {
  for_each = local.guest_data
  name     = "${each.key}"
  base_volume_name = "${each.value.base_name}"
  pool     = local.tectonic.config.platforms.libvirt.storage_pool
  format   = "qcow2"
  size     = (lookup(each.value, "disk", 10) * 1073741824)
}

resource "libvirt_cloudinit_disk" "commoninit" {
  for_each = local.guest_data
  name           = "guestinit-${local.tectonic.institution}-${local.tectonic.lab_name}-${each.key}.iso"
  user_data      = templatefile("${path.module}/cloud_init.cfg", { 
    hostname = "${each.key}", 
    user = local.os_data[each.value.base_os]["username"],
    authorized_keys = replace(local.tectonic.authorized_keys, "\n", "\\n")
  })
  network_config = local.network_config[each.key]
  pool           = local.tectonic.config.platforms.libvirt.storage_pool
}

resource "libvirt_network" "subnets" {
  for_each = local.subnetworks
  name = "${each.key}"
  addresses = [lookup(each.value, "cidr")]
  mode = "${lookup(each.value, "mode")}"
  autostart = true
  dns {
    enabled = "${lookup(each.value, "mode")}" == "nat"
    local_only = false
  }
}

# Create the machines
resource "libvirt_domain" "machines" {
  for_each = local.guest_data
  name      = "${each.key}"
  memory    = lookup(each.value, "memory", "1024")
  vcpu      = lookup(each.value, "vcpu", "1")
  cpu {
    mode = "host-passthrough"
  }
  cloudinit = libvirt_cloudinit_disk.commoninit[each.key].id

  dynamic "network_interface" {
    for_each = each.value.interfaces
    content {
      network_id = libvirt_network.subnets[network_interface.value.subnetwork_name].id
      addresses = [network_interface.value.private_ip]
    }
  }

  # IMPORTANT: this is a known bug on cloud images, since they expect a console
  # we need to pass it
  # https://bugs.launchpad.net/cloud-images/+bug/1573095
  console {
    type        = "pty"
    target_port = "0"
    target_type = "serial"
  }
  console {
    type        = "pty"
    target_type = "virtio"
    target_port = "1"
  }
  disk {
    volume_id = libvirt_volume.cloned_image[each.key].id
  }
  graphics {
    type        = "spice"
    listen_type = "address"
    autoport    = true
  }
  autostart = true
}
