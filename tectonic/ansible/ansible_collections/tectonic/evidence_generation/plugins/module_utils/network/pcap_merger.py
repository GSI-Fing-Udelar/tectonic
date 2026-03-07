"""
PCAP Merging Utility using mergecap

This utility provides timestamp-based PCAP merging using the mergecap tool.
mergecap automatically sorts packets by timestamp, unlike simple concatenation.

Usage in Ansible modules:
    from ansible.module_utils.pcap_merger import merge_pcap_with_mergecap
    
    merge_pcap_with_mergecap(module, output_path, packets, output_dir)
"""

import os
import subprocess
import tempfile
import sys

try:
    from scapy.all import wrpcap
except ImportError:
    # Auto-install scapy if not available
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'scapy'])
    from scapy.all import wrpcap


def merge_pcap_with_mergecap(module, output_path, packets, output_dir=None):
    """
    Merge packets with existing PCAP file using mergecap (timestamp-based sorting).
    
    Args:
        module: AnsibleModule instance (for error reporting)
        output_path: Path to output PCAP file
        packets: List of Scapy packets to merge
        output_dir: Directory for temporary files (defaults to same as output_path)
    
    Features:
        - Automatic mergecap installation if not found
        - Timestamp-based packet sorting (not simple append)
        - Automatic cleanup of temporary files
        - Atomic file replacement (via .tmp file)
    
    Returns:
        None (raises module.fail_json on error)
    """
    # Determine output directory
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(output_path))
    
    # Create output directory if needed
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # If output file doesn't exist, just write packets directly
    if not os.path.exists(output_path):
        wrpcap(output_path, packets)
        return
    
    # Merge with existing PCAP using mergecap
    temp_fd, temp_path = tempfile.mkstemp(suffix='.pcap', dir=output_dir)
    os.close(temp_fd)
    
    try:
        # Write new packets to temporary file
        wrpcap(temp_path, packets)
        
        # Check if mergecap is available
        mergecap_check = subprocess.run(
            ['which', 'mergecap'],
            capture_output=True,
            text=True
        )
        
        if mergecap_check.returncode != 0:
            # mergecap not found, try to install it
            install_result = subprocess.run(
                ['sudo', 'apt-get', 'install', '-y', 'wireshark-common'],
                capture_output=True,
                text=True,
                timeout=60
            )
            if install_result.returncode != 0:
                module.fail_json(
                    msg="mergecap not found and automatic installation failed. "
                        "Please install wireshark-common package manually: "
                        "sudo apt-get install wireshark-common"
                )
        
        # Merge PCAPs using mergecap (sorts by timestamp automatically)
        merge_result = subprocess.run(
            ['mergecap', '-w', output_path + '.tmp', output_path, temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if merge_result.returncode == 0:
            # Replace original with merged file
            os.replace(output_path + '.tmp', output_path)
        else:
            module.fail_json(
                msg=f"mergecap failed: {merge_result.stderr}"
            )
            
    finally:
        # Clean up temporary files
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(output_path + '.tmp'):
            os.remove(output_path + '.tmp')
