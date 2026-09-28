"""The Eval Generator as a lake library agent (lake#263): one profile per request, nothing published."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from agent_eval_generator import service

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
    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[str] = []
        self.closed = False

    def read(self, capability: str) -> dict:
        self.calls.append(capability)
        return self.response

    def close(self) -> None:
        self.closed = True


def test_a_request_steers_one_profile_and_answers_its_tables(tmp_path):
    profile = deepcopy(PROFILE)
    profile["solution"] = "S-1"
    profile["methodology"] = "M-1"
    client = Scripted("```json\n" + json.dumps(profile) + "\n```")
    zetta = FakeZetta({"methodologies": [M1, M4]})
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
    assert result["profile"]["runnable"] is True
    assert result["scoreable"] is True
    assert zetta.calls == ["list_methodologies"]
    assert '"id": "M-4"' in client.sent[0]["messages"][0]["content"]


def test_the_caller_can_pass_the_turns_registry_snapshot(tmp_path):
    profile = deepcopy(PROFILE)
    client = Scripted(json.dumps(profile))
    zetta = FakeZetta({"ok": False, "error": {"code": "must_not_be_called"}})

    answer = service.run_turn(
        {"request": "predict churn", "methodologies": {"methodologies": [M1]}},
        client,
        zetta,
        "m",
        tmp_path,
    )

    assert answer["ok"], answer
    assert answer["result"]["profile"]["methodology"] == "M-1"
    assert zetta.calls == []


def test_an_unrunnable_methodology_is_declined_for_scoring_with_its_issue(tmp_path):
    profile = deepcopy(PROFILE)
    profile["solution"] = "S-5"
    profile["methodology"] = "M-4"
    profile["runnable"] = True
    client = Scripted(json.dumps(profile))
    zetta = FakeZetta({"methodologies": [M1, M4]})

    answer = service.run_turn(
        {"request": "forecast demand"}, client, zetta, "m", tmp_path
    )

    assert answer["ok"], answer
    result = answer["result"]
    assert result["profile"]["runnable"] is False
    assert result["profile"]["issue"] == M4["issue"]
    assert result["scoreable"] is False
    assert "declined this profile for scoring" in answer["reply"]
    assert "Time-series forecasting (M-4)" in answer["reply"]
    assert M4["issue"] in answer["reply"]


def test_an_old_engine_falls_back_to_m1_and_says_so(tmp_path):
    profile = deepcopy(PROFILE)
    profile["solution"] = "S-1"
    profile["methodology"] = "M-1"
    client = Scripted(json.dumps(profile))
    zetta = FakeZetta(
        {
            "ok": False,
            "error": {"code": "unknown_capability", "message": "not found"},
        }
    )

    answer = service.run_turn(
        {"request": "predict churn"}, client, zetta, "m", tmp_path
    )

    assert answer["ok"], answer
    assert answer["result"]["profile"]["methodology"] == "M-1"
    assert answer["result"]["profile"]["runnable"] is True
    assert answer["result"]["scoreable"] is True
    assert "only M-1 is assumed to run" in answer["reply"]
    prompt = client.sent[0]["messages"][0]["content"]
    assert "old-engine fallback" in prompt
    assert '"id": "M-1"' in prompt


def test_no_profile_is_a_failure_not_a_guess(tmp_path):
    answer = service.run_turn(
        {"request": "x"}, Scripted("I cannot."), None, "m", tmp_path
    )
    assert not answer["ok"] and "no eval profile" in answer["error"]


def test_the_summary_is_prose_not_a_heading():
    assert (
        service.first_sentence("### Situation\n\nThe utility bills 40k homes. More.")
        == "The utility bills 40k homes."
    )
