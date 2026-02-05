"""
Profiles Layer 3 - High-Level User Behavior Profiles
=====================================================

This module provides the highest level of abstraction, orchestrating multiple Layer 2
primitives to simulate complete user behavior profiles. It generates large volumes of
realistic network traffic from simple input parameters.

Architecture:
    Layer 3 (Profiles) - User behavior simulation [THIS MODULE]
        ↓ orchestrates
    Layer 2 (Abstraction) - Complete conversations (HTTP2ndLayer, DNS2ndLayer)
        ↓ uses
    Layer 1 (Atomic) - Individual packets (DNSFirstLayer, primitivas_capa_1)

Dependencies:
    - HTTP2ndLayer: High-level HTTP web navigation
    - primitivas_capa_1: TCP/HTTP Layer 1 primitives (Capa1Generador)
    - scapy: Packet manipulation and PCAP export
    - faker: Realistic data generation
    - typing: Type hints

Type Safety:
    All functions use Python 3.8+ type hints (PEP 484)
"""

from ansible.module_utils.dfir.network.second_layer.http import http_web_navigation
from ansible.module_utils.dfir.network.first_layer.tcp_primitives import Layer1Generator
from ansible.module_utils.dfir.network.utils import get_domain_name, get_mac_address, get_public_ip
from typing import List, Optional, Tuple
from ansible.module_utils.dfir.network.utils import *
import random
import subprocess
import sys

try:
    from scapy.all import Packet, wrpcap
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import Packet, wrpcap


def generate_realistic_content_list() -> List[Tuple[str, Optional[int]]]:
    """
    Generate a realistic list of web content types and sizes.
    
    Returns:
        List[Tuple[str, Optional[int]]]: Content types with sizes
        Format: [("html", size), ("css", size), ...]
    
    Note:
        Simulates typical web page resource loading:
        - HTML page (main content)
        - CSS stylesheets (1-2)
        - JavaScript files (1-3)
        - Optional JSON (API calls)
    """
    content = []
    
    # Main HTML page (always present)
    html_size = random.randint(1500, 5000)
    content.append(("html", html_size))
    
    # CSS files (1-2 stylesheets)
    num_css = random.randint(1, 2)
    for _ in range(num_css):
        css_size = random.randint(300, 800)
        content.append(("css", css_size))
    
    # JavaScript files (1-3 scripts)
    num_js = random.randint(1, 3)
    for _ in range(num_js):
        js_size = random.randint(500, 1500)
        content.append(("js", js_size))
    
    # Optional JSON (API calls) - 50% chance
    if random.random() < 0.5:
        json_size = random.randint(200, 600)
        content.append(("json", json_size))
    
    return content


def calculate_reading_delay() -> float:
    """
    Calculate a realistic delay between page visits.
    
    Returns:
        float: Delay in seconds
    
    Note:
        Simulates human reading/interaction time between web pages.
        Range: 5-30 seconds (normal browsing behavior)
    """
    return random.uniform(5.0, 30.0)


# ============================================================================
# LAYER 3 PROFILES CLASS
# ============================================================================

