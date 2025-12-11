#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_network_user_profile

short_description: Generates user behavior profiles (Layer 3)

description:
  - Generates realistic user behavior profiles with multiple web sessions
  - Orchestrates DNS, TCP, and HTTP traffic for complete browsing sessions
  - Supports single user or multiple concurrent users
  - Automatically generates unique domains and realistic content
  - Outputs all packets to a single PCAP file

options:
  profile_type:
    description: Type of user profile to generate
    required: true
    type: str
    choices: [single_user, multiple_users]
  
  hosts_amount:
    description: Number of websites to visit (for single_user profile)
    required: false
    type: int
    default: 5
  
  usrs_amount:
    description: Number of concurrent users (for multiple_users profile)
    required: false
    type: int
    default: 3
  
  hosts_per_user:
    description: Websites each user visits (for multiple_users profile)
    required: false
    type: int
    default: 3
  
  src_ip:
    description: Client IP address (for single_user profile)
    required: false
    type: str
    default: "192.168.1.100"
  
  ip_base:
    description: Base IP for multiple users (e.g., "192.168.1.")
    required: false
    type: str
    default: "192.168.1."
  
  ip_resolver:
    description: DNS resolver IP address
    required: false
    type: str
    default: "8.8.8.8"
  
  dst_port:
    description: HTTP port
    required: false
    type: int
    default: 80
  
  verbose:
    description: Print detailed progress information
    required: false
    type: bool
    default: true
  
  timestamp:
    description: Base timestamp for packets
    required: false
    type: float
  
  output_path:
    description: Path to output PCAP file
    required: true
    type: str

author:
    - Integration Architect
'''

EXAMPLES = r'''
# Single user browsing 5 websites
- name: Generate single user browsing profile
  generate_network_user_profile:
    profile_type: single_user
    hosts_amount: 5
    src_ip: "192.168.1.100"
    ip_resolver: "8.8.8.8"
    output_path: "/tmp/user_browsing.pcap"

# Multiple users (3 users, each visiting 3 websites)
- name: Generate multiple users browsing profile
  generate_network_user_profile:
    profile_type: multiple_users
    usrs_amount: 3
    hosts_per_user: 3
    ip_base: "192.168.1."
    ip_resolver: "8.8.8.8"
    output_path: "/tmp/multi_user_browsing.pcap"
'''

RETURN = r'''
packets_generated:
    description: Total number of packets generated
    type: int
    returned: always
sessions_successful:
    description: Number of successful browsing sessions
    type: int
    returned: always
sessions_failed:
    description: Number of failed browsing sessions
    type: int
    returned: always
output_file:
    description: Path to generated PCAP file
    type: str
    returned: always
duration_seconds:
    description: Duration of generated traffic in seconds
    type: float
    returned: always
'''

import os
import sys
import time
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.third_layer.http_communication import Layer3Profile
from ansible.module_utils.pcap_merger import merge_pcap_with_mergecap


def generate_profile_packets(module):
    """
    Main function to generate user profile packets based on module parameters.
    """
    profile_type = module.params['profile_type']
    hosts_amount = module.params['hosts_amount']
    usrs_amount = module.params['usrs_amount']
    hosts_per_user = module.params['hosts_per_user']
    src_ip = module.params['src_ip']
    ip_base = module.params['ip_base']
    ip_resolver = module.params['ip_resolver']
    dst_port = module.params['dst_port']
    verbose = module.params['verbose']
    timestamp = module.params['timestamp']
    output_path = module.params['output_path']
    
    # Get current timestamp if not provided
    if timestamp is None:
        timestamp = time.time()
    
    try:
        # Initialize Layer 3 profile generator
        profile = Layer3Profile()
        
        # Generate packets based on profile type
        if profile_type == 'single_user':
            packets = profile.web_browsing_profile(
                host_count=hosts_amount,
                client_source_ip=src_ip,
                dns_srvr_ip=ip_resolver,
                base_timestamp=timestamp,
                dest_port=dst_port,
                verbose=verbose
            )
            sessions_successful = hosts_amount  # Approximate
            sessions_failed = 0
            
        elif profile_type == 'multiple_users':
            packets = profile.web_browsing_profile_multiple_users(
                user_count=usrs_amount,
                hosts_per_user=hosts_per_user,
                client_base_ip=ip_base,
                dns_srvr_ip=ip_resolver,
                base_timestamp=timestamp,
                verbose=verbose
            )
            sessions_successful = usrs_amount * hosts_per_user  # Approximate
            sessions_failed = 0
        
        else:
            module.fail_json(msg=f"Unsupported profile_type: {profile_type}")
        
        # Calculate duration
        if packets:
            duration = packets[-1].time - packets[0].time
        else:
            duration = 0.0
        
        merge_pcap_with_mergecap(module, output_path, packets)
        
        # Return success
        module.exit_json(
            changed=True,
            packets_generated=len(packets),
            sessions_successful=sessions_successful,
            sessions_failed=sessions_failed,
            output_file=output_path,
            duration_seconds=round(duration, 2),
            profile_type=profile_type
        )
        
    except Exception as e:
        module.fail_json(msg=f"Error generating user profile: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            profile_type=dict(
                type='str',
                required=True,
                choices=['single_user', 'multiple_users']
            ),
            hosts_amount=dict(type='int', required=False, default=5),
            usrs_amount=dict(type='int', required=False, default=3),
            hosts_per_user=dict(type='int', required=False, default=3),
            src_ip=dict(type='str', required=False, default='192.168.1.100'),
            ip_base=dict(type='str', required=False, default='192.168.1.'),
            ip_resolver=dict(type='str', required=False, default='8.8.8.8'),
            dst_port=dict(type='int', required=False, default=80),
            verbose=dict(type='bool', required=False, default=True),
            timestamp=dict(type='float', required=False, default=None),
            output_path=dict(type='str', required=True)
        ),
        supports_check_mode=False
    )
    
    generate_profile_packets(module)


if __name__ == '__main__':
    main()

