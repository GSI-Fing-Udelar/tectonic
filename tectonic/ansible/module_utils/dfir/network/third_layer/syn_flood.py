"""
SYN Flood Profile - Layer 3 Attack Simulation
==============================================

This module provides a Layer 3 profile for simulating SYN Flood attacks.
It orchestrates multiple Layer 2 not_ended_tcp_connection primitives to
generate realistic attack traffic patterns.

Architecture:
    Layer 3 (Profiles) - syn_flood.py [THIS MODULE]
        ↓ orchestrates
    Layer 2 (Abstraction) - not_ended_tcp_connection.py
        ↓ uses
    Layer 1 (Atomic) - tcp_primitives.py (Layer1Generator)

SYN Flood Attack Overview:
    A SYN Flood is a Denial of Service (DoS) attack that exploits the TCP
    handshake mechanism. The attacker sends many SYN packets to a target,
    but never completes the handshake. This leaves the server with many
    "half-open" connections, exhausting its resources.

Dependencies:
    - not_ended_tcp_connection: Layer 2 incomplete TCP primitive
    - scapy: Packet manipulation and PCAP export
    - faker: IP address generation
    - typing: Type hints
"""

from ansible.module_utils.dfir.network.second_layer.not_ended_tcp_connection import not_ended_tcp_connection
from ansible.module_utils.dfir.network.utils import get_mac_address, get_public_ip, now_ts
from typing import List, Optional
import subprocess
import sys

try:
    from scapy.all import Packet
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import Packet

try:
    from faker import Faker
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'faker'])
    from faker import Faker

# Initialize Faker for realistic data generation
fake = Faker()

def generate_attacker_ips(count: int) -> List[str]:
    """
    Generate a list of unique attacker IP addresses.
    
    Args:
        count: Number of unique IP addresses to generate
    
    Returns:
        List[str]: List of unique IP addresses
    """
    ips = set()
    while len(ips) < count:
        ips.add(get_public_ip())
    return list(ips)


# ============================================================================
# LAYER 3 PROFILE - SYN FLOOD ATTACK
# ============================================================================

