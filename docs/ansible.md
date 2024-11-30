## Ansible

In Ansible, by default, facts are always gathered when executing a playbook. In order to optimize Ansible executions in Tectonic, fact collection has been disabled by default. Therefore, if your playbooks need to use facts, make sure to enable them using `gather_facts: yes` at the play level.