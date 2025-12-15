This is a full reference example of the ansible variables available in
`after_clone` playbooks:

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
    "attacker": 
        "1": {
            "base_name": "attacker",
            "base_os": "ubuntu22",
            "copies": 1,
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
        }
    },
    "victim": {
        "1": {
            "base_name": "victim",
            "base_os": "rocky9",
            "copies": 2,
            "copy": 1,
            "disk": 15,
            "gui": true,
            "hostname": "victim-1-1",
            "instance": 1,
            "interfaces": {
                "test-test-1-victim-1-2": {
                    "name": "test-test-1-victim-1-2",
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
        },
        "2": {
            "base_name": "victim",
            "base_os": "rocky9",
            "copies": 2,
            "copy": 2,
            "disk": 15,
            "gui": true,
            "hostname": "victim-1-2",
            "instance": 1,
            "interfaces": {
                "test-test-1-victim-2-2": {
                    "name": "test-test-1-victim-2-2",
                    "private_ip": "10.99.1.6",
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
    }
},
"guest": "attacker",
"instance": 1,
"instances": 1,
"institution": "test",
"lab_name": "test",
"networks": {
    "internal": {
        "members": {
            "attacker": {
                "1": "10.99.2.4"
            }, 
            "victim": {
                "1": "10.99.2.5",
                "2": "10.99.2.6"
            }
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
