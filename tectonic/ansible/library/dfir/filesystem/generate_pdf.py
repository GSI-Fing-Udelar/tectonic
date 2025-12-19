#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2025, Rodrigo
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_pdf

short_description: Generates PDF with author data and random content using Faker

description:
  - This module runs a Python script that generates a PDF
  - Allows to manually specify the author
  - The rest of the parameters (title, content, pages) are generated with Faker
  - Uses Pandoc for PDF generation (requires pandoc installed on the system)

version_added: "1.0.0"

options:
  author:
    description:
      - Name of the PDF author
      - This parameter is REQUIRED and controlled by the user
    required: true
    type: str
  
  output_path:
    description:
      - Path where the generated PDF will be saved
      - By default it is saved in /tmp/generated_document.pdf
    required: false
    type: str
    default: /tmp/generated_document.pdf
  
  num_pages:
    description:
      - Number of pages to generate (Faker generates content for each one)
      - By default generates between 1-5 random pages
    required: false
    type: int
    default: 0
  
  title:
    description:
      - Document title (if not specified, Faker generates one)
    required: false
    type: str
    default: ""
  
  faker_locale:
    description:
      - Locale for Faker (es_ES, en_US, fr_FR, etc.)
    required: false
    type: str
    default: es_ES

author:
  - Rodrigo (@rodrigo)

requirements:
  - python >= 3.8
  - pandoc (system)
  - faker

notes:
  - Make sure you have pandoc installed (apt install pandoc / brew install pandoc)
  - Faker must be installed (pip install faker)
  - An intermediate Markdown file will be generated that Pandoc will convert to PDF

seealso:
  - name: Pandoc Documentation
    description: Pandoc documentation for document conversion
    link: https://pandoc.org/

examples:
  - name: Generate PDF with specific author (rest random)
    generate_pdf:
      author: "John Doe"
  
  - name: Generate PDF with author and custom path
    generate_pdf:
      author: "Mary Smith"
      output_path: "/home/user/documents/report.pdf"
  
  - name: PDF with author, title and number of pages
    generate_pdf:
      author: "Rodrigo López"
      title: "Annual Report 2025"
      num_pages: 10
      output_path: "/tmp/report_2025.pdf"
  
  - name: PDF in English
    generate_pdf:
      author: "John Doe"
      faker_locale: "en_US"
      num_pages: 5

return:
  pdf_path:
    description: Full path of the generated PDF
    returned: always
    type: str
    sample: /tmp/generated_document.pdf
  
  author:
    description: PDF author
    returned: always
    type: str
    sample: John Doe
  
  title:
    description: PDF title (generated or specified)
    returned: always
    type: str
    sample: "Strategic Market Analysis"
  
  num_pages:
    description: Number of pages generated
    returned: always
    type: int
    sample: 3
  
  size_kb:
    description: PDF file size in KB
    returned: always
    type: float
    sample: 45.2
  
  metadata:
    description: Metadata generated with Faker
    returned: always
    type: dict
    sample:
      company: "Tech Solutions Inc."
      date: "2025-11-10"
      department: "Human Resources"
