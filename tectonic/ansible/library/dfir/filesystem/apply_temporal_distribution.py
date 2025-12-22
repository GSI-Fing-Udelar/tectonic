#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: apply_temporal_distribution

short_description: Apply temporal distributions to file timestamps (Layer 2)

description:
  - Orchestrates timestamp modification for multiple files using Layer 1 primitives
  - Supports statistical distributions (UNIFORM, GAUSSIAN, EXPONENTIAL, PARETO)
  - Modifies mtime (modification time) and atime (access time)
  - Useful for creating realistic forensic timelines
  
version_added: "2.0.0"

options:
  files:
    description: List of file paths to modify timestamps
    required: true
    type: list
    elements: str
    
  base_timestamp:
    description:
      - Base epoch timestamp for distribution calculations
      - All offsets are calculated relative to this time
    required: true
    type: int
    
  distribution_type:
    description: Statistical distribution type
    required: true
    type: str
    choices: [uniform, gaussian, exponential, pareto, deterministic]
    
  distribution_params:
    description:
      - Distribution-specific parameters
      - See notes for required parameters per distribution type
    required: true
    type: dict
    
  seed:
    description: Random seed for reproducible distributions
    required: false
    type: int
    default: 0

notes:
  - Uses Layer 1 primitive apply_file_timestamps() from module_utils.layer1_primitives
  - Uses Layer 2 orchestrator apply_temporal_distribution() from module_utils.layer2_orchestrators
  - "UNIFORM: requires 'offset_min' and 'offset_max' (e.g., '-30d', '0')"
  - "GAUSSIAN: requires 'mean' and 'stddev' (e.g., '-7d', '2d')"
  - "EXPONENTIAL: requires 'lambda_param' or 'mean' (e.g., '7d')"
  - "PARETO: requires 'alpha' and 'scale' (e.g., 1.5, '-30d')"
  - "DETERMINISTIC: requires 'fixed_offset' (e.g., '-1d')"
  - "Time format: supports 's', 'm', 'h', 'd' suffixes or raw seconds"
  - "Note: Birth time (btime/ctime) CANNOT be modified on Linux filesystems"

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Apply uniform distribution (files created over last 30 days)
- name: Distribute files over last month
  apply_temporal_distribution:
    files:
      - /tmp/file1.docx
      - /tmp/file2.pdf
    base_timestamp: "{{ ansible_date_time.epoch }}"
    distribution_type: uniform
    distribution_params:
      offset_min: "-30d"
      offset_max: "0"
    seed: 42

# Apply Gaussian distribution (concentration around 7 days ago)
- name: Simulate infection window
  apply_temporal_distribution:
    files: "{{ encrypted_files }}"
    base_timestamp: "{{ ansible_date_time.epoch }}"
    distribution_type: gaussian
    distribution_params:
      mean: "-7d"
      stddev: "2d"

# Apply Pareto distribution (power law - most files recent)
- name: Apply power law timestamps
  apply_temporal_distribution:
    files: "{{ all_documents }}"
    base_timestamp: "{{ ansible_date_time.epoch }}"
    distribution_type: pareto
    distribution_params:
      alpha: 1.5
      scale: "-30d"

# Apply deterministic offset (all files same time)
- name: Set all files to specific time
  apply_temporal_distribution:
    files: "{{ victim_files }}"
    base_timestamp: "{{ ansible_date_time.epoch }}"
    distribution_type: deterministic
    distribution_params:
      fixed_offset: "-4h"
'''

RETURN = r'''
changed:
  description: Whether any timestamps were modified
  type: bool
  returned: always
  sample: true

files_modified:
  description: Number of files successfully modified
  type: int
  returned: always
  sample: 150

files_failed:
  description: List of files that failed timestamp modification
  type: list
  returned: always
  sample: []

total_files:
  description: Total number of files processed
  type: int
  returned: always
  sample: 150
