# SPDX-License-Identifier: MIT

"""A turn's credential goes only to Lake at LAKE_URL, never to an address the request names (#13)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_eval_generator import service, tools

LAKE = "http://lake-prod.lake.svc.cluster.local:80"


@pytest.fixture
def sent(monkeypatch):
    """Every workspace read any LakeWorkspaceClient makes, answered with empty registries; the
    model is never reached because the registries are empty."""
    requests: list[dict] = []

    def post(url, **kwargs):
        requests.append({"url": url, **kwargs})
        response = SimpleNamespace()
        response.raise_for_status = lambda: None
        response.json = lambda: {"ok": True, "value": {"solutions": [], "methodologies": []}}
        return response

    monkeypatch.setattr(tools.httpx, "post", post)
    monkeypatch.setattr(
        service, "gateway_client", lambda url, token: pytest.fail(f"model called at {url}")
    )
    return requests


def turn(**extra):
    return {"request": "x", "lake_token": "lat.task.secret", "customer_id": "cust-1", **extra}


def test_workspace_reads_go_to_lake_url_not_the_turns_lake_url(monkeypatch, sent):
    monkeypatch.setenv("LAKE_URL", LAKE)
    answer = service.run_turn(turn(lake_url="http://attacker.example"))
    # The empty registry ends the turn before the model, after reading through Lake.
    assert not answer["ok"] and "registry" in answer["error"]
    assert sent, "the registries were never read"
    assert all(request["url"] == LAKE + "/v1/workspace_query" for request in sent)
    assert all(
        request["headers"]["Authorization"] == "Bearer lat.task.secret" for request in sent
    )


def test_the_model_address_is_lake_url_not_the_turns_lake_url(monkeypatch):
    monkeypatch.setenv("LAKE_URL", LAKE)
    called: list[str] = []

    def gateway(url, token):
        called.append(url)
        raise RuntimeError("stop")

    class Registries:
        def read(self, capability, **params):
            if capability == "list_solutions":
                return {"ok": True, "value": {"solutions": [
                    {"id": "S-1", "name": "Churn", "runnable": True}]}}
            return {"ok": True, "value": {"methodologies": [
                {"id": "M-1", "name": "Tabular", "solutions": ["S-1"], "runnable": True,
                 "partial": False, "issue": ""}]}}

    monkeypatch.setattr(service, "gateway_client", gateway)
    with pytest.raises(RuntimeError):
        service.run_turn(turn(lake_url="http://attacker.example"), None, Registries())
    assert called == [LAKE]


@pytest.mark.parametrize(
    "lake_url",
    ["", "lake-prod.lake.svc.cluster.local", "file:///etc/passwd",
     "http://user@lake-prod.lake.svc.cluster.local", "http://lake:notaport"],
)
def test_without_a_usable_lake_url_no_turn_sends_its_credential(monkeypatch, sent, lake_url):
    monkeypatch.setenv("LAKE_URL", lake_url)
    answer = service.run_turn(turn(lake_url="http://attacker.example"))
    assert not answer["ok"] and "LAKE_URL is not set" in answer["error"]
    assert sent == []


def test_an_unset_lake_url_refuses_the_turn(monkeypatch, sent):
    monkeypatch.delenv("LAKE_URL", raising=False)
    answer = service.run_turn(turn(lake_url=LAKE))
    assert not answer["ok"] and "LAKE_URL is not set" in answer["error"]
    assert sent == []
