# WannaCry DFIR Training Scenario

## Overview

This scenario simulates a complete WannaCry ransomware attack for digital forensics training. It generates:

1. **Network Traffic (PCAP)**: Realistic attack packets showing exploitation, malware download, and Command and Control communication
2. **Forensic Disk Image**: A complete filesystem with encrypted files and a hidden flag
3. **Forensic Challenge**: Participants must recover and decrypt a deleted encrypted file to find the flag

## Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                   WANNACRY DFIR SCENARIO                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Phase 1: Network Attack (PCAP Generation)                   │
│  ├─ Reconnaissance & Credential Exfiltration                 │
│  ├─ Malware Download (5 fake WannaCry components)           │
│  └─ Remote Execution Commands                                │
│                                                               │
│  Phase 2: Disk Image Creation                                │
│  ├─ Create 1GB ext4 filesystem                              │
│  ├─ Mount via loop device                                    │
│  └─ Prepare directory structure                              │
│                                                               │
│  Phase 3: Ransomware Simulation                              │
│  ├─ Generate 150 realistic victim files                      │
│  ├─ Encrypt all files with AES-256-CBC (.WNCRY extension)   │
│  ├─ Create ransom note (@Please_Read_Me@.txt)              │
│  └─ Delete 25% of encrypted files                           │
│                                                               │
│  Phase 4: Flag Generation (Forensic Challenge)               │
│  ├─ Create flag file (flagsinha.txt)                        │
│  ├─ Encrypt with AES-256-CBC (flagsinha.txt.WNCRY)         │
│  ├─ Delete original plain-text file                         │
│  └─ Delete encrypted file using debugfs (recoverable)       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Deploy the Scenario
```bash
# Create base images
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml create-images

# Deploy the scenario
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml deploy
```

### 2. Extract Forensic Evidence

After the scenario completes, extract all evidence files to your local machine:
```bash
# Create directory for evidence
mkdir -p ~/forensic_evidence

# Extract network traffic capture
docker cp udelar-dfirunifiedtraining-1-victim:/tmp/wannacry_unified_attack.pcap ~/forensic_evidence/

# Extract forensic disk image (1GB)
docker cp udelar-dfirunifiedtraining-1-victim:/tmp/final_forensic.img ~/forensic_evidence/

# Verify extraction
ls -lh ~/forensic_evidence/
```

## Forensic Analysis Guide

### Step 1: Network Traffic Analysis

Analyze the PCAP file to identify attack indicators:
```bash
# Open in Wireshark
wireshark ~/forensic_evidence/wannacry_unified_attack.pcap

# Or use tshark for command-line analysis
# View HTTP traffic (malware downloads)
tshark -r ~/forensic_evidence/wannacry_unified_attack.pcap -Y "http" | head -20

# View TCP SYN packets (reconnaissance)
tshark -r ~/forensic_evidence/wannacry_unified_attack.pcap -Y "tcp.flags.syn==1 && tcp.flags.ack==0"
```

**Key Indicators to Look For:**
- Plain-text credentials in TCP stream (port 4444)
- Multiple binary downloads from malicious host (198.51.100.25)
- Base64-encoded executables in HTTP responses
- Remote execution commands
- Files downloaded: `wcry1.exe`, `wcry2.exe`, `wcry3.exe`, `wcry4.exe`, `wcry5.exe`

### Step 2: Disk Image Analysis with Autopsy

#### Mount the disk image in Autopsy
```bash
# Launch Autopsy
autopsy
```

1. Create a new case
2. Add Data Source → Disk Image or VM File
3. Select: `~/forensic_evidence/final_forensic.img`
4. Wait for analysis to complete

#### Navigate the filesystem
```
final_forensic.img/
└── srv/
    └── samba/
        └── share/
            ├── @Please_Read_Me@.txt (Ransom note)
            ├── *.WNCRY (150+ encrypted files)
            └── flagsinha.txt.WNCRY (DELETED - forensic challenge)
```

### Step 3: Recover Deleted Flag File with icat

