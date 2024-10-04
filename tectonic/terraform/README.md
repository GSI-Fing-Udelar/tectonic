# Tectonic Main Terraform Modules

Terraform modules to deploy a lab scenario to either AWS or libvirt.


## Scenario Specification
The virtual machine configuration and scenario topology are specified in the variable `guest_data_json`.

It is a map from guest instance names to data that includes:

- `guest_name`: the name of this particular instance machine (e.g.: `udelar-mitm-1-server-2`).
- `base_name`: the base name of the machine (e.g.: `server`).
- `instance`: the instance number of the machine (e.g.: `1`).
- `copy`: the copy number of the machine (e.g.: `2`).
- `hostname`: the DNS hostname of the machine (e.g.: `server-1-2`).
- `entry_point`: whether the machine can be accessed by the students
  to enter the scenario.
- `entry_point_index`: An index, starting in 1, of entry points. This
  is used by the libvirt module to assign consecutive IP addresses in
  bridged networks or consecutive ports if student access is done
  through port-forwarding.
- `internet_access`: whether the machine has access to the internet
  (*Note:* this might be expensive in AWS).
- `instance_type`: The type of machine to create in AWS (e.g.: `t2.micro`).
- `memory`: The amount of RAM in megabytes for libvirt machines (e.g.: `1024`).
- `vcpu`: The number of virtual CPUs for libvirt machines (e.g.: `1`).
- `base_os`: The operating system name of the machine (must be one of
  the listed in the variable `os_data`).
