"""
DNS Second Layer - High-Level DNS Communication Primitive
==========================================================
This module provides high-level primitives for complete DNS conversations,
abstracting away the low-level packet construction details.

Dependencies:
    - DNSFirstLayer: Atomic DNS packet primitives
    - scapy: Packet manipulation
    - typing: Type hints

Type Safety:
    All functions use Python 3.8+ type hints (PEP 484)
"""

from ansible.module_utils.first_layer.dns import create_dns_query, create_dns_response
from typing import List, Optional, Tuple
import time
import random
import subprocess
import sys
from ansible.module_utils.utils import seed_random, get_public_ip

try:
    from scapy.all import Packet, wrpcap
except ImportError:
    # Auto-install scapy if not available
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import Packet, wrpcap


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_current_timestamp() -> float:
    """
    Get the current Unix timestamp with microsecond precision.
    
    Returns:
        float: Current timestamp in seconds since epoch
    """
    return time.time()


def generate_realistic_ip(seed: Optional[int] = None, index: int = 0) -> str:
    """
    Generate a realistic public IP address for DNS responses.
    
    Args:
        seed: Base seed for reproducibility
        index: Index offset for unique values
    
    Returns:
        str: Random public IP address (avoiding private ranges)
    """
    if seed is not None:
        # Use get_public_ip with seeding for consistent IPs
        return get_public_ip(seed=seed, index=index)
    
    # Fallback to original implementation for unseeded calls
    # Generate public IP (avoiding 10.x, 172.16-31.x, 192.168.x)
    seed_random(seed, index)
    first_octet = random.choice([8, 20, 40, 93, 104, 151, 185, 216])
    second_octet = random.randint(1, 254)
    third_octet = random.randint(1, 254)
    fourth_octet = random.randint(1, 254)
    
    return f"{first_octet}.{second_octet}.{third_octet}.{fourth_octet}"


# ============================================================================
# DNS LAYER 2 PRIMITIVE - HIGH-LEVEL COMMUNICATION
# ============================================================================

def dns_communication(
    domain: str,
    source_ip: str,
    dns_server_ip: str,
    expected_result: str = "Success",
    return_ip: Optional[str] = None,
    base_timestamp: Optional[float] = None,
    qtype: str = "A",
    rtt_ms: float = 15.0,
    seed: Optional[int] = None,
    index: int = 0
) -> Tuple[List[Packet], Optional[str]]:
    """
    Complete DNS communication primitive (Query + Response).
    
    This high-level primitive encapsulates a complete DNS conversation,
    handling both the query and response with appropriate timing and
    response codes based on the desired outcome.
    
    Args:
        domain: Domain name to query (e.g., "www.example.com")
        source_ip: Client IP address (resolver)
        dns_server_ip: DNS server IP address (e.g., "8.8.8.8")
        expected_result: Desired outcome for the query
                        - "Success": Successful resolution (NOERROR)
                        - "Failed": Server error/timeout (SERVFAIL)
                        - "Not Exists": Domain does not exist (NXDOMAIN)
        return_ip: IP address to return in successful response
                  If None, generates a random realistic IP
        base_timestamp: Base timestamp for the query (current time if None)
        qtype: DNS query type (default: "A" for IPv4)
        rtt_ms: Round-trip time in milliseconds (default: 15.0)
        seed: Base seed for reproducibility (None for random behavior)
        index: Index offset to derive unique sub-seeds
    
    Returns:
        Tuple containing:
            - List[Packet]: [Query, Response] packets
            - Optional[str]: Resolved IP address (None if resolution failed)
    
    DNS Communication Flow:
        1. Client sends DNS query to DNS server
        2. DNS server responds based on expected_result:
           - Success: Returns IP address (RCODE=0)
           - Not Exists: Returns NXDOMAIN (RCODE=3)
           - Failed: Returns empty response or server failure
    
    Example:
        >>> # Successful DNS resolution with seeding
        >>> packets, ip = dns_communication(
        ...     domain="www.example.com",
        ...     source_ip="192.168.1.100",
        ...     dns_server_ip="8.8.8.8",
        ...     expected_result="Success",
        ...     return_ip="93.184.216.34",
        ...     seed=42
        ... )
        >>> print(f"Resolved to: {ip}")
        Resolved to: 93.184.216.34
    """
    # Initialize timestamp
    timestamp: float = base_timestamp if base_timestamp is not None else get_current_timestamp()
    
    # Prepare result containers
    packets: List[Packet] = []
    resolved_ip: Optional[str] = None
    
    # ========================================================================
    # STEP 1: Create DNS Query
    # ========================================================================
    query_packet = create_dns_query(
        ip_src=source_ip,
        ip_dst=dns_server_ip,
        qname=domain,
        qtype=qtype,
        seed=seed,
        index=index
    )
    query_packet.time = timestamp
    packets.append(query_packet)
    
    # ========================================================================
    # STEP 2: Create DNS Response based on desired outcome
    # ========================================================================
    
    if expected_result == "Success":
        # Successful resolution
        if return_ip is None:
            return_ip = generate_realistic_ip(seed=seed, index=index + 100)
        
        response_packet = create_dns_response(
            query_packet=query_packet,
            answer_ip=return_ip,
            success=True,
            ttl=300
        )
        resolved_ip = return_ip
        
    elif expected_result == "Not Exists":
        # Domain does not exist (NXDOMAIN)
        response_packet = create_dns_response(
            query_packet=query_packet,
            success=False
        )
        resolved_ip = None
        
    elif expected_result == "Failed":
        # Server failure or no response
        # For forensic purposes, we'll create a response with empty answer
        response_packet = create_dns_response(
            query_packet=query_packet,
            success=False
        )
        resolved_ip = None
        
    else:
        raise ValueError(
            f"Invalid expected_result: {expected_result}. "
            "Valid options: 'Success', 'Not Exists', 'Failed'"
        )
    
    # Set response timestamp (query time + RTT)
    response_packet.time = timestamp + (rtt_ms / 1000.0)
    packets.append(response_packet)
    
    return packets, resolved_ip


