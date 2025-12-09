#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: delete_file_debugfs

short_description: Delete file using debugfs on ext4 filesystem

description:
  - Deletes a file from ext4 filesystem using debugfs
  - Captures inode number before deletion for forensic recovery
  - True forensic deletion - file can be recovered with icat/Autopsy
  - Marks inode as deleted but data blocks remain intact temporarily
  
version_added: "2.0.0"

options:
  filename:
    description: Name of file to delete in filesystem
    required: true
    type: str
  
  device:
    description: Block device path (e.g., /dev/sda3)
    required: true
    type: str
    
  directory:
    description: Directory containing file (relative to mount point)
    required: false
    type: str
    default: '/'

notes:
  - Requires sudo privileges for debugfs
  - File must already exist on the filesystem

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Delete file with debugfs capturing inode
- name: Delete password file forensically
  delete_file_debugfs:
    filename: FORENSIC_passwords.txt
    device: /dev/sda3

# Delete file in subdirectory
- name: Delete document
  delete_file_debugfs:
    filename: FORENSIC_document.txt
    device: /dev/sda3
    directory: /home
'''

RETURN = r'''
changed:
  description: Whether the file was deleted
  type: bool
  returned: always
  sample: true

filename:
  description: Name of deleted file
  type: str
  returned: always
  sample: "FORENSIC_passwords.txt"

deleted:
  description: Whether file was successfully deleted
  type: bool
  returned: always
  sample: true

device:
  description: Block device used
  type: str
  returned: always
  sample: "/dev/sda3"

msg:
  description: Status message
  type: str
  returned: always
  sample: "Successfully deleted FORENSIC_passwords.txt from /dev/sda3 using debugfs"
'''

from ansible.module_utils.basic import AnsibleModule


def main():
    """
    Main execution function for delete_file_debugfs module.
    """
    
    # Define module argument specification
    module = AnsibleModule(
        argument_spec=dict(
            filename=dict(type='str', required=True),
            device=dict(type='str', required=True),
            directory=dict(type='str', default='/')
        ),
        supports_check_mode=True
    )
    
    # Extract parameters
    filename = module.params['filename']
    device = module.params['device']
    directory = module.params['directory']
    
    # Check mode
    if module.check_mode:
        module.exit_json(
            changed=True,
            filename=filename,
            device=device,
            deleted=False
        )
    
    # Import Layer 1 primitives
    try:
        from ansible.module_utils import layer1_primitives as l1
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer1_primitives: {str(e)}")
    
    try:
        # Call debugfs deletion primitive (Layer 1)
        success, error = l1.delete_file_with_debugfs(
            device=device,
            filename=filename,
            directory=directory
        )
        
        if not success:
            module.fail_json(msg=f"Failed to delete with debugfs: {error}")
        
        # Build result
        result = {
            'changed': True,
            'filename': filename,
            'device': device,
            'deleted': True,
            'msg': f"Successfully deleted {filename} from {device} using debugfs"
        }
        
        module.exit_json(**result)
        
    except Exception as e:
        module.fail_json(msg=f"Unexpected error: {str(e)}")


if __name__ == '__main__':
    main()
