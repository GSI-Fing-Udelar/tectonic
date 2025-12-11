#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: generate_wannacry_attack

short_description: Generates WannaCry-style multi-stage attack simulation (Layer 3 Profile)

description:
  - Generates a realistic multi-stage cyberattack simulation
  - Phase 1 - Reconnaissance & credential exfiltration via plain-text TCP
  - Phase 2 - Downloads 5 fake WannaCry components via HTTP (base64-encoded)
  - Phase 3 - Remote execution of downloaded payload
  - Creates forensically realistic attack patterns for training purposes
  - DISCLAIMER - All malware is FAKE (random base64 data) for training only

options:
  victim_ip:
    description: Victim's IP address
    required: true
    type: str
  
  attacker_ip:
    description: Attacker's IP address (random public IP if not specified)
    required: false
    type: str
  
  ip_malicious_server:
    description: Malicious server hosting malware (random public IP if not specified)
    required: false
    type: str
  
  timestamp:
    description: Base timestamp for packets (current time if not specified)
    required: false
    type: float
  
  seed:
    description: Random seed for reproducibility (None for random behavior)
    required: false
    type: int
  
  verbose:
    description: Print detailed progress information
    required: false
    type: bool
    default: true
  
  output_path:
    description: Path to output PCAP file
    required: true
    type: str
'''

EXAMPLES = r'''
# Generate WannaCry-style attack simulation
- name: Generate WannaCry attack scenario
  generate_wannacry_attack:
    victim_ip: "192.168.1.100"
    attacker_ip: "203.0.113.50"
    ip_malicious_server: "198.51.100.25"
    output_path: "/tmp/wannacry_attack.pcap"

# Generate reproducible attack (with seed)
- name: Generate reproducible WannaCry attack
  generate_wannacry_attack:
    victim_ip: "192.168.1.100"
    seed: 42
    verbose: true
    output_path: "/tmp/wannacry_attack_seeded.pcap"

# Generate with auto-generated attacker IPs
- name: Generate WannaCry attack with random attacker IPs
  generate_wannacry_attack:
    victim_ip: "10.0.0.50"
    output_path: "/tmp/wannacry_attack_auto.pcap"
'''

RETURN = r'''
packets_generated:
    description: Total number of packets generated
    type: int
    returned: always
phase1_packets:
    description: Number of packets in Phase 1 (exfiltration)
    type: int
    returned: always
phase2_packets:
    description: Number of packets in Phase 2 (malware download)
    type: int
    returned: always
phase3_packets:
    description: Number of packets in Phase 3 (execution)
    type: int
    returned: always
components_downloaded:
    description: Number of fake WannaCry components downloaded
    type: int
    returned: always
victim_ip:
    description: Victim IP address
    type: str
    returned: always
attacker_ip:
    description: Attacker IP address
    type: str
    returned: always
malicious_server_ip:
    description: Malicious server IP address
    type: str
    returned: always
output_file:
    description: Path to generated PCAP file
    type: str
    returned: always
duration_seconds:
    description: Duration of attack traffic in seconds
    type: float
    returned: always
attack_phases:
    description: Description of attack phases
    type: list
    returned: always
