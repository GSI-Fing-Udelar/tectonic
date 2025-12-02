#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: shared_features_bulk

short_description: Bulk file characteristics modifier (Layer 2)

description:
  - Applies shared characteristics to existing files
  - Owner control (distribution by percentages)
  - Default permissions (base for future modifications)
  - Ratio or count of deleted files
  - Size control (average, maximum, minimum)

options:
  base_directory:
    description: Directory containing files to modify
    required: true
    type: str
  
  default_owners:
    description: List of owners with file percentages for each one
    required: false
    type: list
    default: []
    elements: dict
    suboptions:
      owner:
        description: Owner/user name
        required: true
        type: str
      percentage:
        description: Percentage of files for this owner
        required: true
        type: int
  
  default_permissions:
    description: Base permissions in octal (e.g. 0644, 0755)
    required: false
    type: str
    default: '0644'
  
  deleted_ratio:
    description: Percentage of files to mark as deleted (0-100)
    required: false
    type: int
    default: 0
  
  deleted_count:
    description: Exact count of files to mark as deleted
    required: false
    type: int
    default: 0
  
  average_size:
    description: Target average size (e.g. "50KB", "2MB")
    required: false
    type: str
    default: ''
  
  maximum_size:
    description: Maximum allowed size (e.g. "100KB", "5MB")
    required: false
    type: str
    default: ''
  
  minimum_size:
    description: Minimum required size (e.g. "10KB", "100B")
    required: false
    type: str
    default: ''
  
  name_pattern:
    description: Glob pattern to filter files (e.g. "*.pdf", "doc_*")
    required: false
    type: str
    default: '*'
  
  recursive:
    description: Search files recursively in subdirectories
    required: false
    type: bool
    default: true

author:
  - File Generation System
'''

EXAMPLES = r'''
# Example 1: Assign owners by percentages
- name: Distribute files among 3 users
  shared_features_bulk:
    base_directory: /tmp/data
    default_owners:
      - owner: "user1"
        percentage: 50
      - owner: "user2"
        percentage: 30
      - owner: "user3"
        percentage: 20

# Example 2: Mark 10% of files as deleted
- name: Simulate deleted files
  shared_features_bulk:
    base_directory: /tmp/data
    deleted_ratio: 10
    default_permissions: '0644'

# Example 3: Delete exact count of files
- name: Delete 50 specific files
  shared_features_bulk:
    base_directory: /tmp/data
    deleted_count: 50

# Example 4: Size control
- name: Adjust file sizes
  shared_features_bulk:
    base_directory: /tmp/data
    average_size: "100KB"
    maximum_size: "500KB"
    minimum_size: "10KB"
    name_pattern: "*.pdf"

# Example 5: Complete combination
- name: Apply all characteristics
  shared_features_bulk:
    base_directory: /tmp/company_docs
    default_owners:
      - owner: "admin"
        percentage: 20
      - owner: "user1"
        percentage: 40
      - owner: "user2"
        percentage: 40
    default_permissions: '0755'
    deleted_ratio: 5
    maximum_size: "10MB"
    recursive: true