def dns_communication_multiple(
    domains: List[str],
    source_ip: str,
    dns_server_ip: str,
    base_timestamp: Optional[float] = None,
    spacing_ms: float = 100.0,
    seed: Optional[int] = None
) -> Tuple[List[Packet], dict]:
    """
    Perform multiple DNS queries with realistic spacing.
    
    This primitive simulates realistic DNS behavior where a client performs
    multiple queries (e.g., when loading a webpage with multiple external
    resources from different domains).
    
    Args:
        domains: List of domain names to query
        source_ip: Client IP address
        dns_server_ip: DNS server IP address
        base_timestamp: Base timestamp (current time if None)
        spacing_ms: Time spacing between queries in milliseconds
        seed: Base seed for reproducibility (None for random behavior)
    
    Returns:
        Tuple containing:
            - List[Packet]: All query/response packets
            - dict: Mapping of domain -> resolved IP (or None if failed)
    
    Example:
        >>> domain_list = ["cdn.example.com", "api.example.com", "www.example.com"]
        >>> packets, resolutions = dns_communication_multiple(
        ...     domains=domain_list,
        ...     source_ip="192.168.1.100",
        ...     dns_server_ip="8.8.8.8",
        ...     seed=42
        ... )
        >>> for domain, ip in resolutions.items():
        ...     print(f"{domain} -> {ip}")
    """
    timestamp = base_timestamp if base_timestamp is not None else get_current_timestamp()
    all_packets: List[Packet] = []
    resolutions: dict = {}
    
    for i, domain in enumerate(domains):
        # Calculate timestamp for this query
        query_time = timestamp + (i * spacing_ms / 1000.0)
        
        # Perform DNS query with unique index for each domain
        packets, resolved_ip = dns_communication(
            domain=domain,
            source_ip=source_ip,
            dns_server_ip=dns_server_ip,
            expected_result="Success",
            base_timestamp=query_time,
            seed=seed,
            index=i * 1000  # Use large offset for each domain
        )
        
        all_packets.extend(packets)
        resolutions[domain] = resolved_ip
    
    return all_packets, resolutions


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def main() -> None:
    """
    Demonstration of DNS Layer 2 high-level primitives.
    
    This function creates:
    1. Successful DNS resolution
    2. Failed DNS resolution (NXDOMAIN)
    3. Multiple DNS queries
    
    Output: Complete DNS conversation PCAP file
    """
    print("=" * 80)
    print("DNS Second Layer - High-Level Communication Demonstration")
    print("=" * 80)
    
    all_packets: List[Packet] = []
    
    # ========================================================================
    # SCENARIO 1: Successful DNS Resolution
    # ========================================================================
    print("\n[1] Successful DNS Resolution")
    print("-" * 80)
    
    packets_success, ip_success = dns_communication(
        domain="www.example.com",
        source_ip="192.168.1.100",
        dns_server_ip="8.8.8.8",
        expected_result="Success",
        return_ip="93.184.216.34"
    )
    all_packets.extend(packets_success)
    
    print(f"  ✓ Domain: www.example.com")
    print(f"  ✓ Client: 192.168.1.100")
    print(f"  ✓ DNS Server: 8.8.8.8")
    print(f"  ✓ Result: Success")
    print(f"  ✓ Resolved IP: {ip_success}")
    print(f"  ✓ Packets generated: {len(packets_success)}")
    
    # ========================================================================
    # SCENARIO 2: Failed DNS Resolution (NXDOMAIN)
    # ========================================================================
    print("\n[2] Failed DNS Resolution (Domain Not Found)")
    print("-" * 80)
    
    packets_nxdomain, ip_nxdomain = dns_communication(
        domain="nonexistent-domain-12345.com",
        source_ip="192.168.1.100",
        dns_server_ip="8.8.8.8",
        expected_result="Not Exists",
        base_timestamp=packets_success[-1].time + 1.0
    )
    all_packets.extend(packets_nxdomain)
    
    print(f"  ✓ Domain: nonexistent-domain-12345.com")
    print(f"  ✓ Result: NXDOMAIN")
    print(f"  ✓ Resolved IP: {ip_nxdomain}")
    print(f"  ✓ Packets generated: {len(packets_nxdomain)}")
    
    # ========================================================================
    # SCENARIO 3: Multiple DNS Queries
    # ========================================================================
    print("\n[3] Multiple DNS Queries (Simulating Web Page Load)")
    print("-" * 80)
    
    domain_list = [
        "www.example.com",
        "cdn.example.com",
        "api.example.com",
        "static.example.com"
    ]
    
    packets_multiple, resolutions = dns_communication_multiple(
        domains=domain_list,
        source_ip="192.168.1.100",
        dns_server_ip="8.8.8.8",
        base_timestamp=packets_nxdomain[-1].time + 2.0,
        spacing_ms=50.0
    )
    all_packets.extend(packets_multiple)
    
    print(f"  ✓ Domains queried: {len(domain_list)}")
    for domain, ip in resolutions.items():
        print(f"    - {domain} -> {ip}")
    print(f"  ✓ Total packets: {len(packets_multiple)}")
    
    # ========================================================================
    # SCENARIO 4: DNS Resolution with Server Failure
    # ========================================================================
    print("\n[4] DNS Resolution with Server Failure")
    print("-" * 80)
    
    packets_fail, ip_fail = dns_communication(
        domain="timeout-test.com",
        source_ip="192.168.1.100",
        dns_server_ip="8.8.8.8",
        expected_result="Failed",
        base_timestamp=packets_multiple[-1].time + 1.0
    )
    all_packets.extend(packets_fail)
    
    print(f"  ✓ Domain: timeout-test.com")
    print(f"  ✓ Result: Server Failure")
    print(f"  ✓ Resolved IP: {ip_fail}")
    print(f"  ✓ Packets generated: {len(packets_fail)}")
    
    # ========================================================================
    # EXPORT TO PCAP
    # ========================================================================
    print("\n" + "=" * 80)
    print("PCAP Generation Summary")
    print("=" * 80)
    
    output_filename = "dns_layer2_communication.pcap"
    wrpcap(output_filename, all_packets)
    
    print(f"\n✅ PCAP file generated: {output_filename}")
    print(f"📊 Total packets: {len(all_packets)}")
    print(f"📊 DNS conversations: 4 scenarios")
    print(f"🔍 Analysis recommendations:")
    print(f"   - Open in Wireshark: wireshark {output_filename}")
    print(f"   - Apply filter: dns")
    print(f"   - Check successful queries: dns.flags.rcode == 0")
    print(f"   - Check NXDOMAIN: dns.flags.rcode == 3")
    print(f"   - Follow DNS stream for each conversation")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

