
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

data "aws_vpc" "vpc" {
  tags = {
    Name = "${var.institution}-${var.lab_name}"
  }
}

data "aws_network_interfaces" "interfaces" {
  tags = {
    Institution = var.institution
    Lab         = var.lab_name
  }
}

data "aws_security_group" "teacher_access_sg" {
  tags = {
    Name = "${var.institution}-${var.lab_name}-teacher_access"
  }
}

data "aws_network_interface" "interface" {
  for_each = toset(data.aws_network_interfaces.interfaces.ids)
  id       = each.value
}

data "aws_key_pair" "pub_key" {
  key_name           = "${var.institution}-${var.lab_name}-pubkey"
  include_public_key = true
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_subnet" "services_subnet" {
  for_each    = local.subnetworks
  vpc_id      = data.aws_vpc.vpc.id
  availability_zone       = data.aws_availability_zones.available.names[0]
  cidr_block  = lookup(each.value, "cidr")
  tags = {
    Institution = var.institution
    Lab         = var.lab_name
  }
}

data "aws_route53_zone" "reverse" {
  count         = var.configure_dns ? 1 : 0
  name          = "in-addr.arpa"
  private_zone  = true
  vpc_id        = data.aws_vpc.vpc.id
  tags = {
    Institution = var.institution
    Lab         = var.lab_name
  }
}