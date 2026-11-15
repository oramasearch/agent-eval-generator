# SPDX-License-Identifier: MIT

"""`POST /v1/turn` requires the service token, compared in constant time, and fails closed (#8)."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from agent_eval_generator import service


def _post(port: int, authorization: str | None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if authorization is not None:
        headers["Authorization"] = authorization
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/turn", data=b"{}", headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.fixture
def server(monkeypatch):
    turns: list[dict] = []
    monkeypatch.setattr(service, "run_turn", lambda turn: turns.append(turn) or {"ok": True})
    servers: list[ThreadingHTTPServer] = []

    def start(token: str) -> int:
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), service.make_handler(token))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        servers.append(httpd)
        return httpd.server_address[1]

    yield start, turns
    for httpd in servers:
        httpd.shutdown()
        httpd.server_close()


def test_the_right_bearer_runs_the_turn(server):
    start, turns = server
    port = start("s3cret")
    assert _post(port, "Bearer s3cret") == (200, {"ok": True})
    assert len(turns) == 1


@pytest.mark.parametrize(
    "authorization", [None, "", "Bearer", "Bearer wrong", "Bearer s3cre", "Bearer s3cretx", "s3cret"]
)
def test_a_wrong_or_missing_bearer_is_refused(server, authorization):
    start, turns = server
    port = start("s3cret")
    status, body = _post(port, authorization)
    assert status == 401 and body == {"ok": False, "error": "unauthorized"}
    assert turns == []


@pytest.mark.parametrize("authorization", [None, "Bearer ", "Bearer anything"])
def test_an_unset_token_refuses_every_turn(server, authorization):
    start, turns = server
    port = start("")
    status, body = _post(port, authorization)
    assert status == 503
    assert "AGENT_SERVICE_TOKEN is not set" in body["error"]
    assert turns == []


def test_the_comparison_is_constant_time(monkeypatch):
    calls: list[tuple[bytes, bytes]] = []
    real = service.hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(service.hmac, "compare_digest", spy)
    assert service.turn_refusal("Bearer s3cret", "s3cret") is None
    assert service.turn_refusal("Bearer nope", "s3cret") == (401, "unauthorized")
    assert calls == [(b"Bearer s3cret", b"Bearer s3cret"), (b"Bearer nope", b"Bearer s3cret")]


def test_a_non_ascii_bearer_is_refused_not_an_error():
    assert service.turn_refusal("Bearer sécret", "s3cret") == (401, "unauthorized")
