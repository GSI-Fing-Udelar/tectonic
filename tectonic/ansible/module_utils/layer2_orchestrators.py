"""
Filesystem Layer 2 Orchestrators - Bulk Operations and Complex Workflows
=========================================================================

Author: Filesystem Forensics Team
Purpose: Provide bulk operation orchestrators for ransomware simulation
Context: Layer 2 (Orchestration) filesystem primitives for WannaCry simulator

This module provides high-level orchestrators that coordinate multiple Layer 1
primitives to perform complex operations like bulk file generation, temporal
distribution application, and shared characteristics management.

Dependencies:
    - layer1_primitives: Atomic file operations
    - faker: Realistic name/content generation
    - random: Distribution calculations

Type Safety:
    All functions use Python 3.8+ type hints (PEP 484)
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import random
import glob
import math
from typing import List, Dict, Tuple, Optional, Any, Union
from datetime import datetime, timedelta

try:
    from faker import Faker
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False


# ============================================================================
# HELPER FUNCTIONS FOR LAYER 2
# ============================================================================

def distribute_by_percentages(
    total: int,
    distribution: Dict[str, float]
) -> Dict[str, int]:
    """
    Distribute total count according to percentages.
    
    This helper ensures that the sum of distributed counts equals total,
    allocating remainders to the last category.
    
    Args:
        total: Total number of items to distribute
        distribution: Dictionary of {category: percentage}
        
    Returns:
        Dict[str, int]: Dictionary of {category: count}
    """
    result = {}
    total_percentage = sum(distribution.values())
    
    # Normalize percentages to sum to 1.0
    distribution_norm = {k: v / total_percentage for k, v in distribution.items()}
    
    # Calculate counts for all categories except last
    remaining = total
    categories = list(distribution_norm.items())
    
    for category, percentage in categories[:-1]:
        count = int(total * percentage)
        result[category] = count
        remaining -= count
    
    # Last category gets all remaining items
    last_category = categories[-1][0]
    result[last_category] = remaining
    
    return result


def expand_filename_pattern(
    pattern: str,
    index: int,
    file_type: str,
    faker_enabled: bool = True,
    seed: Optional[int] = None
) -> str:
    """
    Expand filename pattern with variables.
    
    Supported variables:
        {n} - file number
        {date} - current date (YYYYMMDD)
        {time} - current time (HHMMSS)
        {file_type} - file extension
        {faker_name} - random person name
        {faker_company} - random company name
        {faker_city} - random city
        {faker_word} - random word
        {faker_job} - random job title
    
    Each file gets UNIQUE faker values by using seed + index.
    
    Args:
        pattern: Filename template with variables
        index: File index (0-based)
        file_type: File extension
        faker_enabled: Enable Faker variables
        seed: Base random seed
        
    Returns:
        str: Expanded filename
    """
    result = pattern
    
    # Basic variables
    result = result.replace('{n}', str(index))
    result = result.replace('{date}', datetime.now().strftime('%Y%m%d'))
    result = result.replace('{time}', datetime.now().strftime('%H%M%S'))
    result = result.replace('{file_type}', file_type)
    
    # Faker variables (unique per file using seed + index)
    if faker_enabled and FAKER_AVAILABLE and any('{faker_' in result for _ in range(1)):
        # Create unique faker instance for this file
        file_seed = (seed if seed else 1) + index
        Faker.seed(file_seed)
        fake = Faker('en_US')
        
        result = result.replace('{faker_name}', fake.name().replace(' ', '_'))
        result = result.replace('{faker_company}', fake.company().replace(' ', '_'))
        result = result.replace('{faker_city}', fake.city().replace(' ', '_'))
        result = result.replace('{faker_word}', fake.word())
        result = result.replace('{faker_job}', fake.job().replace(' ', '_'))
    
    return result


def parse_time_offset(offset_str: str) -> int:
    """
    Parse human-readable time offset to seconds.
    
    Examples:
        "2h" -> 7200
        "30m" -> 1800
        "7d" -> 604800
        
    Args:
        offset_str: Time string with unit (s, m, h, d)
        
    Returns:
        int: Offset in seconds
    """
    if not offset_str:
        return 0
    
    offset_str = str(offset_str).strip().lower()
    
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }
    
    for unit, multiplier in units.items():
        if offset_str.endswith(unit):
            try:
                value = float(offset_str[:-1])
                return int(value * multiplier)
            except ValueError:
                return 0
    
    # No unit, assume seconds
    try:
        return int(offset_str)
    except ValueError:
        return 0


# ============================================================================
# LAYER 2: BULK FILE GENERATION ORCHESTRATOR
# ============================================================================

def generate_files_bulk(
    count: int,
    distribution: Dict[str, float],
    base_directory: str,
    structure: str = 'flat',
    name_pattern: str = 'document_{n}',
    tree_depth: int = 3,
    subdirs_per_level: int = 3,
    faker_seed: int = 1
) -> Tuple[bool, List[str], List[str], str]:
    """
    Generate multiple files with specified distribution and structure.
    
    This orchestrator coordinates Layer 1 file creation primitives to generate
    a bulk set of files. It handles directory structure creation, filename
    generation, and file type distribution.
    
    Workflow:
        1. Calculate file counts per type based on distribution
        2. Generate directory structure (flat or tree)
        3. Generate filenames using pattern
        4. Call appropriate Layer 1 primitive for each file type
        5. Return results summary
    
    Args:
        count: Total number of files to generate
        distribution: File type distribution {ext: percentage}
        base_directory: Root directory for file generation
        structure: Directory structure ('flat' or 'tree')
        name_pattern: Filename template with variables
        tree_depth: Maximum depth for tree structure
        subdirs_per_level: Subdirectories per level in tree
        faker_seed: Seed for reproducible generation
        
    Returns:
        Tuple[bool, List[str], List[str], str]: 
            (success, created_files, failed_files, error_message)
    """
    from . import layer1_primitives as l1
    
    try:
        # Step 1: Distribute file types
        type_counts = distribute_by_percentages(count, distribution)
        
        # Step 2: Generate directory structure
        if structure == 'flat':
            directories = _generate_flat_structure(base_directory, count)
        elif structure == 'tree':
            directories = _generate_tree_structure(
                base_directory, count, tree_depth, subdirs_per_level, faker_seed
            )
        else:
            return False, [], [], f"Invalid structure type: {structure}"
        
        # Step 3: Generate files
        created_files = []
        failed_files = []
        file_index = 0
        
        for file_type, file_count in type_counts.items():
            for i in range(file_count):
                # Generate filename
                filename = expand_filename_pattern(
                    name_pattern,
                    file_index,
                    file_type,
                    faker_enabled=True,
                    seed=faker_seed
                )
                
                # Ensure filename has correct extension
                if not filename.endswith(f'.{file_type}'):
                    filename = f"{filename}.{file_type}"
                
                # Select directory for this file
                directory = directories[file_index % len(directories)]
                filepath = os.path.join(directory, filename)
                
                # Call appropriate Layer 1 primitive
                success, error = _create_file_by_type(
                    filepath, file_type, seed=faker_seed + file_index
                )
                
                if success:
                    created_files.append(filepath)
                else:
                    failed_files.append((filepath, error))
                
                file_index += 1
        
        return True, created_files, failed_files, ""
    
    except Exception as e:
        return False, [], [], str(e)


def _generate_flat_structure(base_directory: str, count: int) -> List[str]:
    """
    Generate flat directory structure (all files in base_directory).
    
    Args:
        base_directory: Root directory
        count: Number of files (unused in flat structure)
        
    Returns:
        List[str]: List of directory paths (repeated base_directory)
    """
    os.makedirs(base_directory, exist_ok=True)
    return [base_directory] * count


def _generate_tree_structure(
    base_directory: str,
    count: int,
    depth: int,
    subdirs_per_level: int,
    seed: int
) -> List[str]:
    """
    Generate tree directory structure with random subdirectories.
    
    Args:
        base_directory: Root directory
        count: Number of files to distribute
        depth: Maximum tree depth
        subdirs_per_level: Subdirectories per level
        seed: Random seed
        
    Returns:
        List[str]: List of directory paths for file distribution
    """
    if FAKER_AVAILABLE:
        Faker.seed(seed)
        fake = Faker('en_US')
    
    # Create directory tree
    directories = [base_directory]
    os.makedirs(base_directory, exist_ok=True)
    
    for level in range(depth):
        new_directories = []
        for parent_dir in directories:
            for i in range(subdirs_per_level):
                # Generate subdirectory name
                if FAKER_AVAILABLE:
                    subdir_name = fake.word() + str(i)
                else:
                    subdir_name = f"subdir_{level}_{i}"
                
                subdir_path = os.path.join(parent_dir, subdir_name)
                os.makedirs(subdir_path, exist_ok=True)
                new_directories.append(subdir_path)
        
        directories.extend(new_directories)
    
    # Distribute files randomly among directories
    random.seed(seed)
    return [random.choice(directories) for _ in range(count)]


def _create_file_by_type(
    filepath: str,
    file_type: str,
    seed: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Call appropriate Layer 1 primitive based on file type.
    
    Args:
        filepath: Full path for file
        file_type: File extension
        seed: Random seed
        
    Returns:
        Tuple[bool, str]: (success, error_message)
    """
    from . import layer1_primitives as l1
    
    if file_type in ['txt', 'log', 'csv']:
        return l1.create_text_file(filepath, size=5000, seed=seed)
    
    elif file_type == 'pdf':
        return l1.create_pdf_file(filepath, size=10000, seed=seed)
    
    elif file_type in ['jpg', 'jpeg', 'png']:
        return l1.create_image_file(filepath, extension=file_type, size=50000, seed=seed)
    
    elif file_type in ['docx', 'doc']:
        return l1.create_docx_file(filepath, seed=seed)
    
    elif file_type == 'xlsx':
        return l1.create_xlsx_file(filepath, rows=20, cols=5, seed=seed)
    
    elif file_type in ['zip', 'tar.gz', 'tar']:
        return l1.create_compressed_file(filepath, extension=file_type, seed=seed)
    
    elif file_type in ['sh', 'py', 'bash']:
        return l1.create_executable_file(filepath, extension=file_type)
    
    else:
        # Fallback: create empty text file
        return l1.create_text_file(filepath, content="", seed=seed)


