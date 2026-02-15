#!/usr/bin/env python3
"""Multi-Agent System — Command Center v3 (Days 11-14 Final)"""

import json, os, glob, subprocess, hashlib
from datetime import datetime
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
EXEC_WORKSPACE = "/home/executive-workspace"

EXECUTIVES = {
    "jarvis": {"role":"COO/CPO/CSO/CCO","title":"Central Executive","color":"#3b82f6","emoji":"🤖",
        "desc":"Strategic oversight, product vision, security governance, compliance.",
        "skills":["Operations","Product","Security","Compliance","Strategy"]},
    "tesla": {"role":"CTO/CIO","title":"Technology","color":"#8b5cf6","emoji":"⚡",
        "desc":"Architecture, infrastructure, engineering, AI/ML, digital transformation.",
        "skills":["Architecture","Cloud","AI/ML","DevOps","Infrastructure"]},
    "warren": {"role":"CFO/CAO","title":"Finance & Admin","color":"#10b981","emoji":"📊",
        "desc":"Budgeting, forecasting, resource management, organizational efficiency.",
        "skills":["Finance","Budgeting","Procurement","Administration","Risk"]},
    "steve": {"role":"CMO","title":"Marketing","color":"#f59e0b","emoji":"🎯",
        "desc":"Marketing strategy, customer acquisition, brand building, market intelligence.",
        "skills":["Marketing","Brand","Analytics","Content","SEO"]},
    "tony": {"role":"CLO","title":"Legal","color":"#ef4444","emoji":"⚖️",
        "desc":"Contracts, compliance, IP protection, corporate governance, risk management.",
        "skills":["Legal","Compliance","Contracts","IP","Governance"]},
}

TEAMS = {
    "tesla": {
        "backend":{"role":"Backend Architect","desc":"APIs, databases, microservices"},
        "frontend":{"role":"Frontend Developer","desc":"UI/UX, React, responsive design"},
        "ai-mlops":{"role":"AI/MLOps Engineer","desc":"ML pipelines, model deployment"},
        "devops-engineer":{"role":"DevOps Engineer","desc":"CI/CD, IaC, containers, monitoring"},
        "security-engineer":{"role":"Security Engineer","desc":"Cybersecurity, threat detection"},
        "data-engineer":{"role":"Data Engineer","desc":"Data pipelines, warehousing, ETL"},
    },
    "warren": {
        "financial-analyst":{"role":"Financial Analyst","desc":"Financial modeling, forecasting"},
        "accounting-specialist":{"role":"Accounting Specialist","desc":"General ledger, AR/AP, reporting"},
        "resource-manager":{"role":"Resource Manager","desc":"Resource allocation, vendor management"},
        "administrative-coordinator":{"role":"Admin Coordinator","desc":"Office ops, scheduling, documentation"},
    },
    "steve": {
        "brand-strategist":{"role":"Brand Strategist","desc":"Brand development, market research"},
        "content-creator":{"role":"Content Creator","desc":"Copywriting, visual design, content strategy"},
        "social-media-manager":{"role":"Social Media Manager","desc":"Social strategy, community"},
        "seo-specialist":{"role":"SEO Specialist","desc":"SEO strategy, keyword research"},
        "analytics-expert":{"role":"Analytics Expert","desc":"Marketing analytics, BI dashboards"},
    },
    "tony": {
        "contract-specialist":{"role":"Contract Specialist","desc":"Contract drafting, review, negotiation"},
        "compliance-analyst":{"role":"Compliance Analyst","desc":"Regulatory monitoring, audit prep"},
        "intellectual-property":{"role":"IP Specialist","desc":"Patents, trademarks, copyright"},
        "litigation-support":{"role":"Litigation Support","desc":"Document review, discovery"},
        "corporate-governance":{"role":"Governance Specialist","desc":"Board relations, corporate records"},
    },
}

def read_json(path):
    try:
        with open(path) as f: return json.load(f)
    except: return None

def get_agent_status(agent):
    return read_json(f"{EXEC_WORKSPACE}/status/{agent}.json") or {"agent":agent,"status":"unknown","details":"","timestamp":""}

def count_files(pattern):
    try: return len(glob.glob(pattern))
    except: return 0

def get_tasks():
    tasks = []
    for state in ["pending","active","completed"]:
        for f in glob.glob(f"{EXEC_WORKSPACE}/tasks/{state}/*.json"):
            data = read_json(f)
            if data: data["state"]=state; tasks.append(data)
    return tasks

def get_all_messages(limit=50):
    messages = []
    for log_file, msg_type, sep in [
        (f"{EXEC_WORKSPACE}/logs/message_log.txt","executive"," | "),
        (f"{EXEC_WORKSPACE}/logs/sub_message_log.txt","sub-agent","|"),
    ]:
        try:
            with open(log_file) as f:
                for line in f.readlines()[-limit:]:
                    parts = line.strip().split(sep)
                    if len(parts) >= 4:
                        messages.append({"ts":parts[0],"id":parts[1],
                            "route":f"{parts[2]} → {parts[3]}" if msg_type=="sub-agent" else parts[2],
                            "priority":parts[3] if msg_type=="executive" else parts[4] if len(parts)>4 else "MEDIUM",
                            "subject":parts[4] if msg_type=="executive" and len(parts)>4 else parts[5] if len(parts)>5 else "",
                            "type":msg_type})
        except: pass
    messages.sort(key=lambda m: m.get("ts",""), reverse=True)
    return messages[:limit]

