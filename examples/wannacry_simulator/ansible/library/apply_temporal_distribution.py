#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: apply_temporal_distribution

short_description: Applies temporal distributions to file timestamps (Layer 1 primitive)

description:
  - Primitive module to apply temporal distributions to existing files
  - Supports UNIFORM, GAUSSIAN, EXPONENTIAL, and DETERMINISTIC distributions
  - Calculates timestamps in chain (CREATION → MODIFICATION → ACCESS)
  - Maintains temporal invariant (CREATION ≤ MODIFICATION ≤ ACCESS)
  - |
    IMPORTANT LIMITATION: Only modifies mtime and atime timestamps.
    Birth time (btime/creation) CANNOT be modified on Linux ext4/xfs filesystems.
    The creation_distribution parameter is used for calculation logic but does NOT
    modify the actual file birth time (which remains the system-assigned time).

version_added: "1.0.0"

options:
  files:
    description: 
      - List of file paths to apply temporal distribution
      - Can be a single file or multiple files
    required: true
    type: list
    elements: str
  
  base_timestamp:
    description:
      - Base epoch timestamp for calculations
      - All distributions calculate relative to this base
    required: true
    type: int
  
  creation_distribution:
    description: Distribution function for creation timestamp
    required: false
    type: dict
    default: {}
    suboptions:
      type:
        description: Distribution type
        required: true
        type: str
        choices: [uniform, gaussian, exponential, deterministic]
      params:
        description: Distribution parameters (depends on type)
        required: true
        type: dict
  
  modification_distribution:
    description: Distribution function for modification timestamp
    required: false
    type: dict
    default: {}
    suboptions:
      type:
        description: Distribution type
        required: true
        type: str
        choices: [uniform, gaussian, exponential, deterministic, immutable]
      params:
        description: Distribution parameters (depends on type)
        required: true
        type: dict
  
  access_distribution:
    description: Distribution function for access timestamp
    required: false
    type: dict
    default: {}
    suboptions:
      type:
        description: Distribution type
        required: true
        type: str
        choices: [uniform, gaussian, exponential, deterministic]
      params:
        description: Distribution parameters (depends on type)
        required: true
        type: dict
  
  seed:
    description: Random seed for reproducibility
    required: false
    type: int
    default: 0

notes:
  - Distribution parameters vary by type
  - UNIFORM requires offset_min and offset_max (in seconds or human format like "7d")
  - GAUSSIAN requires mean and stddev (in seconds or human format like "2h")
  - EXPONENTIAL requires lambda_param OR mean (human format like "30d")
  - DETERMINISTIC requires fixed_offset (in seconds or human format like "1d")
  - IMMUTABLE sets modification = creation (for backups)
  - 
    FILESYSTEM LIMITATION: Birth time (btime/ctime) cannot be modified on Linux.
    Only mtime (modification) and atime (access) can be changed with os.utime().
    The creation_distribution is used for temporal logic calculations but the actual
    file birth time will always be the system-assigned creation time.
  - To see actual timestamps use 'stat filename' command
  - atime = Access time (when file was last read)
  - mtime = Modification time (when file content was last changed)
  - ctime = Change time (when file metadata was last changed) - auto-updated by system
  - btime = Birth time (when file was created) - IMMUTABLE on ext4/xfs

'''

EXAMPLES = r'''
# Example 1: Apply uniform creation distribution to logs
- name: Uniform creation timestamps (last 7 days)
  apply_temporal_distribution:
    files:
      - /tmp/demo/log1.txt
      - /tmp/demo/log2.txt
    base_timestamp: "{{ ansible_date_time.epoch }}"
    creation_distribution:
      type: uniform
      params:
        offset_min: -604800  # -7 days in seconds
        offset_max: 0
    modification_distribution:
      type: gaussian
      params:
        mean: 7200        # 2 hours after creation
        stddev: 3600      # ±1 hour
    access_distribution:
      type: exponential
      params:
        lambda_param: 0.5  # mean = 2 days

# Example 2: Historical documents with exponential access
- name: Historical documents timestamps
  apply_temporal_distribution:
    files: "{{ historical_files }}"
    base_timestamp: "{{ ansible_date_time.epoch }}"
    creation_distribution:
      type: uniform
      params:
        offset_min: -31536000  # -1 year
        offset_max: -15552000  # -6 months
    modification_distribution:
      type: exponential
      params:
        lambda_param: 0.033  # mean = 30 days
    access_distribution:
      type: exponential
      params:
        lambda_param: 0.011  # mean = 90 days

