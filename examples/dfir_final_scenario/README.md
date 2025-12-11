# DFIR Final Scenario - Unified WannaCry Attack Simulation

## Overview

Complete Digital Forensics and Incident Response (DFIR) training scenario that simulates a real WannaCry ransomware attack. This scenario combines **network traffic simulation** with **filesystem forensics** to provide comprehensive hands-on training.

## Features

### 🌐 Network Attack Simulation
- **SMB Exploitation**: Realistic EternalBlue-style attack traffic
- **Malware Download**: HTTP-based payload delivery (5 WannaCry components)
- **C2 Communication**: Command & Control plain-text communication
- **Output**: Complete PCAP file for Wireshark analysis

### 💾 Filesystem Forensics
- **Forensic Disk Image**: 1GB ext4 image with infected filesystem
- **150 Victim Files**: DOCX, PDF, XLSX, JPG, TXT with realistic content
- **Real Encryption**: AES-256-CBC encryption (not simulated)
- **File Deletion**: 25% of files deleted (forensically recoverable)
- **PE Executables**: WannaCry malware binaries with proper MZ headers
- **Ransom Notes**: Authentic WannaCry ransom message

### 🎯 Forensic Challenge
- **Hidden Flag**: `flagsinha.txt.WNCRY` (encrypted + deleted)
- **Challenge**: Students must recover the deleted file using Autopsy and decrypt it
- **Skill Practice**: File carving, data recovery, cryptographic analysis

## Architecture

### Tectonic Integration

This scenario is fully integrated with Tectonic's automation framework:

```
tectonic deploy
    ↓
cli.py → core.py → ansible.py
    ↓
ansible.py sets environment variables:
    - ANSIBLE_LIBRARY = "tectonic/ansible/library"
    - ANSIBLE_MODULE_UTILS = "tectonic/ansible/module_utils"
    - ANSIBLE_FILTER_PLUGINS = "tectonic/ansible/filter_plugins"
    ↓
ansible_runner.interface.run()
    ↓
examples/dfir_final_scenario/ansible/after_clone.yml
    ↓
Modules execute with auto-dependency installation
```

### Module Architecture

**Network Modules** (Layer 3):
- `generate_wannacry_attack.py`: Complete attack traffic generation
  - Uses: `third_layer/wannacry.py`
  - Uses: `second_layer/http.py`, `tcp_plain_text_communication.py`
  - Uses: `first_layer/tcp_primitives.py`, `dns.py`

**Filesystem Modules** (Layer 1-3):
- `execute_ransomware_profile.py`: WannaCry profile orchestrator (Layer 3)
- `generate_files_bulk.py`: Bulk file generation (Layer 2)
- `encrypt_files_aes.py`: AES-256-CBC encryption (Layer 1)
- `delete_file_debugfs.py`: Forensic-style deletion (Layer 1)
- `generate_file.py`: Single file generation (Layer 1)

**Utility Modules**:
- `pcap_merger.py`: PCAP file manipulation
- `utils.py`: Common utilities

## Deployment

### Prerequisites

1. **Tectonic Installed**:
   ```bash
   pip install tectonic-cyberrange
   # OR for development:
   cd /path/to/tectonic
   pip install -e .
   ```

2. **Tectonic Configuration** (`tectonic.ini`):
   - Platform: libvirt / AWS / Docker
   - Resources: Minimum 6GB RAM, 4 CPUs, 70GB disk

3. **Python Dependencies** (auto-installed by modules):
   - scapy (network simulation)
   - cryptography (encryption)
   - faker (realistic data generation)
   - openpyxl (Excel files)

### Quick Start

```bash
# Step 1: Create base images (one-time)
tectonic -c tectonic.ini examples/dfir_final_scenario/edition.yml create-images

# Step 2: Deploy scenario
tectonic -c tectonic.ini examples/dfir_final_scenario/edition.yml deploy

# Step 3: Get connection info
tectonic -c tectonic.ini examples/dfir_final_scenario/edition.yml show-info

# Step 4: Connect to victim machine
ssh ubuntu@<victim-ip>

# Step 5: Verify outputs
ls -lh /tmp/wannacry_unified_attack.pcap
ls -lh /tmp/final_forensic.img
```

### Cleanup

```bash
tectonic -c tectonic.ini examples/dfir_final_scenario/edition.yml destroy
```

## Forensic Analysis Workflow

### Phase 1: Network Forensics

1. **Copy PCAP to analyst workstation**:
   ```bash
   scp victim:/tmp/wannacry_unified_attack.pcap .
   ```

2. **Wireshark Analysis**:
   ```bash
   wireshark wannacry_unified_attack.pcap
   ```
   
   **Look for**:
   - SMB exploitation attempts (port 445)
   - HTTP malware downloads (port 80)
   - Plain-text C2 commands (port 4444)

3. **CLI Analysis with tshark**:
   ```bash
   # View SMB traffic
   tshark -r wannacry_unified_attack.pcap -Y "smb2"
   
   # View HTTP downloads
   tshark -r wannacry_unified_attack.pcap -Y "http.request"
   
   # View TCP plain-text
   tshark -r wannacry_unified_attack.pcap -Y "tcp.port==4444" -T fields -e data.text
   ```

### Phase 2: Disk Forensics

1. **Copy disk image to analyst workstation**:
   ```bash
   scp victim:/tmp/final_forensic.img .
   ```

2. **Import to Autopsy**:
   - Open Autopsy
   - Create New Case
   - Add Data Source → Disk Image
   - Select `final_forensic.img`

3. **Navigate filesystem**:
   - File Tree → `/srv/samba/share/`
   - Identify `.WNCRY` encrypted files
   - Check for `@Please_Read_Me@.txt` ransom note
   - Look for PE executables (wannacry.exe, tasksche.exe, etc.)

