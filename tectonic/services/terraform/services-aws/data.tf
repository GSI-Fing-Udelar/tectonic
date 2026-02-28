
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

data "aws_ami" "base_images" {
  for_each = toset(local.guest_basenames)

  most_recent = true
  owners      = ["self"]

  filter {
    name   = "name"
    values = ["${each.key}"]
  }
}

data "aws_ami" "teacher_access_host" {
  most_recent = true
  owners      = [local.os_data[local.tectonic.default_os]["owner"]]

  filter {
    name = "name"
    values = [local.os_data[local.tectonic.default_os]["ami_filter"]]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}