#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import subprocess

# Auto-install cryptography if not available
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
except ImportError:
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'cryptography'])
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    except Exception:
        pass  # Will be handled by layer1_primitives

DOCUMENTATION = r'''
---
module: execute_ransomware_profile

short_description: Execute complete ransomware simulation using Layer 3 profiles

description:
  - Orchestrates complete ransomware attack simulation using Layer 3 profiles
  - Supports predefined profiles (WannaCry) or custom configurations
  - Executes full attack chain from file generation to encryption and timeline manipulation
  - Uses Layer 3 orchestrator (layer3_ransomwareprofile) which coordinates Layer 2 and Layer 1 primitives
  - Provides idempotency control and reproducible results
  
version_added: "3.0.0"

options:
  profile:
    description:
      - Ransomware profile to execute
      - Predefined profiles available: 'wannacry'
      - Or use 'custom' with profile_config parameter
    required: true
    type: str
    choices: ['wannacry', 'custom']
    
  target_directory:
    description:
      - Target directory where simulation will be executed
      - Must be an absolute path
      - Will be created if it doesn't exist
    required: true
    type: str
    
  profile_config:
    description:
      - Custom profile configuration (only used when profile='custom')
      - Can override any parameter from predefined profiles
      - See PROFILE CONFIGURATION section for available parameters
    required: false
    type: dict
    default: {}
    
  file_count:
    description:
      - Override number of files to generate
      - Overrides profile default if specified
    required: false
    type: int
    default: null
    
  faker_seed:
    description:
      - Random seed for reproducible results
      - Same seed produces identical file names and content
      - Overrides profile default if specified
    required: false
    type: int
    default: null
    
  force_rerun:
    description:
      - Force re-execution even if simulation already ran
      - Deletes all existing files and re-creates from scratch
      - Use with caution in production environments
    required: false
    type: bool
    default: false
    
  encryption_key:
    description:
      - Specific AES-256 encryption key (64 hex characters)
      - If not provided, random key will be generated
      - Useful for testing decryption scenarios
    required: false
    type: str
    default: null
    
  enable_encryption:
    description:
      - Enable or disable actual file encryption
      - When false, only generates files without encryption
      - Useful for testing file generation without encryption overhead
    required: false
    type: bool
    default: true
    
  create_ransom_note:
    description:
      - Create ransom note file
      - Overrides profile default if specified
    required: false
    type: bool
    default: null
    
  deletion_ratio:
    description:
      - Percentage of files to delete (0-100)
      - Simulates deletion of backups/logs
      - Overrides profile default if specified
    required: false
    type: float
    default: null

requirements:
  - python >= 3.8
  - cryptography (for AES encryption)
  - faker (for realistic data generation)

notes:
  - Uses Layer 3 profile orchestrator from module_utils.layer3_ransomwareprofile
  - Uses Layer 2 orchestrators from module_utils.layer2_orchestrators
  - Uses Layer 1 primitives from module_utils.layer1_primitives
  - Creates marker file .ransomware_executed for idempotency
  - Encryption is REAL - files cannot be recovered without the key
  - All timestamps are forensically accurate and reproducible

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Execute WannaCry simulation with default parameters
- name: Simulate WannaCry ransomware
  execute_ransomware_profile:
    profile: wannacry
    target_directory: /tmp/wannacry_simulation

# Execute WannaCry with custom file count
- name: WannaCry with 500 files
  execute_ransomware_profile:
    profile: wannacry
    target_directory: /tmp/wannacry_test
    file_count: 500
    faker_seed: 12345


# Custom ransomware profile based on WannaCry
- name: Custom ransomware simulation
  execute_ransomware_profile:
    profile: custom
    target_directory: /tmp/custom_ransomware
    profile_config:
      base_profile: wannacry
      file_count: 300
      encrypted_extension: CUSTOM
      deletion_ratio: 25
      ransom_note_filename: YOUR_FILES_ARE_ENCRYPTED.txt
      ransom_note_content: |
        Your files have been encrypted!
        Pay 10 BTC to recover them.

# Test file generation without encryption
- name: Generate files only (no encryption)
  execute_ransomware_profile:
    profile: wannacry
    target_directory: /tmp/test_files
    enable_encryption: false

# Reproducible encryption with known key (for testing)
- name: WannaCry with known key for testing
  execute_ransomware_profile:
    profile: wannacry
    target_directory: /tmp/wannacry_reproducible
    encryption_key: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    faker_seed: 42

# Force re-run of existing simulation
- name: Re-run WannaCry simulation
  execute_ransomware_profile:
    profile: wannacry
    target_directory: /tmp/wannacry_simulation
    force_rerun: true
'''

