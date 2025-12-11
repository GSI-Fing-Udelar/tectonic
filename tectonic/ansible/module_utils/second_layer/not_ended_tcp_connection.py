"""
Not Ended TCP Connection - Layer 2 Primitive
=============================================

This module provides a Layer 2 primitive for generating incomplete TCP connections,
specifically the SYN -> SYN/ACK sequence without the final ACK.

This is commonly used to simulate:
- SYN Flood attacks
- Connection timeouts
- Network scanning behavior

Architecture:
    Layer 3 (Profiles) - syn_flood.py
        ↓ orchestrates
    Layer 2 (Abstraction) - not_ended_tcp_connection.py [THIS MODULE]
        ↓ uses
    Layer 1 (Atomic) - tcp_primitives.py (Layer1Generator)

Dependencies:
    - tcp_primitives: Layer 1 TCP primitives (Layer1Generator)
    - scapy: Packet manipulation
    - typing: Type hints
"""

from ansible.module_utils.first_layer.tcp_primitives import Layer1Generator, rnd_port, rnd_seq, now_ts
from typing import List, Optional, Tuple
import time
import subprocess
import sys

try:
    from scapy.all import Packet, IP, TCP, Ether, wrpcap
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import Packet, IP, TCP, Ether, wrpcap


# ============================================================================
# LAYER 2 PRIMITIVE - NOT ENDED TCP CONNECTION
# ============================================================================

def not_ended_tcp_connection(
    source_ip: str,
    dest_ip: str,
    client_mac: Optional[str] = None,
    server_mac: Optional[str] = None,
    source_port: Optional[int] = None,
    dest_port: int = 80,
    seq: Optional[int] = None,
    ts: Optional[float] = None
) -> Tuple[List[Packet], int, int]:
    """
    Generate an incomplete TCP connection (SYN -> SYN/ACK only).
    
    This primitive simulates a partial TCP handshake where the client sends
    a SYN packet, the server responds with SYN/ACK, but the client never
    sends the final ACK to complete the connection.
    
    This is the characteristic signature of:
    - SYN Flood attacks (DoS/DDoS)
    - Half-open connection scanning
    - Connection timeout scenarios
    
    Args:
        source_ip: Source (attacker/client) IP address
        dest_ip: Destination (victim/server) IP address
        source_port: Source port (random if None)
        dest_port: Destination port (default: 80)
        seq: Initial sequence number (random if None)
        ts: Timestamp for the first packet (current time if None)
    
    Returns:
        Tuple containing:
            - List[Packet]: List of 2 packets [SYN, SYN/ACK]
            - int: Client sequence number after SYN
            - int: Server sequence number after SYN/ACK
    
    Packet Sequence:
        1. SYN (Client -> Server): Connection initiation request
        2. SYN/ACK (Server -> Client): Server acknowledges and responds
        3. [MISSING ACK]: Client never completes the handshake
    
    Forensic Indicators:
        - Half-open connections in server state table
        - Missing final ACK in TCP streams
        - High volume of SYN packets from same source (attack pattern)
        - Resource exhaustion on target server
    
    Example:
        >>> # Single incomplete connection
        >>> packets, seq_c, seq_s = not_ended_tcp_connection(
        ...     source_ip="10.0.0.100",
        ...     dest_ip="192.168.1.1",
        ...     dest_port=443
        ... )
        >>> print(f"Generated {len(packets)} packets (SYN + SYN/ACK)")
        
        >>> # For SYN flood simulation, call multiple times with different ports
        >>> for i in range(100):
        ...     attack_pkts, _, _ = not_ended_tcp_connection(
        ...         source_ip=f"10.0.0.{i}",
        ...         dest_ip="192.168.1.1",
        ...         dest_port=80
        ...     )
    """
    # Initialize Layer 1 generator
    generator = Layer1Generator()
    
    # Generate the complete handshake first
    tcp_packets, seq_c, seq_s = generator.start_complete_connection(
        source_ip=source_ip,
        dest_ip=dest_ip,
        source_port=source_port,
        dest_port=dest_port,
        seq=seq,
        ts=ts,
        client_mac=client_mac,
        server_mac=server_mac
    )
    
    # Return only the first 2 packets (SYN and SYN/ACK), removing the final ACK
    # This simulates a half-open connection state
    return tcp_packets[:2], seq_c, seq_s
