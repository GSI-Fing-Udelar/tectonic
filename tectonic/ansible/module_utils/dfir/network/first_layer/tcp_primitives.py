from ansible.module_utils.dfir.network.utils import *
from typing import Optional
import subprocess
import sys

try:
    from scapy.all import IP, TCP, Ether, Raw, wrpcap
except ImportError:
    # Auto-install scapy if not available
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import IP, TCP, Ether, Raw, wrpcap

class Layer1Generator:
    """
    Class for generating Layer 1 primitives (individual packets) and
    protocol modules (TCP and HTTP).
    
    Supports deterministic seeding for reproducible packet generation.
    """

    def __init__(self, seed: Optional[int] = None, index: int = 0):
        """
        Initialize Layer 1 Generator.
        
        Args:
            seed: Base seed for reproducibility (None for random behavior)
            index: Index offset to derive unique sub-seeds
        """
        self.seed = seed
        self.index = index
        
        # Generic MAC address storage (assumes there is a client and a server)
        self.client_mac = get_mac_address(seed=seed, index=index)
        self.server_mac = get_mac_address(seed=seed, index=index + 1)
        
        # List to collect all generated packets in order
        self.packets = []

    # --- TCP MODULE (Handshake and Sequence Management) ---

    def _create_base_layers(
        self, source_ip, dest_ip, source_port, dest_port, 
        client_mac=None, server_mac=None, **kwargs
    ):
        client_mac = client_mac or self.client_mac
        server_mac = server_mac or self.server_mac
        return Ether(src=client_mac, dst=server_mac) / \
            IP(src=source_ip, dst=dest_ip) / \
            TCP(sport=source_port, dport=dest_port, **kwargs)
    
    def start_complete_connection(self, source_ip, dest_ip, source_port=None, dest_port=443, seq=None, ts=None, client_mac=None, server_mac=None):
        """
        Generates a complete 3-Way TCP Handshake sequence (SYN, SYN/ACK, ACK).
        Returns the list of 3 packets and the final sequence numbers.
        """
        tcp_packets = []
        
        # Use seeded random generation if seed is set
        sport = source_port if source_port else rnd_port(seed=self.seed, index=self.index + 10)
        seq_c = seq if seq else rnd_seq(seed=self.seed, index=self.index + 11)

        # 1. SYN Packet (Client -> Server)
        syn = self._create_base_layers(source_ip, dest_ip, sport, dest_port, flags="S", seq=seq_c, client_mac=client_mac, server_mac=server_mac)
        syn.time = ts if ts else now_ts()
        tcp_packets.append(syn)

        # 2. SYN/ACK Packet (Server -> Client)
        # The server increments the client's ACK (seq_c + 1) and starts its own sequence
        seq_s = rnd_seq(seed=self.seed, index=self.index + 12)
        synack = self._create_base_layers(dest_ip, source_ip, dest_port, sport, flags="SA", seq=seq_s, ack=seq_c + 1, client_mac=client_mac, server_mac=server_mac)
        synack[Ether].src, synack[Ether].dst = self.server_mac, self.client_mac # MAC exchange
        synack.time = get_random_time(syn.time, distribution="uniform", seed=self.seed, index=self.index + 13)
        tcp_packets.append(synack)

        # 3. Final ACK Packet (Client -> Server)
        # The client increments the server's ACK (seq_s + 1) and maintains its sequence
        ack = self._create_base_layers(source_ip, dest_ip, sport, dest_port, flags="A", seq=seq_c + 1, ack=seq_s + 1)
        ack.time = get_random_time(synack.time, distribution="uniform", seed=self.seed, index=self.index + 14)
        tcp_packets.append(ack)

        # Return the packets and the connection state for use in future calls
        return tcp_packets, seq_c + 1, seq_s + 1

    def finalize_connection(self, last_client_packet, last_server_packet, ts=None, client_mac=None, server_mac=None):
        """
        Generates the connection termination sequence (FIN, ACK, FIN, ACK).
        Receives the two last packets to calculate sequences correctly.
        """
        # Extract sequences and ports from the last packets
        seq_c = last_client_packet[TCP].seq + len(last_client_packet[Raw].load) if Raw in last_client_packet else last_client_packet[TCP].seq
        ack_c = last_client_packet[TCP].ack
        sport = last_client_packet[TCP].sport
        dport = last_client_packet[TCP].dport

        seq_s = last_server_packet[TCP].seq + len(last_server_packet[Raw].load) if Raw in last_server_packet else last_server_packet[TCP].seq
        ack_s = last_server_packet[TCP].ack

        fin_packets = []
        base_time = ts if ts else now_ts()

        # 1. FIN (Client -> Server)
        fin1 = self._create_base_layers(last_client_packet[IP].src, last_client_packet[IP].dst, sport, dport,
                                     flags="FA", seq=seq_c, ack=ack_c, client_mac=client_mac, server_mac=server_mac)
        fin1.time = base_time
        fin_packets.append(fin1)

        # 2. Server ACK (Server -> Client)
        ack1 = self._create_base_layers(last_server_packet[IP].src, last_server_packet[IP].dst, dport, sport,
                                     flags="A", seq=seq_s, ack=seq_c + 1, client_mac=client_mac, server_mac=server_mac)
        ack1.time = get_random_time(fin1.time, distribution="uniform", seed=self.seed, index=self.index + 20)
        fin_packets.append(ack1)

        # 3. Server FIN (Server -> Client)
        fin2 = self._create_base_layers(last_server_packet[IP].src, last_server_packet[IP].dst, dport, sport,
                                     flags="FA", seq=seq_s, ack=seq_c + 1, client_mac=client_mac, server_mac=server_mac)
        fin2[Ether].src, fin2[Ether].dst = self.server_mac, self.client_mac
        fin2.time = get_random_time(ack1.time, distribution="uniform", seed=self.seed, index=self.index + 21)
        fin_packets.append(fin2)

        # 4. Final Client ACK (Client -> Server)
        ack2 = self._create_base_layers(last_client_packet[IP].src, last_client_packet[IP].dst, sport, dport,
                                     flags="A", seq=seq_c + 1, ack=seq_s + 1, client_mac=client_mac, server_mac=server_mac)
        ack2.time = get_random_time(fin2.time, distribution="uniform", seed=self.seed, index=self.index + 22)
        fin_packets.append(ack2)

        return fin_packets

    def add_packet_in_progress(self, previous_packet, payload, flags="PA", ts=None, client_mac=None, server_mac=None):
        """
        Adds a packet with payload to an active TCP communication.
        Automatically calculates sequences and ACKs.
        
        CRITICAL: TCP sequence/ACK handling
        ===================================
        For any new packet, we need:
        1. Source/Dest: Reverse of previous packet (opposite direction)
        2. SEQ: Must be the ACK value from the previous packet (what was expected)
        3. ACK: Must acknowledge all bytes received from the other side:
                = previous_seq + len(previous_payload)
        """
        # Get previous packet details
        prev_src = previous_packet[IP].src
        prev_dst = previous_packet[IP].dst
        prev_seq = previous_packet[TCP].seq
        prev_ack = previous_packet[TCP].ack if previous_packet[TCP].ack is not None else 0
        prev_payload_len = len(previous_packet[Raw].load) if Raw in previous_packet else 0
        syn_len = 1 if previous_packet[TCP].flags & 0x02 else 0
        fin_len = 1 if previous_packet[TCP].flags & 0x01 else 0
        prev_seg_len = prev_payload_len + syn_len + fin_len
        
        effective_client_mac = client_mac or self.client_mac
        effective_server_mac = server_mac or self.server_mac

        # Determine if previous packet was from Client or Server
        is_client_packet = previous_packet[Ether].src == effective_client_mac
        
        ip_src = prev_dst
        ip_dst = prev_src
        sport = previous_packet[TCP].dport
        dport = previous_packet[TCP].sport
        
        new_seq = prev_ack
        new_ack = prev_seq + prev_seg_len

        new_packet = self._create_base_layers(ip_src, ip_dst, sport, dport, flags=flags, seq=new_seq, ack=new_ack, client_mac=effective_client_mac, server_mac=effective_server_mac)
        
        if is_client_packet:
            new_packet[Ether].src, new_packet[Ether].dst = effective_server_mac, effective_client_mac
        else:
            new_packet[Ether].src, new_packet[Ether].dst = effective_client_mac, effective_server_mac
    
        new_packet = new_packet / Raw(load=payload)
        new_packet.time = ts if ts else now_ts()

        return new_packet

    # --- APPLICATION PROTOCOL PRIMITIVES (Layers 5+) ---
    
    def http_get_request(self, previous_packet, host, uri="/", ts=None, client_mac=None, server_mac=None):
        """
        Generates a simple HTTP GET request.
        Uses add_packet_in_progress to maintain TCP synchronization.
        """
        # HTTP GET content (payload)
        http_get_payload = (
            f"GET {uri} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"User-Agent: {rnd_user_agent(seed=self.seed, index=self.index + 30)}\r\n"
            f"Accept: text/html,application/xhtml+xml\r\n"
            f"Connection: keep-alive\r\n"
            f"\r\n"
        ).encode('utf-8')

        # Call the TCP primitive for the new packet
        http_packet = self.add_packet_in_progress(
            previous_packet, 
            http_get_payload, 
            flags="PA", # Push + ACK
            ts=ts,
            client_mac=client_mac,
            server_mac=server_mac
        )
        return http_packet

    def http_200_response(self, previous_packet, html_content="<html>OK Response.</html>", ts=None, client_mac=None, server_mac=None):
        """
        Generates an HTTP 200 OK response from the server.
        """
        html_bytes = html_content.encode('utf-8')
        
        http_resp_payload = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: text/html; charset=UTF-8\r\n"
            f"Content-Length: {len(html_bytes)}\r\n"
            f"\r\n"
        ).encode('utf-8') + html_bytes
        
        http_resp_packet = self.add_packet_in_progress(
            previous_packet, 
            http_resp_payload, 
            flags="PA", 
            ts=ts,
            client_mac=client_mac,
            server_mac=server_mac
        )
        return http_resp_packet