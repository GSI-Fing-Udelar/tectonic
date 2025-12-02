#!/usr/bin/env python3
"""
WannaCry Forensics Analyzer
Análisis forense completo usando auditd, ent y osquery

SCORING SYSTEM (Maximum: 120 points, displays as X/100 for readability):
  • Auditd (30 pts): Mass file operations >10 ops/sec (CRITICAL indicator)
  • Entropy (40 pts): Average entropy >7.5 bits/byte (strong encryption)
  • High Entropy Count (10 pts): Files with entropy >7.5
  • Encrypted Files (20 pts): >50 files with ransomware extensions
  • Ransom Notes (20 pts): Presence of ransom demand files

INTERPRETATION:
  • 0-40:  Low threat (possible false positive)
  • 40-70: Suspected infection (investigate further)  
  • 70+:   CRITICAL - Confirmed ransomware (immediate response)

EXIT CODES:
  • 0: Low threat (<40)
  • 1: Warning (>=40)
  • 2: Critical (>=70)
"""

import os
import sys
import json
import subprocess
import shutil
import re
from datetime import datetime
from pathlib import Path

def check_and_install_tools():
    """Check and install required forensic tools if missing"""
    tools_to_check = {
        'ausearch': {'package': 'auditd', 'check_cmd': 'ausearch'},
        'ent': {'package': 'ent', 'check_cmd': 'ent'},
        'osqueryi': {'package': 'osquery', 'check_cmd': 'osqueryi'}
    }
    
    missing_tools = []
    installed_tools = []
    
    print("=" * 80)
    print("  CHECKING FORENSIC TOOLS")
    print("=" * 80)
    
    # Check which tools are missing
    for tool_name, tool_info in tools_to_check.items():
        if shutil.which(tool_info['check_cmd']) is None:
            missing_tools.append(tool_info['package'])
            print(f"  ✗ {tool_name} not found - will attempt to install {tool_info['package']}")
        else:
            installed_tools.append(tool_name)
            print(f"  ✓ {tool_name} already installed")
    
    # If tools are missing, attempt installation
    if missing_tools:
        print(f"\n📦 Installing missing tools: {', '.join(missing_tools)}")
        print("   This requires sudo privileges...")
        
        # Detect package manager
        if shutil.which('apt-get'):
            pkg_manager = 'apt-get'
            update_cmd = ['sudo', 'apt-get', 'update', '-qq']
            install_cmd_base = ['sudo', 'apt-get', 'install', '-y']
        elif shutil.which('dnf'):
            pkg_manager = 'dnf'
            update_cmd = None
            install_cmd_base = ['sudo', 'dnf', 'install', '-y']
        elif shutil.which('yum'):
            pkg_manager = 'yum'
            update_cmd = None
            install_cmd_base = ['sudo', 'yum', 'install', '-y']
        else:
            print("  ⚠️  WARNING: No supported package manager found (apt/dnf/yum)")
            print("     Please install manually: sudo apt-get install auditd ent osquery")
            return False
        
        try:
            # Update package cache (for apt-based systems)
            if update_cmd:
                print(f"  → Updating package cache...")
                subprocess.run(update_cmd, check=False, capture_output=True)
            
            # Install each missing tool
            for package in missing_tools:
                print(f"  → Installing {package}...")
                
                # Special handling for osquery (needs repository setup on Debian/Ubuntu)
                if package == 'osquery' and pkg_manager == 'apt-get':
                    # Check if osquery repo is configured
                    repo_check = subprocess.run(
                        ['grep', '-r', 'osquery', '/etc/apt/sources.list', '/etc/apt/sources.list.d/'],
                        capture_output=True,
                        check=False
                    )
                    
                    if repo_check.returncode != 0:
                        print(f"     → Setting up osquery repository...")
                        # Add osquery repository
                        setup_commands = [
                            ['sudo', 'apt-key', 'adv', '--keyserver', 'keyserver.ubuntu.com', '--recv-keys', '1484120AC4E9F8A1A577AEEE97A80C63C9D8B80B'],
                            ['sudo', 'bash', '-c', 'echo "deb [arch=amd64] https://pkg.osquery.io/deb deb main" > /etc/apt/sources.list.d/osquery.list'],
                            ['sudo', 'apt-get', 'update', '-qq']
                        ]
                        
                        for cmd in setup_commands:
                            result = subprocess.run(cmd, capture_output=True, check=False)
                            if result.returncode != 0:
                                print(f"     ⚠️  Repository setup failed, trying alternative method...")
                                # Try without repository (might be available in universe)
                                break
                
                # Install the package
                install_cmd = install_cmd_base + [package]
                result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    print(f"     ✓ {package} installed successfully")
                else:
                    print(f"     ✗ Failed to install {package}")
                    print(f"       Error: {result.stderr[:200]}")
                    
                    # Special message for osquery if it fails
                    if package == 'osquery':
                        print(f"       → osquery may require manual installation:")
                        print(f"          Visit: https://osquery.io/downloads/")
            
            # Verify installations
            print("\n  Verifying installations...")
            all_installed = True
            for tool_name, tool_info in tools_to_check.items():
                if shutil.which(tool_info['check_cmd']) is not None:
                    print(f"  ✓ {tool_name} verified")
                else:
                    print(f"  ✗ {tool_name} still not available")
                    all_installed = False
            
            print("=" * 80 + "\n")
            return all_installed
            
        except subprocess.TimeoutExpired:
            print("  ✗ Installation timed out (>300s)")
            return False
        except Exception as e:
            print(f"  ✗ Installation error: {e}")
            return False
    else:
        print("\n✓ All forensic tools are already installed")
        print("=" * 80 + "\n")
        return True

