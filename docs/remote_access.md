## Access to instances
Access to the cyber range machines is via SSH. The trainer's authentication method is through a public/private key.

We are working on incorporating other access methods such as Guacamole.

### Trainer access:
To access any host in the scenario, including services, the trainer can use the command:

```
tectonic -c <ini_conf_file> <lab_edition_file> console -i <instance> -g <guest> -c <copy>
```

Another way to access is through SSH connections. In this case, the connection depends on the `platform` used.

#### AWS

```
ssh -J ubuntu@<teacher_access_ip> <admin_username>@<machine_ip>
```

where:
 - `teacher_access_ip`: is obtained from the output of the `info` command.
 - `admin_username`: it depends on the machine's OS. See the [description](./description.md) for more details.
 - `machine_ip`: is obtained from the output of the `list` command.

#### Libvirt and Docker

```
ssh <admin_username>@<machine_ip>
```
where:

 - `admin_username`: it depends on the machine's OS. See the [description](./description.md) for more details.
 - `machine_ip`: is obtained from the output of the `list` command.

Note: In the case of Docker, it only works if you're using Linux. For macOS and Windows, use the `console` command.


### Trainee access

The connection method depends on the type of `platform` used. The trainee can only access the machines that were marked as `entry_point` in the description. The trainee's authentication method will be through a public/private key or passwords as defined in the lab edition file. If passwords are used, they can be obtained with the `info` command.

#### AWS

```
ssh -J traineeXX@<student_access_ip> traineeXX@<machine_ip>
```

where:
 - `XX`: will be the instance number assigned to the user.
 - `student_access_ip`: is obtained from the output of the `info` command.
 - `machine_ip`: is obtained from the output of the `list` command.

#### Libvirt

```
ssh traineeXX@<machine_ip>
```
where:
 - `XX`: will be the instance number assigned to the user.
 - `machine_ip`: it depends on the `external_network` and `bridge_base_ip` options in the ini config file. Assuming a scenario with a single `entry_point` per instance, then the entry_point of instance X will have the IP `bridge_base_ip` + X within the `external_network`. Taking the default values ​​of these variables, the entry_point of instance 1 will have the IP 192.168.0.11, that of instance 2 the IP 192.168.0.12 and so on.

#### Docker

Not applicable since Docker is used solely as a development and testing environment for the scenarios.
