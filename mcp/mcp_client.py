#!/usr/bin/env python3
"""
Multi-Agent MCP Client Library (SDK-based)
============================================
Uses the official MCP Python SDK for reliable server communication.

Usage:
    from mcp_client import MCPClient
    import asyncio

    async def main():
        mcp = MCPClient()
        
        # Fetch a URL
        result = await mcp.call("fetch", "fetch", url="https://example.com")
        print(result)
        
        # Git status
        result = await mcp.call("git", "git_status", repo_path="/home/ubuntu/shared-repo")
        print(result)
        
        # List tools on a server
        tools = await mcp.list_tools("git")
        print(tools)
        
        # Browse catalog
        print(mcp.catalog())

    asyncio.run(main())

Synchronous wrapper (simpler):
    from mcp_client import mcp_call, mcp_list_tools, mcp_catalog
    
    result = mcp_call("fetch", "fetch", url="https://example.com")
    tools = mcp_list_tools("git")
    catalog = mcp_catalog()
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional

REGISTRY_PATH = "/home/executive-workspace/mcp/registry.json"

# Server definitions: name -> (command, args)
SERVER_DEFS = {
    "fetch":      ("python3", ["-m", "mcp_server_fetch"]),
    "git":        ("python3", ["-m", "mcp_server_git"]),
    "filesystem": ("npx", ["-y", "mcp-server-filesystem",
                           "/home/executive-workspace", "/home/ubuntu/shared-repo", "/tmp"]),
}


class MCPClient:
    """Async MCP client using the official SDK."""

    def __init__(self):
        with open(REGISTRY_PATH) as f:
            self.registry = json.load(f)

    async def call(self, server: str, tool: str, **params) -> str:
        """Call an MCP tool. Returns the text result."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        defn = SERVER_DEFS.get(server)
        if not defn:
            return f"ERROR: Unknown server '{server}'. Available: {list(SERVER_DEFS)}"

        cmd, args = defn
        sp = StdioServerParameters(command=cmd, args=args)
        try:
            async with stdio_client(sp) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, params)
                    texts = []
                    for c in result.content:
                        if hasattr(c, "text"):
                            texts.append(c.text)
                    return "\n".join(texts) if texts else str(result)
        except Exception as e:
            return f"ERROR: {e}"

    async def list_tools(self, server: str) -> List[str]:
        """List tools on a server."""
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        defn = SERVER_DEFS.get(server)
        if not defn:
            return []
        cmd, args = defn
        sp = StdioServerParameters(command=cmd, args=args)
        try:
            async with stdio_client(sp) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [t.name for t in result.tools]
        except:
            return []

    def catalog(self) -> dict:
        """Full catalog: installed + available."""
        out = {"installed": {}, "available": {}}
        for name, info in self.registry.get("installed", {}).items():
            out["installed"][name] = {
                "description": info.get("description", ""),
                "tools": info.get("tools", []),
                "team_relevance": info.get("team_relevance", [])
            }
        for cat, servers in self.registry.get("available_free", {}).items():
            for sid, info in servers.items():
                out["available"][sid] = {
                    "category": cat,
                    "description": info.get("description", ""),
                    "install": info.get("install", ""),
                    "auth": info.get("auth", "none"),
                    "team_relevance": info.get("team_relevance", [])
                }
        return out


# ── Synchronous wrappers (for simple scripts) ──────────────

def mcp_call(server: str, tool: str, **params) -> str:
    mcp = MCPClient()
    return asyncio.run(mcp.call(server, tool, **params))

def mcp_list_tools(server: str) -> list:
    mcp = MCPClient()
    return asyncio.run(mcp.list_tools(server))

def mcp_catalog() -> dict:
    return MCPClient().catalog()


if __name__ == "__main__":
    async def main():
        mcp = MCPClient()

        print("=== Installed MCP Servers ===")
        for name in SERVER_DEFS:
            tools = await mcp.list_tools(name)
            status = "ONLINE" if tools else "OFFLINE"
            print(f"  {name}: {status} ({len(tools)} tools)")
            if tools:
                print(f"    tools: {tools}")

        cat = mcp.catalog()
        print(f"\n=== Catalog: {len(cat['installed'])} installed, {len(cat['available'])} available ===")

        print("\n=== Live Test: fetch httpbin ===")
        r = await mcp.call("fetch", "fetch", url="https://httpbin.org/get", max_length=300)
        print(f"  {r[:150]}...")

        print("\n=== Live Test: git status ===")
        r = await mcp.call("git", "git_status", repo_path="/home/ubuntu/shared-repo")
        print(f"  {r[:150]}...")

    asyncio.run(main())
