"""
TCP Plain Text Communication - Layer 2 Primitive
=================================================

This module provides a Layer 2 primitive for generating plain-text TCP
communication between two endpoints. It simulates raw TCP exchanges where
commands and responses are sent as readable ASCII text.

Architecture:
    Layer 2 (Abstraction) - tcp_plain_text_communication.py [THIS MODULE]
        ↓ uses
    Layer 1 (Atomic) - tcp_primitives.py (Layer1Generator)

Use Cases:
    - Simulating netcat-like communications
    - Credential exfiltration scenarios
    - Command & control (C2) communications
    - Plain-text remote execution simulations
    - Forensic analysis demonstrations

Dependencies:
    - Layer1Generator: TCP Layer 1 primitives
    - scapy: Packet manipulation
    - typing: Type hints
"""

from ansible.module_utils.dfir.network.first_layer.tcp_primitives import Layer1Generator
from ansible.module_utils.dfir.network.utils import get_random_time, get_public_ip, now_ts
from typing import List, Optional, Dict, Union
import subprocess
import sys

try:
    from scapy.all import Packet
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import Packet


def tcp_plain_text_communication(
    messages: List[Dict[str, str]],
    attacker_ip: str,
    victim_ip: str,
    base_timestamp: Optional[float] = None,
    attacker_port: Optional[int] = None,
    victim_port: int = 4444,
    attacker_mac: Optional[str] = None,
    victim_mac: Optional[str] = None,
    seed: Optional[int] = None,
    index: int = 0,
    close_connection: bool = True
) -> List[Packet]:
    """
    Generate plain-text TCP communication between attacker and victim.
    
    This Layer 2 primitive orchestrates a complete TCP conversation with
    plain-text messages. It handles:
    1. TCP three-way handshake (SYN, SYN/ACK, ACK)
    2. Message exchange (attacker sends, victim responds)
    3. TCP connection termination (FIN sequence) [optional]
    
    Args:
        messages: List of message pairs in format:
                 [{"attacker": "command", "victim": "response"}, ...]
                 Example:
                 [
                     {"attacker": "cat /etc/passwd", "victim": "root:x:0:0..."},
                     {"attacker": "whoami", "victim": "root"}
                 ]
        attacker_ip: Attacker's IP address (generates random public IP if None)
        victim_ip: Victim's IP address
        base_timestamp: Base timestamp for first packet (current time if None)
        attacker_port: Source port for attacker (random if None)
        victim_port: Destination port on victim (default: 4444)
        attacker_mac: Attacker's MAC address (random if None)
        victim_mac: Victim's MAC address (random if None)
        seed: Base seed for reproducibility (None for random behavior)
        index: Index offset to derive unique sub-seeds
        close_connection: If True, append FIN sequence at end (default: True)
    
    Returns:
        List[Packet]: All packets in the communication:
                     - 3 packets for TCP handshake
                     - 2 packets per message (attacker → victim, victim → attacker)
                     - 4 packets for connection close (if close_connection=True)
    
    Forensic Indicators:
        - Plain-text commands visible in packet payload
        - Readable ASCII text in TCP stream
        - Sequential command/response pattern
        - Typical C2 or exfiltration behavior
        - Use of non-standard ports (e.g., 4444)
    
    Example:
        >>> messages = [
        ...     {"attacker": "cat /etc/samba/creds.txt", 
        ...      "victim": "username=juan\\npassword=12345"},
        ...     {"attacker": "exfiltrate creds", "victim": "ok"}
        ... ]
        >>> packets = tcp_plain_text_communication(
        ...     messages=messages,
        ...     attacker_ip="203.0.113.50",
        ...     victim_ip="192.168.1.100",
        ...     victim_port=4444,
        ...     seed=42
        ... )
        >>> # Result: 3 (handshake) + 4 (messages) + 4 (close) = 11 packets
    """
    # Initialize
    timestamp = base_timestamp if base_timestamp is not None else now_ts()
    all_packets: List[Packet] = []
    
    # Generate random attacker IP if not provided
    if attacker_ip is None:
        attacker_ip = get_public_ip(seed=seed, index=index)
    
    # Initialize Layer 1 generator with seed
    generator = Layer1Generator(seed=seed, index=index)
    
    # ========================================================================
    # STEP 1: TCP Three-Way Handshake
    # ========================================================================
    tcp_handshake, seq_attacker, seq_victim = generator.start_complete_connection(
        source_ip=attacker_ip,
        dest_ip=victim_ip,
        source_port=attacker_port,
        dest_port=victim_port,
        ts=timestamp,
        client_mac=attacker_mac,
        server_mac=victim_mac
    )
    all_packets.extend(tcp_handshake)
    
    # Update timestamp after handshake
    current_time = get_random_time(
        tcp_handshake[-1].time, 
        distribution="uniform", 
        seed=seed, 
        index=index + 1000
    )
    
    # ========================================================================
    # STEP 2: Exchange Messages
    # ========================================================================
    # Track last packet from each side for sequence number calculation
    # tcp_handshake = [SYN (attacker), SYN/ACK (victim), ACK (attacker)]
    last_attacker_packet = tcp_handshake[-1]  # ACK from attacker
    last_victim_packet = tcp_handshake[1]      # SYN/ACK from victim
    
    for i, message_pair in enumerate(messages):
        attacker_msg = message_pair.get("attacker", "")
        victim_msg = message_pair.get("victim", "")
        
        # Attacker sends command/message
        if attacker_msg:
            attacker_packet = generator.add_packet_in_progress(
                previous_packet=last_victim_packet,
                payload=attacker_msg.encode('utf-8'),
                flags="PA",  # Push + ACK
                ts=current_time,
                client_mac=attacker_mac,
                server_mac=victim_mac
            )
            all_packets.append(attacker_packet)
            last_attacker_packet = attacker_packet
            
            # Update timestamp
            current_time = get_random_time(
                current_time, 
                distribution="uniform", 
                seed=seed, 
                index=index + 2000 + i * 10
            )
        
        # Victim responds
        if victim_msg:
            victim_packet = generator.add_packet_in_progress(
                previous_packet=last_attacker_packet,
                payload=victim_msg.encode('utf-8'),
                flags="PA",  # Push + ACK
                ts=current_time,
                client_mac=attacker_mac,
                server_mac=victim_mac
            )
            all_packets.append(victim_packet)
            last_victim_packet = victim_packet
            
            # Update timestamp
            current_time = get_random_time(
                current_time, 
                distribution="uniform", 
                seed=seed, 
                index=index + 2001 + i * 10
            )
    
    # ========================================================================
    # STEP 3: TCP Connection Termination (Optional)
    # ========================================================================
    if close_connection:
        fin_packets = generator.finalize_connection(
            last_client_packet=last_attacker_packet,
            last_server_packet=last_victim_packet,
            ts=current_time,
            client_mac=attacker_mac,
            server_mac=victim_mac
        )
        all_packets.extend(fin_packets)
    
    return all_packets