RETURN = r'''
changed:
  description: Whether the simulation was executed
  type: bool
  returned: always
  sample: true

profile_name:
  description: Name of the executed ransomware profile
  type: str
  returned: always
  sample: "WannaCry"

target_directory:
  description: Directory where simulation was executed
  type: str
  returned: always
  sample: "/tmp/wannacry_simulation"

files_generated:
  description: Number of original files generated
  type: int
  returned: when simulation executed
  sample: 150

files_encrypted:
  description: Number of files successfully encrypted
  type: int
  returned: when encryption enabled
  sample: 150

files_deleted:
  description: Number of files deleted (simulating backup deletion)
  type: int
  returned: when simulation executed
  sample: 18

encryption_key:
  description: AES-256 encryption key used (first 32 chars shown)
  type: str
  returned: when encryption enabled
  sample: "a1b2c3d4e5f6..."

execution_time:
  description: Total execution time in seconds
  type: float
  returned: always
  sample: 12.456

idempotent_skip:
  description: Whether execution was skipped due to idempotency
  type: bool
  returned: always
  sample: false

ransom_note_created:
  description: Whether ransom note was created
  type: bool
  returned: always
  sample: true

profile_config:
  description: Final profile configuration used
  type: dict
  returned: always
  sample:
    name: "WannaCry"
    file_count: 150
    encryption_algorithm: "AES-256-CBC"
    encrypted_extension: "WNCRY"
'''

# ============================================================================
# IMPORTS
# ============================================================================

import os
import time
import traceback
import subprocess
from ansible.module_utils.basic import AnsibleModule


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_idempotency(target_directory: str) -> tuple:
    """
    Check if simulation already executed.
    
    Returns:
        Tuple of (already_executed, marker_path)
    """
    marker_path = os.path.join(target_directory, '.ransomware_executed')
    return os.path.exists(marker_path), marker_path


def create_idempotency_marker(marker_path: str, profile_name: str, metadata: dict) -> None:
    """Create idempotency marker file."""
    content = f"""Ransomware simulation executed
Profile: {profile_name}
Execution time: {metadata.get('timestamp', 'N/A')}
Files generated: {metadata.get('files_generated', 0)}
Files encrypted: {metadata.get('files_encrypted', 0)}
Encryption key: {metadata.get('encryption_key', 'N/A')}
"""
    with open(marker_path, 'w') as f:
        f.write(content)


def cleanup_directory(target_directory: str, marker_path: str) -> None:
    """Remove all files except marker file."""
    import subprocess
    
    # Remove all files except marker
    subprocess.run(
        f"find {target_directory} -type f ! -name '.ransomware_executed' -delete",
        shell=True,
        check=False
    )
    
    # Remove empty directories
    subprocess.run(
        f"find {target_directory} -mindepth 1 -type d -empty -delete",
        shell=True,
        check=False
    )


