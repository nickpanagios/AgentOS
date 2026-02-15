#!/usr/bin/env bash
###############################################################################
# AgentOS Deploy Script — Full system bootstrap for Ubuntu 22.04/24.04
# Usage: sudo ./deploy.sh [--api-key KEY] [--skip-validation]
###############################################################################
set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────────
LOGFILE="/var/log/agentos-deploy.log"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EW="/home/executive-workspace"
SHARED="/home/ubuntu/shared-repo"
CHROMIUM_DIR="/opt/chromium"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[1;34m'
BOLD='\033[1m'; NC='\033[0m'

# Agents
EXECUTIVES=(jarvis tesla warren steve tony)
SUBAGENTS=(backend frontend ai-mlops devops-engineer security-engineer data-engineer \
  financial-analyst accounting-specialist resource-manager administrative-coordinator \
  brand-strategist content-creator social-media-manager seo-specialist analytics-expert \
  contract-specialist compliance-analyst intellectual-property litigation-support corporate-governance)
ALL_AGENTS=("${EXECUTIVES[@]}" "${SUBAGENTS[@]}")

# Groups: name:gid
declare -A GROUPS=( [executive-agents]=1011 [sub-agents]=1012 [shared-code]=1013 \
  [team-tesla]=1014 [team-warren]=1015 [team-steve]=1016 [team-tony]=1017 )

# Team memberships (primary supplementary groups)
declare -A USER_GROUPS
USER_GROUPS[jarvis]="executive-agents,shared-code,team-tesla,team-warren,team-steve,team-tony"
USER_GROUPS[tesla]="executive-agents,shared-code,team-tesla"
USER_GROUPS[warren]="executive-agents,shared-code,team-warren"
USER_GROUPS[steve]="executive-agents,shared-code,team-steve"
USER_GROUPS[tony]="executive-agents,shared-code,team-tony"
for sa in "${SUBAGENTS[@]}"; do USER_GROUPS[$sa]="sub-agents,shared-code"; done

# Venv packages
declare -A VENV_PKGS
VENV_PKGS[jarvis]="black flake8 mypy pytest flask gunicorn chromadb"
VENV_PKGS[tesla]="docker-compose ansible pandas numpy matplotlib requests beautifulsoup4 chromadb"
VENV_PKGS[warren]="pandas numpy matplotlib seaborn openpyxl xlsxwriter chromadb"
VENV_PKGS[steve]="pandas plotly requests beautifulsoup4 matplotlib seaborn chromadb"
VENV_PKGS[tony]="pandas requests beautifulsoup4 matplotlib seaborn chromadb"

SHARED_LIBS=(llm_client.py agent_executor.py orchestrator.py api_client.py mcp_client.py knowledge_client.py screenshot.py)

# ── Args ─────────────────────────────────────────────────────────────────────
API_KEY=""
SKIP_VALIDATION=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-key) API_KEY="$2"; shift 2 ;;
    --skip-validation) SKIP_VALIDATION=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────
exec > >(tee -a "$LOGFILE") 2>&1

phase()  { echo -e "\n${BLUE}${BOLD}══════════════════════════════════════════${NC}"; \
           echo -e "${BLUE}${BOLD}  Phase $1: $2${NC}"; \
           echo -e "${BLUE}${BOLD}══════════════════════════════════════════${NC}"; }
info()   { echo -e "${YELLOW}[INFO]${NC} $*"; }
ok()     { echo -e "${GREEN}[OK]${NC} $*"; }
fail()   { echo -e "${RED}[FAIL]${NC} $*"; }

cleanup() { echo -e "\n${RED}Deploy interrupted at $(date)${NC}"; }
trap cleanup ERR

# ── Pre-flight ───────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && { fail "Must run as root"; exit 1; }
echo -e "${BOLD}AgentOS Deployment — $(date)${NC}"
echo "Repo: $REPO_DIR"

###############################################################################
# Phase 1: System Dependencies
###############################################################################
phase 1 "System Dependencies"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
  python3 python3-pip python3-venv python3-dev \
  nginx curl git jq sqlite3 \
  build-essential libffi-dev libssl-dev \
  nodejs npm 2>&1 | tail -1

