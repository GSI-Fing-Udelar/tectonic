
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

module "vpc" {
  source             = "terraform-aws-modules/vpc/aws"
  version            = "~>5.0"
  name               = "vpc"
  cidr               = local.tectonic.config.network_cidr_block
  azs                = [data.aws_availability_zones.available.names[0]]
  public_subnets     = [local.tectonic.config.internet_network_cidr_block]
  private_subnets    = [local.tectonic.config.services_network_cidr_block]
  enable_nat_gateway = local.internet_access
  single_nat_gateway = true
  enable_vpn_gateway = false

  tags = {
    Name = "${local.tectonic.institution}-${local.tectonic.lab_name}"
  }
}

resource "aws_key_pair" "pub_key" {
  key_name   = "${local.tectonic.institution}-${local.tectonic.lab_name}-pubkey"
  public_key = file("${local.tectonic.config.ssh_public_key_file}")

  tags = {
    Name = "${local.tectonic.institution}-${local.tectonic.lab_name}"
  }
}

resource "aws_security_group" "services_internet_access_sg" {
  count       = local.internet_access ? 1 : 0
  description = "[Services] Allow outbound internet traffic for enabled machines."
  vpc_id = module.vpc.vpc_id
  egress {
    description = "Allow outbound internet traffic for enabled machines."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = format("%s-%s-services_internet_acecss", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_security_group" "subnet_sg" {
  for_each = local.subnetworks
  description = "[Services] Allow all traffic within the services subnet. Drop everything else."
  vpc_id   = module.vpc.vpc_id
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
  description = "[Services] Allow traffic for Caldera."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description   = "Caldera: Allow agent traffic from scenario instances."
    from_port     = 443
    to_port       = 443
    protocol      = "tcp"
    cidr_blocks   = [local.tectonic.config.network_cidr_block]
  }
  ingress {
    description   = "Caldera: Allow agent traffic from scenario instances."
    from_port     = 7010
    to_port       = 7010
    protocol      = "tcp"
    cidr_blocks   = [local.tectonic.config.network_cidr_block]
  }
  ingress {
    description   = "Caldera: Allow agent traffic from scenario instances."
    from_port     = 7011
    to_port       = 7011
    protocol      = "udp"
    cidr_blocks   = [local.tectonic.config.network_cidr_block]
  }
  ingress {
    description       = "Caldera: Allow traffic from bastion host."
    from_port         = local.tectonic.services.caldera.internal_port
    to_port           = local.tectonic.services.caldera.internal_port
    protocol          = "tcp"
    cidr_blocks       = [local.tectonic.config.internet_network_cidr_block]
  }
  egress {
    description = "Allow outbound traffic to all scenario instances."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [local.tectonic.config.network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-caldera", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_security_group" "elastic_endpoint_scenario_sg" {
  description = "[Services] Allow traffic for Elastic in endpoint mode."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description   = "Elastic: Allow fleet traffic from scenario instances."
    from_port     = 8220
    to_port       = 8220
    protocol      = "tcp"
    cidr_blocks   = [local.tectonic.config.network_cidr_block]
  }
  ingress {
    description   = "Elastic: Allow logstash traffic from scenario instances."
    from_port     = 5044
    to_port       = 5044
    protocol      = "tcp"
    cidr_blocks   = [local.tectonic.config.network_cidr_block]
  }
  ingress {
    description       = "Elastic: Allow traffic from bastion host."
    from_port         = local.tectonic.services.elastic.internal_port
    to_port           = local.tectonic.services.elastic.internal_port
    protocol          = "tcp"
    cidr_blocks       = [local.tectonic.config.internet_network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-elastic_endpoint", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_security_group" "elastic_traffic_scenario_sg" {
  description = "[Services] Allow traffic for Elastic in traffic mode."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description       = "Elastic: Allow traffic from bastion host."
    from_port         = local.tectonic.services.elastic.internal_port
    to_port           = local.tectonic.services.elastic.internal_port
    protocol          = "tcp"
    cidr_blocks       = [local.tectonic.config.internet_network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-elastic_traffic", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_security_group" "packetbeat_scenario_sg" {
  description = "[Services] Allow traffic for packetbeat."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description = "Allow VXLAN encapsulation for traffic mirroring"
    from_port   = 4789
    to_port     = 4789
    protocol    = "udp"
    cidr_blocks = [local.tectonic.config.network_cidr_block]
  }
  egress {
    description = "Allow all outbound traffic to all scenario instances."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [local.tectonic.config.network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-packetbeat", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_security_group" "guacamole_scenario_sg" {
  description = "[Services] Allow traffic for Guacamole."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description       = "Guacamole: Allow traffic from bastion host"
    from_port         = local.tectonic.services.guacamole.internal_port
    to_port           = local.tectonic.services.guacamole.internal_port
    protocol          = "tcp"
    cidr_blocks       = [local.tectonic.config.internet_network_cidr_block]
  }
  egress {
    description = "Guacamole: Allow SSH outbound traffic to all scenario instances."
    from_port   = "22"
    to_port     = "22"
    protocol    = "tcp"
    cidr_blocks = [local.tectonic.config.network_cidr_block]
  }
  egress {
    description = "Guacamole: Allow RDP outbound traffic to all scenario instances."
    from_port   = "3389"
    to_port     = "3389"
    protocol    = "tcp"
    cidr_blocks = [local.tectonic.config.network_cidr_block]
  }
  egress {
    description = "Guacamole: Allow VNC outbound traffic to all scenario instances."
    from_port   = "5900"
    to_port     = "5900"
    protocol    = "tcp"
    cidr_blocks = [local.tectonic.config.network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-guacamole", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_security_group" "moodle_scenario_sg" {
  description = "[Services] Allow traffic for Moodle."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description       = "Moodle: Allow traffic from bastion host"
    from_port         = local.tectonic.services.moodle.internal_port
    to_port           = local.tectonic.services.moodle.internal_port
    protocol          = "tcp"
    cidr_blocks       = [local.tectonic.config.internet_network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-guacamole", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_security_group" "bastion_host_scenario_sg" {
  description = "[Service] Allow traffic for Bastion Host."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description = "Bastion Host: Allow ingress SSH traffic from internet."
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Bastion Host: Allow ingress HTTP traffic from internet to default virtualhost."
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Bastion Host: Allow ingress HTTP traffic from internet to bastion_host/guacamole virtualhost."
    from_port   = local.tectonic.services.guacamole.external_port
    to_port     = local.tectonic.services.guacamole.external_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Bastion Host: Allow ingress HTTP traffic from internet to elastic virtualhost."
    from_port   = local.tectonic.services.elastic.external_port
    to_port     = local.tectonic.services.elastic.external_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Bastion Host: Allow ingress HTTP traffic from internet to caldera virtualhost."
    from_port   = local.tectonic.services.caldera.external_port
    to_port     = local.tectonic.services.caldera.external_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    description = "Bastion Host: Allow ingress HTTP traffic from internet to moodle virtualhost."
    from_port   = local.tectonic.services.moodle.external_port
    to_port     = local.tectonic.services.moodle.external_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    description = "Bastion Host: Allow SSH outbound traffic to all scenario instances."
    from_port   = "22"
    to_port     = "22"
    protocol    = "tcp"
    cidr_blocks = [local.tectonic.config.network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-bastion_host", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_security_group" "teacher_access_host_scenario_sg" {
  description = "[Service] Allow traffic for Teacher Access Host."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description = "Teacher Access Host: Allow ingress SSH traffic bastion host."
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.tectonic.config.internet_network_cidr_block]
  }
  egress {
    description = "Teacher Access Host: Allow SSH outbound traffic to all scenario instances."
    from_port   = "22"
    to_port     = "22"
    protocol    = "tcp"
    cidr_blocks = [local.tectonic.config.network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-teacher_access_host", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_network_interface" "interfaces" {
  for_each    = local.network_interfaces
  subnet_id   = local.guest_data[each.value.guest_name].base_name == "bastion_host" ? module.vpc.public_subnets[0] : module.vpc.private_subnets[0]
  private_ips = [each.value.private_ip]
  source_dest_check = false
  security_groups = concat([aws_security_group.subnet_sg[each.value.subnetwork_name].id],
    local.guest_data[each.value.guest_name].internet_access ? [aws_security_group.services_internet_access_sg[0].id] : [],
    local.guest_data[each.value.guest_name].base_name == "caldera" ? [aws_security_group.caldera_scenario_sg.id] : [],
    local.guest_data[each.value.guest_name].base_name == "elastic" && local.tectonic.services.elastic.monitor_type == "endpoint" ? [aws_security_group.elastic_endpoint_scenario_sg.id] : [aws_security_group.elastic_traffic_scenario_sg.id],
    local.guest_data[each.value.guest_name].base_name == "packetbeat" ? [aws_security_group.packetbeat_scenario_sg.id ] : [],
    local.guest_data[each.value.guest_name].base_name == "guacamole" ? [aws_security_group.guacamole_scenario_sg.id] : [],
    local.guest_data[each.value.guest_name].base_name == "moodle" ? [aws_security_group.moodle_scenario_sg.id] : [],
    local.guest_data[each.value.guest_name].base_name == "bastion_host" ? [aws_security_group.bastion_host_scenario_sg.id] : [],
    local.guest_data[each.value.guest_name].base_name == "teacher_access_host" ? [aws_security_group.teacher_access_host_scenario_sg.id] : [],
  )
  tags = {
    Name = each.key
  }
}

resource "aws_instance" "machines" {
  for_each = local.guest_data
  ami = each.value.base_name == "teacher_access_host" ? data.aws_ami.teacher_access_host.id : data.aws_ami.base_images[each.value.base_name].id
  instance_type = each.value.instance_type
  key_name = aws_key_pair.pub_key.key_name
  dynamic "network_interface" {
    for_each = each.value.interfaces
    content {
      device_index         = network_interface.value.index
      network_interface_id = aws_network_interface.interfaces[network_interface.key].id
    }
  }
  user_data = templatefile(format("%s/%s", abspath(path.root), "user_data_linux.pkrtpl"),
    { 
      authorized_keys = local.tectonic.authorized_keys, 
      hostname = each.value.base_name,
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

resource "aws_eip" "bastion_host" {
  vpc = true
  tags = {
    Name = format("%s-%s-bastion_host", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_eip_association" "eip_assoc_bastion_host" {
  instance_id   = aws_instance.machines[format("%s-%s-bastion_host", local.tectonic.institution, local.tectonic.lab_name)].id
  allocation_id = aws_eip.bastion_host.id
}

resource "null_resource" "wait_for_machines" {
  # Wait for instances to become ready.
  for_each = local.guest_data
  triggers = {
    guest_id = aws_instance.machines[each.key].id
  }
  provisioner "local-exec" {
    command = "aws --region=${local.tectonic.config.platforms.aws.region} ec2 wait instance-status-ok --instance-ids ${aws_instance.machines[each.key].id}"
  }
}

# DNS Configuration
resource "aws_route53_zone" "zones" {
  for_each = toset(local.tectonic.config.configure_dns ? local.network_names : [])
  name     = each.key
  vpc {
    vpc_id = module.vpc.vpc_id
  }
  tags = {
    Name = format("%s-%s-%s", local.tectonic.institution, local.tectonic.lab_name, each.key)
  }
}

resource "aws_route53_zone" "reverse" {
  count = local.tectonic.config.configure_dns ? 1 : 0
  name  = "in-addr.arpa"

  vpc {
    vpc_id = module.vpc.vpc_id
  }

  tags = {
    Name = format("%s-%s-reverse", local.tectonic.institution, local.tectonic.lab_name)
  }
}

resource "aws_route53_record" "records" {
  for_each = local.tectonic.config.configure_dns ? local.dns_data : {}
  zone_id  = aws_route53_zone.zones[each.value.network].zone_id
  name     = each.value.name #<guest_name>-(<guest_copy_number>)?-<instance_number>.<network_name>
  type     = "A"
  ttl      = 300
  records  = [each.value.ip]
}

resource "aws_route53_record" "records_reverse" {
  for_each = local.tectonic.config.configure_dns ? local.dns_data : {}
  zone_id  = aws_route53_zone.reverse[0].zone_id
  name     = join(".", reverse(split(".", each.value.ip)))
  type     = "PTR"
  ttl      = 300
  records  = [format("%s.%s", each.value.name, each.value.network)]
}

resource "aws_ec2_instance_connect_endpoint" "teacher_access" {
  count = local.tectonic.config.platforms.aws.teacher_access == "endpoint" ? 1 : 0

  subnet_id = module.vpc.private_subnets[0]

  security_group_ids = [aws_security_group.bastion_host_scenario_sg.id]

  tags = {
    Name = format("%s-%s", local.tectonic.institution, local.tectonic.lab_name)
  }
}