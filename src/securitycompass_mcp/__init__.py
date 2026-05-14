"""ZeroPath Security Compass MCP server.

Customer-installed MCP server that exposes the eight ZeroPath ↔ Security
Compass (SD Elements) integration tools to AI agents over stdio. The server
is a thin proxy: each tool call forwards to the corresponding v1 tRPC
procedure on the ZeroPath frontend, authenticated with the customer's API
token (read from environment variables, never seen by the agent).
"""

__version__ = "0.1.0"
