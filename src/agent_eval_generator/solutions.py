# SPDX-License-Identifier: MIT

"""Solution registry snapshots and profile scoring contracts.

The catalogue belongs to Zetta. The generator reads ``list_solutions`` before
generation and ``get_solution`` after the model selects an entry, on every turn.
No local list stands in for a workspace whose registry is absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SolutionSnapshot:
    """One turn's list response; an absent registry has no entries."""

    solutions: list[dict[str, Any]]
    deployed: bool = True


def _error_code(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or "")
    return str(payload.get("code") or "")


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and isinstance(payload.get("value"), dict):
        return payload["value"]
    return payload


def parse_list(payload: Any) -> SolutionSnapshot:
    """Normalize ``list_solutions`` without inventing a compatibility catalogue."""
    if payload is None or _error_code(payload) == "unknown_capability":
        return SolutionSnapshot([], deployed=False)

    if isinstance(payload, dict) and payload.get("ok") is False:
        code = _error_code(payload) or "registry_error"
        raise ValueError(f"list_solutions failed with {code}")

    payload = _unwrap(payload)
    entries = payload.get("solutions") if isinstance(payload, dict) else payload
    if not isinstance(entries, list):
        raise ValueError("list_solutions did not return a solutions list")

    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("id") or not entry.get("name"):
            raise ValueError("list_solutions returned an entry without id and name")
        if not isinstance(entry.get("runnable"), bool):
            raise ValueError(f"solution {entry['id']} has no boolean runnable state")
        if not entry["runnable"] and not entry.get("issue"):
            raise ValueError(f"unrunnable solution {entry['id']} has no issue")
        normalized.append(dict(entry))
    return SolutionSnapshot(normalized)


def snapshot_for_turn(source: Any) -> SolutionSnapshot:
    """Read the current catalogue; a missing source means there is no registry."""
    if source is None:
        return parse_list(None)
    try:
        return parse_list(source.read("list_solutions"))
    except Exception as error:
        response = getattr(error, "response", None)
        if response is not None:
            try:
                return parse_list(response.json())
            except (TypeError, ValueError):
                pass
        raise


def _parse_detail(payload: Any) -> dict[str, Any]:
    if _error_code(payload) == "unknown_capability":
        raise ValueError("get_solution is not deployed yet")
    if isinstance(payload, dict) and payload.get("ok") is False:
        code = _error_code(payload) or "registry_error"
        raise ValueError(f"get_solution failed with {code}")
    payload = _unwrap(payload)
    solution = payload.get("solution") if isinstance(payload, dict) else None
    if not isinstance(solution, dict):
        raise ValueError("get_solution did not return a solution")
    return dict(solution)


def _selected_level(solution: dict[str, Any], level: int) -> dict[str, Any]:
    levels = solution.get("capability_levels")
    if not isinstance(levels, list):
        raise ValueError(f"solution {solution.get('id')} has no capability levels")
    selected = next(
        (
            entry
            for entry in levels
            if isinstance(entry, dict) and entry.get("level") == level
        ),
        None,
    )
    if selected is None:
        raise ValueError(
            f"level {level} is not declared by solution {solution.get('id')}"
        )
    return dict(selected)


def _correctness_checks(
    solution: dict[str, Any], level: int, capability_level: dict[str, Any]
) -> dict[str, Any]:
    composition = solution.get("composition")
    pipeline_order = solution.get("pipeline_order")
    data_roles = solution.get("required_data_roles")
    guardrails = solution.get("guardrails")
    measurement = solution.get("measurement_design")
    if not isinstance(composition, list):
        raise ValueError(f"solution {solution.get('id')} has no composition")
    if not isinstance(pipeline_order, list):
        raise ValueError(f"solution {solution.get('id')} has no pipeline order")
    if not isinstance(data_roles, list):
        raise ValueError(f"solution {solution.get('id')} has no required data roles")
    if not isinstance(guardrails, list) or not isinstance(measurement, str):
        raise ValueError(f"solution {solution.get('id')} has incomplete checks")

    selected_composition = [
        dict(entry)
        for entry in composition
        if isinstance(entry, dict)
        and isinstance(entry.get("minimum_level"), int)
        and entry["minimum_level"] <= level
    ]
    selected_ids = {
        entry.get("methodology")
        for entry in selected_composition
        if entry.get("methodology")
    }
    selected_order = [
        methodology
        for methodology in pipeline_order
        if methodology in selected_ids
    ]
    if not selected_composition or len(selected_order) != len(selected_ids):
        raise ValueError(f"solution {solution.get('id')} has inconsistent composition")

    return {
        "capability_level": capability_level,
        "composition": selected_composition,
        "pipeline_order": selected_order,
        "required_data_roles": data_roles,
        "measurement_design": measurement,
        "guardrails": guardrails,
    }


def apply_solution(
    profile: dict[str, Any], snapshot: SolutionSnapshot, source: Any
) -> dict[str, Any]:
    """Fetch the selected solution and attach its exact offline scoring contract."""
    solution_id = profile.get("solution")
    level = profile.get("level")
    if not isinstance(solution_id, str) or not solution_id:
        raise ValueError("the generated profile does not name a solution")
    if not isinstance(level, int) or isinstance(level, bool):
        raise ValueError("the generated profile does not name an integer solution level")

    listed = next(
        (entry for entry in snapshot.solutions if entry.get("id") == solution_id),
        None,
    )
    if listed is None:
        available = ", ".join(entry["id"] for entry in snapshot.solutions)
        raise ValueError(
            f"solution {solution_id} is not in this turn's registry ({available})"
        )
    if source is None:
        raise ValueError("get_solution cannot run without a registry source")

    detail = _parse_detail(source.read("get_solution", solution=solution_id))
    if detail.get("id") != solution_id:
        raise ValueError(
            f"get_solution returned {detail.get('id')} for requested {solution_id}"
        )
    if detail.get("status") == "sketch":
        raise ValueError(f"{solution_id} is a sketch, not a catalogue solution")

    capability_level = _selected_level(detail, level)
    decision_policy = detail.get("decision_policy_template")
    if not isinstance(decision_policy, str) or not decision_policy:
        raise ValueError(f"solution {solution_id} has no decision policy")
    checks = _correctness_checks(detail, level, capability_level)
    selected_methodologies = {
        entry.get("methodology") for entry in checks["composition"]
    }
    if profile.get("methodology") not in selected_methodologies:
        raise ValueError(
            f"methodology {profile.get('methodology')} is not part of "
            f"{solution_id} at level {level}"
        )

    methodology_runnable = profile.get("runnable") is True
    methodology_issue = profile.get("issue")
    solution_runnable = detail.get("runnable")
    if not isinstance(solution_runnable, bool):
        raise ValueError(f"solution {solution_id} has no boolean runnable state")

    profile["solution_checks"] = checks
    profile["decision_policy"] = decision_policy
    profile["runnable"] = methodology_runnable and solution_runnable
    if not solution_runnable:
        issue = detail.get("issue")
        if not issue:
            raise ValueError(f"unrunnable solution {solution_id} has no issue")
        profile["issue"] = issue
    elif not methodology_runnable:
        if not methodology_issue:
            raise ValueError("the selected methodology is unrunnable without an issue")
        profile["issue"] = methodology_issue
    else:
        profile.pop("issue", None)
    return detail
