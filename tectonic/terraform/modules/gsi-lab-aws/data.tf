
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

data "aws_vpc" "vpc" {
  tags = {
    Name = "${local.tectonic.institution}-${local.tectonic.lab_name}"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_key_pair" "pub_key" {
  key_name           = "${local.tectonic.institution}-${local.tectonic.lab_name}-pubkey"
  include_public_key = true
}

data "aws_nat_gateway" "ngw" {
  state = "available" 
  tags  = {
    Name = "${local.tectonic.institution}-${local.tectonic.lab_name}"
  }
}

data "aws_ami" "base_images" {
  for_each = toset(local.guest_basenames)

  most_recent = true
  owners      = ["self"]

  filter {
    name   = "name"
    values = ["${local.tectonic.institution}-${local.tectonic.lab_name}-${each.key}"]
  }
}

data "aws_route53_zone" "reverse" {
  count         = local.tectonic.config.configure_dns ? 1 : 0
  name          = "in-addr.arpa"
  private_zone  = true
  vpc_id        = data.aws_vpc.vpc.id
  tags = {
    Institution = local.tectonic.institution
    Lab         = local.tectonic.lab_name
  }
}

data "aws_instance" "packetbeat" {
  count         = local.tectonic.services.elastic.enable && local.tectonic.services.elastic.monitor_type == "traffic" ? 1 : 0
  instance_tags = {
    Name = "${local.tectonic.institution}-${local.tectonic.lab_name}-packetbeat"
  }
  filter {
    name   = "instance-state-name"
    values = ["running"]
  }
}