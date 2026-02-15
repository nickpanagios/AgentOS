# AgentOS — 31-Agent AI Operating System

A complete multi-agent AI system with 6 executive agents and 25 specialized sub-agents, organized into technology, finance, marketing, legal, and sales teams.

## Architecture

```
Nikolas (Human Principal)
  └── Jarvis (COO/CPO/CSO/CCO)
        ├── Tesla (CTO/CIO)   → 6 tech sub-agents
        ├── Warren (CFO/CAO)  → 4 finance sub-agents
        ├── Steve (CMO)       → 5 marketing sub-agents
        ├── Tony (CLO)        → 5 legal sub-agents
        └── Jordan (CSO)      → 5 sales sub-agents
```

### Executive Team

| Agent | Role | Team Size |
|-------|------|-----------|
| **Jarvis** | COO/CPO/CSO/CCO — Central orchestrator | Oversees all |
| **Tesla** | CTO/CIO — Technology & infrastructure | 6 sub-agents |
| **Warren** | CFO/CAO — Finance & administration | 4 sub-agents |
| **Steve** | CMO — Marketing & brand | 5 sub-agents |
| **Tony** | CLO — Legal & compliance | 5 sub-agents |
| **Jordan** | CSO — Sales & revenue | 5 sub-agents |

### Sub-Agents by Team

**Tesla's Team (Tech):** backend, frontend, ai-mlops, devops-engineer, security-engineer, data-engineer

**Warren's Team (Finance):** financial-analyst, accounting-specialist, resource-manager, administrative-coordinator

**Steve's Team (Marketing):** brand-strategist, content-creator, social-media-manager, seo-specialist, analytics-expert

**Tony's Team (Legal):** contract-specialist, compliance-analyst, intellectual-property, litigation-support, corporate-governance

**Jordan's Team (Sales):** sales-director, account-executive, business-development, client-success, sales-operations

## Quick Start

```bash
# 1. Clone and deploy
git clone <repo-url> agentos && cd agentos
sudo bash deploy.sh

# 2. Configure API keys
sudo nano /home/executive-workspace/apis/keys.env

# 3. Start services
sudo systemctl start agent-dashboard
sudo systemctl start agent-daily-reports.timer
sudo systemctl start agent-health-monitor.timer
```

## Components

| Directory | Purpose |
|-----------|---------|
| `agents/` | All 31 agent prompts (executives + sub-agents) |
| `engine/` | LLM client with fallback chain, agent executor, orchestrator |
| `scripts/` | Inter-agent messaging, task assignment, auditing |
| `reports/` | Daily briefings (general, financial, tech) |
| `dashboard/` | Web UI for agent monitoring |
| `apis/` | 53-API registry with unified client |
| `mcp/` | Model Context Protocol integration |
| `monitoring/` | Health checks for all agents |
| `config/` | Agent definitions, model configs, API registry |
| `services/` | systemd unit files |
| `nginx/` | Reverse proxy configuration |
| `knowledge/` | ChromaDB knowledge base setup |
| `tools/` | Shared tools (screenshot, browser automation) |

## LLM Strategy

All inference routes through **OpenRouter** with a free-tier fallback chain:
1. Kimi K2.5 → 2. MiniMax M2.5 → 3. Trinity → 4. Aurora → ... → 11. Free Router

Paid models require explicit human authorization.

## Requirements

- Ubuntu 22.04 or 24.04
- Python 3.10+
- 4GB+ RAM recommended
- OpenRouter API key (free tier sufficient)

## License

Private — All rights reserved.