# Example 3: Immutable backups (deterministic)
- name: Daily backups at 02:00 AM
  apply_temporal_distribution:
    files: "{{ backup_files }}"
    base_timestamp: "{{ ansible_date_time.epoch }}"
    creation_distribution:
      type: deterministic
      params:
        fixed_offset: -86400  # -1 day
        hour: 2
        minute: 0
    modification_distribution:
      type: immutable  # modification = creation
      params: {}
    access_distribution:
      type: deterministic
      params:
        fixed_offset: 120  # +2 minutes after creation

# Example 4: Using seed for reproducibility
- name: Reproducible timestamps
  apply_temporal_distribution:
    files:
      - /tmp/file1.txt
      - /tmp/file2.txt
    base_timestamp: 1732377600
    seed: 42
    creation_distribution:
      type: uniform
      params:
        offset_min: -86400
        offset_max: 0
    modification_distribution:
      type: gaussian
      params:
        mean: 3600
        stddev: 1800
    access_distribution:
      type: exponential
      params:
        lambda_param: 1.0
'''

RETURN = r'''
files_processed:
  description: Number of files processed successfully
  type: int
  returned: always
  sample: 20

files_failed:
  description: Number of files that failed to process
  type: int
  returned: always
  sample: 0

timestamp_ranges:
  description: Timestamp ranges applied
  type: dict
  returned: always
  sample:
    creation:
      min: 1731772800
      max: 1732377600
    modification:
      min: 1731780000
      max: 1732384800
    access:
      min: 1731952800
      max: 1732550400

distribution_summary:
  description: Summary of distributions applied
  type: dict
  returned: always
  sample:
    creation: "uniform(-7d, 0d)"
    modification: "gaussian(μ=2h, σ=1h)"
    access: "exponential(λ=0.5, media=2d)"

failed_files:
  description: List of files that failed to process
  type: list
  returned: when failures occur
  sample: ["/tmp/file1.txt", "/tmp/file2.txt"]
