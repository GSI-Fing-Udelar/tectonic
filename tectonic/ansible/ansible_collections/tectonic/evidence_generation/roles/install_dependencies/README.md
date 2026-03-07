install_dependecies
=========

Install dependencies required for evidence generation.

System packages (build dependencies):
  - python3-dev / python3-devel: Python development headers
  - build-essential / gcc: C compiler for Python packages with C extensions
  - libssl-dev / openssl-devel: SSL library for cryptography
  - libffi-dev / libffi-devel: Foreign function interface for cryptography
  - pkg-config: Package configuration tool

System tools:
  - wireshark-common: Provides mergecap tool for PCAP merging
  - pandoc: Document converter for PDF generation

Python libraries:
  - faker: Realistic fake data generation
  - Pillow: Image generation (JPG, PNG)
  - python-docx: DOCX document generation
  - openpyxl: XLSX spreadsheet generation
  - cryptography: AES encryption for ransomware simulation
  - scapy: Network packet generation (PCAP files)


Role Variables
--------------

- debian_packages: list of packages to install on Debian-like operating system machines
- redhat_packages: list of packages to install on RedHat-like operating system machines
- python_libraries: list of python libraries to install
- python_executable_path: python executable path
- pip_executable_path: pip executable path


Requirements
------------

Depends on roles: 
  - tectonic.core.install_system_packages
  - tectonic.core.install_python_libraries


Example Playbook
----------------

- hosts: victim
  become: yes
  roles:
    - tectonic.evidence_generation.install_dependencies


License
-------

GPL-3.0-only
