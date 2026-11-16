# SPDX-License-Identifier: MIT

"""The Eval Generator as a lake library agent (lake#263): one profile per request, nothing published."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from agent_eval_generator import service
from agent_eval_generator.tools import LakeWorkspaceClient

PROFILE = json.loads(
    Path(
        "evals/profiles/churn-chief-operating-officer-enterprise/profile.json"
    ).read_text()
)

M1 = {
    "id": "M-1",
    "name": "Tabular supervised learning",
    "solutions": ["S-1"],
    "runnable": True,
    "partial": False,
    "issue": "",
}
M4 = {
    "id": "M-4",
    "name": "Time-series forecasting",
    "solutions": ["S-5"],
    "runnable": False,
    "partial": False,
    "issue": "https://github.com/oramasearch/zetta/issues/1043",
}
S1 = {
    "id": "S-1",
    "name": "Churn & Retention",
    "composition": [
        {"methodology": "M-1", "role": "primary", "minimum_level": 1},
        {"methodology": "M-6", "role": "attachable", "minimum_level": 3},
    ],
    "pipeline_order": ["M-1", "M-6"],
    "required_data_roles": [
        {"role": "entity", "required": True, "description": "customer"},
        {"role": "label", "required": True, "description": "churn event"},
    ],
    "decision_policy_template": "Eligibility, contact caps, and approvals.",
    "measurement_design": "Permanent holdout with incremental read-back.",
    "guardrails": ["complaints", "margin"],
    "capability_levels": [
        {"level": 1, "name": "CL-1", "description": "propensity and report"},
        {"level": 2, "name": "CL-2", "description": "add survival timing"},
        {"level": 3, "name": "CL-3", "description": "add uplift targeting"},
        {"level": 4, "name": "CL-4", "description": "add arbitration"},
    ],
    "status": "catalogue",
    "runnable": True,
    "issue": "",
}
S5 = {
    **S1,
    "id": "S-5",
    "name": "Demand Forecasting",
    "composition": [
        {"methodology": "M-4", "role": "primary", "minimum_level": 1}
    ],
    "pipeline_order": ["M-4"],
    "decision_policy_template": "Planner-owned exceptions and override reasons.",
    "runnable": False,
    "issue": "https://github.com/oramasearch/zetta/issues/1102",
}


class Scripted:
    def __init__(self, content: str) -> None:
        self.sent: list = []
        message = SimpleNamespace(content=content, tool_calls=None)
        message.model_dump = lambda exclude_none=True: {
            "role": "assistant",
            "content": content,
        }
        reply = SimpleNamespace(choices=[SimpleNamespace(message=message)])

        def create(**kwargs):
            self.sent.append(kwargs)
            return reply

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


class FakeZetta:
    def __init__(
        self,
        methodologies: dict | None = None,
        solutions: dict | None = None,
        details: dict[str, dict] | None = None,
    ) -> None:
        self.methodologies = (
            methodologies
            if methodologies is not None
            else {"methodologies": [M1, M4]}
        )
        self.solutions = (
            solutions if solutions is not None else {"solutions": [S1, S5]}
        )
        self.details = details if details is not None else {"S-1": S1, "S-5": S5}
        self.calls: list[tuple[str, dict]] = []
        self.closed = False

    def read(self, capability: str, **params) -> dict:
        self.calls.append((capability, params))
        if capability == "list_methodologies":
            if self.methodologies.get("ok") is False:
                return self.methodologies
            return {"ok": True, "value": self.methodologies}
        if capability == "list_solutions":
            if self.solutions.get("ok") is False:
                return self.solutions
            return {"ok": True, "value": self.solutions}
        if capability == "get_solution":
            return {
                "ok": True,
                "value": {"solution": self.details[params["solution"]]},
            }
        raise AssertionError(capability)

    def close(self) -> None:
        self.closed = True


def test_lake_workspace_reads_use_the_turns_customer_and_credential():
    sent: list[dict] = []

    def send(url, **kwargs):
        sent.append({"url": url, **kwargs})
        response = SimpleNamespace()
        response.raise_for_status = lambda: None
        response.json = lambda: {"ok": True, "value": {"solutions": []}}
        return response

    source = LakeWorkspaceClient(
        "https://lake.example/", "lat.task.secret", "customer-7", send=send
    )

    assert source.read("list_solutions") == {
        "ok": True,
        "value": {"solutions": []},
    }
    assert sent == [
        {
            "url": "https://lake.example/v1/workspace_query",
            "headers": {"Authorization": "Bearer lat.task.secret"},
            "json": {
                "customer_id": "customer-7",
                "capability": "list_solutions",
                "input": {},
            },
            "timeout": 120.0,
        }
    ]


def test_a_request_steers_one_profile_and_answers_its_tables(tmp_path):
    profile = deepcopy(PROFILE)
    profile["solution"] = "S-1"
    profile["level"] = 1
    profile["methodology"] = "M-1"
    client = Scripted("```json\n" + json.dumps(profile) + "\n```")
    zetta = FakeZetta()
    answer = service.run_turn(
        {"request": "collections at a water utility"}, client, zetta, "m", tmp_path
    )
    assert answer["ok"], answer
    assert "collections at a water utility" in client.sent[0]["messages"][1]["content"]
    result = answer["result"]
    assert (
        result["kind"] == "eval_profile"
        and result["profile"]["profile_id"] == PROFILE["profile_id"]
    )
    assert result["tables"] and all(item["rows"] > 0 for item in result["tables"])
    assert len(result["tables"][0]["sample"]) <= service.SAMPLE_ROWS
    assert PROFILE["profile_id"] in answer["reply"]
    assert "#" not in answer["reply"].split("\n")[0], (
        "no markdown heading in the summary"
    )
    assert client.sent[0]["tools"] == [], "a test case invents its own tables"
    assert result["profile"]["methodology"] == "M-1"
    assert result["profile"]["level"] == 1
    assert result["profile"]["decision_policy"] == S1["decision_policy_template"]
    checks = result["profile"]["solution_checks"]
    assert checks["capability_level"]["name"] == "CL-1"
    assert checks["pipeline_order"] == ["M-1"]
    assert checks["measurement_design"] == S1["measurement_design"]
    assert result["profile"]["runnable"] is True
    assert result["scoreable"] is True
    assert zetta.calls == [
        ("list_methodologies", {}),
        ("list_solutions", {}),
        ("get_solution", {"solution": "S-1"}),
    ]
    assert '"id": "M-4"' in client.sent[0]["messages"][0]["content"]
    assert '"id": "S-5"' in client.sent[0]["messages"][0]["content"]


def test_the_caller_can_pass_the_turns_registry_snapshot(tmp_path):
    profile = deepcopy(PROFILE)
    profile["level"] = 1
    client = Scripted(json.dumps(profile))
    zetta = FakeZetta(
        methodologies={"ok": False, "error": {"code": "must_not_be_called"}}
    )

    answer = service.run_turn(
        {"request": "predict churn", "methodologies": {"methodologies": [M1]}},
        client,
        zetta,
        "m",
        tmp_path,
    )

    assert answer["ok"], answer
    assert answer["result"]["profile"]["methodology"] == "M-1"
    assert zetta.calls == [
        ("list_solutions", {}),
        ("get_solution", {"solution": "S-1"}),
    ]


def test_an_unrunnable_solution_is_declined_for_scoring_with_its_issue(tmp_path):
    profile = deepcopy(PROFILE)
    profile["solution"] = "S-5"
    profile["level"] = 1
    profile["methodology"] = "M-4"
    profile["runnable"] = True
    client = Scripted(json.dumps(profile))
    zetta = FakeZetta()

    answer = service.run_turn(
        {"request": "forecast demand"}, client, zetta, "m", tmp_path
    )

    assert answer["ok"], answer
    result = answer["result"]
    assert result["profile"]["runnable"] is False
    assert result["profile"]["issue"] == S5["issue"]
    assert result["scoreable"] is False
    assert "declined this profile for scoring" in answer["reply"]
    assert "Demand Forecasting (S-5) at level 1" in answer["reply"]
    assert S5["issue"] in answer["reply"]


def test_an_engine_without_the_solution_registry_has_no_solutions(tmp_path):
    profile = deepcopy(PROFILE)
    profile["solution"] = "S-1"
    profile["level"] = 1
    profile["methodology"] = "M-1"
    client = Scripted(json.dumps(profile))
    unknown = {
        "ok": False,
        "error": {"code": "unknown_capability", "message": "not found"},
    }
    zetta = FakeZetta(
        methodologies=unknown,
        solutions=unknown,
    )

    answer = service.run_turn(
        {"request": "predict churn"}, client, zetta, "m", tmp_path
    )

    assert not answer["ok"]
    assert "not deployed yet" in answer["error"]
    assert "no solutions" in answer["error"]
    assert client.sent == []
    assert zetta.calls == [
        ("list_methodologies", {}),
        ("list_solutions", {}),
    ]


def test_no_profile_is_a_failure_not_a_guess(tmp_path):
    answer = service.run_turn(
        {"request": "x"}, Scripted("I cannot."), FakeZetta(), "m", tmp_path
    )
    assert not answer["ok"] and "no eval profile" in answer["error"]


def test_the_summary_is_prose_not_a_heading():
    assert (
        service.first_sentence("### Situation\n\nThe utility bills 40k homes. More.")
        == "The utility bills 40k homes."
    )


def test_a_turn_calls_its_model_through_lakes_gateway_with_the_turns_key(tmp_path, monkeypatch):
    """lake#248: the model is lake's `/openai/v1`, with the turn's own key, never a provider key."""
    import httpx

    from agent_eval_generator import model

    profile = deepcopy(PROFILE)
    profile["solution"] = "S-1"
    profile["level"] = 1
    profile["methodology"] = "M-1"
    seen: list[httpx.Request] = []

    def gateway(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={
            "id": "chatcmpl-1", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": "```json\n" + json.dumps(profile) + "\n```"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}})

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(service, "gateway_client", lambda url, token: model.gateway_client(
        url, token, http_client=httpx.Client(transport=httpx.MockTransport(gateway))))
    monkeypatch.setenv("LAKE_URL", "http://lake:8080")
    # The turn's own lake_url is never used: the key goes to this service's LAKE_URL (#13).
    answer = service.run_turn(
        {"request": "collections at a water utility", "lake_url": "http://elsewhere:9",
         "lake_token": "lat.task.secret"}, None, FakeZetta(), "m", tmp_path)
    assert answer["ok"], answer
    assert [str(request.url) for request in seen] == ["http://lake:8080/openai/v1/chat/completions"]
    assert seen[0].headers["authorization"] == "Bearer lat.task.secret"

    refused = service.run_turn({"request": "x"}, None, FakeZetta(), "m", tmp_path)
    assert not refused["ok"] and "lake_token" in refused["error"]
    assert len(seen) == 1

    monkeypatch.delenv("LAKE_URL", raising=False)
    refused = service.run_turn({"request": "x", "lake_url": "http://lake:8080",
                                "lake_token": "lat.task.secret"}, None, FakeZetta(), "m", tmp_path)
    assert not refused["ok"] and "LAKE_URL is not set" in refused["error"]
    assert len(seen) == 1