'''

import os
import sys
import time
import traceback
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.third_layer.wannacry import wannacry_attack_simulation
from ansible.module_utils.pcap_merger import merge_pcap_with_mergecap


def generate_wannacry_attack_packets(module):
    """
    Main function to generate WannaCry attack simulation packets based on module parameters.
    """
    victim_ip = module.params['victim_ip']
    attacker_ip = module.params['attacker_ip']
    ip_malicious_server = module.params['ip_malicious_server']
    timestamp = module.params['timestamp']
    seed = module.params['seed']
    verbose = module.params['verbose']
    output_path = module.params['output_path']
    
    # Get current timestamp if not provided
    if timestamp is None:
        timestamp = time.time()
    
    # Validate output_path
    if not output_path:
        module.fail_json(msg="output_path is required and cannot be empty")
    
    try:
        if verbose:
            module.warn("=" * 70)
            module.warn("WANNACRY ATTACK SIMULATION - Layer 3 Profile")
            module.warn("=" * 70)
            module.warn(f"Victim IP: {victim_ip}")
            if attacker_ip:
                module.warn(f"Attacker IP: {attacker_ip}")
            else:
                module.warn("Attacker IP: <random public IP will be generated>")
            if ip_malicious_server:
                module.warn(f"Malicious Server IP: {ip_malicious_server}")
            else:
                module.warn("Malicious Server IP: <random public IP will be generated>")
            module.warn("=" * 70)
            module.warn("Phase 1: Reconnaissance & Credential Exfiltration")
            module.warn("  - Plain-text TCP commands (port 4444)")
            module.warn("  - Reading Samba credentials")
            module.warn("  - Fake exfiltration of credentials")
            module.warn("")
            module.warn("Phase 2: Malware Download (Fake wget)")
            module.warn("  - Downloading 5 fake WannaCry components")
            module.warn("  - HTTP downloads of base64-encoded fake executables")
            module.warn("  - Files: wcry1.bin, wcry2.bin, wcry3.bin, wcry4.bin, wcry5.bin")
            module.warn("")
            module.warn("Phase 3: Remote Execution")
            module.warn("  - Execution command via plain-text TCP")
            module.warn("  - Victim confirms execution")
            module.warn("=" * 70)
        
        # Generate attack packets using Layer 3 profile
        packets = wannacry_attack_simulation(
            victim_ip=victim_ip,
            attacker_ip=attacker_ip,
            malicious_server_ip=ip_malicious_server,
            base_timestamp=timestamp,
            seed=seed,
            index=0
        )
        
        # Calculate statistics
        if packets:
            duration = packets[-1].time - packets[0].time
        else:
            duration = 0.0
        
        # Estimate packet counts per phase (approximate)
        # Phase 1: ~11 packets (3 handshake + 4 messages * 2 - 4 close kept for Phase 3)
        # Phase 2: ~40 packets (5 files × 8 packets per HTTP exchange)
        # Phase 3: ~7 packets (2 messages + 4 close)
        phase1_packets = 11
        phase2_packets = 40
        phase3_packets = 7
        
        # Get actual IPs used (from first few packets)
        victim_ip_used = victim_ip
        attacker_ip_used = attacker_ip if attacker_ip else "auto-generated"
        malicious_server_used = ip_malicious_server if ip_malicious_server else "auto-generated"
        
        # If IPs were auto-generated, extract from packets
        if packets and len(packets) > 0:
            from scapy.all import IP
            if IP in packets[0]:
                if not attacker_ip:
                    attacker_ip_used = packets[0][IP].src
                if not ip_malicious_server and len(packets) > 15:
                    # Try to find the malicious server IP from Phase 2
                    for pkt in packets[10:20]:
                        if IP in pkt and pkt[IP].dst != victim_ip_used and pkt[IP].src == victim_ip_used:
                            malicious_server_used = pkt[IP].dst
                            break
        
        # Write packets to PCAP file
        merge_pcap_with_mergecap(module, output_path, packets)
        
        if verbose:
            module.warn("")
            module.warn("=" * 70)
            module.warn("ATTACK SIMULATION COMPLETE")
            module.warn("=" * 70)
            module.warn(f"Total Packets Generated: {len(packets)}")
            module.warn(f"Phase 1 Packets (Exfiltration): ~{phase1_packets}")
            module.warn(f"Phase 2 Packets (Malware Download): ~{phase2_packets}")
            module.warn(f"Phase 3 Packets (Execution): ~{phase3_packets}")
            module.warn(f"Duration: {duration:.3f} seconds")
            module.warn(f"Output File: {output_path}")
            module.warn("=" * 70)
            module.warn("FORENSIC INDICATORS TO LOOK FOR:")
            module.warn("  - Plain-text credentials in TCP stream")
            module.warn("  - Multiple binary downloads from malicious host")
            module.warn("  - Base64-encoded executables in HTTP responses")
            module.warn("  - Remote execution commands")
            module.warn("  - Use of non-standard port 4444")
            module.warn("=" * 70)
        
        # Return success with detailed statistics
        module.exit_json(
            changed=True,
            packets_generated=len(packets),
            phase1_packets=phase1_packets,
            phase2_packets=phase2_packets,
            phase3_packets=phase3_packets,
            components_downloaded=5,
            victim_ip=victim_ip_used,
            attacker_ip=attacker_ip_used,
            malicious_server_ip=malicious_server_used,
            output_file=output_path,
            duration_seconds=round(duration, 3),
            attack_phases=[
                "Phase 1: Reconnaissance & Credential Exfiltration",
                "Phase 2: Malware Download (5 fake WannaCry components)",
                "Phase 3: Remote Execution"
            ]
        )
        
    except Exception as e:
        tb = traceback.format_exc()
        module.fail_json(msg=f"Error generating WannaCry attack: {str(e)}\nTraceback:\n{tb}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            victim_ip=dict(type='str', required=True),
            attacker_ip=dict(type='str', required=False, default=None),
            ip_malicious_server=dict(type='str', required=False, default=None),
            timestamp=dict(type='float', required=False, default=None),
            seed=dict(type='int', required=False, default=None),
            verbose=dict(type='bool', required=False, default=True),
            output_path=dict(type='str', required=True)
        ),
        supports_check_mode=False
    )
    
    generate_wannacry_attack_packets(module)


if __name__ == '__main__':
    main()
