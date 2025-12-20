# Services

In Tectonic, the concept of services is used. These are special machines that operate across all instances within a scenario. Currently, the available services are:

- Elastic: for monitoring participant training
- Caldera: for adversary emulation
- Guacamole: for remote access to instances (using protocols such as SSH and RDP)
- Moodle: learning management system (LMS) for theoretical content
- Bastion Host: the single entry point to the services listed above

For more details on how the Elastic, Caldera, and Guacamole services
are enabled, see [description](./description.md) file. For more
details on the configuration of these services, see the specific docs
for [Elastic](./elastic.md) and [Caldera](./caldera.md). The Bastion
Host service is implicitly enabled if any of the previously mentioned
services is enabled.

If it is necessary to present an SSL/TLS certificate on the Bastion Host service, the playbook [valid_certificate.yml](../tectonic/services/bastion_host/valid_certificate.yml) can be executed on demand, which will generate a Let's Encrypt certificate. For this, it is necessary to have a domain name that resolves to the public IP associated with the Bastion Host. Use the following command to run the playbook:
```
tectonic -c <ini_file> <description_file> run-ansible -p ./tectonic/services/bastion_host/valid_certificate.yml -g bastion_host
```