# ============================================================================
# LAYER 2: TEMPORAL DISTRIBUTION ORCHESTRATOR
# ============================================================================

def apply_temporal_distribution(
    files: List[str],
    base_timestamp: int,
    distribution_type: str,
    distribution_params: Dict[str, Any],
    seed: int = 0
) -> Tuple[bool, int, List[str], str]:
    """
    Apply temporal distribution to file timestamps.
    
    This orchestrator modifies mtime/atime of multiple files according to
    a statistical distribution. Supports:
    - UNIFORM: Random timestamps in a range
    - GAUSSIAN: Normal distribution around a mean
    - EXPONENTIAL: Exponential decay from base time
    - PARETO: Power law distribution (old files are rare)
    
    Args:
        files: List of file paths to modify
        base_timestamp: Base epoch timestamp
        distribution_type: Distribution function type
        distribution_params: Distribution-specific parameters
        seed: Random seed for reproducibility
        
    Returns:
        Tuple[bool, int, List[str], str]:
            (success, files_modified, failed_files, error_message)
    """
    from . import layer1_primitives as l1
    
    try:
        random.seed(seed)
        
        files_modified = 0
        failed_files = []
        
        for filepath in files:
            if not os.path.exists(filepath):
                failed_files.append(filepath)
                continue
            
            # Calculate timestamp offset based on distribution
            offset = _calculate_temporal_offset(
                distribution_type,
                distribution_params,
                seed + files_modified  # Unique seed per file
            )
            
            # Apply timestamp (modification time)
            timestamp = base_timestamp + offset
            success, error = l1.apply_file_timestamps(
                filepath,
                mtime=timestamp,
                atime=timestamp + random.randint(0, 3600)  # atime slightly after mtime
            )
            
            if success:
                files_modified += 1
            else:
                failed_files.append(filepath)
        
        return True, files_modified, failed_files, ""
    
    except Exception as e:
        return False, 0, [], str(e)