class ForensicsAnalyzer:
    def __init__(self, target_directory, audit_key="wannacry_simulator"):
        self.target_dir = target_directory
        self.audit_key = audit_key
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'target_directory': target_directory,
            'auditd': {},
            'entropy': {},
            'osquery': {},
            'summary': {}
        }
        
        # Check tool availability
        self.auditd_available = shutil.which("ausearch") is not None
        self.ent_available = shutil.which("ent") is not None
        self.osquery_available = shutil.which("osqueryi") is not None
    
    def print_header(self):
        """Print analysis header"""
        print("=" * 80)
        print("  WANNACRY FORENSICS ANALYZER")
        print("=" * 80)
        print(f"Target Directory: {self.target_dir}")
        print(f"Analysis Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"")
        print(f"Tool Availability:")
        print(f"  • auditd (ausearch): {'✓ Available' if self.auditd_available else '✗ Not found'}")
        print(f"  • ent CLI:           {'✓ Available' if self.ent_available else '✗ Not found'}")
        print(f"  • osquery:           {'✓ Available' if self.osquery_available else '✗ Not found'}")
        print("=" * 80)
        print()
    
    def analyze_auditd(self):
        """Analyze audit logs for mass file operations"""
        print("\n" + "=" * 80)
        print("  [1/3] AUDITD ANALYSIS - Mass File Operations Detection")
        print("=" * 80)
        
        if not self.auditd_available:
            print("⚠️  ausearch not available. Skipping auditd analysis.")
            self.results['auditd']['status'] = 'unavailable'
            return
        
        try:
            # Search for audit events with our key (requires root/sudo)
            # Use "boot" to capture all events since system boot
            cmd = ["sudo", "ausearch", "-k", self.audit_key, "--format", "text", "--start", "boot"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                print(f"⚠️  No audit events found for key '{self.audit_key}'")
                self.results['auditd']['status'] = 'no_events'
                self.results['auditd']['events'] = []
                return
            
            # Parse audit events - text format uses "At HH:MM:SS" as separator
            lines = result.stdout.strip().split('\n')
            events = []
            current_event = []
            
            for line in lines:
                if line.startswith('At '):
                    if current_event:
                        events.append('\n'.join(current_event))
                    current_event = [line]
                else:
                    current_event.append(line)
            
            # Don't forget the last event
            if current_event:
                events.append('\n'.join(current_event))
            
            # Count operations by type
            operations = {'write': 0, 'create': 0, 'delete': 0, 'chmod': 0, 'rename': 0, 'open': 0}
            file_paths = set()
            timestamps = []
            
            for event in events:
                # Extract operation type from text format (e.g., "successfully opened-file")
                if 'opened-file' in event or 'open' in event.lower():
                    operations['open'] += 1
                if 'created-file' in event or 'created-directory' in event:
                    operations['create'] += 1
                if 'deleted' in event or 'remove' in event.lower():
                    operations['delete'] += 1
                if 'changed-file-permissions' in event or 'chmod' in event.lower():
                    operations['chmod'] += 1
                if 'renamed' in event or 'moved' in event.lower():
                    operations['rename'] += 1
                if 'wrote-to-file' in event or 'modified' in event.lower():
                    operations['write'] += 1
                
                # Extract file paths (look for paths in /tmp/wannacry_simulator)
                path_matches = re.findall(rf'{re.escape(self.target_dir)}[^\s]+', event)
                for path in path_matches:
                    file_paths.add(path)
                
                # Extract timestamp from "At HH:MM:SS DD/MM/YY" format
                time_match = re.search(r'At\s+(\d{2}):(\d{2}):(\d{2})', event)
                if time_match:
                    h, m, s = map(int, time_match.groups())
                    # Convert to seconds since midnight for relative timing
                    timestamp = h * 3600 + m * 60 + s
                    timestamps.append(timestamp)
            
            # Calculate time window and operations/second
            # For ransomware detection, focus on the encryption burst, not setup/cleanup
            if timestamps and len(timestamps) > 1:
                # Sort timestamps to find the dense operation cluster
                sorted_times = sorted(timestamps)
                
                # Find the tightest window containing 80% of operations (the encryption burst)
                # Skip first 10% (setup) and last 10% (cleanup) 
                p10 = int(len(sorted_times) * 0.10)
                p90 = int(len(sorted_times) * 0.90)
                
                if p90 > p10 + 10:  # Need at least 10 events
                    core_times = sorted_times[p10:p90]
                    time_window = max(core_times) - min(core_times)
                    core_events = len(core_times)
                else:
                    # Fallback to full window
                    time_window = max(timestamps) - min(timestamps)
                    core_events = len(events)
                
                # Ensure minimum 1 second window to avoid division artifacts
                if time_window < 1:
                    time_window = 1
                
                operations_per_second = core_events / time_window
            else:
                time_window = 0
                operations_per_second = 0
            
            self.results['auditd'] = {
                'status': 'success',
                'total_events': len(events),
                'operations': operations,
                'unique_files': len(file_paths),
                'time_window_seconds': round(time_window, 2),
                'operations_per_second': round(operations_per_second, 2)
            }
            
            print(f"\n📊 Audit Log Analysis Results:")
            print(f"  Total Events:        {len(events)}")
            print(f"  Time Window:         {time_window:.2f} seconds")
            print(f"  Operations/second:   {operations_per_second:.2f}")
            print(f"\n  Operations Breakdown:")
            for op_type, count in operations.items():
                if count > 0:
                    print(f"    • {op_type.capitalize()}: {count}")
            print(f"\n  Unique Files:        {len(file_paths)}")
            
            # Detect mass operation anomaly
            if operations_per_second > 10:
                print(f"\n  🚨 ANOMALY DETECTED: {operations_per_second:.1f} ops/sec indicates MASS FILE OPERATION")
                print(f"     This is consistent with ransomware behavior!")
            elif operations_per_second > 5:
                print(f"\n  ⚠️  WARNING: {operations_per_second:.1f} ops/sec is higher than normal")
            else:
                print(f"\n  ✓ Normal operation rate")
            
        except subprocess.TimeoutExpired:
            print("⚠️  ausearch timed out")
            self.results['auditd']['status'] = 'timeout'
        except Exception as e:
            print(f"❌ Error analyzing auditd: {e}")
            self.results['auditd']['status'] = 'error'
            self.results['auditd']['error'] = str(e)
    
    def analyze_entropy(self):
        """Analyze file entropy using ent CLI"""
        print("\n" + "=" * 80)
        print("  [2/3] ENTROPY ANALYSIS - Encryption Detection")
        print("=" * 80)
        
        if not self.ent_available:
            print("⚠️  ent CLI not available. Skipping entropy analysis.")
            self.results['entropy']['status'] = 'unavailable'
            return
        
        # Find encrypted files
        encrypted_files = []
        for root, dirs, files in os.walk(self.target_dir):
            for filename in files:
                if filename.endswith(('.WNCRY', '.WCRY', '.WNCRYPT')):
                    encrypted_files.append(os.path.join(root, filename))
        
        if not encrypted_files:
            print("ℹ️  No encrypted files found (.WNCRY/.WCRY/.WNCRYPT)")
            self.results['entropy']['status'] = 'no_files'
            return
        
        entropy_results = []
        high_entropy_count = 0
        
        print(f"\nAnalyzing entropy of {len(encrypted_files)} encrypted files...")
        print(f"(Showing first 10 for brevity)\n")
        
        # Analyze ALL files but only show first 10
        for idx, filepath in enumerate(encrypted_files):
            try:
                result = subprocess.run(
                    ["ent", filepath],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Parse ent output
                    entropy_match = re.search(r'Entropy\s*=\s*([0-9]+(?:\.[0-9]+)?)\s+bits', result.stdout)
                    chi_square_match = re.search(r'Chi square.*?(\d+\.\d+)%', result.stdout)
                    
                    if entropy_match:
                        entropy = float(entropy_match.group(1))
                        chi_square = float(chi_square_match.group(1)) if chi_square_match else None
                        
                        entropy_results.append({
                            'file': os.path.relpath(filepath, self.target_dir),
                            'entropy': entropy,
                            'chi_square_percent': chi_square
                        })
                        
                        if entropy > 7.5:
                            high_entropy_count += 1
                        
                        # Only print first 10 to avoid cluttering output
                        if idx < 10:
                            status = "🔴 ENCRYPTED" if entropy > 7.5 else "🟡 SUSPICIOUS" if entropy > 7.0 else "🟢 NORMAL"
                            print(f"  {status} {os.path.basename(filepath)}: {entropy:.3f} bits/byte")
                    
            except subprocess.TimeoutExpired:
                if idx < 10:
                    print(f"  ⏱️  Timeout analyzing {os.path.basename(filepath)}")
            except Exception as e:
                if idx < 10:
                    print(f"  ❌ Error analyzing {os.path.basename(filepath)}: {e}")
        
        # Calculate statistics
        if entropy_results:
            avg_entropy = sum(r['entropy'] for r in entropy_results) / len(entropy_results)
            max_entropy = max(r['entropy'] for r in entropy_results)
            min_entropy = min(r['entropy'] for r in entropy_results)
        else:
            avg_entropy = max_entropy = min_entropy = 0
        
        self.results['entropy'] = {
            'status': 'success',
            'total_files': len(encrypted_files),
            'analyzed_files': len(entropy_results),
            'high_entropy_count': high_entropy_count,
            'avg_entropy': round(avg_entropy, 3),
            'max_entropy': round(max_entropy, 3),
            'min_entropy': round(min_entropy, 3),
            'sample_results': entropy_results[:20]  # Save first 20 in report
        }
        
        print(f"\n📊 Entropy Analysis Summary:")
        print(f"  Total Encrypted Files:  {len(encrypted_files)}")
        print(f"  Analyzed:               {len(entropy_results)}")
        print(f"  High Entropy (>7.5):    {high_entropy_count}/{len(entropy_results)}")
        print(f"  Average Entropy:        {avg_entropy:.3f} bits/byte")
        print(f"  Range:                  {min_entropy:.3f} - {max_entropy:.3f}")
        
        if avg_entropy > 7.5:
            print(f"\n  🚨 ALERT: Average entropy {avg_entropy:.3f} indicates STRONG ENCRYPTION")
            print(f"     Random/encrypted data typically has entropy > 7.5 bits/byte")
        elif avg_entropy > 7.0:
            print(f"\n  ⚠️  WARNING: Average entropy {avg_entropy:.3f} suggests compression or weak encryption")
        else:
            print(f"\n  ✓ Low entropy suggests plaintext or structured data")
    
    def analyze_osquery(self):
        """Analyze filesystem using osquery"""
        print("\n" + "=" * 80)
        print("  [3/3] OSQUERY ANALYSIS - Filesystem Forensics")
        print("=" * 80)
        
        if not self.osquery_available:
            print("⚠️  osquery not available. Skipping osquery analysis.")
            self.results['osquery']['status'] = 'unavailable'
            return
        
        # First, get accurate count using Python (osquery has issues with deep recursion)
        encrypted_files_list = []
        ransom_notes_list = []
        for root, dirs, files in os.walk(self.target_dir):
            for filename in files:
                if filename.endswith(('.WNCRY', '.WCRY', '.WNCRYPT')):
                    encrypted_files_list.append(os.path.join(root, filename))
                if 'Please_Read_Me' in filename or 'Wana' in filename:
                    ransom_notes_list.append(os.path.join(root, filename))
        
        total_encrypted = len(encrypted_files_list)
        total_ransom = len(ransom_notes_list)
        
        print(f"\n📊 Quick Scan Results (Python):")
        print(f"  Total encrypted files: {total_encrypted}")
        print(f"  Total ransom notes: {total_ransom}")
        
        queries = {
            'encrypted_files_count': f"""
                SELECT COUNT(*) as total_count
                FROM file
                WHERE directory LIKE '{self.target_dir}%'
                  AND (filename LIKE '%.WNCRY' OR filename LIKE '%.WCRY' OR filename LIKE '%.WNCRYPT');
            """,
            
            'encrypted_files': f"""
                SELECT 
                    path,
                    size,
                    datetime(mtime, 'unixepoch', 'localtime') as modified_time,
                    datetime(ctime, 'unixepoch', 'localtime') as changed_time
                FROM file
                WHERE directory LIKE '{self.target_dir}%'
                  AND (filename LIKE '%.WNCRY' OR filename LIKE '%.WCRY' OR filename LIKE '%.WNCRYPT')
                ORDER BY mtime DESC
                LIMIT 10;
            """,
            
            'ransom_notes': f"""
                SELECT 
                    path,
                    size,
                    datetime(mtime, 'unixepoch', 'localtime') as modified_time
                FROM file
                WHERE directory LIKE '{self.target_dir}%'
                  AND (filename LIKE '%Please_Read_Me%' OR filename LIKE '%Wana%')
                ORDER BY mtime DESC;
            """,
            
            'suspicious_executables': f"""
                SELECT 
                    path,
                    size,
                    datetime(mtime, 'unixepoch', 'localtime') as modified_time
                FROM file
                WHERE directory LIKE '{self.target_dir}%'
                  AND filename LIKE '%.exe'
                ORDER BY mtime DESC;
            """,
            
            'file_timeline': f"""
                SELECT 
                    strftime('%Y-%m-%d %H', datetime(mtime, 'unixepoch')) as hour,
                    COUNT(*) as files_modified
                FROM file
                WHERE directory LIKE '{self.target_dir}%'
                  AND (filename LIKE '%.WNCRY' OR filename LIKE '%.WCRY')
                GROUP BY hour
                ORDER BY hour DESC
                LIMIT 24;
            """,
            
            'size_distribution': f"""
                SELECT 
                    CASE 
                        WHEN size < 1024 THEN '< 1KB'
                        WHEN size < 102400 THEN '1KB-100KB'
                        WHEN size < 1048576 THEN '100KB-1MB'
                        ELSE '> 1MB'
                    END as size_range,
                    COUNT(*) as count
                FROM file
                WHERE directory LIKE '{self.target_dir}%'
                  AND (filename LIKE '%.WNCRY' OR filename LIKE '%.WCRY')
                GROUP BY size_range;
            """
        }
        
        osquery_results = {}
        osquery_results['total_encrypted_count'] = total_encrypted
        osquery_results['total_ransom_count'] = total_ransom
        
        for query_name, query_sql in queries.items():
            try:
                result = subprocess.run(
                    ["osqueryi", "--json", query_sql],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    osquery_results[query_name] = data
                    
                    print(f"\n📋 {query_name.replace('_', ' ').title()}:")
                    if data:
                        if query_name == 'encrypted_files_count':
                            total = data[0].get('total_count', 0) if data else 0
                            print(f"  Total encrypted files in target directory: {total}")
                        
                        elif query_name == 'encrypted_files':
                            print(f"  Found {len(data)} encrypted files (showing first 10):")
                            for item in data[:5]:
                                print(f"    • {os.path.basename(item['path'])} ({item['size']} bytes) - {item['modified_time']}")
                        
                        elif query_name == 'ransom_notes':
                            print(f"  Found {len(data)} ransom notes:")
                            for item in data:
                                print(f"    • {os.path.basename(item['path'])}")
                        
                        elif query_name == 'suspicious_executables':
                            print(f"  Found {len(data)} PE executables:")
                            for item in data:
                                print(f"    • {os.path.basename(item['path'])} ({item['size']} bytes)")
                        
                        elif query_name == 'file_timeline':
                            print(f"  File modification timeline (last 24 hours):")
                            for item in data[:10]:
                                print(f"    • {item['hour']}: {item['files_modified']} files")
                        
                        elif query_name == 'size_distribution':
                            print(f"  File size distribution:")
                            for item in data:
                                print(f"    • {item['size_range']}: {item['count']} files")
                    else:
                        print(f"  No results")
                
            except subprocess.TimeoutExpired:
                print(f"  ⏱️  Query timeout: {query_name}")
                osquery_results[query_name] = {'error': 'timeout'}
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON parse error: {query_name}")
                osquery_results[query_name] = {'error': 'json_parse_error'}
            except Exception as e:
                print(f"  ❌ Error executing query {query_name}: {e}")
                osquery_results[query_name] = {'error': str(e)}
        
        self.results['osquery'] = {
            'status': 'success',
            'queries': osquery_results
        }
    
    def generate_summary(self):
        """Generate final forensic summary"""
        print("\n" + "=" * 80)
        print("  FORENSIC ANALYSIS SUMMARY")
        print("=" * 80)
        
        score = 0
        indicators = []
        
        # Auditd scoring
        if self.results['auditd'].get('status') == 'success':
            ops_per_sec = self.results['auditd'].get('operations_per_second', 0)
            if ops_per_sec > 10:
                score += 30
                indicators.append(f"🚨 Mass file operations: {ops_per_sec:.1f} ops/sec (CRITICAL)")
            elif ops_per_sec > 5:
                score += 15
                indicators.append(f"⚠️  Elevated file operations: {ops_per_sec:.1f} ops/sec")
        
        # Entropy scoring
        if self.results['entropy'].get('status') == 'success':
            avg_entropy = self.results['entropy'].get('avg_entropy', 0)
            high_entropy_count = self.results['entropy'].get('high_entropy_count', 0)
            
            if avg_entropy > 7.5:
                score += 40
                indicators.append(f"🚨 High entropy files: {avg_entropy:.3f} bits/byte (ENCRYPTED)")
            elif avg_entropy > 7.0:
                score += 20
                indicators.append(f"⚠️  Medium entropy files: {avg_entropy:.3f} bits/byte")
            
            if high_entropy_count > 0:
                score += 10
                indicators.append(f"🔴 {high_entropy_count} files with entropy > 7.5")
        
        # Osquery scoring
        if self.results['osquery'].get('status') == 'success':
            queries = self.results['osquery'].get('queries', {})
            
            # Use the accurate Python-based count
            encrypted_count = queries.get('total_encrypted_count', 0)
            ransom_count = queries.get('total_ransom_count', 0)
            
            exe_count = len(queries.get('suspicious_executables', []))
            
            if encrypted_count > 50:
                score += 20
                indicators.append(f"🔴 {encrypted_count} encrypted files detected")
            elif encrypted_count > 10:
                score += 10
                indicators.append(f"🟡 {encrypted_count} encrypted files detected")
            
            if ransom_count > 0:
                score += 20
                indicators.append(f"📄 {ransom_count} ransom notes found")
            
            if exe_count > 0:
                indicators.append(f"⚙️  {exe_count} PE executables found")
        
        self.results['summary'] = {
            'score': score,
            'max_score': 100,
            'indicators': indicators,
            'verdict': self._get_verdict(score)
        }
        
        print(f"\n🎯 Threat Score: {score}/100")
        print(f"\n📊 Indicators Found:")
        for indicator in indicators:
            print(f"  • {indicator}")
        
        print(f"\n⚖️  Verdict: {self._get_verdict(score)}")
        
        if score >= 70:
            print("\n🚨 CRITICAL: High confidence of ransomware infection")
            print("   Recommended actions:")
            print("   1. Isolate affected systems immediately")
            print("   2. Preserve forensic evidence")
            print("   3. Engage incident response team")
            print("   4. Do NOT pay ransom")
            print("   5. Assess backup availability")
        elif score >= 40:
            print("\n⚠️  WARNING: Suspicious activity detected")
            print("   Recommended actions:")
            print("   1. Investigate further with additional tools")
            print("   2. Check backup integrity")
            print("   3. Review security logs")
        else:
            print("\n✓ Low threat level - continue monitoring")
    
    def _get_verdict(self, score):
        """Get verdict based on score"""
        if score >= 70:
            return "🚨 CONFIRMED RANSOMWARE INFECTION"
        elif score >= 40:
            return "⚠️  SUSPECTED RANSOMWARE ACTIVITY"
        elif score >= 20:
            return "🟡 SUSPICIOUS ACTIVITY"
        else:
            return "✅ NO SIGNIFICANT THREATS"
    
    def save_report(self, output_file):
        """Save JSON report"""
        try:
            with open(output_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            print(f"\n💾 Report saved to: {output_file}")
        except Exception as e:
            print(f"\n❌ Error saving report: {e}")
    
    def run(self):
        """Run complete forensic analysis"""
        self.print_header()
        
        self.analyze_auditd()
        self.analyze_entropy()
        self.analyze_osquery()
        
        self.generate_summary()
        
        # Save report
        report_file = f"{self.target_dir}/forensics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.save_report(report_file)
        
        print("\n" + "=" * 80)
        print(f"  Analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        return self.results['summary']['score']


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 wannacry_forensics_analyzer.py <target_directory> [audit_key]")
        print("\nExample:")
        print("  python3 wannacry_forensics_analyzer.py /tmp/wannacry_simulator/")
        print("  python3 wannacry_forensics_analyzer.py /tmp/wannacry_simulator/ wannacry_simulator")
        sys.exit(1)
    
    target_dir = sys.argv[1]
    audit_key = sys.argv[2] if len(sys.argv) > 2 else "wannacry_simulator"
    
    if not os.path.isdir(target_dir):
        print(f"Error: {target_dir} is not a valid directory")
        sys.exit(1)
    
    # Check and install required tools before analysis
    print("🔧 Checking forensic tools installation...\n")
    tools_ready = check_and_install_tools()
    
    if not tools_ready:
        print("\n⚠️  WARNING: Some tools could not be installed automatically.")
        print("   The analysis will continue but may be incomplete.\n")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Analysis cancelled.")
            sys.exit(1)
    
    try:
        analyzer = ForensicsAnalyzer(target_dir, audit_key)
        score = analyzer.run()
        
        # Exit with code based on severity
        if score >= 70:
            sys.exit(2)  # Critical
        elif score >= 40:
            sys.exit(1)  # Warning
        else:
            sys.exit(0)  # OK
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
