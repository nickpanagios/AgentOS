#!/usr/bin/env python3
"""
Orchestrator — Jarvis's task dispatch brain.

Takes a high-level directive, breaks it into subtasks, routes to the right
agents based on specialization, monitors progress, and consolidates results.

Supports project namespacing: all operations can be scoped to a project.

Usage:
    from orchestrator import Orchestrator
    orch = Orchestrator()
    
    # Dispatch a directive within a project
    results = orch.dispatch("Prepare Q2 analysis", project="acme-corp")
    
    # Or step by step
    plan = orch.plan("Prepare a full market analysis for healthcare AI", project="personal")
    results = orch.execute_plan(plan, project="personal")
    summary = orch.consolidate("...", results, project="personal")
"""

import json
import os
import sys
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, "/home/executive-workspace/engine")
from llm_client import LLMClient
from agent_executor import AgentExecutor, AGENT_HOMES, enqueue_task, init_queue, list_tasks, process_next_task

# ── Agent Capability Map ─────────────────────────────────────────────────

AGENT_CAPABILITIES = {
    # Executives
    "tesla":  ["technology", "engineering", "infrastructure", "security", "devops", "ai", "coding", "architecture"],
    "warren": ["finance", "budgeting", "accounting", "resource_management", "administration", "cost_analysis"],
    "steve":  ["marketing", "branding", "content", "social_media", "seo", "analytics", "growth"],
    "tony":   ["legal", "compliance", "contracts", "ip", "governance", "risk", "regulatory"],
    
    # Tesla's team
    "backend":           ["api", "server", "database", "python", "backend_dev"],
    "frontend":          ["ui", "ux", "web", "react", "frontend_dev"],
    "ai-mlops":          ["ml", "ai", "training", "models", "mlops", "data_science"],
    "devops-engineer":   ["ci_cd", "deployment", "docker", "kubernetes", "monitoring"],
    "security-engineer": ["security", "penetration_testing", "vulnerabilities", "audit"],
    "data-engineer":     ["data_pipelines", "etl", "databases", "data_modeling"],
    
    # Warren's team
    "financial-analyst":          ["financial_analysis", "forecasting", "valuation", "investment"],
    "accounting-specialist":      ["bookkeeping", "tax", "audit", "financial_reporting"],
    "resource-manager":           ["hr", "staffing", "procurement", "budgeting"],
    "administrative-coordinator": ["scheduling", "coordination", "documentation", "filing"],
    
    # Steve's team
    "brand-strategist":      ["branding", "positioning", "market_research", "strategy"],
    "content-creator":       ["writing", "copywriting", "blog", "newsletter"],
    "social-media-manager":  ["social_media", "community", "engagement", "campaigns"],
    "seo-specialist":        ["seo", "keywords", "search_ranking", "technical_seo"],
    "analytics-expert":      ["analytics", "metrics", "reporting", "data_visualization"],
    
    # Tony's team
    "contract-specialist":   ["contracts", "negotiations", "terms", "agreements"],
    "compliance-analyst":    ["compliance", "regulations", "policy", "standards"],
    "intellectual-property": ["patents", "trademarks", "copyright", "ip_strategy"],
    "litigation-support":    ["litigation", "disputes", "evidence", "legal_research"],
    "corporate-governance":  ["governance", "board", "bylaws", "corporate_structure"],
}

PLANNING_PROMPT = """You are Jarvis, the Chief Operating Officer of a multi-agent AI organization.
You must decompose a directive into concrete subtasks and assign each to the most appropriate agent.

{project_context}Available agents and their capabilities:
{agents}

RULES:
1. Break the directive into 2-8 specific, actionable subtasks
2. Assign each subtask to ONE agent best suited for it
3. Identify dependencies (which tasks must finish before others can start)
4. Set priority: CRITICAL > HIGH > MEDIUM > LOW
5. Set task_type for model selection: coding, analysis, financial, legal_analysis, marketing, writing, research, general

Respond in EXACT JSON format:
{{
  "plan_summary": "Brief description of the execution plan",
  "subtasks": [
    {{
      "id": 1,
      "title": "Short task title",
      "description": "Detailed description of what to do",
      "assigned_to": "agent_name",
      "task_type": "type",
      "priority": "HIGH",
      "depends_on": [],
      "estimated_minutes": 5
    }}
  ]
}}"""

