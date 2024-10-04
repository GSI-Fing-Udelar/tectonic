
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

resource "aws_security_group" "services_internet_access_sg" {
  count       = local.internet_access ? 1 : 0
  description = "[Services] Allow outbound internet traffic for enabled machines."
  vpc_id = data.aws_vpc.vpc.id
  egress {
    description = "Allow outbound internet traffic for enabled machines."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = format("%s-%s-services_internet_acecss", var.institution, var.lab_name)
  }
}

resource "aws_security_group" "subnet_sg" {
  for_each = local.subnetworks
  description = "[Services] Allow all traffic within the services subnet. Drop everything else."
  vpc_id   = data.aws_vpc.vpc.id
  ingress {
    description     = "Allow inbound SSH traffic from teacher access host."
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [data.aws_security_group.teacher_access_sg.id]
  }
  ingress {
    description     = "Allow inbound Elasticsearch traffic from teacher access host."
    from_port       = 9200
    to_port         = 9200
    protocol        = "tcp"
    security_groups = [data.aws_security_group.teacher_access_sg.id]
  }
  ingress {
    description     = "Allow inbound Kibana traffic from teacher access host."
    from_port       = 5601
    to_port         = 5601
    protocol        = "tcp"
    security_groups = [data.aws_security_group.teacher_access_sg.id]
  }
  ingress {
    description     = "Allow inbound Caldera traffic from teacher access host."
    from_port       = 8443
    to_port         = 8443
    protocol        = "tcp"
    security_groups = [data.aws_security_group.teacher_access_sg.id]
  }
  ingress {
    description = "Allow inbound traffic from all services subnets."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [lookup(each.value, "cidr")]
  }
  egress {
    description = "Allow outbound traffic to all services subnets."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [lookup(each.value, "cidr")]
  }
  tags = {
    Name = each.key
  }
}

resource "aws_security_group" "caldera_scenario_sg" {
  description = "[Services] Allow inbound traffic from scenario instances to services port."
  vpc_id   = data.aws_vpc.vpc.id
  ingress {
    description   = "Caldera: Allow agent traffic from scenario instances."
    from_port     = 443
    to_port       = 443
    protocol      = "tcp"
    cidr_blocks   = [var.network_cidr_block]
  }
  ingress {
    description   = "Caldera: Allow agent traffic from scenario instances."
    from_port     = 7010
    to_port       = 7010
    protocol      = "tcp"
    cidr_blocks   = [var.network_cidr_block]
  }
  ingress {
    description   = "Caldera: Allow agent traffic from scenario instances."
    from_port     = 7011
    to_port       = 7011
    protocol      = "udp"
    cidr_blocks   = [var.network_cidr_block]
  }
  ingress {
    description       = "Caldera: Allow traffic from teacher access."
    from_port         = 8443
    to_port           = 8443
    protocol          = "tcp"
    security_groups   = [data.aws_security_group.teacher_access_sg.id]
  }
  egress {
    description = "Allow outbound traffic to all instance scenario instances."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-caldera", var.institution, var.lab_name)
  }
}

resource "aws_security_group" "elastic_endpoint_scenario_sg" {
  description = "[Services] Allow inbound traffic from scenario instances to services port."
  vpc_id   = data.aws_vpc.vpc.id
  ingress {
    description   = "Elastic: Allow fleet traffic from scenario instances."
    from_port     = 8220
    to_port       = 8220
    protocol      = "tcp"
    cidr_blocks   = [var.network_cidr_block]
  }
  ingress {
    description   = "Elastic: Allow logstash traffic from scenario instances."
    from_port     = 5044
    to_port       = 5044
    protocol      = "tcp"
    cidr_blocks   = [var.network_cidr_block]
  }
  ingress {
    description       = "Elastic: Allow traffic from teacher access."
    from_port         = 5601
    to_port           = 5601
    protocol          = "tcp"
    security_groups   = [data.aws_security_group.teacher_access_sg.id]
  }
  egress {
    description = "Allow outbound traffic to all instance scenario instances."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-elastic_endpoint", var.institution, var.lab_name)
  }
}

resource "aws_security_group" "elastic_traffic_scenario_sg" {
  description = "[Services] Allow inbound traffic from scenario instances to services port."
  vpc_id   = data.aws_vpc.vpc.id
  ingress {
    description = "Allow VXLAN encapsulation for traffic mirroring"
    from_port   = 4789
    to_port     = 4789
    protocol    = "udp"
    cidr_blocks = [var.network_cidr_block]
  }
  egress {
    description = "Allow outbound traffic to all instance scenario instances."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-elastic_traffic", var.institution, var.lab_name)
  }
}

