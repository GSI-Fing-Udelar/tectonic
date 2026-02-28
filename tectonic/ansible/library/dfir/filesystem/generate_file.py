#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_file

short_description: Generate a single file by type (Layer 1)

description:
  - Creates a single file using appropriate Layer 1 primitive
  - Routes to specific primitive based on file extension
  - Supports text, PDF, images, Office documents, archives, executables
  - Atomic operation for single file creation
  
version_added: "2.0.0"

options:
  path:
    description: Full path where the file will be created
    required: true
    type: str
  
  name:
    description:
      - Base filename (optional, can be derived from path)
    required: false
    type: str
    default: null
    
  extension:
    description:
      - File type extension (e.g., txt, pdf, jpg, docx)
      - Determines which Layer 1 primitive to call
    required: true
    type: str
    choices: [txt, pdf, jpg, png, docx, xlsx, zip, tar, tar.gz, sh, py, exe]
    
  content:
    description:
      - Content for text-based files
      - If not provided, Faker generates realistic content
    required: false
    type: str
    default: null
    
  size:
    description:
      - Target file size (e.g., "10KB", "2MB")
      - Used for text and PDF files
    required: false
    type: str
    default: null
    
  modification_date:
    description:
      - Modification timestamp (format "YYYY-MM-DD HH:MM:SS")
      - If not provided, uses current time
    required: false
    type: str
    default: null
    
  permissions:
    description:
      - File permissions in octal format as string (e.g., "0644", "0755")
      - Applied after file creation
    required: false
    type: str
    default: null
    
  seed:
    description: Random seed for reproducible content generation
    required: false
    type: int
    default: 42
    
  rows:
    description: Number of rows for XLSX files
    required: false
    type: int
    default: 10
    
  cols:
    description: Number of columns for XLSX files
    required: false
    type: int
    default: 5

notes:
  - Uses Layer 1 primitives from module_utils.layer1_primitives
  - For bulk file generation, use generate_files_bulk module
  - Supported extensions txt, pdf, jpg, png, docx, xlsx, zip, tar, tar.gz, sh, py
  - Archives (zip, tar) contain randomly generated dummy files

author:
  - Filesystem Forensics Team
'''

EXAMPLES = r'''
# Generate text file with custom content
- name: Create text file
  generate_file:
    path: /tmp/readme.txt
    extension: txt
    content: "This is a test file\\nMultiple lines\\nSupported"

# Generate PDF with specific size
- name: Create large PDF
  generate_file:
    path: /tmp/document.pdf
    extension: pdf
    size: "5MB"
    seed: 12345

# Generate image file
- name: Create JPEG image
  generate_file:
    path: /tmp/photo.jpg
    extension: jpg
    size: "2MB"

# Generate Office document
- name: Create Word document
  generate_file:
    path: /tmp/report.docx
    extension: docx
    seed: 42

# Generate Excel with custom dimensions
- name: Create spreadsheet
  generate_file:
    path: /tmp/data.xlsx
    extension: xlsx
    rows: 50
    cols: 10

# Generate compressed archive
- name: Create ZIP file
  generate_file:
    path: /tmp/backup.zip
    extension: zip

# Generate executable script
- name: Create shell script
  generate_file:
    path: /tmp/script.sh
    extension: sh
'''

RETURN = r'''
changed:
  description: Whether the file was created
  type: bool
  returned: always
  sample: true

path:
  description: Path of the created file
  type: str
  returned: always
  sample: "/tmp/document.pdf"

created:
  description: Whether the file was successfully created
  type: bool
  returned: always
  sample: true

extension:
  description: File extension/type created
  type: str
  returned: always
  sample: "pdf"

size_kb:
  description: File size in kilobytes
  type: float
  returned: always
  sample: 245.3
