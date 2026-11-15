"""Task credentials by reference (lake#871, lake docs/api/agent-bus.md).

A claim asks Lake for `credentials: by_reference`: the body arrives with no credential, and every
call made for the task carries this agent's bus credential and `X-Lake-Agent-Task: <task id>`. A
Lake from before lake#871 refuses the field; the claim is asked again and the body's own credential
is used, as before.
"""

from __future__ import annotations

import json
import threading
import urllib.parse
from typing import Any

import pytest

from types import SimpleNamespace

from agent_eval_generator import lake_bus, service, tools

TASK = {"task_id": "t1", "customer_id": "c", "workspace_id": "w", "kind": "ask"}


class BusLake:
    """lake's bus in memory. `supports_by_reference` False is a Lake from before lake#871."""

    def __init__(self, supports_by_reference: bool) -> None:
        self.supports_by_reference = supports_by_reference
        self.claims: list[dict[str, Any]] = []
        self.headers: list[dict[str, str]] = []
        self.stop = threading.Event()
        self.received = False

    def send(self, method: str, url: str, headers: dict[str, str],
             body: bytes | None) -> tuple[int, str]:
        self.headers.append(headers)
        capability = urllib.parse.urlparse(url).path.rsplit("/", 1)[-1]
        if capability == "receive_agent_tasks":
            tasks = [] if self.received else [{"sequence": 1, **TASK}]
            self.received = True
            if not tasks:
                self.stop.set()
            return 200, json.dumps({"ok": True, "value": {"tasks": tasks, "next_sequence": 2}})
        arguments = json.loads(body or b"{}")
        if capability == "claim_agent_task":
            self.claims.append(arguments)
            if "credentials" in arguments and not self.supports_by_reference:
                return 400, json.dumps({"ok": False, "error": {
                    "code": "invalid_input", "message": "unexpected field credentials",
                    "path": "/credentials"}})
            by_reference = arguments.get("credentials") == "by_reference"
            credential = "" if by_reference else "lat.t1.secret"
            value = {**TASK, "body": {"message": "hi", "lake_token": credential,
                                      "zetta_token": credential}}
            if by_reference:
                value["credentials"] = "by_reference"
            return 200, json.dumps({"ok": True, "value": value})
        return 200, json.dumps({"ok": True, "value": {}})


def handed_body(lake: BusLake) -> dict[str, Any]:
    handed: list[dict[str, Any]] = []
    bus = lake_bus.LakeBus("http://lake", "bus-token", "agent-eval-generator", send=lake.send)
    lake_bus.work(bus, lambda body: handed.append(body) or {"ok": True}, lake.stop, workers=1)
    assert len(handed) == 1, handed
    return handed[0]


def test_a_claim_asks_by_reference_and_the_turn_holds_no_task_credential():
    lake = BusLake(supports_by_reference=True)
    body = handed_body(lake)
    assert lake.claims == [{"task_id": "t1", "agent": "agent-eval-generator", "credentials": "by_reference"}]
    assert body["lake_token"] == "bus-token", "the turn calls Lake with the bus credential"
    assert body["zetta_token"] == "bus-token"
    assert body["lake_headers"] == {"X-Lake-Agent-Task": "t1"}
    assert lake_bus.task_headers(body) == {"X-Lake-Agent-Task": "t1"}
    # Bus calls themselves never name a task: Lake would answer them as the task.
    assert all(lake_bus.TASK_HEADER not in headers for headers in lake.headers)


def test_a_lake_from_before_by_reference_is_claimed_again_with_the_credential_in_the_body():
    lake = BusLake(supports_by_reference=False)
    body = handed_body(lake)
    assert lake.claims == [
        {"task_id": "t1", "agent": "agent-eval-generator", "credentials": "by_reference"},
        {"task_id": "t1", "agent": "agent-eval-generator"},
    ]
    assert body["lake_token"] == "lat.t1.secret", "the body's own credential is used, as before"
    assert "lake_headers" not in body
    assert lake_bus.task_headers(body) == {}


