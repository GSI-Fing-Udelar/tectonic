
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
  cidr               = var.network_cidr_block
  azs                = [data.aws_availability_zones.available.names[0]]
  public_subnets     = [var.internet_network_cidr_block]
  private_subnets    = [var.services_network_cidr_block]
  enable_nat_gateway = local.internet_access || var.services_internet_access
  single_nat_gateway = true
  enable_vpn_gateway = false

  tags = {
    Name = "${var.institution}-${var.lab_name}"
  }
}

resource "aws_key_pair" "admin_pubkey" {
  key_name   = "${var.institution}-${var.lab_name}-pubkey"
  public_key = file("${var.ssh_public_key_file}")

  tags = {
    Name = "${var.institution}-${var.lab_name}"
  }
}

resource "aws_subnet" "instance_subnets" {
  for_each = local.subnetworks

  vpc_id                  = module.vpc.vpc_id
  map_public_ip_on_launch = false
  availability_zone       = module.vpc.azs[0]
  cidr_block              = each.value

  tags = {
    Name = each.key
  }
}

resource "aws_ec2_instance_connect_endpoint" "teacher_access" {
  count = var.teacher_access == "endpoint" ? 1 : 0

  subnet_id = module.vpc.private_subnets[0]

  security_group_ids = [aws_security_group.teacher_access_sg.id]

  tags = {
    Name = format("%s-%s", var.institution, var.lab_name)
  }
}

resource "aws_instance" "teacher_access_host" {
  count = var.teacher_access == "host" ? 1 : 0

  ami           = data.aws_ami.student_access_host.id
  instance_type = var.aws_default_instance_type

  key_name = aws_key_pair.admin_pubkey.key_name

  subnet_id                   = module.vpc.public_subnets[0]
  vpc_security_group_ids      = [aws_security_group.teacher_access_sg.id, aws_security_group.student_access_sg.id]
  associate_public_ip_address = true

  user_data = <<EOF
#!/bin/bash
hostnamectl set-hostname ${var.institution}-${var.lab_name}-teacher
echo "${var.authorized_keys}" > ~${local.os_data[var.default_os]["username"]}/.ssh/authorized_keys
EOF

  tags = {
    Name = "${var.institution}-${var.lab_name}-teacher_access"
  }
}

resource "aws_security_group" "teacher_access_sg" {
  description = "Allow outbound SSH and RDP traffic from the teacher access host/EIC endpoint to the whole VPC and access to services."

  vpc_id = module.vpc.vpc_id
  egress {
    description = "Allow outbound SSH traffic to the VPC."
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.network_cidr_block]
  }
  egress {
    description = "Allow outbound RDP traffic to the VPC."
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = [var.network_cidr_block]
  }
  egress {
    description = "Allow outbound caldera traffic to services network."
    from_port   = 8443
    to_port     = 8443
    protocol    = "tcp"
    cidr_blocks = [var.services_network_cidr_block]
  }
  egress {
    description = "Allow outbound kibana traffic to the services network."
    from_port   = 5601
    to_port     = 5601
    protocol    = "tcp"
    cidr_blocks = [var.services_network_cidr_block]
  }
  tags = {
    Name = format("%s-%s-teacher_access", var.institution, var.lab_name)
  }
}

resource "aws_security_group" "student_access_sg" {
  description = "[Student Access Host] Allow all SSH traffic to the student access host. Allow SSH and RDP traffic to the whole VPC."

  vpc_id = module.vpc.vpc_id
  egress {
    description = "Allow outbound SSH traffic to the VPC."
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.network_cidr_block]
  }
  egress {
    description = "Allow outbound RDP traffic to the VPC."
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = [var.network_cidr_block]
  }

  ingress {
    description = "Allow ingress SSH traffic."
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = format("%s-%s-student_access_host", var.institution, var.lab_name)
  }
}

