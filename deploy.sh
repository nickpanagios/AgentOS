#!/bin/bash
# ══════════════════════════════════════════════════════════════
# AgentOS — Master Deployment Script
# ══════════════════════════════════════════════════════════════
# Usage: sudo bash deploy.sh
# Deploys the full 25-agent AI system on a fresh Ubuntu server.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
EXECUTIVE_WS="/home/executive-workspace"

echo "══════════════════════════════════════════════════════════════"
echo "  AgentOS Deployment"
echo "══════════════════════════════════════════════════════════════"

# ── 1. System packages ──────────────────────────────────────
echo "[1/8] Installing system packages..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv nginx jq curl

# ── 2. Create groups ────────────────────────────────────────
echo "[2/8] Creating groups..."
for g in executive-agents sub-agents technology-team finance-team marketing-team legal-team; do
    groupadd -f "$g"
done

# ── 3. Create agent users and home directories ──────────────
echo "[3/8] Creating agent users..."
EXECUTIVES="jarvis tesla warren steve tony"
SUB_AGENTS="backend frontend ai-mlops devops-engineer security-engineer data-engineer financial-analyst accounting-specialist resource-manager administrative-coordinator brand-strategist content-creator social-media-manager seo-specialist analytics-expert contract-specialist compliance-analyst intellectual-property litigation-support corporate-governance"

for agent in $EXECUTIVES; do
    useradd -m -s /bin/bash -G executive-agents "$agent" 2>/dev/null || true
done
for agent in $SUB_AGENTS; do
    useradd -m -s /bin/bash -G sub-agents "$agent" 2>/dev/null || true
done

# ── 4. Create executive workspace ───────────────────────────
echo "[4/8] Setting up executive workspace..."
mkdir -p "$EXECUTIVE_WS"/{engine,apis,mcp,reports,monitoring,knowledge,tools,messages,tasks,status,logs}
cp "$REPO_DIR"/engine/*.py "$EXECUTIVE_WS/engine/"
cp "$REPO_DIR"/scripts/*.sh "$EXECUTIVE_WS/"
cp "$REPO_DIR"/apis/{api_client.py,api_helpers.sh,registry.json} "$EXECUTIVE_WS/apis/"
cp "$REPO_DIR"/mcp/{mcp_client.py,registry.json} "$EXECUTIVE_WS/mcp/"
cp "$REPO_DIR"/reports/*.py "$EXECUTIVE_WS/reports/"
cp "$REPO_DIR"/monitoring/health_check.py "$EXECUTIVE_WS/monitoring/"
cp "$REPO_DIR"/knowledge/knowledge_client.py "$EXECUTIVE_WS/knowledge/" 2>/dev/null || true
cp "$REPO_DIR"/tools/screenshot.py "$EXECUTIVE_WS/tools/"
chmod +x "$EXECUTIVE_WS"/*.sh

# Copy keys template (user must fill in real keys)
if [ ! -f "$EXECUTIVE_WS/apis/keys.env" ]; then
    cp "$REPO_DIR/apis/keys.env.template" "$EXECUTIVE_WS/apis/keys.env"
    echo "⚠  Fill in API keys at: $EXECUTIVE_WS/apis/keys.env"
fi

chown -R jarvis:executive-agents "$EXECUTIVE_WS"
chmod -R 770 "$EXECUTIVE_WS"

# ── 5. Deploy agent prompts ─────────────────────────────────
echo "[5/8] Deploying agent prompts..."
for agent in $EXECUTIVES; do
    mkdir -p "/home/$agent/member"
    cp "$REPO_DIR/agents/executives/$agent/prompt.md" "/home/$agent/member/" 2>/dev/null || true
    chown -R "$agent:$agent" "/home/$agent"
done
for agent in $SUB_AGENTS; do
    mkdir -p "/home/$agent/member"
    cp "$REPO_DIR/agents/sub-agents/$agent/prompt.md" "/home/$agent/member/" 2>/dev/null || true
    chown -R "$agent:$agent" "/home/$agent"
done

# ── 6. Dashboard ────────────────────────────────────────────
echo "[6/8] Setting up dashboard..."
mkdir -p /home/jarvis/dashboard/templates
cp "$REPO_DIR"/dashboard/app.py /home/jarvis/dashboard/ 2>/dev/null || true
cp "$REPO_DIR"/dashboard/templates/dashboard.html /home/jarvis/dashboard/templates/ 2>/dev/null || true

# ── 7. Systemd services ────────────────────────────────────
echo "[7/8] Installing systemd services..."
cp "$REPO_DIR"/services/*.service "$REPO_DIR"/services/*.timer /etc/systemd/system/ 2>/dev/null || true
systemctl daemon-reload
for svc in agent-dashboard agent-health-monitor; do
    systemctl enable "$svc.service" 2>/dev/null || true
done
for tmr in agent-daily-reports agent-health-monitor; do
    systemctl enable "$tmr.timer" 2>/dev/null || true
done

# ── 8. Nginx ────────────────────────────────────────────────
echo "[8/8] Configuring nginx..."
cp "$REPO_DIR/nginx/agent-dashboard.conf" /etc/nginx/sites-available/agent-dashboard
ln -sf /etc/nginx/sites-available/agent-dashboard /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✅ AgentOS deployed successfully!"
echo "  → Fill API keys: $EXECUTIVE_WS/apis/keys.env"
echo "  → Start dashboard: systemctl start agent-dashboard"
echo "══════════════════════════════════════════════════════════════"
