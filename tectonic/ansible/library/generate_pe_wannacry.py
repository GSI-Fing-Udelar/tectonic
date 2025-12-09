#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Ansible Module: generate_pe_wannacry
Generate simulated PE (Portable Executable) files with WannaCry signatures
detectable by ReversingLabs YARA rules.

This module is a thin wrapper around Layer 1 primitive create_pe_wannacry_file.
"""

from ansible.module_utils.basic import AnsibleModule
import os

DOCUMENTATION = '''
---
module: generate_pe_wannacry
short_description: Generate PE files with WannaCry malware signatures
description:
    - Creates Windows PE executable files with embedded WannaCry patterns
    - Patterns match those searched by ReversingLabs YARA rules
    - Files are detectable by professional malware analysis tools
    - Uses Layer 1 primitive from module_utils.layer1_primitives
options:
    target_directory:
        description:
            - Directory where PE files will be created
        required: true
        type: str
    executable_names:
        description:
            - List of executable filenames to generate
        required: true
        type: list
    include_patterns:
        description:
            - List of YARA pattern names to include
        required: false
        type: list
        default: ['main_1', 'main_2', 'main_3']
    seed:
        description:
            - Random seed for reproducibility
        required: false
        type: int
        default: 42
author:
    - WannaCry Simulator Team
'''

EXAMPLES = '''
- name: Generate WannaCry PE executables
  generate_pe_wannacry:
    target_directory: "/tmp/wannacry_exe"
    executable_names:
      - "mssecsvc.exe"
      - "tasksche.exe"
      - "wcry.exe"
    include_patterns:
      - main_1
      - main_2
      - start_service_3
    seed: 42
'''


def main():
    module = AnsibleModule(
        argument_spec=dict(
            target_directory=dict(type='str', required=True),
            executable_names=dict(type='list', required=True),
            include_patterns=dict(type='list', default=['main_1', 'main_2', 'main_3']),
            seed=dict(type='int', default=42)
        ),
        supports_check_mode=False
    )
    
    target_dir = module.params['target_directory']
    executable_names = module.params['executable_names']
    include_patterns = module.params['include_patterns']
    seed = module.params['seed']
    
    # Import Layer 1 primitive
    try:
        from ansible.module_utils import layer1_primitives as l1
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer1_primitives: {str(e)}")
    
    # Ensure target directory exists
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, mode=0o755)
    
    generated_files = []
    total_size = 0
    
    try:
        for idx, exe_name in enumerate(executable_names):
            filepath = os.path.join(target_dir, exe_name)
            
            # Use different seed for each file
            file_seed = seed + idx if seed is not None else None
            
            # Call Layer 1 primitive to generate PE file
            success, error = l1.create_pe_wannacry_file(
                filepath=filepath,
                patterns_to_include=include_patterns,
                seed=file_seed
            )
            
            if not success:
                module.fail_json(msg=f"Failed to create {exe_name}: {error}")
            
            # Get file size
            file_size = os.path.getsize(filepath)
            
            generated_files.append({
                'name': exe_name,
                'path': filepath,
                'size': file_size,
                'patterns': include_patterns
            })
            total_size += file_size
        
        module.exit_json(
            changed=True,
            generated_files=generated_files,
            total_files=len(generated_files),
            total_size=total_size,
            target_directory=target_dir,
            msg=f"Generated {len(generated_files)} PE files with WannaCry signatures"
        )
        
    except Exception as e:
        module.fail_json(msg=f"Failed to generate PE files: {str(e)}")


if __name__ == '__main__':
    main()