resource "aws_security_group" "entry_point_sg" {
  description = "[Entry Point Machines] Allow inbound SSH traffic from student access host to lab entry points."

  vpc_id = module.vpc.vpc_id
  ingress {
    description     = "Allow inbound SSH traffic from student access host to lab entry points."
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.student_access_sg.id]
  }

  tags = {
    Name = format("%s-%s-entry_point", var.institution, var.lab_name)
  }
}
resource "aws_security_group" "windows_entry_point_sg" {
  description = "[Entry Point Machines] Allow inbound RDP traffic from student access host to windows entry points."

  vpc_id = module.vpc.vpc_id
  ingress {
    description     = "Allow inbound RDP traffic from student access host to windows entry points."
    from_port       = 3389
    to_port         = 3389
    protocol        = "tcp"
    security_groups = [aws_security_group.student_access_sg.id]
  }

  tags = {
    Name = format("%s-%s-windows_entry_point", var.institution, var.lab_name)
  }
}

resource "aws_security_group" "internet_access_sg" {
  count       = local.internet_access ? 1 : 0
  description = "[Machines] Allow outbound internet traffic for enabled machines."

  vpc_id = module.vpc.vpc_id
  egress {
    description = "Allow outbound internet traffic for enabled machines."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = format("%s-%s-internet_acecss", var.institution, var.lab_name)
  }
}

resource "aws_security_group" "subnet_sg" {
  description = "[Machines] Allow all traffic within the subnet. Drop everything else."

  for_each = local.subnetworks
  vpc_id   = module.vpc.vpc_id

  ingress {
    description     = "Allow inbound SSH traffic from teacher access host."
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.teacher_access_sg.id]
  }
  ingress {
    description     = "Allow inbound RDP traffic from teacher access host."
    from_port       = 3389
    to_port         = 3389
    protocol        = "tcp"
    security_groups = [aws_security_group.teacher_access_sg.id]
  }
  ingress {
    description = "Allow inbound traffic from all instance subnets."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [each.value]
  }
  egress {
    description = "Allow outbound traffic to all instance subnets."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [each.value]
  }

  tags = {
    Name = each.key
  }
}

resource "aws_security_group" "services_subnet_sg" {
  description = "[Machines] Allow traffic to services from subnet."
  vpc_id   = module.vpc.vpc_id
  ingress {
    description = "Allow inbound traffic from services subnets."
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = module.vpc.private_subnets_cidr_blocks
  }
  egress {
    description   = "Allow outbound traffic to Fleet"
    from_port     = 8220
    to_port       = 8220
    protocol      = "tcp"
    cidr_blocks   = module.vpc.private_subnets_cidr_blocks
  }
  egress {
    description   = "Allow outbound traffic to Logstash."
    from_port     = 5044
    to_port       = 5044
    protocol      = "tcp"
    cidr_blocks   = module.vpc.private_subnets_cidr_blocks
  }
  egress {
    description   = "Allow outbound traffic to Caldera"
    from_port     = 443
    to_port       = 443
    protocol      = "tcp"
    cidr_blocks   = module.vpc.private_subnets_cidr_blocks
  }
  egress {
    description   = "Caldera: Allow agent traffic from scenario instances."
    from_port     = 7010
    to_port       = 7010
    protocol      = "tcp"
    cidr_blocks   = module.vpc.private_subnets_cidr_blocks
  }
  egress {
    description   = "Caldera: Allow agent traffic from scenario instances."
    from_port     = 7011
    to_port       = 7011
    protocol      = "udp"
    cidr_blocks   = module.vpc.private_subnets_cidr_blocks
  }
  tags = {
    Name = "${var.institution}-${var.lab_name}-services-subnet"
  }
}

resource "aws_route_table" "scenario_internet_access" {
  count = local.internet_access ? 1 : 0
  vpc_id = module.vpc.vpc_id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = module.vpc.natgw_ids[0]
  }
  tags = {
    Name = "${var.institution}-${var.lab_name}-scenario_internet_access"
  }
}

resource "aws_route_table_association" "scenario_internet_access" {
  for_each       = local.internet_access ? local.subnetworks : {}
  subnet_id      = aws_subnet.instance_subnets[each.key].id
  route_table_id = aws_route_table.scenario_internet_access[0].id
}

