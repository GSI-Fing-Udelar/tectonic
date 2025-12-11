#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_dns_conversation

short_description: Generates DNS conversation primitives (Layer 2)

description:
  - Generates complete DNS query/response conversations
  - Supports successful resolutions (NOERROR)
  - Supports failed resolutions (NXDOMAIN, SERVFAIL)
  - Supports multiple DNS queries in sequence
  - Outputs packets to a PCAP file

options:
  domain:
    description: Domain name to query
    required: true
    type: str
  
  src_ip:
    description: Client IP address
    required: true
    type: str
  
  ip_resolver:
    description: DNS resolver IP address (e.g., 8.8.8.8)
    required: true
    type: str
  
  result:
    description: Desired DNS resolution outcome
    required: false
    type: str
    choices: [Exitoso, No Existente, Fallido]
    default: Exitoso
  
  response_ip:
    description: IP address to return in successful resolution (auto-generated if not provided)
    required: false
    type: str
  
  timestamp:
    description: Base timestamp for packets (current time if not specified)
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
# Successful DNS resolution with deterministic seeding
- name: Resolve domain successfully
  generate_dns_conversation:
    domain: "www.example.com"
    src_ip: "192.168.1.100"
    ip_resolver: "8.8.8.8"
    result: "Exitoso"
    response_ip: "93.184.216.34"
    output_path: "/tmp/dns_success.pcap"
    faker_seed: 42

# Failed DNS resolution (NXDOMAIN)
- name: Failed DNS resolution
  generate_dns_conversation:
    domain: "nonexistent.com"
    src_ip: "192.168.1.100"
    ip_resolver: "8.8.8.8"
    result: "No Existente"
    output_path: "/tmp/dns_nxdomain.pcap"
    faker_seed: 42
'''

RETURN = r'''
packets_generated:
    description: Number of packets generated
    type: int
    returned: always
resolved_ip:
    description: Resolved IP address (None if resolution failed)
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
from ansible.module_utils.second_layer.dns import dns_communication
from ansible.module_utils.pcap_merger import merge_pcap_with_mergecap


def generate_dns_packets(module):
    """
    Main function to generate DNS packets based on module parameters.
    """
    domain = module.params['domain']
    src_ip = module.params['src_ip']
    ip_resolver = module.params['ip_resolver']
    result = module.params['result']
    response_ip = module.params['response_ip']
    timestamp = module.params['timestamp']
    output_path = module.params['output_path']
    faker_seed = module.params.get('faker_seed')  # Get seed parameter
    
    # Get current timestamp if not provided
    if timestamp is None:
        timestamp = time.time()
    
    try:
        # Map Spanish result values to English
        result_mapping = {
            "Exitoso": "Success",
            "No Existente": "Not Exists",
            "Fallido": "Failed"
        }
        expected_result = result_mapping.get(result, result)
        
        # Generate DNS conversation with optional seeding
        packets, resolved_ip = dns_communication(
            domain=domain,
            source_ip=src_ip,
            dns_server_ip=ip_resolver,
            expected_result=expected_result,
            return_ip=response_ip,
            base_timestamp=timestamp,
            seed=faker_seed
        )
        
        merge_pcap_with_mergecap(module, output_path, packets)
        
        # Return success
        module.exit_json(
            changed=True,
            packets_generated=len(packets),
            resolved_ip=resolved_ip,
            output_file=output_path,
            result=result,
            faker_seed=faker_seed
        )
        
    except Exception as e:
        module.fail_json(msg=f"Error generating DNS packets: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            domain=dict(type='str', required=True),
            src_ip=dict(type='str', required=True),
            ip_resolver=dict(type='str', required=True),
            result=dict(
                type='str',
                required=False,
                default='Exitoso',
                choices=['Exitoso', 'No Existente', 'Fallido']
            ),
            response_ip=dict(type='str', required=False, default=None),
            timestamp=dict(type='float', required=False, default=None),
            output_path=dict(type='str', required=True),
            faker_seed=dict(type='int', required=False, default=None)
        ),
        supports_check_mode=False
    )
    
    generate_dns_packets(module)


if __name__ == '__main__':
    main()

