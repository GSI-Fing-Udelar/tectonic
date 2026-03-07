# Ansible Collection - tectonic.evidence_generation

## Description
Collection for evidence and artifacts generation in Tectonic cyber range.

Artifact generation is organized into four main layers:

- Cross-cutting layer of synthetic atomic attributes (Layer 0):
Generates pseudo-random, technically coherent values through Jinja2 filters that expose Faker, automatically populating non-essential parameters of the primitives in the upper layers. Instructors can override any auto-generated value for precise control when required.

- Atomic Layer (Layer 1):
Contains the basic functions for creating a single atomic artifact (e.g., a network packet, the creation of an individual file, or an in-memory process).

- Orchestrator Layer (Layer 2):
Orchestrates multiple calls to the atomic layer to generate coherent activity flows (e.g., a complete TCP connection setup, a full DNS resolution, or the creation of multiple files).

- Profile Layer (Layer 3):
Represents the highest level of abstraction, where complex behaviors are defined by combining multiple primitives to simulate complete attack scenarios and/or background activity.

The artifacts that can be generated operate at the file level or the network level.

- File artifacts: Individual files and directories.
- Networkartifacts: Network packets, TCP connections, DNS queries, or other communication flows.

## Modules

This collection includes the following modules:

- **filesystem_generate_file**: Generate a single file by type (Layer 1)
- **filesystem_delete_file_standard**: Delete a file with optional backup (Layer 1)
- **filesystem_delete_file_debugfs**: Delete file using debugfs on ext4 filesystem (Layer 1)
- **filesystem_generate_files_bulk**: Bulk file generation orchestrator (Layer 2)
- **filesystem_apply_temporal_distribution**: Apply temporal distributions to file timestamps (Layer 2)
- **filesystem_shared_features_bulk**: Apply shared characteristics to files (Layer 2)
- **filesystem_decrypt_files_aes**: Bulk AES-256-CBC file decryption (Layer 2)
- **filesystem_encrypt_files_aes**: Bulk AES-256-CBC file encryption (Layer 2)
- **filesystem_execute_ransomware_profile**: Execute complete ransomware simulation using Layer 3 profiles
- **filesystem_generate_fs_user_profile**: Generate realistic user filesystem profiles (Layer 3)
- **network_generate_tcp_connection**: Generates TCP connection primitives (Layer 1)
- **network_generate_dns_conversation**: Generates DNS conversation primitives (Layer 2)
- **network_generate_http_navigation**: Generates complete HTTP web navigation (Layer 2)
- **network_generate_pe_wannacry**: Generate PE files with WannaCry malware signatures
- **network_generate_syn_flood**: Generates SYN Flood attack traffic (Layer 3 Profile)
- **network_generate_network_user_profile**: Generates user behavior profiles (Layer 3)
- **network_generate_wannacry_attack**: Generates WannaCry-style multi-stage attack simulation (Layer 3 Profile)

Example of using a module:

```yaml
- name: Create office worker profile
  generate_fs_user_profile:
    profile_type: corporate
    base_directory: /home/employee1
    apply_temporal: true
    apply_permissions: true
```

## Roles

This collection includes the following roles:

- **install_dependencies**: Install Linux system packages and Python libraries for evidence and artifact generation. 

Each role has its own README with detailed usage instructions and variables.

**Usage:**
```yaml
- hosts: all
  become: yes
  roles:
    - role: tectonic.evidence_generation.install_dependencies
```
