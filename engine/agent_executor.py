#!/usr/bin/env python3
"""
Agent Executor — The brain that makes agents think and act.

Each agent has:
  - A persona (from their prompt.md)
  - Tools (APIs, MCPs, shell commands)
  - An LLM (selected per task)

The executor:
  1. Loads the agent's prompt/persona
  2. Receives a task
  3. Selects the best model
  4. Runs an agentic loop: think → decide → act → observe → repeat
  5. Returns the result

Usage:
    from agent_executor import AgentExecutor
    
    executor = AgentExecutor("tesla")
    result = executor.run("Set up a CI/CD pipeline for the shared repo")
    
    # Or with specific task type
    result = executor.run("Review this code for security issues", task_type="code_review")
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, "/home/executive-workspace/engine")
sys.path.insert(0, "/home/executive-workspace/apis")
sys.path.insert(0, "/home/executive-workspace/mcp")

from llm_client import LLMClient, MODELS, TASK_MODEL_MAP

# ── Agent Definitions ────────────────────────────────────────────────────

AGENT_HOMES = {
    # Executives
    "jarvis": {"home": "/home/jarvis", "type": "executive", "team": "central"},
    "tesla":  {"home": "/home/tesla",  "type": "executive", "team": "tesla"},
    "warren": {"home": "/home/warren", "type": "executive", "team": "warren"},
    "steve":  {"home": "/home/steve",  "type": "executive", "team": "steve"},
    "tony":   {"home": "/home/tony",   "type": "executive", "team": "tony"},
    # Sub-agents
    "backend":           {"home": "/home/backend",           "type": "sub", "team": "tesla"},
    "frontend":          {"home": "/home/frontend",          "type": "sub", "team": "tesla"},
    "ai-mlops":          {"home": "/home/ai-mlops",          "type": "sub", "team": "tesla"},
    "devops-engineer":   {"home": "/home/devops-engineer",   "type": "sub", "team": "tesla"},
    "security-engineer": {"home": "/home/security-engineer", "type": "sub", "team": "tesla"},
    "data-engineer":     {"home": "/home/data-engineer",     "type": "sub", "team": "tesla"},
    "financial-analyst":         {"home": "/home/financial-analyst",         "type": "sub", "team": "warren"},
    "accounting-specialist":     {"home": "/home/accounting-specialist",     "type": "sub", "team": "warren"},
    "resource-manager":          {"home": "/home/resource-manager",          "type": "sub", "team": "warren"},
    "administrative-coordinator":{"home": "/home/administrative-coordinator","type": "sub", "team": "warren"},
    "brand-strategist":      {"home": "/home/brand-strategist",      "type": "sub", "team": "steve"},
    "content-creator":       {"home": "/home/content-creator",       "type": "sub", "team": "steve"},
    "social-media-manager":  {"home": "/home/social-media-manager",  "type": "sub", "team": "steve"},
    "seo-specialist":        {"home": "/home/seo-specialist",        "type": "sub", "team": "steve"},
    "analytics-expert":      {"home": "/home/analytics-expert",      "type": "sub", "team": "steve"},
    "contract-specialist":   {"home": "/home/contract-specialist",   "type": "sub", "team": "tony"},
    "compliance-analyst":    {"home": "/home/compliance-analyst",    "type": "sub", "team": "tony"},
    "intellectual-property": {"home": "/home/intellectual-property", "type": "sub", "team": "tony"},
    "litigation-support":    {"home": "/home/litigation-support",    "type": "sub", "team": "tony"},
    "corporate-governance":  {"home": "/home/corporate-governance",  "type": "sub", "team": "tony"},
}

# Tools available to agents (as OpenAI-compatible function definitions)
AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Execute a shell command and return the output. Use for file operations, system queries, running scripts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"},
                    "cwd": {"type": "string", "description": "Working directory (optional)"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                    "max_lines": {"type": "integer", "description": "Max lines to read (default 200)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to write"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch a URL and return its content as text/markdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                    "max_length": {"type": "integer", "description": "Max characters (default 5000)"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "api_call",
            "description": "Call a public API from the agent's API registry. Returns JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full API URL to call"},
                    "method": {"type": "string", "description": "HTTP method (GET/POST)", "default": "GET"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a message to another agent in the organization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Agent name to send to"},
                    "subject": {"type": "string", "description": "Message subject"},
                    "body": {"type": "string", "description": "Message body"},
                    "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "report_result",
            "description": "Report the final result of your task. Call this when you have completed the assigned task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["completed", "partial", "failed", "blocked"]},
                    "summary": {"type": "string", "description": "Brief summary of what was accomplished"},
                    "details": {"type": "string", "description": "Detailed output or findings"},
                    "artifacts": {"type": "array", "items": {"type": "string"}, "description": "List of files created/modified"}
                },
                "required": ["status", "summary"]
            }
        }
    }
]


class AgentExecutor:
    """Executes tasks as a specific agent with LLM-powered reasoning."""
    
    def __init__(self, agent_name: str, api_key: Optional[str] = None):
        if agent_name not in AGENT_HOMES:
            raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENT_HOMES.keys())}")
        
        self.agent_name = agent_name
        self.agent_info = AGENT_HOMES[agent_name]
        self.llm = LLMClient(api_key=api_key)
        self.prompt = self._load_prompt()
        self.max_iterations = 10
        self.log = []
    
    def _load_prompt(self) -> str:
        """Load agent's personality/prompt from their prompt.md file."""
        prompt_path = os.path.join(self.agent_info["home"], "member", "prompt.md")
        try:
            with open(prompt_path) as f:
                return f.read()
        except:
            return f"You are {self.agent_name}, an agent in a multi-agent organization."
    
    def _build_system_prompt(self, task_context: str = "") -> str:
        """Build the full system prompt for the agent."""
        return f"""{self.prompt}

## Execution Context
You are executing a task within the AgentOS multi-agent system.
- Your home directory: {self.agent_info['home']}
- Your team: {self.agent_info['team']}
- Shared workspace: /home/executive-workspace
- Shared repo: /home/ubuntu/shared-repo
- Current time: {datetime.utcnow().isoformat()}Z

## Available Resources
- Public APIs: /home/executive-workspace/apis/ (53 free APIs)
- MCP Servers: /home/executive-workspace/mcp/ (fetch, git, filesystem)
- Team workspace: /home/executive-workspace/teams/{self.agent_info['team']}/

## Instructions
1. Analyze the task carefully
2. Use tools to gather information and take actions
3. When done, call report_result with your findings
4. Be thorough but efficient — minimize unnecessary tool calls
5. IMPORTANT: You MUST call report_result when finished. This is how your work gets recorded.
6. If you have enough information, stop gathering and call report_result immediately.
7. Maximum {max_iter} tool calls allowed — plan accordingly.
{task_context}"""
    
    def _execute_tool(self, name: str, args: dict) -> str:
        """Execute a tool call and return the result."""
        try:
            if name == "run_shell":
                cmd = args.get("command", "")
                cwd = args.get("cwd", self.agent_info["home"])
                result = subprocess.run(
                    ["sudo", "-u", self.agent_name, "bash", "-c", cmd],
                    capture_output=True, text=True, timeout=30, cwd=cwd
                )
                output = result.stdout[:3000]
                if result.stderr:
                    output += f"\nSTDERR: {result.stderr[:500]}"
                return output or "(no output)"
            
            elif name == "read_file":
                path = args.get("path", "")
                max_lines = args.get("max_lines", 200)
                with open(path) as f:
                    lines = f.readlines()[:max_lines]
                return "".join(lines)[:5000]
            
            elif name == "write_file":
                path = args.get("path", "")
                content = args.get("content", "")
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(content)
                return f"Written {len(content)} bytes to {path}"
            
            elif name == "fetch_url":
                url = args.get("url", "")
                max_length = args.get("max_length", 5000)
                req = urllib.request.Request(url, headers={"User-Agent": f"AgentOS/{self.agent_name}"})
                import urllib.request
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode()[:max_length]
            
            elif name == "api_call":
                url = args.get("url", "")
                req = urllib.request.Request(url, headers={"User-Agent": f"AgentOS/{self.agent_name}"})
                import urllib.request
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return resp.read().decode()[:5000]
            
            elif name == "send_message":
                to = args.get("to", "")
                subject = args.get("subject", "")
                body = args.get("body", "")
                priority = args.get("priority", "MEDIUM")
                result = subprocess.run(
                    ["sudo", "-u", self.agent_name, 
                     "/home/executive-workspace/send_message.sh",
                     self.agent_name, to, subject, priority],
                    input=body, capture_output=True, text=True, timeout=10
                )
                return f"Message sent to {to}: {subject}"
            
            elif name == "report_result":
                # This is handled by the main loop
                return json.dumps(args)
            
            else:
                return f"Unknown tool: {name}"
                
        except Exception as e:
            return f"Tool error ({name}): {str(e)}"
    
    def run(self, task: str, task_type: Optional[str] = None, 
            model: Optional[str] = None) -> dict:
        """
        Execute a task as this agent.
        
        Returns: {
            "agent": str,
            "task": str,
            "status": str,  # completed|partial|failed|max_iterations
            "result": str,
            "iterations": int,
            "model_used": str,
            "log": list
        }
        """
        # Build fallback chain
        chain = self.llm.get_fallback_chain(task=task_type or "agentic", needs_tools=True)
        model_info = chain[0] if chain else {"id": "openrouter/free", "name": "Free Router"}
        
        system = self._build_system_prompt()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"## Task\n{task}\n\nBegin working on this task. Use tools as needed. You MUST call report_result when done — this is mandatory."}
        ]
        
        self.log = []
        result = {"agent": self.agent_name, "task": task, "model_used": model_info["name"]}
        
        for iteration in range(self.max_iterations):
            # Call LLM with fallback
            response = None
            for candidate in chain:
                response = self.llm._raw(
                    candidate["id"], messages,
                    temperature=0.3, max_tokens=4096,
                    tools=AGENT_TOOLS
                )
                if "error" not in response:
                    model_info = candidate
                    result["model_used"] = candidate["name"]
                    break
            if response is None or "error" in response:
                response = response or {"error": "No models available"}
            
            if "error" in response:
                result["status"] = "failed"
                result["result"] = f"LLM error: {response['error']}"
                result["iterations"] = iteration + 1
                result["log"] = self.log
                return result
            
            choice = response.get("choices", [{}])[0]
            msg = choice.get("message", {})
            
            # Add assistant message to conversation
            messages.append(msg)
            
            # Check for tool calls
            tool_calls = msg.get("tool_calls", [])
            
            if not tool_calls:
                # No tool calls — agent is done or just responding
                content = msg.get("content", "")
                result["status"] = "completed"
                result["result"] = content
                result["iterations"] = iteration + 1
                result["log"] = self.log
                return result
            
            # Execute each tool call
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                try:
                    args = json.loads(func.get("arguments", "{}"))
                except:
                    args = {}
                
                self.log.append({"iteration": iteration + 1, "tool": name, "args": args})
                
                # Execute
                tool_result = self._execute_tool(name, args)
                
                # Check if this is report_result
                if name == "report_result":
                    try:
                        report = json.loads(tool_result)
                        result["status"] = report.get("status", "completed")
                        result["result"] = report.get("summary", "")
                        result["details"] = report.get("details", "")
                        result["artifacts"] = report.get("artifacts", [])
                    except:
                        result["status"] = "completed"
                        result["result"] = tool_result
                    result["iterations"] = iteration + 1
                    result["log"] = self.log
                    return result
                
                # Add tool result to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{iteration}_{name}"),
                    "content": tool_result
                })
        
        # Max iterations reached
        result["status"] = "max_iterations"
        result["result"] = "Task incomplete — reached maximum iteration limit"
        result["iterations"] = self.max_iterations
        result["log"] = self.log
        return result


