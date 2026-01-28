## Tectonic Configuration File
Tectonic general behaviour can be configured using an ini file with a
main `config` section and special sections for different platforms
(`aws`, `libvirt`, `docker`) and technologies (`ansible`, `elastic`,
`caldera`, `guacamole`). The available options are:

### [config] section:
* `platform`: The underlying platform to deploy the Cyber Range in.
  Can be `aws`, `libvirt` or `docker`. Default: `docker`.
* `lab_repo_uri`: The URI of a repository of labs to use in the Cyber
  Range. Must be a local directory that contains either a subdirectory
  or a .ctf package file for each lab. Relative paths will be assumed
  to be relative to the directory that contains the ini file.
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
* `routing`: Enable routing and the use of traffic filtering rules to specify more complex scenarios. Currently only available on AWS and Libvirt. Default: `no`. In AWS this option is forced to take the value `yes` and in Docker the value `no`.

### [ansible] section:
* `ssh_common_args`: SSH arguments for ansible connection. Proxy Jump
  configuration through bastion hosts is added automatically by
  Tectonic. Default: `-o UserKnownHostsFile=/dev/null -o
  StrictHostKeyChecking=no -o ControlMaster=auto -o
  ControlPersist=3600 `.
* `keep_logs`: Keep Ansible logs on guests. Default: `no`.
* `forks`: Number of parallel connection for Ansible. If you deploy
  many instances, increase this number so that the configurations
  applied with Ansible are faster. Default: `5`
* `pipelining`: Whether pipelining is enabled in order to reduce the
  number of SSH connections. Default: `no`.
* `timeout`: Ansible connection timeout in seconds. Default: `10`.

### [libvirt] section:
* `uri`: URI to connect to libvirt server. Default:
  `qemu:///system`.
* `storage_pool`: Name of (pre-existing) storage pool where images
  will be created. Default: `default`.
* `student_access`: Currently this value must be `bridge`. NICs will
  be added to the entry points in a bridged network. Default:
  `bridge`.
* `bridge`: Name of the libvirt server bridge to use for student
  access. Required if `libvirt_student_access` is `bridge`. Default:
  `tectonic`.
* `external_network`: CIDR block of the external bridged network, if
  appropriate. Static IP addresses are assigned sequentially to lab
  entry points. Default: `192.168.0.0/25`.
* `bridge_base_ip`: Base number from which to assign static IP address
  in bridged networks. Default: `10`.

### [aws] section:
* `region`: The region to deploy instances in AWS. Default:
  `us-east-1`.
* `teacher_access`: Type of teacher access to configure. Can be either
  `host` (an instance that acts as a bastion host), or `endpoint` (an
  EIC endpoint that connects to all instances in the lab). Default:
  `host`.
* `access_host_instance_type`: The instance type to use for the `bastion_host` machine. Default: `t2.micro`.
* `packetbeat_vlan_id`: VLAN id used for traffic mirroring. Default:
  `1`.

### [docker] section:
* `uri`: URI to connect to docker server. Default: `unix:///var/run/docker.sock`
* `dns`: DNS server to use in internet network. Leave empty to use Docker defaults. Default: `8.8.8.8`.

### [elastic] section:
* `elastic_stack_version`: Elastic Stack version to use. Use `latest`
  for latest version (on 8.X) or assign a specific version. Default:
  `9.1.0`. All tests were performed on version 9.1.0 so we recommend
  using it. However, it may also work for older or new Elastic
  versions.
* `packetbeat_policy_name`: Packetbeat policy agent name. Do not use
  this name for custom agent policies. Default: `Packetbeat`.
* `endpoint_policy_name`: Endpoint policy agent name. Do not use this
  name for custom agent policies. Default: `Endpoint`.
* `user_install_packetbeat`: When using Docker or Libvirt and monitor
  type is configured as `traffic` in the scenario description,
  Packetbeat must be deployed on the host. This variable modifies the
  user used by Ansible for this task. Keep in mind that this user
  needs to be able to escalate privileges to root without a password.
  To do this you can configure the sudoers file. Default: `tectonic`.
* `external_port`: Port on which the service is offered. If using Docker, do not make use of privileged ports. Default: `5601`.

### [caldera] section:
* `version`: Caldera version to use. Use `latest` for latest version
  or assign a specific version. Default: `5.3.0`. All tests were
  performed on version 5.3.0 so we recommend using it. However, it may
  also work for older or newer Caldera versions.
* `ot_enabled`: Enable [OT plugins](https://github.com/mitre/caldera-ot) for Caldera. Default: `no`.
* `external_port`: Port on which the service is offered. If using Docker, do not make use of privileged ports. Default: `8443`.

### [guacamole] section:
* `version`: Guacamole version to use. Use `latest` for latest version
  or assign a specific version. Default: `1.6.0`. All tests were
  performed on version 1.6.0 so we recommend using it. However, it may
  also work for older or newer Guacamole versions.
* `brute_force_protection_enabled`: Whether Guacamole's brute force protection should be enabled. See [Guacamole brute force protection](https://guacamole.apache.org/doc/1.6.0/gug/auth-ban.html#securing-guacamole-against-brute-force-attacks). Default: `no`.
* `external_port`: Port on which the service is offered. If using Docker, do not make use of privileged ports. Default: `10443`.

### [moodle] section:
* `version`: Moodle version to use. Use `latest` for latest version or assign a specific version. Default: `5.1.0`. All tests were performed on version `5.1.0` so we recommend using it. However, it may also work for older or newer Moodle versions.
* `site_fullname`: Moodle site full name. Default: `Tectonic Moodle`.
* `site_shortname`: Moodle site short name. Default: `Tectonic`.
* `admin_email`: Email for administrator account. Default: `admin@tectonic.local`
* `external_port`: Port on which the service is offered. If using Docker, do not make use of privileged ports. Default: `8080`.

### [bastion_host] section
* `domain`:Domain name used.


You can find an example configuration file with the default values
[here](../tectonic.ini).

The `tectonic` program also accepts command line arguments for the
most common of these options. See `tectonic.py --help` for detailed
information. Command line options have precedence over the values
configured in the ini file.

