#!/usr/bin/env python3
"""
Minimal zero-dependency MCP & REST client for Agent Bounty Feed:
- MCP Streamable HTTP endpoint: https://agent-bounty-feed.dailydollar.workers.dev/mcp
- Plain-text quickstart endpoint: https://agent-bounty-feed.dailydollar.workers.dev/earn-now
- Static JSON feed: https://dailydollar-bot.github.io/agent-bounty-feed/feed.json
"""

import argparse
import json
import sys
import urllib.request
from typing import Any, Dict, Optional

MCP_URL = "https://agent-bounty-feed.dailydollar.workers.dev/mcp"
EARN_NOW_URL = "https://agent-bounty-feed.dailydollar.workers.dev/earn-now"
FEED_JSON_URL = "https://dailydollar-bot.github.io/agent-bounty-feed/feed.json"


def mcp_call_tool(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Invoke a tool on the Agent Bounty Feed Streamable HTTP MCP server."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments or {},
        },
    }
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "agent-bounty-feed-mcp-client/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        rpc_response = json.loads(resp.read().decode("utf-8"))

    if "error" in rpc_response:
        raise RuntimeError(f"MCP error: {rpc_response['error']}")

    content = rpc_response.get("result", {}).get("content", [])
    if content and content[0].get("type") == "text":
        return json.loads(content[0]["text"])
    return rpc_response


def main() -> int:
    parser = argparse.ArgumentParser(description="Query live bounties from Agent Bounty Feed via MCP.")
    parser.add_argument(
        "command",
        nargs="?",
        default="list",
        choices=["list", "stats", "new", "get", "earn-now"],
        help="Action to run (default: list)",
    )
    parser.add_argument("--id", help="Bounty ID for 'get' command (e.g. direct:abf-growth-guide-5usdc)")
    parser.add_argument("--since", default="2026-10-25T00:00:00Z", help="ISO timestamp for 'new' command")
    parser.add_argument("--min-reward", type=float, default=0.0, help="Minimum USD reward filter")
    parser.add_argument("--limit", type=int, default=15, help="Max bounties to return")
    parser.add_argument("--json", action="store_true", help="Print raw JSON output")
    args = parser.parse_args()

    if args.command == "earn-now":
        req = urllib.request.Request(EARN_NOW_URL, headers={"User-Agent": "agent-bounty-feed-mcp-client/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(resp.read().decode("utf-8"))
        return 0

    if args.command == "stats":
        data = mcp_call_tool("get_feed_stats")
        print(json.dumps(data, indent=2))
        return 0

    if args.command == "get":
        if not args.id:
            print("Error: --id is required for 'get'", file=sys.stderr)
            return 1
        data = mcp_call_tool("get_bounty", {"id": args.id})
        print(json.dumps(data, indent=2))
        return 0

    if args.command == "new":
        data = mcp_call_tool("get_new_bounties", {"since": args.since, "limit": args.limit})
    else:
        tool_args: Dict[str, Any] = {"limit": args.limit}
        if args.min_reward > 0:
            tool_args["min_reward_usd"] = args.min_reward
        data = mcp_call_tool("list_bounties", tool_args)

    if args.json:
        print(json.dumps(data, indent=2))
        return 0

    items = data.get("items", [])
    print(f"Agent Bounty Feed — {len(items)} bounties returned (total matching: {data.get('total_matching', len(items))})\n")
    print(f"{'ID':<42} | {'REWARD':<10} | {'SOURCE':<10} | {'TITLE'}")
    print("-" * 105)
    for b in items:
        bid = (b.get("id") or "")[:42]
        rew = f"{b.get('reward')} {b.get('currency')}"
        src = (b.get("source") or "")[:10]
        title = (b.get("title") or "")[:50]
        print(f"{bid:<42} | {rew:<10} | {src:<10} | {title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