def get_system_health():
    try:
        stat = os.statvfs('/')
        dt = stat.f_blocks * stat.f_frsize
        du = (stat.f_blocks - stat.f_bfree) * stat.f_frsize
        with open('/proc/meminfo') as f:
            mem = {}
            for line in f: p=line.split(); mem[p[0].rstrip(':')]=int(p[1])
        mt, mu = mem['MemTotal'], mem['MemTotal']-mem['MemAvailable']
        with open('/proc/loadavg') as f: ld=f.read().split()
        return {"disk_pct":round(du/dt*100,1),"disk_used":round(du/1e9,1),"disk_total":round(dt/1e9,1),
            "mem_pct":round(mu/mt*100,1),"mem_used":round(mu/1e6,1),"mem_total":round(mt/1e6,1),
            "load":[float(ld[0]),float(ld[1]),float(ld[2])],"cpus":os.cpu_count()}
    except Exception as e: return {"error":str(e)}

def get_security_summary():
    """Run lightweight security checks"""
    results = {"integrity":"PASS","world_readable":0,"alerts":0,"last_scan":"","groups":7}
    # Check integrity baseline
    baseline = f"{EXEC_WORKSPACE}/security/integrity_baseline.json"
    bl = read_json(baseline)
    if bl:
        fails = 0
        for fpath, expected_hash in bl.items():
            try:
                with open(fpath, 'rb') as f:
                    actual = hashlib.sha256(f.read()).hexdigest()
                if actual != expected_hash: fails += 1
            except: fails += 1
        results["integrity"] = "PASS" if fails == 0 else f"FAIL ({fails} files)"
        results["files_checked"] = len(bl)
    # Check audit log counts
    for cat in ["access","communication","security","system"]:
        log = f"{EXEC_WORKSPACE}/audit/{cat}.log"
        try:
            with open(log) as f: results[f"audit_{cat}"] = sum(1 for _ in f)
        except: results[f"audit_{cat}"] = 0
    results["last_scan"] = datetime.utcnow().isoformat() + "Z"
    return results

def get_agent_tools(agent):
    """Check what tools are available for an agent"""
    venv = f"/home/{agent}/venv"
    tools = []
    try:
        pip_list = subprocess.run(
            [f"{venv}/bin/pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=5
        )
        if pip_list.returncode == 0:
            pkgs = json.loads(pip_list.stdout)
            tools = [{"name":p["name"],"version":p["version"]} for p in pkgs
                     if p["name"] not in ("pip","setuptools","wheel")]
    except: pass
    return tools

# ── Routes ──────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/data')
def api_data():
    execs = {}
    for name, info in EXECUTIVES.items():
        st = get_agent_status(name)
        execs[name] = {**info, "status":st.get("status","unknown"),
            "status_detail":st.get("details",""), "last_seen":st.get("timestamp",""),
            "inbox":count_files(f"{EXEC_WORKSPACE}/messages/inbox/{name}/*.json"),
            "team":list(TEAMS.get(name,{}).keys()), "team_details":TEAMS.get(name,{})}
    sub_agents = {}
    for team, agents in TEAMS.items():
        for agent, info in agents.items():
            sub_agents[agent] = {**info, "team":team, "executive":team,
                "configured":all([os.path.exists(f"/home/{agent}/venv/bin/python3"),
                    os.path.exists(f"/home/{agent}/member/prompt.md"),
                    os.path.exists(f"/home/{agent}/.agent_env")])}
    return jsonify({"executives":execs,"sub_agents":sub_agents,"tasks":get_tasks(),
        "messages":get_all_messages(30),"system":get_system_health(),
        "stats":{"total_agents":25,"executives":5,"sub_agents":20,
            "active":sum(1 for n in EXECUTIVES if get_agent_status(n).get("status")=="online"),
            "configured":sum(1 for sa in sub_agents.values() if sa["configured"])},
        "ts":datetime.utcnow().isoformat()+"Z"})

@app.route('/api/security')
def api_security():
    return jsonify(get_security_summary())

@app.route('/api/agent/<name>')
def api_agent(name):
    """Detailed agent info"""
    info = EXECUTIVES.get(name) or {}
    for team, agents in TEAMS.items():
        if name in agents: info = {**agents[name], "team":team, "executive":team}; break
    if not info: return jsonify({"error":"Agent not found"}), 404
    return jsonify({**info, "status":get_agent_status(name),
        "tools":get_agent_tools(name),
        "has_prompt":os.path.exists(f"/home/{name}/member/prompt.md"),
        "has_venv":os.path.exists(f"/home/{name}/venv/bin/python3"),
        "has_env":os.path.exists(f"/home/{name}/.agent_env"),
        "inbox":count_files(f"{EXEC_WORKSPACE}/messages/inbox/{name}/*.json")})

@app.route('/api/teams/<team>')
def api_team(team):
    agents = TEAMS.get(team)
    if not agents: return jsonify({"error":"Team not found"}), 404
    result = {}
    for agent, info in agents.items():
        result[agent] = {**info, "tools":get_agent_tools(agent),
            "configured":all([os.path.exists(f"/home/{agent}/venv/bin/python3"),
                os.path.exists(f"/home/{agent}/member/prompt.md"),
                os.path.exists(f"/home/{agent}/.agent_env")])}
    return jsonify({"team":team,"executive":EXECUTIVES.get(team,{}),"agents":result})

@app.route('/api/audit')
def api_audit():
    """Recent audit log entries"""
    entries = []
    for cat in ["access","communication","security","system"]:
        log = f"{EXEC_WORKSPACE}/audit/{cat}.log"
        try:
            with open(log) as f:
                for line in f.readlines()[-25:]:
                    entries.append({"category":cat,"entry":line.strip()})
        except: pass
    return jsonify({"entries":entries[-50:]})

@app.route('/api/health')
def api_health():
    """Simple health check endpoint"""
    return jsonify({"status":"ok","ts":datetime.utcnow().isoformat()+"Z",
        "agents":25,"uptime":"active"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
