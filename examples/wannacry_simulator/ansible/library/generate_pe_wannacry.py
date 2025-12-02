#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Ansible Module: generate_pe_wannacry
Generate simulated PE (Portable Executable) files with WannaCry signatures
detectable by ReversingLabs YARA rules.
"""

from ansible.module_utils.basic import AnsibleModule
import os
import struct
import random

DOCUMENTATION = '''
---
module: generate_pe_wannacry
short_description: Generate PE files with WannaCry malware signatures
description:
    - Creates Windows PE executable files with embedded WannaCry patterns
    - Patterns match those searched by ReversingLabs YARA rules
    - Files are detectable by professional malware analysis tools
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

# WannaCry malware patterns from ReversingLabs YARA rules
# These are simplified representations that will trigger YARA detection
WANNACRY_PATTERNS = {
    'main_1': bytes([
        0xA0, 0x00, 0x40, 0x00, 0x00, 0x56, 0x57, 0x6A, 0x00, 0x88, 0x85, 0x00, 0xFC, 0xFF, 0xFF, 0x59,
        0x33, 0xC0, 0x8D, 0xBD, 0x00, 0xFC, 0xFF, 0xFF, 0xF3, 0xAB, 0x66, 0xAB, 0xAA, 0x8D, 0x85, 0x00,
        0xFC, 0xFF, 0xFF, 0x68, 0x00, 0x50, 0x40, 0x00, 0x50, 0x53, 0xFF, 0x15, 0x00, 0x30, 0x40, 0x00
    ]),
    'main_2': bytes([
        0x68, 0x00, 0x50, 0x40, 0x00, 0x33, 0xDB, 0x50, 0x53, 0xFF, 0x15, 0x00, 0x30, 0x40, 0x00, 0x68,
        0x00, 0x60, 0x40, 0x00, 0xE8, 0x00, 0x10, 0x00, 0x00, 0x59, 0xFF, 0x15, 0x00, 0x31, 0x40, 0x00,
        0x83, 0x38, 0x00, 0x75, 0x10, 0x68, 0x00, 0x61, 0x40, 0x00, 0xFF, 0x15, 0x00, 0x32, 0x40, 0x00
    ]),
    'main_3': bytes([
        0x83, 0xEC, 0x20, 0x56, 0x57, 0xB9, 0x40, 0x00, 0x00, 0x00, 0xBE, 0x00, 0x50, 0x40, 0x00, 0x8D,
        0x7C, 0x24, 0x08, 0x33, 0xC0, 0xF3, 0xA5, 0xA4, 0x89, 0x44, 0x24, 0x08, 0x89, 0x44, 0x24, 0x0C,
        0x89, 0x44, 0x24, 0x10, 0x89, 0x44, 0x24, 0x14, 0x89, 0x44, 0x24, 0x18, 0x66, 0x89, 0x44, 0x24
    ]),
    'start_service_3': bytes([
        0x83, 0xEC, 0x10, 0x68, 0x00, 0x70, 0x40, 0x00, 0x68, 0x00, 0x71, 0x40, 0x00, 0x6A, 0x00, 0xFF,
        0x15, 0x00, 0x40, 0x40, 0x00, 0xFF, 0x15, 0x00, 0x41, 0x40, 0x00, 0x83, 0x38, 0x00, 0x7D, 0x10,
        0xE8, 0x00, 0x20, 0x00, 0x00, 0x83, 0xC4, 0x10, 0xC3, 0x57, 0x68, 0x00, 0x72, 0x40, 0x00, 0x6A
    ]),
    'main_4': bytes([
        0x83, 0xEC, 0x10, 0x57, 0x68, 0x00, 0x80, 0x40, 0x00, 0x6A, 0x00, 0x6A, 0x00, 0xFF, 0x15, 0x00,
        0x50, 0x40, 0x00, 0x8B, 0xF8, 0x85, 0xFF, 0x74, 0x30, 0x53, 0x56, 0x68, 0x00, 0x81, 0x40, 0x00,
        0x68, 0x00, 0x82, 0x40, 0x00, 0x57, 0xFF, 0x15, 0x00, 0x51, 0x40, 0x00, 0x8B, 0x1D, 0x00, 0x52
    ]),
    'main_5': bytes([
        0x68, 0x00, 0x90, 0x40, 0x00, 0x50, 0x53, 0xFF, 0x15, 0x00, 0x60, 0x40, 0x00, 0x8B, 0x35, 0x00,
        0x61, 0x40, 0x00, 0x8D, 0x85, 0x00, 0xFC, 0xFF, 0xFF, 0x6A, 0x00, 0x50, 0xFF, 0xD6, 0x59, 0x85,
        0xC0, 0x59, 0x74, 0x20, 0x8D, 0x85, 0x00, 0xFD, 0xFF, 0xFF, 0x6A, 0x00, 0x50, 0xFF, 0xD6, 0x59
    ]),
    'main_6': bytes([
        0xFF, 0x74, 0x24, 0x04, 0xFF, 0x74, 0x24, 0x08, 0xFF, 0x74, 0x24, 0x0C, 0xFF, 0x74, 0x24, 0x10,
        0xE8, 0x00, 0x20, 0x00, 0x00, 0xC2, 0x10, 0x00
    ])
}


def create_dos_header():
    """
    Create DOS header (first 64 bytes of PE file)
    MZ signature + DOS stub
    """
    dos_header = bytearray(64)
    dos_header[0:2] = b'MZ'  # DOS signature
    dos_header[60:64] = struct.pack('<I', 128)  # PE header offset at 0x80
    return bytes(dos_header)


def create_pe_signature():
    """
    Create PE signature
    """
    return b'PE\x00\x00'


def create_coff_header():
    """
    Create COFF header (20 bytes)
    """
    coff = struct.pack(
        '<HHIIIHH',
        0x014C,   # Machine (Intel 386)
        2,        # NumberOfSections
        0,        # TimeDateStamp
        0,        # PointerToSymbolTable
        0,        # NumberOfSymbols
        224,      # SizeOfOptionalHeader
        0x0102    # Characteristics (executable, 32-bit)
    )
    return coff


def create_optional_header():
    """
    Create Optional Header (224 bytes for PE32)
    """
    optional = bytearray(224)
    optional[0:2] = struct.pack('<H', 0x010B)  # Magic (PE32)
    optional[16:20] = struct.pack('<I', 0x1000)  # SizeOfCode
    optional[20:24] = struct.pack('<I', 0x1000)  # SizeOfInitializedData
    optional[24:28] = struct.pack('<I', 0x400000)  # ImageBase
    optional[32:36] = struct.pack('<I', 0x1000)  # SectionAlignment
    optional[36:40] = struct.pack('<I', 0x200)   # FileAlignment
    optional[56:60] = struct.pack('<I', 0x3000)  # SizeOfImage
    optional[60:64] = struct.pack('<I', 0x400)   # SizeOfHeaders
    optional[92:94] = struct.pack('<H', 3)       # Subsystem (Console)
    return bytes(optional)


def create_section_header(name, virtual_size, virtual_address, raw_size, raw_offset, characteristics):
    """
    Create Section Header (40 bytes)
    """
    header = bytearray(40)
    header[0:8] = name.ljust(8, b'\x00')[:8]
    header[8:12] = struct.pack('<I', virtual_size)
    header[12:16] = struct.pack('<I', virtual_address)
    header[16:20] = struct.pack('<I', raw_size)
    header[20:24] = struct.pack('<I', raw_offset)
    header[36:40] = struct.pack('<I', characteristics)
    return bytes(header)


def generate_pe_file(filepath, patterns_to_include, seed):
    """
    Generate a complete PE file with WannaCry patterns
    """
    random.seed(seed)
    
    # Build PE file components
    dos_header = create_dos_header()
    dos_stub = b'\x0e\x1f\xba\x0e\x00\xb4\x09\xcd\x21\xb8\x01\x4c\xcd\x21' * 4  # 56 bytes
    
    pe_signature = create_pe_signature()
    coff_header = create_coff_header()
    optional_header = create_optional_header()
    
    # Section headers
    text_section = create_section_header(
        b'.text', 0x1000, 0x1000, 0x1000, 0x400,
        0x60000020  # CODE | EXECUTE | READ
    )
    data_section = create_section_header(
        b'.data', 0x1000, 0x2000, 0x1000, 0x1400,
        0xC0000040  # INITIALIZED_DATA | READ | WRITE
    )
    
    # Headers
    headers = dos_header + dos_stub + b'\x00' * 8  # Padding to 0x80
    headers += pe_signature + coff_header + optional_header
    headers += text_section + data_section
    
    # Pad headers to FileAlignment (0x400)
    headers = headers.ljust(0x400, b'\x00')
    
    # Create .text section (code) with WannaCry patterns
    text_data = bytearray(0x1000)
    offset = 0
    
    for pattern_name in patterns_to_include:
        if pattern_name in WANNACRY_PATTERNS:
            pattern = WANNACRY_PATTERNS[pattern_name]
            # Insert pattern at random offset
            insert_offset = random.randint(offset, min(offset + 200, 0x1000 - len(pattern)))
            text_data[insert_offset:insert_offset + len(pattern)] = pattern
            offset = insert_offset + len(pattern) + random.randint(50, 100)
    
    # Fill remaining space with random x86-like instructions
    for i in range(0, 0x1000, 4):
        if text_data[i:i+4] == b'\x00\x00\x00\x00':
            text_data[i:i+4] = bytes([
                random.choice([0x55, 0x8B, 0x89, 0x83, 0xFF, 0x33, 0x50, 0x51]),
                random.randint(0, 255),
                random.randint(0, 255),
                random.choice([0xC3, 0x00, 0x90, 0xEB])
            ])
    
    # Create .data section
    data_section_content = bytearray(0x1000)
    # Add some string data
    strings = [
        b"WANNACRY\x00",
        b"mssecsvc.exe\x00",
        b"tasksche.exe\x00",
        b"C:\\Windows\\System32\\\x00",
        b"icacls . /grant Everyone:F /T /C /Q\x00"
    ]
    data_offset = 0
    for string in strings:
        if data_offset + len(string) < 0x1000:
            data_section_content[data_offset:data_offset+len(string)] = string
            data_offset += len(string) + random.randint(10, 50)
    
    # Assemble final PE file
    pe_file = headers + bytes(text_data) + bytes(data_section_content)
    
    # Write to file
    with open(filepath, 'wb') as f:
        f.write(pe_file)
    
    return len(pe_file)


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
    
    # Ensure target directory exists
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, mode=0o755)
    
    generated_files = []
    total_size = 0
    
    try:
        for idx, exe_name in enumerate(executable_names):
            filepath = os.path.join(target_dir, exe_name)
            
            # Use different seed for each file
            file_seed = seed + idx
            
            # Generate PE file
            file_size = generate_pe_file(filepath, include_patterns, file_seed)
            
            # Set executable permissions
            os.chmod(filepath, 0o755)
            
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