4. **Analyze deleted files**:
   - Deleted Files view in Autopsy
   - Find `flagsinha.txt.WNCRY`
   - Export file for decryption

### Phase 3: Flag Recovery Challenge

1. **Find deleted flag**:
   ```bash
   # Mount disk image locally
   sudo losetup -fP final_forensic.img
   sudo mount /dev/loop0 /mnt/forensic
   
   # Use testdisk or photorec
   sudo photorec /dev/loop0
   ```

2. **Decrypt flag file**:
   ```python
   from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
   from cryptography.hazmat.backends import default_backend
   import base64
   
   # Get key from simulation output
   key = b"<encryption_key_from_output>"
   
   # Read encrypted file
   with open("flagsinha.txt.WNCRY", "rb") as f:
       iv = f.read(16)
       encrypted_data = f.read()
   
   # Decrypt
   cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
   decryptor = cipher.decryptor()
   decrypted = decryptor.update(encrypted_data) + decryptor.finalize()
   
   # Remove padding
   padding_length = decrypted[-1]
   plaintext = decrypted[:-padding_length]
   
   print(plaintext.decode('utf-8'))
   # Output: "Encontraste la flag, sos el mejor DFIR user del maldito pais "
   ```

## File Locations

### Victim Machine

| File | Description | Size |
|------|-------------|------|
| `/tmp/wannacry_unified_attack.pcap` | Network traffic capture | ~50KB |
| `/tmp/final_forensic.img` | Forensic disk image | 1GB |
| `/mnt/simple_forensic/` | Mounted filesystem (during simulation) | - |

### Inside Disk Image (`/srv/samba/share/`)

| File/Dir | Description | Count |
|----------|-------------|-------|
| `*.WNCRY` | Encrypted victim files | ~93 files |
| `@Please_Read_Me@.txt` | Ransom note | 1 file |
| `wannacry.exe` | Malware executable | 1 file |
| `tasksche.exe` | Malware component | 1 file |
| `mssecsvc.exe` | Malware component | 1 file |
| `flagsinha.txt.WNCRY` | **Hidden flag (DELETED)** | 1 file |
| Subdirectories | Faker-generated dirs | ~8 dirs |

## Learning Objectives

### Network Analysis
- ✅ Identify SMB exploitation patterns
- ✅ Recognize malware download traffic
- ✅ Analyze C2 communication protocols
- ✅ Correlate network events with filesystem changes

### Disk Forensics
- ✅ Import and analyze forensic disk images
- ✅ Identify ransomware encryption patterns
- ✅ Recognize file entropy changes
- ✅ Recover deleted files

### Incident Response
- ✅ Build attack timeline from multiple sources
- ✅ Correlate network and filesystem evidence
- ✅ Document forensic findings
- ✅ Practice chain-of-custody procedures

### Cryptanalysis
- ✅ Understand AES-256-CBC encryption
- ✅ Decrypt recovered files
- ✅ Analyze encryption key management

## Troubleshooting

### Issue: Modules not found

**Cause**: `ansible.py` not setting environment variables correctly.

**Solution**: Verify Tectonic installation:
```bash
python3 -c "from importlib import resources; print(resources.files('tectonic') / 'ansible')"
```

### Issue: Disk image mount fails

**Cause**: Loop device already attached.

**Solution**: Manually detach:
```bash
sudo losetup -D  # Detach all loop devices
```

### Issue: Python dependencies not installing

**Cause**: Network isolation in `after_clone.yml`.

**Solution**: Dependencies should auto-install. If issues persist, pre-install in `base_config.yml`:
```yaml
- name: "Pre-install Python dependencies"
  pip:
    name:
      - scapy
      - cryptography
      - faker
      - openpyxl
    executable: pip3
```

## Technical Details

### Network Traffic Phases

1. **Phase 1: Reconnaissance** (Packets 1-10)
   - SMB negotiation
   - Credential exfiltration
   - Duration: ~2 seconds

2. **Phase 2: Malware Download** (Packets 11-60)
   - HTTP GET requests for 5 WannaCry components
   - Total payload: ~180KB
   - Duration: ~5 seconds

3. **Phase 3: C2 Communication** (Packets 61-70)
   - TCP plain-text commands
   - Kill switch domain check
   - Duration: ~1 second

### Encryption Details

- **Algorithm**: AES-256-CBC
- **Key Size**: 256 bits (32 bytes)
- **IV**: 16 bytes (random per file)
- **Padding**: PKCS7
- **Extension**: `.WNCRY`

### Deletion Method

Files deleted with `debugfs` to simulate forensic recovery:
```bash
debugfs -w /dev/loop0 -R "rm /srv/samba/share/flagsinha.txt.WNCRY"
```

This marks inodes as deleted but data remains on disk, recoverable with tools like:
- Autopsy
- PhotoRec
- TestDisk
- Sleuth Kit

## Contributing

To add new features or modify the scenario:

1. Edit `*/tectonic/ansible/library/` for new modules
2. Edit `*/tectonic/ansible/module_utils/` for new layers
3. Edit `after_clone.yml` for new simulation phases
4. Test with: `tectonic deploy`

## License

GNU General Public License v3.0 or later (GPLv3+)

## Authors

- GSI-Fing-Udelar
- Rodrigo Aguillón
- Ignacio Alesina

## References

- [Tectonic Documentation](https://github.com/GSI-Fing-Udelar/tectonic)
- [WannaCry Analysis](https://www.malware-traffic-analysis.net/)
- [Autopsy Documentation](https://www.sleuthkit.org/autopsy/)
- [Wireshark User Guide](https://www.wireshark.org/docs/)
