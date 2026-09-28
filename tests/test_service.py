"""The Eval Generator as a lake library agent (lake#263): one profile per request, nothing published."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from agent_eval_generator import service

PROFILE = json.loads(next(Path("evals/profiles").glob("*/profile.json")).read_text())


class Scripted:
    def __init__(self, content: str) -> None:
        self.sent: list = []
        message = SimpleNamespace(content=content, tool_calls=None)
        message.model_dump = lambda exclude_none=True: {"role": "assistant", "content": content}
        reply = SimpleNamespace(choices=[SimpleNamespace(message=message)])

        def create(**kwargs):
            self.sent.append(kwargs)
            return reply
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


class FakeZetta:
    closed = False

    def close(self) -> None:
        self.closed = True


def test_a_request_steers_one_profile_and_answers_its_tables(tmp_path):
    client, zetta = Scripted("```json\n" + json.dumps(PROFILE) + "\n```"), None
    answer = service.run_turn({"request": "collections at a water utility"}, client, zetta,
                              "m", tmp_path)
    assert answer["ok"], answer
    assert "collections at a water utility" in client.sent[0]["messages"][1]["content"]
    result = answer["result"]
    assert result["kind"] == "eval_profile" and result["profile"]["profile_id"] == PROFILE["profile_id"]
    assert result["tables"] and all(item["rows"] > 0 for item in result["tables"])
    assert len(result["tables"][0]["sample"]) <= service.SAMPLE_ROWS
    assert PROFILE["profile_id"] in answer["reply"]
    assert "#" not in answer["reply"].split("\n")[0], "no markdown heading in the summary"
    assert client.sent[0]["tools"] == [], "a test case invents its own tables"


def test_no_profile_is_a_failure_not_a_guess(tmp_path):
    answer = service.run_turn({"request": "x"}, Scripted("I cannot."), None, "m", tmp_path)
    assert not answer["ok"] and "no eval profile" in answer["error"]


def test_the_summary_is_prose_not_a_heading():
    assert service.first_sentence("### Situation\n\nThe utility bills 40k homes. More.") == \
        "The utility bills 40k homes."
