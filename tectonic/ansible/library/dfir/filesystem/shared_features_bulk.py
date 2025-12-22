#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: shared_features_bulk

short_description: Apply shared characteristics to files (Layer 2)

description:
  - Orchestrates bulk modification of file characteristics using Layer 1 primitives
  - Modifies file permissions (chmod)
  - Simulates file deletion for forensic scenarios
  - Operates on existing files matching pattern
  
version_added: "2.0.0"

options:
  base_directory:
    description: Directory containing files to modify
    required: true
    type: str
    
  default_permissions:
    description:
      - Default permissions in octal format as string (e.g., "0644", "0444", "0755")
      - Applied to all matched files
    required: false
    type: str
    default: null
    
  default_owners:
    description:
      - List of owners with percentage distribution
      - Each item has 'owner' and 'percentage' keys
      - Example: [{'owner': 'user1', 'percentage': 50}, {'owner': 'user2', 'percentage': 50}]
    required: false
    type: list
    elements: dict
    default: null
    
  deleted_ratio:
    description:
      - Percentage of files to delete (0.0 to 1.0 or 0-100)
      - Simulates ransomware behavior of deleting some originals
    required: false
    type: float
    default: 0.0
    
  deleted_count:
    description:
      - Exact number of files to delete
      - Overrides deleted_ratio if specified
    required: false
    type: int
    default: null
    
  minimum_size:
    description:
      - Minimum file size (e.g., "50KB", "1MB")
      - Files smaller than this will be padded
    required: false
    type: str
    default: null
    
  maximum_size:
    description:
      - Maximum file size (e.g., "100KB", "5MB")
      - Files larger than this will be truncated
    required: false
    type: str
    default: null
    
  average_size:
    description:
      - Target average file size (e.g., "75KB", "2MB")
      - Adjusts files to achieve this average with ±20% variance
    required: false
    type: str
    default: null
    
  name_pattern:
    description: Glob pattern to filter files (e.g., "*.pdf", "*.WNCRY")
    required: false
    type: str
    default: "*"
    
  recursive:
    description: Search files recursively in subdirectories
    required: false
    type: bool
    default: true

notes:
  - Uses Layer 1 primitives from module_utils.layer1_primitives
  - Uses Layer 2 orchestrator apply_shared_characteristics() from module_utils.layer2_orchestrators
  - Deletion is random selection from matched files
  - Useful for simulating ransomware shadow copy deletion behavior

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Set all encrypted files to read-only
- name: Make encrypted files read-only
  shared_features_bulk:
    base_directory: "/tmp/wannacry_simulator"
    name_pattern: "*.WNCRY"
    default_permissions: "0444"
    recursive: true

# Delete 12% of files (simulate shadow copy deletion)
- name: Simulate backup deletion
  shared_features_bulk:
    base_directory: "/tmp/wannacry_simulator"
    name_pattern: "*.WNCRY"
    deleted_ratio: 0.12

# Delete exact count of files
- name: Delete specific number of files
  shared_features_bulk:
    base_directory: "/tmp/documents"
    name_pattern: "*.docx.WNCRY"
    deleted_count: 18

# Apply permissions without deletion
- name: Change all file permissions
  shared_features_bulk:
    base_directory: "/tmp/data"
    name_pattern: "*"
    default_permissions: "0755"
    recursive: false
'''

RETURN = r'''
changed:
  description: Whether any modifications were made
  type: bool
  returned: always
  sample: true

files_found:
  description: Total number of files found matching pattern
  type: int
  returned: always
  sample: 150

permissions_changed:
  description: Number of files with permissions modified
  type: int
  returned: always
  sample: 150

files_deleted:
  description: Number of files deleted
  type: int
  returned: always
  sample: 18

files_failed:
  description: List of files that failed modification
  type: list
  returned: always
  sample: []
