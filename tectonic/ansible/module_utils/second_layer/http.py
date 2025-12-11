"""
HTTP Second Layer - High-Level HTTP Navigation Primitive
=========================================================


This module provides high-level primitives for complete web browsing sessions,
orchestrating DNS resolution, TCP connections, and HTTP exchanges.

Dependencies:
    - primitivas_capa_1: TCP/HTTP Layer 1 primitives (Capa1Generador)
    - DNS2ndLayer: DNS communication primitives
    - scapy: Packet manipulation
    - faker: Realistic content generation
    - typing: Type hints

Type Safety:
    All functions use Python 3.8+ type hints (PEP 484)
"""

from ansible.module_utils.first_layer.tcp_primitives import Layer1Generator
from ansible.module_utils.second_layer.dns import dns_communication
from ansible.module_utils.second_layer.not_ended_tcp_connection import not_ended_tcp_connection
from ansible.module_utils.utils import *
from ansible.module_utils.utils import get_random_time, get_text, get_random_title, get_company_name, get_sentence
from typing import List, Optional, Tuple
import random
import subprocess
import sys

try:
    from scapy.all import Packet, wrpcap
except ImportError:
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


def generate_html_content(size_bytes: Optional[int] = None, seed: Optional[int] = None, index: int = 0) -> str:
    """
    Generate realistic HTML content for HTTP responses.
    
    Args:
        size_bytes: Desired size in bytes (random if None)
        seed: Base seed for reproducibility
        index: Index offset for unique values
    
    Returns:
        str: HTML content
    """
    if seed is not None:
        seed_random(seed, index)
    
    if size_bytes is None:
        size_bytes = random.randint(500, 5000)
    
    # Generate base HTML structure with seeded data
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{get_random_title(seed=seed, index=index)}</title>
    <link rel="stylesheet" href="/css/style.css">
</head>
<body>
    <header>
        <h1>{get_company_name(seed=seed, index=index + 1)}</h1>
        <nav>
            <a href="/">Inicio</a>
            <a href="/productos">Productos</a>
            <a href="/contacto">Contacto</a>
        </nav>
    </header>
    <main>
        <article>
            <h2>{get_sentence(seed=seed, index=index + 2)}</h2>
            <p>{get_text(max_nb_chars=200, seed=seed, index=index + 3)}</p>
        </article>
    </main>
</body>
</html>"""
    
    # Pad to desired size if needed
    current_size = len(html.encode('utf-8'))
    if current_size < size_bytes:
        padding = "<!-- " + get_text(max_nb_chars=size_bytes - current_size - 10, seed=seed, index=index + 4) + " -->"
        html = html.replace("</body>", f"{padding}</body>")
    
    return html


def generate_css_content(size_bytes: Optional[int] = None, seed: Optional[int] = None, index: int = 0) -> str:
    """
    Generate realistic CSS content.
    
    Args:
        size_bytes: Desired size in bytes (random if None)
        seed: Base seed for reproducibility
        index: Index offset for unique values
    
    Returns:
        str: CSS content
    """
    if seed is not None:
        seed_random(seed, index)
    
    if size_bytes is None:
        size_bytes = random.randint(100, 1000)
    
    css = """/* Estilos principales */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 0;
    background-color: #f4f4f4;
}
header {
    background-color: #333;
    color: white;
    padding: 1rem;
}
nav a {
    color: white;
    margin: 0 1rem;
    text-decoration: none;
}
main {
    padding: 2rem;
}
"""
    
    # Pad to desired size
    current_size = len(css.encode('utf-8'))
    if current_size < size_bytes:
        css += f"\n/* {get_text(max_nb_chars=size_bytes - current_size - 10, seed=seed, index=index)} */"
    
    return css


def generate_js_content(size_bytes: Optional[int] = None, seed: Optional[int] = None, index: int = 0) -> str:
    """
    Generate realistic JavaScript content.
    
    Args:
        size_bytes: Desired size in bytes (random if None)
        seed: Base seed for reproducibility
        index: Index offset for unique values
    
    Returns:
        str: JavaScript content
    """
    if seed is not None:
        seed_random(seed, index)
    
    if size_bytes is None:
        size_bytes = random.randint(100, 800)
    
    js = """// Main application script
