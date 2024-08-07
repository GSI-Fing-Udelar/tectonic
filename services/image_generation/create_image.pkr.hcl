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
variable "os_data_json" {
  type = string
  description = "A JSON encoded map of operating system information."
}
variable "machines_json" {
  type        = string
  description = "A JSON encoded map of machine information."
}

locals {
  machines = jsondecode(var.machines_json)
  os_data = jsondecode(var.os_data_json)

  build_type = var.platform == "aws" ? "amazon-ebs" : "libvirt"
  machine_builds = [ for m, _ in local.machines : "${local.build_type}.${m}" ]

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

#Elastic variables
variable "elastic_version" {
  type = string
  description = "Elastic Stack version to install."
}
variable "elastic_latest_version" {
  type = string
  description = "Use Elastic Stack latest version"
}

#Caldera variables
variable "caldera_version" {
  type = string
  description = "Caldera version to install."
}

#Packetbeat variables
variable "packetbeat_vlan_id" {
  type = string
  description = "Packetbeat VLAN ID."
}

variable "remove_ansible_logs" {
  type = string
  description = "Remove Ansible logs on managed host."
  default = "true"
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
      ami_name = "${source.key}"
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
      communicator         = "ssh"
      ssh_username = local.os_data[source.value["base_os"]]["username"]
      launch_block_device_mappings {
        device_name = "/dev/sda1"
        volume_size = "${source.value["disk"]}"
        volume_type = "gp2"
      }
      snapshot_tags = {
        "Name" = "${source.key}"
      }
      tags = {
	      "Name" = "${source.key}"
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
      }
      vcpu   = source.value["vcpu"]
      memory = source.value["memory"]
      volume {
        name = "${source.key}"
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
    playbook_file = "${abspath(path.root)}/../../image_generation/libvirt_conf.yml"
    use_sftp = false
    use_proxy = false
    host_alias = source.name
    user = local.os_data[local.machines[source.name]["base_os"]]["username"]
    extra_arguments = concat(
      var.libvirt_proxy != null ? ["--extra-vars", "proxy=${var.libvirt_proxy}"] : [],
      ["--extra-vars", "ansible_no_target_syslog=${var.remove_ansible_logs}"]
    )
    ansible_ssh_extra_args = [var.ansible_ssh_common_args]
    except = var.platform != "libvirt" ? local.machine_builds : []
  }

  provisioner "ansible" {
    playbook_file = fileexists("${local.machines[source.name]["ansible_playbook"]}") ? "${local.machines[source.name]["ansible_playbook"]}" : "/dev/null"
    use_sftp = false
    use_proxy = false
    host_alias = source.name
    user = local.os_data[local.machines[source.name]["base_os"]]["username"]
    ansible_ssh_extra_args = [var.ansible_ssh_common_args]
    extra_arguments = concat(
      ["--extra-vars", "basename=${source.name} platform=${var.platform} ansible_become=true ansible_become_flags=-i ansible_no_target_syslog=${var.remove_ansible_logs}"],
      var.ansible_scp_extra_args != "" ? ["--scp-extra-args", "${var.ansible_scp_extra_args}"] : [],
      var.elastic_latest_version == "yes" ? ["--extra-vars", "elastic_latest_version=true"] : ["--extra-vars", "elastic_latest_version=false"],
      ["--extra-vars", "elastic_version=${var.elastic_version}"],
      ["--extra-vars", "caldera_version=${var.caldera_version}"],
      ["--extra-vars", "packetbeat_vlan_id=${var.packetbeat_vlan_id}"]
    )
  }

  # Clean cloud-init configuration, so it runs again after clone
  provisioner "shell" {
    inline = [ 
      "sudo systemctl stop cloud-init",
      "sudo cloud-init clean --logs",
    ]
  }
}

