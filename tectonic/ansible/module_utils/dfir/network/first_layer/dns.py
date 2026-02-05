"""
DNS First Layer Primitives - Atomic DNS Packet Generation
==========================================================

This module provides low-level primitives for creating individual DNS query and
response packets with forensic accuracy.

Dependencies:
    - scapy: DNS packet construction
    - typing: Type hints

Type Safety:
    All functions use Python 3.8+ type hints (PEP 484)
"""

from typing import Optional
from ansible.module_utils.dfir.network.utils import *
import subprocess
import sys

try:
    from scapy.all import IP, UDP, Ether, DNS, DNSQR, DNSRR, Packet
except ImportError:
    # Auto-install scapy if not available
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import IP, UDP, Ether, DNS, DNSQR, DNSRR, Packet

# ============================================================================
# DNS LAYER 1 PRIMITIVES
# ============================================================================

def create_dns_query(
    ip_src: str,
    ip_dst: str,
    qname: str,
    qtype: str = "A",
    port_src: Optional[int] = None,
    mac_src: Optional[str] = None,
    mac_dst: Optional[str] = None,
    transaction_id: Optional[int] = None,
    seed: Optional[int] = None,
    index: int = 0
) -> Packet:
    """
    Create a DNS query packet (Client -> DNS Server).
    
    This primitive constructs a complete DNS query packet with Ethernet, IP,
    UDP, and DNS layers. The query can be for various record types (A, AAAA,
    MX, TXT, etc.).
    
    Args:
        ip_src: Source IP address (client)
        ip_dst: Destination IP address (DNS server)
        qname: Domain name to query (e.g., "example.com")
        qtype: DNS query type (default: "A")
               Common values: "A", "AAAA", "MX", "TXT", "NS", "CNAME"
        port_src: Source port (random ephemeral port if None)
        mac_src: Source MAC address (random if None)
        mac_dst: Destination MAC address (random if None)
        transaction_id: DNS transaction ID (random if None)
        seed: Base seed for reproducibility (None for random behavior)
        index: Index offset to derive unique sub-seeds
    
    Returns:
        Packet: Complete DNS query packet ready for transmission
    
    DNS Query Structure:
        - Opcode: QUERY (0)
        - Recursion desired: True
        - Question: qname with specified qtype
    
    Example:
        >>> query = create_dns_query(
        ...     ip_src="192.168.1.100",
        ...     ip_dst="8.8.8.8",
        ...     qname="www.example.com",
        ...     qtype="A",
        ...     seed=42
        ... )
        >>> print(query[DNS].qd.qname)
        b'www.example.com.'
    """
    # Initialize parameters with optional seeding
    if mac_src is None:
        mac_src = get_mac_address(seed=seed, index=index)
    if mac_dst is None:
        mac_dst = get_mac_address(seed=seed, index=index + 1)
    
    sport: int = port_src if port_src is not None else rnd_port(seed=seed, index=index + 2)
    txid: int = transaction_id if transaction_id is not None else generate_dns_transaction_id(seed=seed, index=index + 3)
    
    # Ensure domain name ends with '.' for DNS format
    if not qname.endswith('.'):
        qname = qname + '.'
    
    # Construct DNS query packet
    query_packet = (
        Ether(src=mac_src, dst=mac_dst) /
        IP(src=ip_src, dst=ip_dst) /
        UDP(sport=sport, dport=get_dns_port()) /
        DNS(
            id=txid,
            rd=1,  # Recursion desired
            qd=DNSQR(qname=qname, qtype=qtype)
        )
    )
    
    return query_packet