'''

from ansible.module_utils.basic import AnsibleModule
import os


def main():
    """
    Main execution function for generate_file module.
    
    This module acts as an Ansible interface to Layer 1 primitives
    from module_utils.layer1_primitives. It routes to the appropriate
    primitive based on the file extension.
    
    Workflow:
        1. Parse and validate module arguments
        2. Import Layer 1 primitives
        3. Route to appropriate primitive based on extension
        4. Call primitive to create file
        5. Return results in Ansible format
    """
    
    # Define module argument specification
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type='str', required=True),
            name=dict(type='str', required=False, default=None),
            extension=dict(
                type='str',
                required=True,
                choices=['txt', 'pdf', 'jpg', 'png', 'docx', 'xlsx', 'zip', 'tar', 'tar.gz', 'sh', 'py', 'exe']
            ),
            content=dict(type='str', required=False, default=None),
            size=dict(type='str', required=False, default=None),
            modification_date=dict(type='str', required=False, default=None),
            permissions=dict(type='str', required=False, default=None),
            seed=dict(type='int', required=False, default=42),
            rows=dict(type='int', required=False, default=10),
            cols=dict(type='int', required=False, default=5)
        ),
        supports_check_mode=True
    )
    
    # Extract parameters
    filepath = module.params['path']
    name = module.params['name']
    extension = module.params['extension']
    content = module.params['content']
    size = module.params['size']
    modification_date = module.params['modification_date']
    permissions = module.params['permissions']
    seed = module.params['seed']
    rows = module.params['rows']
    cols = module.params['cols']
    
    # Check mode - don't actually create
    if module.check_mode:
        module.exit_json(changed=True, path=filepath, created=False, extension=extension)
    
    # Import Layer 1 primitives
    try:
        from ansible.module_utils.dfir.filesystem.first_layer import layer1_primitives as l1
    except ImportError as e:
        module.fail_json(msg=f"Failed to import layer1_primitives: {str(e)}")
    
    # Route to appropriate Layer 1 primitive based on extension
    try:
        if extension == 'txt':
            # Create text file
            success, error = l1.create_text_file(
                filepath=filepath,
                content=content,
                size=size,
                seed=seed
            )
            
        elif extension == 'pdf':
            # Create PDF file
            success, error = l1.create_pdf_file(
                filepath=filepath,
                content=content,
                size=size,
                seed=seed
            )
            
        elif extension in ['jpg', 'png']:
            # Create image file
            success, error = l1.create_image_file(
                filepath=filepath,
                extension=extension,
                size=size,
                seed=seed
            )
            
        elif extension == 'docx':
            # Create Word document
            success, error = l1.create_docx_file(
                filepath=filepath,
                content=content,
                seed=seed
            )
            
        elif extension == 'xlsx':
            # Create Excel spreadsheet
            success, error = l1.create_xlsx_file(
                filepath=filepath,
                rows=rows,
                cols=cols,
                seed=seed
            )
            
        elif extension in ['zip', 'tar', 'tar.gz']:
            # Create compressed archive
            success, error = l1.create_compressed_file(
                filepath=filepath,
                extension=extension,
                seed=seed
            )
            
        elif extension in ['sh', 'py']:
            # Create executable script
            success, error = l1.create_executable_file(
                filepath=filepath,
                extension=extension
            )
            
        else:
            module.fail_json(msg=f"Unsupported extension: {extension}")
        
        # Check primitive result
        if not success:
            module.fail_json(msg=f"Failed to create {extension} file: {error}")
        
        # Apply modification date if provided
        if modification_date:
            try:
                from datetime import datetime
                dt = datetime.strptime(modification_date, "%Y-%m-%d %H:%M:%S")
                timestamp = int(dt.timestamp())
                
                success_ts, error_ts = l1.apply_file_timestamps(
                    filepath=filepath,
                    mtime=timestamp,
                    atime=timestamp
                )
                if not success_ts:
                    module.warn(f"Failed to apply modification date: {error_ts}")
            except Exception as e:
                module.warn(f"Failed to parse modification_date: {str(e)}")
        
        # Apply permissions if provided
        if permissions:
            try:
                permissions_int = int(permissions, 8)
                success_perms, error_perms = l1.change_file_permissions(
                    filepath=filepath,
                    mode=permissions_int
                )
                if not success_perms:
                    module.warn(f"Failed to apply permissions: {error_perms}")
            except ValueError:
                module.warn(f"Invalid permissions format: {permissions}")
        
        # Calculate file size
        file_size_bytes = os.path.getsize(filepath)
        file_size_kb = round(file_size_bytes / 1024, 1)
        
        # Return success result
        module.exit_json(
            changed=True,
            path=filepath,
            created=True,
            extension=extension,
            size_kb=file_size_kb,
            msg=f"Successfully created {extension} file at {filepath}"
        )
        
    except Exception as e:
        module.fail_json(msg=f"Unexpected error during file creation: {str(e)}")


if __name__ == '__main__':
    main()
