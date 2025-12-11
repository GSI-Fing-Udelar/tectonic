#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_fs_user_profile

short_description: Generate realistic user filesystem profiles (Layer 3)

description:
  - Generates complete user filesystem profiles with realistic file distributions
  - Orchestrates Layer 2 bulk operations and Layer 1 primitives
  - Supports predefined profiles (personal, corporate, developer, designer, student, server)
  - Automatically creates directory structures, files, and applies temporal distributions
  - Can generate single or multiple user profiles simultaneously

version_added: "3.0.0"

options:
  profile_type:
    description:
      - Type of user profile to generate
      - Each profile has specific file types, directories, and behavior patterns
    required: true
    type: str
    choices: ['personal', 'corporate', 'developer', 'designer', 'student', 'server']
    
  base_directory:
    description:
      - Root directory where profile will be created
      - Profile directories will be created under this path
    required: true
    type: str
    
  file_count:
    description:
      - Number of files to generate
      - If not specified, uses profile default range
    required: false
    type: int
    default: null
    
  faker_seed:
    description:
      - Seed for reproducible generation
      - Same seed produces identical file structures
    required: false
    type: int
    default: 42
    
  verbose:
    description:
      - Print detailed progress information during generation
    required: false
    type: bool
    default: true
    
  multi_user:
    description:
      - Generate multiple user profiles in parallel
      - Requires user_configs parameter
    required: false
    type: bool
    default: false
    
  user_configs:
    description:
      - List of user configurations for multi-user generation
      - Each dict should have 'type', 'user', and optional 'file_count'
      - Example: [{'type': 'personal', 'user': 'john'}, ...]
    required: false
    type: list
    elements: dict
    default: []

notes:
  - Uses Layer 3 orchestrator from module_utils.layer3_commonprofile
  - Profiles include realistic file type distributions and activity patterns
  - Temporal distributions simulate realistic user behavior
  - "Profile: personal - Home user (photos, music, videos, documents)"
  - "Profile: corporate - Office worker (reports, spreadsheets, presentations)"
  - "Profile: developer - Programmer (code, scripts, configs)"
  - "Profile: designer - Graphic designer (images, designs, exports)"
  - "Profile: student - University student (notes, assignments, PDFs)"
  - "Profile: server - File server (backups, logs, archives)"

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Generate a personal user profile
- name: Create personal user filesystem
  generate_fs_user_profile:
    profile_type: personal
    base_directory: /tmp/users/john
    file_count: 300
    faker_seed: 42
    verbose: true

# Generate a corporate user profile
- name: Create office worker profile
  generate_fs_user_profile:
    profile_type: corporate
    base_directory: /tmp/users/employee1
    apply_temporal: true
    apply_permissions: true

# Generate a developer profile with many files
- name: Create developer environment
  generate_fs_user_profile:
    profile_type: developer
    base_directory: /tmp/users/dev_team
    file_count: 500
    faker_seed: 100

# Generate multiple users in an office environment
- name: Create multi-user office
  generate_fs_user_profile:
    profile_type: corporate
    base_directory: /tmp/office
    multi_user: true
    user_configs:
      - type: corporate
        user: manager
        file_count: 200
      - type: developer
        user: dev1
        file_count: 400
      - type: designer
        user: marketing
        file_count: 150

# Generate student profile with default settings
- name: Create student filesystem
  generate_fs_user_profile:
    profile_type: student
    base_directory: /tmp/students/alice
'''

RETURN = r'''
changed:
  description: Whether the module made changes
  type: bool
  returned: always
  sample: true

profile_type:
  description: Type of profile generated
  type: str
  returned: always
  sample: "personal"

profile_name:
  description: Human-readable profile name
  type: str
  returned: always
  sample: "Personal"

base_directory:
  description: Root directory where profile was created
  type: str
  returned: always
  sample: "/tmp/users/john"

total_files:
  description: Total number of files created
  type: int
  returned: always
  sample: 342

failed_files:
  description: Number of files that failed to create
  type: int
  returned: always
  sample: 0

directories_created:
  description: Number of directories created
  type: int
  returned: always
  sample: 4

file_types:
  description: List of file extensions used
  type: list
  returned: always
  sample: ["jpg", "png", "mp4", "mp3", "pdf"]

