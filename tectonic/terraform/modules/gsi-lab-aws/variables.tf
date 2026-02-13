
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

variable "os_data_json" {
  type        = string
  description = "A JSON encoded map of operating system information."
}

variable "tectonic_json" {
  type        = string
  description = "A JSON encoded map of tectonic configuration."
}