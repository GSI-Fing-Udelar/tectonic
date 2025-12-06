## Ansible

### Config

Modify the Ansible options in the [ini file](./ini_config.md) to
change Ansible's global configurations.

### Facts

In Ansible, by default, facts are always gathered when executing a
playbook. In order to optimize Ansible executions in Tectonic, fact
collection has been disabled by default. Therefore, if your playbooks
need to use facts, make sure to enable them using `gather_facts: yes`
at the playbook level.

### Parameters

These parameters are used to individualize the instances, for example
by configuring unique flag values. Tectonic selects parameters from
the user-provided parameters in the `ansible/parameters` directory,
inside `ndjson` files. These `ndjson` files should contain a value per
line in json format. A value is selected for each parameter in a
pseudo-random manner (based on the value of the `random_seed` option
in the [lab edition file](./description.md#lab-edition-information))
and assigns them to each instance.

The parameters are loaded in the playbook as dictionaries in the `parameters`
variable:

```
parameters['<parameter_file_name>']
```

For example, if there are two parameter files as follows:
+ Filename: `flags.ndjson`:

	```
	"super_secret_flag1"
	"super_secret_flag2"
	... 
	```

+ Filename: `users.ndjson`
```
{"name":"admin1","password":"admin"}
{"name":"admin2","password":"admin"}
...
```

These parameters are used in a playbook as follows:

```
parameters["flags"]
parameters["users"]["name"] and parametes["users"]["password"]
```


### Variables

A set of Ansible variables is available that refer to the Tectonic
configuration and the scenario description. 

#### Base configuration

The variables for the `base_config` playbooks are the following:

- `scenario_dir`: Path to the directory with the scenario definition.
- `ansible_dir`: Path to the directory with the ansible playbooks.
- `config`: Dictionary with configurations associated with parameters of the ini file.
    - `ansible`
        - `ssh_common_args`
        - `keep_logs`
    - `configure_dns`
    - `debug`
    - `internet_network_cidr_block`
    - `platform`
    - `platforms`
        - `aws`
            - `access_host_instance_type`
            - `packetbeat_vlan_id`
            - `region`
            - `teacher_access`
        - `docker`
            - `dns`
        - `libvirt`
            - `bridge_base_ip`
            - `external_network`
    - `proxy`
    - `services_network_cidr_block`
    - `create_students_password`
- `institution`: Institution.
- `lab_name`: Laboratory name.
- `guest`: Base name of the guest.
- `guests`: Configuration parameters of all guest. Each entry in the dictionary contains a guest with the following parameters:
    - `base_os`
    - `blue_team_agent`
    - `copies`
    - `disk`
    - `entry_point`
    - `gui`
    - `hostname`
    - `instance`
    - `instance_type`
    - `interfaces`: Dictionary of the machine’s interfaces.
        - `<interface_name>`
            - `name`
            - `private_ip`
            - `subnetwork_base_name`
            - `subnetwork_cidr`
            - `subnetwork_name`
    - `internet_access`
    - `is_in_services_network`
    - `memory`
    - `monitor`
    - `name`
    - `red_team_agent`
    - `vcpu`
- `networks`: Network configuration. Each entry contains a network with the following parameters:
    - `members`: List of the guest's base_name on the network.
- `services`: Services enabled in the scenario. Each entry in the dictionary contains a service with configuration parameters analogous to those listed for the `guest` variable presented earlier. Additionally, each service has specific configuration parameters. The following lists these parameters for each service.
    - `bastion_host`
        - `<guest_configuracion>`
        - `domain`
    - `caldera`
        - `<guest_configuracion>`
        - `external_port`
        - `internal_port`
        - `ot_enabled`
        - `version`
    - `elastic`
        - `<guest_configuracion>`
        - `deploy_default_policy`
        - `endpoint_policy_name`
        - `external_port`
        - `internal_port`
        - `monitor_type`
        - `packetbeat_policy_name`
        - `user_install_packetbeat`
        - `version`
    - `guacamole`
        - `<guest_configuracion>`
        - `brute_force_protection_enabled`
        - `external_port`
        - `internal_port`
        - `version`

#### After clone configuration

The variables for the `after_clone` playbooks are the same as those for `base_config`. The following variables are added or modified:

- `instances`: Number of total instances.
- `instance`: Guest instance number where the playbook is running.
- `copy`: Guest copy number where the playbook is running.
- `guests`: Configuration of all guests belonging to the instance corresponding to the guest where the playbook is running. It is a dictionary where each entry corresponds to a guest with the same variables as in `base_config` but also include the following:
    - `base_name`
    - `hostname`
    - `instance`
    - `interfaces`: Dictionary of the machine’s interfaces.
        - `<interface_name>`
            - `name`
            - `private_ip`
            - `subnetwork_base_name`
            - `subnetwork_cidr`
            - `subnetwork_name`
    - `is_in_services_network`
    - `name`
- `networks`: Configuration of all networks belonging to the instance corresponding to the guest where the playbook is running. It is a dictionary where each entry corresponds to a network with the following variables.
    - `members`: Dictionary where each entry contains the guest's base_name and its IP address on the network.
    - `network_cidr`
- `random_seed`: Seed used for parameter selection.
- `parameters`: Dictionary with the chosen parameters for the instance.
- `create_students_password`: Whether to create students passwords.
- `ssh_password_login`: Enable password authentication for trainers.
- `student_prefix`: Prefix for naming trainer users.
- `users`: Trainer users. Each entry in the dictionary is a user with the following configuration parameters.
    - `<user_name>`
        - `instance`
        - `password`
        - `password_hash`


If you have any doubts about the variables available on the host where
a playbook is running, you can add the following task to your playbook
to print the variables:

```
- name: Print all variables/facts known for the current host
  ansible.builtin.debug:
    var: hostvars[inventory_hostname]
```

Below is a reference example.

```
"config": {
    "ansible": {
        "keep_logs": false
        "ssh_common_args: "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=3600 "
    }
    "configure_dns": false,
    "debug": true,
    "internet_network_cidr_block": "10.99.0.0/25",
    "network_cidr_block": "10.99.0.0/16",
    "platform": "docker",
    "platforms": {
        "aws": {
            "access_host_instance_type": "t2.micro",
            "packetbeat_vlan_id": "1",
            "region": "us-east-1",
            "teacher_access": "host"
        },
        "docker": {
            "dns": "8.8.8.8"
        },
        "libvirt": {
            "bridge_base_ip": "10",
            "external_network": "192.168.0.0/25"
        }
    },
    "proxy": "http://localhost:3128",
    "services_network_cidr_block": "10.99.0.128/25"
},
"copy": "1",
"create_students_password": true,
"guests": {
    "attacker": {
        "base_name": "attacker",
        "base_os": "ubuntu22",
        "copy": 1,
        "disk": 15,
        "gui": true,
        "hostname": "attacker-1",
        "instance_number": 1,
        "interfaces": {
            "test-test-1-attacker-2": {
                "name": "test-test-1-attacker-2",
                "private_ip": "10.99.1.4",
                "subnetwork_base_name": "internal",
                "subnetwork_cidr": "10.99.1.0/25",
                "subnetwork_name": "test-test-1-internal"
            },
            "test-test-1-attacker-3": {
                "name": "test-test-1-attacker-3",
                "private_ip": "10.99.1.132",
                "subnetwork_base_name": "internal2",
                "subnetwork_cidr": "10.99.1.128/25",
                "subnetwork_name": "test-test-1-internal2"
            }
        },
        "is_in_services_network": true,
        "memory": 1024,
        "name": "test-test-1-attacker",
        "vcpu": 1
    },
    "victim": {
        "base_name": "victim",
        "base_os": "rocky9",
        "copy": 1,
        "disk": 15,
        "gui": true,
        "hostname": "victim-1",
        "instance": 1,
        "interfaces": {
            "test-test-1-victim-2": {
                "name": "test-test-1-victim-2",
                "private_ip": "10.99.1.5",
                "subnetwork_base_name": "internal",
                "subnetwork_cidr": "10.99.1.0/25",
                "subnetwork_name": "test-test-1-internal"
            }
        },
        "is_in_services_network": true,
        "memory": 1024,
        "name": "test-test-1-victim",
        "vcpu": 1
    }
},
"guest": "attacker",
"instance": 1,
"instances": 2,
"institution": "test",
"lab_name": "test",
"networks": {
    "internal": {
        "members": {
            "attacker": "10.99.2.4",
            "victim": "10.99.2.5"
        },
        "network_cidr":"10.99.1.0/25"
    },
    "external": {
        "members": {
            "attacker": "10.99.1.132"
        },
        "network_cidr": "10.99.1.128/25"
    }
},
"parameters": {
    "flags": "y]utxvds=+w96}~q51iA0@fngc_1p*`&"
},
"random_seed": 1234567890,
"scenario_dir": "/Users/gguerrero/Desktop/Fing/CyberRange/practicas/lab-test",
"ansible_dir": "/Users/gguerrero/Desktop/Fing/CyberRange/practicas/lab-test/ansible",
"services": {
    "bastion_host": {
        "base_name": "bastion_host",
        "base_os": "ubuntu22",
        "disk": 10,
        "domain": "tectonic.cyberrange.com",
        "enable": true,
        "interfaces": {
            "test-test-bastion_host-2": {
                "name": "test-test-bastion_host-2",
                "private_ip": "10.99.0.136",
                "subnetwork_name": "test-test-services"
            }
        },
        "ip": "10.99.0.136",
        "memory": 1024,
        "name": "test-test-bastion_host",
        "ports": {
            "caldera": {
                "external_port": "8443",
                "internal_port": 8443
            },
            "elastic": {
                "external_port": "5601",
                "internal_port": 5601
            },
            "guacamole": {
                "external_port": "10443",
                "internal_port": 10443
            }
        },
        "vcpu": 1
    },
    "caldera": {
        "base_name": "caldera",
        "base_os": "rocky9",
        "disk": 30,
        "enable": true,
        "external_port": "8443",
        "interfaces": {
            "test-test-caldera-2": {
                "name": "test-test-caldera-2",
                "private_ip": "10.99.0.134",
                "subnetwork_name": "test-test-services"
            }
        },
        "internal_port": 8443,
        "ip": "10.99.0.134",
        "memory": 2048,
        "name": "test-test-caldera",
        "ot_enabled": false,
        "vcpu": 1,
        "version": "5.3.0"
    },
    "elastic": {
        "base_name": "elastic",
        "base_os": "rocky9",
        "deploy_default_policy": true,
        "disk": 50,
        "enable": true,
        "endpoint_policy_name": "Endpoint",
        "external_port": "5601",
        "interfaces": {
            "test-test-elastic-2": {
                "name": "test-test-elastic-2",
                "private_ip": "10.99.0.133",
                "subnetwork_name": "test-test-services"
            },
            "test-test-elastic-3": {
                "name": "test-test-elastic-3",
                "private_ip": "10.99.0.5",
                "subnetwork_name": "test-test-internet"
            }
        },
        "internal_port": 5601,
        "ip": "10.99.0.133",
        "memory": 8096,
        "monitor_type": "endpoint",
        "name": "test-test-elastic",
        "packetbeat_policy_name": "Packetbeat",
        "user_install_packetbeat": "tectonic",
        "vcpu": 2,
        "version": "9.1.0"
    },
    "guacamole": {
        "base_name": "guacamole",
        "base_os": "ubuntu22",
        "brute_force_protection_enabled": false,
        "disk": 10,
        "enable": true,
        "external_port": "10443",
        "interfaces": {
            "test-test-guacamole-2": {
                "name": "test-test-guacamole-2",
                "private_ip": "10.99.0.135",
                "subnetwork_name": "test-test-services"
            }
        },
        "internal_port": 10443,
        "ip": "10.99.0.135",
        "memory": 2048,
        "name": "test-test-guacamole",
        "vcpu": 1,
        "version": "1.6.0"
    }
},
"ssh_password_login": true,
"student_prefix": "trainee",
"users": {
    "trainee1": {
        "instance": 1,
        "password": "6LOkCoZM5WZt",
        "password_hash": "$6$rounds=656000$q4fCi3BkcRx94tss$MfsztYkflFSs/sXGbvI3XWxwu9cn6mnzJC/BaJBSSN..sTRyNFnMHVIyOlomp9syKO3.vbjRLgg3TeDo3f0r5/"
    },
    "trainee2": {
        "instance": 2,
        "password": "P1Tfwk2COpB9",
        "password_hash": "$6$rounds=656000$5ylj049ZZGbMoy0g$QBOgI48EI0Cp8hhvlYzAWQrLDEcy3CJGaiWmReAaDEVmEn2zAmKHFej.GgZ5T212R/JnZFbiDbaGACzF9HAro1"
    }
}
```