'''

from ansible.module_utils.basic import AnsibleModule


def main():
    """
    Main execution function for shared_features_bulk module.
    
    This module acts as an Ansible interface to the Layer 2 orchestrator
    apply_shared_characteristics() from module_utils.layer2_orchestrators.
    
    Workflow:
        1. Parse and validate module arguments
        2. Import Layer 2 orchestrator
        3. Call orchestrator with modification parameters
        4. Return results in Ansible format
    """
    
    # Define module argument specification
    module = AnsibleModule(
        argument_spec=dict(
            base_directory=dict(type='str', required=True),
            default_permissions=dict(type='str', required=False, default=None),
            default_owners=dict(type='list', elements='dict', required=False, default=None),
            deleted_ratio=dict(type='float', required=False, default=0.0),
            deleted_count=dict(type='int', required=False, default=None),
            minimum_size=dict(type='str', required=False, default=None),
            maximum_size=dict(type='str', required=False, default=None),
            average_size=dict(type='str', required=False, default=None),
            name_pattern=dict(type='str', required=False, default='*'),
            recursive=dict(type='bool', required=False, default=True)
        ),
        supports_check_mode=False
    )
    
    # Extract parameters
    base_directory = module.params['base_directory']
    default_permissions = module.params['default_permissions']
    default_owners = module.params['default_owners']
    deleted_ratio = module.params['deleted_ratio']
    deleted_count = module.params['deleted_count']
    minimum_size = module.params['minimum_size']
    maximum_size = module.params['maximum_size']
    average_size = module.params['average_size']
    name_pattern = module.params['name_pattern']
    recursive = module.params['recursive']
    
    # Validate base directory exists
    import os
    if not os.path.exists(base_directory):
        module.fail_json(msg=f"base_directory does not exist: {base_directory}")
    
    if not os.path.isdir(base_directory):
        module.fail_json(msg=f"base_directory is not a directory: {base_directory}")
    
    # Convert deleted_ratio: accept both percentage (25) and ratio (0.25)
    if deleted_ratio > 1.0:
        deleted_ratio = deleted_ratio / 100.0  # Convert 25 → 0.25
    
    # Validate deleted_ratio after conversion
    if deleted_ratio < 0.0 or deleted_ratio > 1.0:
        module.fail_json(msg=f"deleted_ratio must be between 0.0-1.0 or 0-100 (got {module.params['deleted_ratio']})")
    
    # Convert permissions from octal string to int if provided
    permissions_int = None
    if default_permissions:
        try:
            # Support both "0644" and "644" formats
            permissions_int = int(default_permissions, 8)
        except ValueError:
            module.fail_json(msg=f"Invalid permissions format: {default_permissions}. Use octal format like '0644'")
    
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    # Call Layer 2 orchestrator to apply shared characteristics
    try:
        success, stats, failed_files, error = l2.apply_shared_characteristics(
            base_directory=base_directory,
            default_permissions=permissions_int,
            default_owners=default_owners,
            deleted_ratio=deleted_ratio,
            deleted_count=deleted_count,
            minimum_size=minimum_size,
            maximum_size=maximum_size,
            average_size=average_size,
            name_pattern=name_pattern,
            recursive=recursive
        )
        
        if not success:
            module.fail_json(msg=f"Shared characteristics application failed: {error}")
        
        # Return success results
        module.exit_json(
            changed=True,
            files_found=stats.get('files_found', 0),
            files_processed=stats.get('files_processed', 0),
            permissions_changed=stats.get('permissions_changed', 0),
            owners_changed=stats.get('owners_changed', 0),
            sizes_adjusted=stats.get('sizes_adjusted', 0),
            files_deleted=stats.get('files_deleted', 0),
            files_failed=failed_files,
            msg=f"Modified {stats.get('files_found', 0)} files"
        )
        
    except Exception as e:
        module.fail_json(msg=f"Unexpected error during characteristics modification: {str(e)}")


if __name__ == '__main__':
    main()