class SynFloodProfile:
    """
    Layer 3 (Profiles) - SYN Flood Attack Simulation.
    
    This class provides high-level primitives for generating SYN Flood attack
    traffic. It orchestrates multiple Layer 2 not_ended_tcp_connection calls
    to create realistic attack patterns.
    
    Attributes:
        packets_generated: Running count of packets generated
    
    Attack Patterns Supported:
        - Simple SYN Flood: Multiple IPs targeting one server/port
        - Distributed SYN Flood: Many source IPs (DDoS simulation)
        - Multi-port SYN Flood: Targeting multiple ports on same server
    
    Usage:
        >>> profile = SynFloodProfile()
        >>> packets = profile.syn_flood_attack(
        ...     victim_ip="192.168.1.100",
        ...     attacker_count=100,
        ...     base_timestamp=time.time()
        ... )
        >>> print(f"Generated {len(packets)} attack packets")
    """
    
    def __init__(self) -> None:
        """
        Initialize the SYN Flood profile generator.
        """
        self.packets_generated: int = 0
    
    def syn_flood_attack(
        self,
        victim_ip: str,
        base_timestamp: Optional[float] = None,
        attacker_count: int = 100,
        dest_port: int = 80,
        attack_duration_ms: float = 1000.0,
        verbose: bool = True,
        victim_mac: Optional[str] = None
    ) -> List[Packet]:
        """
        Generate a SYN Flood attack from multiple source IPs.
        
        This high-level primitive simulates a Distributed Denial of Service
        (DDoS) attack where multiple attackers send SYN packets to a victim
        server, overwhelming its connection table.
        
        Args:
            victim_ip: Target server IP address
            base_timestamp: Base timestamp for first packet (current time if None)
            attacker_count: Number of unique attacker IPs (default: 100)
            dest_port: Target port on victim server (default: 80)
            attack_duration_ms: Total attack duration in milliseconds (default: 1000ms)
            verbose: Print progress information (default: True)
        
        Returns:
            List[Packet]: All attack packets (2 per attacker: SYN + SYN/ACK)
        
        Attack Characteristics:
            - Each attacker sends one SYN packet
            - Server responds with SYN/ACK (half-open connection)
            - No final ACK sent (connection never completes)
            - Packets are distributed across the attack_duration
        
        Packet Count:
            Total packets = attacker_count × 2
            (Each attacker generates: 1 SYN + 1 SYN/ACK response)
        
        Forensic Indicators:
            - High volume of SYN packets to same destination
            - Many unique source IPs
            - No corresponding ACK packets
            - Server TCP state table exhaustion
            - All targeting same port
        
        Example:
            >>> profile = SynFloodProfile()
            >>> # Simulate 100 attackers flooding port 443
            >>> packets = profile.syn_flood_attack(
            ...     victim_ip="10.0.0.1",
            ...     attacker_count=100,
            ...     dest_port=443,
            ...     attack_duration_ms=500.0
            ... )
            >>> wrpcap("syn_flood_attack.pcap", packets)
        """
        # Initialize timestamp
        timestamp: float = base_timestamp if base_timestamp is not None else now_ts()
        
        # Calculate time interval between attacks
        interval_ms = attack_duration_ms / attacker_count
        interval_sec = interval_ms / 1000.0
        
        # Generate unique attacker IPs
        attacker_ips: List[str] = generate_attacker_ips(attacker_count)
        
        # Initialize packet collection
        all_packets: List[Packet] = []
        
        victim_mac = victim_mac if victim_mac is not None else get_mac_address()
        
        if verbose:
            print("=" * 80)
            print("LAYER 3 - SYN FLOOD ATTACK PROFILE")
            print("=" * 80)
            print(f"\n🎯 Attack Configuration:")
            print(f"   Victim IP: {victim_ip}")
            print(f"   Target Port: {dest_port}")
            print(f"   Attacker Count: {attacker_count}")
            print(f"   Attack Duration: {attack_duration_ms}ms")
            print(f"   Interval between SYNs: {interval_ms:.2f}ms")
            print(f"   Base Timestamp: {timestamp:.2f}")
            print(f"\n⚔️  Launching attack...")
            print("-" * 80)
        
        # ====================================================================
        # MAIN ATTACK LOOP - Generate SYN flood from each attacker
        # ====================================================================
        
        current_time = timestamp
        
        for i, attacker_ip in enumerate(attacker_ips):
            # Generate incomplete TCP connection (SYN + SYN/ACK only)
            attack_packets, _, _ = not_ended_tcp_connection(
                source_ip=attacker_ip,
                dest_ip=victim_ip,
                dest_port=dest_port,
                ts=current_time,
                server_mac=victim_mac
            )
            all_packets.extend(attack_packets)
            
            # Progress indicator (every 10% or every 10 attackers for small counts)
            if verbose and (i + 1) % max(1, attacker_count // 10) == 0:
                progress = ((i + 1) / attacker_count) * 100
                print(f"   [{progress:5.1f}%] Attacker {i + 1}/{attacker_count}: {attacker_ip}")
            
            # Advance time for next attack
            current_time += interval_sec
        
        # ====================================================================
        # SUMMARY AND STATISTICS
        # ====================================================================
        
        self.packets_generated = len(all_packets)
        
        if verbose:
            print("\n" + "=" * 80)
            print("ATTACK COMPLETE")
            print("=" * 80)
            print(f"\n📊 Attack Statistics:")
            print(f"   Total packets generated: {len(all_packets)}")
            print(f"   SYN packets: {attacker_count}")
            print(f"   SYN/ACK responses: {attacker_count}")
            print(f"   Unique source IPs: {attacker_count}")
            print(f"   Half-open connections created: {attacker_count}")
            
            if all_packets:
                duration = all_packets[-1].time - all_packets[0].time
                print(f"\n⏱  Timing:")
                print(f"   Attack duration: {duration:.3f} seconds ({duration * 1000:.1f}ms)")
                print(f"   Packet rate: {len(all_packets) / duration:.2f} packets/second")
                print(f"   SYN rate: {attacker_count / duration:.2f} SYNs/second")
            
            print("\n" + "=" * 80)
        
        return all_packets
    
    def syn_flood_multiport(
        self,
        victim_ip: str,
        ports: List[int],
        base_timestamp: Optional[float] = None,
        attackers_per_port: int = 50,
        verbose: bool = True
    ) -> List[Packet]:
        """
        Generate a SYN Flood attack targeting multiple ports.
        
        This variant simulates a port scanning combined with SYN flood,
        where attackers target multiple services on the same server.
        
        Args:
            victim_ip: Target server IP address
            ports: List of target ports
            base_timestamp: Base timestamp (current time if None)
            attackers_per_port: Number of attackers per port (default: 50)
            verbose: Print progress information
        
        Returns:
            List[Packet]: All attack packets
        
        Example:
            >>> profile = SynFloodProfile()
            >>> # Attack common web ports
            >>> packets = profile.syn_flood_multiport(
            ...     victim_ip="10.0.0.1",
            ...     ports=[80, 443, 8080, 8443],
            ...     attackers_per_port=25
            ... )
        """
        timestamp = base_timestamp if base_timestamp is not None else get_current_timestamp()
        all_packets: List[Packet] = []
        
        if verbose:
            print("=" * 80)
            print("LAYER 3 - MULTI-PORT SYN FLOOD ATTACK")
            print("=" * 80)
            print(f"\n🎯 Attack Configuration:")
            print(f"   Victim IP: {victim_ip}")
            print(f"   Target Ports: {ports}")
            print(f"   Attackers per port: {attackers_per_port}")
            print(f"   Total attackers: {len(ports) * attackers_per_port}")
            print("\n" + "=" * 80)
        
        current_time = timestamp
        victim_mac = get_mac_address()
        for port in ports:
            if verbose:
                print(f"\n⚔️  Attacking port {port}...")
            
            port_packets = self.syn_flood_attack(
                victim_ip=victim_ip,
                base_timestamp=current_time,
                attacker_count=attackers_per_port,
                dest_port=port,
                attack_duration_ms=200.0,
                verbose=False,
                victim_mac=victim_mac
            )
            
            all_packets.extend(port_packets)
            
            if verbose:
                print(f"   ✓ Port {port}: {len(port_packets)} packets")
            
            # Small gap between port attacks
            current_time = port_packets[-1].time + 0.1
        
        self.packets_generated = len(all_packets)
        
        if verbose:
            print("\n" + "=" * 80)
            print(f"✅ MULTI-PORT ATTACK COMPLETE: {len(all_packets)} total packets")
            print("=" * 80)
        
        return all_packets