# ── Task Queue (SQLite) ──────────────────────────────────────────────────

import sqlite3

QUEUE_DB = "/home/executive-workspace/engine/task_queue.db"

def init_queue():
    """Initialize the task queue database."""
    db = sqlite3.connect(QUEUE_DB)
    db.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        created TEXT DEFAULT CURRENT_TIMESTAMP,
        assigned_to TEXT,
        assigned_by TEXT DEFAULT 'jarvis',
        task_type TEXT DEFAULT 'general',
        priority TEXT DEFAULT 'MEDIUM',
        status TEXT DEFAULT 'pending',
        title TEXT,
        description TEXT,
        model TEXT,
        result TEXT,
        started TEXT,
        completed TEXT
    )""")
    db.commit()
    db.close()

def enqueue_task(title: str, description: str, assigned_to: str,
                 task_type: str = "general", priority: str = "MEDIUM",
                 assigned_by: str = "jarvis", model: str = None) -> str:
    """Add a task to the queue. Returns task ID."""
    import uuid
    task_id = str(uuid.uuid4())[:8]
    db = sqlite3.connect(QUEUE_DB)
    db.execute(
        "INSERT INTO tasks (id, assigned_to, assigned_by, task_type, priority, title, description, model) VALUES (?,?,?,?,?,?,?,?)",
        (task_id, assigned_to, assigned_by, task_type, priority, title, description, model)
    )
    db.commit()
    db.close()
    return task_id

def process_next_task(agent_name: str) -> Optional[dict]:
    """Pick up and execute the next pending task for an agent."""
    db = sqlite3.connect(QUEUE_DB)
    db.row_factory = sqlite3.Row
    
    # Get next pending task
    row = db.execute(
        "SELECT * FROM tasks WHERE assigned_to=? AND status='pending' ORDER BY CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, created ASC LIMIT 1",
        (agent_name,)
    ).fetchone()
    
    if not row:
        db.close()
        return None
    
    task_id = row["id"]
    
    # Mark as active
    db.execute("UPDATE tasks SET status='active', started=CURRENT_TIMESTAMP WHERE id=?", (task_id,))
    db.commit()
    
    # Execute
    executor = AgentExecutor(agent_name)
    result = executor.run(
        task=f"{row['title']}\n\n{row['description']}",
        task_type=row["task_type"],
        model=row["model"]
    )
    
    # Update with result
    db.execute(
        "UPDATE tasks SET status=?, result=?, completed=CURRENT_TIMESTAMP WHERE id=?",
        (result["status"], json.dumps(result), task_id)
    )
    db.commit()
    db.close()
    
    return result

def list_tasks(status: str = None, agent: str = None) -> list:
    """List tasks, optionally filtered."""
    db = sqlite3.connect(QUEUE_DB)
    db.row_factory = sqlite3.Row
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    if agent:
        query += " AND assigned_to=?"
        params.append(agent)
    query += " ORDER BY created DESC LIMIT 50"
    rows = db.execute(query, params).fetchall()
    db.close()
    return [dict(r) for r in rows]


# ── CLI ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_queue()
    
    if len(sys.argv) < 2:
        print("""
