# Image Generation

This directory contains a [Packer template](create_image.pkr.hcl) used
to create and configure VMs disks (either AMIs in AWS or libvirt qcow2
images) based on an Ansible playbook, for use in Cyber Range lessons.
The template has six required variables:
- `ansible_scp_extra_args`: SCP extra arguments for ansible connection.
- `os_data_json`: A JSON encoded map of operating system information.
- `machines_json`: A JSON encoded map of machine information.
- `tectonic_json`: A JSON encoded map of Tectonic description and configuration.
- `networks_json`: A JSON encoded map of network information.
- `guests_json`: A JSON encoded map of guests information.

The created image will be named `<institution>-<lesson>-<machine>`.
If an image of the same name already exists, it will be deleted and a
new one will be created from scratch.

