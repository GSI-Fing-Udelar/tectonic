#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_files_bulk

short_description: Bulk file generation orchestrator (Layer 2)

description:
  - Orchestrates bulk file generation using Layer 1 primitives
  - Supports multiple file types with percentage distribution
  - Creates flat or tree directory structures
  - Generates realistic filenames using Faker variables
  - Atomic operations ensure forensic accuracy
  
version_added: "2.0.0"

options:
  count:
    description: Total number of files to generate
    required: true
    type: int
    
  distribution:
    description: 
      - File type distribution with percentages
      - Percentages will be normalized if they don't sum to 100
    required: false
    type: dict
    default: {"pdf": 30, "docx": 40, "txt": 30}
    
  structure:
    description: Directory structure type
    required: false
    type: str
    choices: [flat, tree]
    default: flat
    
  base_directory:
    description: Root directory where files will be generated
    required: true
    type: str
    
  name_pattern:
    description: 
      - Filename template with variable substitution
      - "Supported variables: {n}, {date}, {time}, {file_type}"
      - "Faker variables: {faker_name}, {faker_company}, {faker_city}, {faker_word}, {faker_job}"
      - "Each file gets UNIQUE faker values using seed + file_index for reproducibility"
    required: false
    type: str
    default: "document_{n}"
    
  tree_depth:
    description: Maximum depth of directory tree (only used with structure=tree)
    required: false
    type: int
    default: 3
    
  subdirs_per_level:
    description: Number of subdirectories per level in tree structure
    required: false
    type: int
    default: 3
    
  faker_seed:
    description: 
      - Random seed for reproducible Faker generation
      - Same seed will produce identical filenames and content
    required: false
    type: int
    default: 1

notes:
  - Uses Layer 1 primitives from module_utils.layer1_primitives
  - Uses Layer 2 orchestrators from module_utils.layer2_orchestrators
  - Supported file types: txt, pdf, jpg, png, docx, xlsx, zip, tar.gz, sh, py
  - Each file type uses appropriate Layer 1 primitive for generation

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Generate 100 files with default distribution (flat structure)
- name: Generate 100 files
  generate_files_bulk:
    count: 100
    base_directory: "/tmp/documents"
    distribution:
      pdf: 30
      docx: 40
      txt: 20
      jpg: 10

# Generate files in tree structure with Faker names
- name: Generate files with realistic names
  generate_files_bulk:
    count: 50
    base_directory: "/tmp/company_files"
    structure: tree
    tree_depth: 3
    subdirs_per_level: 2
    name_pattern: "{faker_company}_{faker_name}_{n}"
    distribution:
      docx: 50
      xlsx: 30
      pdf: 20
    faker_seed: 42

# Generate files for ransomware simulation
- name: Generate victim files
  generate_files_bulk:
    count: 150
    base_directory: "/tmp/wannacry_simulator"
    name_pattern: "document_{date}_{n}"
    distribution:
      docx: 30
      pdf: 25
      jpg: 20
      xlsx: 15
      txt: 10
'''

RETURN = r'''
changed:
  description: Whether any files were created
  type: bool
  returned: always
  sample: true

files_created:
  description: List of successfully created files
  type: list
  returned: always
  sample: ["/tmp/documents/document_0.pdf", "/tmp/documents/document_1.docx"]

files_failed:
  description: List of files that failed to create
  type: list
  returned: always
  sample: []

total_created:
  description: Total number of files successfully created
  type: int
  returned: always
  sample: 100

total_failed:
  description: Total number of files that failed
  type: int
  returned: always
  sample: 0

distribution_used:
  description: Actual file count distribution by type
  type: dict
  returned: always
  sample: {"pdf": 30, "docx": 40, "txt": 20, "jpg": 10}
'''

import os
from ansible.module_utils.basic import AnsibleModule


def main():
    """
    Main execution function for generate_files_bulk module.
    
    This module acts as an Ansible interface to the Layer 2 orchestrator
    generate_files_bulk() from module_utils.layer2_orchestrators.
    
    Workflow:
        1. Parse and validate module arguments
        2. Import Layer 2 orchestrator
        3. Call orchestrator with parameters
        4. Return results in Ansible format
    """
    
    # Define module argument specification
    module = AnsibleModule(
        argument_spec=dict(
            count=dict(type='int', required=True),
            distribution=dict(
                type='dict',
                required=False,
                default={'pdf': 30, 'docx': 40, 'txt': 30}
            ),
            structure=dict(
                type='str',
                required=False,
                default='flat',
                choices=['flat', 'tree']
            ),
            base_directory=dict(type='str', required=True),
            name_pattern=dict(type='str', required=False, default='document_{n}'),
            tree_depth=dict(type='int', required=False, default=3),
            subdirs_per_level=dict(type='int', required=False, default=3),
            faker_seed=dict(type='int', required=False, default=1)
        ),
        supports_check_mode=False
    )
    
    # Extract parameters
    count = module.params['count']
    distribution = module.params['distribution']
    structure = module.params['structure']
    base_directory = module.params['base_directory']
    name_pattern = module.params['name_pattern']
    tree_depth = module.params['tree_depth']
    subdirs_per_level = module.params['subdirs_per_level']
    faker_seed = module.params['faker_seed']
    
    # Validate count
    if count <= 0:
        module.fail_json(msg="count must be positive")
    
    # Validate distribution
    if not distribution or len(distribution) == 0:
        module.fail_json(msg="distribution must contain at least one file type")
    
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils.dfir.filesystem.second_layer import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    # Call Layer 2 orchestrator to generate files
    try:
        success, created_files, failed_files, error = l2.generate_files_bulk(
            count=count,
            distribution=distribution,
            base_directory=base_directory,
            structure=structure,
            name_pattern=name_pattern,
            tree_depth=tree_depth,
            subdirs_per_level=subdirs_per_level,
            faker_seed=faker_seed
        )
        
        if not success:
            module.fail_json(msg=f"Bulk file generation failed: {error}")
        
        # Calculate distribution used
        distribution_used = {}
        for filepath in created_files:
            ext = filepath.split('.')[-1] if '.' in filepath else 'unknown'
            distribution_used[ext] = distribution_used.get(ext, 0) + 1
        
        # Return success results
        module.exit_json(
            changed=True,
            files_created=created_files,
            files_failed=[f[0] for f in failed_files],  # Extract just filenames
            total_created=len(created_files),
            total_failed=len(failed_files),
            distribution_used=distribution_used,
            generated_count=len(created_files),  # Alias for compatibility
            base_directory=base_directory,
            applied_distribution=distribution_used,  # Alias for compatibility
            files=[{"nombre": os.path.basename(f)} for f in created_files],  # For compatibility
            msg=f"Created {len(created_files)} files successfully"
        )
        
    except Exception as e:
        module.fail_json(msg=f"Unexpected error during file generation: {str(e)}")


if __name__ == '__main__':
    main()