'''

from ansible.module_utils.basic import AnsibleModule
import time


def main():
    """
    Main execution function for apply_temporal_distribution module.
    
    This module acts as an Ansible interface to the Layer 2 orchestrator
    apply_temporal_distribution() from module_utils.layer2_orchestrators.
    
    Workflow:
        1. Parse and validate module arguments (supports both simple and complex formats)
        2. Import Layer 2 orchestrator
        3. Call orchestrator with distribution parameters
        4. Return results in Ansible format
    """
    
    # Define module argument specification - support both formats
    module = AnsibleModule(
        argument_spec=dict(
            files=dict(type='list', elements='str', required=True),
            base_timestamp=dict(type='int', required=True),
            # Simple format (backward compatibility)
            distribution_type=dict(
                type='str',
                required=False,
                choices=['uniform', 'gaussian', 'exponential', 'pareto', 'deterministic']
            ),
            distribution_params=dict(type='dict', required=False),
            # Advanced format (separate distributions for each timestamp type)
            creation_distribution=dict(type='dict', required=False),
            modification_distribution=dict(type='dict', required=False),
            access_distribution=dict(type='dict', required=False),
            # Common
            seed=dict(type='int', required=False, default=0)
        ),
        supports_check_mode=False,
        required_one_of=[
            ['distribution_type', 'creation_distribution', 'modification_distribution']
        ]
    )
    
    # Extract parameters
    files = module.params['files']
    base_timestamp = module.params['base_timestamp']
    seed = module.params['seed']
    
    # Detect format and extract distribution info
    distribution_type = module.params.get('distribution_type')
    distribution_params = module.params.get('distribution_params')
    creation_dist = module.params.get('creation_distribution')
    modification_dist = module.params.get('modification_distribution')
    access_dist = module.params.get('access_distribution')
    
    # Use simple format if provided
    if distribution_type and distribution_params:
        # Simple format: apply same distribution to mtime and atime
        dist_type = distribution_type
        dist_params = distribution_params
        use_advanced = False
    elif creation_dist or modification_dist or access_dist:
        # Advanced format: separate distributions
        use_advanced = True
    else:
        module.fail_json(msg="Must provide either distribution_type/distribution_params OR creation/modification/access distributions")
    
    # Validate files list
    if not files or len(files) == 0:
        module.fail_json(msg="files list cannot be empty")
    
    # Import Layer 2 orchestrator
    try:
        from ansible.module_utils import layer2_orchestrators as l2
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer2_orchestrators: {str(e)}")
    
    # Handle advanced format (separate distributions for creation/modification/access)
    if use_advanced:
        try:
            import os
            from datetime import datetime
            
            # Initialize results
            files_processed = 0
            files_failed = []
            timestamp_ranges = {
                'creation': {'min': None, 'max': None},
                'modification': {'min': None, 'max': None},
                'access': {'min': None, 'max': None}
            }
            distribution_summary = {
                'creation': 'N/A',
                'modification': 'N/A',
                'access': 'N/A'
            }
            
            # Process modification distribution (this will set mtime)
            if modification_dist:
                dist_type = modification_dist['type']
                dist_params = modification_dist['params']
                distribution_summary['modification'] = f"{dist_type} ({dist_params})"
                
                success, modified_count, failed, error = l2.apply_temporal_distribution(
                    files=files,
                    base_timestamp=base_timestamp,
                    distribution_type=dist_type,
                    distribution_params=dist_params,
                    seed=seed
                )
                
                if not success:
                    module.fail_json(msg=f"Modification distribution failed: {error}")
                
                files_processed = modified_count
                files_failed.extend(failed)
                
                # Collect modification time ranges
                mtimes = [os.path.getmtime(f) for f in files if os.path.exists(f)]
                if mtimes:
                    timestamp_ranges['modification']['min'] = datetime.fromtimestamp(min(mtimes)).isoformat()
                    timestamp_ranges['modification']['max'] = datetime.fromtimestamp(max(mtimes)).isoformat()
            
            # Process access distribution (this will set atime)
            # Note: We need to apply this after modification
            # For now, we'll set it to be similar to mtime or later
            if access_dist:
                dist_type = access_dist['type']
                dist_params = access_dist['params']
                distribution_summary['access'] = f"{dist_type} ({dist_params})"
                
                # Apply access time distribution (using same approach)
                success, modified_count, failed, error = l2.apply_temporal_distribution(
                    files=files,
                    base_timestamp=base_timestamp,
                    distribution_type=dist_type,
                    distribution_params=dist_params,
                    seed=seed + 1  # Different seed for variation
                )
                
                if not success:
                    module.fail_json(msg=f"Access distribution failed: {error}")
                
                files_failed.extend(failed)
                
                # Collect access time ranges
                atimes = [os.path.getatime(f) for f in files if os.path.exists(f)]
                if atimes:
                    timestamp_ranges['access']['min'] = datetime.fromtimestamp(min(atimes)).isoformat()
                    timestamp_ranges['access']['max'] = datetime.fromtimestamp(max(atimes)).isoformat()
            
            # Creation time tracking (for display only - cannot modify on Linux)
            if creation_dist:
                dist_type = creation_dist['type']
                dist_params = creation_dist['params']
                distribution_summary['creation'] = f"{dist_type} ({dist_params}) - NOT APPLIED (Linux limitation)"
                # Note: Birth time (btime) cannot be modified on Linux
                timestamp_ranges['creation']['min'] = 'N/A (cannot modify btime on Linux)'
                timestamp_ranges['creation']['max'] = 'N/A (cannot modify btime on Linux)'
            
            # Return advanced format results
            module.exit_json(
                changed=True,
                files_processed=files_processed,
                files_failed=files_failed,
                distribution_summary=distribution_summary,
                timestamp_ranges=timestamp_ranges,
                msg=f"Applied temporal distributions to {files_processed}/{len(files)} files"
            )
            
        except Exception as e:
            module.fail_json(msg=f"Unexpected error during advanced timestamp modification: {str(e)}")
    
    # Handle simple format (backward compatibility)
    else:
        # Validate distribution parameters based on type
        required_params = {
            'uniform': ['offset_min', 'offset_max'],
            'gaussian': ['mean', 'stddev'],
            'exponential': ['lambda_param'],  # or 'mean' as alternative
            'pareto': ['alpha', 'scale'],
            'deterministic': ['fixed_offset']
        }
        
        if dist_type in required_params:
            for param in required_params[dist_type]:
                if param not in dist_params and dist_type != 'exponential':
                    module.fail_json(
                        msg=f"distribution_params must include '{param}' for {dist_type} distribution"
                    )
                elif dist_type == 'exponential' and 'lambda_param' not in dist_params and 'mean' not in dist_params:
                    module.fail_json(
                        msg="distribution_params must include either 'lambda_param' or 'mean' for exponential distribution"
                    )
        
        # Call Layer 2 orchestrator to apply temporal distribution
        try:
            success, files_modified, failed_files, error = l2.apply_temporal_distribution(
                files=files,
                base_timestamp=base_timestamp,
                distribution_type=dist_type,
                distribution_params=dist_params,
                seed=seed
            )
            
            if not success:
                module.fail_json(msg=f"Temporal distribution failed: {error}")
            
            # Return simple format results
            module.exit_json(
                changed=True,
                files_modified=files_modified,
                files_failed=failed_files,
                total_files=len(files),
                msg=f"Modified timestamps for {files_modified}/{len(files)} files"
            )
            
        except Exception as e:
            module.fail_json(msg=f"Unexpected error during timestamp modification: {str(e)}")


if __name__ == '__main__':
    main()
