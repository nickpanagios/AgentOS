#!/usr/bin/env python3
"""
Orchestrator — Jarvis's task dispatch brain.

Takes a high-level directive, breaks it into subtasks, routes to the right
agents based on specialization, monitors progress, and consolidates results.

Usage:
    from orchestrator import Orchestrator
    orch = Orchestrator()
    
    # Dispatch a directive
    results = orch.dispatch("Prepare a full market analysis for entering the healthcare AI space")
    
    # Or step by step
    plan = orch.plan("Prepare a full market analysis for healthcare AI")
    results = orch.execute_plan(plan)
    summary = orch.consolidate(results)
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

Available agents and their capabilities:
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

Directive: {directive}

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

    def plan(self, directive: str) -> dict:
        """Break a directive into subtasks with agent assignments."""
        agents_desc = "\n".join(
            f"  - {name}: {', '.join(caps)}"
            for name, caps in sorted(AGENT_CAPABILITIES.items())
        )
        
        system = PLANNING_PROMPT.format(agents=agents_desc)
        response = self.llm.chat(directive, system=system, task="reasoning", temperature=0.3)
        
        # Parse JSON from response
        try:
            # Try to extract JSON from response
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            plan = json.loads(response.strip())
        except json.JSONDecodeError:
            # If parsing fails, create a simple single-task plan
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
        
        return plan

    def execute_plan(self, plan: dict, parallel: bool = False) -> List[dict]:
        """Execute all subtasks in a plan. Returns list of results."""
        results = []
        completed_ids = set()
        subtasks = plan.get("subtasks", [])
        
        # Sort by dependency order (tasks with no deps first)
        remaining = list(subtasks)
        
        while remaining:
            # Find tasks whose dependencies are met
            ready = [t for t in remaining if all(d in completed_ids for d in t.get("depends_on", []))]
            
            if not ready:
                # Circular dependency or error — just run everything remaining
                ready = remaining
            
            for task in ready:
                agent = task["assigned_to"]
                print(f"  [{task['id']}] Dispatching to {agent}: {task['title']}")
                
                executor = AgentExecutor(agent)
                result = executor.run(
                    task=f"{task['title']}\n\n{task['description']}",
                    task_type=task.get("task_type", "general")
                )
                result["task_id"] = task["id"]
                result["title"] = task["title"]
                results.append(result)
                completed_ids.add(task["id"])
                
                print(f"  [{task['id']}] {result['status']} ({result['iterations']} iterations, model: {result['model_used']})")
            
            remaining = [t for t in remaining if t["id"] not in completed_ids]
        
        return results

    def consolidate(self, directive: str, results: List[dict]) -> str:
        """Consolidate results into an executive summary."""
        results_text = "\n\n".join(
            f"### Task {r.get('task_id', '?')}: {r.get('title', 'Unknown')} (Agent: {r['agent']})\n"
            f"Status: {r['status']}\n"
            f"Result: {r.get('result', 'N/A')[:500]}"
            for r in results
        )
        
        system = CONSOLIDATION_PROMPT.format(directive=directive, results=results_text)
        return self.llm.chat("Consolidate these results.", system=system, task="summarization")

    def dispatch(self, directive: str, dry_run: bool = False) -> dict:
        """
        Full pipeline: plan → execute → consolidate.
        
        Returns: {
            "directive": str,
            "plan": dict,
            "results": list,
            "summary": str,
            "total_iterations": int,
            "agents_used": list
        }
        """
        print(f"\n{'='*60}")
        print(f"DIRECTIVE: {directive}")
        print(f"{'='*60}")
        
        # Plan
        print("\n📋 Planning...")
        plan = self.plan(directive)
        print(f"  Plan: {plan.get('plan_summary', 'N/A')}")
        print(f"  Subtasks: {len(plan.get('subtasks', []))}")
        
        for t in plan.get("subtasks", []):
            deps = f" (after: {t['depends_on']})" if t.get("depends_on") else ""
            print(f"    [{t['id']}] {t['assigned_to']:20s} → {t['title']}{deps}")
        
        if dry_run:
            return {"directive": directive, "plan": plan, "results": [], "summary": "DRY RUN"}
        
        # Execute
        print("\n🚀 Executing...")
        results = self.execute_plan(plan)
        
        # Consolidate
        print("\n📊 Consolidating...")
        summary = self.consolidate(directive, results)
        
        total_iters = sum(r.get("iterations", 0) for r in results)
        agents_used = list(set(r["agent"] for r in results))
        
        output = {
            "directive": directive,
            "plan": plan,
            "results": results,
            "summary": summary,
            "total_iterations": total_iters,
            "agents_used": agents_used
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
                "agents": agents_used,
                "tasks": len(plan.get("subtasks", [])),
                "iterations": total_iters,
                "status": "completed"
            })
            with open(log_path, "w") as f:
                json.dump(logs[-50:], f, indent=2)  # Keep last 50
        except:
            pass
        
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(summary)
        print(f"\nAgents: {', '.join(agents_used)} | Iterations: {total_iters}")
        
        return output

    def queue_directive(self, directive: str) -> dict:
        """Plan and queue subtasks (don't execute immediately)."""
        plan = self.plan(directive)
        task_ids = []
        
        for t in plan.get("subtasks", []):
            tid = enqueue_task(
                title=t["title"],
                description=t["description"],
                assigned_to=t["assigned_to"],
                task_type=t.get("task_type", "general"),
                priority=t.get("priority", "MEDIUM")
            )
            task_ids.append(tid)
            print(f"  Queued [{tid}] → {t['assigned_to']}: {t['title']}")
        
        return {"plan": plan, "task_ids": task_ids}


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("""
Orchestrator — Jarvis's command center.

Usage:
  python3 orchestrator.py dispatch "Your directive here"
  python3 orchestrator.py plan "Your directive here"        # Plan only (dry run)
  python3 orchestrator.py queue "Your directive here"       # Plan + queue (no execute)
  python3 orchestrator.py process <agent>                   # Process queued tasks for agent
  python3 orchestrator.py status                            # Show queue status

Examples:
  python3 orchestrator.py dispatch "Analyze our current security posture and write a report"
  python3 orchestrator.py plan "Build a landing page for our new AI product"
  python3 orchestrator.py queue "Prepare quarterly financial projections"
""")
        sys.exit(0)
    
    cmd = sys.argv[1]
    orch = Orchestrator()
    
    if cmd == "dispatch" and len(sys.argv) >= 3:
        directive = " ".join(sys.argv[2:])
        result = orch.dispatch(directive)
    
    elif cmd == "plan" and len(sys.argv) >= 3:
        directive = " ".join(sys.argv[2:])
        result = orch.dispatch(directive, dry_run=True)
    
    elif cmd == "queue" and len(sys.argv) >= 3:
        directive = " ".join(sys.argv[2:])
        result = orch.queue_directive(directive)
        print(f"\n{len(result['task_ids'])} tasks queued.")
    
    elif cmd == "process" and len(sys.argv) >= 3:
        agent = sys.argv[2]
        result = process_next_task(agent)
        if result:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"No pending tasks for {agent}")
    
    elif cmd == "status":
        for status in ["pending", "active", "completed", "failed"]:
            tasks = list_tasks(status=status)
            if tasks:
                print(f"\n{status.upper()} ({len(tasks)}):")
                for t in tasks:
                    print(f"  [{t['id']}] {t['assigned_to']:20s} {t['priority']:8s} {t['title']}")
    
    else:
        print(f"Unknown command: {cmd}")
