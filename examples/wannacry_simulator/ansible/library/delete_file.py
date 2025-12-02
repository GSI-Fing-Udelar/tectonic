#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: delete_file

short_description: Deletes a file (Layer 1 primitive - state:absent)

description:
  - Primitive module to delete files (equivalent to state:absent in Ansible file module)
  - Part of Layer 1 primitives for file operations
  - Can be used by Layer 2 orchestrators to mark files for deletion

options:
  path:
    description: Full path to the file to delete
    required: true
    type: str
  
  backup:
    description: Make a backup before deleting
    required: false
    type: bool
    default: false

author:
  - Demo Author
'''

EXAMPLES = r'''
# Delete a single file
- name: Delete file
  delete_file:
    path: /tmp/file_to_delete.txt

# Delete with backup
- name: Delete file with backup
  delete_file:
    path: /tmp/important_file.txt
    backup: true
'''

RETURN = r'''
path:
  description: Path of the deleted file
  type: str
  returned: always
deleted:
  description: Whether the file was deleted
  type: bool
  returned: always
backup_file:
  description: Path to backup file if created
  type: str
  returned: when backup is true
'''

import os
import shutil
from ansible.module_utils.basic import AnsibleModule


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='str', required=True),
            backup=dict(type='bool', default=False)
        ),
        supports_check_mode=True
    )
    
    path = module.params['path']
    backup = module.params['backup']
    
    result = {
        'changed': False,
        'path': path,
        'deleted': False
    }
    
    # Check if file exists
    if not os.path.exists(path):
        module.exit_json(**result)
    
    if not os.path.isfile(path):
        module.fail_json(msg=f"{path} is not a file")
    
    # Check mode - don't actually delete
    if module.check_mode:
        result['changed'] = True
        module.exit_json(**result)
    
    # Create backup if requested
    if backup:
        backup_path = path + '.backup'
        try:
            shutil.copy2(path, backup_path)
            result['backup_file'] = backup_path
        except Exception as e:
            module.fail_json(msg=f"Failed to create backup: {str(e)}")
    
    # Delete the file
    try:
        os.remove(path)
        result['changed'] = True
        result['deleted'] = True
    except Exception as e:
        module.fail_json(msg=f"Failed to delete {path}: {str(e)}")
    
    module.exit_json(**result)


if __name__ == '__main__':
    main()
