#!/usr/bin/env python3
"""
LLM Client — OpenRouter with smart fallback chain.

All models route through OpenRouter (including opencode/ prefix models).

Fallback order:
  1. opencode/kimi-k2.5-free        — best free model
  2. opencode/minimax-m2.5-free      — backup free
  3. arcee-ai/trinity-large-preview:free — best free on OpenRouter native
  4. Other free OpenRouter models as available

Paid models: ONLY at Nikolas's explicit request.

Usage:
    from llm_client import LLMClient
    llm = LLMClient()
    response = llm.chat("What is 2+2?")
    response = llm.chat("Analyze this...", task="analysis")
"""

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

KEYS_PATH = "/home/executive-workspace/apis/keys.env"
BASE_URL = "https://openrouter.ai/api/v1"

# ── Model Registry ───────────────────────────────────────────────────────

MODELS = {
    # === FREE TIER — default fallback chain order ===
    "kimi_k25": {
        "id": "opencode/kimi-k2.5-free",
        "name": "Kimi K2.5 (OpenCode)",
        "cost": 0, "context": 262144,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 1,
        "best_for": ["coding", "reasoning", "analysis", "agentic", "general"]
    },
    "minimax_m25": {
        "id": "opencode/minimax-m2.5-free",
        "name": "MiniMax M2.5 (OpenCode)",
        "cost": 0, "context": 204800,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 2,
        "best_for": ["coding", "office_work", "agents", "general"]
    },
    "trinity": {
        "id": "arcee-ai/trinity-large-preview:free",
        "name": "Trinity Large Preview",
        "cost": 0, "context": 131000,
        "supports_tools": True, "supports_reasoning": False,
        "tier": "free", "priority": 3,
        "best_for": ["creative_writing", "agentic", "general", "reasoning"]
    },
    "aurora": {
        "id": "openrouter/aurora-alpha",
        "name": "Aurora Alpha",
        "cost": 0, "context": 128000,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 4,
        "best_for": ["coding", "agentic", "reasoning"]
    },
    "step_flash": {
        "id": "stepfun/step-3.5-flash:free",
        "name": "Step 3.5 Flash",
        "cost": 0, "context": 256000,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 5,
        "best_for": ["reasoning", "long_context", "analysis"]
    },
    "qwen_coder_free": {
        "id": "qwen/qwen3-coder:free",
        "name": "Qwen3 Coder (Free)",
        "cost": 0, "context": 262144,
        "supports_tools": True, "supports_reasoning": False,
        "tier": "free", "priority": 6,
        "best_for": ["coding", "tool_use"]
    },
    "solar_pro": {
        "id": "upstage/solar-pro-3:free",
        "name": "Solar Pro 3",
        "cost": 0, "context": 128000,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 7,
        "best_for": ["general", "multilingual"]
    },
    "glm_air": {
        "id": "z-ai/glm-4.5-air:free",
        "name": "GLM 4.5 Air",
        "cost": 0, "context": 128000,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 8,
        "best_for": ["general", "reasoning"]
    },
    "llama_70b": {
        "id": "meta-llama/llama-3.3-70b-instruct:free",
        "name": "Llama 3.3 70B",
        "cost": 0, "context": 131072,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 9,
        "best_for": ["general", "reasoning", "coding"]
    },
    "gpt_oss": {
        "id": "openai/gpt-oss-120b:free",
        "name": "GPT-OSS 120B",
        "cost": 0, "context": 128000,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 10,
        "best_for": ["general", "coding"]
    },
    "free_router": {
        "id": "openrouter/free",
        "name": "Free Router (random)",
        "cost": 0, "context": 200000,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "free", "priority": 99,
        "best_for": ["general", "testing"]
    },

    # === PAID TIER — Nikolas authorization ONLY ===
    "kimi_paid": {
        "id": "moonshotai/kimi-k2.5",
        "name": "Kimi K2.5 (Paid)",
        "cost": 0.0005, "context": 262144,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "paid", "priority": 100,
        "best_for": ["coding", "reasoning"]
    },
    "minimax_paid": {
        "id": "minimax/minimax-m2.5",
        "name": "MiniMax M2.5 (Paid)",
        "cost": 0.0003, "context": 204800,
        "supports_tools": True, "supports_reasoning": True,
        "tier": "paid", "priority": 101,
        "best_for": ["coding", "agents"]
    },
    "qwen_coder_paid": {
        "id": "qwen/qwen3-coder-next",
        "name": "Qwen3 Coder Next (Paid)",
        "cost": 0.0001, "context": 262144,
        "supports_tools": True, "supports_reasoning": False,
        "tier": "paid", "priority": 102,
        "best_for": ["coding", "tool_use"]
    },
}

