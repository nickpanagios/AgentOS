#!/usr/bin/env python3
"""Health check script for the multi-agent infrastructure."""

import json
import subprocess
import shutil
import psutil
import urllib.request
import datetime
import os

LOG_DIR = "/home/executive-workspace/monitoring/logs"

def check_dashboard_http():
    try:
        resp = urllib.request.urlopen("http://localhost:80", timeout=5)
        return {"status": "pass", "code": resp.getcode()}
    except Exception as e:
        return {"status": "fail", "error": str(e)}

def check_disk_usage():
    usage = shutil.disk_usage("/")
    pct = (usage.used / usage.total) * 100
    return {"status": "fail" if pct > 80 else "pass", "percent": round(pct, 1)}

def check_memory_usage():
    mem = psutil.virtual_memory()
    return {"status": "fail" if mem.percent > 80 else "pass", "percent": round(mem.percent, 1)}

def check_service(name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=5
        )
        active = result.stdout.strip() == "active"
        return {"status": "pass" if active else "fail", "state": result.stdout.strip()}
    except Exception as e:
        return {"status": "fail", "error": str(e)}

def main():
    report = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "checks": {
            "dashboard_http": check_dashboard_http(),
            "disk_usage": check_disk_usage(),
            "memory_usage": check_memory_usage(),
            "agent_dashboard_service": check_service("agent-dashboard"),
            "nginx_service": check_service("nginx"),
        }
    }

    output = json.dumps(report, indent=2)
    print(output)

    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d_%H%M%S")
    with open(os.path.join(LOG_DIR, f"health_{ts}.json"), "w") as f:
        f.write(output + "\n")

if __name__ == "__main__":
    main()
