## Tectonic Configuration File
Tectonic general behaviour can be configured using an ini file with
a main `config` section and sections for `aws`, `libvirt` and
`elastic`, as appropriate. The available options are:

### [config] section:
* `platform`: The underlying platform to deploy the Cyber Range in.
  Can be either `aws` or `libvirt`. Default: `aws`.
* `lab_repo_uri`: The URI of a repository of labs to use in the Cyber
  Range. Must be a local directory that contains either a subdirectory
  or a .ctf package file for each lab. Relative paths will be assumed
  to be relative to the tectonic main directory.
* `network_cidr_block`: The network block to use for the lab. Must be
  a `/16` private block. Default: `10.0.0.0/16`.
* `internet_network_cidr_block`: The network block to use for services that require internet access. Default: `10.0.0.0/25`.
* `services_network_cidr_block`: The network block to use for services. Default: `10.0.0.128/25`.
* `ssh_public_key_file`: SSH public key to connect to machines for
  installation and configuration. Default: `~/.ssh/id_rsa.pub`.
* `ansible_ssh_common_args`: SSH arguments for ansible connetion.
  Proxy Jump configuration through bastion hosts is added
  automatically by Tectonic. Default: `-o
  UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no`.
* `configure_dns`: Whether to add the guest names to the lab DNS. The
  names are of the form `basename-instance[-copy]`. Default: `true`.
* `gitlab_backend_url`: Gitlab terraform state url to use for state
  syncronization and sharing. Default: *None*. **Required option.**
* `debug`: Show debug messages during execution (also shows stack
  trace on error). Default: `yes`.
* `keep_ansible_logs`: Keep Ansible logs on guests. Default: `no`.

### [aws] section:
* `aws_region`: The region to deploy instances in AWS. Default:
  `us-east-1`.
* `aws_default_instance_type`: Default instance type to use for
  machines. Can be overwritten in the per guest configuration in the
  lab description file (attribute `instance_type`, see
  [ref](description)). Default: `t2.micro`.
* `teacher_access`: Type of teacher access to configure. Can be either
  `host` (an instance that acts as a bastion host), or `endpoint` (an
  EIC endpoint that connects to all instances in the lab). Default:
  `host`.
* `packetbeat_vlan_id`: VLAN id used for traffic mirroring. Default:
  `1`.

### [libvirt] section:
* `libvirt_uri`: URI to connect to libvirt server. Default:
  `qemu:///system`.
* `libvirt_storage_pool`: Name of (pre-existing) storage pool where
  images will be created. Default: `default`.
* `libvirt_student_access`: How student access should be configured:
  port forwarding in the libvirt server (`port_forwarding`) or adding
  NICs to the entry points in a bridged network (`bridge`). Default:
  `port-forwarding`.
* `libvirt_bridge`: Name of the libvirt server bridge to use for
  student access. Required if `libvirt_student_access` is `bridge`.
* `libvirt_external_network`: CIDR block of the external bridged
  network, if appropriate. Static IP addresses are assigned
  sequentially to lab entry points. Default: `192.168.44.0/25`.
* `libvirt_proxy`: Proxy configuration to use inside guest machines,
  if necessary for web access. Default: no proxy.

### [elastic] section:
* `elastic_stack_version`: Elastic Stack version to use. Use `latest` for latest version or assign a specific version. Default: `latest`.
* `packetbeat_policy_name`: Packetbeat policy agent name. Do not use this name for custom agent policies. Default: `Packetbeat`.
* `endpoint_policy_name`: Endpoint policy agent name. Do not use this name for custom agent policies. Default: `Endpoint`.

You can find an example configuration file with the default values
[here](./python/tectonic.ini).

The `tectonic` program also accepts command line arguments for all
of these options. See `tectonic.py --help` for detailed information.
Command line options have precedence over the values configured in the
ini file.

