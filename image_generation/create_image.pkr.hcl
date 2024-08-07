#
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
#

packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = "~> 1"
    }
    ansible = {
      source  = "github.com/hashicorp/ansible"
      version = "~> 1"
    }
    sshkey = {
      version = ">= 1.0.1"
      source = "github.com/ivoronin/sshkey"
    }
    libvirt = {
      version = ">= 0.5.0"
      source  = "github.com/thomasklein94/libvirt"
    }
  }
}


variable "platform" {
  type        = string
  description = "Whether to create images in AWS or use libvirt."

  validation {
    condition = can(regex("^(aws|libvirt)$", var.platform))
    error_message = "Supported platforms are 'aws', 'libvirt'."
  }
}

# Image identification
variable "institution" {
  type        = string
  description = "The institution that created the lab."
}
variable "lab_name" {
  type        = string
  description = "The name of the lab."
}
variable "instance_number" {
  type        = number
  description = "The total number of instances in the lab."
}
variable "ansible_ssh_common_args" {
  type = string
  description = "SSH arguments for ansible connection to machine."
  default = "-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedKeyTypes=+ssh-rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -x"
}
variable "ansible_scp_extra_args" {
  type = string
  description = "SCP extra arguments for ansible connection."
  default = ""
}

variable "ansible_playbooks_path" {
  type = string
  description = "Path to the ansible playbooks."
}

variable "os_data_json" {
  type = string
  description = "A JSON encoded map of operating system information."
}

variable "machines_json" {
  type        = string
  description = "A JSON encoded map of machine information."
}

variable "remove_ansible_logs" {
  type = string
  description = "Remove Ansible logs on managed host."
  default = "true"
}

locals {
  machines = jsondecode(var.machines_json)
  os_data = jsondecode(var.os_data_json)

  build_type = var.platform == "aws" ? "amazon-ebs" : "libvirt"
  machine_builds = [ for m, _ in local.machines : "${local.build_type}.${m}" ]

  win_machines = [ for name, m in local.machines :
    "${local.build_type}.${name}" if m["base_os"] == "windows_srv_2022"
  ]

  not_endpoint_monitoring_machines = [ for name, m in local.machines : "${local.build_type}.${name}" if !m["endpoint_monitoring"] ]
}


# AWS configuration
variable "aws_region" {
  type    = string
  default = "us-east-1"
}

# libvirt configuration
variable "libvirt_uri" {
  type        = string
  default     = "qemu:///system"
  description = "URI to connect to libvirt daemon."
}
variable "libvirt_storage_pool" {
  type        = string
  default     = "default"
  description = "Libvirt Storage pool to store the configured image."
}
variable "libvirt_proxy" {
  type        = string
  default     = null
  description = "Guest machines proxy configuration URI for libvirt."
}

# Elastic configuration
variable "elastic_version" {
  type = string
  description = "Elastic version."
}

source "amazon-ebs" "machine" {
  region        = var.aws_region

  force_deregister = true
  force_delete_snapshot = true
}

data "sshkey" "install" {
}

source "libvirt" "machine" {
  libvirt_uri = var.libvirt_uri
  # Network interface to connect to machine when building
  network_interface {
    type  = "managed"
    alias = "communicator"
  }

  network_address_source = "lease"

  volume {
    pool  = var.libvirt_storage_pool
    source {
      type = "cloud-init"
      user_data = format("#cloud-config\n%s", jsonencode({
        ssh_authorized_keys = [
          data.sshkey.install.public_key,
        ]
      }))
    }
    bus        = "sata"
  }
  shutdown_mode = "acpi"
}


