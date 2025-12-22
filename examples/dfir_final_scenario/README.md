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

---

# 🍎 macOS Complete Guide

This section provides a complete step-by-step guide specifically for macOS users, as macOS requires different tools and configurations than Linux.

## Prerequisites and Setup

### 1. Install Required Tools

```bash
# Install Wireshark (GUI and CLI tools)
brew install --cask wireshark

# Install Sleuth Kit for disk forensics
brew install sleuthkit

# Install Autopsy (optional, may have compatibility issues)
brew install autopsy
```

### 2. Configure macOS Environment

```bash
# Fix macOS fork() issues with Ansible (REQUIRED)
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"

# Make permanent by adding to ~/.zshrc
echo 'export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES' >> ~/.zshrc
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
```

### 3. Update tectonic.ini

Edit `/Users/macos/tectonic/tectonic.ini`:
```ini
[config]
platform = docker
lab_repo_uri = ./examples
network_cidr_block = 10.0.0.0/16
internet_network_cidr_block = 10.0.0.0/25
services_network_cidr_block = 10.0.0.128/25
ssh_public_key_file = ~/.ssh/id_rsa.pub
configure_dns = no
debug = yes

[ansible]
ssh_common_args = -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=3600 
keep_logs = no
forks = 1  # CRITICAL: Must be 1 for macOS to avoid fork() issues
pipelining = no
timeout = 10

[docker]
uri = unix:///Users/macos/.docker/run/docker.sock
dns = 8.8.8.8
```

## Complete Workflow

### Step 1: Deploy the Scenario

```bash
# Navigate to tectonic directory
cd /Users/macos/tectonic

# Set environment variables
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export PATH="$HOME/.local/bin:$PATH"

# Create base images (takes 5-15 minutes)
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml create-images

# Deploy the scenario
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml deploy

# Generate forensic evidence
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml run-ansible \
  -p ./examples/dfir_final_scenario/ansible/after_clone.yml -f
```

### Step 2: Extract Forensic Evidence

```bash
# Create evidence directory
mkdir -p ~/forensic_evidence

# Extract PCAP file (66KB)
docker cp udelar-dfirunifiedtraining-1-victim:/tmp/wannacry_unified_attack.pcap ~/forensic_evidence/

# Extract disk image (1GB)
docker cp udelar-dfirunifiedtraining-1-victim:/tmp/final_forensic.img ~/forensic_evidence/

# Verify extraction
ls -lh ~/forensic_evidence/
```

### Step 3: Analyze Network Traffic (PCAP)

#### Using Wireshark (GUI)

```bash
# Open PCAP in Wireshark
open -a Wireshark ~/forensic_evidence/wannacry_unified_attack.pcap
```

**What to look for:**
- **Port 4444**: Plain-text credentials and commands
- **HTTP traffic**: Downloads from 198.51.100.25
- **Files downloaded**: wanna0.exe through wanna4.exe (5 files, 12KB each)

#### Using tshark (CLI)

```bash
cd ~/forensic_evidence

# View statistics
tshark -r wannacry_unified_attack.pcap -q -z io,stat,0

# View TCP conversations
tshark -r wannacry_unified_attack.pcap -q -z conv,tcp

# Extract HTTP requests (malware downloads)
tshark -r wannacry_unified_attack.pcap -Y "http.request" -T fields \
  -e frame.number -e ip.src -e ip.dst -e http.request.method -e http.request.uri
```

**Expected output:**
```
29      192.168.1.100   198.51.100.25   GET     /wanna0.exe
31      192.168.1.100   198.51.100.25   GET     /wanna1.exe
33      192.168.1.100   198.51.100.25   GET     /wanna2.exe
35      192.168.1.100   198.51.100.25   GET     /wanna3.exe
37      192.168.1.100   198.51.100.25   GET     /wanna4.exe
```

### Step 4: Analyze Disk Image

**IMPORTANT:** macOS cannot mount ext4 filesystems natively. Use Sleuth Kit tools directly on the image file.

```bash
cd ~/forensic_evidence

# View filesystem information
fsstat final_forensic.img

# List all files in the image
fls -r -p final_forensic.img | head -50

# List directory structure
fls -r -p final_forensic.img | grep "srv/samba/share"
```

**Expected structure:**
```
srv/samba/share/
├── @Please_Read_Me@.txt (Ransom notes in each folder)
├── purpose0/
│   ├── dog0/ (encrypted files with .WNCRY extension)
│   ├── chair1/
│   └── since2/
└── flagsinha.txt.WNCRY (DELETED - the forensic challenge!)
```

### Step 5: Find Deleted Flag File

```bash
# List deleted files (look for asterisk *)
fls -r -d -p ~/forensic_evidence/final_forensic.img | grep -i flag

# Expected output:
# r/r * 59:       srv/samba/share/flagsinha.txt.WNCRY
```

