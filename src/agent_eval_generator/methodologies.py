# SPDX-License-Identifier: MIT

"""Methodology snapshots attached to generated eval profiles.

The lake library agent has no workspace tools. Lake therefore passes the latest
``list_methodologies`` result in the turn body. Direct embeddings may provide a client with a
``read`` method instead. Older engines that answer ``unknown_capability`` are represented by the
documented M-1-only fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

LEGACY_M1 = {
    "id": "M-1",
    "name": "Tabular supervised learning",
    "family": "The tabular decision core",
    "model_kinds": ["gbdt", "classification", "regression", "tabular"],
    "solutions": ["S-1", "S-2", "S-3", "S-4", "S-10"],
    "inputs": [
        {"role": "entity", "required": True, "description": "entity identifier"},
        {"role": "label", "required": True, "description": "outcome column"},
        {
            "role": "time",
            "required": False,
            "description": "point-in-time cutoff column",
        },
    ],
    "outputs": ["model", "scores", "drivers", "ranked entities"],
    "metrics": ["ROC-AUC", "PR-AUC", "log loss", "Brier score", "lift"],
    "runnable": True,
    "partial": False,
    "issue": "",
}


@dataclass(frozen=True)
class MethodologySnapshot:
    """One turn's registry response and whether it came from the legacy fallback."""

    methodologies: list[dict[str, Any]]
    legacy_fallback: bool = False


def _error_code(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or "")
    return str(payload.get("code") or "")


def parse_snapshot(payload: Any) -> MethodologySnapshot:
    """Normalize a list_methodologies response or its unknown-capability fallback."""
    if payload is None or _error_code(payload) == "unknown_capability":
        return MethodologySnapshot([dict(LEGACY_M1)], legacy_fallback=True)

    if isinstance(payload, dict) and payload.get("ok") is False:
        code = _error_code(payload) or "registry_error"
        raise ValueError(f"list_methodologies failed with {code}")

    if isinstance(payload, dict) and isinstance(payload.get("value"), dict):
        payload = payload["value"]

    entries = payload.get("methodologies") if isinstance(payload, dict) else payload
    if not isinstance(entries, list) or not entries:
        raise ValueError(
            "list_methodologies did not return a non-empty methodologies list"
        )

    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id") or not entry.get("name"):
            raise ValueError("list_methodologies returned an entry without id and name")
        if not isinstance(entry.get("solutions"), list):
            raise ValueError(f"methodology {entry['id']} has no solutions list")
        if not isinstance(entry.get("runnable"), bool):
            raise ValueError(f"methodology {entry['id']} has no boolean runnable state")
        if not entry["runnable"] and not entry.get("issue"):
            raise ValueError(f"unrunnable methodology {entry['id']} has no issue")
        normalized.append(dict(entry))
    return MethodologySnapshot(normalized)


def snapshot_for_turn(turn: dict[str, Any], source: Any = None) -> MethodologySnapshot:
    """Read the caller's snapshot, or ask an explicitly injected source for one."""
    if "methodologies" in turn:
        return parse_snapshot(turn["methodologies"])
    if source is not None:
        try:
            return parse_snapshot(source.read("list_methodologies"))
        except Exception as error:
            response = getattr(error, "response", None)
            if response is not None:
                try:
                    return parse_snapshot(response.json())
                except (TypeError, ValueError):
                    pass
            raise
    return parse_snapshot(None)


def apply_snapshot(
    profile: dict[str, Any], snapshot: MethodologySnapshot
) -> dict[str, Any]:
    """Attach support facts from the registry to a model-selected methodology."""
    methodology_id = profile.get("methodology")
    solution = profile.get("solution")
    if not isinstance(methodology_id, str) or not methodology_id:
        raise ValueError("the generated profile does not name a methodology")
    if not isinstance(solution, str) or not solution:
        raise ValueError("the generated profile does not name a solution")

    selected = next(
        (
            entry
            for entry in snapshot.methodologies
            if entry.get("id") == methodology_id
        ),
        None,
    )
    if selected is None:
        available = ", ".join(entry["id"] for entry in snapshot.methodologies)
        raise ValueError(
            f"methodology {methodology_id} is not in this turn's registry ({available})"
        )

    solutions = selected.get("solutions") or []
    if solution not in solutions:
        raise ValueError(
            f"solution {solution} does not use {methodology_id} in this turn's registry"
        )

    runnable = bool(selected.get("runnable"))
    profile["runnable"] = runnable
    if runnable:
        profile.pop("issue", None)
    else:
        issue = selected.get("issue")
        if not issue:
            raise ValueError(f"unrunnable methodology {methodology_id} has no issue")
        profile["issue"] = issue
    return selected