build {
  dynamic "source" {
    for_each = { for machine_name, m in local.machines: machine_name => m if var.platform == "aws" }
    labels   = ["amazon-ebs.machine"]
    content {
      name = source.key
      ami_name = "${var.institution}-${var.lab_name}-${source.key}"
      instance_type = "${source.value["instance_type"]}"
      source_ami_filter {
        filters = {
          name                = local.os_data[source.value["base_os"]]["ami_filter"]
          root-device-type    = "ebs"
          virtualization-type = "hvm"
        }
        most_recent = true
        owners      = [local.os_data[source.value["base_os"]]["owner"]]
      }
      launch_block_device_mappings {
        device_name = "/dev/sda1"
        volume_size = "${source.value["disk"]}"
        volume_type = "gp2"
      }
      communicator         = "ssh"
      ssh_username = local.os_data[source.value["base_os"]]["username"]
      ssh_private_key_file = (source.value["base_os"] == "windows_srv_2022" ? data.sshkey.install.private_key_path : null)
      # Windows only config. bootstrap_win enables OpenSSH access with
      # pubkey for the administrator.
      user_data = (source.value["base_os"] == "windows_srv_2022" ? templatefile("${abspath(path.root)}/bootstrap_win.pkrtpl", { pubkey = data.sshkey.install.public_key }): null)
      snapshot_tags = {
        "Name" = "${var.institution}-${var.lab_name}-${source.key}"
      }
      tags = {
	      "Name" = "${var.institution}-${var.lab_name}-${source.key}"
      }
    }
  }

  dynamic "source" {
    for_each = { for machine_name, m in local.machines: machine_name => m if var.platform == "libvirt" }
    labels   = ["libvirt.machine"]
    content {
      name = source.key
      communicator {
        communicator         = "ssh"
        ssh_username         = local.os_data[source.value["base_os"]]["username"]
        ssh_private_key_file = data.sshkey.install.private_key_path
        # ssh_agent_auth = true
        # ssh_bastion_host = "tortuga"
        # ssh_bastion_port = 4446
        # ssh_bastion_username = "gsi"
        # ssh_bastion_agent_auth = true
        # ssh_timeout = "1m"
      }
      vcpu   = source.value["vcpu"]
      memory = source.value["memory"]
      volume {
        name = "${var.institution}-${var.lab_name}-${source.key}"
        alias = "artifact"
        pool  = var.libvirt_storage_pool
        source {
          type = "external"
          urls     = [local.os_data[source.value["base_os"]]["cloud_image_url"]]
          checksum = local.os_data[source.value["base_os"]]["cloud_image_checksum"]
        }
        capacity = "${source.value["disk"]}G"
        bus        = "sata"
        format     = "qcow2"
      }
    }
  }

  provisioner "ansible" {
    playbook_file = "${abspath(path.root)}/libvirt_conf.yml"
    
    use_sftp = false
    use_proxy = false

    host_alias = source.name
    user = local.os_data[local.machines[source.name]["base_os"]]["username"]

    extra_arguments = var.libvirt_proxy != null ? ["--extra-vars", "proxy=${var.libvirt_proxy}"] : []
    ansible_ssh_extra_args = [var.ansible_ssh_common_args]

    except = var.platform != "libvirt" ? local.machine_builds : []
  }

  provisioner "ansible" {
    playbook_file = "${abspath(path.root)}/elastic_agent.yml"

    use_sftp = false
    use_proxy = false

    host_alias = source.name
    user = local.os_data[local.machines[source.name]["base_os"]]["username"]

    extra_arguments = ["--extra-vars", "elastic_version=${var.elastic_version} ansible_become_flags=-i ansible_become=true ansible_no_target_syslog=${var.remove_ansible_logs}"]
    ansible_ssh_extra_args = [var.ansible_ssh_common_args]

    except = local.not_endpoint_monitoring_machines
  }

  provisioner "ansible" {
    playbook_file = (fileexists("${var.ansible_playbooks_path}/base_config.yml") ? 
      "${var.ansible_playbooks_path}/base_config.yml" :
      "/dev/null")

    use_sftp = false
    use_proxy = false

    host_alias = source.name
    user = local.os_data[local.machines[source.name]["base_os"]]["username"]

    ansible_ssh_extra_args = [var.ansible_ssh_common_args]

    extra_arguments = concat((local.machines[source.name]["base_os"] == "windows_srv_2022" ?
      # Set powershell and become method for windows
      ["-vvv","--extra-vars", format("ansible_shell_type=powershell ansible_become_method=runas ansible_become_user=%s",
                    local.os_data[local.machines[source.name]["base_os"]]["username"])] :
      # Load environment for sudo in linux (so that the proxy is configured, if necessary)
      ["--extra-vars", "ansible_become_flags=-i"]),
      var.ansible_scp_extra_args != "" ? ["--scp-extra-args", "${var.ansible_scp_extra_args}"] : [],
      # Common vars for all machines:
      ["--extra-vars", "basename=${source.name} instances=${var.instance_number} ansible_become=true ansible_no_target_syslog=${var.remove_ansible_logs}"])


    except = !fileexists("${var.ansible_playbooks_path}/base_config.yml") ? local.machine_builds : []
  }

  # Clean cloud-init configuration, so it runs again after clone
  provisioner "shell" {
    inline = [ 
      "sudo systemctl stop cloud-init",
      "sudo cloud-init clean --logs",
    ]
    except = local.win_machines
  }
}

