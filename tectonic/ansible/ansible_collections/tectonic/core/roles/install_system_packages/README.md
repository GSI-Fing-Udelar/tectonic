install_system_packages
=========

Install Linux system packages


Role Variables
--------------

- packages_to_install: list of packages to install


Example Playbook
----------------

- hosts: all
  become: yes
  roles:
    - role: tectonic.core.install_system_packages
      vars:
        packages_to_install:
          - python3
          - python3-pip


License
-------

GPL-3.0-only