resource "aws_network_interface" "interfaces" {
  for_each    = local.network_interfaces
  subnet_id   = data.aws_subnet.services_subnet[each.value.subnetwork_name].id
  private_ips = [each.value.private_ip]
  source_dest_check = false
  security_groups = concat([aws_security_group.subnet_sg[each.value.subnetwork_name].id],
    local.guest_data[each.value.guest_name].internet_access ? [aws_security_group.services_internet_access_sg[0].id] : [],
    local.guest_data[each.value.guest_name].base_name == "caldera" ? [aws_security_group.caldera_scenario_sg.id] : [],
    local.guest_data[each.value.guest_name].base_name == "elastic" && var.monitor_type == "endpoint" ? [aws_security_group.elastic_endpoint_scenario_sg.id] : [],
    local.guest_data[each.value.guest_name].base_name == "packetbeat" ? [aws_security_group.elastic_traffic_scenario_sg.id] : [],
  )
  tags = {
    Name = each.key
  }
}

resource "aws_instance" "machines" {
  for_each = local.guest_data
  ami = data.aws_ami.base_images[each.value.base_name].id
  instance_type = each.value.instance_type
  key_name = data.aws_key_pair.pub_key.key_name
  dynamic "network_interface" {
    for_each = each.value.interfaces
    content {
      device_index         = network_interface.value.index
      network_interface_id = aws_network_interface.interfaces[network_interface.key].id
    }
  }
  user_data = templatefile(format("%s/%s", abspath(path.root), "user_data_linux.pkrtpl"),
    { 
      authorized_keys = var.authorized_keys, 
      hostname = each.value.hostname,
      username = local.os_data[each.value.base_os]["username"],
      base_os = each.value.base_os
    }
  )
  root_block_device {
    volume_size = lookup(each.value, "disk", 10)
    volume_type = "gp2"
  }
  tags = {
    Name = each.key
  }
}

resource "null_resource" "wait_for_machines" {
  # Wait for instances to become ready.
  for_each = local.guest_data
  triggers = {
    guest_id = aws_instance.machines[each.key].id
  }
  provisioner "local-exec" {
    command = "aws --region=${var.aws_region} ec2 wait instance-status-ok --instance-ids ${aws_instance.machines[each.key].id}"
  }
}

# DNS Configuration
resource "aws_route53_zone" "zones" {
  for_each = toset(var.configure_dns ? local.network_names : [])
  name     = each.key
  vpc {
    vpc_id = data.aws_vpc.vpc.id
  }
  tags = {
    Name = format("%s-%s-%s", var.institution, var.lab_name, each.key)
  }
}

resource "aws_route53_record" "records" {
  for_each = var.configure_dns ? local.dns_data : {}
  zone_id  = aws_route53_zone.zones[each.value.network].zone_id
  name     = each.value.name #<guest_name>-(<guest_copy_number>)?-<instance_number>.<network_name>
  type     = "A"
  ttl      = 300
  records  = [each.value.ip]
}

resource "aws_route53_record" "records_reverse" {
  for_each = var.configure_dns ? local.dns_data : {}
  zone_id  = data.aws_route53_zone.reverse[0].zone_id
  name     = join(".", reverse(split(".", each.value.ip)))
  type     = "PTR"
  ttl      = 300
  records  = [format("%s.%s", each.value.name, each.value.network)]
}

#Traffic mirroring
resource "aws_ec2_traffic_mirror_target" "packetbeat" {
  count = var.monitor && var.monitor_type == "traffic" ? 1 : 0
  description          = "Packetbeat target mirror traffic."
  network_interface_id = aws_instance.machines["${var.institution}-${var.lab_name}-packetbeat"].primary_network_interface_id

  tags = {
    Name = "${var.institution}-${var.lab_name}"
  }
}
resource "aws_ec2_traffic_mirror_filter" "filter" {
  count = var.monitor && var.monitor_type == "traffic" ? 1 : 0
  tags = {
    Name = "${var.institution}-${var.lab_name}"
  }
}
resource "aws_ec2_traffic_mirror_filter_rule" "filter_all_inbound" {
  count = var.monitor && var.monitor_type == "traffic" ? 1 : 0
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.filter[0].id
  source_cidr_block        = "0.0.0.0/0"
  destination_cidr_block   = "0.0.0.0/0"
  rule_number              = 1
  rule_action              = "accept"
  traffic_direction        = "ingress"
}
resource "aws_ec2_traffic_mirror_filter_rule" "filter_all_outbound" {
  count = var.monitor && var.monitor_type == "traffic" ? 1 : 0
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.filter[0].id
  source_cidr_block        = "0.0.0.0/0"
  destination_cidr_block   = "0.0.0.0/0"
  rule_number              = 2
  rule_action              = "accept"
  traffic_direction        = "egress"
}
resource "aws_ec2_traffic_mirror_session" "session" {
  for_each = {
    for interface in local.interfaces_to_mirror :
    interface.interface_name => interface
  }
  network_interface_id     = each.value.interface_id
  session_number           = 1
  traffic_mirror_filter_id = aws_ec2_traffic_mirror_filter.filter[0].id
  traffic_mirror_target_id = aws_ec2_traffic_mirror_target.packetbeat[0].id
  virtual_network_id       = var.packetbeat_vlan_id
  tags = {
    Name = "${each.key}"
  }
}