def test_a_claim_refused_for_another_reason_is_not_asked_again():
    assert not lake_bus.refuses_by_reference(
        lake_bus.BusError("invalid_input", "task_id is required"))
    assert lake_bus.refuses_by_reference(
        lake_bus.BusError("invalid_input", "unexpected field credentials"))

    claims: list[dict[str, Any]] = []

    def send(method, url, headers, body):
        claims.append(json.loads(body or b"{}"))
        return 403, json.dumps({"ok": False, "error": {"code": "forbidden", "message": "no"}})

    bus = lake_bus.LakeBus("http://lake", "bus-token", "agent-eval-generator", send=send)
    with pytest.raises(lake_bus.BusError):
        bus.claim("t1")
    assert len(claims) == 1


def test_task_headers_take_only_the_task_header():
    assert lake_bus.task_headers({"lake_headers": {"X-Lake-Agent-Task": "t1",
                                                   "Authorization": "Bearer other"}}) == {
        "X-Lake-Agent-Task": "t1"}
    assert lake_bus.task_headers({"lake_headers": "t1"}) == {}
    assert lake_bus.task_headers({}) == {}


LAKE = "http://lake:8080"


class Registries:
    def read(self, capability, **params):
        if capability == "list_solutions":
            return {"ok": True, "value": {"solutions": [
                {"id": "S-1", "name": "Churn", "runnable": True}]}}
        return {"ok": True, "value": {"methodologies": [
            {"id": "M-1", "name": "Tabular", "solutions": ["S-1"], "runnable": True,
             "partial": False, "issue": ""}]}}


def by_reference_turn() -> dict[str, Any]:
    claimed = {**TASK, "credentials": "by_reference",
               "body": {"request": "x", "lake_token": "", "customer_id": "cust-1"}}
    return lake_bus.task_credentials("bus-token", claimed)


def in_body_turn() -> dict[str, Any]:
    claimed = {**TASK, "body": {"request": "x", "lake_token": "lat.t1.secret",
                                "customer_id": "cust-1"}}
    return lake_bus.task_credentials("bus-token", claimed)


@pytest.fixture
def reads(monkeypatch):
    """Every workspace read a LakeWorkspaceClient makes, answered with empty registries, which
    end the turn before the model."""
    requests: list[dict] = []

    def post(url, **kwargs):
        requests.append({"url": url, **kwargs})
        response = SimpleNamespace()
        response.raise_for_status = lambda: None
        response.json = lambda: {"ok": True, "value": {"solutions": [], "methodologies": []}}
        return response

    monkeypatch.setattr(tools.httpx, "post", post)
    monkeypatch.setattr(
        service, "gateway_client",
        lambda url, token, **kw: pytest.fail(f"model called at {url}"))
    monkeypatch.setenv("LAKE_URL", LAKE)
    return requests


def test_every_workspace_read_of_a_by_reference_turn_names_its_task(reads):
    answer = service.run_turn(by_reference_turn())
    assert not answer["ok"] and "registry" in answer["error"]
    assert reads, "the registries were never read"
    for request in reads:
        assert request["headers"] == {"X-Lake-Agent-Task": "t1",
                                      "Authorization": "Bearer bus-token"}


def test_an_in_body_turns_reads_send_no_task_header(reads):
    service.run_turn(in_body_turn())
    assert reads
    for request in reads:
        assert request["headers"] == {"Authorization": "Bearer lat.t1.secret"}


@pytest.mark.parametrize("turn, token, headers", [
    (by_reference_turn(), "bus-token", {"X-Lake-Agent-Task": "t1"}),
    (in_body_turn(), "lat.t1.secret", {}),
])
def test_the_model_client_names_the_task_only_by_reference(monkeypatch, turn, token, headers):
    monkeypatch.setenv("LAKE_URL", LAKE)
    called: list[tuple[str, dict]] = []

    def gateway(url, key, **kwargs):
        called.append((key, kwargs.get("headers") or {}))
        raise RuntimeError("stop")

    monkeypatch.setattr(service, "gateway_client", gateway)
    with pytest.raises(RuntimeError):
        service.run_turn(turn, None, Registries())
    assert called == [(token, headers)]