CONSOLIDATION_PROMPT = """You are Jarvis. Consolidate these results from your team into a clear executive summary.

{project_context}Directive: {directive}

Results:
{results}

Provide:
1. Executive summary (2-3 sentences)
2. Key findings
3. Action items
4. Any issues or blockers"""


class Orchestrator:
    """Jarvis's task planning and dispatch engine."""

    def __init__(self):
        self.llm = LLMClient()
        init_queue()

    def plan(self, directive: str, project: str = None) -> dict:
        """Break a directive into subtasks with agent assignments."""
        agents_desc = "\n".join(
            f"  - {name}: {', '.join(caps)}"
            for name, caps in sorted(AGENT_CAPABILITIES.items())
        )
        
        project_context = ""
        if project and project != "default":
            project_context = f"**Project Context:** You are planning within the '{project}' project. All tasks should be scoped to this project.\n\n"
        
        system = PLANNING_PROMPT.format(agents=agents_desc, project_context=project_context)
        response = self.llm.chat(directive, system=system, task="reasoning", temperature=0.3)
        
        # Parse JSON from response
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            plan = json.loads(response.strip())
        except json.JSONDecodeError:
            plan = {
                "plan_summary": "Direct execution",
                "subtasks": [{
                    "id": 1,
                    "title": directive[:100],
                    "description": directive,
                    "assigned_to": "tesla",
                    "task_type": "general",
                    "priority": "MEDIUM",
                    "depends_on": [],
                    "estimated_minutes": 10
                }]
            }
        
        if project:
            plan["project"] = project
        return plan

    def execute_plan(self, plan: dict, parallel: bool = False, project: str = None) -> List[dict]:
        """Execute all subtasks in a plan. Returns list of results."""
        results = []
        completed_ids = set()
        subtasks = plan.get("subtasks", [])
        proj = project or plan.get("project", "default")
        
        remaining = list(subtasks)
        
        while remaining:
            ready = [t for t in remaining if all(d in completed_ids for d in t.get("depends_on", []))]
            
            if not ready:
                ready = remaining
            
            for task in ready:
                agent = task["assigned_to"]
                proj_tag = f" [{proj}]" if proj and proj != "default" else ""
                print(f"  [{task['id']}] Dispatching to {agent}{proj_tag}: {task['title']}")
                
                executor = AgentExecutor(agent)
                result = executor.run(
                    task=f"{task['title']}\n\n{task['description']}",
                    task_type=task.get("task_type", "general"),
                    project=proj
                )
                result["task_id"] = task["id"]
                result["title"] = task["title"]
                results.append(result)
                completed_ids.add(task["id"])
                
                print(f"  [{task['id']}] {result['status']} ({result['iterations']} iterations, model: {result['model_used']})")
            
            remaining = [t for t in remaining if t["id"] not in completed_ids]
        
        return results

    def consolidate(self, directive: str, results: List[dict], project: str = None) -> str:
        """Consolidate results into an executive summary."""
        results_text = "\n\n".join(
            f"### Task {r.get('task_id', '?')}: {r.get('title', 'Unknown')} (Agent: {r['agent']})\n"
            f"Status: {r['status']}\n"
            f"Result: {r.get('result', 'N/A')[:500]}"
            for r in results
        )
        
        project_context = ""
        if project and project != "default":
            project_context = f"**Project:** {project}\n\n"
        
        system = CONSOLIDATION_PROMPT.format(
            directive=directive, results=results_text, project_context=project_context)
        return self.llm.chat("Consolidate these results.", system=system, task="summarization")

    def dispatch(self, directive: str, dry_run: bool = False, project: str = None) -> dict:
        """
        Full pipeline: plan → execute → consolidate.
        """
        proj = project or "default"
        proj_tag = f" [{proj}]" if proj != "default" else ""
        
        print(f"\n{'='*60}")
        print(f"DIRECTIVE{proj_tag}: {directive}")
        print(f"{'='*60}")
        
        # Plan
        print("\n📋 Planning...")
        plan = self.plan(directive, project=proj)
        print(f"  Plan: {plan.get('plan_summary', 'N/A')}")
        print(f"  Subtasks: {len(plan.get('subtasks', []))}")
        
        for t in plan.get("subtasks", []):
            deps = f" (after: {t['depends_on']})" if t.get("depends_on") else ""
            print(f"    [{t['id']}] {t['assigned_to']:20s} → {t['title']}{deps}")
        
        if dry_run:
            return {"directive": directive, "plan": plan, "results": [], "summary": "DRY RUN", "project": proj}
        
        # Execute
        print("\n🚀 Executing...")
        results = self.execute_plan(plan, project=proj)
        
        # Consolidate
        print("\n📊 Consolidating...")
        summary = self.consolidate(directive, results, project=proj)
        
        total_iters = sum(r.get("iterations", 0) for r in results)
        agents_used = list(set(r["agent"] for r in results))
        
        output = {
            "directive": directive,
            "plan": plan,
            "results": results,
            "summary": summary,
            "total_iterations": total_iters,
            "agents_used": agents_used,
            "project": proj
        }
        
        # Save to log
        log_path = "/home/executive-workspace/engine/dispatch_log.json"
        try:
            logs = []
            if os.path.exists(log_path):
                with open(log_path) as f:
                    logs = json.load(f)
            logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "directive": directive,
                "project": proj,
                "agents": agents_used,
                "tasks": len(plan.get("subtasks", [])),
                "iterations": total_iters,
                "status": "completed"
            })
            with open(log_path, "w") as f:
                json.dump(logs[-50:], f, indent=2)
        except:
            pass
        
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(summary)
        print(f"\nProject: {proj} | Agents: {', '.join(agents_used)} | Iterations: {total_iters}")
        
        return output

    def queue_directive(self, directive: str, project: str = None) -> dict:
        """Plan and queue subtasks (don't execute immediately)."""
        proj = project or "default"
        plan = self.plan(directive, project=proj)
        task_ids = []
        
        for t in plan.get("subtasks", []):
            tid = enqueue_task(
                title=t["title"],
                description=t["description"],
                assigned_to=t["assigned_to"],
                task_type=t.get("task_type", "general"),
                priority=t.get("priority", "MEDIUM"),
                project=proj
            )
            task_ids.append(tid)
            print(f"  Queued [{tid}] → {t['assigned_to']}: {t['title']} (project: {proj})")
        
        return {"plan": plan, "task_ids": task_ids, "project": proj}