'''

import os
import random
import math
import re
from datetime import datetime
from ansible.module_utils.basic import AnsibleModule


def parse_human_time(time_str):
    """
    Converts human-readable time format to seconds
    
    Supported formats:
        - "5s" or "5sec" or "5seconds" → 5 seconds
        - "10m" or "10min" or "10minutes" → 600 seconds
        - "2h" or "2hr" or "2hours" → 7200 seconds
        - "3d" or "3day" or "3days" → 259200 seconds
        - "1w" or "1week" or "1weeks" → 604800 seconds
        - "1mo" or "1month" or "1months" → 2592000 seconds (30 days)
        - "1y" or "1year" or "1years" → 31536000 seconds (365 days)
        - "-7d" → -604800 (negative offsets supported)
        - "2.5h" → 9000 (decimals supported)
        - Integer → interpreted as seconds directly
    
    Args:
        time_str: Time string in human format or integer
    
    Returns:
        int: Time in seconds
    
    Raises:
        ValueError: If format is invalid
    """
    # If already an integer, return it
    if isinstance(time_str, int):
        return time_str
    
    # If it's a float, convert to int
    if isinstance(time_str, float):
        return int(time_str)
    
    # Convert to string and strip whitespace
    time_str = str(time_str).strip()
    
    # Try to parse as plain integer
    try:
        return int(time_str)
    except ValueError:
        pass
    
    # Try to parse as float (in case user passes "123.45")
    try:
        return int(float(time_str))
    except ValueError:
        pass
    
    # Parse human format with regex
    # Pattern: optional sign, number (int or float), optional space, unit
    pattern = r'^([+-]?)(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$'
    match = re.match(pattern, time_str)
    
    if not match:
        raise ValueError(f"Invalid time format: '{time_str}'. Use formats like '7d', '2h', '30m', or integer seconds")
    
    sign = match.group(1)
    number = float(match.group(2))
    unit = match.group(3).lower()
    
    # Unit conversion table
    units = {
        # Seconds
        's': 1,
        'sec': 1,
        'second': 1,
        'seconds': 1,
        # Minutes
        'm': 60,
        'min': 60,
        'mins': 60,
        'minute': 60,
        'minutes': 60,
        # Hours
        'h': 3600,
        'hr': 3600,
        'hrs': 3600,
        'hour': 3600,
        'hours': 3600,
        # Days
        'd': 86400,
        'day': 86400,
        'days': 86400,
        # Weeks
        'w': 604800,
        'wk': 604800,
        'week': 604800,
        'weeks': 604800,
        # Months (30 days)
        'mo': 2592000,
        'mon': 2592000,
        'month': 2592000,
        'months': 2592000,
        # Years (365 days)
        'y': 31536000,
        'yr': 31536000,
        'year': 31536000,
        'years': 31536000,
    }
    
    if unit not in units:
        raise ValueError(
            f"Unknown time unit: '{unit}'. "
            f"Supported units: s, m, h, d, w, mo, y (and variations)"
        )
    
    # Calculate seconds
    seconds = int(number * units[unit])
    
    # Apply sign
    if sign == '-':
        seconds = -seconds
    
    return seconds


def validate_time_param(param_value, param_name, allow_negative=True):
    """
    Validates and converts a time parameter
    
    Args:
        param_value: Value to validate (can be int, str, or human format)
        param_name: Name of parameter (for error messages)
        allow_negative: Whether negative values are allowed
    
    Returns:
        int: Validated time in seconds
    
    Raises:
        ValueError: If validation fails
    """
    try:
        seconds = parse_human_time(param_value)
    except ValueError as e:
        raise ValueError(f"Invalid {param_name}: {str(e)}")
    
    if not allow_negative and seconds < 0:
        raise ValueError(f"{param_name} cannot be negative (got {param_value} = {seconds}s)")
    
    return seconds


def uniform_distribution(offset_min, offset_max):
    """
    Generates random offset with uniform distribution
    
    Args:
        offset_min: minimum offset (seconds, int, or human format like "-7d")
        offset_max: maximum offset (seconds, int, or human format like "0")
    
    Returns:
        int: random offset in seconds
    """
    # Parse human-readable formats
    min_seconds = validate_time_param(offset_min, "offset_min", allow_negative=True)
    max_seconds = validate_time_param(offset_max, "offset_max", allow_negative=True)
    
    if min_seconds > max_seconds:
        raise ValueError(f"offset_min ({min_seconds}s) cannot be greater than offset_max ({max_seconds}s)")
    
    return random.randint(min_seconds, max_seconds)


def gaussian_distribution(mean, stddev):
    """
    Generates random offset with gaussian (normal) distribution
    
    Args:
        mean: mean value (seconds, int, or human format like "2h")
        stddev: standard deviation (seconds, int, or human format like "1h")
    
    Returns:
        int: random offset in seconds
    """
    # Parse human-readable formats
    mean_seconds = validate_time_param(mean, "mean", allow_negative=False)
    stddev_seconds = validate_time_param(stddev, "stddev", allow_negative=False)
    
    if stddev_seconds < 0:
        raise ValueError(f"stddev cannot be negative (got {stddev})")
    
    value = random.gauss(mean_seconds, stddev_seconds)
    # Ensure minimum 1 second
    return max(1, int(value))


def exponential_distribution(lambda_param=None, mean=None):
    """
    Generates random offset with exponential distribution
    
    Can specify either lambda_param OR mean (will calculate lambda from mean)
    
    Args:
        lambda_param: rate parameter (λ = 1/mean) - use this OR mean
        mean: mean value (human format like "2d") - will calculate lambda
    
    Returns:
        int: random offset in seconds
    """
    # Allow specifying mean instead of lambda
    if mean is not None and lambda_param is None:
        mean_seconds = validate_time_param(mean, "mean", allow_negative=False)
        if mean_seconds <= 0:
            raise ValueError(f"Exponential mean must be positive (got {mean})")
        lambda_param = 1.0 / mean_seconds
    
    if lambda_param is None:
        raise ValueError("Exponential distribution requires either 'lambda_param' or 'mean'")
    
    if lambda_param <= 0:
        raise ValueError(f"lambda_param must be positive (got {lambda_param})")
    
    # random.expovariate expects lambda (rate)
    value = random.expovariate(lambda_param)
    # Convert to seconds and ensure minimum 1 second
    return max(1, int(value))


def deterministic_offset(fixed_offset, hour=None, minute=None, base_ts=None):
    """
    Generates deterministic offset (fixed value)
    
    Args:
        fixed_offset: fixed offset (seconds, int, or human format like "-1d")
        hour: optional hour to snap to (0-23)
        minute: optional minute to snap to (0-59)
        base_ts: base timestamp for hour/minute calculations
    
    Returns:
        int: fixed offset or adjusted timestamp
    """
    # Parse human-readable format
    offset_seconds = validate_time_param(fixed_offset, "fixed_offset", allow_negative=True)
    
    if hour is not None and minute is not None and base_ts is not None:
        # Validate hour and minute
        if not (0 <= hour <= 23):
            raise ValueError(f"hour must be between 0 and 23 (got {hour})")
        if not (0 <= minute <= 59):
            raise ValueError(f"minute must be between 0 and 59 (got {minute})")
        
        # Calculate timestamp at specific hour:minute
        day_start = base_ts - (base_ts % 86400)
        return (hour * 3600) + (minute * 60)
    
    return offset_seconds


def calculate_creation_timestamp(base_ts, distribution):
    """
    Calculates creation timestamp based on distribution
    
    Returns:
        int: creation timestamp (epoch)
    """
    dist_type = distribution.get('type', 'uniform').lower()
    params = distribution.get('params', {})
    
    if dist_type == 'uniform':
        offset = uniform_distribution(
            params.get('offset_min', '-7d'),  # default: -7 days
            params.get('offset_max', 0)
        )
        return base_ts + offset
    
    elif dist_type == 'gaussian':
        mean = params.get('mean', '2h')
        stddev = params.get('stddev', '1h')
        offset = gaussian_distribution(mean, stddev)
        return base_ts + offset
    
    elif dist_type == 'exponential':
        lambda_param = params.get('lambda_param')
        mean = params.get('mean')
        offset = exponential_distribution(lambda_param=lambda_param, mean=mean)
        return base_ts - offset  # Usually creation is in the past
    
    elif dist_type == 'deterministic':
        fixed_offset = params.get('fixed_offset', 0)
        hour = params.get('hour')
        minute = params.get('minute')
        
        offset_seconds = validate_time_param(fixed_offset, "fixed_offset", allow_negative=True)
        
        if hour is not None and minute is not None:
            # Calculate specific time
            day_start = (base_ts + offset_seconds) - ((base_ts + offset_seconds) % 86400)
            return day_start + (hour * 3600) + (minute * 60)
        
        return base_ts + offset_seconds
    
    else:
        return base_ts


def calculate_modification_timestamp(create_ts, distribution):
    """
    Calculates modification timestamp based on creation and distribution
    
    Returns:
        int: modification timestamp (epoch)
    """
    dist_type = distribution.get('type', 'gaussian').lower()
    params = distribution.get('params', {})
    
    if dist_type == 'immutable':
        # Modification = creation (backups, immutable files)
        return create_ts
    
    elif dist_type == 'uniform':
        offset = uniform_distribution(
            params.get('offset_min', 0),
            params.get('offset_max', '1h')  # default: 0-1 hour
        )
        return create_ts + offset
    
    elif dist_type == 'gaussian':
        mean = params.get('mean', '2h')  # default: 2 hours
        stddev = params.get('stddev', '1h')  # default: ±1 hour
        offset = gaussian_distribution(mean, stddev)
        return create_ts + offset
    
    elif dist_type == 'exponential':
        lambda_param = params.get('lambda_param')
        mean = params.get('mean', '30d')  # default: mean = 30 days
        offset = exponential_distribution(lambda_param=lambda_param, mean=mean)
        return create_ts + offset
    
    elif dist_type == 'deterministic':
        fixed_offset = params.get('fixed_offset', 0)
        offset_seconds = validate_time_param(fixed_offset, "fixed_offset", allow_negative=True)
        return create_ts + offset_seconds
    
    else:
        return create_ts + 3600  # default: +1 hour


def calculate_access_timestamp(modify_ts, distribution):
    """
    Calculates access timestamp based on modification and distribution
    
    Returns:
        int: access timestamp (epoch)
    """
    dist_type = distribution.get('type', 'exponential').lower()
    params = distribution.get('params', {})
    
    if dist_type == 'uniform':
        offset = uniform_distribution(
            params.get('offset_min', 0),
            params.get('offset_max', '1d')  # default: 0-1 day
        )
        return modify_ts + offset
    
    elif dist_type == 'gaussian':
        mean = params.get('mean', '1h')  # default: 1 hour
        stddev = params.get('stddev', '30m')  # default: ±30 min
        offset = gaussian_distribution(mean, stddev)
        return modify_ts + offset
    
    elif dist_type == 'exponential':
        lambda_param = params.get('lambda_param')
        mean = params.get('mean', '2d')  # default: mean = 2 days
        offset = exponential_distribution(lambda_param=lambda_param, mean=mean)
        return modify_ts + offset
    
    elif dist_type == 'deterministic':
        fixed_offset = params.get('fixed_offset', '2m')  # default: +2 minutes
        offset_seconds = validate_time_param(fixed_offset, "fixed_offset", allow_negative=True)
        return modify_ts + offset_seconds
    
    else:
        return modify_ts + 86400  # default: +1 day


def apply_timestamps_to_file(filepath, create_ts, modify_ts, access_ts):
    """
    Applies timestamps to a file using os.utime
    
    IMPORTANT: Only modifies mtime (modification) and atime (access)
    Birth time (btime/creation) CANNOT be modified on Linux ext4/xfs filesystems
    
    Args:
        filepath: path to file
        create_ts: creation timestamp (IGNORED - cannot be modified on Linux)
        modify_ts: modification timestamp (mtime) - CAN BE MODIFIED
        access_ts: access timestamp (atime) - CAN BE MODIFIED
    
    Returns:
        bool: True if successful, False otherwise
    
    Note:
        os.utime(path, (atime, mtime)) - sets access and modification times
        Birth time is set by the filesystem at file creation and is immutable
    """
    try:
        # Apply timestamps: (access_time, modification_time)
        # Order matters: os.utime expects (atime, mtime)
        os.utime(filepath, (access_ts, modify_ts))
        return True
    except Exception as e:
        return False


def format_human_time(seconds):
    """
    Converts seconds back to human-readable format
    
    Args:
        seconds: Time in seconds (can be negative)
    
    Returns:
        str: Human-readable format (e.g., "-7d", "2h", "30m")
    """
    if seconds == 0:
        return "0s"
    
    negative = seconds < 0
    seconds = abs(seconds)
    
    # Choose best unit
    if seconds >= 31536000 and seconds % 31536000 == 0:
        value = seconds // 31536000
        unit = 'y'
    elif seconds >= 2592000 and seconds % 2592000 == 0:
        value = seconds // 2592000
        unit = 'mo'
    elif seconds >= 604800 and seconds % 604800 == 0:
        value = seconds // 604800
        unit = 'w'
    elif seconds >= 86400 and seconds % 86400 == 0:
        value = seconds // 86400
        unit = 'd'
    elif seconds >= 3600 and seconds % 3600 == 0:
        value = seconds // 3600
        unit = 'h'
    elif seconds >= 60 and seconds % 60 == 0:
        value = seconds // 60
        unit = 'm'
    else:
        value = seconds
        unit = 's'
    
    sign = '-' if negative else ''
    return f"{sign}{value}{unit}"


def format_distribution_summary(dist):
    """
    Formats distribution for human-readable summary
    """
    if not dist:
        return "none"
    
    dist_type = dist.get('type', 'unknown')
    params = dist.get('params', {})
    
    if dist_type == 'uniform':
        offset_min = params.get('offset_min', 0)
        offset_max = params.get('offset_max', 0)
        # Try to parse if they're human format, otherwise treat as seconds
        try:
            min_sec = validate_time_param(offset_min, "offset_min", allow_negative=True)
            max_sec = validate_time_param(offset_max, "offset_max", allow_negative=True)
            min_str = format_human_time(min_sec)
            max_str = format_human_time(max_sec)
            return f"uniform({min_str}, {max_str})"
        except:
            return f"uniform({offset_min}, {offset_max})"
    
    elif dist_type == 'gaussian':
        mean = params.get('mean', 0)
        stddev = params.get('stddev', 0)
        try:
            mean_sec = validate_time_param(mean, "mean", allow_negative=False)
            std_sec = validate_time_param(stddev, "stddev", allow_negative=False)
            mean_str = format_human_time(mean_sec)
            std_str = format_human_time(std_sec)
            return f"gaussian(μ={mean_str}, σ={std_str})"
        except:
            return f"gaussian(μ={mean}, σ={stddev})"
    
    elif dist_type == 'exponential':
        lambda_param = params.get('lambda_param')
        mean = params.get('mean')
        
        if mean is not None:
            try:
                mean_sec = validate_time_param(mean, "mean", allow_negative=False)
                mean_str = format_human_time(mean_sec)
                return f"exponential(media={mean_str})"
            except:
                return f"exponential(media={mean})"
        elif lambda_param is not None:
            mean_sec = int(1 / lambda_param) if lambda_param > 0 else 0
            mean_str = format_human_time(mean_sec)
            return f"exponential(λ={lambda_param}, media={mean_str})"
        return "exponential"
    
    elif dist_type == 'deterministic':
        fixed = params.get('fixed_offset', 0)
        hour = params.get('hour')
        minute = params.get('minute')
        if hour is not None:
            return f"deterministic({hour:02d}:{minute:02d})"
        try:
            fixed_sec = validate_time_param(fixed, "fixed_offset", allow_negative=True)
            fixed_str = format_human_time(fixed_sec)
            return f"deterministic({fixed_str})"
        except:
            return f"deterministic({fixed})"
    
    elif dist_type == 'immutable':
        return "immutable"
    
    return dist_type


def main():
    module = AnsibleModule(
        argument_spec=dict(
            files=dict(type='list', required=True, elements='str'),
            base_timestamp=dict(type='int', required=True),
            creation_distribution=dict(type='dict', required=False, default={}),
            modification_distribution=dict(type='dict', required=False, default={}),
            access_distribution=dict(type='dict', required=False, default={}),
            seed=dict(type='int', required=False, default=0)
        ),
        supports_check_mode=True
    )
    
    files = module.params['files']
    base_timestamp = module.params['base_timestamp']
    creation_dist = module.params['creation_distribution']
    modification_dist = module.params['modification_distribution']
    access_dist = module.params['access_distribution']
    seed = module.params['seed']
    
    # Set random seed for reproducibility
    if seed > 0:
        random.seed(seed)
    
    # Validate files exist
    valid_files = []
    for filepath in files:
        if not os.path.exists(filepath):
            module.warn(f"File does not exist: {filepath}")
        elif not os.path.isfile(filepath):
            module.warn(f"Not a file: {filepath}")
        else:
            valid_files.append(filepath)
    
    if not valid_files:
        module.fail_json(msg="No valid files to process")
    
    # Check mode
    if module.check_mode:
        module.exit_json(
            changed=False,
            msg="Check mode: timestamps not applied",
            files_to_process=len(valid_files)
        )
    
    # Process files
    results = []
    failed_files = []
    
    create_timestamps = []
    modify_timestamps = []
    access_timestamps = []
    
    for filepath in valid_files:
        try:
            # Calculate timestamps in chain
            create_ts = calculate_creation_timestamp(base_timestamp, creation_dist)
            modify_ts = calculate_modification_timestamp(create_ts, modification_dist)
            access_ts = calculate_access_timestamp(modify_ts, access_dist)
            
            # Ensure invariant: creation <= modification <= access
            if modify_ts < create_ts:
                modify_ts = create_ts
            if access_ts < modify_ts:
                access_ts = modify_ts
            
            # Apply timestamps
            success = apply_timestamps_to_file(filepath, create_ts, modify_ts, access_ts)
            
            if success:
                results.append({
                    'file': filepath,
                    'creation': create_ts,
                    'modification': modify_ts,
                    'access': access_ts
                })
                
                create_timestamps.append(create_ts)
                modify_timestamps.append(modify_ts)
                access_timestamps.append(access_ts)
            else:
                failed_files.append(filepath)
        
        except Exception as e:
            failed_files.append(filepath)
            module.warn(f"Failed to process {filepath}: {str(e)}")
    
    # Calculate ranges
    timestamp_ranges = {}
    if create_timestamps:
        timestamp_ranges['creation'] = {
            'min': min(create_timestamps),
            'max': max(create_timestamps)
        }
    if modify_timestamps:
        timestamp_ranges['modification'] = {
            'min': min(modify_timestamps),
            'max': max(modify_timestamps)
        }
    if access_timestamps:
        timestamp_ranges['access'] = {
            'min': min(access_timestamps),
            'max': max(access_timestamps)
        }
    
    # Distribution summary
    dist_summary = {
        'creation': format_distribution_summary(creation_dist),
        'modification': format_distribution_summary(modification_dist),
        'access': format_distribution_summary(access_dist)
    }
    
    # Exit with results
    module.exit_json(
        changed=True,
        files_processed=len(results),
        files_failed=len(failed_files),
        timestamp_ranges=timestamp_ranges,
        distribution_summary=dist_summary,
        failed_files=failed_files if failed_files else [],
        sample_results=results[:5]  # First 5 as sample
    )


if __name__ == '__main__':
    main()
