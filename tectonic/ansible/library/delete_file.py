#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: delete_file

short_description: Delete a file with optional backup (Layer 1)

description:
  - Deletes a single file using Layer 1 primitive
  - Optionally creates backup before deletion
  - Equivalent to state=absent in Ansible file module
  - Atomic operation for single file deletion
  
version_added: "2.0.0"

options:
  path:
    description: Full path to the file to delete
    required: true
    type: str
    
  backup:
    description: Create backup before deleting (.backup extension)
    required: false
    type: bool
    default: false
    
  forensic_recoverable:
    description: |
      Enable forensic recoverability (soft delete - moves to hidden .deleted_files directory).
      When true, file is moved to .deleted_files/ subdirectory and is 100% recoverable.
      When false, file is permanently deleted (production behavior).
      
      IMPORTANT: Modern ext4/xfs filesystems clean deleted inodes immediately, making
      traditional forensic recovery (debugfs, extundelete) impossible. The only reliable
      "recoverable deletion" is to not actually delete - just hide the file.
    required: false
    type: bool
    default: true

notes:
  - Uses Layer 1 primitive delete_file() from module_utils.layer1_primitives
  - For bulk deletion, use shared_features_bulk module
  - Fails if file does not exist

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Delete a single file (forensic recoverable by default)
- name: Delete temporary file
  delete_file:
    path: /tmp/file_to_delete.txt

# Delete with backup
- name: Delete important file with backup
  delete_file:
    path: /tmp/important_data.xlsx
    backup: true

# Production delete (unrecoverable)
- name: Remove encrypted file permanently
  delete_file:
    path: /tmp/document.docx.WNCRY
    forensic_recoverable: false

# Forensic-recoverable deletion (for testing recovery tools)
- name: Delete file but keep recoverable
  delete_file:
    path: /tmp/test_recovery.txt
    forensic_recoverable: true
'''

RETURN = r'''
changed:
  description: Whether the file was deleted
  type: bool
  returned: always
  sample: true

path:
  description: Path of the deleted file
  type: str
  returned: always
  sample: "/tmp/file_to_delete.txt"

deleted:
  description: Whether the file was successfully deleted
  type: bool
  returned: always
  sample: true

backup_file:
  description: Path to backup file if created
  type: str
  returned: when backup is true
  sample: "/tmp/important_data.xlsx.backup"
'''

from ansible.module_utils.basic import AnsibleModule


def main():
    """
    Main execution function for delete_file module.
    
    This module acts as an Ansible interface to the Layer 1 primitive
    delete_file() from module_utils.layer1_primitives.
    
    Workflow:
        1. Parse and validate module arguments
        2. Import Layer 1 primitive
        3. Call primitive to delete file
        4. Return results in Ansible format
    """
    
    # Define module argument specification
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='str', required=True),
            backup=dict(type='bool', default=False),
            forensic_recoverable=dict(type='bool', default=True)
        ),
        supports_check_mode=True
    )
    
    # Extract parameters
    path = module.params['path']
    backup = module.params['backup']
    forensic_recoverable = module.params['forensic_recoverable']
    
    # Check mode - don't actually delete
    if module.check_mode:
        import os
        if os.path.exists(path):
            module.exit_json(changed=True, path=path, deleted=False)
        else:
            module.exit_json(changed=False, path=path, deleted=False)
    
    # Import Layer 1 primitive
    try:
        from ansible.module_utils import layer1_primitives as l1
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer1_primitives: {str(e)}")
    
    # Call Layer 1 primitive to delete file
    try:
        success, error, backup_path = l1.delete_file(path, backup=backup, forensic_recoverable=forensic_recoverable)
        
        if not success:
            if "does not exist" in error:
                # File doesn't exist - no change needed
                module.exit_json(changed=False, path=path, deleted=False, msg=error)
            else:
                module.fail_json(msg=f"Failed to delete {path}: {error}")
        
        # Build result dictionary
        result = {
            'changed': True,
            'path': path,
            'deleted': True
        }
        
        if backup_path:
            result['backup_file'] = backup_path
        
        module.exit_json(**result)
        
    except Exception as e:
        module.fail_json(msg=f"Unexpected error during file deletion: {str(e)}")


if __name__ == '__main__':
    main()