The flag file was deleted using `debugfs`, making it forensically recoverable:
```bash
# Mount the disk image as loop device
sudo losetup -fP ~/forensic_evidence/final_forensic.img
sudo losetup -j ~/forensic_evidence/final_forensic.img  # Note the device (e.g., /dev/loop25)

# List deleted files with debugfs
sudo debugfs /dev/loop25
debugfs> ls -d /srv/samba/share
# Look for flagsinha.txt.WNCRY with inode number

# Exit debugfs
debugfs> quit

# Recover the deleted encrypted flag file using icat
# Replace <INODE> with the inode number from debugfs output
sudo icat /dev/loop25 <INODE> > ~/forensic_evidence/flagsinha.txt.WNCRY

# Verify recovery
file ~/forensic_evidence/flagsinha.txt.WNCRY
hexdump -C ~/forensic_evidence/flagsinha.txt.WNCRY | head
```

**Alternative method using Autopsy:**
1. In Autopsy, navigate to "Deleted Files" view
2. Find `flagsinha.txt.WNCRY` 
3. Right-click → Extract File(s)
4. Save to `~/forensic_evidence/`

### Step 4: Extract Encryption Key and IV

The AES-256-CBC encryption uses a **hardcoded key and IV** stored in the playbook. Extract them:

**From the playbook (`demo_unified_attack.yml`):**
```yaml
# Encryption key (64 hex characters = 32 bytes for AES-256)
key: "0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF"

# IV is derived from first 16 bytes of encrypted file
```

**Extract IV from the encrypted file:**
```bash
# The IV is stored in the first 16 bytes of the .WNCRY file
head -c 16 ~/forensic_evidence/flagsinha.txt.WNCRY | xxd -p
# Example output: a7324dbbcf5...
```

### Step 5: Decrypt Flag with CyberChef

1. Open **CyberChef**: https://gchq.github.io/CyberChef/

2. **Load the encrypted file:**
   - Drag `flagsinha.txt.WNCRY` into the Input pane

3. **Configure AES Decrypt recipe:**
   - Search and add: **"AES Decrypt"**
   - **Key**: `0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF`
   - **IV**: `a7324dbbcf5...` (from step 4)
   - **Mode**: `CBC`
   - **Input**: `Raw`
   - **Output**: `Raw`

4. **Bake (execute)** the recipe

5. **Read the flag:**
```
   Encontraste la flag, sos el mejor dfir user del pais
```

## Forensic Challenge Summary

**Objective:** Recover and decrypt the hidden flag file

**Required Steps:**
1. ✅ Extract disk image from container
2. ✅ Analyze filesystem with Autopsy
3. ✅ Identify deleted encrypted file (`flagsinha.txt.WNCRY`)
4. ✅ Recover file using `icat` or Autopsy
5. ✅ Extract IV from recovered file (first 16 bytes)
6. ✅ Use hardcoded AES-256 key from playbook
7. ✅ Decrypt in CyberChef with correct key + IV
8. ✅ Read the flag message

## Encryption Details

**Algorithm:** AES-256-CBC  
**Key Size:** 256 bits (32 bytes)  
**IV Size:** 128 bits (16 bytes)  
**Key (hex):** `0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF`  
**File Extension:** `.WNCRY`  

**Encrypted File Structure:**
```
[16 bytes IV][Encrypted Content with PKCS7 Padding]
```

## Cleanup
```bash
# Destroy the scenario
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml destroy

# Remove loop device (if manually mounted)
sudo losetup -d /dev/loop25

# Clean extracted evidence (optional)
rm -rf ~/forensic_evidence/
```

### Network Overlap Error

If deployment fails with `Pool overlaps with other one`:
```bash
# Destroy previous deployment
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml destroy

# Force clean networks
docker network prune -f

# Redeploy
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml deploy
```

## References

- **Autopsy Documentation:** https://www.autopsy.com/
- **The Sleuth Kit (icat):** https://wiki.sleuthkit.org/index.php?title=Icat
- **CyberChef:** https://gchq.github.io/CyberChef/
- **Wireshark User Guide:** https://www.wireshark.org/docs/wsug_html_chunked/