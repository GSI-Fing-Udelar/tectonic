
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

# resource "libvirt_pool" "lab_images" {
#   name = "base-images"
#   type = "dir"
#   path = var.libvirt_storage_pool
# }

# Base images
# FZ: creo que esto debería ser un data source, no un resource
# Basado en https://github.com/dmacvicar/terraform-provider-libvirt/pull/987
# resource "libvirt_volume" "base_image" {
#   for_each = keys(var.guest_settings)
#   name = "${var.institution}.${var.lab_name}.${each.value}.qcow2"
#   pool = libvirt_pool.lab_images.name
# }

# Base images already exist, here we create a volume for each
# guest, using the base image as a template
resource "libvirt_volume" "cloned_image" {
  for_each = local.guest_data
  name     = "${each.key}"
  base_volume_name = "${var.institution}-${var.lab_name}-${each.value.base_name}"
  pool     = var.libvirt_storage_pool
  format   = "qcow2"
  size     = (lookup(each.value, "disk", 10) * 1073741824)
}

resource "libvirt_cloudinit_disk" "commoninit" {
  for_each = local.guest_data
  name           = "guestinit-${each.key}.iso"
  user_data      = templatefile("${path.module}/cloud_init.cfg", { 
    hostname = each.value.hostname, 
    user = local.os_data[each.value.base_os]["username"],
    authorized_keys = replace(var.authorized_keys, "\n", "\\n")
  })
  network_config = local.network_config[each.key]
  pool           = var.libvirt_storage_pool
}

# External network for student access
resource "libvirt_network" "external" {
  name = "${var.institution}-${var.lab_name}-external"
  mode = "bridge"
  bridge = var.libvirt_bridge
}

resource "libvirt_network" "subnets" {
  for_each = local.subnetworks

  name = "${each.key}"
  addresses = [lookup(each.value, "ip_network")]
  mode = "none"
  autostart = true
}

# Create the machines
resource "libvirt_domain" "machines" {
  for_each = local.guest_data

  name   = each.key
  memory = lookup(each.value, "memory", "1024")
  vcpu   = lookup(each.value, "vcpu", "1")

  cloudinit = libvirt_cloudinit_disk.commoninit[each.key].id

  dynamic "network_interface" { 
    for_each = each.value.entry_point ? ["external-nic"] : []
    content { 
      network_id = libvirt_network.external.id
    }
  }

  dynamic "network_interface" { 
    for_each = each.value.is_in_services_network ? ["services-nic"] : []
    content { 
      network_name = "${var.institution}-${var.lab_name}-services"
    }
  }

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

  xml {
    #xslt = file(lookup(each.value, "advanced_options_file", "/dev/null"))
    xslt = file("${path.root}/xslt/nw_filters.xslt")
  }
}