def create_dns_response(
    query_packet: Packet,
    answer_ip: Optional[str] = None,
    success: bool = True,
    ttl: int = 300,
    mac_src: str = "02:00:00:00:00:02",
    mac_dst: str = "02:00:00:00:00:01"
) -> Packet:
    """
    Create a DNS response packet (DNS Server -> Client).
    
    This primitive constructs a DNS response packet that corresponds to a given
    query. It automatically extracts transaction ID, ports, IPs, and query details
    from the original query packet.
    
    Args:
        query_packet: The original DNS query packet to respond to
        answer_ip: IP address to return in the answer (required if success=True)
        success: Whether the query was successful (default: True)
                 If False, returns NXDOMAIN (name does not exist)
        ttl: Time-to-live for the DNS record in seconds (default: 300)
        mac_src: Source MAC address (default: server MAC)
        mac_dst: Destination MAC address (default: client MAC)
    
    Returns:
        Packet: Complete DNS response packet
    
    DNS Response Structure:
        - Transaction ID: Copied from query
        - QR: 1 (response)
        - AA: 1 (authoritative answer)
        - RD: Copied from query
        - RA: 1 (recursion available)
        - RCODE: 0 (success) or 3 (NXDOMAIN)
    
    Response Codes:
        - 0 (NOERROR): Successful query
        - 3 (NXDOMAIN): Domain does not exist
    
    Example:
        >>> query = create_dns_query("192.168.1.100", "8.8.8.8", "example.com")
        >>> response = create_dns_response(
        ...     query,
        ...     answer_ip="93.184.216.34",
        ...     success=True
        ... )
        >>> print(response[DNS].an.rdata)
        '93.184.216.34'
    """
    # Validate input
    if success and answer_ip is None:
        raise ValueError("answer_ip is required when success=True")
    
    # Extract information from query
    query_dns = query_packet[DNS]
    query_qname = query_dns.qd.qname
    query_qtype = query_dns.qd.qtype
    query_id = query_dns.id
    
    # Extract network information (reverse src/dst)
    ip_src = query_packet[IP].dst
    ip_dst = query_packet[IP].src
    port_src = get_dns_port()
    port_dst = query_packet[UDP].sport
    
    # Build DNS response
    if success:
        # Successful response with answer
        response_packet = (
            Ether(src=mac_src, dst=mac_dst) /
            IP(src=ip_src, dst=ip_dst) /
            UDP(sport=port_src, dport=port_dst) /
            DNS(
                id=query_id,
                qr=1,  # Response
                aa=1,  # Authoritative answer
                rd=query_dns.rd,  # Copy from query
                ra=1,  # Recursion available
                rcode=0,  # No error
                qd=DNSQR(qname=query_qname, qtype=query_qtype),
                an=DNSRR(
                    rrname=query_qname,
                    type=query_qtype,
                    rdata=answer_ip,
                    ttl=ttl
                )
            )
        )
    else:
        # Failed response (NXDOMAIN)
        response_packet = (
            Ether(src=mac_src, dst=mac_dst) /
            IP(src=ip_src, dst=ip_dst) /
            UDP(sport=port_src, dport=port_dst) /
            DNS(
                id=query_id,
                qr=1,  # Response
                aa=1,  # Authoritative answer
                rd=query_dns.rd,  # Copy from query
                ra=1,  # Recursion available
                rcode=3,  # NXDOMAIN (name does not exist)
                qd=DNSQR(qname=query_qname, qtype=query_qtype)
                # No answer section for NXDOMAIN
            )
        )
    
    return response_packet


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def main() -> None:
    """
    Demonstration of DNS Layer 1 primitives.
    
    This function creates:
    1. Successful DNS query/response for A record
    2. Failed DNS query/response (NXDOMAIN)
    3. AAAA record query (IPv6)
    
    Output: Individual packet details and optional PCAP export
    """
    print("=" * 80)
    print("DNS First Layer Primitives - Demonstration")
    print("=" * 80)
    
    from scapy.all import wrpcap
    import time
    
    all_packets = []
    
    # ========================================================================
    # SCENARIO 1: Successful DNS A Record Query
    # ========================================================================
    print("\n[1] Creating Successful DNS A Record Query")
    print("-" * 80)
    
    query_a = create_dns_query(
        ip_src="192.168.1.100",
        ip_dst="8.8.8.8",
        qname="www.example.com",
        qtype="A"
    )
    query_a.time = time.time()
    all_packets.append(query_a)
    
    print(f"  ✓ Query created:")
    print(f"    - Domain: {query_a[DNS].qd.qname.decode()}")
    print(f"    - Type: A (IPv4)")
    print(f"    - Transaction ID: {query_a[DNS].id}")
    print(f"    - Source: {query_a[IP].src}:{query_a[UDP].sport}")
    print(f"    - Destination: {query_a[IP].dst}:{query_a[UDP].dport}")
    
    response_a = create_dns_response(
        query_packet=query_a,
        answer_ip="93.184.216.34",
        success=True,
        ttl=3600
    )
    response_a.time = query_a.time + 0.015  # 15ms RTT
    all_packets.append(response_a)
    
    print(f"  ✓ Response created:")
    print(f"    - Answer: {response_a[DNS].an.rdata}")
    print(f"    - TTL: {response_a[DNS].an.ttl} seconds")
    print(f"    - RCODE: {response_a[DNS].rcode} (NOERROR)")
    
    # ========================================================================
    # SCENARIO 2: Failed DNS Query (NXDOMAIN)
    # ========================================================================
    print("\n[2] Creating Failed DNS Query (NXDOMAIN)")
    print("-" * 80)
    
    query_nxdomain = create_dns_query(
        ip_src="192.168.1.100",
        ip_dst="8.8.8.8",
        qname="nonexistent-domain-12345.com",
        qtype="A"
    )
    query_nxdomain.time = response_a.time + 1.0
    all_packets.append(query_nxdomain)
    
    print(f"  ✓ Query created:")
    print(f"    - Domain: {query_nxdomain[DNS].qd.qname.decode()}")
    print(f"    - Type: A (IPv4)")
    
    response_nxdomain = create_dns_response(
        query_packet=query_nxdomain,
        success=False
    )
    response_nxdomain.time = query_nxdomain.time + 0.020
    all_packets.append(response_nxdomain)
    
    print(f"  ✓ Response created:")
    print(f"    - RCODE: {response_nxdomain[DNS].rcode} (NXDOMAIN)")
    print(f"    - No answer section (domain does not exist)")
    
    # ========================================================================
    # SCENARIO 3: AAAA Record Query (IPv6)
    # ========================================================================
    print("\n[3] Creating DNS AAAA Record Query (IPv6)")
    print("-" * 80)
    
    query_aaaa = create_dns_query(
        ip_src="192.168.1.100",
        ip_dst="8.8.8.8",
        qname="www.google.com",
        qtype="AAAA"
    )
    query_aaaa.time = response_nxdomain.time + 0.5
    all_packets.append(query_aaaa)
    
    print(f"  ✓ Query created:")
    print(f"    - Domain: {query_aaaa[DNS].qd.qname.decode()}")
    print(f"    - Type: AAAA (IPv6)")
    
    response_aaaa = create_dns_response(
        query_packet=query_aaaa,
        answer_ip="2607:f8b0:4004:0c07::0067",  # Example IPv6
        success=True
    )
    response_aaaa.time = query_aaaa.time + 0.018
    all_packets.append(response_aaaa)
    
    print(f"  ✓ Response created:")
    print(f"    - Answer: {response_aaaa[DNS].an.rdata}")
    
    # ========================================================================
    # EXPORT TO PCAP
    # ========================================================================
    print("\n" + "=" * 80)
    print("PCAP Generation Summary")
    print("=" * 80)
    
    output_filename = "dns_layer1_primitives.pcap"
    wrpcap(output_filename, all_packets)
    
    print(f"\n✅ PCAP file generated: {output_filename}")
    print(f"📊 Total packets: {len(all_packets)}")
    print(f"🔍 Analysis recommendations:")
    print(f"   - Open in Wireshark: wireshark {output_filename}")
    print(f"   - Apply filter: udp.port == 53")
    print(f"   - Check DNS queries: dns.flags.response == 0")
    print(f"   - Check DNS responses: dns.flags.response == 1")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