'''

import os
import sys
import json
from ansible.module_utils.basic import AnsibleModule

def generate_pdf_with_faker(author, output_path, num_pages, title, faker_locale):
    """
    Generate a PDF using Pandoc and Faker
    """
    try:
        from faker import Faker
        import random
        from datetime import datetime
        import subprocess
        import tempfile
    except ImportError as e:
        return False, f"Error importing libraries: {str(e)}. Install: pip install faker"
    
    # Verify that pandoc is installed
    try:
        result = subprocess.run(['pandoc', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "Pandoc is not installed. Install: apt install pandoc (Ubuntu) or brew install pandoc (Mac)"
    except FileNotFoundError:
        return False, "Pandoc is not installed. Install: apt install pandoc (Ubuntu) or brew install pandoc (Mac)"
    
    # Initialize Faker with specified locale
    fake = Faker(faker_locale)
    
    # Generate data with Faker if not specified
    if not title or title == "":
        title = fake.catch_phrase() if faker_locale.startswith('en') else fake.sentence(nb_words=6).rstrip('.')
    
    if num_pages == 0:
        num_pages = random.randint(2, 5)
    
    # Metadata generated with Faker
    metadata = {
        'company': fake.company(),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'department': fake.job(),
        'city': fake.city(),
        'email': fake.company_email()
    }
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Generate Markdown content
    markdown_content = f"""---
title: "{title}"
author: "{author}"
date: "{metadata['date']}"
geometry: margin=2.5cm
fontsize: 11pt
documentclass: article
---

# {title}

**Author:** {author}  
**Company:** {metadata['company']}  
**Department:** {metadata['department']}  
**Date:** {metadata['date']}  
**City:** {metadata['city']}  
**Email:** {metadata['email']}

---

"""

    # CONTENT GENERATED WITH FAKER
    for i in range(num_pages):
        # Section title
        section_title = fake.catch_phrase() if faker_locale.startswith('en') else fake.sentence(nb_words=4).rstrip('.')
        markdown_content += f"\n## Section {i+1}: {section_title}\n\n"
        
        # Content paragraphs
        num_paragraphs = random.randint(3, 6)
        for _ in range(num_paragraphs):
            paragraph = fake.paragraph(nb_sentences=random.randint(4, 8))
            markdown_content += f"{paragraph}\n\n"
        
        # Bullet list
        if random.choice([True, False]):
            markdown_content += "### Key Points:\n\n"
            for _ in range(random.randint(3, 5)):
                bullet = fake.sentence(nb_words=random.randint(5, 10))
                markdown_content += f"- {bullet}\n"
            markdown_content += "\n"
        
        # Random data table
        if random.choice([True, False]) and i < num_pages - 1:
            markdown_content += "### Statistical Data:\n\n"
            markdown_content += "| Concept | Value | Percentage |\n"
            markdown_content += "|---------|-------|------------|\n"
            
            for _ in range(random.randint(3, 6)):
                concept = fake.word().capitalize()
                value = random.randint(100, 9999)
                percentage = random.randint(1, 100)
                markdown_content += f"| {concept} | {value} | {percentage}% |\n"
            
            markdown_content += "\n"
        
        # Page break (except last page)
        if i < num_pages - 1:
            markdown_content += "\n\\newpage\n\n"
    
    # Save temporary Markdown
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_md:
        temp_md.write(markdown_content)
        temp_md_path = temp_md.name
    
    try:
        # Convert Markdown to PDF with Pandoc
        pandoc_cmd = [
            'pandoc',
            temp_md_path,
            '-o', output_path,
            '--pdf-engine=pdflatex',
            '-V', 'geometry:margin=2.5cm',
            '-V', 'fontsize=11pt',
            '--toc',  # Table of contents
            '--toc-depth=2',
            '--highlight-style=tango'
        ]
        
        result = subprocess.run(
            pandoc_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            # Try with alternative engine if pdflatex fails
            pandoc_cmd[3] = '--pdf-engine=xelatex'
            result = subprocess.run(
                pandoc_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                return False, f"Error executing Pandoc: {result.stderr}"
        
    finally:
        # Clean up temporary file
        if os.path.exists(temp_md_path):
            os.unlink(temp_md_path)
    
    # Verify that the PDF was created
    if not os.path.exists(output_path):
        return False, "The PDF was not generated correctly"
    
    # Get file size
    size_bytes = os.path.getsize(output_path)
    size_kb = round(size_bytes / 1024, 2)
    
    return True, {
        'pdf_path': output_path,
        'author': author,
        'title': title,
        'num_pages': num_pages,
        'size_kb': size_kb,
        'metadata': metadata
    }


def main():
    module = AnsibleModule(
        argument_spec=dict(
            author=dict(type='str', required=True),
            output_path=dict(type='str', required=False, default='/tmp/generated_document.pdf'),
            num_pages=dict(type='int', required=False, default=0),
            title=dict(type='str', required=False, default=''),
            faker_locale=dict(type='str', required=False, default='es_ES')
        ),
        supports_check_mode=True
    )
    
    # Get parameters
    author = module.params['author']
    output_path = module.params['output_path']
    num_pages = module.params['num_pages']
    title = module.params['title']
    faker_locale = module.params['faker_locale']
    
    # Validations
    if not author or author.strip() == '':
        module.fail_json(msg="The 'author' parameter cannot be empty")
    
    if num_pages < 0 or num_pages > 100:
        module.fail_json(msg="The 'num_pages' parameter must be between 0 and 100")
    
    # Check mode (--check)
    if module.check_mode:
        module.exit_json(
            changed=False,
            msg="Check mode: PDF was not generated",
            pdf_path=output_path,
            author=author
        )
    
    # Generate the PDF
    success, result = generate_pdf_with_faker(author, output_path, num_pages, title, faker_locale)
    
    if success:
        module.exit_json(
            changed=True,
            msg=f"PDF generated successfully: {output_path}",
            **result
        )
    else:
        module.fail_json(msg=f"Error generating PDF: {result}")


if __name__ == '__main__':
    main()
