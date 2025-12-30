#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_http_navigation

short_description: Generates complete HTTP web navigation (Layer 2)

description:
  - Generates complete web browsing sessions with DNS + TCP + HTTP
  - Supports multiple content types (HTML, CSS, JS, JSON)
  - Automatically handles DNS resolution, TCP handshake, and termination
  - Outputs packets to a PCAP file

options:
  host:
    description: Domain name to navigate to
    required: true
    type: str
  
  src_ip:
    description: Client IP address
    required: true
    type: str
  
  dns_srvr_ip:
    description: DNS resolver IP address
    required: true
    type: str
  
  contents:
    description: List of content types and sizes to fetch
    required: false
    type: list
    default: [{"tipo": "html", "tamano": 1000}]
    notes:
      - "Format: list of dicts with 'tipo' and 'tamano' keys"
      - "Valid tipos: html, css, js, json"
      - "tamano in bytes (or null for auto-generation)"
  
  dst_port:
    description: HTTP port (80 or 443)
    required: false
    type: int
    default: 80
  
  timestamp:
    description: Base timestamp for packets
    required: false
    type: float
  
  output_path:
    description: Path to output PCAP file
    required: true
    type: str
  
  faker_seed:
    description: Seed for reproducibility (ensures deterministic packet generation)
    required: false
    type: int
    default: null

author:
    - Integration Architect
'''

EXAMPLES = r'''
# Simple web navigation (HTML only) with deterministic seeding
- name: Navigate to website
  generate_http_navigation:
    host: "www.example.com"
    src_ip: "192.168.1.100"
    dns_srvr_ip: "8.8.8.8"
    contents:
      - tipo: "html"
        tamano: 1500
    output_path: "/tmp/http_navigation.pcap"
    faker_seed: 42

# Complete web page load (HTML + CSS + JS)
- name: Load complete web page
  generate_http_navigation:
    host: "www.social-network.com"
    src_ip: "192.168.1.100"
    dns_srvr_ip: "8.8.8.8"
    contents:
      - tipo: "html"
        tamano: 2000
      - tipo: "css"
        tamano: 500
      - tipo: "js"
        tamano: 800
      - tipo: "json"
        tamano: 300
    output_path: "/tmp/http_complete.pcap"
'''

RETURN = r'''
packets_generated:
    description: Number of packets generated
    type: int
    returned: always
success:
    description: Whether navigation was successful
    type: bool
    returned: always
resolved_ip:
    description: Resolved IP address
    type: str
    returned: always
output_file:
    description: Path to generated PCAP file
    type: str
    returned: always
'''

import os
import sys
import time
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dfir.network.second_layer.http import http_web_navigation
from ansible.module_utils.dfir.network.pcap_merger import merge_pcap_with_mergecap


def generate_http_packets(module):
    """
    Main function to generate HTTP navigation packets based on module parameters.
    """
    host = module.params['host']
    src_ip = module.params['src_ip']
    dns_srvr_ip = module.params['dns_srvr_ip']
    contents_params = module.params['contents']
    dst_port = module.params['dst_port']
    timestamp = module.params['timestamp']
    output_path = module.params['output_path']
    faker_seed = module.params.get('faker_seed')  # Get seed parameter
    
    # Get current timestamp if not provided
    if timestamp is None:
        timestamp = time.time()
    
    try:
        # Convert contents format from Ansible to function format
        # Ansible format: [{"tipo": "html", "tamano": 1000}, ...]
        # Function format: [("html", 1000), ...]
        contents = []
        if contents_params:
            for item in contents_params:
                tipo = item.get('tipo', 'html')
                tamano = item.get('tamano', None)
                contents.append((tipo, tamano))
        else:
            contents = [("html", 1000)]
        
        # Generate HTTP navigation with optional seeding
        packets, success, resolved_ip = http_web_navigation(
            host=host,
            source_ip=src_ip,
            dns_srvr_ip=dns_srvr_ip,
            contents=contents,
            base_timestamp=timestamp,
            dest_port=dst_port,
            seed=faker_seed
        )
        
        merge_pcap_with_mergecap(module, output_path, packets)
        
        # Return success
        module.exit_json(
            changed=True,
            packets_generated=len(packets),
            success=success,
            resolved_ip=resolved_ip,
            output_file=output_path,
            host=host,
            faker_seed=faker_seed
        )
        
    except Exception as e:
        module.fail_json(msg=f"Error generating HTTP navigation: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', required=True),
            src_ip=dict(type='str', required=True),
            dns_srvr_ip=dict(type='str', required=True),
            contents=dict(
                type='list',
                required=False,
                default=[{"tipo": "html", "tamano": 1000}]
            ),
            dst_port=dict(type='int', required=False, default=80),
            timestamp=dict(type='float', required=False, default=None),
            output_path=dict(type='str', required=True),
            faker_seed=dict(type='int', required=False, default=None)
        ),
        supports_check_mode=False
    )
    
    generate_http_packets(module)


if __name__ == '__main__':
    main()

