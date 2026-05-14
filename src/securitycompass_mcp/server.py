"""MCP server registration.

Hardcoded tool list (the eight SC tools) registered against the low-level
``mcp.server.Server``. ``tools/call`` invocations are dispatched to the
corresponding v1 tRPC procedure on the ZeroPath frontend via :mod:`trpc_client`.

Customer-installed transport is stdio (see :mod:`__main__`); the customer's
MCP client (Claude Desktop, Cursor, etc.) runs this process per-session and
talks to it over stdin/stdout.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import mcp.types as types
from mcp.server.lowlevel import Server

from . import __version__
from .tools import TOOL_DEFINITIONS, call_tool
from .trpc_client import ConfigError, TrpcClient, UpstreamError, load_config

SERVER_NAME = "securitycompass-mcp"


def create_server() -> Server:
    """Build and configure the MCP server.

    Loads configuration from the environment up front and exits with a
    helpful message if credentials are missing — the client has no UI to
    surface a runtime auth failure cleanly, so failing fast at process start
    is the right behaviour.
    """
    try:
        config = load_config()
    except ConfigError as err:
        print(f"[securitycompass-mcp] {err}", file=sys.stderr)
        sys.exit(2)

    client = TrpcClient(config)
    server: Server = Server(SERVER_NAME, version=__version__)

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=tool["inputSchema"],
            )
            for tool in TOOL_DEFINITIONS
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
        try:
            result = call_tool(name, arguments or {}, client=client)
        except (UpstreamError, ValueError) as err:
            # MCP convention: surface tool errors as a text payload that the
            # agent can read alongside other tool results. Raising would
            # collapse the response to a generic JSON-RPC error and lose
            # the upstream code/message detail.
            return [types.TextContent(type="text", text=f"Error: {err}")]

        return [
            types.TextContent(
                type="text",
                text=json.dumps(result, default=str, indent=2),
            )
        ]

    return server
