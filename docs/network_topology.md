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


### Traffic
Network traffic will be blocked between different subnetworks (either
within the same instance or to other instances). All traffic within a
subnetwork will be allowed. In the case of AWS, a machine may have
internet access if the `internet_access: yes` option is set in the
description at the guest level.

Machines will only have access to the Elastic server if the `monitor:
yes` option is set in the guest description. Similarly, they will only
have access to the Caldera server if the `red_team_agent: yes` and/or
`blue_team_agent: yes` options are set.