- `interfaces`: A list of network interfaces of the machine (see next).
- `advanced_options_file`: path to advanced options file to be used in libvirt (see this [link](https://github.com/multani/terraform-provider-libvirt/tree/master/examples/v0.13/xslt) for more information).
- `endpoint_monitoring`: whether the machine is monitored using the Elastic endpoint.
- `endpoint_monitoring_index`: An index, starting in 1, of entry points. This is used by the libvirt module to assign consecutive IP addresses in monitoring network.


### Network Interface specification
The network_interface object has the following attributes:

- `name`: The identifying name of the interface (e.g.: `udelar-mitm-1-server-2-1`).
- `index`: The index of the interface in the guest machine.
- `guest_name`: The complete name of the guest machine.
- `network_name`: The name of the network this interface is connected to (e.g.: `internal`).
- `subnetwork_name`: The identifying name of the subnetwork this interface is connected to (e.g.: `udelar-mitm-1-internal`).
- `private_ip`: The interface IP address.
- `mask`: The network mask.

### Example Usage
A possible specification for two instances of a *Man in the Middle* scenario with four machines (a server, two copies of a victim and the attacker) can be:

```
guest_data = {
  udelar-mitm-1-attacker = {
    guest_name = "udelar-mitm-1-attacker"
	base_name = "attacker"
	instance = 1
	copy = 1
	hostname = "attacker-1"
	entry_point = true
	internet_access = false
	instance_type = "t2.micro"
	base_os = "kali"
	interfaces = {
	  udelar-mitm-1-attacker-1 = {
		  name = "udelar-mitm-1-attacker-1"
		  index = 0
		  guest_name = "udelar-mitm-1-attacker"
		  network_name = "internal"
		  subnetwork_name = "udelar-mitm-1-internal"
		  private_ip = "10.0.1.4"
	  }
	}
	advanced_options_file = "../../advanced_options/attacker.xsl"
	endpoint_monitoring = true
	endpoint_monitoring_index = 1
  }
  udelar-mitm-1-server = {
    guest_name = "udelar-mitm-1-server"
	base_name = "server"
	instance = 1
	copy = 1
	hostname = "server-1"
	entry_point = true
	internet_access = false
	instance_type = "t2.micro"
	base_os = "rocky8"
	interfaces = {
	  udelar-mitm-1-server-1 = {
		  name = "udelar-mitm-1-server-1"
		  index = 0
		  guest_name = "udelar-mitm-1-server"
		  network_name = "internal"
		  subnetwork_name = "udelar-mitm-1-internal"
		  private_ip = "10.0.1.5"
	  }
	}
	endpoint_monitoring = false
  }
  udelar-mitm-1-victim-1 = {
    guest_name = "udelar-mitm-1-victim-1"
	base_name = "victim"
	instance = 1
	copy = 1
	hostname = "victim-1-1"
	entry_point = true
	internet_access = false
	instance_type = "t2.micro"
	base_os = "ubuntu22"
	interfaces = {
	  udelar-mitm-1-victim-1-1 = {
		  name = "udelar-mitm-1-victim-1-1"
		  index = 0
		  guest_name = "udelar-mitm-1-victim-1"
		  network_name = "internal"
		  subnetwork_name = "udelar-mitm-1-internal"
		  private_ip = "10.0.1.6"
	  }
	}
	endpoint_monitoring = true
	endpoint_monitoring_index = 2
  }
  udelar-mitm-1-victim-2 = {
    guest_name = "udelar-mitm-1-victim-2"
	base_name = "victim"
	instance = 1
	copy = 2
	hostname = "victim-1-2"
	entry_point = true
	internet_access = false
	instance_type = "t2.micro"
	base_os = "ubuntu22"
	interfaces = {
	  udelar-mitm-1-victim-2-1 = {
		  name = "udelar-mitm-1-victim-2-1"
		  index = 0
		  guest_name = "udelar-mitm-1-victim-2"
		  network_name = "internal"
		  subnetwork_name = "udelar-mitm-1-internal"
		  private_ip = "10.0.1.7"
	  }
	}
  }


  udelar-mitm-2-attacker = {
    guest_name = "udelar-mitm-2-attacker"
	base_name = "attacker"
	instance = 2
	copy = 1
	hostname = "attacker-2"
	entry_point = true
	internet_access = false
	instance_type = "t2.micro"
	base_os = "kali"
	interfaces = {
	  udelar-mitm-2-attacker-1 = {
		  name = "udelar-mitm-2-attacker-1"
		  index = 0
		  guest_name = "udelar-mitm-2-attacker"
		  network_name = "internal"
		  subnetwork_name = "udelar-mitm-2-internal"
		  private_ip = "10.0.2.4"
	  }
	}
  }
  udelar-mitm-2-server = {
    guest_name = "udelar-mitm-2-server"
	base_name = "server"
	instance = 2
	copy = 1
	hostname = "server-2"
	entry_point = true
	internet_access = false
	instance_type = "t2.micro"
	base_os = "rocky8"
	interfaces = {
	  udelar-mitm-2-server-1 = {
		  name = "udelar-mitm-2-server-1"
		  index = 0
		  guest_name = "udelar-mitm-2-server"
		  network_name = "internal"
		  subnetwork_name = "udelar-mitm-2-internal"
		  private_ip = "10.0.2.5"
	  }
	}
  }
  udelar-mitm-2-victim-1 = {
    guest_name = "udelar-mitm-2-victim-1"
	base_name = "victim"
	instance = 2
	copy = 1
	hostname = "victim-2-1"
	entry_point = true
	internet_access = false
	instance_type = "t2.micro"
	base_os = "ubuntu22"
	interfaces = {
	  udelar-mitm-2-victim-1-1 = {
		  name = "udelar-mitm-2-victim-1-1"
		  index = 0
		  guest_name = "udelar-mitm-2-victim-1"
		  network_name = "internal"
		  subnetwork_name = "udelar-mitm-2-internal"
		  private_ip = "10.0.2.6"
	  }
	}
  }
  udelar-mitm-2-victim-2 = {
    guest_name = "udelar-mitm-2-victim-2"
	base_name = "victim"
	instance = 2
	copy = 2
	hostname = "victim-2-2"
	entry_point = true
	internet_access = false
	instance_type = "t2.micro"
	base_os = "ubuntu22"
	interfaces = {
	  udelar-mitm-2-victim-2-1 = {
		  name = "udelar-mitm-2-victim-2-1"
		  index = 0
		  guest_name = "udelar-mitm-2-victim-2"
		  network_name = "internal"
		  subnetwork_name = "udelar-mitm-2-internal"
		  private_ip = "10.0.2.7"
	  }
	}
  }
}
```

## Network Topology (AWS)
A **vpc** is created for the scenario using the $/16$ IP block
`network_cidr_block` (for example $10.0.0.0/16$). Within this vpc, an
amazon **subnetwork** is created for each network in each instance.

We divide the $10.0.i.0/24$ block into the number of networks defined
in the scenario, where $i$ is the instance number. If $N$ is the
number of defined networks, then network $n$ of instance $i$ will be
assigned the block:

$$
10.0.i.n\times 2^{(8-x)}/(24+x)
$$

where $x = log_2(N)$

Each subnetwork will allow a maximum of $2^{(8-x)}-4$ hosts. The
first 3 hosts of any amazon subnetwork are reserved by amazon, while
the last is the network address.

For example: 

- For scenarios with 1 network:
  + instance networks: $10.0.i.0/24$
  + max instances: 200
  + max hosts per network: 252
- For scenarios with 2 network:
  + instance networks: $10.0.i.0/25$ and $10.0.i.128/25$
  + max instances: 100
  + max hosts per network: 124
- For scenarios with 3 or 4 network:
  + instance networks: $10.0.i.0/26$, $10.0.i.64/26$, $10.0.i.128/26$ and $10.0.i.192/26$
  + max instances: 50
  + max hosts per network: 60

Whithin each subnetwork, IP addresses are assigned sequentially
(starting in 4) to each host, in the order they appear in the network
`members` attribute in the yaml description, taking copies into
account.

In the example above, the second copy of the `victim` of instance 1
will have IP $10.0.1.6/24$, and the `server` of instance 2 will have
IP $10.0.2.7/24$.

Network traffic will be blocked between different subnetworks (either
within the same instance or to other instances). All traffic within a
subnetwork will be allowed.

## After Clone Configuration
An ansible playbook can be specified to perform configuration tasks in
each scenario host. The playbook can access these extra ansible
variables:

- `basename`: the base name of the machine (e.g. `attacker`)
- `instance`: the instance number
- `copy`: the copy number within the instance

`ansible-playbook` will be run locally on the PC running terraform,
and it will connect to the VM through an [EC2 Instance Connect
Endpoint](https://aws.amazon.com/jp/blogs/compute/secure-connectivity-from-public-to-private-introducing-ec2-instance-connect-endpoint-june-13-2023/)
using ssh, or a *bastion host*, depending on the value of the
`teacher_access` variable.

The VM will not have internet access during the execution of the
after-clone playbook, unless the guest has the `internet_access`
attribute set to `true`.

## External Connectivity
### Trainer access:
To access any host of the scenario, a trainer can use the ECI endpoint:
```
ssh ubuntu@<instance_id> -o ProxyCommand='aws ec2-instance-connect open-tunnel --instance-id %h'
```

where `<instance_id>` is the amazon id of the running instance.

Note that ssh access to the instances using appropriate keys must be
working.
