# ZeroPath Security Compass MCP Server

An MCP server that exposes ZeroPath's [Security Compass (SD Elements)](https://www.securitycompass.com/sdelements/)
integration tools to AI assistants (Claude Desktop, Cursor, Windsurf, and any
other MCP-compatible client).

This server is a thin proxy: each tool call forwards to the corresponding v1
tRPC procedure on the ZeroPath frontend, authenticated with your ZeroPath API
token. The server runs on your machine and connects to ZeroPath via HTTPS.

If you're looking for the general-purpose ZeroPath MCP (issues, patches,
scans), see [`zeropath-mcp-server`](https://github.com/ZeroPathAI/zeropath-mcp-server).
This package is dedicated to the SC integration only.

## Tools

| Tool | Purpose |
|---|---|
| `securityCompass.getIntegration` | Read the configured SDE integration and all project-to-repo mappings |
| `securityCompass.upsertIntegration` | Create or update the SDE integration (base URL + API token) |
| `securityCompass.testConnection` | Validate SDE credentials against a specific project |
| `securityCompass.addProjectMapping` | Link an SDE project to a ZeroPath repository |
| `securityCompass.removeProjectMapping` | Detach a project-to-repo mapping |
| `securityCompass.syncRules` | Trigger a rule sync for one mapping |
| `securityCompass.getMappingAudit` | Read the per-task coverage breakdown for a mapping |
| `securityCompass.getSyncHistory` | Read recent SC audit-log events |

## Installation

The recommended way is via [uv](https://docs.astral.sh/uv/) — `uvx` will
download the package on first use and cache it for subsequent invocations.

### Claude Desktop / Cursor / Windsurf

Add this to your MCP client's configuration:

```json
{
  "mcpServers": {
    "zeropath-securitycompass": {
      "command": "uvx",
      "args": ["securitycompass-mcp"],
      "env": {
        "ZEROPATH_TOKEN_ID": "<your-api-token-id>",
        "ZEROPATH_TOKEN_SECRET": "<your-api-token-secret>",
        "ZEROPATH_ORG_ID": "<your-organization-id>",
        "ZEROPATH_BASE_URL": "https://securitycompass.branch.zeropath.com/"
      }
    }
  }
}
```

Generate an API token at <https://zeropath.com/app/settings/api-tokens>.

### Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `ZEROPATH_TOKEN_ID` | yes | — | API token id |
| `ZEROPATH_TOKEN_SECRET` | yes | — | API token secret |
| `ZEROPATH_ORG_ID` | yes | — | Default organization id (auto-injected when tools omit it). Required for the Security Compass deployment — see below. |
| `ZEROPATH_BASE_URL` | yes | `https://zeropath.com` | URL of the ZeroPath deployment to connect to. Required for the Security Compass deployment — the built-in default does **not** point at it (see below). |

> **Security Compass deployment.** This server targets the dedicated Security
> Compass deployment of ZeroPath, not `https://zeropath.com`. Because of that,
> `ZEROPATH_BASE_URL` is **always required**: the built-in default is not the
> Security Compass deployment, so leaving it unset connects to the wrong host.
> Set it explicitly to the deployment URL, for example:
>
> ```
> ZEROPATH_BASE_URL=https://securitycompass.branch.zeropath.com/
> ```
>
> `ZEROPATH_ORG_ID` is likewise **required** for this deployment, so that every
> tool call resolves to the correct organization. If `ZEROPATH_ORG_ID` is not
> set, every tool call must include `organizationId` in its arguments.

## Development

```bash
uv venv
uv pip install -e ".[dev]"
python -m securitycompass_mcp
```

Run tests:

```bash
uv run pytest
```

## License

MIT