# ── Default Fallback Chain ───────────────────────────────────────────────
DEFAULT_FALLBACK = [
    "kimi_k25", "minimax_m25", "trinity",
    "aurora", "step_flash", "qwen_coder_free",
    "solar_pro", "glm_air", "llama_70b", "gpt_oss",
    "free_router"
]

# ── Task Mappings (all start with kimi→minimax→...) ─────────────────────
TASK_MODEL_MAP = {
    "coding":         ["kimi_k25", "minimax_m25", "aurora", "qwen_coder_free", "trinity", "step_flash"],
    "code_review":    ["kimi_k25", "minimax_m25", "aurora", "trinity", "step_flash"],
    "debugging":      ["kimi_k25", "minimax_m25", "aurora", "qwen_coder_free", "trinity"],
    "analysis":       ["kimi_k25", "minimax_m25", "step_flash", "trinity", "aurora"],
    "reasoning":      ["kimi_k25", "minimax_m25", "step_flash", "aurora", "trinity"],
    "research":       ["kimi_k25", "minimax_m25", "step_flash", "trinity", "aurora"],
    "financial":      ["kimi_k25", "minimax_m25", "step_flash", "trinity", "aurora"],
    "legal_analysis": ["kimi_k25", "minimax_m25", "step_flash", "trinity", "aurora"],
    "business":       ["kimi_k25", "minimax_m25", "trinity", "step_flash", "aurora"],
    "writing":        ["kimi_k25", "minimax_m25", "trinity", "aurora", "solar_pro"],
    "marketing":      ["kimi_k25", "minimax_m25", "trinity", "aurora", "solar_pro"],
    "creative":       ["kimi_k25", "minimax_m25", "trinity", "aurora", "solar_pro"],
    "general":        ["kimi_k25", "minimax_m25", "trinity", "aurora", "solar_pro", "free_router"],
    "simple":         ["kimi_k25", "minimax_m25", "trinity", "solar_pro", "free_router"],
    "extraction":     ["kimi_k25", "minimax_m25", "aurora", "step_flash", "trinity"],
    "summarization":  ["kimi_k25", "minimax_m25", "step_flash", "trinity", "aurora"],
    "agentic":        ["kimi_k25", "minimax_m25", "trinity", "aurora", "step_flash"],
    "tool_use":       ["kimi_k25", "minimax_m25", "aurora", "qwen_coder_free", "trinity"],
    "long_context":   ["kimi_k25", "minimax_m25", "step_flash", "qwen_coder_free", "trinity"],
}