**Key:**
- `r/r` = regular file
- `*` = deleted file
- `59` = inode number (use this to recover)

### Step 6: Recover Deleted File

```bash
# Recover using icat with the inode number (59)
icat ~/forensic_evidence/final_forensic.img 59 > ~/forensic_evidence/flagsinha.txt.WNCRY.recovered

# Verify recovery
ls -lh ~/forensic_evidence/flagsinha.txt.WNCRY.recovered

# View encrypted content (hex dump)
xxd ~/forensic_evidence/flagsinha.txt.WNCRY.recovered | head -10
```

**Expected output:**
```
-rw-r--r--  1 macos  staff    80B Dec 22 16:02 flagsinha.txt.WNCRY.recovered

00000000: 4936 6728 ce60 6f29 53cb 5dcf 2a08 b8e3  I6g(.`o)S.].*...
00000010: 8066 e6c3 a589 9aed 8d23 aa48 c5a5 467c  .f.......#.H..F|
...
```

### Step 7: Decrypt the Flag

#### Method 1: Using OpenSSL (Recommended)

```bash
cd ~/forensic_evidence

# Decrypt with AES-256-CBC
openssl enc -d -aes-256-cbc \
  -in flagsinha.txt.WNCRY.recovered \
  -out flagsinha.txt.decrypted \
  -K 0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF \
  -iv 00000000000000000000000000000000

# Read the flag
cat flagsinha.txt.decrypted
```

**Flag Result:**
```
Encontraste la flag, sos el mejor dfir user del pais
```

#### Method 2: Using CyberChef (Web-based)

1. Open https://gchq.github.io/CyberChef/
2. Drag `flagsinha.txt.WNCRY.recovered` to Input pane
3. Add recipe: **"AES Decrypt"**
   - **Key (hex)**: `0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF`
   - **IV (hex)**: `00000000000000000000000000000000`
   - **Mode**: CBC
   - **Input**: Raw
   - **Output**: Raw
4. Click "Bake"
5. Read the flag in the output

## macOS-Specific Commands Reference

### Sleuth Kit Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `fsstat` | Show filesystem info | `fsstat final_forensic.img` |
| `fls` | List files | `fls -r -p final_forensic.img` |
| `fls -d` | List deleted files | `fls -r -d -p final_forensic.img` |
| `icat` | Extract file by inode | `icat final_forensic.img 59 > output.file` |
| `istat` | Show inode info | `istat final_forensic.img 59` |

### Network Analysis Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `tshark` | CLI packet analyzer | `tshark -r file.pcap -Y "http"` |
| `capinfos` | File statistics | `capinfos wannacry_unified_attack.pcap` |
| `editcap` | Edit capture files | `editcap -r in.pcap out.pcap` |

## Cleanup

```bash
# Destroy the scenario
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export PATH="$HOME/.local/bin:$PATH"
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml destroy

# Clean extracted evidence (optional)
rm -rf ~/forensic_evidence/

# Stop Docker containers manually if needed
docker stop $(docker ps -a -q --filter "name=udelar-dfirunifiedtraining")
docker rm $(docker ps -a -q --filter "name=udelar-dfirunifiedtraining")
```

## Troubleshooting (macOS)

### Issue: macOS fork() Error

**Error message:**
```
objc[xxxxx]: +[NSMutableString initialize] may have been in progress in another thread when fork() was called.
```

**Solutions:**
```bash
# Solution 1: Set environment variable (required every time)
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

# Solution 2: Make it permanent
echo 'export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES' >> ~/.zshrc

# Solution 3: Update tectonic.ini
[ansible]
forks = 1  # Must be 1 for macOS
```

### Issue: tshark Not Found

**Solutions:**
```bash
# Check if installed
which tshark

# Add Homebrew to PATH
export PATH="/opt/homebrew/bin:$PATH"

# Verify
tshark --version

# Make permanent
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zshrc
```

### Issue: Cannot Mount ext4 Image

**This is expected on macOS!** Use Sleuth Kit tools instead:
- ❌ Don't use: `mount`, `losetup`, `debugfs`
- ✅ Use instead: `fls`, `icat`, `fsstat`

### Issue: Docker Socket Not Found

**Error:** `Cannot connect to the Docker daemon`

**Solution:**
```bash
# Check Docker Desktop is running
docker ps

# Update tectonic.ini with correct socket path
[docker]
uri = unix:///Users/macos/.docker/run/docker.sock

# Or find socket location
ls -la ~/.docker/run/docker.sock
```

### Issue: Network Overlap Error

```bash
# Destroy existing deployment
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml destroy

# Clean Docker networks
docker network prune -f

# Retry deployment
poetry run tectonic -c ./tectonic.ini ./examples/dfir_final_scenario/edition.yml deploy
```