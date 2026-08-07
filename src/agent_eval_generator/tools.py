"""Tool definitions for the eval generator — every call goes to a live Zetta node.

An agent scaffolded against mocks proves nothing about whether the platform supports the job,
which is the question this bootstrap exists to answer (zetta#986). So there is no mock transport
here and no `if testing:` branch: if the node is not up, the agent fails rather than pretending.

Two things that cost real time when they were guessed:
  * `--listen` sets the PEER port. The API, MCP and web UI stay on 4800.
  * Reads are GET, actions are POST (zetta#954). Probing a read with POST returns an empty reply
    indistinguishable from a hang.
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class ZettaClient:
    """Thin, honest client. Raises on failure rather than returning a plausible empty result."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or os.environ["ZETTA_BASE_URL"]).rstrip("/")
        self.token = token or os.environ["ZETTA_TOKEN"]
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=120.0,
        )

    def read(self, capability: str, **params: Any) -> dict[str, Any]:
        """A read capability. GET, per zetta#954."""
        response = self._client.get(f"/v1/{capability}", params=params)
        response.raise_for_status()
        return response.json()

    def act(self, capability: str, **body: Any) -> dict[str, Any]:
        """An action capability. POST."""
        response = self._client.post(f"/v1/{capability}", json=body)
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._client.close()


# The tool surface offered to the frontier model.
#
# HAND-WRITTEN TODAY, AND THAT IS A KNOWN DEFECT. The first run failed on `get_dataset` because
# this list said the parameter was `name` when the capability requires `dataset` — precisely the
# failure the repo's "render from source, never retype" rule exists to prevent, made on the first
# attempt. `derive_tool_specs()` below reads the node's own OpenAPI so the list cannot drift; the
# static table remains only as the fallback when a node is unreachable.
TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_datasets",
            "description": "List the datasets on this node, with row and column counts.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dataset",
            "description": "Read one dataset's schema: column names, types, null rates.",
            "parameters": {
                "type": "object",
                "properties": {"dataset": {"type": "string"}},
                "required": ["dataset"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_models",
            "description": "List the trained models and their measures.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "model_health",
            "description": (
                "Whether a deployed model can still be trusted: the held-out figure, the "
                "overfitting gap, whether scores are calibrated."
            ),
            "parameters": {
                "type": "object",
                "properties": {"model_id": {"type": "string"}},
                "required": ["model_id"],
            },
        },
    },
]

READ_CAPABILITIES = {spec["function"]["name"] for spec in TOOL_SPECS}


def derive_tool_specs(client: ZettaClient, allow: set[str] | None = None) -> list[dict[str, Any]]:
    """Build the tool list from the node's OWN OpenAPI spec.

    The node is the source of truth for its capabilities. A retyped list is wrong the day someone
    adds a capability or renames a parameter, and it was wrong on the very first run here.
    """
    spec = client._client.get("/v1/openapi.json").json()
    wanted = allow or READ_CAPABILITIES
    derived: list[dict[str, Any]] = []
    for path, methods in spec.get("paths", {}).items():
        capability = path.rsplit("/", 1)[-1]
        if capability not in wanted or "get" not in methods:
            continue
        operation = methods["get"]
        properties: dict[str, Any] = {}
        required: list[str] = []
        for parameter in operation.get("parameters", []):
            properties[parameter["name"]] = parameter.get("schema", {"type": "string"})
            if parameter.get("required"):
                required.append(parameter["name"])
        derived.append({
            "type": "function",
            "function": {
                "name": capability,
                "description": operation.get("summary") or operation.get("description", ""),
                "parameters": {
                    "type": "object", "properties": properties, "required": required,
                },
            },
        })
    return derived or TOOL_SPECS


def dispatch(client: ZettaClient, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Run one tool call against the node.

    Unknown tools fail loudly. A model that invents a capability must not receive a plausible
    result — that is how a hallucinated tool call becomes training data.
    """
    if name not in READ_CAPABILITIES:
        raise ValueError(
            f"unknown tool {name!r}; this node exposes {sorted(READ_CAPABILITIES)}"
        )
    return client.read(name, **arguments)
