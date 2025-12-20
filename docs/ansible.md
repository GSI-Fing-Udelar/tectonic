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

### Variables

A set of Ansible variables is available that refer to the Tectonic
configuration and the scenario description. 

#### Base configuration

The variables for the `base_config` playbooks are the following:

- `scenario_dir`: Path to the directory with the scenario definition.
- `ansible_dir`: Path to the directory with the ansible playbooks.
- `config`: Dictionary with configurations associated with [parameters
  of the ini file](./ini_config.md).
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

The variables for the `after_clone` playbooks are mainly the same as
those for `base_config`. The following variables are added or
modified:

- `instances`: Number of total instances.
- `instance`: Guest instance number where the playbook is running.
- `copy`: Guest copy number where the playbook is running.
- `guests`: Configuration of all guests belonging to the instance corresponding to the guest where the playbook is running. It's a dictionary where the key corresponds to the guest's `base_name` and the value is a dictionary. For this last dictionary, the key corresponds to the `copy` and the value is a dictionary made up of the same parameters as in the `base_config` and includes the following additional values:
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
    - `copy`
- `networks`: Configuration of all networks belonging to the instance corresponding to the guest where the playbook is running. It is a dictionary where the key corresponds to the base name of the network and the value is a dictionary with the following variables.
    - `members`: It's a dictionary where the key corresponds to the guest's `base_name` and the value is a dictionary entry. Each dictionary is composed of keys representing the guest's `copy` and values ​​representing the corresponding IP address on the network.
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

You can see an example dump of the available variables
[here](./ansible_vars_dump.md).

### Scenario parametrization
Scenario parametrization is used to individualize the instances, for
example by configuring unique flag values. Tectonic selects parameters
from the user-provided parameters in the `ansible/parameters`
directory, inside `ndjson` files. These `ndjson` files should contain
a value per line in json format. A value is selected for each
parameter in a pseudo-random manner (based on the value of the
`random_seed` option in the [lab edition
file](./description.md#lab-edition-information)) and assigns them to
each instance.

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
