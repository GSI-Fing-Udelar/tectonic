"""
Filesystem Layer 3 - Common User Profile Orchestrator
======================================================

Author: Filesystem Forensics Team
Purpose: High-level user behavior simulation for filesystem analysis
Context: Layer 3 (Profiles) - Orchestrates Layer 2 and Layer 1 primitives

This module provides the highest level of abstraction for generating realistic
user filesystem profiles. It simulates complete user behavior patterns by
orchestrating multiple Layer 2 operations.

Architecture:
    Layer 3 (Profiles) - User behavior simulation [THIS MODULE]
        ↓ orchestrates
    Layer 2 (Orchestrators) - Bulk operations (generate_files_bulk, etc.)
        ↓ uses
    Layer 1 (Primitives) - Atomic operations (create_file, chmod, etc.)

Dependencies:
    - layer2_orchestrators: Bulk file generation, temporal distribution
    - layer1_primitives: File creation, permission changes
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
from typing import List, Dict, Tuple, Optional, Any
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
# USER PROFILE DEFINITIONS
# ============================================================================

# Profile: Personal - Typical home user with photos, music, documents
PROFILE_PERSONAL = {
    'name': 'Personal',
    'extensions': ['jpg', 'png', 'mp4', 'mp3', 'pdf', 'docx', 'txt'],
    'directories': ['/tmp/Photos', '/tmp/Music', '/tmp/Videos', '/tmp/Documents'],
    'file_count_range': (200, 500),
    'file_sizes': 'large',  # 1MB-50MB
    'naming_patterns': ['vacation_{date}', 'IMG_{n}', 'song_{faker_word}', 'document_{faker_name}'],
    'activity': 'sporadic',  # Many file accesses
    'description': 'Home user with personal media collection'
}

# Profile: Corporate - Office worker with business documents
PROFILE_CORPORATE = {
    'name': 'Corporate',
    'extensions': ['docx', 'xlsx', 'pdf', 'pptx', 'txt', 'csv'],
    'directories': ['/tmp/Projects', '/tmp/Reports', '/tmp/Budgets', '/tmp/Contracts'],
    'file_count_range': (100, 300),
    'file_sizes': 'medium',  # 10KB-5MB
    'naming_patterns': ['report_{date}', 'budget_{faker_company}', 'contract_{n}', '{faker_job}_{date}'],
    'activity': 'frequent',  # Regular updates
    'description': 'Corporate user with business documents'
}

# Profile: Developer - Programmer with code and project files
PROFILE_DEVELOPER = {
    'name': 'Developer',
    'extensions': ['py', 'js', 'html', 'css', 'json', 'txt', 'sh'],
    'directories': ['/tmp/projects', '/tmp/scripts', '/tmp/configs', '/tmp/logs'],
    'file_count_range': (300, 800),
    'file_sizes': 'small',  # 1KB-500KB
    'naming_patterns': ['{faker_word}.py', 'script_{n}.sh', 'config_{faker_word}.json', 'app_{n}.js'],
    'activity': 'very_frequent',  # Constant modifications
    'description': 'Software developer with code repositories'
}

# Profile: Designer - Graphic designer with images and project files
PROFILE_DESIGNER = {
    'name': 'Designer',
    'extensions': ['jpg', 'png', 'pdf', 'psd', 'ai', 'svg'],
    'directories': ['/tmp/Projects', '/tmp/Resources', '/tmp/Exports', '/tmp/Clients'],
    'file_count_range': (150, 400),
    'file_sizes': 'very_large',  # 5MB-100MB
    'naming_patterns': ['design_{faker_company}', 'mockup_{date}', 'logo_{n}', 'banner_{faker_word}'],
    'activity': 'moderate',
    'description': 'Graphic designer with large media files'
}

# Profile: Student - University student with academic documents
PROFILE_STUDENT = {
    'name': 'Student',
    'extensions': ['pdf', 'docx', 'pptx', 'txt', 'xlsx', 'jpg'],
    'directories': ['/tmp/Courses', '/tmp/Notes', '/tmp/Assignments', '/tmp/Bibliography'],
    'file_count_range': (80, 200),
    'file_sizes': 'medium',  # 10KB-5MB
    'naming_patterns': ['notes_{faker_word}', 'assignment_{n}', 'book_{faker_name}', 'class_{date}'],
    'activity': 'moderate',
    'description': 'University student with academic files'
}

# Profile: Server - File server with organized archives
PROFILE_SERVER = {
    'name': 'Server',
    'extensions': ['zip', 'tar.gz', 'log', 'backup', 'sql', 'txt'],
    'directories': ['/tmp/backups', '/tmp/logs', '/tmp/archives', '/tmp/databases'],
    'file_count_range': (50, 150),
    'file_sizes': 'very_large',  # 10MB-500MB
    'naming_patterns': ['backup_{date}', 'log_{date}_{time}', 'archive_{n}', 'db_dump_{date}'],
    'activity': 'scheduled',  # Periodic automated activity
    'description': 'Server with automated backup and logging'
}

# Available profiles registry
AVAILABLE_PROFILES = {
    'personal': PROFILE_PERSONAL,
    'corporate': PROFILE_CORPORATE,
    'developer': PROFILE_DEVELOPER,
    'designer': PROFILE_DESIGNER,
    'student': PROFILE_STUDENT,
    'server': PROFILE_SERVER
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_file_size_range(size_category: str) -> Tuple[str, str]:
    """
    Get file size range based on category.
    
    Args:
        size_category: Category (small, medium, large, very_large)
        
    Returns:
        Tuple[str, str]: (min_size, max_size) in human-readable format
    """
    size_ranges = {
        'small': ('1KB', '500KB'),
        'medium': ('10KB', '5MB'),
        'large': ('1MB', '50MB'),
        'very_large': ('5MB', '100MB')
    }
    return size_ranges.get(size_category, ('10KB', '1MB'))


def get_activity_temporal_params(activity_level: str) -> Dict[str, Any]:
    """
    Get temporal distribution parameters based on activity level.
    
    Args:
        activity_level: Activity level (sporadic, moderate, frequent, very_frequent, scheduled)
        
    Returns:
        Dict[str, Any]: Temporal distribution parameters
    """
    activity_params = {
        'sporadic': {
            'distribution_type': 'uniform',
            'distribution_params': {'offset_min': '0', 'offset_max': '30d'}
        },
        'moderate': {
            'distribution_type': 'uniform',
            'distribution_params': {'offset_min': '0', 'offset_max': '15d'}
        },
        'frequent': {
            'distribution_type': 'gaussian',
            'distribution_params': {'mean': '3d', 'stddev': '2d'}
        },
        'very_frequent': {
            'distribution_type': 'gaussian',
            'distribution_params': {'mean': '12h', 'stddev': '6h'}
        },
        'scheduled': {
            'distribution_type': 'uniform',
            'distribution_params': {'offset_min': '1d', 'offset_max': '30d'}
        }
    }
    return activity_params.get(activity_level, activity_params['moderate'])


# ============================================================================
# LAYER 3 PROFILE CLASS
# ============================================================================

class Layer3UserProfile:
    """
    Layer 3 User Profile Generator - High-level user behavior simulation.
    
    This class orchestrates Layer 2 and Layer 1 primitives to generate
    complete, realistic user filesystem profiles.
    
    Usage:
        >>> profile_gen = Layer3UserProfile()
        >>> stats = profile_gen.generate_profile('personal', base_dir='/tmp/user1')
        >>> print(f"Generated {stats['total_files']} files")
    """
    
    def __init__(self) -> None:
        """Initialize the Layer 3 profile generator."""
        self.profiles_available = list(AVAILABLE_PROFILES.keys())
    
    def generate_profile(
        self,
        profile_type: str,
        base_directory: str,
        file_count: Optional[int] = None,
        faker_seed: int = 42,
        verbose: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a complete user profile with realistic file structure.
        
        This is the main orchestration function that:
        1. Creates directory structure based on profile
        2. Generates files with appropriate distribution
        3. Applies temporal distribution (timestamps)
        4. Sets realistic permissions
        
        Args:
            profile_type: Profile name ('personal', 'corporate', 'developer', etc.)
            base_directory: Root directory for profile
            file_count: Override default file count
            faker_seed: Seed for reproducible generation
            verbose: Print progress information
            
        Returns:
            Dict[str, Any]: Statistics about generated profile
        """
        from . import layer2_orchestrators as l2
        from . import layer1_primitives as l1
        
        # Validate profile
        if profile_type not in AVAILABLE_PROFILES:
            raise ValueError(f"Unknown profile: {profile_type}. Available: {self.profiles_available}")
        
        profile = AVAILABLE_PROFILES[profile_type]
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"GENERATING USER PROFILE: {profile['name']}")
            print(f"{'='*70}")
            print(f"Description: {profile['description']}")
        
        # Step 1: Determine file count
        if file_count is None:
            min_count, max_count = profile['file_count_range']
            file_count = random.randint(min_count, max_count)
        
        if verbose:
            print(f"\nTarget files: {file_count}")
        
        # Step 2: Calculate file type distribution
        extensions = profile['extensions']
        distribution = {ext: 100.0 / len(extensions) for ext in extensions}
        
        if verbose:
            print(f"File types: {', '.join(extensions)}")
            print(f"Distribution: {len(extensions)} types equally distributed")
        
        # Step 3: Generate directory structure
        directories = profile['directories']
        for directory in directories:
            # Remove /tmp/ prefix correctly (not with lstrip which removes individual chars)
            if directory.startswith('/tmp/'):
                dir_relative = directory[5:]  # Remove '/tmp/' (5 characters)
            else:
                dir_relative = directory.lstrip('/')
            
            full_path = os.path.join(base_directory, dir_relative)
            os.makedirs(full_path, exist_ok=True)
            if verbose:
                print(f"Created directory: {full_path}")
        
        # Step 4: Generate files in each directory
        if verbose:
            print(f"\nGenerating {file_count} files...")
        
        all_created_files = []
        all_failed_files = []
        files_per_dir = file_count // len(directories)
        remaining_files = file_count % len(directories)
        
        for idx, directory in enumerate(directories):
            # Distribute files evenly, with remainder in last directory
            dir_file_count = files_per_dir + (remaining_files if idx == len(directories) - 1 else 0)
            
            # Select random name pattern
            name_pattern = random.choice(profile['naming_patterns'])
            
            # Generate files for this directory - remove /tmp/ prefix correctly
            if directory.startswith('/tmp/'):
                dir_relative = directory[5:]  # Remove '/tmp/' (5 characters)
            else:
                dir_relative = directory.lstrip('/')
            target_dir = os.path.join(base_directory, dir_relative)
            
            success, created, failed, error = l2.generate_files_bulk(
                count=dir_file_count,
                distribution=distribution,
                base_directory=target_dir,
                structure='flat',
                name_pattern=name_pattern,
                faker_seed=faker_seed + idx
            )
            
            if success:
                all_created_files.extend(created)
                all_failed_files.extend(failed)
                if verbose:
                    dir_name = directory.split('/')[-1]
                    print(f"  {dir_name}: {len(created)} files created")
            else:
                if verbose:
                    print(f"  ERROR in {directory}: {error}")
        
        # Step 5: Apply temporal distribution
        if all_created_files:
            if verbose:
                print(f"\nApplying temporal distribution ({profile['activity']} activity)...")
            
            temporal_params = get_activity_temporal_params(profile['activity'])
            base_timestamp = int(datetime.now().timestamp())
            
            success, modified_count, failed, error = l2.apply_temporal_distribution(
                files=all_created_files,
                base_timestamp=base_timestamp,
                distribution_type=temporal_params['distribution_type'],
                distribution_params=temporal_params['distribution_params'],
                seed=faker_seed
            )
            
            if verbose:
                if success:
                    print(f"  Timestamps applied: {modified_count} files")
                else:
                    print(f"  ERROR: {error}")
        
        # Step 6: Apply permissions
        if all_created_files:
            if verbose:
                print(f"\nApplying realistic permissions...")
            
            # Different permission patterns based on profile
            if profile_type in ['personal', 'student']:
                # More relaxed permissions for personal files
                permission_mode = '0644'
            elif profile_type in ['corporate', 'designer']:
                # Standard permissions for office files
                permission_mode = '0640'
            elif profile_type == 'developer':
                # Varied permissions (some executable)
                permission_mode = '0755'  # Scripts need execute
            else:
                # Server - restrictive permissions
                permission_mode = '0600'
            
            permissions_changed = 0
            for filepath in all_created_files:
                perm_int = int(permission_mode, 8)
                success, error = l1.change_file_permissions(filepath, perm_int)
                if success:
                    permissions_changed += 1
            
            if verbose:
                print(f"  Permissions set ({permission_mode}): {permissions_changed} files")
        
        # Step 7: Apply size constraints
        min_size, max_size = get_file_size_range(profile['file_sizes'])
        if verbose:
            print(f"\nFile size range: {min_size} - {max_size}")
        
        # Summary statistics
        stats = {
            'profile_type': profile_type,
            'profile_name': profile['name'],
            'base_directory': base_directory,
            'total_files': len(all_created_files),
            'failed_files': len(all_failed_files),
            'directories_created': len(directories),
            'file_types': extensions,
            'file_size_category': profile['file_sizes'],
            'activity_level': profile['activity']
        }
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"PROFILE GENERATION COMPLETE")
            print(f"{'='*70}")
            print(f"Total files created: {stats['total_files']}")
            print(f"Failed: {stats['failed_files']}")
            print(f"Directories: {stats['directories_created']}")
            print(f"{'='*70}\n")
        
        return stats
    
    def generate_multiple_profiles(
        self,
        profiles: List[Dict[str, Any]],
        base_directory: str,
        faker_seed: int = 42,
        verbose: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple user profiles in parallel.
        
        Useful for simulating multi-user environments or creating
        diverse filesystem scenarios.
        
        Args:
            profiles: List of profile configurations
                     [{'type': 'personal', 'user': 'user1', ...}, ...]
            base_directory: Root directory for all profiles
            faker_seed: Base seed for reproducible generation
            verbose: Print progress information
            
        Returns:
            List[Dict[str, Any]]: Statistics for each profile
        """
        if verbose:
            print(f"\n{'='*70}")
            print(f"GENERATING MULTIPLE USER PROFILES")
            print(f"{'='*70}")
            print(f"Profiles to generate: {len(profiles)}")
        
        all_stats = []
        
        for idx, profile_config in enumerate(profiles):
            profile_type = profile_config['type']
            user_name = profile_config.get('user', f'user{idx+1}')
            
            # Create user-specific directory
            user_dir = os.path.join(base_directory, user_name)
            os.makedirs(user_dir, exist_ok=True)
            
            if verbose:
                print(f"\n--- Profile {idx+1}/{len(profiles)}: {user_name} ({profile_type}) ---")
            
            # Generate profile
            stats = self.generate_profile(
                profile_type=profile_type,
                base_directory=user_dir,
                file_count=profile_config.get('file_count'),
                faker_seed=faker_seed + idx * 1000,
                verbose=False  # Suppress per-profile verbosity
            )
            
            stats['user_name'] = user_name
            all_stats.append(stats)
            
            if verbose:
                print(f"  ✓ {stats['total_files']} files generated for {user_name}")
        
        if verbose:
            print(f"\n{'='*70}")
            print(f"ALL PROFILES COMPLETE")
            print(f"{'='*70}")
            total_files = sum(s['total_files'] for s in all_stats)
            print(f"Total files across all profiles: {total_files}")
            print(f"{'='*70}\n")
        
        return all_stats


# ============================================================================
# DEMONSTRATION
# ============================================================================

def main():
    """Demonstration of Layer 3 user profile generation."""
    print("="*70)
    print("LAYER 3 USER PROFILES - DEMONSTRATION")
    print("="*70)
    
    generator = Layer3UserProfile()
    
    # Demo 1: Single personal profile
    print("\nDEMO 1: Personal User Profile")
    stats1 = generator.generate_profile(
        profile_type='personal',
        base_directory='/tmp/demo_profiles/user_personal',
        faker_seed=42,
        verbose=True
    )
    
    # Demo 2: Multiple profiles (simulated office environment)
    print("\n\nDEMO 2: Office Environment (3 users)")
    profiles_config = [
        {'type': 'corporate', 'user': 'manager'},
        {'type': 'developer', 'user': 'dev_team'},
        {'type': 'designer', 'user': 'marketing'}
    ]
    
    stats_multi = generator.generate_multiple_profiles(
        profiles=profiles_config,
        base_directory='/tmp/demo_profiles/office',
        faker_seed=100,
        verbose=True
    )
    
    print("\n✅ Demonstration complete!")
    print("\nAnalyze generated files:")
    print("  tree /tmp/demo_profiles")
    print("  ls -lh /tmp/demo_profiles/user_personal/tmp/Fotos")


if __name__ == '__main__':
    main()
