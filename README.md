# AgentOS — 25-Agent AI Operating System

A complete multi-agent AI system with 5 executive agents and 20 specialized sub-agents, organized into technology, finance, marketing, and legal teams.

## Architecture

```
Nikolas (Human Principal)
  └── Jarvis (COO/CPO/CSO/CCO)
        ├── Tesla (CTO/CIO) → 6 tech sub-agents
        ├── Warren (CFO/CAO) → 4 finance sub-agents
        ├── Steve (CMO) → 5 marketing sub-agents
        └── Tony (CLO) → 5 legal sub-agents
```

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
| `engine/` | LLM client with fallback chain, agent executor, orchestrator |
| `scripts/` | Inter-agent messaging, task assignment, auditing |
| `reports/` | Daily briefings (general, financial, tech) |
| `dashboard/` | Web UI for agent monitoring |
| `apis/` | 53-API registry with unified client |
| `mcp/` | Model Context Protocol integration |
| `monitoring/` | Health checks for all agents |
| `config/` | Agent definitions, model configs, API registry |

## LLM Strategy

All inference routes through **OpenRouter** with a free-tier fallback chain:
1. Kimi K2.5 → 2. MiniMax M2.5 → 3. Trinity → 4. Aurora → ... → 11. Free Router

Paid models require explicit human authorization.

## License

Private — All rights reserved.
