# Image Generation

This directory contains a [Packer template](create_image.pkr.hcl) used
to create and configure VMs disks (either AMIs in AWS or libvirt qcow2
images) based on an Ansible playbook, for use in Cyber Range lessons.
The template has four required variables:
- `platform`: Whether to create images in AWS or use libvirt. Values:
  `aws` or `libvirt`.
- `institution`: The institution that created the lesson. Example:
  `udelar`.
- `lab_name`: The name of the lesson. Examples:
  `mitm`,`privilege_escalation`, `reverse_shell`.
- `ansible_ssh_common_args`: SSH arguments for ansible connection to machine.
- `ansible_playbooks_path`: Path to the ansible playbooks. A playbook
  named `base_config.yml` will be run, if found.
- `os_data_json`: A JSON encoded map of operating system information.
- `machines_json`: A JSON encoded map of machine information.

The created image will be named `<institution>-<lesson>-<machine>`.
If an image of the same name already exists, it will be deleted and a
new one will be created from scratch.

