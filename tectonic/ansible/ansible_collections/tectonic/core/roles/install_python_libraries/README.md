install_python_libraries
=========

Install python libraries using pip


Role Variables
--------------

- libraries_to_install: list of python libraries to install
- python_executable: python executable path
- pip_executable: pip executable path


Requirements
------------

Python and pip should already be installed


Example Playbook
----------------

- hosts: all
  become: yes
  roles:
    - role: tectonic.core.install_python_libraries
      vars:
        libraries_to_install:
          - request
        python_executable: python3
        pip_executable: pip3


License
-------

GPL-3.0-only
