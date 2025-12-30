#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_tcp_connection

short_description: Generates TCP connection primitives (Layer 1)

description:
  - Generates TCP packet sequences (handshakes, data transfer, termination)
  - Supports complete 3-way handshake
  - Supports incomplete connections (SYN flood simulation)
  - Supports connection termination sequences
  - Outputs packets to a PCAP file

options:
  connection_type:
    description: Type of TCP connection to generate
    required: true
    type: str
    choices: [handshake_complete, handshake_incomplete, data_transfer, termination]
  
  src_ip:
    description: Source IP address (client)
    required: true
    type: str
  
  dest_ip:
    description: Destination IP address (server)
    required: true
    type: str
  
  src_port:
    description: Source port (random if not specified)
    required: false
    type: int
  
  dest_port:
    description: Destination port
    required: false
    type: int
    default: 80
  
  payload:
    description: Optional payload data for data_transfer type
    required: false
    type: str
    default: ""
  
  timestamp:
    description: Base timestamp for packets (current time if not specified)
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
# Generate complete TCP handshake
- name: Generate TCP handshake
  generate_tcp_connection:
    connection_type: handshake_complete
    src_ip: "192.168.1.100"
    dest_ip: "172.16.0.50"
    dest_port: 443
    output_path: "/tmp/tcp_handshake.pcap"

# Generate SYN flood (incomplete handshake)
- name: Generate SYN flood packet
  generate_tcp_connection:
    connection_type: handshake_incomplete
    src_ip: "1.2.3.4"
    dest_ip: "172.16.0.10"
    dest_port: 443
    output_path: "/tmp/syn_flood.pcap"
'''

RETURN = r'''
packets_generated:
    description: Number of packets generated
    type: int
    returned: always
packet_count:
    description: Detailed packet count
    type: int
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
from ansible.module_utils.dfir.network.first_layer.tcp_primitives import Layer1Generator
from ansible.module_utils.dfir.network.second_layer.not_ended_tcp_connection import not_ended_tcp_connection
from ansible.module_utils.dfir.network.pcap_merger import merge_pcap_with_mergecap


def generate_tcp_packets(module):
    """
    Main function to generate TCP packets based on module parameters.
    """
    connection_type = module.params['connection_type']
    src_ip = module.params['src_ip']
    dest_ip = module.params['dest_ip']
    src_port = module.params['src_port']
    dest_port = module.params['dest_port']
    payload = module.params['payload']
    timestamp = module.params['timestamp']
    output_path = module.params['output_path']
    
    # Initialize generator
    generator = Layer1Generator()
    packets = []
    
    # Get current timestamp if not provided
    if timestamp is None:
        timestamp = time.time()
    
    try:
        if connection_type == 'handshake_complete':
            # Generate complete 3-way handshake
            tcp_packets, seq_c, seq_s = generator.start_complete_connection(
                source_ip=src_ip,
                dest_ip=dest_ip,
                source_port=src_port,
                dest_port=dest_port,
                ts=timestamp
            )
            packets = tcp_packets
            
        elif connection_type == 'handshake_incomplete':
            # Generate incomplete handshake (SYN flood)
            # Use Layer 2 not_ended_tcp_connection primitive
            tcp_packets, _, _ = not_ended_tcp_connection(
                source_ip=src_ip,
                dest_ip=dest_ip,
                source_port=src_port,
                dest_port=dest_port,
                ts=timestamp
            )
            packets = tcp_packets
            
        elif connection_type == 'data_transfer':
            # This requires a previous packet context
            # For standalone mode, generate handshake first, then data
            tcp_handshake, seq_c, seq_s = generator.start_complete_connection(
                source_ip=src_ip,
                dest_ip=dest_ip,
                source_port=src_port,
                dest_port=dest_port,
                ts=timestamp
            )
            packets.extend(tcp_handshake)
            
            if payload:
                # Add data packet
                data_packet = generator.add_packet_in_progress(
                    previous_packet=tcp_handshake[-1],
                    payload=payload.encode('utf-8'),
                    flags="PA",
                    ts=timestamp + 0.01
                )
                packets.append(data_packet)
        
        else:
            module.fail_json(msg=f"Unsupported connection_type: {connection_type}")
        
        merge_pcap_with_mergecap(module, output_path, packets)
        
        # Return success
        module.exit_json(
            changed=True,
            packets_generated=len(packets),
            packet_count=len(packets),
            output_file=output_path,
            connection_type=connection_type
        )
        
    except Exception as e:
        module.fail_json(msg=f"Error generating TCP packets: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            connection_type=dict(
                type='str',
                required=True,
                choices=['handshake_complete', 'handshake_incomplete', 'data_transfer', 'termination']
            ),
            src_ip=dict(type='str', required=True),
            dest_ip=dict(type='str', required=True),
            src_port=dict(type='int', required=False, default=None),
            dest_port=dict(type='int', required=False, default=80),
            payload=dict(type='str', required=False, default=''),
            timestamp=dict(type='float', required=False, default=None),
            output_path=dict(type='str', required=True)
        ),
        supports_check_mode=False
    )
    
    generate_tcp_packets(module)


if __name__ == '__main__':
    main()

