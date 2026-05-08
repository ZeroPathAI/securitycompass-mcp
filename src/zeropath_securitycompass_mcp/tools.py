"""Tool definitions for the Security Compass MCP server.

Each tool is a thin proxy to a v1 tRPC procedure. Names mirror the tRPC
paths (``securityCompass.<method>``) so behaviour is unambiguous when
cross-referencing the dashboard or platform docs.

The schemas describe the same shape the underlying Zod validators enforce
on the server. The server is the source of truth for validation; the
schemas here are descriptive enough for the agent's planner to call them
correctly, no looser.
"""

from __future__ import annotations

from typing import Any

from .trpc_client import TrpcClient

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "securityCompass.getIntegration",
        "description": (
            "Read the Security Compass (SD Elements) integration configured for the given "
            "ZeroPath organization, including all project-to-repository mappings and their "
            "latest sync status. Returns null if no integration is configured."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organizationId": {
                    "type": "string",
                    "description": "ZeroPath organization id. Optional if ZEROPATH_ORG_ID is configured.",
                },
            },
        },
    },
    {
        "name": "securityCompass.upsertIntegration",
        "description": (
            "Create or update the Security Compass integration for an organization. Stores "
            "the SD Elements base URL and API token. Idempotent — safe to call repeatedly "
            "with the same inputs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organizationId": {"type": "string"},
                "sdeBaseUrl": {
                    "type": "string",
                    "format": "uri",
                    "description": "Base URL of the customer's SD Elements tenant, e.g. https://sde-ent-acme.sdelab.app/",
                },
                "sdeApiToken": {
                    "type": "string",
                    "description": "SD Elements API token. Optional on update — preserves the existing token when omitted.",
                },
                "enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "When false, all syncs and pushes are gated off.",
                },
            },
            "required": ["sdeBaseUrl"],
        },
    },
    {
        "name": "securityCompass.testConnection",
        "description": (
            "Validate SD Elements credentials against a specific project before persisting "
            "them. Returns the countermeasure count for the project on success."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organizationId": {"type": "string"},
                "sdeBaseUrl": {"type": "string", "format": "uri"},
                "sdeApiToken": {
                    "type": "string",
                    "description": "Optional. Reuses the saved token when omitted.",
                },
                "sdeProjectId": {
                    "type": "string",
                    "description": "SD Elements project id to probe.",
                },
            },
            "required": ["sdeBaseUrl", "sdeProjectId"],
        },
    },
    {
        "name": "securityCompass.addProjectMapping",
        "description": (
            "Link an SD Elements project to a ZeroPath repository. Adds one mapping per "
            "(integration, project, repo) triple. Multiple repos can map to the same SDE "
            "project (the documented multi-repo case)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organizationId": {"type": "string"},
                "sdeProjectId": {"type": "string"},
                "repositoryId": {
                    "type": "string",
                    "description": "ZeroPath repository id to attach.",
                },
            },
            "required": ["sdeProjectId", "repositoryId"],
        },
    },
    {
        "name": "securityCompass.removeProjectMapping",
        "description": (
            "Detach a project-to-repository mapping. Auto-generated NL rules created by the "
            "mapping persist; remove them separately if desired."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organizationId": {"type": "string"},
                "mappingId": {"type": "string"},
            },
            "required": ["mappingId"],
        },
    },
    {
        "name": "securityCompass.syncRules",
        "description": (
            "Trigger a rule sync for one mapping. Pulls SD Elements countermeasures, "
            "classifies them as SAST-detectable / NL-rule / unsupported, and creates or "
            "updates ZeroPath natural-language rules accordingly. Returns sync stats. "
            "Errors with HTTP 409 if a sync is already running for the mapping."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organizationId": {"type": "string"},
                "mappingId": {"type": "string"},
            },
            "required": ["mappingId"],
        },
    },
    {
        "name": "securityCompass.getMappingAudit",
        "description": (
            "Read the per-task coverage breakdown for a mapping (which countermeasures are "
            "covered by AI SAST vs NL rule vs unsupported). Available after the first "
            "successful syncRules call."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organizationId": {"type": "string"},
                "mappingId": {"type": "string"},
            },
            "required": ["mappingId"],
        },
    },
    {
        "name": "securityCompass.getSyncHistory",
        "description": (
            "Read recent Security Compass audit-log events (sync attempts, push attempts, "
            "mapping add/remove, integration upsert/delete) for an organization."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "organizationId": {"type": "string"},
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                },
            },
        },
    },
]


# Each tool's tuple: (kind, tRPC procedure path).
# `kind` controls whether we issue a tRPC GET (query) or POST (mutation).
_TOOL_DISPATCH: dict[str, tuple[str, str]] = {
    "securityCompass.getIntegration": ("query", "v1.securityCompass.getIntegration"),
    "securityCompass.upsertIntegration": ("mutation", "v1.securityCompass.upsertIntegration"),
    "securityCompass.testConnection": ("mutation", "v1.securityCompass.testConnection"),
    "securityCompass.addProjectMapping": ("mutation", "v1.securityCompass.addProjectMapping"),
    "securityCompass.removeProjectMapping": ("mutation", "v1.securityCompass.removeProjectMapping"),
    "securityCompass.syncRules": ("mutation", "v1.securityCompass.syncRules"),
    "securityCompass.getMappingAudit": ("query", "v1.securityCompass.getMappingAudit"),
    "securityCompass.getSyncHistory": ("query", "v1.securityCompass.getSyncHistory"),
}


def call_tool(name: str, arguments: dict[str, Any], *, client: TrpcClient) -> Any:
    """Dispatch an MCP ``tools/call`` to the corresponding ZeroPath tRPC procedure.

    Injects ``organizationId`` from configuration if the agent didn't supply
    one — every SC procedure requires it server-side, so this is the
    customer-friendly default.
    """
    if name not in _TOOL_DISPATCH:
        raise ValueError(f"Unknown tool: {name}")

    payload = dict(arguments)
    if "organizationId" not in payload or not payload["organizationId"]:
        if client.organization_id:
            payload["organizationId"] = client.organization_id
        else:
            raise ValueError(
                "organizationId is required. Pass it explicitly or set ZEROPATH_ORG_ID."
            )

    kind, procedure = _TOOL_DISPATCH[name]
    if kind == "query":
        return client.query(procedure, payload)
    return client.mutate(procedure, payload)
