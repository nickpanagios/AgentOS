#!/usr/bin/env python3
"""Tech Brief — Tesla's domain. Git log, services, disk trends."""
import subprocess, shutil, os
from datetime import date
from pathlib import Path

OUTPUT_DIR = Path(f"/home/executive-workspace/reports/output/{date.today()}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPO = "/home/ubuntu/shared-repo"

def git_summary():
    if not os.path.isdir(os.path.join(REPO, ".git")):
        return "## Git Activity\n\n_No repo found at shared-repo._\n"
    try:
        log = subprocess.run(
            ["git", "-C", REPO, "log", "--oneline", "--since=24 hours ago", "-20"],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()
        if not log:
            log = "_No commits in the last 24 hours._"
        return f"## Git Activity (last 24h)\n\n```\n{log}\n```\n"
    except Exception as e:
        return f"## Git Activity\n\n_Error: {e}_\n"

def running_services():
    try:
        r = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--no-legend"],
            capture_output=True, text=True, timeout=10
        )
        services = [line.split()[0] for line in r.stdout.strip().splitlines() if line.strip()]
        return f"## Running Services\n\n- **Count**: {len(services)}\n- Key services: {', '.join(services[:15])}{'…' if len(services) > 15 else ''}\n"
    except Exception as e:
        return f"## Running Services\n\n_Error: {e}_\n"

def disk_trends():
    lines = ["## Disk Usage\n"]
    lines.append("| Mount | Size | Used | Avail | Use% |")
    lines.append("|-------|------|------|-------|------|")
    try:
        r = subprocess.run(["df", "-h", "--output=target,size,used,avail,pcent"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.strip().splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 5 and not parts[0].startswith("/snap"):
                lines.append(f"| {' | '.join(parts[:5])} |")
    except Exception as e:
        lines.append(f"_Error: {e}_")
    return "\n".join(lines) + "\n"

def main():
    report = f"# Tech Brief — {date.today()}\n\n"
    report += git_summary() + "\n"
    report += running_services() + "\n"
    report += disk_trends()
    out = OUTPUT_DIR / "tech_brief.md"
    out.write_text(report)
    print(f"✅ Tech brief written to {out}")
    return report

if __name__ == "__main__":
    main()