# Node.js 22+ via NodeSource if needed
NODE_VER=$(node --version 2>/dev/null | sed 's/v//' | cut -d. -f1 || echo 0)
if (( NODE_VER < 22 )); then
  info "Installing Node.js 22 via NodeSource..."
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >/dev/null 2>&1
  apt-get install -y -qq nodejs 2>&1 | tail -1
fi

# Chromium
if ! command -v chromium-browser &>/dev/null && ! command -v chromium &>/dev/null; then
  apt-get install -y -qq chromium-browser 2>/dev/null || apt-get install -y -qq chromium 2>/dev/null || info "System chromium unavailable; will use Playwright in Phase 13"
fi

# Playwright global
npm list -g playwright &>/dev/null || npm install -g playwright 2>&1 | tail -1

ok "System dependencies installed"

###############################################################################
# Phase 2: Create Groups
###############################################################################
phase 2 "Create Groups (7)"

for grp in "${!GROUPS[@]}"; do
  gid=${GROUPS[$grp]}
  getent group "$grp" &>/dev/null || groupadd -g "$gid" "$grp"
  ok "Group $grp ($gid)"
done

###############################################################################
# Phase 3: Create Users (25)
###############################################################################
phase 3 "Create Users (25 agents)"

for agent in "${ALL_AGENTS[@]}"; do
  if ! id "$agent" &>/dev/null; then
    useradd -m -s /bin/bash "$agent"
  fi
  usermod -aG "${USER_GROUPS[$agent]}" "$agent"
  chmod 750 "/home/$agent"
  # umask
  grep -q 'umask 027' "/home/$agent/.bashrc" 2>/dev/null || echo 'umask 027' >> "/home/$agent/.bashrc"
  ok "User $agent"
done

###############################################################################
# Phase 4: Directory Structure
###############################################################################
phase 4 "Directory Structure"

mkdir -p "$EW"
chown jarvis:executive-agents "$EW"
chmod 2770 "$EW"

for d in messages logs tasks status security audit teams engine apis mcp knowledge reports monitoring tools config; do
  mkdir -p "$EW/$d"
done

# Inboxes
for agent in "${ALL_AGENTS[@]}"; do
  mkdir -p "$EW/messages/inbox/$agent"
done

# Tasks
for d in pending active completed; do mkdir -p "$EW/tasks/$d"; done

# Audit logs
for f in access communication security system; do touch "$EW/audit/${f}.log"; done

# Team dirs
for team in tesla warren steve tony; do
  mkdir -p "$EW/teams/$team"
  chown "root:team-$team" "$EW/teams/$team"
  chmod 2770 "$EW/teams/$team"
done

# Shared repo
mkdir -p "$SHARED"
chown ubuntu:shared-code "$SHARED"
chmod 2770 "$SHARED"

# Set EW ownership recursively
chown -R jarvis:executive-agents "$EW"
chmod -R g+rwX "$EW"
find "$EW" -type d -exec chmod g+s {} +

ok "Directory structure created"

###############################################################################
# Phase 5: Python Virtual Environments
###############################################################################
phase 5 "Python Virtual Environments"

for exec_agent in "${EXECUTIVES[@]}"; do
  VDIR="/home/$exec_agent/venv"
  if [[ ! -d "$VDIR" ]]; then
    python3 -m venv "$VDIR"
  fi
  info "Installing packages for $exec_agent..."
  "$VDIR/bin/pip" install --upgrade pip -q 2>&1 | tail -1
  "$VDIR/bin/pip" install ${VENV_PKGS[$exec_agent]} -q 2>&1 | tail -1
  chown -R "$exec_agent:$(id -gn "$exec_agent")" "$VDIR"
  ok "Venv $exec_agent"
done

###############################################################################
# Phase 6: Copy Files from Repo
###############################################################################
phase 6 "Copy Files from Repo"

copy_if_exists() {
  # $1=source glob/dir, $2=dest dir
  local src="$1" dst="$2"
  mkdir -p "$dst"
  if compgen -G "$src" >/dev/null 2>&1; then
    cp -f $src "$dst/"
    ok "Copied $src → $dst"
  else
    info "Skipped (not found): $src"
  fi
}

