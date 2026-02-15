#!/usr/bin/env python3
"""Daily Brief — System health, agent activity, security, comms summary."""
import os, subprocess, sqlite3, glob, shutil, psutil
from datetime import date
from pathlib import Path

OUTPUT_DIR = Path(f"/home/executive-workspace/reports/output/{date.today()}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def system_health():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = shutil.disk_usage("/")
    return f"""## System Health

| Metric | Value |
|--------|-------|
| CPU Usage | {cpu}% |
| Memory | {mem.used // (1024**2)} MB / {mem.total // (1024**2)} MB ({mem.percent}%) |
| Disk | {disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB ({100 * disk.used // disk.total}%) |
| Load Avg (1/5/15) | {' / '.join(f'{x:.2f}' for x in os.getloadavg())} |
"""

def agent_activity():
    db_path = "/home/executive-workspace/engine/task_queue.db"
    if not os.path.exists(db_path):
        return "## Agent Activity\n\n_No task queue database found._\n"
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if not tables:
            conn.close()
            return "## Agent Activity\n\n_Task queue DB exists but has no tables._\n"
        lines = ["## Agent Activity\n"]
        for t in tables:
            count = cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            lines.append(f"- **{t}**: {count} rows")
        conn.close()
        return "\n".join(lines) + "\n"
    except Exception as e:
        return f"## Agent Activity\n\n_Error reading task queue: {e}_\n"

def security_status():
    script = "/home/executive-workspace/security_monitor.sh"
    if not os.path.exists(script):
        return "## Security Status\n\n_security_monitor.sh not found — skipped._\n"
    try:
        r = subprocess.run(["bash", script], capture_output=True, text=True, timeout=30)
        output = (r.stdout or r.stderr or "_No output_").strip()
        return f"## Security Status\n\n```\n{output}\n```\n"
    except Exception as e:
        return f"## Security Status\n\n_Error: {e}_\n"

def comms_summary():
    msg_dir = "/home/executive-workspace/messages/"
    if not os.path.isdir(msg_dir):
        return "## Communications\n\n_No messages directory._\n"
    files = glob.glob(os.path.join(msg_dir, "**/*"), recursive=True)
    files = [f for f in files if os.path.isfile(f)]
    return f"## Communications\n\n- **Total message files**: {len(files)}\n"

def main():
    report = f"# Daily Brief — {date.today()}\n\n"
    report += system_health() + "\n"
    report += agent_activity() + "\n"
    report += security_status() + "\n"
    report += comms_summary()
    out = OUTPUT_DIR / "daily_brief.md"
    out.write_text(report)
    print(f"✅ Daily brief written to {out}")
    return report

if __name__ == "__main__":
    main()