def setup_target_directory(target_dir: str) -> None:
    """
    Setup target directory with proper permissions.
    Creates directory if it doesn't exist and ensures current user has write access.
    Uses sudo if necessary to change ownership.
    """
    import pwd
    import grp
    
    # Create directory if it doesn't exist
    os.makedirs(target_dir, mode=0o755, exist_ok=True)
    
    # Get current user and group
    current_user = pwd.getpwuid(os.getuid()).pw_name
    current_group = grp.getgrgid(os.getgid()).gr_name
    
    # Get directory stats
    dir_stat = os.stat(target_dir)
    dir_uid = dir_stat.st_uid
    dir_gid = dir_stat.st_gid
    
    # Check if current user is owner
    if dir_uid != os.getuid():
        # Need to change ownership - try with sudo
        try:
            subprocess.run(
                f"sudo chown -R {current_user}:{current_group} {target_dir}",
                shell=True,
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            # If sudo fails, check if we can at least write
            if not os.access(target_dir, os.W_OK):
                raise PermissionError(
                    f"Cannot write to {target_dir}. "
                    f"Directory is owned by UID {dir_uid}, but current user is UID {os.getuid()}. "
                    f"Please run with sudo or change directory ownership manually: "
                    f"sudo chown -R {current_user}:{current_group} {target_dir}"
                )
    
    # Ensure directory has write permissions
    if not os.access(target_dir, os.W_OK):
        try:
            os.chmod(target_dir, 0o755)
        except PermissionError:
            subprocess.run(
                f"sudo chmod 755 {target_dir}",
                shell=True,
                check=True
            )


# ============================================================================
# PHASE EXECUTORS
# ============================================================================

def phase1_generate_files(module: AnsibleModule, profile: dict, target_dir: str) -> dict:
    """
    PHASE 1: Generate original files before encryption.
    
    Returns:
        Dict with generated file paths and count
    """
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils.dfir.filesystem.second_layer import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    success, created_files, failed_files, error = l2.generate_files_bulk(
        count=profile['file_count'],
        distribution=profile['file_distribution'],
        base_directory=target_dir,
        structure=profile['directory_structure'],
        name_pattern=profile['file_naming_pattern'],
        tree_depth=profile.get('tree_depth', 3),
        subdirs_per_level=profile.get('subdirs_per_level', 3),
        faker_seed=profile['faker_seed']
    )
    
    if not success:
        module.fail_json(msg=f"File generation failed: {error}")
    
    return {
        'files': created_files,
        'count': len(created_files),
        'failed': failed_files
    }


def phase2_apply_original_timestamps(module: AnsibleModule, profile: dict, files: list) -> dict:
    """
    PHASE 2: Apply realistic timestamps to original files (pre-infection).
    
    Returns:
        Dict with timestamp application results
    """
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils.dfir.filesystem.second_layer import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    timerange = profile['original_files_timerange']
    creation_dist = timerange['creation_distribution']
    
    success, files_modified, failed_files, error = l2.apply_temporal_distribution(
        files=files,
        base_timestamp=int(time.time()),
        distribution_type=creation_dist['type'],
        distribution_params=creation_dist['params'],
        seed=profile['faker_seed']
    )
    
    if not success:
        module.fail_json(msg=f"Timestamp application failed: {error}")
    
    return {
        'files_modified': files_modified,
        'failed': failed_files
    }


def phase3_encrypt_files(module: AnsibleModule, profile: dict, files: list, encryption_key: str = None) -> dict:
    """
    PHASE 3: Encrypt files with AES-256-CBC.
    
    Returns:
        Dict with encryption results and key
    """
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils.dfir.filesystem.second_layer import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    # Generate key if not provided
    if encryption_key is None:
        import secrets
        encryption_key = secrets.token_hex(32)  # 64 hex chars = 32 bytes
    
    # Convert hex key to bytes
    key_bytes = bytes.fromhex(encryption_key)
    
    success, encrypted_files, failed_files, error = l2.encrypt_files_bulk(
        files=files,
        encryption_key=key_bytes,
        encrypted_extension=profile['encrypted_extension'],
        keep_originals=profile['keep_original_files']
    )
    
    if not success:
        module.fail_json(msg=f"Encryption failed: {error}")
    
    return {
        'encrypted_count': len(encrypted_files),
        'encrypted_files': encrypted_files,
        'encryption_key': encryption_key,
        'failed': failed_files
    }


def phase4_create_ransom_note(module: AnsibleModule, profile: dict, target_dir: str) -> dict:
    """
    PHASE 4: Create ransom note file(s).
    
    Returns:
        Dict with ransom note creation status
    """
    # Import Layer 1 primitive
    try:
        from ansible.module_utils.dfir.filesystem.first_layer import layer1_primitives as l1
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer1_primitives: {str(e)}")
    
    note_path = os.path.join(target_dir, profile['ransom_note_filename'])
    
    # create_text_file returns (success, error_msg)
    success, error_msg = l1.create_text_file(
        filepath=note_path,
        content=profile['ransom_note_content']
    )
    
    if not success:
        module.fail_json(msg=f"Failed to create ransom note: {error_msg}")
    
    notes_created = 1
    
    # Create in subdirectories if enabled
    if profile['ransom_note_in_subdirs']:
        import subprocess
        result = subprocess.run(
            f"find {target_dir} -type d -exec cp {note_path} {{}}/ \\;",
            shell=True,
            capture_output=True
        )
        # Count subdirectories
        subdir_result = subprocess.run(
            f"find {target_dir} -mindepth 1 -type d | wc -l",
            shell=True,
            capture_output=True,
            text=True
        )
        notes_created += int(subdir_result.stdout.strip()) if result.returncode == 0 else 0
    
    return {
        'created': notes_created,
        'path': note_path
    }


def phase5_apply_infection_timestamps(module: AnsibleModule, profile: dict, encrypted_files: list) -> dict:
    """
    PHASE 5: Apply infection timestamps to encrypted files.
    
    Returns:
        Dict with timestamp application results
    """
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils.dfir.filesystem.second_layer import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    infection = profile['infection_window']
    
    success, files_modified, failed_files, error = l2.apply_temporal_distribution(
        files=encrypted_files,
        base_timestamp=time.time(),
        distribution_type=infection['distribution']['type'],
        distribution_params=infection['distribution']['params'],
        seed=profile['faker_seed']
    )
    
    if not success:
        module.fail_json(msg=f"Infection timestamp application failed: {error}")
    
    return {
        'files_modified': files_modified,
        'failed': failed_files
    }


def phase6_delete_files(module: AnsibleModule, profile: dict, target_dir: str) -> dict:
    """
    PHASE 6: Simulate deletion of backups and logs.
    
    Returns:
        Dict with deletion results
    """
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils.dfir.filesystem.second_layer import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    
    success, stats, failed_files, error = l2.apply_shared_characteristics(
        base_directory=target_dir,
        deleted_ratio=profile['deletion_ratio'] / 100.0,  # Convert percentage to ratio
        name_pattern=f"*.{profile['encrypted_extension']}"
    )
    
    if not success:
        module.fail_json(msg=f"File deletion failed: {error}")
    
    return {
        'deleted_count': stats.get('files_deleted', 0),
        'failed': failed_files
    }


def phase7_set_permissions(module: AnsibleModule, profile: dict, target_dir: str) -> dict:
    """
    PHASE 7: Set encrypted files to read-only.
    
    Returns:
        Dict with permission change results
    """
    if not profile['set_readonly']:
        return {'modified_count': 0}
    
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils.dfir.filesystem.second_layer import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    # Convert permission string to octal integer
    permissions = int(profile['readonly_permissions'], 8)
    
    success, stats, failed_files, error = l2.apply_shared_characteristics(
        base_directory=target_dir,
        default_permissions=permissions,
        name_pattern=f"*.{profile['encrypted_extension']}"
    )
    
    if not success:
        module.fail_json(msg=f"Permission change failed: {error}")
    
    return {
        'modified_count': stats.get('permissions_changed', 0),
        'failed': failed_files
    }


def phase8_generate_pe_executables(module: AnsibleModule, profile: dict, target_dir: str) -> dict:
    """
    PHASE 8: Generate PE executable files with WannaCry signatures.
    
    Returns:
        Dict with PE generation results
    """
    # Skip if PE generation not enabled in profile
    if not profile.get('generate_pe_executables', False):
        return {
            'pe_generated': 0,
            'pe_files': []
        }
    
    # Import Layer 1 primitive
    try:
        from ansible.module_utils.dfir.filesystem.first_layer import layer1_primitives as l1
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer1_primitives: {str(e)}")
    
    # Determine PE target directory
    pe_subdir = profile.get('pe_target_subdirectory', '')
    if pe_subdir:
        pe_target_path = os.path.join(target_dir, pe_subdir)
        # Create PE target directory
        os.makedirs(pe_target_path, exist_ok=True)
    else:
        # Empty subdirectory = use root directory
        pe_target_path = target_dir
    
    # Get PE configuration
    pe_names = profile.get('pe_executable_names', ['mssecsvc.exe', 'tasksche.exe'])
    pe_patterns = profile.get('pe_patterns', ['main_1', 'main_2', 'main_3'])
    seed = profile.get('faker_seed', 42)
    
    generated_pe_files = []
    
    try:
        for idx, exe_name in enumerate(pe_names):
            filepath = os.path.join(pe_target_path, exe_name)
            
            # Use different seed for each file
            file_seed = seed + idx if seed is not None else None
            
            # Call Layer 1 primitive to generate PE file
            success, error = l1.create_pe_wannacry_file(
                filepath=filepath,
                patterns_to_include=pe_patterns,
                seed=file_seed
            )
            
            if not success:
                module.warn(f"Failed to create PE file {exe_name}: {error}")
                continue
            
            generated_pe_files.append(filepath)
        
        return {
            'pe_generated': len(generated_pe_files),
            'pe_files': generated_pe_files
        }
    
    except Exception as e:
        module.warn(f"Error generating PE executables: {str(e)}")
        return {
            'pe_generated': 0,
            'pe_files': []
        }


# ============================================================================
# MAIN EXECUTION FUNCTION
# ============================================================================

def execute_ransomware_simulation(module: AnsibleModule) -> dict:
    """
    Execute complete ransomware simulation.
    
    Returns:
        Dict with execution results
    """
    start_time = time.time()
    
    # Import Layer 3 profile orchestrator
    try:
        from ansible.module_utils.dfir.filesystem.third_layer import layer3_ransomwareprofile as l3
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer3_ransomwareprofile: {str(e)}")
    
    # Get parameters
    profile_name = module.params['profile']
    target_dir = module.params['target_directory']
    force_rerun = module.params['force_rerun']
    enable_encryption = module.params['enable_encryption']
    encryption_key = module.params['encryption_key']
    
    # Check idempotency
    already_executed, marker_path = check_idempotency(target_dir)
    
    if already_executed and not force_rerun:
        return {
            'changed': False,
            'idempotent_skip': True,
            'message': 'Simulation already executed. Use force_rerun=true to re-execute.',
            'target_directory': target_dir
        }
    
    # Get profile configuration
    if profile_name == 'custom':
        profile_config = module.params['profile_config']
        base_profile = profile_config.get('base_profile', 'wannacry')
        profile = l3.create_custom_ransomware_profile(
            name='Custom',
            base_profile=base_profile,
            **profile_config
        )
    else:
        profile = l3.get_ransomware_profile(profile_name)
    
    # Apply parameter overrides
    if module.params['file_count']:
        profile['file_count'] = module.params['file_count']
    if module.params['faker_seed']:
        profile['faker_seed'] = module.params['faker_seed']
    if module.params['create_ransom_note'] is not None:
        profile['create_ransom_note'] = module.params['create_ransom_note']
    if module.params['deletion_ratio'] is not None:
        profile['deletion_ratio'] = module.params['deletion_ratio']
    
    # Validate profile
    valid, errors = l3.validate_ransomware_profile(profile)
    if not valid:
        module.fail_json(msg=f"Invalid profile configuration: {'; '.join(errors)}")
    
    # Setup target directory with proper permissions
    setup_target_directory(target_dir)
    
    # Cleanup if force_rerun
    if force_rerun and already_executed:
        cleanup_directory(target_dir, marker_path)
    
    # Execute simulation phases
    results = {}
    
    try:
        # PHASE 1: Generate files
        phase1_result = phase1_generate_files(module, profile, target_dir)
        results['files_generated'] = phase1_result['count']
        results['generated_files'] = phase1_result['files']
        
        # PHASE 2: Apply original timestamps
        phase2_result = phase2_apply_original_timestamps(
            module, profile, phase1_result['files']
        )
        
        # PHASE 3: Encrypt files (if enabled)
        if enable_encryption:
            # Get list of files to encrypt (excluding .exe files)
            import glob
            files_to_encrypt = []
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    if not file.startswith('.') and not file.endswith('.exe'):
                        files_to_encrypt.append(os.path.join(root, file))
            
            phase3_result = phase3_encrypt_files(
                module, profile, files_to_encrypt, encryption_key
            )
            results['files_encrypted'] = phase3_result['encrypted_count']
            results['encryption_key'] = phase3_result['encryption_key'][:32] + '...'
            
            # Get encrypted file paths
            encrypted_files = []
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    if file.endswith(f".{profile['encrypted_extension']}"):
                        encrypted_files.append(os.path.join(root, file))
            
            # PHASE 5: Apply infection timestamps
            phase5_result = phase5_apply_infection_timestamps(
                module, profile, encrypted_files
            )
        else:
            results['files_encrypted'] = 0
            results['encryption_key'] = 'N/A (encryption disabled)'
        
        # PHASE 4: Create ransom note
        if profile['create_ransom_note']:
            phase4_result = phase4_create_ransom_note(module, profile, target_dir)
            results['ransom_note_created'] = True
            results['ransom_notes_count'] = phase4_result['created']
        else:
            results['ransom_note_created'] = False
            results['ransom_notes_count'] = 0
        
        # PHASE 6: Delete files
        if enable_encryption and profile['deletion_ratio'] > 0:
            phase6_result = phase6_delete_files(module, profile, target_dir)
            results['files_deleted'] = phase6_result['deleted_count']
        else:
            results['files_deleted'] = 0
        
        # PHASE 7: Set permissions
        if enable_encryption and profile['set_readonly']:
            phase7_result = phase7_set_permissions(module, profile, target_dir)
            results['files_set_readonly'] = phase7_result['modified_count']
        else:
            results['files_set_readonly'] = 0

        # PHASE 8: Generate PE executables
        phase8_result = phase8_generate_pe_executables(module, profile, target_dir)
        results['pe_executables_generated'] = phase8_result['pe_generated']
        results['pe_executables_paths'] = phase8_result['pe_files']
        
        # Create idempotency marker
        metadata = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'files_generated': results['files_generated'],
            'files_encrypted': results['files_encrypted'],
            'encryption_key': results.get('encryption_key', 'N/A')
        }
        create_idempotency_marker(marker_path, profile['name'], metadata)
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            'changed': True,
            'idempotent_skip': False,
            'profile_name': profile['name'],
            'target_directory': target_dir,
            'execution_time': round(execution_time, 3),
            'profile_config': {
                'name': profile['name'],
                'file_count': profile['file_count'],
                'encryption_algorithm': profile['encryption_algorithm'],
                'encrypted_extension': profile['encrypted_extension'],
                'deletion_ratio': profile['deletion_ratio']
            },
            **results
        }
        
    except Exception as e:
        module.fail_json(
            msg=f"Ransomware simulation failed: {str(e)}",
            exception=traceback.format_exc()
        )


# ============================================================================
# ANSIBLE MODULE MAIN
# ============================================================================

def main():
    """Main Ansible module entry point."""
    
    module = AnsibleModule(
        argument_spec=dict(
            profile=dict(
                type='str',
                required=True,
                choices=['wannacry', 'locky', 'ryuk', 'custom']
            ),
            target_directory=dict(type='str', required=True),
            profile_config=dict(type='dict', default={}),
            file_count=dict(type='int', default=None),
            faker_seed=dict(type='int', default=None),
            force_rerun=dict(type='bool', default=False),
            encryption_key=dict(type='str', default=None, no_log=True),
            enable_encryption=dict(type='bool', default=True),
            create_ransom_note=dict(type='bool', default=None),
            deletion_ratio=dict(type='float', default=None)
        ),
        supports_check_mode=False
    )
    
    # Execute simulation
    result = execute_ransomware_simulation(module)
    
    module.exit_json(**result)


if __name__ == '__main__':
    main()
