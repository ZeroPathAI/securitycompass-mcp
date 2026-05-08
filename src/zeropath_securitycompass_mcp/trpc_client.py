"""Sync HTTP client for ZeroPath's v1 tRPC surface.

Customer-installed: credentials are loaded once at startup from environment
variables and held in this module. Each tool call forwards to a v1 tRPC
procedure carrying the API token via the platform's two custom headers.

tRPC HTTP wire format (per `trpc-sveltekit` + tRPC v10):
    queries     → GET  /trpc/<procedure>?input=<urlencoded {"json": <payload>}>
    mutations   → POST /trpc/<procedure>     body: {"json": <payload>}

Successful responses: ``{ "result": { "data": { "json": <T> } } }``
Error responses:      ``{ "error":  { "json": { "code", "message", ... } } }``
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests

API_TOKEN_ID_HEADER = "X-ZeroPath-API-Token-Id"
API_TOKEN_SECRET_HEADER = "X-ZeroPath-API-Token-Secret"
CLIENT_HEADER_VALUE = "zeropath-securitycompass-mcp"
DEFAULT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Config:
    base_url: str
    token_id: str
    token_secret: str
    organization_id: str | None


class ConfigError(RuntimeError):
    """Misconfigured environment — server cannot start."""


class UpstreamError(RuntimeError):
    """Non-2xx response or tRPC-level error from the ZeroPath backend.

    Surfaces the upstream code/message verbatim — this server runs on the
    customer's machine, so leaking diagnostic detail is fine and helpful.
    """


def load_config() -> Config:
    base_url = os.getenv("ZEROPATH_BASE_URL", "https://zeropath.com").rstrip("/")
    token_id = os.getenv("ZEROPATH_TOKEN_ID")
    token_secret = os.getenv("ZEROPATH_TOKEN_SECRET")
    organization_id = os.getenv("ZEROPATH_ORG_ID")

    if not token_id or not token_secret:
        raise ConfigError(
            "ZEROPATH_TOKEN_ID and ZEROPATH_TOKEN_SECRET are both required. "
            "Generate an API token at https://zeropath.com/app/settings/api-tokens "
            "and configure them in your MCP client's `env` block."
        )

    return Config(
        base_url=base_url,
        token_id=token_id,
        token_secret=token_secret,
        organization_id=organization_id or None,
    )


class TrpcClient:
    """Thin sync tRPC client. One instance per server process."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._session = requests.Session()

    @property
    def organization_id(self) -> str | None:
        return self._config.organization_id

    def query(self, procedure: str, payload: Mapping[str, Any]) -> Any:
        encoded = quote(json.dumps({"json": dict(payload)}), safe="")
        url = f"{self._config.base_url}/trpc/{procedure}?input={encoded}"
        response = self._session.get(
            url,
            headers=self._headers(),
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        return self._unwrap(response, procedure)

    def mutate(self, procedure: str, payload: Mapping[str, Any]) -> Any:
        url = f"{self._config.base_url}/trpc/{procedure}"
        response = self._session.post(
            url,
            json={"json": dict(payload)},
            headers=self._headers(),
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        return self._unwrap(response, procedure)

    def _headers(self) -> dict[str, str]:
        return {
            API_TOKEN_ID_HEADER: self._config.token_id,
            API_TOKEN_SECRET_HEADER: self._config.token_secret,
            "Content-Type": "application/json",
            "User-Agent": CLIENT_HEADER_VALUE,
        }

    @staticmethod
    def _unwrap(response: requests.Response, procedure: str) -> Any:
        try:
            body = response.json()
        except ValueError:
            raise UpstreamError(
                f"{procedure}: HTTP {response.status_code} (non-JSON response: "
                f"{response.text[:500]!r})"
            ) from None

        if isinstance(body, dict) and "error" in body:
            err = body["error"]
            if isinstance(err, dict) and "json" in err:
                err = err["json"]
            if isinstance(err, dict):
                code = err.get("code") or err.get("data", {}).get("code") or "ERROR"
                message = err.get("message") or "unknown error"
                raise UpstreamError(f"{procedure}: {code}: {message}")
            raise UpstreamError(f"{procedure}: {err!r}")

        if response.status_code >= 400:
            raise UpstreamError(f"{procedure}: HTTP {response.status_code}")

        if not isinstance(body, dict):
            return body
        return body.get("result", {}).get("data", {}).get("json")
