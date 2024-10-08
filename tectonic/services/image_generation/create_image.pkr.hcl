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
    docker = {
      version = ">= 1.0.8"
      source = "github.com/hashicorp/docker"
    }
  }
}


variable "platform" {
  type        = string
  description = "Whether to create images in AWS or use libvirt."

  validation {
    condition = can(regex("^(aws|libvirt|docker)$", var.platform))
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

  platform_to_buildtype = { "aws": "amazon-ebs", "libvirt": "libvirt", "docker":"docker" }

  build_type = local.platform_to_buildtype[var.platform]
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
variable "proxy" {
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
  description = "Use Elastic Stack latest version."
}

variable "elasticsearch_memory" {
  type = number
  description = "Elasticsearch JVM memory to use."
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

source "docker" "machine" {
  commit = true
  discard = false
  privileged = true
  pull = false
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

  dynamic "source" {
    for_each = { for machine_name, m in local.machines: machine_name => m if var.platform == "docker" }
    labels   = [ "docker.machine" ]
    content {
      name = source.key
      image = local.os_data[source.value["base_os"]]["docker_base_image"]
    }
  }

  provisioner "ansible" {
    playbook_file = "${abspath(path.root)}/../../image_generation/libvirt_conf.yml"
    use_sftp = var.platform == "docker"
    use_proxy = var.platform == "docker"
    host_alias = source.name
    user = var.platform == "docker" ? "root" : local.os_data[local.machines[source.name]["base_os"]]["username"]
    extra_arguments = concat(
      var.proxy != null ? ["--extra-vars", "proxy=${var.proxy} platform=${var.platform}"] : ["--extra-vars", "platform=${var.platform}"],
      ["--extra-vars", "ansible_no_target_syslog=${var.remove_ansible_logs}"]
    )
    ansible_ssh_extra_args = [var.ansible_ssh_common_args]

    except = var.platform == "aws" ? local.machine_builds : []
  }

  provisioner "ansible" {
    playbook_file = fileexists("${local.machines[source.name]["ansible_playbook"]}") ? "${local.machines[source.name]["ansible_playbook"]}" : "/dev/null"
    use_sftp = var.platform == "docker"
    use_proxy = var.platform == "docker"
    host_alias = source.name
    user = var.platform == "docker" ? "root" : local.os_data[local.machines[source.name]["base_os"]]["username"]
    ansible_ssh_extra_args = [var.ansible_ssh_common_args]
    extra_arguments = concat(
      ["--extra-vars", "basename=${source.name} platform=${var.platform} ansible_become=true ansible_become_flags=-i ansible_no_target_syslog=${var.remove_ansible_logs}"],
      var.ansible_scp_extra_args != "" ? ["--scp-extra-args", "${var.ansible_scp_extra_args}"] : [],
      ["--extra-vars", "elastic_latest_version=${var.elastic_latest_version}"],
      ["--extra-vars", "elastic_version=${var.elastic_version}"],
      ["--extra-vars", "caldera_version=${var.caldera_version}"],
      ["--extra-vars", "packetbeat_vlan_id=${var.packetbeat_vlan_id}"],
      ["--extra-vars", "elasticsearch_memory=${var.elasticsearch_memory}"],
    )
  }

  # Clean cloud-init configuration, so it runs again after clone
  provisioner "shell" {
    inline = [ 
      "sudo systemctl stop cloud-init",
      "sudo cloud-init clean --logs",
    ]
    except = var.platform != "docker" ? [] : local.machine_builds 
  }

  post-processor "docker-tag" {
    repository =  "${source.name}"
    tags = ["latest"]
    except = var.platform != "docker" ? local.machine_builds : []
  }
}

