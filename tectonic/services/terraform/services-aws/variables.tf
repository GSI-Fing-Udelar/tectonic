
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

variable "institution" {
  type        = string
  description = "The institution that created the lab."

  validation {
    condition     = !strcontains(var.institution, "-")
    error_message = "Names cannot contain the '-' symbol."
  }
}

variable "lab_name" {
  type        = string
  description = "The name of the lab"

  validation {
    condition     = !strcontains(var.lab_name, "-")
    error_message = "Names cannot contain the '-' symbol."
  }
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "The region to use for the aws provider"
}

variable "subnets_json" {
  type        = string
  default     = "{}"
  description = "A JOSN map from subnetwork names to cidr blocks."
}

variable "guest_data_json" {
  type        = string
  default     = "{}"
  description = "The map with all guest data, in JSON format."
}

variable "default_os" {
  type        = string
  description = "Default base VM operating system to use. Can be ubuntu22 (the default) or rocky8."
  default     = "ubuntu22"
}

variable "os_data_json" {
  type        = string
  description = "A JSON encoded map of operating system information."
}

variable "authorized_keys" {
  type        = string
  description = "Admin user authorized_keys file contents "
}

variable "configure_dns" {
  description = "Whether to configure DNS hostnames for instances."
  type        = bool
  default     = true
}

variable "services_network_cidr_block" {
  description = "CIDR block for services subnet"
  type        = string
  default     = "10.0.0.128/25"
}

variable "network_cidr_block" {
  description = "CIDR block for lab VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "monitor_type" {
  type        = string
  default     = "traffic"
  description = "How to monitor instances using Elastic."
}

variable "packetbeat_vlan_id" {
  description = "Identifier of the VLAN needed for traffic mirroring."
  type        = string
  default     = "1"
}

variable "machines_to_monitor" {
  description = "Base name of the machines to monitor with packetbeat. All instances and copies will be monitored."
  type        = list(string)
  default     = []
}

variable "monitor" {
  description = "Whether to monitor instances."
  type        = bool
  default     = false
}