# ── CLI ──────────────────────────────────────────────────────────────────

def _extract_flag(args, flag, default=None):
    """Extract --flag value from args list."""
    remaining = []
    value = default
    i = 0
    while i < len(args):
        if args[i] == flag and i + 1 < len(args):
            value = args[i + 1]
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    return value, remaining


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
Orchestrator — Jarvis's command center.

Usage:
  python3 orchestrator.py dispatch "Your directive here" [--project PROJECT]
  python3 orchestrator.py plan "Your directive here" [--project PROJECT]
  python3 orchestrator.py queue "Your directive here" [--project PROJECT]
  python3 orchestrator.py process <agent> [--project PROJECT]
  python3 orchestrator.py status [--project PROJECT]

Examples:
  python3 orchestrator.py dispatch --project "acme-corp" "Prepare Q2 financial analysis"
  python3 orchestrator.py dispatch --project "personal" "Research best CRM tools"
  python3 orchestrator.py plan "Build a landing page for our new AI product"
  python3 orchestrator.py queue "Prepare quarterly financial projections" --project acme-corp
""")
        sys.exit(0)
    
    cmd = sys.argv[1]
    remaining = sys.argv[2:]
    project, remaining = _extract_flag(remaining, "--project")
    
    orch = Orchestrator()
    
    if cmd == "dispatch" and remaining:
        directive = " ".join(remaining)
        result = orch.dispatch(directive, project=project)
    
    elif cmd == "plan" and remaining:
        directive = " ".join(remaining)
        result = orch.dispatch(directive, dry_run=True, project=project)
    
    elif cmd == "queue" and remaining:
        directive = " ".join(remaining)
        result = orch.queue_directive(directive, project=project)
        print(f"\n{len(result['task_ids'])} tasks queued (project: {result['project']}).")
    
    elif cmd == "process" and remaining:
        agent = remaining[0]
        result = process_next_task(agent, project=project)
        if result:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"No pending tasks for {agent}" + (f" in project {project}" if project else ""))
    
    elif cmd == "status":
        for status in ["pending", "active", "completed", "failed"]:
            tasks = list_tasks(status=status, project=project)
            if tasks:
                proj_filter = f" (project: {project})" if project else ""
                print(f"\n{status.upper()} ({len(tasks)}){proj_filter}:")
                for t in tasks:
                    proj_tag = f" [{t.get('project','default')}]" if not project else ""
                    print(f"  [{t['id']}] {t['assigned_to']:20s} {t['priority']:8s} {t['title']}{proj_tag}")
    
    else:
        print(f"Unknown command: {cmd}")
