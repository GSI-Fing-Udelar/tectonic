## Ansible

### Config

Modifies the Ansible options in the INI file to change Ansible’s global configurations.

### Facts

In Ansible, by default, facts are always gathered when executing a playbook. In order to optimize Ansible executions in Tectonic, fact collection has been disabled by default. Therefore, if your playbooks need to use facts, make sure to enable them using `gather_facts: yes` at the play level.

### Parameters

These parameters are used to individualize the instances, for example by configuring unique flag values. Tectonic selects parameters from the user-provided parameter lists in a pseudo-random manner (based on the value of the random seed) and assigns them to each instance.

The parameters are loaded as dictionaries within the variable:

```
parameters['<parameter_file_name>']
```

For example, if there are two parameter files as follows:
```
filename: flags.ndjson
content:
"super_secret_flag"
... 


filename: users.ndjson
content:
{"name":"admin","password":"admin"}
...
```
These parameters are used in a playbook as follows:

```
parameters["flags"]
parameters["users"]["name"] and parametes["users"]["password"]
```


### Variables

A set of Ansible variables is available that refer to Tectonic configurations and the scenario description. The variables are listed below.

- `config`: Dictionary with configurations associated with parameters of the ini file.
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
- `ìnstance`: Configuration parameters of the instance where the playbook is being executed.
    - `base_name`
    - `base_os`
    - `copy`
    - `disk`
    - `gui`
    - `hostname`
    - `instance_number`
    - `interfaces`: Dictionary of the instance’s interfaces.
        - `<interface_name>`
            - `name`
            - `private_ip`
            - `subnetwork_name`
    - `is_in_services_network`
    - `memory`
    - `name`
    - `vcpu`
- `instances_number`: Number of the instance where the playbook is being executed.
- `instances`: Configuration parameters of all instances. Each entry in the dictionary contains an instance, and the parameters are analogous to those previously indicated for the `instance` variable.
- `institution`: Institution.
- `lab_name`: Laboratory name.
- `networks`:
- `parameters`: Dictionary with defined parameters for the instance.
- `networks`: Scenario networks. Each entry in the scenario contains a network with its configuration parameters.
    - `<network_name>`
        - `ip_network`
        - `name`
- `random_seed`: Seed used for parameters selection.
- `scenario_dir`: Directory with the scenario definition.
- `services`: Services enabled in the scenario. Each entry in the dictionary contains a service with configuration parameters analogous to those listed for the 'instance' variable presented earlier. Additionally, each service has specific configuration parameters. The following lists these parameters for each service.
    - `bastion_host`
        - `<instance_configuracion>`
        - `domain`
    - `caldera`
        - `<instance_configuracion>`
        - `external_port`
        - `internal_port`
        - `ot_enabled`
        - `version`
    - `elastic`
        - `<instance_configuracion>`
        - `deploy_default_policy`
        - `endpoint_policy_name`
        - `external_port`
        - `internal_port`
        - `monitor_type`
        - `packetbeat_policy_name`
        - `user_install_packetbeat`
        - `version`
    - `guacamole`
        - `<instance_configuracion>`
        - `brute_force_protection_enabled`
        - `external_port`
        - `internal_port`
        - `version`
- `ssh_password_login`: Enable password authentication for trainers.
- `student_prefix`: Prefix for naming trainer users.
- `topology`: Network configuration of the instance corresponding to the instance number of the machine where the playbook is being executed.
    - `<network_base_name>`: Dictionary where each entry contains the machine's base_name and its IP address on the network.
        - `<instance_base_name>` : <instance_ip>

- `users`: Trainer users. Each entry in the dictionary is a user with the following configuration parameters.
    - `<user_name>`
        - `instance`
        - `password`
        - `password_hash`

Below is a reference example.

```
"config": {
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
"create_students_password": true,
"instance": {
    "base_name": "attacker",
    "base_os": "ubuntu22",
    "copy": 1,
    "disk": 15,
    "gui": true,
    "hostname": "attacker-2",
    "instance_number": 2,
    "interfaces": {
        "test-test-2-attacker-2": {
            "name": "test-test-2-attacker-2",
            "private_ip": "10.99.2.4",
            "subnetwork_name": "test-test-2-internal"
        },
        "test-test-2-attacker-3": {
            "name": "test-test-2-attacker-3",
            "private_ip": "10.99.2.132",
            "subnetwork_name": "test-test-2-internal2"
        }
    },
    "is_in_services_network": true,
    "memory": 1024,
    "name": "test-test-2-attacker",
    "vcpu": 1
},
"instances_number": 2,
"instances": {
    "test-test-1-attacker": {
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
                "subnetwork_name": "test-test-1-internal"
            },
            "test-test-1-attacker-3": {
                "name": "test-test-1-attacker-3",
                "private_ip": "10.99.1.132",
                "subnetwork_name": "test-test-1-internal2"
            }
        },
        "is_in_services_network": true,
        "memory": 1024,
        "name": "test-test-1-attacker",
        "vcpu": 1
    },
    "test-test-1-victim": {
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
                "subnetwork_name": "test-test-1-internal"
            }
        },
        "is_in_services_network": true,
        "memory": 1024,
        "name": "test-test-1-victim",
        "vcpu": 1
    },
    "test-test-2-attacker": {
        "base_name": "attacker",
        "base_os": "ubuntu22",
        "copy": 1,
        "disk": 15,
        "gui": true,
        "hostname": "attacker-2",
        "instance": 2,
        "interfaces": {
            "test-test-2-attacker-2": {
                "name": "test-test-2-attacker-2",
                "private_ip": "10.99.2.4",
                "subnetwork_name": "test-test-2-internal"
            },
            "test-test-2-attacker-3": {
                "name": "test-test-2-attacker-3",
                "private_ip": "10.99.2.132",
                "subnetwork_name": "test-test-2-internal2"
            }
        },
        "is_in_services_network": true,
        "memory": 1024,
        "name": "test-test-2-attacker",
        "vcpu": 1
    },
    "test-test-2-victim": {
        "base_name": "victim",
        "base_os": "rocky9",
        "copy": 1,
        "disk": 15,
        "gui": true,
        "hostname": "victim-2",
        "instance": 2,
        "interfaces": {
            "test-test-2-victim-2": {
                "name": "test-test-2-victim-2",
                "private_ip": "10.99.2.5",
                "subnetwork_name": "test-test-2-internal"
            }
        },
        "is_in_services_network": true,
        "memory": 1024,
        "name": "test-test-2-victim",
        "vcpu": 1
    }
},
"institution": "test",
"lab_name": "test",
"networks": {
    "test-test-1-internal": {
        "ip_network": "10.99.1.0/25",
        "name": "test-test-1-internal"
    },
    "test-test-1-internal2": {
        "ip_network": "10.99.1.128/25",
        "name": "test-test-1-internal2"
    },
    "test-test-2-internal": {
        "ip_network": "10.99.2.0/25",
        "name": "test-test-2-internal"
    },
    "test-test-2-internal2": {
        "ip_network": "10.99.2.128/25",
        "name": "test-test-2-internal2"
    }
},
"parameters": {
    "flags": "y]utxvds=+w96}~q51iA0@fngc_1p*`&"
},
"random_seed": 1234567890,
"scenario_dir": "/Users/gguerrero/Desktop/Fing/CyberRange/practicas/lab-test",
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
"topology": {
    "internal": {
        "attacker": "10.99.2.4",
        "victim": "10.99.2.5"
    },
    "external": {
        "attacker": "10.99.2.132"
    }
},
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