class LLMClient:
    """OpenRouter LLM client with automatic fallback chain."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_key()
        self.paid_authorized = False  # Only Nikolas can flip this

    def _load_key(self) -> str:
        try:
            with open(KEYS_PATH) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("OPENROUTER_API_KEY=") and not line.startswith("#"):
                        return line.split("=", 1)[1].strip()
        except:
            pass
        return os.environ.get("OPENROUTER_API_KEY", "")

    def authorize_paid(self, authorized: bool = True):
        """Enable paid models. Only Nikolas can authorize this."""
        self.paid_authorized = authorized

    def get_fallback_chain(self, task: Optional[str] = None,
                           needs_tools: bool = False,
                           needs_reasoning: bool = False,
                           min_context: int = 0) -> List[dict]:
        chain_names = TASK_MODEL_MAP.get(task, DEFAULT_FALLBACK)
        chain = []
        for name in chain_names:
            m = MODELS.get(name)
            if not m:
                continue
            if m["tier"] == "paid" and not self.paid_authorized:
                continue
            if needs_tools and not m["supports_tools"]:
                continue
            if needs_reasoning and not m["supports_reasoning"]:
                continue
            if m["context"] < min_context:
                continue
            chain.append(m)
        if not any(m["id"] == "openrouter/free" for m in chain):
            chain.append(MODELS["free_router"])
        return chain

    def chat(self, message: str,
             system: Optional[str] = None,
             task: Optional[str] = None,
             model: Optional[str] = None,
             paid: bool = False,
             temperature: float = 0.7,
             max_tokens: int = 4096) -> str:
        if paid:
            self.paid_authorized = True

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})

        if model:
            if model in MODELS:
                info = MODELS[model]
                if info["tier"] == "paid" and not self.paid_authorized:
                    return "ERROR: Paid model not authorized. Only Nikolas can approve paid model usage."
                result = self._call(info["id"], messages, temperature, max_tokens)
                if not result.startswith("ERROR:"):
                    return result
            # Try as raw model ID
            result = self._call(model, messages, temperature, max_tokens)
            if not result.startswith("ERROR:"):
                return result
            return result

        # Fallback chain
        chain = self.get_fallback_chain(task=task)
        last_err = "No models available"
        for m in chain:
            result = self._call(m["id"], messages, temperature, max_tokens)
            if not result.startswith("ERROR:"):
                return result
            last_err = result
        return last_err

    def chat_with_tools(self, message: str, tools: List[Dict],
                        system: Optional[str] = None,
                        task: Optional[str] = None,
                        temperature: float = 0.3,
                        max_tokens: int = 4096) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})
        chain = self.get_fallback_chain(task=task or "tool_use", needs_tools=True)
        for m in chain:
            result = self._raw(m["id"], messages, temperature, max_tokens, tools=tools)
            if "error" not in result:
                return result
        return {"error": "All models in fallback chain failed"}

    def multi_turn(self, messages: List[Dict],
                   task: Optional[str] = None,
                   temperature: float = 0.7,
                   max_tokens: int = 4096) -> str:
        chain = self.get_fallback_chain(task=task)
        for m in chain:
            result = self._call(m["id"], messages, temperature, max_tokens)
            if not result.startswith("ERROR:"):
                return result
        return "ERROR: All models failed"

    def _call(self, model_id: str, messages: list,
              temperature: float, max_tokens: int) -> str:
        result = self._raw(model_id, messages, temperature, max_tokens)
        if "error" in result:
            return f"ERROR: {result['error']}"
        choices = result.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if content:
                return content
        return "ERROR: Empty response"

    def _raw(self, model_id: str, messages: list,
             temperature: float, max_tokens: int,
             tools: Optional[list] = None) -> dict:
        if not self.api_key:
            return {"error": "No OPENROUTER_API_KEY configured"}

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        data = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://agent-os.local",
            "X-Title": "AgentOS Multi-Agent System"
        }

        req = urllib.request.Request(
            f"{BASE_URL}/chat/completions",
            data=data, headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            return {"error": f"HTTP {e.code}: {body[:300]}"}
        except Exception as e:
            return {"error": str(e)}

    def list_models(self, tier: Optional[str] = None) -> list:
        result = []
        for name, info in sorted(MODELS.items(), key=lambda x: x[1]["priority"]):
            if tier and info["tier"] != tier:
                continue
            result.append({
                "name": name, "id": info["id"], "display": info["name"],
                "tier": info["tier"], "cost": info["cost"],
                "context": info["context"], "priority": info["priority"],
                "tools": info["supports_tools"],
                "reasoning": info["supports_reasoning"],
                "best_for": info["best_for"]
            })
        return result


def quick_chat(message: str, task: str = "general", system: str = None) -> str:
    return LLMClient().chat(message, system=system, task=task)


if __name__ == "__main__":
    llm = LLMClient()

    print("=== Fallback Chain (default) ===")
    for i, m in enumerate(llm.get_fallback_chain(), 1):
        cost = "FREE" if m["cost"] == 0 else f"${m['cost']}/1K"
        print(f"  {i}. {m['name']:30s} {m['id']:45s} {cost}")

    print("\n=== All Models ===")
    for m in llm.list_models():
        cost = "FREE" if m["cost"] == 0 else f"${m['cost']}/1K"
        tier = "💰" if m["tier"] == "paid" else "🆓"
        tools = "🔧" if m["tools"] else "  "
        reason = "🧠" if m["reasoning"] else "  "
        print(f"  {tier} P{m['priority']:<3d} {m['name']:20s} {cost:>8s} {tools}{reason} ctx:{m['context']:>7d}  {m['display']}")

    if llm.api_key:
        print("\n=== Live Test ===")
        r = llm.chat("What is 2+2? Reply with ONLY the number.", task="simple")
        print(f"  Response: {r}")
    else:
        print("\n⚠️  No OPENROUTER_API_KEY. Add to /home/executive-workspace/apis/keys.env")