def _calculate_temporal_offset(
    distribution_type: str,
    params: Dict[str, Any],
    seed: int
) -> int:
    """
    Calculate timestamp offset based on distribution type.
    
    Args:
        distribution_type: Type of distribution
        params: Distribution parameters
        seed: Random seed
        
    Returns:
        int: Offset in seconds (negative for past timestamps)
    """
    random.seed(seed)
    
    if distribution_type == 'uniform':
        # Uniform distribution between min and max
        offset_min = parse_time_offset(params.get('offset_min', '-30d'))
        offset_max = parse_time_offset(params.get('offset_max', '0'))
        return random.randint(offset_min, offset_max)
    
    elif distribution_type == 'gaussian':
        # Gaussian (normal) distribution
        mean = parse_time_offset(params.get('mean', '-7d'))
        stddev = parse_time_offset(params.get('stddev', '2d'))
        return int(random.gauss(mean, stddev))
    
    elif distribution_type == 'exponential':
        # Exponential distribution (decay)
        lambda_param = params.get('lambda_param', 1.0 / parse_time_offset('7d'))
        return -int(random.expovariate(lambda_param))
    
    elif distribution_type == 'pareto':
        # Pareto distribution (power law)
        alpha = params.get('alpha', 1.5)
        scale = parse_time_offset(params.get('scale', '-30d'))
        # Generate Pareto-distributed value
        pareto_value = (random.paretovariate(alpha) - 1) * abs(scale)
        return -int(pareto_value)
    
    elif distribution_type == 'deterministic':
        # Fixed offset for all files
        fixed_offset = parse_time_offset(params.get('fixed_offset', '-1d'))
        return fixed_offset
    
    else:
        # Default: no offset
        return 0


