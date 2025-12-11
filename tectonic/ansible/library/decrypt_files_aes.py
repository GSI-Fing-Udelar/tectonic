#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: decrypt_files_aes

short_description: Bulk AES-256-CBC file decryption (Layer 2)

description:
  - Orchestrates bulk file decryption using Layer 1 AES-256-CBC primitive
  - Decrypts files previously encrypted with encrypt_files_aes
  - Restores original files using the same encryption key
  - Removes encrypted files after successful decryption
  
version_added: "2.0.0"

options:
  files:
    description: List of encrypted file paths to decrypt
    required: true
    type: list
    elements: str
    
  key:
    description:
      - AES-256 decryption key (64 hex characters = 32 bytes)
      - Must be the same key used for encryption
    required: true
    type: str
    
  encrypted_extension:
    description: Extension of encrypted files (e.g., "WNCRY")
    required: false
    type: str
    default: "WNCRY"
    
  keep_encrypted:
    description:
      - Keep encrypted files after decryption (for testing)
      - Normal behavior is to delete encrypted files (keep_encrypted=false)
    required: false
    type: bool
    default: false

requirements:
  - python >= 3.8
  - cryptography

notes:
  - Uses Layer 1 primitive decrypt_file_aes256_cbc() from module_utils.layer1_primitives
  - Uses Layer 2 orchestrator decrypt_files_bulk() from module_utils.layer2_orchestrators
  - Decryption format: Reads [16-byte IV] + [AES-256-CBC encrypted data with PKCS7 padding]
  - Requires the exact same key used for encryption

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Decrypt files with known key
- name: Decrypt victim files
  decrypt_files_aes:
    files:
      - /tmp/wannacry_simulator/file1.docx.WNCRY
      - /tmp/wannacry_simulator/file2.pdf.WNCRY
      - /tmp/wannacry_simulator/file3.jpg.WNCRY
    key: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

# Decrypt and keep encrypted files (for testing)
- name: Decrypt with backup
  decrypt_files_aes:
    files:
      - /tmp/document.docx.WNCRY
    key: "{{ encryption_key }}"
    keep_encrypted: true

# Decrypt all encrypted files in directory (using find)
- name: Find all encrypted files
  find:
    paths: /tmp/wannacry_simulator
    patterns: "*.WNCRY"
  register: files_to_decrypt

- name: Decrypt found files
  decrypt_files_aes:
    files: "{{ files_to_decrypt.files | map(attribute='path') | list }}"
    key: "{{ saved_encryption_key }}"
'''

RETURN = r'''
changed:
  description: Whether any files were decrypted
  type: bool
  returned: always
  sample: true

decrypted_files:
  description: List of successfully decrypted files (original names restored)
  type: list
  returned: always
  sample: ["/tmp/file1.docx", "/tmp/file2.pdf"]

decryption_key:
  description: AES-256 key used (hex format, 64 characters)
  returned: always
  type: str
  sample: "a1b2c3d4e5f6..."

failed_files:
  description: List of files that failed to decrypt
  type: list
  returned: always
  sample: []

total_decrypted:
  description: Number of files successfully decrypted
  type: int
  returned: always
  sample: 10

total_failed:
  description: Number of files that failed decryption
  type: int
  returned: always
  sample: 0
'''

import os
from ansible.module_utils.basic import AnsibleModule


def main():
    """
    Main execution function for decrypt_files_aes module.
    
    This module acts as an Ansible interface to the Layer 2 orchestrator
    decrypt_files_bulk() from module_utils.layer2_orchestrators.
    
    Workflow:
        1. Parse and validate module arguments
        2. Parse decryption key
        3. Import Layer 2 orchestrator
        4. Call orchestrator to decrypt files
        5. Return results in Ansible format
    """
    
    # Define module argument specification
    module = AnsibleModule(
        argument_spec=dict(
            files=dict(type='list', elements='str', required=True),
            key=dict(type='str', required=True, no_log=True),
            encrypted_extension=dict(type='str', required=False, default='WNCRY'),
            keep_encrypted=dict(type='bool', required=False, default=False)
        ),
        supports_check_mode=False
    )
    
    # Extract parameters
    files = module.params['files']
    key_hex = module.params['key']
    encrypted_extension = module.params['encrypted_extension']
    keep_encrypted = module.params['keep_encrypted']
    
    # Validate files list
    if not files or len(files) == 0:
        module.fail_json(msg="files list cannot be empty")
    
    # Validate and parse decryption key
    if len(key_hex) != 64:
        module.fail_json(msg="key must be 64 hex characters (32 bytes for AES-256)")
    
    try:
        key_bytes = bytes.fromhex(key_hex)
    except ValueError:
        module.fail_json(msg="key must contain valid hexadecimal characters")
    
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    # Call Layer 2 orchestrator to decrypt files
    try:
        success, decrypted_files, failed_files, error = l2.decrypt_files_bulk(
            files=files,
            decryption_key=key_bytes,
            encrypted_extension=encrypted_extension,
            keep_encrypted=keep_encrypted
        )
        
        if not success:
            module.fail_json(msg=f"Bulk decryption failed: {error}")
        
        # Return success results
        module.exit_json(
            changed=True,
            decrypted_files=decrypted_files,
            decryption_key=key_hex,
            failed_files=[f[0] for f in failed_files],  # Extract filenames
            total_decrypted=len(decrypted_files),
            total_failed=len(failed_files),
            msg=f"Decrypted {len(decrypted_files)} files successfully"
        )
        
    except Exception as e:
        module.fail_json(msg=f"Unexpected error during decryption: {str(e)}")


if __name__ == '__main__':
    main()