document.addEventListener('DOMContentLoaded', function() {
    console.log('Page loaded');
    
    // Navigation handler
    const links = document.querySelectorAll('nav a');
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            console.log('Navigating to:', this.href);
        });
    });
});
"""
    
    # Pad to desired size
    current_size = len(js.encode('utf-8'))
    if current_size < size_bytes:
        js += f"\n// {get_text(max_nb_chars=size_bytes - current_size - 10, seed=seed, index=index)}"
    
    return js


# ============================================================================
# HTTP LAYER 2 PRIMITIVE - HIGH-LEVEL WEB NAVIGATION
# ============================================================================

def http_web_navigation(
    host: str,
    source_ip: str,
    dns_srvr_ip: str = "8.8.8.8",
    srvr_ip: Optional[str] = None,
    contents: Optional[List[Tuple[str, Optional[int], Optional[str]]]] = None,
    base_timestamp: Optional[float] = None,
    dest_port: int = 80,
    client_mac: Optional[str] = None,
    server_mac: Optional[str] = None,
    seed: Optional[int] = None,
    index: int = 0
) -> Tuple[List[Packet], bool, Optional[str]]:
    """
    Complete HTTP web navigation primitive with DNS resolution and arbitrary payloads.
    
    This high-level primitive orchestrates a complete web browsing session:
    1. DNS resolution for the host
    2. TCP three-way handshake
    3. HTTP GET request and response(s) for main page and resources
    4. TCP connection termination
    
    Supports both standard web content (HTML/CSS/JS) and arbitrary binary payloads,
    making it suitable for simulating file downloads including malware samples.
    
    Args:
        host: Domain name to navigate to (e.g., "www.example.com")
        source_ip: Client IP address
        dns_srvr_ip: DNS server IP address (e.g., "8.8.8.8")
        contents: List of content tuples (content_type, size, [optional_payload])
                 Format variations:
                 - ("html", 1000): Auto-generate HTML
                 - ("css", 200): Auto-generate CSS
                 - ("binary", 2048, "base64_encoded_data"): Custom binary payload
                 - ("custom", None, "raw_payload_string"): Custom arbitrary payload
                 If None, defaults to basic HTML page
        base_timestamp: Base timestamp (current time if None)
        dest_port: Destination port (default: 80 for HTTP)
        client_mac: Client MAC address (random if None)
        server_mac: Server MAC address (random if None)
        seed: Base seed for reproducibility (None for random behavior)
        index: Index offset to derive unique sub-seeds
    
    Returns:
        Tuple containing:
            - List[Packet]: All packets (DNS + TCP + HTTP)
            - bool: Success status (False if DNS failed)
            - Optional[str]: Resolved IP address (None if DNS failed)
    
    Example:
        >>> # Standard web content
        >>> packets, success, ip = http_web_navigation(
        ...     host="www.example.com",
        ...     source_ip="192.168.1.100",
        ...     dns_srvr_ip="8.8.8.8",
        ...     contents=[("html", 1500), ("css", 300)],
        ...     seed=42
        ... )
        >>> # Download fake binary with custom payload
        >>> packets, success, ip = http_web_navigation(
        ...     host="malware.com",
        ...     source_ip="192.168.1.100",
        ...     dns_srvr_ip="8.8.8.8",
        ...     contents=[("binary", 2048, "SGVsbG8gV29ybGQh")],  # base64
        ...     seed=42
        ... )
    """
    # Initialize
    timestamp = base_timestamp if base_timestamp is not None else get_current_timestamp()
    all_packets: List[Packet] = []
    
    # Default contents if not specified
    if contents is None:
        contents = [("html", 1000)]
    
    # Initialize Layer 1 generator with seed
    generator = Layer1Generator(seed=seed, index=index)
    
    # ========================================================================
    # STEP 1: DNS Resolution
    # ========================================================================
    resolver_ip = dns_srvr_ip if dns_srvr_ip else "8.8.8.8"
    dns_packets, resolved_ip = dns_communication(
        domain=host,
        source_ip=source_ip,
        dns_server_ip=resolver_ip,
        return_ip=srvr_ip,
        expected_result="Success",
        base_timestamp=timestamp,
        seed=seed,
        index=index + 10000
    )
    all_packets.extend(dns_packets)
    
    # Update timestamp to after DNS resolution
    current_time = get_random_time(dns_packets[-1].time, distribution="uniform", seed=seed, index=index + 10001)

    # ========================================================================
    # STEP 2: TCP Three-Way Handshake
    # ========================================================================
    tcp_handshake, seq_client, seq_server = generator.start_complete_connection(
        source_ip=source_ip,
        dest_ip=resolved_ip,
        dest_port=dest_port,
        ts=current_time,
        client_mac=client_mac,
        server_mac=server_mac
    )
    all_packets.extend(tcp_handshake)
    
    # Update current time
    current_time = get_random_time(tcp_handshake[-1].time, distribution="uniform", seed=seed, index=index + 10002)
    
    # ========================================================================
    # STEP 3: HTTP Exchange for Each Content Type
    # ========================================================================
    # tcp_handshake = [SYN (client), SYN/ACK (server), ACK (client)]
    # IMPORTANT: These are used to track the last packet from EACH SIDE
    # for sequence number calculation in add_packet_in_progress
    last_client_packet = tcp_handshake[-1]  # ACK from client (last client packet)
    last_server_packet = tcp_handshake[1]   # SYN/ACK from server (last server packet before data)
    
    for i, content_tuple in enumerate(contents):
        # Unpack content tuple (handle both old and new formats)
        if len(content_tuple) == 2:
            content_type, size = content_tuple
            custom_payload = None
        else:  # len >= 3
            content_type, size, custom_payload = content_tuple[0], content_tuple[1], content_tuple[2]
        
        # Determine URI and content based on type
        if custom_payload is not None:
            # Use custom payload (e.g., for binary downloads or arbitrary content)
            content = custom_payload
            uri = f"/wanna{i}.exe" if content_type.lower() == "binary" else f"/resource{i}"
            # For arbitrary payloads, use application/octet-stream
            mime_type = "application/octet-stream" if content_type.lower() in ["binary", "custom"] else "text/plain"
        elif content_type.lower() == "html":
            uri = "/" if i == 0 else f"/page{i}.html"
            content = generate_html_content(size, seed=seed, index=index + 20000 + i * 100)
            mime_type = "text/html; charset=UTF-8"
        elif content_type.lower() == "css":
            uri = f"/css/style{i if i > 0 else ''}.css"
            content = generate_css_content(size, seed=seed, index=index + 20000 + i * 100)
            mime_type = "text/css"
        elif content_type.lower() == "js" or content_type.lower() == "javascript":
            uri = f"/js/script{i if i > 0 else ''}.js"
            content = generate_js_content(size, seed=seed, index=index + 20000 + i * 100)
            mime_type = "application/javascript"
        elif content_type.lower() == "json":
            uri = f"/api/data{i if i > 0 else ''}.json"
            content = f'{{"status": "success", "data": "{get_text(max_nb_chars=size if size else 100, seed=seed, index=index + 20000 + i * 100)}"}}'
            mime_type = "application/json"
        else:
            # Generic content
            uri = f"/resource{i}.txt"
            content = get_text(max_nb_chars=size if size else 200, seed=seed, index=index + 20000 + i * 100)
            mime_type = "text/plain"
        
        # HTTP GET Request
        http_get = generator.http_get_request(
            previous_packet=last_server_packet,
            host=host,
            uri=uri,
            ts=current_time,
            client_mac=client_mac,
            server_mac=server_mac
        )
        all_packets.append(http_get)
        current_time = get_random_time(http_get.time, distribution="uniform", seed=seed, index=index + 30000 + i * 10)
        
        # HTTP 200 Response
        http_response = generator.http_200_response(
            previous_packet=http_get,
            html_content=content,
            ts=current_time,
            client_mac=client_mac,
            server_mac=server_mac
        )
        all_packets.append(http_response)
        current_time = get_random_time(http_response.time, distribution="uniform", seed=seed, index=index + 30001 + i * 10)
        
        # Update packet references
        last_client_packet = http_get
        last_server_packet = http_response
    
    # ========================================================================
    # STEP 4: TCP Connection Termination
    # ========================================================================
    tcp_close = generator.finalize_connection(
        last_client_packet=last_client_packet,
        last_server_packet=last_server_packet,
        ts=current_time,
        client_mac=client_mac,
        server_mac=server_mac
    )
    all_packets.extend(tcp_close)
    
    return all_packets, True, resolved_ip


def http_web_navigation_failed(
    host: str,
    source_ip: str,
    dns_srvr_ip: str = "8.8.8.8",
    failure_type: str = "DNS",
    base_timestamp: Optional[float] = None,
    client_mac: Optional[str] = None,
    server_mac: Optional[str] = None
) -> Tuple[List[Packet], bool]:
    """
    Simulate a failed web navigation attempt.
    
    Args:
        host: Domain name to attempt navigation
        source_ip: Client IP address
        dns_srvr_ip: DNS server IP
        failure_type: Type of failure
                     - "DNS": DNS resolution fails (NXDOMAIN)
                     - "Timeout": Connection timeout (SYN only)
        base_timestamp: Base timestamp
    
    Returns:
        Tuple containing:
            - List[Packet]: Packets generated before failure
            - bool: Always False (failure)
    
    Example:
        >>> # Simulate DNS failure
        >>> packets, success = http_web_navigation_failed(
        ...     host="nonexistent.com",
        ...     source_ip="192.168.1.100",
        ...     dns_srvr_ip="8.8.8.8",
        ...     failure_type="DNS"
        ... )
    """
    timestamp = base_timestamp if base_timestamp is not None else get_current_timestamp()
    all_packets: List[Packet] = []
    
    if failure_type == "DNS":
        # DNS fails with NXDOMAIN
        dns_packets, _ = dns_communication(
            domain=host,
            source_ip=source_ip,
            dns_server_ip=dns_srvr_ip,
            expected_result="Not Exists",
            base_timestamp=timestamp
        )
        all_packets.extend(dns_packets)
        
    elif failure_type == "Timeout":
        # DNS succeeds but TCP connection fails
        dns_packets, resolved_ip = dns_communication(
            domain=host,
            source_ip=source_ip,
            dns_server_ip=dns_srvr_ip,
            expected_result="Success",
            base_timestamp=timestamp
        )
        all_packets.extend(dns_packets)
        
        # Only SYN packet (no response = timeout)
        # Use Layer 2 not_ended_tcp_connection primitive
        syn_packets, _, _ = not_ended_tcp_connection(
            source_ip=source_ip,
            dest_ip=resolved_ip,
            dest_port=80,
            ts=get_random_time(dns_packets[-1].time, distribution="uniform"),
            client_mac=client_mac,
            server_mac=server_mac
        )
        # Only add the SYN packet (simulate no response)
        all_packets.append(syn_packets[0])
    
    return all_packets, False


# ============================================================================
# DEMONSTRATION AND TESTING
# ============================================================================

def main() -> None:
    """
    Demonstration of HTTP Layer 2 high-level web navigation primitive.
    
    This function creates:
    1. Successful web navigation (HTML only)
    2. Complete web page load (HTML + CSS + JS)
    3. Failed navigation (DNS failure)
    
    Output: Complete web browsing session PCAP file
    """
    print("=" * 80)
    print("HTTP Second Layer - High-Level Web Navigation Demonstration")
    print("=" * 80)
    
    all_packets: List[Packet] = []
    
    # ========================================================================
    # SCENARIO 1: Simple Web Navigation (HTML Only)
    # ========================================================================
    print("\n[1] Simple Web Navigation (HTML Only)")
    print("-" * 80)
    
    packets_simple, success_simple, ip_simple = http_web_navigation(
        host="www.example.com",
        source_ip="192.168.1.100",
        dns_srvr_ip="8.8.8.8",
        contents=[("html", 1500)]
    )
    all_packets.extend(packets_simple)
    
    print(f"  ✓ Host: www.example.com")
    print(f"  ✓ Client: 192.168.1.100")
    print(f"  ✓ DNS Resolver: 8.8.8.8")
    print(f"  ✓ Success: {success_simple}")
    print(f"  ✓ Resolved IP: {ip_simple}")
    print(f"  ✓ Total packets: {len(packets_simple)}")
    print(f"    - DNS: 2 packets")
    print(f"    - TCP Handshake: 3 packets")
    print(f"    - HTTP Exchange: 2 packets")
    print(f"    - TCP Close: 4 packets")
    
    # ========================================================================
    # SCENARIO 2: Complete Web Page Load (HTML + CSS + JS)
    # ========================================================================
    print("\n[2] Complete Web Page Load (HTML + CSS + JS)")
    print("-" * 80)
    
    packets_complete, success_complete, ip_complete = http_web_navigation(
        host="www.social-network.com",
        source_ip="192.168.1.100",
        dns_srvr_ip="8.8.8.8",
        contents=[
            ("html", 2000),
            ("css", 500),
            ("js", 800),
            ("json", 300)
        ],
        base_timestamp=packets_simple[-1].time + 2.0
    )
    all_packets.extend(packets_complete)
    
    print(f"  ✓ Host: www.social-network.com")
    print(f"  ✓ Success: {success_complete}")
    print(f"  ✓ Resolved IP: {ip_complete}")
    print(f"  ✓ Total packets: {len(packets_complete)}")
    print(f"  ✓ Content types: HTML, CSS, JS, JSON")
    print(f"  ✓ HTTP exchanges: {len([p for p in packets_complete if 'HTTP' in str(p)])}")
    
    # ========================================================================
    # SCENARIO 3: Failed Navigation (DNS Failure)
    # ========================================================================
    print("\n[3] Failed Web Navigation (DNS NXDOMAIN)")
    print("-" * 80)
    
    packets_failed, success_failed = http_web_navigation_failed(
        host="nonexistent-site-12345.com",
        source_ip="192.168.1.100",
        dns_srvr_ip="8.8.8.8",
        failure_type="DNS",
        base_timestamp=packets_complete[-1].time + 1.0
    )
    all_packets.extend(packets_failed)
    
    print(f"  ✓ Host: nonexistent-site-12345.com")
    print(f"  ✓ Success: {success_failed}")
    print(f"  ✓ Failure type: DNS NXDOMAIN")
    print(f"  ✓ Total packets: {len(packets_failed)}")
    print(f"  ✓ Note: Only DNS packets (no TCP/HTTP)")
    
    # ========================================================================
    # SCENARIO 4: Connection Timeout
    # ========================================================================
    print("\n[4] Failed Web Navigation (Connection Timeout)")
    print("-" * 80)
    
    packets_timeout, success_timeout = http_web_navigation_failed(
        host="timeout-test.com",
        source_ip="192.168.1.100",
        dns_srvr_ip="8.8.8.8",
        failure_type="Timeout",
        base_timestamp=packets_failed[-1].time + 1.0
    )
    all_packets.extend(packets_timeout)
    
    print(f"  ✓ Host: timeout-test.com")
    print(f"  ✓ Success: {success_timeout}")
    print(f"  ✓ Failure type: Connection Timeout")
    print(f"  ✓ Total packets: {len(packets_timeout)}")
    print(f"  ✓ Note: DNS + SYN only (no SYN/ACK)")
    
    # ========================================================================
    # EXPORT TO PCAP
    # ========================================================================
    print("\n" + "=" * 80)
    print("PCAP Generation Summary")
    print("=" * 80)
    
    output_filename = "http_layer2_navigation.pcap"
    wrpcap(output_filename, all_packets)
    
    print(f"\n✅ PCAP file generated: {output_filename}")
    print(f"📊 Total packets: {len(all_packets)}")
    print(f"📊 Scenarios: 4 (2 successful, 2 failed)")
    print(f"🔍 Analysis recommendations:")
    print(f"   - Open in Wireshark: wireshark {output_filename}")
    print(f"   - DNS filter: dns")
    print(f"   - HTTP filter: http")
    print(f"   - TCP streams: tcp.stream eq N (where N = 0, 1, 2...)")
    print(f"   - Follow HTTP stream: Right-click → Follow → HTTP Stream")
    print(f"   - Check DNS resolutions before HTTP traffic")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()