# ============================================================================
# LAYER 2: SHARED CHARACTERISTICS ORCHESTRATOR
# ============================================================================

def apply_shared_characteristics(
    base_directory: str,
    default_permissions: Optional[int] = None,
    default_owners: Optional[List[Dict[str, Any]]] = None,
    deleted_ratio: float = 0.0,
    deleted_count: Optional[int] = None,
    deletion_mode: str = 'soft',
    minimum_size: Optional[Union[int, str]] = None,
    maximum_size: Optional[Union[int, str]] = None,
    average_size: Optional[Union[int, str]] = None,
    name_pattern: str = '*',
    recursive: bool = True
) -> Tuple[bool, Dict[str, int], List[str], str]:
    """
    Apply shared characteristics to existing files.
    
    This orchestrator modifies characteristics of multiple files:
    - File permissions (chmod)
    - File ownership (chown)
    - Size adjustments (minimum, maximum, average)
    - Deletion simulation (mark files as deleted)
    
    Args:
        base_directory: Directory containing files
        default_permissions: Permission mode (e.g., 0o644, 0o444)
        default_owners: List of owners with percentage distribution
                       [{'owner': 'user1', 'percentage': 50}, ...]
        deleted_ratio: Percentage of files to delete (0.0-1.0)
        deleted_count: Exact number of files to delete (overrides ratio)
        deletion_mode: 'hard' = unrecoverable deletion, 'soft' = forensic recoverable
        minimum_size: Minimum file size (e.g., \"50KB\" or 51200)
        maximum_size: Maximum file size (e.g., \"100KB\" or 102400)
        average_size: Target average size (e.g., \"75KB\" with ±20% variance)
        name_pattern: Glob pattern to filter files
        recursive: Search recursively
        
    Returns:
        Tuple[bool, Dict[str, int], List[str], str]:
            (success, statistics, failed_files, error_message)
    """
    from . import layer1_primitives as l1
    
    try:
        # Step 1: List all files matching pattern
        files = _list_files_by_pattern(base_directory, name_pattern, recursive)
        
        if not files:
            return True, {'files_found': 0}, [], "No files found"
        
        stats = {
            'files_found': len(files),
            'permissions_changed': 0,
            'owners_changed': 0,
            'sizes_adjusted': 0,
            'files_deleted': 0,
            'files_processed': len(files)
        }
        failed_files = []
        
        # Step 2: Apply ownership distribution if specified
        if default_owners is not None:
            # Parse size strings if needed
            import pwd
            total_percentage = sum(o.get('percentage', 0) for o in default_owners)
            if abs(total_percentage - 100) > 0.1:
                return False, {}, [], f"Owner percentages must sum to 100 (got {total_percentage})"
            
            # Calculate file counts for each owner
            file_indices = list(range(len(files)))
            random.shuffle(file_indices)
            
            start_idx = 0
            for owner_spec in default_owners:
                owner_name = owner_spec.get('owner')
                percentage = owner_spec.get('percentage', 0)
                file_count = int(len(files) * percentage / 100.0)
                
                # Get UID for owner
                try:
                    uid = pwd.getpwnam(owner_name).pw_uid
                    gid = pwd.getpwnam(owner_name).pw_gid
                except KeyError:
                    return False, {}, [], f"User '{owner_name}' does not exist"
                
                # Apply ownership to assigned files
                for idx in file_indices[start_idx:start_idx + file_count]:
                    filepath = files[idx]
                    success, error = l1.change_file_ownership(filepath, uid, gid)
                    if success:
                        stats['owners_changed'] += 1
                    else:
                        failed_files.append(filepath)
                
                start_idx += file_count
        
        # Step 3: Apply size adjustments if specified
        min_size_bytes = None
        max_size_bytes = None
        avg_size_bytes = None
        
        if minimum_size:
            min_size_bytes = l1.parse_size_string(minimum_size) if isinstance(minimum_size, str) else minimum_size
        if maximum_size:
            max_size_bytes = l1.parse_size_string(maximum_size) if isinstance(maximum_size, str) else maximum_size
        if average_size:
            avg_size_bytes = l1.parse_size_string(average_size) if isinstance(average_size, str) else average_size
        
        # Apply size constraints
        if min_size_bytes or max_size_bytes or avg_size_bytes:
            import os
            
            if avg_size_bytes:
                # Distribute sizes around average with ±20% variance
                for filepath in files:
                    target_size = int(avg_size_bytes * random.uniform(0.8, 1.2))
                    current_size = os.path.getsize(filepath)
                    if current_size != target_size:
                        success, error = l1.adjust_file_size(filepath, target_size)
                        if success:
                            stats['sizes_adjusted'] += 1
                        else:
                            failed_files.append(filepath)
            else:
                # Apply min/max constraints
                for filepath in files:
                    current_size = os.path.getsize(filepath)
                    target_size = current_size
                    
                    if min_size_bytes and current_size < min_size_bytes:
                        target_size = min_size_bytes
                    elif max_size_bytes and current_size > max_size_bytes:
                        target_size = max_size_bytes
                    
                    if target_size != current_size:
                        success, error = l1.adjust_file_size(filepath, target_size)
                        if success:
                            stats['sizes_adjusted'] += 1
                        else:
                            failed_files.append(filepath)
        
        # Step 4: Apply permissions if specified
        if default_permissions is not None:
            for filepath in files:
                success, error = l1.change_file_permissions(filepath, default_permissions)
                if success:
                    stats['permissions_changed'] += 1
                else:
                    failed_files.append(filepath)
        
        # Step 5: Delete files if specified
        if deleted_count is not None:
            files_to_delete = min(deleted_count, len(files))
        elif deleted_ratio > 0:
            files_to_delete = int(len(files) * deleted_ratio)
        else:
            files_to_delete = 0
        
        if files_to_delete > 0:
            # Randomly select files to delete
            random.shuffle(files)
            # Use hard delete (unrecoverable) if deletion_mode is 'hard'
            forensic_recoverable = (deletion_mode == 'soft')
            for filepath in files[:files_to_delete]:
                success, error, _ = l1.delete_file(filepath, backup=False, forensic_recoverable=forensic_recoverable)
                if success:
                    stats['files_deleted'] += 1
                else:
                    failed_files.append(filepath)
        
        return True, stats, failed_files, ""
    
    except Exception as e:
        return False, {}, [], str(e)