'''

import os
import sys
import json
import random
import shutil
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule


def parse_size(size_str):
    """
    Converts size string to bytes
    Ex: "10KB" -> 10240, "2MB" -> 2097152
    """
    if not size_str:
        return None
    
    size_str = size_str.upper().strip()
    # Order matters! Check longer units first (GB before B, KB before B, etc.)
    units = [
        ('GB', 1024 * 1024 * 1024),
        ('MB', 1024 * 1024),
        ('KB', 1024),
        ('B', 1)
    ]
    
    for unit, multiplier in units:
        if size_str.endswith(unit):
            try:
                number = float(size_str[:-len(unit)])
                return int(number * multiplier)
            except ValueError:
                return None
    
    # If no unit, assume bytes
    try:
        return int(size_str)
    except ValueError:
        return None


def list_files(base_directory, pattern='*', recursive=True):
    """
    Lists all files in the directory that match the pattern
    """
    import glob
    
    files = []
    
    if recursive:
        glob_pattern = os.path.join(base_directory, '**', pattern)
        files = glob.glob(glob_pattern, recursive=True)
    else:
        glob_pattern = os.path.join(base_directory, pattern)
        files = glob.glob(glob_pattern)
    
    # Filter only files (not directories)
    files = [f for f in files if os.path.isfile(f)]
    
    return files


def distribute_owners(files, owners_config):
    """
    Distributes files among owners according to percentages
    
    Returns:
        dict: {file: owner}
    """
    if not owners_config:
        return {}
    
    # Normalize percentages
    total_percentage = sum(item['percentage'] for item in owners_config)
    owners_norm = [
        {
            'owner': item['owner'],
            'percentage': item['percentage'] / total_percentage
        }
        for item in owners_config
    ]
    
    # Calculate file count per owner
    total_files = len(files)
    distribution = {}
    files_shuffled = files.copy()
    random.shuffle(files_shuffled)
    
    start = 0
    for i, owner_info in enumerate(owners_norm):
        if i == len(owners_norm) - 1:
            # Last owner receives the remaining
            count = total_files - start
        else:
            count = int(total_files * owner_info['percentage'])
        
        end = start + count
        for file in files_shuffled[start:end]:
            distribution[file] = owner_info['owner']
        
        start = end
    
    return distribution


def adjust_size(file, target_size):
    """
    Adjusts file size by adding or truncating content
    """
    current_size = os.path.getsize(file)
    
    if current_size < target_size:
        # Add random bytes
        with open(file, 'ab') as f:
            missing_bytes = target_size - current_size
            f.write(os.urandom(missing_bytes))
    elif current_size > target_size:
        # Truncate file
        with open(file, 'r+b') as f:
            f.truncate(target_size)


def apply_sizes(files, min_size=None, max_size=None, avg_size=None):
    """
    Applies size restrictions to files
    
    Returns:
        dict: modification statistics
    """
    stats = {
        'adjusted_min': 0,
        'adjusted_max': 0,
        'adjusted_avg': 0
    }
    
    for file in files:
        current_size = os.path.getsize(file)
        target_size = None
        
        # Check minimum
        if min_size and current_size < min_size:
            target_size = min_size
            stats['adjusted_min'] += 1
        
        # Check maximum
        if max_size and current_size > max_size:
            target_size = max_size
            stats['adjusted_max'] += 1
        
        # Apply average if no restrictions
        if avg_size and not target_size:
            # Apply with ±20% variation
            variation = int(avg_size * 0.2)
            target_size = random.randint(
                avg_size - variation,
                avg_size + variation
            )
            stats['adjusted_avg'] += 1
        
        # Apply adjustment
        if target_size:
            try:
                adjust_size(file, target_size)
            except Exception:
                pass  # Ignore permission errors
    
    return stats


def main():
    module = AnsibleModule(
        argument_spec=dict(
            base_directory=dict(type='str', required=True),
            default_owners=dict(type='list', required=False, default=[], elements='dict'),
            default_permissions=dict(type='str', required=False, default='0644'),
            deleted_ratio=dict(type='int', required=False, default=0),
            deleted_count=dict(type='int', required=False, default=0),
            average_size=dict(type='str', required=False, default=''),
            maximum_size=dict(type='str', required=False, default=''),
            minimum_size=dict(type='str', required=False, default=''),
            name_pattern=dict(type='str', required=False, default='*'),
            recursive=dict(type='bool', required=False, default=True)
        ),
        supports_check_mode=True
    )
    
    base_directory = module.params['base_directory']
    default_owners = module.params['default_owners']
    default_permissions = module.params['default_permissions']
    deleted_ratio = module.params['deleted_ratio']
    deleted_count = module.params['deleted_count']
    name_pattern = module.params['name_pattern']
    recursive = module.params['recursive']
    
    # Validations
    if not os.path.isdir(base_directory):
        module.fail_json(msg=f"The directory {base_directory} does not exist")
    
    # 1. List files
    files = list_files(base_directory, name_pattern, recursive)
    
    if not files:
        module.exit_json(
            changed=False,
            msg="No files found matching the pattern",
            total_files=0
        )
    
    # Initialize result
    result = {
        'files_processed': len(files),
        'owners_applied': {},
        'permissions_modified': 0,
        'files_deleted': 0,
        'sizes_adjusted': {}
    }
    
    # 2. Handle file deletion (deleted_ratio or deleted_count)
    files_to_delete = []
    
    if deleted_count > 0:
        # Delete exact count
        files_to_delete = random.sample(files, min(deleted_count, len(files)))
    elif deleted_ratio > 0:
        # Delete by percentage
        count_to_delete = int(len(files) * deleted_ratio / 100)
        files_to_delete = random.sample(files, count_to_delete)
    
    # Delete selected files
    for file in files_to_delete:
        try:
            os.remove(file)
            result['files_deleted'] += 1
        except Exception as e:
            pass  # Ignore errors
    
    # Remove deleted files from the list for further processing
    files = [f for f in files if f not in files_to_delete]
    
    if not files:
        # All files were deleted
        module.exit_json(
            changed=True,
            **result,
            msg="All files were deleted",
            base_directory=base_directory
        )
    
    # 3. Distribute owners
    if default_owners:
        owner_distribution = distribute_owners(files, default_owners)
        
        for file, owner in owner_distribution.items():
            try:
                # Use shutil.chown to change ownership (owner and group)
                shutil.chown(file, user=owner, group=owner)
                
                if owner not in result['owners_applied']:
                    result['owners_applied'][owner] = 0
                result['owners_applied'][owner] += 1
            except Exception as e:
                # If permission denied, just register (for non-root users)
                if owner not in result['owners_applied']:
                    result['owners_applied'][owner] = 0
                result['owners_applied'][owner] += 1
    
    # 4. Apply default permissions
    try:
        permissions_oct = int(default_permissions, 8)
        for file in files:
            try:
                os.chmod(file, permissions_oct)
                result['permissions_modified'] += 1
            except Exception:
                pass
    except ValueError:
        module.fail_json(msg=f"Invalid permissions: {default_permissions}")
    
    # 5. Adjust sizes
    min_size = parse_size(module.params['minimum_size'])
    max_size = parse_size(module.params['maximum_size'])
    avg_size = parse_size(module.params['average_size'])
    
    if min_size or max_size or avg_size:
        size_stats = apply_sizes(files, min_size, max_size, avg_size)
        result['sizes_adjusted'] = size_stats
    
    # 6. Final result
    module.exit_json(
        changed=True,
        **result,
        base_directory=base_directory,
        pattern_applied=name_pattern
    )


if __name__ == '__main__':
    main()