AgentOS Executor — Give agents brains.

Usage:
  python3 agent_executor.py run <agent> <task> [--type TYPE] [--model MODEL]
  python3 agent_executor.py queue <agent> <title> <description> [--type TYPE] [--priority PRI]
  python3 agent_executor.py process <agent>
  python3 agent_executor.py list [--status STATUS] [--agent AGENT]
  python3 agent_executor.py models
  
Examples:
  python3 agent_executor.py run tesla "Check the git status of the shared repo"
  python3 agent_executor.py queue warren "Q4 Report" "Analyze Q4 financials" --type financial
  python3 agent_executor.py process warren
  python3 agent_executor.py list --status pending
""")
        sys.exit(0)
    
    cmd = sys.argv[1]
    
    if cmd == "models":
        llm = LLMClient()
        print("=== Available Models ===")
        for m in llm.list_models():
            cost = "FREE" if m["cost"] == 0 else f"${m['cost']}/1K"
            print(f"  {m['name']:20s} {cost:>8s}  {m['display']:30s}  best_for: {', '.join(m['best_for'])}")
    
    elif cmd == "run" and len(sys.argv) >= 4:
        agent = sys.argv[2]
        task = sys.argv[3]
        task_type = None
        model = None
        for i, arg in enumerate(sys.argv[4:]):
            if arg == "--type" and i + 5 < len(sys.argv):
                task_type = sys.argv[i + 5]
            if arg == "--model" and i + 5 < len(sys.argv):
                model = sys.argv[i + 5]
        
        print(f"Executing as {agent}...")
        executor = AgentExecutor(agent)
        result = executor.run(task, task_type=task_type, model=model)
        print(f"\nStatus: {result['status']}")
        print(f"Model: {result['model_used']}")
        print(f"Iterations: {result['iterations']}")
        print(f"Result:\n{result.get('result', '')}")
        if result.get("log"):
            print(f"\nTool calls: {len(result['log'])}")
            for entry in result["log"]:
                print(f"  [{entry['iteration']}] {entry['tool']}({json.dumps(entry['args'])[:80]})")
    
    elif cmd == "queue" and len(sys.argv) >= 5:
        agent = sys.argv[2]
        title = sys.argv[3]
        desc = sys.argv[4]
        task_id = enqueue_task(title, desc, agent)
        print(f"Task {task_id} queued for {agent}: {title}")
    
    elif cmd == "process" and len(sys.argv) >= 3:
        agent = sys.argv[2]
        print(f"Processing next task for {agent}...")
        result = process_next_task(agent)
        if result:
            print(f"Completed: {result['status']}")
            print(f"Result: {result.get('result', '')}")
        else:
            print("No pending tasks.")
    
    elif cmd == "list":
        status = None
        agent = None
        for i, arg in enumerate(sys.argv[2:]):
            if arg == "--status" and i + 3 < len(sys.argv):
                status = sys.argv[i + 3]
            if arg == "--agent" and i + 3 < len(sys.argv):
                agent = sys.argv[i + 3]
        tasks = list_tasks(status=status, agent=agent)
        if tasks:
            for t in tasks:
                print(f"  [{t['id']}] {t['status']:10s} {t['assigned_to']:20s} {t['priority']:8s} {t['title']}")
        else:
            print("No tasks found.")