def _list_files_by_pattern(
    base_directory: str,
    pattern: str = '*',
    recursive: bool = True
) -> List[str]:
    """
    List files matching pattern in directory.
    
    Args:
        base_directory: Root directory
        pattern: Glob pattern
        recursive: Search recursively
        
    Returns:
        List[str]: List of file paths
    """
    files = []
    
    if recursive:
        # Recursive search using os.walk
        for root, dirs, filenames in os.walk(base_directory):
            for filename in filenames:
                if _matches_pattern(filename, pattern):
                    files.append(os.path.join(root, filename))
    else:
        # Non-recursive search using glob
        search_pattern = os.path.join(base_directory, pattern)
        files = [f for f in glob.glob(search_pattern) if os.path.isfile(f)]
    
    return files


def _matches_pattern(filename: str, pattern: str) -> bool:
    """
    Check if filename matches glob pattern.
    
    Args:
        filename: Filename to check
        pattern: Glob pattern
        
    Returns:
        bool: True if matches
    """
    import fnmatch
    return fnmatch.fnmatch(filename, pattern)


# ============================================================================
# LAYER 2: BULK ENCRYPTION ORCHESTRATOR
# ============================================================================

def encrypt_files_bulk(
    files: List[str],
    encryption_key: bytes,
    encrypted_extension: str = 'WNCRY',
    keep_originals: bool = False
) -> Tuple[bool, List[str], List[Tuple[str, str]], str]:
    """
    Encrypt multiple files using AES-256-CBC.
    
    This orchestrator coordinates Layer 1 encryption primitives to encrypt
    a batch of files. It's the primary operation in ransomware simulation.
    
    Args:
        files: List of file paths to encrypt
        encryption_key: AES-256 key (32 bytes)
        encrypted_extension: Extension for encrypted files
        keep_originals: Keep original files (testing mode)
        
    Returns:
        Tuple[bool, List[str], List[Tuple[str, str]], str]:
            (success, encrypted_files, failed_files, error_message)
    """
    from . import layer1_primitives as l1
    
    try:
        encrypted_files = []
        failed_files = []
        
        for filepath in files:
            if not os.path.exists(filepath):
                failed_files.append((filepath, "File not found"))
                continue
            
            # Skip if already encrypted
            if filepath.endswith(f'.{encrypted_extension}'):
                continue
            
            # Call Layer 1 encryption primitive
            success, encrypted_path, error = l1.encrypt_file_aes256_cbc(
                filepath,
                encryption_key,
                encrypted_extension,
                keep_originals
            )
            
            if success:
                encrypted_files.append(encrypted_path)
            else:
                failed_files.append((filepath, error))
        
        return True, encrypted_files, failed_files, ""
    
    except Exception as e:
        return False, [], [], str(e)