class Layer3Profile:
    """
    Layer 3 (Profiles) - High-level user behavior simulation.
    
    This class provides the highest level of abstraction for generating
    network traffic. It orchestrates Layer 2 primitives to create complex
    scenarios that simulate real user behavior.
    
    Attributes:
        layer1_generator: Layer 1 packet generator (for reference)
        packets_generated: Running count of packets generated
    
    Usage:
        >>> profile = Layer3Profile()
        >>> packets = profile.web_browsing_profile(
        ...     host_count=5,
        ...     client_source_ip="192.168.1.100",
        ...     dns_srvr_ip="8.8.8.8"
        ... )
        >>> print(f"Generated {len(packets)} packets")
    """
    
    def __init__(self) -> None:
        """
        Initialize the Layer 3 profile generator.
        
        Creates instances of required lower-layer generators and initializes
        internal state tracking.
        """
        self.layer1_generator = Layer1Generator()
        self.packets_generated: int = 0
    
    def web_browsing_profile(
        self,
        host_count: int,
        client_source_ip: str,
        dns_srvr_ip: str,
        base_timestamp: Optional[float] = None,
        dest_port: int = 80,
        verbose: bool = True
    ) -> List[Packet]:
        """
        Generate a complete web browsing profile with multiple unique sessions.
        
        This high-level primitive simulates a normal user browsing multiple
        different websites over time. Each session includes:
        - DNS resolution
        - TCP connection establishment
        - HTTP request/response exchanges
        - TCP connection termination
        
        This creates essential "noise" traffic for forensic scenarios, making
        the PCAP more realistic and challenging for analysis.
        
        Args:
            host_count: Number of unique websites to visit
                       Determines the volume of traffic generated
            client_source_ip: Client IP address (fixed for this profile)
            dns_srvr_ip: DNS server IP address (e.g., "8.8.8.8")
            base_timestamp: Base timestamp for first session (current time if None)
            dest_port: HTTP port (default: 80)
            verbose: Print progress information (default: True)
        
        Returns:
            List[Packet]: All packets from all sessions combined in chronological order
        
        Traffic Pattern:
            For each of host_count iterations:
            1. Generate unique domain name (via Faker)
            2. Generate realistic server IP (via Faker)
            3. Generate realistic content list (HTML + CSS + JS + JSON)
            4. Call http_web_navigation (Layer 2)
            5. Add realistic reading delay (5-30 seconds)
        
        Packet Count Estimation:
            Per session (typical):
            - DNS: 2 packets (query + response)
            - TCP handshake: 3 packets
            - HTTP exchanges: 2N packets (where N = number of content items)
            - TCP close: 4 packets
            - Total per session: ~15-25 packets (average ~20)
            
            Total for profile: host_count × 20 (approximate)
        
        Example:
            >>> profile = Layer3Profile()
            >>> # Simulate user visiting 10 different websites
            >>> packets = profile.web_browsing_profile(
            ...     host_count=10,
            ...     client_source_ip="192.168.1.100",
            ...     dns_srvr_ip="8.8.8.8"
            ... )
            >>> print(f"Generated {len(packets)} packets")
            Generated 203 packets
            
            >>> # Export to PCAP
            >>> from scapy.all import wrpcap
            >>> wrpcap("user_browsing.pcap", packets)
        
        Forensic Use Cases:
            - Generate baseline "normal" traffic for comparison
            - Create noise to hide attack traffic
            - Simulate multiple concurrent users
            - Test IDS/IPS with high-volume traffic
            - Validate timeline reconstruction capabilities
        
        Note:
            All timestamps are carefully managed to ensure monotonic progression.
            Each session starts after the previous one completes, with realistic
            delays simulating user reading/interaction time.
        """
        # Initialize timestamp
        timestamp: float = base_timestamp if base_timestamp is not None else now_ts()
        
        # Initialize packet collection
        all_packets: List[Packet] = []
        
        # Statistics tracking
        total_sessions_successful: int = 0
        total_sessions_failed: int = 0
        
        if verbose:
            print("=" * 80)
            print("LAYER 3 - WEB BROWSING PROFILE GENERATION")
            print("=" * 80)
            print(f"\n📊 Profile Configuration:")
            print(f"   Websites to visit: {host_count}")
            print(f"   Client IP: {client_source_ip}")
            print(f"   DNS Server: {dns_srvr_ip}")
            print(f"   HTTP Port: {dest_port}")
            print(f"   Base timestamp: {timestamp:.2f}")
            print("\n" + "-" * 80)
        
        # ====================================================================
        # MAIN LOOP - Generate traffic for each website visit
        # ====================================================================
        
        for i in range(host_count):
            if verbose:
                print(f"\n[SESSION {i+1}/{host_count}] Generating web navigation...")
            
            # ================================================================
            # STEP 1: Generate unique domain name
            # ================================================================
            domain_name: str = get_domain_name()
            server_mac = get_mac_address()
            client_mac = get_mac_address()
            
            if verbose:
                print(f"  ✓ Generated domain: {domain_name}")
            
            # ================================================================
            # STEP 2: Generate realistic content list
            # ================================================================
            contents: List[Tuple[str, Optional[int]]] = generate_realistic_content_list()
            
            if verbose:
                content_summary = ", ".join([f"{ct[0]}({ct[1]}B)" for ct in contents])
                print(f"  ✓ Content plan: {content_summary}")
            
            # ================================================================
            # STEP 3: Call Layer 2 - Complete web navigation
            # ================================================================
            try:
                session_packets, success, resolved_ip = http_web_navigation(
                    host=domain_name,
                    source_ip=client_source_ip,
                    dns_srvr_ip=dns_srvr_ip,
                    contents=contents,
                    base_timestamp=timestamp,
                    dest_port=dest_port,
                    client_mac=client_mac,
                    server_mac=server_mac
                )
                
                # Add packets to collection
                all_packets.extend(session_packets)
                
                if success:
                    total_sessions_successful += 1
                    if verbose:
                        print(f"  ✓ Navigation successful: {len(session_packets)} packets")
                        print(f"    → DNS resolved to: {resolved_ip}")
                else:
                    total_sessions_failed += 1
                    if verbose:
                        print(f"  ✗ Navigation failed: {len(session_packets)} packets")
                
                # ============================================================
                # STEP 5: Calculate next session timestamp
                # ============================================================
                # Ensure monotonic progression with realistic delay
                last_packet_time = session_packets[-1].time
                reading_delay = calculate_reading_delay()
                
                timestamp = last_packet_time + reading_delay
                
                if verbose:
                    print(f"  ⏱  Reading delay: {reading_delay:.1f}s")
                    print(f"  ⏱  Next session starts at: T+{timestamp - base_timestamp if base_timestamp else 0:.1f}s")
            
            except Exception as e:
                if verbose:
                    print(f"  ❌ ERROR generating session: {e}")
                total_sessions_failed += 1
                # Add small delay even on failure
                timestamp += 1.0
        
        # ====================================================================
        # SUMMARY AND STATISTICS
        # ====================================================================
        
        self.packets_generated = len(all_packets)
        
        if verbose:
            print("\n" + "=" * 80)
            print("PROFILE GENERATION COMPLETE")
            print("=" * 80)
            print(f"\n📈 Generation Statistics:")
            print(f"   Total packets generated: {len(all_packets)}")
            print(f"   Successful sessions: {total_sessions_successful}")
            print(f"   Failed sessions: {total_sessions_failed}")
            print(f"   Average packets/session: {len(all_packets) / host_count:.1f}")
            
            if all_packets:
                duration = all_packets[-1].time - all_packets[0].time
                print(f"   Total duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
                print(f"   Packet rate: {len(all_packets) / duration:.2f} packets/second")
            
            # Packet type breakdown
            dns_packets = sum(1 for p in all_packets if 'DNS' in str(p))
            tcp_packets = sum(1 for p in all_packets if 'TCP' in str(p))
            http_packets = sum(1 for p in all_packets if 'Raw' in str(p) and b'HTTP' in bytes(p))
            
            print(f"\n📊 Packet Type Breakdown:")
            print(f"   DNS packets: {dns_packets} ({dns_packets/len(all_packets)*100:.1f}%)")
            print(f"   TCP packets: {tcp_packets} ({tcp_packets/len(all_packets)*100:.1f}%)")
            print(f"   HTTP packets: {http_packets} ({http_packets/len(all_packets)*100:.1f}%)")
            
            print("\n" + "=" * 80)
        
        return all_packets
    
    def web_browsing_profile_multiple_users(
        self,
        user_count: int,
        hosts_per_user: int,
        client_base_ip: str = "192.168.1.",
        dns_srvr_ip: str = "8.8.8.8",
        base_timestamp: Optional[float] = None,
        verbose: bool = True
    ) -> List[Packet]:
        """
        Generate web browsing profiles for multiple concurrent users.
        
        This advanced primitive simulates multiple users browsing simultaneously,
        with interleaved traffic for maximum realism.
        
        Args:
            user_count: Number of concurrent users to simulate
            hosts_per_user: Websites each user visits
            client_base_ip: Base IP for clients (e.g., "192.168.1.")
            dns_srvr_ip: DNS server IP
            base_timestamp: Base timestamp
            verbose: Print progress
        
        Returns:
            List[Packet]: All packets from all users, chronologically interleaved
        
        Example:
            >>> profile = Layer3Profile()
            >>> # Simulate 5 users, each visiting 3 websites
            >>> packets = profile.web_browsing_profile_multiple_users(
            ...     user_count=5,
            ...     hosts_per_user=3
            ... )
        """
        timestamp = base_timestamp if base_timestamp is not None else now_ts()
        all_packets: List[Packet] = []
        
        if verbose:
            print("=" * 80)
            print("LAYER 3 - MULTIPLE USERS WEB BROWSING PROFILE")
            print("=" * 80)
            print(f"\n👥 Simulating {user_count} concurrent users")
            print(f"🌐 Each user visits {hosts_per_user} websites")
            print(f"📊 Expected total packets: ~{user_count * hosts_per_user * 20}")
            print("\n" + "=" * 80)
        
        # Generate traffic for each user
        for user_num in range(user_count):
            user_ip = f"{client_base_ip}{100 + user_num}"
            
            if verbose:
                print(f"\n👤 User {user_num + 1}/{user_count} ({user_ip})")
            
            # Generate browsing profile for this user
            user_packets = self.web_browsing_profile(
                host_count=hosts_per_user,
                client_source_ip=user_ip,
                dns_srvr_ip=dns_srvr_ip,
                base_timestamp=timestamp,
                verbose=False  # Suppress individual session logs
            )
            
            all_packets.extend(user_packets)
            
            if verbose:
                print(f"  ✓ Generated {len(user_packets)} packets")
            
            # Stagger user start times for realism
            if user_num < user_count - 1:
                timestamp = user_packets[-1].time + random.uniform(2.0, 10.0)
        
        # Sort all packets by timestamp for chronological order
        all_packets.sort(key=lambda p: p.time)
        
        if verbose:
            print("\n" + "=" * 80)
            print(f"✅ COMPLETE: {len(all_packets)} packets from {user_count} users")
            print("=" * 80)
        
        return all_packets


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def main() -> None:
    """
    Demonstration of Layer 3 profile generation.
    
    This function demonstrates:
    1. Single user browsing 5 websites
    2. Multiple users (3 users) browsing concurrently
    
    Output: Two PCAP files for analysis
    """
    print("=" * 80)
    print("LAYER 3 PROFILES - DEMONSTRATION")
    print("=" * 80)
    
    # Initialize Layer 3 profile generator
    perfil = Layer3Profile()
    
    # ========================================================================
    # SCENARIO 1: Single User Browsing Profile
    # ========================================================================
    print("\n" + "=" * 80)
    print("SCENARIO 1: Single User Browsing 5 Websites")
    print("=" * 80)
    
    packets_single_user = perfil.web_browsing_profile(
        host_count=5,
        client_source_ip="192.168.1.100",
        dns_srvr_ip="8.8.8.8",
        verbose=True
    )
    
    # Export to PCAP
    filename_single = "navegacion_web_perfil_single_user.pcap"
    wrpcap(filename_single, packets_single_user)
    
    print(f"\n✅ PCAP exported: {filename_single}")
    print(f"📊 Total packets: {len(packets_single_user)}")
    
    # ========================================================================
    # SCENARIO 2: Multiple Users Browsing Profile
    # ========================================================================
    print("\n\n" + "=" * 80)
    print("SCENARIO 2: Multiple Users (3 users, 3 websites each)")
    print("=" * 80)
    
    packets_multiple_users = perfil.web_browsing_profile_multiple_users(
        user_count=3,
        hosts_per_user=3,
        client_base_ip="192.168.1.",
        dns_srvr_ip="8.8.8.8",
        verbose=True
    )
    
    # Export to PCAP
    filename_multiple = "navegacion_web_perfil_multiple_users.pcap"
    wrpcap(filename_multiple, packets_multiple_users)
    
    print(f"\n✅ PCAP exported: {filename_multiple}")
    print(f"📊 Total packets: {len(packets_multiple_users)}")

if __name__ == "__main__":
    main()