activity_level:
  description: Simulated user activity level
  type: str
  returned: always
  sample: "sporadic"

multi_user_stats:
  description: Statistics for each user (only in multi-user mode)
  type: list
  returned: when multi_user=true
  sample: [{"user_name": "manager", "total_files": 200}, ...]
'''

from ansible.module_utils.basic import AnsibleModule


def main():
    """
    Main execution function for generate_fs_user_profile module.
    
    This module acts as an Ansible interface to the Layer 3 orchestrator
    Layer3UserProfile from module_utils.layer3_commonprofile.
    
    Workflow:
        1. Parse and validate module arguments
        2. Import Layer 3 orchestrator
        3. Generate single or multiple user profiles
        4. Return results in Ansible format
    """
    
    # Define module argument specification
    module = AnsibleModule(
        argument_spec=dict(
            profile_type=dict(
                type='str',
                required=True,
                choices=['personal', 'corporate', 'developer', 'designer', 'student', 'server']
            ),
            base_directory=dict(type='str', required=True),
            file_count=dict(type='raw', required=False, default=None),
            faker_seed=dict(type='int', required=False, default=42),
            verbose=dict(type='bool', required=False, default=True),
            multi_user=dict(type='bool', required=False, default=False),
            user_configs=dict(type='list', elements='dict', required=False, default=[])
        ),
        supports_check_mode=False
    )
    
    # Extract parameters
    profile_type = module.params['profile_type']
    base_directory = module.params['base_directory']
    file_count = module.params['file_count']
    faker_seed = module.params['faker_seed']
    verbose = module.params['verbose']
    multi_user = module.params['multi_user']
    user_configs = module.params['user_configs']
    
    # Handle file_count: convert empty string or None to None
    if file_count == '' or file_count == 'None' or file_count is None:
        file_count = None
    elif isinstance(file_count, str):
        try:
            file_count = int(file_count)
        except ValueError:
            file_count = None
    
    # Validate base directory path
    import os
    if not os.path.isabs(base_directory):
        module.fail_json(msg=f"base_directory must be an absolute path: {base_directory}")
    
    # Validate multi-user mode
    if multi_user and not user_configs:
        module.fail_json(msg="multi_user mode requires user_configs parameter")
    
    # Import Layer 3 orchestrator
    try:
        from ansible.module_utils import layer3_commonprofile as l3
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer3_commonprofile: {str(e)}")
    
    # Generate profile(s)
    try:
        generator = l3.Layer3UserProfile()
        
        if multi_user:
            # Generate multiple profiles
            all_stats = generator.generate_multiple_profiles(
                profiles=user_configs,
                base_directory=base_directory,
                faker_seed=faker_seed,
                verbose=verbose
            )
            
            # Calculate aggregate statistics
            total_files = sum(s['total_files'] for s in all_stats)
            total_failed = sum(s['failed_files'] for s in all_stats)
            
            # Return multi-user results
            module.exit_json(
                changed=True,
                profile_type='multi_user',
                profile_name='Multiple Users',
                base_directory=base_directory,
                total_files=total_files,
                failed_files=total_failed,
                users_generated=len(all_stats),
                multi_user_stats=all_stats,
                msg=f"Generated {len(all_stats)} user profiles with {total_files} total files"
            )
        
        else:
            # Generate single profile
            result = profile_generator.generate_profile(
                profile_type=profile_type,
                base_directory=base_directory,
                file_count=file_count,
                faker_seed=faker_seed,
                verbose=verbose
            )
            
            # Return single profile results
            module.exit_json(
                changed=True,
                profile_type=stats['profile_type'],
                profile_name=stats['profile_name'],
                base_directory=stats['base_directory'],
                total_files=stats['total_files'],
                failed_files=stats['failed_files'],
                directories_created=stats['directories_created'],
                file_types=stats['file_types'],
                activity_level=stats['activity_level'],
                temporal_applied=stats['temporal_applied'],
                permissions_applied=stats['permissions_applied'],
                file_size_category=stats['file_size_category'],
                msg=f"Generated {stats['profile_name']} profile with {stats['total_files']} files"
            )
    
    except Exception as e:
        module.fail_json(msg=f"Error generating user profile: {str(e)}")


if __name__ == '__main__':
    main()
