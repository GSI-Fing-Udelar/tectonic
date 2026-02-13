## Network Topology

### Networks
A scenario has a `/16` network defined according to the
`network_cidr_block` variable located in the ini config file (by
default `10.0.0.0/16`). Within this network, a `/24` subnetwork is
generated for each scenario instance, so that instance `i` gets
network `10.0.i.0/24`. 

We divide each instance's `10.0.i.0/24` block by the number of
networks defined in the scenario. If `N` is the total number of
defined networks, then network `k` of instance `i` will be assigned
the block:

$$
10.0.i.(k\times 2^{(8-x)})\ /\ (24+x)
$$

where $x = log_2(N)$

Each subnetwork will allow a maximum of $2^{(8-x)}-4$ hosts. This is
because the first three and the last IP in a subnet are reserved.

For example: 

- For scenarios with 1 network:
  + instance networks: `10.0.i.0/24`
  + max instances: 200
  + max hosts per network: 252
- For scenarios with 2 networks:
  + instance networks: `10.0.i.0/25` and `10.0.i.128/25`
  + max instances: 100
  + max hosts per network: 124
- For scenarios with 3 or 4 network:
  + instance networks: `10.0.i.0/26`,  `10.0.i.64/26`, `10.0.i.128/26` and `10.0.i.192/26`
  + max instances: 50
  + max hosts per network: 60

Within each subnetwork, IP addresses are assigned sequentially
(starting on the fourth available) to each machine in the order they
appear in the network `members` attribute, taking copies into account.

Taking the following scenario as an example:
```
guest_settings:
  attacker:
    copies: 1
  victim:
    copies: 2
topology:
  - name: internal
    members:
      - attacker
      - victim
  - name: external
    members:
      - attacker
```

The `attacker` of instance 1 will have IP `10.0.1.4/25` in the
`internal` network and will have IP `10.0.1.132/25` in the `external`
network. Similarly, the `attacker` of instance 2 will have the IPs
`10.0.2.4/25` and `10.0.2.132/25`. The first copy of the `victim`
machine of instance 1 will have IP `10.0.1.5/25`, while the second
copy will have IP `10.0.1.6/25`.

The `internet_network_cidr_block` and `services_network_cidr_block`
subnets (defined in the ini config file) are special networks used to
locate services (Elastic, Caldera, Guacamole and Bastion Host) and allow them to access the
internet. These subnets cannot be the same as the subnets used to
locate scenario instances, and are by default assigned networks in the
range `10.0.0.0/24` which is unused by instances.


### Routing
The `routing` option in the tectonic.ini file controls whether routing exists between networks. 

By default, `routing: no`. In this case, network traffic will be blocked between different subnetworks (either within the same instance or to other instances). All traffic within a subnetwork will be allowed. In other words, for two machines to be able to communicate they must be on the same subnetwork.

If `routing: yes`, the enabled traffic depends on the rules specified in `traffic_rules` section of the scenario [description file](https://github.com/GSI-Fing-Udelar/tectonic/blob/feature/routing_trafficrules/docs/description.md). If no rules are specified, 
then only traffic within the same subnet is allowed, and all other traffic is denied (similar to the `routing: no` case). Otherwise, traffic is enabled according to the rules specified in the scenario description. With routing enabled and the correct traffic rules, it is possible for two machines of the same instance to communicate even though they are on different subnetworks.

For technical differences between platforms, the `routing` option has the following behavior:
  - In Docker it always has the value `no`. Therefore, routing is not possible on this platform.
  - In Libvirt it can take the value `yes` or `no`, at the user's discretion.
  - In AWS it always has the value `yes`.

### Traffic
The traffic in a scenario follows these rules:
 - Traffic is allowed from the service network to the guests in the scenario and vice versa. This will depend on the deployed services and guest configuration options such as `monitor`, `red_team_agent`, `blue_team_agent`, among others.
 - Traffic between guests on the same instance is permitted. This traffic depends on rules specified in the `traffic_rules` section; if this section is omitted, only traffic within the same subnet is allowed.
 - Internet access is permitted for some services. For guests, it is enabled with the `internet_access` option (disabled by default) .
 - All other traffic is denied.

#### Services traffic
Regarding services, the following traffic is allowed.

##### Elastic
-  Guests have access to the `elastic` server on ports 5044/tcp and 8220/tcp if the `monitor: yes` option is set in the guest description and `monitor_type: endpoint` is set in the elastic_settings section of the description file. If `monitor_type: network`, then the guests do not have access to `elastic`. Instead, `packetbeat` will have this access.
- The `elastic` server has internet access.
- The `bastion_host` has access to `elastic` on port 5601/tcp.

If `routing: no`, then in order for guests to reach Elastic, it is necessary that the guests have an interface on the services network (`services_network_cidr_block`).

##### Caldera
- Guests have access to `caldera` on ports 443/tcp, 7010/tcp, 7011/udp if the `red_team_agent: yes` and/or `blue_team_agent: yes` options are set in the guest description.
- The `bastion_host` has access to `caldera` on port 8443/tcp.

If `routing: no`, then in order for guests to reach Caldera, it is necessary that the guests have an interface on the services network (`services_network_cidr_block`).

##### Guacamole
- `Guacamole` has access to guests on ports 22/tcp (SSH) and 3389/tcp (RDP).
- The `bastion_host` has access to `guacamole` on port 10443/tcp.

If `routing: no`, then in order for Guacamole to reach guests, it is necessary that the guests have an interface on the services network (`services_network_cidr_block`).

##### Moodle
- The `bastion_host` has access to `moodle` on port 443/tcp.

##### Bastion Host
- The ports indicated with the `external_port` option for each of the services in the tectonic.ini file are accessible. In the case of AWS, access is enabled for the entire internet. In the case of Libvirt and Docker, it is possible to access these ports from the host where the deployment is performed.

##### Teacher Access Host
- It is used exclusively in AWS. From this machine, it is possible to access all guests in the scenario via port 22/tcp using the SSH protocol. For Libvirt and Docker, SSH access to port 22/tcp is enabled directly from the host where the deployment is performed.