# Executive prompts
for exec_agent in "${EXECUTIVES[@]}"; do
  mkdir -p "/home/$exec_agent/member"
  src="$REPO_DIR/agents/executives/$exec_agent/prompt.md"
  [[ -f "$src" ]] && cp -f "$src" "/home/$exec_agent/member/prompt.md" && ok "Prompt: $exec_agent" || info "No prompt for $exec_agent"
  chown -R "$exec_agent:" "/home/$exec_agent/member" 2>/dev/null || true
done

# Sub-agent prompts
for sa in "${SUBAGENTS[@]}"; do
  mkdir -p "/home/$sa/member"
  src="$REPO_DIR/agents/sub-agents/$sa/prompt.md"
  [[ -f "$src" ]] && cp -f "$src" "/home/$sa/member/prompt.md" && ok "Prompt: $sa" || info "No prompt for $sa"
  chown -R "$sa:" "/home/$sa/member" 2>/dev/null || true
done

# Engine, reports, monitoring, knowledge, tools, mcp
copy_if_exists "$REPO_DIR/engine/*.py"      "$EW/engine"
copy_if_exists "$REPO_DIR/reports/*.py"      "$EW/reports"
copy_if_exists "$REPO_DIR/monitoring/*.py"   "$EW/monitoring"
copy_if_exists "$REPO_DIR/knowledge/*.py"    "$EW/knowledge"
copy_if_exists "$REPO_DIR/tools/*.py"        "$EW/tools"
copy_if_exists "$REPO_DIR/mcp/*"             "$EW/mcp"

# APIs
copy_if_exists "$REPO_DIR/apis/registry.json" "$EW/apis"
copy_if_exists "$REPO_DIR/apis/api_client.py" "$EW/apis"
copy_if_exists "$REPO_DIR/apis/api_helpers.sh" "$EW/apis"

# Dashboard
mkdir -p /home/jarvis/dashboard/templates
[[ -f "$REPO_DIR/dashboard/app.py" ]] && cp -f "$REPO_DIR/dashboard/app.py" /home/jarvis/dashboard/
copy_if_exists "$REPO_DIR/dashboard/templates/*" /home/jarvis/dashboard/templates
chown -R jarvis: /home/jarvis/dashboard 2>/dev/null || true

# Scripts
copy_if_exists "$REPO_DIR/scripts/*.sh" "$EW"

