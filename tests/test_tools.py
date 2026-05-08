"""Tests for tool dispatch.

Stubs the tRPC client so tests run without network. Asserts that the
documented dispatch table — query vs mutation, procedure path,
organizationId injection from config — actually fires.
"""

from __future__ import annotations

from typing import Any

import pytest

from zeropath_securitycompass_mcp.tools import TOOL_DEFINITIONS, call_tool
from zeropath_securitycompass_mcp.trpc_client import Config, TrpcClient


class _StubClient(TrpcClient):
    def __init__(self, organization_id: str | None = None) -> None:
        self._organization_id = organization_id
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    @property
    def organization_id(self) -> str | None:
        return self._organization_id

    def query(self, procedure: str, payload: dict[str, Any]) -> Any:
        self.calls.append(("query", procedure, dict(payload)))
        return {"ok": True}

    def mutate(self, procedure: str, payload: dict[str, Any]) -> Any:
        self.calls.append(("mutation", procedure, dict(payload)))
        return {"ok": True}


def test_eight_tools_advertised():
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert names == {
        "securityCompass.getIntegration",
        "securityCompass.upsertIntegration",
        "securityCompass.testConnection",
        "securityCompass.addProjectMapping",
        "securityCompass.removeProjectMapping",
        "securityCompass.syncRules",
        "securityCompass.getMappingAudit",
        "securityCompass.getSyncHistory",
    }


def test_query_tool_dispatches_to_get():
    client = _StubClient(organization_id="org_123")
    call_tool("securityCompass.getIntegration", {}, client=client)
    assert client.calls == [
        ("query", "v1.securityCompass.getIntegration", {"organizationId": "org_123"}),
    ]


def test_mutation_tool_dispatches_to_post():
    client = _StubClient(organization_id="org_123")
    call_tool(
        "securityCompass.syncRules",
        {"mappingId": "map_42"},
        client=client,
    )
    assert client.calls == [
        ("mutation", "v1.securityCompass.syncRules", {"mappingId": "map_42", "organizationId": "org_123"}),
    ]


def test_explicit_org_id_overrides_config_default():
    client = _StubClient(organization_id="org_default")
    call_tool(
        "securityCompass.getIntegration",
        {"organizationId": "org_explicit"},
        client=client,
    )
    assert client.calls[0][2]["organizationId"] == "org_explicit"


def test_missing_org_id_raises_when_unconfigured():
    client = _StubClient(organization_id=None)
    with pytest.raises(ValueError, match="organizationId is required"):
        call_tool("securityCompass.getIntegration", {}, client=client)


def test_unknown_tool_raises():
    client = _StubClient(organization_id="org_123")
    with pytest.raises(ValueError, match="Unknown tool"):
        call_tool("securityCompass.bogus", {}, client=client)


def test_load_config_requires_credentials(monkeypatch):
    from zeropath_securitycompass_mcp.trpc_client import ConfigError, load_config

    monkeypatch.delenv("ZEROPATH_TOKEN_ID", raising=False)
    monkeypatch.delenv("ZEROPATH_TOKEN_SECRET", raising=False)
    with pytest.raises(ConfigError, match="ZEROPATH_TOKEN_ID"):
        load_config()


def test_load_config_reads_env(monkeypatch):
    from zeropath_securitycompass_mcp.trpc_client import load_config

    monkeypatch.setenv("ZEROPATH_TOKEN_ID", "id_xyz")
    monkeypatch.setenv("ZEROPATH_TOKEN_SECRET", "secret_xyz")
    monkeypatch.setenv("ZEROPATH_ORG_ID", "org_xyz")
    monkeypatch.setenv("ZEROPATH_BASE_URL", "https://staging.branch.zeropath.com/")

    cfg: Config = load_config()
    assert cfg.token_id == "id_xyz"
    assert cfg.token_secret == "secret_xyz"
    assert cfg.organization_id == "org_xyz"
    assert cfg.base_url == "https://staging.branch.zeropath.com"  # trailing slash stripped
