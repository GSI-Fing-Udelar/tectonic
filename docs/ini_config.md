## Tectonic Configuration File
Tectonic general behaviour can be configured using an ini file with a
main `config` section and special sections for different platforms
(`aws`, `libvirt`, `docker`) and technologies (`ansnible`, `elastic`,
`caldera`). The available options are:

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
* `configure_dns`: Whether to add the guest names to the lab DNS. The
  names are of the form `basename-instance[-copy]`. Default: `true`.
* `debug`: Show debug messages during execution (also shows stack
  trace on error). Default: `yes`.
* `proxy`: Proxy URL. Default: "" (empty).

### [ansible] section:
* `ssh_common_args`: SSH arguments for ansible connetion. Proxy Jump configuration through bastion hosts is added automatically by Tectonic. Default: `-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=3600 `.
* `keep_logs`: Keep Ansible logs on guests. Default: `no`.
* `forks`: Number of parallel connection for Ansible. If you deploy many instances, increase this number so that the configurations applied with Ansible are faster. Default: `5`
* `pipelining`: Whether pipelining is enabled in order to reduce the number of SSH connections. Default: `no`.
* `timeout`: Ansible connection timeout. Default: `10`.

### [libvirt] section:
* `uri`: URI to connect to libvirt server. Default:
  `qemu:///system`.
* `storage_pool`: Name of (pre-existing) storage pool where
  images will be created. Default: `default`.
* `student_access`: Currently this value must be `bridge`. NICs will be added to the entry points in a bridged network. Default: `bridge`.
* `bridge`: Name of the libvirt server bridge to use for
  student access. Required if `libvirt_student_access` is `bridge`.
* `external_network`: CIDR block of the external bridged
  network, if appropriate. Static IP addresses are assigned
  sequentially to lab entry points. Default: `192.168.0.0/25`.
* `bridge_base_ip`: Base number from which to assign static IP address in bridged networks. Default: `10`.

### [aws] section:
* `region`: The region to deploy instances in AWS. Default:
  `us-east-1`.
* `default_instance_type`: Default instance type to use for
  machines. Can be overwritten in the per guest configuration in the
  lab description file (attribute `instance_type`, see
  [ref](description)). Default: `t2.micro`.
* `teacher_access`: Type of teacher access to configure. Can be either
  `host` (an instance that acts as a bastion host), or `endpoint` (an
  EIC endpoint that connects to all instances in the lab). Default:
  `host`.
* `packetbeat_vlan_id`: VLAN id used for traffic mirroring. Default:
  `1`.

### [docker] section:
* `uri`: URI to connect to docker server. Default: `unix:///var/run/docker.sock`
* `dns`: DNS server to use in internet network. leave empty to use Docker defaults. Default: `8.8.8.8`.

### [elastic] section:
* `elastic_stack_version`: Elastic Stack version to use. Use `latest` for latest version or assign a specific version. Default: `8.14.3`. All tests were performed on version 8.14.3 so we recommend using it. However, it may also work for new Elastic features.
* `packetbeat_policy_name`: Packetbeat policy agent name. Do not use this name for custom agent policies. Default: `Packetbeat`.
* `endpoint_policy_name`: Endpoint policy agent name. Do not use this name for custom agent policies. Default: `Endpoint`.
* `user_install_packetbeat`: When using Docker or Libvirt and traffic type as monitoring, Packetbeat must be deployed on the host. This variable modifies the user used by Ansible for this task. Keep in mind that this user needs to be able to escalate privileges to root without a password. To do this you can configure the sudoers file. Default: `tectonic`. 

### [caldera] section:
* `version`: Caldera version to use. Use `latest` for latest version or assign a specific version. Default: `latest`.

You can find an example configuration file with the default values
[here](./tectonic/tectonic.ini).

The `tectonic` program also accepts command line arguments for all
of these options. See `tectonic.py --help` for detailed information.
Command line options have precedence over the values configured in the
ini file.

