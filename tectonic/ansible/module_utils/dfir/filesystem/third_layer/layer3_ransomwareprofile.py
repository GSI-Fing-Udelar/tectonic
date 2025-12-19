"""
Filesystem Layer 3 - Ransomware Profile Orchestrator
=====================================================

Author: Filesystem Forensics Team
Purpose: High-level ransomware behavior simulation for filesystem analysis
Context: Layer 3 (Profiles) - Orchestrates Layer 2 and Layer 1 primitives

This module provides ransomware-specific profiles that simulate complete attack
scenarios including file generation, encryption, deletion, and timeline manipulation.
It orchestrates multiple Layer 2 operations to replicate ransomware behavior patterns.

Architecture:
    Layer 3 (Profiles) - Ransomware behavior simulation [THIS MODULE]
        ↓ orchestrates
    Layer 2 (Orchestrators) - Bulk operations (generate_files_bulk, encrypt_files_bulk, etc.)
        ↓ uses
    Layer 1 (Primitives) - Atomic operations (create_file, encrypt_file, chmod, etc.)

Supported Ransomware Families:
    - WannaCry: AES-256-CBC encryption, .WNCRY extension
    - Custom: User-defined parameters based on WannaCry

Dependencies:
    - layer2_orchestrators: Bulk file operations, temporal distribution
    - layer1_primitives: File creation, encryption, permission changes
    - cryptography: AES encryption (for real encryption simulation)
    - faker: Realistic data generation
    - typing: Type hints

Type Safety:
    All functions use Python 3.8+ type hints (PEP 484)
"""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import random
import sys
import subprocess
from typing import List, Dict, Tuple, Optional, Any, Union
from datetime import datetime, timedelta

try:
    from faker import Faker
    FAKER_AVAILABLE = True
except ImportError:
    # Auto-install faker if not available
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'faker'])
        from faker import Faker
        FAKER_AVAILABLE = True
    except Exception:
        FAKER_AVAILABLE = False


# ============================================================================
# RANSOMWARE PROFILE DEFINITIONS
# ============================================================================

# Profile: WannaCry
PROFILE_WANNACRY = {
    'name': 'WannaCry',
    'description': 'WannaCry ransomware behavior pattern (May 2017)',
    
    # File generation parameters
    'file_count': 150,
    'file_distribution': {
        'docx': 30,
        'pdf': 25,
        'jpg': 20,
        'xlsx': 15,
        'txt': 10
    },
    'directory_structure': 'tree',
    'tree_depth': 2,
    'subdirs_per_level': 3,
    'file_naming_pattern': 'document_{n}_{faker_company}',
    
    # Encryption parameters
    'encryption_algorithm': 'AES-256-CBC',
    'encrypted_extension': 'WNCRY',
    'keep_original_files': False,
    'encryption_key': None,  # Random if None
    
    # Post-encryption behavior
    'deletion_ratio': 12,  # 12% of files deleted (logs, backups)
    'deletion_mode': 'hard',  # 'hard' = unrecoverable, 'soft' = forensic recoverable
    'set_readonly': True,
    'readonly_permissions': '0444',
    
    # Ransom note
    'create_ransom_note': True,
    'ransom_note_filename': '@Please_Read_Me@.txt',
    'ransom_note_content': """=====================================================
          WANNACRY RANSOMWARE
=====================================================

Ooops, your important files are encrypted.

If you see this text, then your files are no longer
accessible, because they have been encrypted.

What happened to my computer?
Your important files are encrypted. Many of your documents,
photos, videos, databases and other files are no longer
accessible because they have been encrypted.

Can I recover my files?
Sure. We guarantee that you can recover all your files safely
and easily. But you have not so enough time.

You can decrypt some of your files for free. Try now by
clicking <Decrypt>.

But if you want to decrypt all your files, you need to pay.
You only have 3 days to submit the payment. After that the
price will be doubled.

Also, if you don't pay in 7 days, you won't be able to
recover your files forever.

We will have free events for users who are so poor that they
couldn't pay in 6 months.

How do I pay?
Payment is accepted in Bitcoin only.

Contact us:
- Email: wowsmith123456@posteo.net
- Bitcoin Address: 115p7UMMngoj1pMvkpHijcRdfJNXj6LrLn

Price: $300 USD (0.1 BTC)

=====================================================
      DO NOT RENAME OR MODIFY FILES
      OR YOU WILL LOSE THEM FOREVER
=====================================================
""",
    'ransom_note_in_subdirs': True,
    
    # PE Executables (WannaCry malware binaries)
    'generate_pe_executables': True,
    'pe_executable_names': [
        'mssecsvc.exe',
        'tasksche.exe', 
        '@WanaDecryptor@.exe',
        'wannacry.exe',
        'wcry.exe'
    ],
    'pe_patterns': ['main_1', 'main_2', 'main_3', 'start_service_3'],
    'pe_target_subdirectory': '',  # Empty = root directory
    
    # Timeline parameters
    'original_files_timerange': {
        'creation_distribution': {
            'type': 'uniform',
            'params': {'offset_min': '0', 'offset_max': '3d'}
        },
        'modification_distribution': {
            'type': 'gaussian',
            'params': {'mean': '2d', 'stddev': '12h'}
        },
        'access_distribution': {
            'type': 'exponential',
            'params': {'mean': '3d'}
        }
    },
    'infection_window': {
        'start': '0',      # Infection starts now
        'end': '4h',       # 4 hours duration
        'distribution': {
            'type': 'uniform',
            'params': {'offset_min': '0', 'offset_max': '4h'}
        },
        'modification_delay': {
            'type': 'gaussian',
            'params': {'mean': '2m', 'stddev': '30s'}
        }
    },
    
    # Reproducibility
    'faker_seed': 42,
    'force_rerun': False
}