# Config → both locations
mkdir -p "$EW/config" "$SHARED/config"
if compgen -G "$REPO_DIR/config/*" >/dev/null 2>&1; then
  cp -f "$REPO_DIR"/config/* "$EW/config/"
  cp -f "$REPO_DIR"/config/* "$SHARED/config/"
  ok "Config files copied"
fi

chown -R jarvis:executive-agents "$EW"

ok "File copy complete"

###############################################################################
# Phase 7: Create .agent_env for all 25 agents
###############################################################################
phase 7 "Create .agent_env Files"

for agent in "${ALL_AGENTS[@]}"; do
  cat > "/home/$agent/.agent_env" << 'AGENTENV'
#!/usr/bin/env bash
# AgentOS Environment — auto-generated by deploy.sh
export AGENTOS_HOME="/home/executive-workspace"
export AGENTOS_ENGINE="$AGENTOS_HOME/engine"
export AGENTOS_APIS="$AGENTOS_HOME/apis"
export AGENTOS_MCP="$AGENTOS_HOME/mcp"
export AGENTOS_KNOWLEDGE="$AGENTOS_HOME/knowledge"
export AGENTOS_TOOLS="$AGENTOS_HOME/tools"

export PATH="$AGENTOS_ENGINE:$AGENTOS_APIS:$AGENTOS_MCP:$AGENTOS_TOOLS:$PATH"
export PYTHONPATH="$AGENTOS_ENGINE:$AGENTOS_APIS:$AGENTOS_MCP:$AGENTOS_KNOWLEDGE:$AGENTOS_TOOLS:${PYTHONPATH:-}"

# Source helpers if they exist
[[ -f "$AGENTOS_APIS/api_helpers.sh" ]] && source "$AGENTOS_APIS/api_helpers.sh"
[[ -f "$AGENTOS_APIS/keys.env" ]]       && source "$AGENTOS_APIS/keys.env"
AGENTENV

  # Add agent-specific venv activation for executives
  for exec_agent in "${EXECUTIVES[@]}"; do
    if [[ "$agent" == "$exec_agent" ]]; then
      echo '[[ -d "$HOME/venv" ]] && source "$HOME/venv/bin/activate"' >> "/home/$agent/.agent_env"
    fi
  done

  chown "$agent:" "/home/$agent/.agent_env"
  chmod 640 "/home/$agent/.agent_env"

  # Auto-source from .bashrc
  grep -q '.agent_env' "/home/$agent/.bashrc" 2>/dev/null || \
    echo '[[ -f "$HOME/.agent_env" ]] && source "$HOME/.agent_env"' >> "/home/$agent/.bashrc"
done

ok "All .agent_env files created"

###############################################################################
# Phase 8: Symlink Shared Libraries into Executive Venvs
###############################################################################
phase 8 "Symlink Shared Libraries"

for exec_agent in "${EXECUTIVES[@]}"; do
  SP=$(find "/home/$exec_agent/venv/lib" -type d -name "site-packages" 2>/dev/null | head -1)
  if [[ -n "$SP" ]]; then
    for lib in "${SHARED_LIBS[@]}"; do
      src="$EW/engine/$lib"
      # Try apis/ and mcp/ and knowledge/ too
      [[ ! -f "$src" && -f "$EW/apis/$lib" ]] && src="$EW/apis/$lib"
      [[ ! -f "$src" && -f "$EW/mcp/$lib" ]] && src="$EW/mcp/$lib"
      [[ ! -f "$src" && -f "$EW/knowledge/$lib" ]] && src="$EW/knowledge/$lib"
      [[ ! -f "$src" && -f "$EW/tools/$lib" ]] && src="$EW/tools/$lib"
      if [[ -f "$src" ]]; then
        ln -sf "$src" "$SP/$lib"
        ok "Linked $lib → $exec_agent"
      else
        info "Source not found: $lib (will link when available)"
        # Create placeholder symlink target
        ln -sf "$EW/engine/$lib" "$SP/$lib" 2>/dev/null || true
      fi
    done
  fi
done

###############################################################################
# Phase 9: Install MCP Servers
###############################################################################
phase 9 "Install MCP Servers"

pip install --break-system-packages mcp mcp-server-fetch mcp-server-git -q 2>&1 | tail -1 || \
  pip install mcp mcp-server-fetch mcp-server-git -q 2>&1 | tail -1 || true
npm install -g @anthropic-ai/mcp-server-filesystem 2>&1 | tail -1 || true

ok "MCP servers installed"

###############################################################################
# Phase 10: API Keys Setup
###############################################################################
phase 10 "API Keys Setup"

KEYS_FILE="$EW/apis/keys.env"
TEMPLATE="$REPO_DIR/apis/keys.env.template"

if [[ ! -f "$KEYS_FILE" ]]; then
  if [[ -f "$TEMPLATE" ]]; then
    cp "$TEMPLATE" "$KEYS_FILE"
  else
    cat > "$KEYS_FILE" << 'EOF'
# AgentOS API Keys
export OPENROUTER_API_KEY=""
EOF
  fi
fi

if [[ -n "$API_KEY" ]]; then
  sed -i "s|^export OPENROUTER_API_KEY=.*|export OPENROUTER_API_KEY=\"$API_KEY\"|" "$KEYS_FILE"
  ok "API key set from argument"
elif grep -q 'OPENROUTER_API_KEY=""' "$KEYS_FILE" 2>/dev/null; then
  info "Enter your OpenRouter API key (or press Enter to skip):"
  read -r key_input </dev/tty 2>/dev/null || key_input=""
  if [[ -n "$key_input" ]]; then
    sed -i "s|^export OPENROUTER_API_KEY=.*|export OPENROUTER_API_KEY=\"$key_input\"|" "$KEYS_FILE"
    ok "API key saved"
  else
    info "Skipped — set OPENROUTER_API_KEY in $KEYS_FILE later"
  fi
fi

chown jarvis:executive-agents "$KEYS_FILE"
chmod 640 "$KEYS_FILE"

###############################################################################
# Phase 11: Initialize Databases
###############################################################################
phase 11 "Initialize Databases"

# Agent registry
REGISTRY_DB="$EW/central_agent_registry.db"
if [[ ! -f "$REGISTRY_DB" ]]; then
  sqlite3 "$REGISTRY_DB" << 'SQL'
CREATE TABLE IF NOT EXISTS agents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL,
  team TEXT,
  status TEXT DEFAULT 'active',
  home_dir TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_seen DATETIME
);
SQL
  for agent in "${EXECUTIVES[@]}"; do
    sqlite3 "$REGISTRY_DB" "INSERT OR IGNORE INTO agents (name,role,team,home_dir) VALUES ('$agent','executive','executive','/home/$agent');"
  done
  for sa in "${SUBAGENTS[@]}"; do
    sqlite3 "$REGISTRY_DB" "INSERT OR IGNORE INTO agents (name,role,team,home_dir) VALUES ('$sa','sub-agent','general','/home/$sa');"
  done
  ok "Agent registry initialized (25 agents)"
fi
chown jarvis:executive-agents "$REGISTRY_DB"

# Task queue
TASK_DB="$EW/engine/task_queue.db"
if [[ ! -f "$TASK_DB" ]]; then
  sqlite3 "$TASK_DB" << 'SQL'
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  assigned_to TEXT,
  created_by TEXT,
  priority INTEGER DEFAULT 5,
  status TEXT DEFAULT 'pending',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  completed_at DATETIME
);
SQL
  ok "Task queue initialized"
fi
chown jarvis:executive-agents "$TASK_DB"

# ChromaDB store directory
mkdir -p "$EW/knowledge/chromadb_store"
chown -R jarvis:executive-agents "$EW/knowledge/chromadb_store"
ok "ChromaDB store directory ready"

# Security integrity baseline
find "$EW" -type f -name "*.py" -exec sha256sum {} + > "$EW/security/integrity_baseline.sha256" 2>/dev/null || true
ok "Security baseline created"

###############################################################################
# Phase 12: Deploy Services
###############################################################################
phase 12 "Deploy Services"

# Copy systemd units if they exist
if compgen -G "$REPO_DIR/services/*.service" >/dev/null 2>&1; then
  cp -f "$REPO_DIR"/services/*.service /etc/systemd/system/
fi
if compgen -G "$REPO_DIR/services/*.timer" >/dev/null 2>&1; then
  cp -f "$REPO_DIR"/services/*.timer /etc/systemd/system/
fi

# Nginx
if [[ -f "$REPO_DIR/nginx/agent-dashboard.conf" ]]; then
  cp -f "$REPO_DIR/nginx/agent-dashboard.conf" /etc/nginx/sites-available/agent-dashboard
  ln -sf /etc/nginx/sites-available/agent-dashboard /etc/nginx/sites-enabled/agent-dashboard
  rm -f /etc/nginx/sites-enabled/default
  ok "Nginx config deployed"
else
  # Create a basic proxy config
  cat > /etc/nginx/sites-available/agent-dashboard << 'NGINX'
server {
    listen 80 default_server;
    server_name _;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX
  ln -sf /etc/nginx/sites-available/agent-dashboard /etc/nginx/sites-enabled/agent-dashboard
  rm -f /etc/nginx/sites-enabled/default
  ok "Default nginx proxy config created"
fi

systemctl daemon-reload

# Enable timers/services if they exist
for svc in agent-dashboard agent-daily-reports.timer agent-health-monitor.timer; do
  if [[ -f "/etc/systemd/system/$svc" ]] || [[ -f "/etc/systemd/system/${svc}.service" ]]; then
    systemctl enable "$svc" 2>/dev/null || true
    systemctl start "$svc" 2>/dev/null || true
    ok "Service $svc enabled"
  else
    info "Service $svc not found in repo — skipped"
  fi
done

systemctl restart nginx 2>/dev/null && ok "Nginx restarted" || info "Nginx restart deferred"

###############################################################################
# Phase 13: Chromium Setup
###############################################################################
phase 13 "Chromium Setup"

CHROMIUM_BIN=""
command -v chromium-browser &>/dev/null && CHROMIUM_BIN=$(command -v chromium-browser)
command -v chromium &>/dev/null && CHROMIUM_BIN=$(command -v chromium)

if [[ -z "$CHROMIUM_BIN" ]]; then
  info "Installing Playwright Chromium to $CHROMIUM_DIR..."
  mkdir -p "$CHROMIUM_DIR"
  PLAYWRIGHT_BROWSERS_PATH="$CHROMIUM_DIR" npx playwright install chromium 2>&1 | tail -3
  # Install system deps for chromium
  npx playwright install-deps chromium 2>&1 | tail -1 || true
  chmod -R a+rX "$CHROMIUM_DIR"
  ok "Playwright Chromium installed at $CHROMIUM_DIR"
else
  ok "System Chromium found: $CHROMIUM_BIN"
fi

# Make accessible to all agents
echo "export PLAYWRIGHT_BROWSERS_PATH=$CHROMIUM_DIR" >> /etc/environment

###############################################################################
# Phase 14: Git Init shared-repo
###############################################################################
phase 14 "Git Init shared-repo"

if [[ ! -d "$SHARED/.git" ]]; then
  git init "$SHARED" >/dev/null
  ok "Initialized git repo at $SHARED"
fi
git config --system safe.directory '*' 2>/dev/null || git config --global safe.directory '*'
chown -R ubuntu:shared-code "$SHARED"
ok "Git configured"

###############################################################################
# Phase 15: Validation
###############################################################################
if [[ "$SKIP_VALIDATION" == true ]]; then
  info "Skipping validation (--skip-validation)"
else
  phase 15 "Validation"
  PASS=0; FAIL_COUNT=0

  check() {
    if eval "$2" &>/dev/null; then
      ok "PASS: $1"; ((PASS++))
    else
      fail "FAIL: $1"; ((FAIL_COUNT++))
    fi
  }

  # 1. All 25 users exist
  for agent in "${ALL_AGENTS[@]}"; do
    check "User $agent exists" "id $agent"
  done

  # 2. All 7 groups exist
  for grp in "${!GROUPS[@]}"; do
    check "Group $grp exists" "getent group $grp"
  done

  # 3. Home dir permissions (750)
  for agent in "${ALL_AGENTS[@]}"; do
    check "Home $agent perms 750" "[[ \$(stat -c '%a' /home/$agent) == '750' ]]"
  done

  # 4. Venvs work
  check "Jarvis venv flask" "/home/jarvis/venv/bin/python3 -c 'import flask'"
  check "Tesla venv pandas" "/home/tesla/venv/bin/python3 -c 'import pandas'"
  check "Warren venv pandas" "/home/warren/venv/bin/python3 -c 'import pandas'"
  check "Steve venv pandas" "/home/steve/venv/bin/python3 -c 'import pandas'"
  check "Tony venv pandas" "/home/tony/venv/bin/python3 -c 'import pandas'"

  # 5. Prompts exist (check executives)
  for exec_agent in "${EXECUTIVES[@]}"; do
    check "Prompt $exec_agent" "[[ -f /home/$exec_agent/member/prompt.md ]]"
  done

  # 6. .agent_env files
  for agent in "${ALL_AGENTS[@]}"; do
    check ".agent_env $agent" "[[ -f /home/$agent/.agent_env ]]"
  done

  # 7. Dashboard on port 80
  check "Dashboard HTTP 200" "curl -sf -o /dev/null http://localhost:80/"

  # 8. Engine files
  check "Engine dir has files" "ls $EW/engine/*.py 2>/dev/null"

  # 9. SQLite DBs
  check "Agent registry DB" "[[ -f $EW/central_agent_registry.db ]]"
  check "Task queue DB" "[[ -f $EW/engine/task_queue.db ]]"

  # 10. Systemd services
  check "Nginx active" "systemctl is-active nginx"

  echo ""
  echo -e "${BOLD}═══════════════════════════════════════${NC}"
  echo -e "${GREEN}  PASSED: $PASS${NC}  |  ${RED}FAILED: $FAIL_COUNT${NC}"
  echo -e "${BOLD}═══════════════════════════════════════${NC}"
fi

###############################################################################
# Done
###############################################################################
echo ""
echo -e "${GREEN}${BOLD}╔═══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║   AgentOS Deployment Complete! 🚀         ║${NC}"
echo -e "${GREEN}${BOLD}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Log:       ${LOGFILE}"
echo -e "  Workspace: ${EW}"
echo -e "  Dashboard: http://$(hostname -I | awk '{print $1}'):80"
echo -e "  Agents:    ${#ALL_AGENTS[@]}"
echo ""
