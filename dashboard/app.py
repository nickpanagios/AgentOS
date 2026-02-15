#!/usr/bin/env python3
"""Multi-Agent System — Command Center v3 (with Project Namespacing)"""

import json, os, glob, subprocess, hashlib, sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)
EXEC_WORKSPACE = "/home/executive-workspace"
QUEUE_DB = "/home/executive-workspace/engine/task_queue.db"

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
    "jordan": {"role":"CSO","title":"Sales","color":"#06b6d4","emoji":"💰",
        "desc":"Revenue strategy, pipeline management, client lifecycle, sales operations.",
        "skills":["Sales","Revenue","Pipeline","CRM","Forecasting"]},
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
    "jordan": {
        "sales-director":{"role":"Sales Director","desc":"Pipeline management, deal strategy, forecasting"},
        "account-executive":{"role":"Account Executive","desc":"Client meetings, proposals, negotiations"},
        "business-development":{"role":"Business Development Rep","desc":"Prospecting, outbound, lead qualification"},
        "client-success":{"role":"Client Success Manager","desc":"Onboarding, retention, upselling, NPS"},
        "sales-operations":{"role":"Sales Operations Analyst","desc":"CRM analytics, process optimization"},
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

def get_tasks(project=None):
    tasks = []
    for state in ["pending","active","completed"]:
        for f in glob.glob(f"{EXEC_WORKSPACE}/tasks/{state}/*.json"):
            data = read_json(f)
            if data:
                data["state"]=state
                if project and data.get("project", "default") != project:
                    continue
                tasks.append(data)
    # Also get tasks from SQLite queue
    try:
        db = sqlite3.connect(QUEUE_DB)
        db.row_factory = sqlite3.Row
        query = "SELECT * FROM tasks ORDER BY created DESC LIMIT 50"
        params = []
        if project:
            query = "SELECT * FROM tasks WHERE project=? ORDER BY created DESC LIMIT 50"
            params = [project]
        for row in db.execute(query, params).fetchall():
            r = dict(row)
            r["state"] = r.get("status", "pending")
            r["name"] = r.get("title", r.get("id", ""))
            if project and r.get("project", "default") != project:
                continue
            tasks.append(r)
        db.close()
    except: pass
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
    results = {"integrity":"PASS","world_readable":0,"alerts":0,"last_scan":"","groups":7}
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
    for cat in ["access","communication","security","system"]:
        log = f"{EXEC_WORKSPACE}/audit/{cat}.log"
        try:
            with open(log) as f: results[f"audit_{cat}"] = sum(1 for _ in f)
        except: results[f"audit_{cat}"] = 0
    results["last_scan"] = datetime.utcnow().isoformat() + "Z"
    return results

def get_agent_tools(agent):
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

def get_all_projects():
    """Get all known projects from task queue and knowledge base."""
    projects = set(["default"])
    # From SQLite task queue
    try:
        db = sqlite3.connect(QUEUE_DB)
        rows = db.execute("SELECT DISTINCT project FROM tasks WHERE project IS NOT NULL").fetchall()
        for r in rows:
            if r[0]: projects.add(r[0])
        db.close()
    except: pass
    # From projects.json config
    try:
        cfg = read_json(f"{EXEC_WORKSPACE}/config/projects.json")
        if cfg and "projects" in cfg:
            for p in cfg["projects"]:
                projects.add(p["id"])
    except: pass
    # From knowledge base
    try:
        sys.path.insert(0, f"{EXEC_WORKSPACE}/knowledge")
        from knowledge_client import KnowledgeBase
        kb = KnowledgeBase()
        for p in kb.list_projects():
            projects.add(p)
    except: pass
    return sorted(projects)

# ── Routes ──────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/data')
def api_data():
    project = request.args.get('project')
    if project == 'all' or project == '':
        project = None
    
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
    return jsonify({"executives":execs,"sub_agents":sub_agents,"tasks":get_tasks(project=project),
        "messages":get_all_messages(30),"system":get_system_health(),
        "stats":{"total_agents":25,"executives":5,"sub_agents":20,
            "active":sum(1 for n in EXECUTIVES if get_agent_status(n).get("status")=="online"),
            "configured":sum(1 for sa in sub_agents.values() if sa["configured"])},
        "ts":datetime.utcnow().isoformat()+"Z"})

@app.route('/api/projects')
def api_projects():
    """Return all known projects with metadata."""
    project_ids = get_all_projects()
    # Load config for colors/names
    cfg = read_json(f"{EXEC_WORKSPACE}/config/projects.json") or {"projects": []}
    cfg_map = {p["id"]: p for p in cfg.get("projects", [])}
    
    projects = []
    for pid in project_ids:
        info = cfg_map.get(pid, {})
        projects.append({
            "id": pid,
            "name": info.get("name", pid.replace("-", " ").title()),
            "description": info.get("description", ""),
            "color": info.get("color", "#3b82f6")
        })
    return jsonify({"projects": projects, "active": cfg.get("active_project", "default")})

@app.route('/api/security')
def api_security():
    return jsonify(get_security_summary())

@app.route('/api/agent/<name>')
def api_agent(name):
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
    return jsonify({"status":"ok","ts":datetime.utcnow().isoformat()+"Z",
        "agents":25,"uptime":"active"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