resource "aws_network_interface" "interfaces" {
  for_each    = local.network_interfaces
  subnet_id   = aws_subnet.instance_subnets[each.value.subnetwork_name].id
  private_ips = [each.value.private_ip]

  source_dest_check = false

  security_groups = concat([aws_security_group.subnet_sg[each.value.subnetwork_name].id],
    local.guest_data[each.value.guest_name].entry_point ? [aws_security_group.entry_point_sg.id] : [],
    local.guest_data[each.value.guest_name].base_os == "windows_srv_2022" && local.guest_data[each.value.guest_name].entry_point ? [aws_security_group.windows_entry_point_sg.id] : [],
    local.guest_data[each.value.guest_name].internet_access ? [aws_security_group.internet_access_sg[0].id] : [],
    local.guest_data[each.value.guest_name].is_in_services_network ? [aws_security_group.services_subnet_sg.id] : [],
  )

  tags = {
    Name = each.key
  }
}

resource "aws_instance" "machines" {
  for_each = local.guest_data

  ami = data.aws_ami.base_images[each.value.base_name].id

  instance_type = each.value.instance_type

  key_name = aws_key_pair.admin_pubkey.key_name

  dynamic "network_interface" {
    for_each = each.value.interfaces
    content {
      device_index         = network_interface.value.index
      network_interface_id = aws_network_interface.interfaces[network_interface.key].id
    }
  }

  user_data = templatefile(format("%s/%s", abspath(path.root), 
    (each.value.base_os == "windows_srv_2022" ? "user_data_win.pkrtpl" : "user_data_linux.pkrtpl")),
    { 
      authorized_keys = var.authorized_keys, 
      hostname = each.value.hostname,
      username = local.os_data[each.value.base_os]["username"],
      base_os = each.value.base_os,
    })

   root_block_device {
    volume_size = lookup(each.value, "disk", 10)
    volume_type = "gp2"
  }
 
  tags = {
    Name = each.key
  }
}

resource "null_resource" "wait_for_machines" {
  # Wait for instances to become ready. This is specially necessary
  # for windows machines that require a reboot in user-data due to
  # hostname change.
  for_each = local.guest_data

  triggers = {
    guest_id = aws_instance.machines[each.key].id
  }

  provisioner "local-exec" {
    command = "aws --region=${var.aws_region} ec2 wait instance-status-ok --instance-ids ${aws_instance.machines[each.key].id}"
  }
}

resource "aws_instance" "student_access" {
  ami = data.aws_ami.student_access_host.id

  instance_type = var.aws_default_instance_type

  key_name = aws_key_pair.admin_pubkey.key_name

  subnet_id                   = module.vpc.public_subnets[0]
  vpc_security_group_ids      = [aws_security_group.student_access_sg.id]
  associate_public_ip_address = true

  user_data = <<EOF
#!/bin/bash
hostnamectl set-hostname ${var.institution}-${var.lab_name}
echo "${var.authorized_keys}" > ~${local.os_data[var.default_os]["username"]}/.ssh/authorized_keys
EOF

  tags = {
    Name = "${var.institution}-${var.lab_name}-student_access"
  }

}


# DNS Configuration

resource "aws_route53_zone" "zones" {
  for_each = toset(var.configure_dns ? local.network_names : [])
  name     = each.key

  vpc {
    vpc_id = module.vpc.vpc_id
  }

  tags = {
    Name = format("%s-%s-%s", var.institution, var.lab_name, each.key)
  }
}

resource "aws_route53_zone" "reverse" {
  count = var.configure_dns ? 1 : 0
  name  = "in-addr.arpa"

  vpc {
    vpc_id = module.vpc.vpc_id
  }

  tags = {
    Name = format("%s-%s-reverse", var.institution, var.lab_name)
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
  zone_id  = aws_route53_zone.reverse[0].zone_id
  name     = join(".", reverse(split(".", each.value.ip)))
  type     = "PTR"
  ttl      = 300
  records  = [format("%s.%s", each.value.name, each.value.network)]
}
