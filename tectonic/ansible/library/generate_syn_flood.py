#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_syn_flood

short_description: Generates SYN Flood attack traffic (Layer 3 Profile)

description:
  - Generates realistic SYN Flood attack patterns
  - Simulates multiple attackers flooding a victim server
  - Creates half-open TCP connections (SYN + SYN/ACK only)
  - Supports single-port and multi-port attack scenarios
  - Outputs all attack packets to a PCAP file

options:
  attack_type:
    description: Type of SYN flood attack to generate
    required: true
    type: str
    choices: [simple, multiport]
  
  victim_ip:
    description: Victim server IP address
    required: true
    type: str
  
  attackers_amount:
    description: Number of unique attacker IP addresses (default 100)
    required: false
    type: int
    default: 100
  
  dest_port:
    description: Target port (for simple attack type)
    required: false
    type: int
    default: 80
  
  dest_multiple_ports:
    description: List of target ports (for multiport attack type)
    required: false
    type: list
    elements: int
    default: [80, 443, 22, 3389]
  
  attackers_per_port:
    description: Number of attackers per port (for multiport attack type)
    required: false
    type: int
    default: 50
  
  ms_attack_duration:
    description: Total attack duration in milliseconds
    required: false
    type: float
    default: 1000.0
  
  timestamp:
    description: Base timestamp for packets (current time if not specified)
    required: false
    type: float
  
  verbose:
    description: Print detailed progress information
    required: false
    type: bool
    default: true
  
  output_path:
    description: Path to output PCAP file
    required: true
    type: str

author:
    - Integration Architect
'''

EXAMPLES = r'''
# Simple SYN flood attack (100 attackers targeting port 80)
- name: Generate simple SYN flood attack
  generate_syn_flood:
    attack_type: simple
    victim_ip: "192.168.1.100"
    attackers_amount: 100
    dest_port: 80
    ms_attack_duration: 1000
    output_path: "/tmp/syn_flood_simple.pcap"

# Large-scale SYN flood (500 attackers)
- name: Generate large-scale SYN flood attack
  generate_syn_flood:
    attack_type: simple
    victim_ip: "10.0.0.50"
    attackers_amount: 500
    dest_port: 443
    ms_attack_duration: 2000
    output_path: "/tmp/syn_flood_large.pcap"

# Multi-port SYN flood attack
- name: Generate multi-port SYN flood attack
  generate_syn_flood:
    attack_type: multiport
    victim_ip: "172.16.0.10"
    dest_multiple_ports: [80, 443, 22, 3389, 8080]
    attackers_per_port: 25
    output_path: "/tmp/syn_flood_multiport.pcap"
'''

RETURN = r'''
packets_generated:
    description: Total number of packets generated
    type: int
    returned: always
syn_packets:
    description: Number of SYN packets generated (attack initiation)
    type: int
    returned: always
half_open_connections:
    description: Number of half-open connections created
    type: int
    returned: always
unique_attackers:
    description: Number of unique attacker IP addresses
    type: int
    returned: always
attack_rate_pps:
    description: Attack rate in packets per second
    type: float
    returned: always
output_file:
    description: Path to generated PCAP file
    type: str
    returned: always
duration_seconds:
    description: Duration of attack traffic in seconds
    type: float
    returned: always
'''

import os
import sys
import time
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.third_layer.syn_flood import SynFloodProfile
from ansible.module_utils.pcap_merger import merge_pcap_with_mergecap


def generate_syn_flood_packets(module):
    """
    Main function to generate SYN flood attack packets based on module parameters.
    """
    attack_type = module.params['attack_type']
    victim_ip = module.params['victim_ip']
    attackers_amount = module.params['attackers_amount']
    dest_port = module.params['dest_port']
    dest_multiple_ports = module.params['dest_multiple_ports']
    attackers_per_port = module.params['attackers_per_port']
    ms_attack_duration = module.params['ms_attack_duration']
    timestamp = module.params['timestamp']
    verbose = module.params['verbose']
    output_path = module.params['output_path']
    
    # Get current timestamp if not provided
    if timestamp is None:
        timestamp = time.time()
    
    # Validate output_path
    if not output_path:
        module.fail_json(msg="output_path is required and cannot be empty")
    
    try:
        # Initialize Layer 3 SYN Flood profile generator
        profile = SynFloodProfile()
        
        # Generate packets based on attack type
        if attack_type == 'simple':
            packets = profile.syn_flood_attack(
                victim_ip=victim_ip,
                base_timestamp=timestamp,
                attacker_count=attackers_amount,
                dest_port=dest_port,
                attack_duration_ms=ms_attack_duration,
                verbose=verbose
            )
            unique_attackers = attackers_amount
            
        elif attack_type == 'multiport':
            packets = profile.syn_flood_multiport(
                victim_ip=victim_ip,
                ports=dest_multiple_ports,
                base_timestamp=timestamp,
                attackers_per_port=attackers_per_port,
                verbose=verbose
            )
            unique_attackers = len(dest_multiple_ports) * attackers_per_port
        
        else:
            module.fail_json(msg=f"Unsupported attack_type: {attack_type}")
        
        # Calculate statistics
        if packets:
            duration = packets[-1].time - packets[0].time
            attack_rate = len(packets) / duration if duration > 0 else 0
        else:
            duration = 0.0
            attack_rate = 0.0
        
        # SYN packets = half of total (SYN + SYN/ACK pairs)
        syn_packets = len(packets) // 2
        half_open_connections = syn_packets
        
        merge_pcap_with_mergecap(module, output_path, packets)
        
        # Return success
        module.exit_json(
            changed=True,
            packets_generated=len(packets),
            syn_packets=syn_packets,
            half_open_connections=half_open_connections,
            unique_attackers=unique_attackers,
            attack_rate_pps=round(attack_rate, 2),
            output_file=output_path,
            duration_seconds=round(duration, 3),
            attack_type=attack_type,
            victim_ip=victim_ip
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        module.fail_json(msg=f"Error generating SYN flood attack: {str(e)}\nTraceback:\n{tb}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            attack_type=dict(
                type='str',
                required=True,
                choices=['simple', 'multiport']
            ),
            victim_ip=dict(type='str', required=True),
            attackers_amount=dict(type='int', required=False, default=100),
            dest_port=dict(type='int', required=False, default=80),
            dest_multiple_ports=dict(type='list', elements='int', required=False, default=[80, 443, 22, 3389]),
            attackers_per_port=dict(type='int', required=False, default=50),
            ms_attack_duration=dict(type='float', required=False, default=1000.0),
            timestamp=dict(type='float', required=False, default=None),
            verbose=dict(type='bool', required=False, default=True),
            output_path=dict(type='str', required=True)
        ),
        supports_check_mode=False
    )
    
    generate_syn_flood_packets(module)


if __name__ == '__main__':
    main()