# ============================================================================
# PROFILE REGISTRY
# ============================================================================

RANSOMWARE_PROFILES = {
    'wannacry': PROFILE_WANNACRY
}


def get_ransomware_profile(profile_name: str) -> Dict[str, Any]:
    """
    Get a ransomware profile by name.
    
    Args:
        profile_name: Name of the ransomware profile
        
    Returns:
        Dict containing profile configuration
        
    Raises:
        KeyError: If profile not found
    """
    profile_name_lower = profile_name.lower()
    if profile_name_lower not in RANSOMWARE_PROFILES:
        available = ', '.join(RANSOMWARE_PROFILES.keys())
        raise KeyError(
            f"Ransomware profile '{profile_name}' not found. "
            f"Available profiles: {available}"
        )
    return RANSOMWARE_PROFILES[profile_name_lower].copy()


def list_ransomware_profiles() -> List[str]:
    """
    Get list of available ransomware profiles.
    
    Returns:
        List of profile names
    """
    return list(RANSOMWARE_PROFILES.keys())


def create_custom_ransomware_profile(
    name: str,
    base_profile: Optional[str] = None,
    **overrides
) -> Dict[str, Any]:
    """
    Create a custom ransomware profile.
    
    Args:
        name: Name for the custom profile
        base_profile: Name of profile to use as base (optional)
        **overrides: Parameters to override from base profile
        
    Returns:
        Dict containing custom profile configuration
        
    Example:
        >>> profile = create_custom_ransomware_profile(
        ...     name='CustomWannaCry',
        ...     base_profile='wannacry',
        ...     file_count=500,
        ...     deletion_ratio=25
        ... )
    """
    if base_profile:
        profile = get_ransomware_profile(base_profile)
    else:
        profile = PROFILE_WANNACRY.copy()
    
    profile['name'] = name
    profile.update(overrides)
    
    return profile


# ============================================================================
# PROFILE VALIDATION
# ============================================================================

def validate_ransomware_profile(profile: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a ransomware profile configuration.
    
    Args:
        profile: Profile configuration dictionary
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Required fields
    required_fields = [
        'name', 'file_count', 'file_distribution', 'directory_structure',
        'encryption_algorithm', 'encrypted_extension'
    ]
    
    for field in required_fields:
        if field not in profile:
            errors.append(f"Missing required field: {field}")
    
    # Validate file_count
    if 'file_count' in profile:
        if not isinstance(profile['file_count'], int) or profile['file_count'] <= 0:
            errors.append("file_count must be a positive integer")
    
    # Validate file_distribution
    if 'file_distribution' in profile:
        if not isinstance(profile['file_distribution'], dict):
            errors.append("file_distribution must be a dictionary")
        elif not profile['file_distribution']:
            errors.append("file_distribution cannot be empty")
    
    # Validate deletion_ratio
    if 'deletion_ratio' in profile:
        ratio = profile['deletion_ratio']
        if not isinstance(ratio, (int, float)) or not (0 <= ratio <= 100):
            errors.append("deletion_ratio must be between 0 and 100")
    
    # Validate directory_structure
    if 'directory_structure' in profile:
        valid_structures = ['flat', 'tree']
        if profile['directory_structure'] not in valid_structures:
            errors.append(f"directory_structure must be one of: {valid_structures}")
    
    return len(errors) == 0, errors


# ============================================================================
# PROFILE INFO
# ============================================================================

def get_profile_info(profile_name: str) -> str:
    """
    Get human-readable information about a ransomware profile.
    
    Args:
        profile_name: Name of the ransomware profile
        
    Returns:
        Formatted string with profile information
    """
    try:
        profile = get_ransomware_profile(profile_name)
    except KeyError as e:
        return str(e)
    
    info = f"""
Ransomware Profile: {profile['name']}
{'-' * 50}
Description: {profile.get('description', 'N/A')}

File Generation:
  - Total files: {profile['file_count']}
  - Distribution: {profile['file_distribution']}
  - Structure: {profile['directory_structure']}
  - Naming pattern: {profile['file_naming_pattern']}

Encryption:
  - Algorithm: {profile['encryption_algorithm']}
  - Extension: .{profile['encrypted_extension']}
  - Keep originals: {profile['keep_original_files']}

Post-Encryption:
  - Deletion ratio: {profile['deletion_ratio']}%
  - Set read-only: {profile['set_readonly']}
  - Ransom note: {profile['create_ransom_note']}
  - Note filename: {profile.get('ransom_note_filename', 'N/A')}

Infection Window:
  - Start: {profile['infection_window']['start']}
  - End: {profile['infection_window']['end']}
  - Distribution: {profile['infection_window']['distribution']['type']}

Reproducibility:
  - Faker seed: {profile['faker_seed']}
"""
    return info
