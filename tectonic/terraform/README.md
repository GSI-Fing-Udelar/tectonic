# Tectonic Main Terraform Modules

Terraform modules to deploy a lab scenario to either AWS, Libvirt or Docker.

The modules have four required variables:
- `os_data_json`: A JSON encoded map of operating system information.
- `guest_data_json`: The map with all guest data, in JSON format.
- `tectonic_json`: A JSON encoded map of tectonic configuration.
- `subnets_json`: A JOSN map from subnetwork names to cidr blocks.

