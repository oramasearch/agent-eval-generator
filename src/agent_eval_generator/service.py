"""The Eval Generator as a library agent of lake (lake#263): one profile per turn, on request.

In lake a person talks to it (Ask Orama → Talk to, or through Ask Orama): "a realistic test case
for a head of collections at a water utility". One turn is one `run_once`, steered by the request
and fresh methodology and solution snapshots, then synthesized and validated exactly as the
batch CLI does. It answers the profile and its tables; it publishes nothing (the Hugging Face
upload stays the CLI's).

Turns arrive on lake's agent bus (lake_bus.py); `POST /v1/turn` answers the same for a direct call.
Standard library only.
"""

from __future__ import annotations

import hmac
import json
import os
import tempfile
from importlib import metadata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from agent_eval_generator import lake_bus
from agent_eval_generator.agent import PROMPT_VERSION, _parse, run_once
from agent_eval_generator.limits import ProfileRejected, check_profile
from agent_eval_generator.methodologies import apply_snapshot, snapshot_for_turn
from agent_eval_generator.model import gateway_client
from agent_eval_generator.records import package
from agent_eval_generator.solutions import (
    apply_solution,
    snapshot_for_turn as solution_snapshot_for_turn,
)
from agent_eval_generator.synth import synthesize
from agent_eval_generator.tools import LakeWorkspaceClient
from agent_eval_generator.validate import validate

SAMPLE_ROWS = 5


def health() -> dict[str, Any]:
    """`GET /healthz`: the agent, its prompt version and the installed package's version."""
    try:
        version = metadata.version("agent-eval-generator")
    except metadata.PackageNotFoundError:
        version = "unknown"
    return {
        "ok": True,
        "agent": "agent-eval-generator",
        "version": version,
        "prompt_version": PROMPT_VERSION,
    }


def lakes_url() -> str:
    """Lake's address from this service's environment (`LAKE_URL`), the only place a turn's
    credential is ever sent; empty when unset or not an absolute http(s) URL without user info."""
    lake = os.environ.get("LAKE_URL", "").strip().rstrip("/")
    try:
        parts = urlsplit(lake)
        parts.port  # noqa: B018 (raises on a malformed port)
    except ValueError:
        return ""
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname or "@" in parts.netloc:
        return ""
    return lake


def registry_source(turn: dict[str, Any], injected: Any = None) -> Any:
    """Use an injected engine client or the lake credential attached to this turn, sent only to
    this service's `LAKE_URL`; a turn's own `lake_url` is never used (agent-eval-generator#13)."""
    if injected is not None:
        return injected
    lake_url = lakes_url()
    lake_token = turn.get("lake_token")
    customer_id = turn.get("customer_id")
    if lake_url and lake_token and customer_id:
        return LakeWorkspaceClient(lake_url, lake_token, customer_id)
    return None


def first_sentence(situation: str) -> str:
    """The situation's first line of prose, not a markdown heading, cut at a sentence."""
    for line in situation.splitlines():
        text = line.strip().lstrip("-*> ").strip()
        if text and not text.startswith("#"):
            end = text.find(". ")
            return (text if end < 0 else text[: end + 1])[:400]
    return ""


def run_turn(
    turn: dict[str, Any],
    client: Any = None,
    zetta: Any = None,
    model: str | None = None,
    trace_dir: Path | None = None,
) -> dict[str, Any]:
    """One eval profile for one request. A failure is an answer, never raised."""
    request = (turn.get("request") or turn.get("message") or "").strip()
    model = model or os.environ.get(
        "EVAL_GEN_MODEL", os.environ.get("AGENT_MODEL", "gpt-4o")
    )
    if (zetta is None or client is None) and not lakes_url():
        # The turn's credential goes only to Lake at this service's own LAKE_URL, never to an
        # address the request names (agent-eval-generator#13).
        return {"ok": False, "error": "LAKE_URL is not set: this agent sends a turn's "
                                      "credential only to Lake's configured address"}
    source = registry_source(turn, zetta)
    # No model workspace tools: a test case invents its own systems and tables. The generator
    # reads the current registries before asking the model instead.
    try:
        snapshot = snapshot_for_turn(turn, source)
    except Exception as error:  # a registry failure is an answer, not a dead worker
        return {"ok": False, "error": f"methodology registry: {error}"}
    try:
        solution_snapshot = solution_snapshot_for_turn(source)
    except Exception as error:
        return {"ok": False, "error": f"solution registry: {error}"}
    if not solution_snapshot.deployed or not solution_snapshot.solutions:
        return {
            "ok": False,
            "error": (
                "solution registry: not deployed yet; no solutions are available"
            ),
        }
    if client is None:
        # The model is reached through lake with the turn's own key, which counts its tokens in
        # the turn's workspace (lake#248); this agent holds no provider key. The address is this
        # service's LAKE_URL; the turn's own `lake_url` is never used, so the key cannot be sent
        # to a host the caller names (agent-eval-generator#13).
        model_key = turn.get("lake_token") or ""
        if not model_key:
            return {"ok": False, "error": "a turn needs its lake_token to reach the model "
                                          "through lake"}
        client = gateway_client(lakes_url(), model_key)
    trace = run_once(
        source,
        client,
        model,
        [],
        request=request,
        methodologies=snapshot.methodologies,
        legacy_fallback=snapshot.legacy_fallback,
        solutions=solution_snapshot.solutions,
    )
    profile = _parse(trace.output)
    if profile is None:
        trace.write(
            trace_dir
            or Path(os.environ.get("TRACE_DIR", "/tmp/agent-eval-generator-traces"))
        )
        return {"ok": False, "error": "no eval profile came back from the model"}
    # The model's names become file names and its table and column counts decide memory: both
    # are checked before anything is written or synthesized (agent-eval-generator#21, #22).
    try:
        check_profile(profile)
    except ProfileRejected as error:
        trace.grade(False, str(error))
        trace.write(
            trace_dir
            or Path(os.environ.get("TRACE_DIR", "/tmp/agent-eval-generator-traces"))
        )
        return {"ok": False, "error": f"invalid profile: {error}"}
    try:
        apply_snapshot(profile, snapshot)
        selected_solution = apply_solution(profile, solution_snapshot, source)
    except Exception as error:
        trace.grade(False, str(error))
        trace.write(
            trace_dir
            or Path(os.environ.get("TRACE_DIR", "/tmp/agent-eval-generator-traces"))
        )
        return {"ok": False, "error": f"invalid profile registry selection: {error}"}
    trace.output = json.dumps(profile)
    trace.write(
        trace_dir
        or Path(os.environ.get("TRACE_DIR", "/tmp/agent-eval-generator-traces"))
    )
    tables = synthesize(profile)
    with tempfile.TemporaryDirectory() as out:
        directory = package(
            profile["profile_id"],
            profile.get("situation", ""),
            tables,
            Path(out),
        )
        (directory / "profile.json").write_text(json.dumps(profile, indent=2))
        problems = validate(directory)
    records = sum(len(table.rows) for table in tables)
    summary = [
        {
            "table": f"{table.database}.{table.name}",
            "rows": len(table.rows),
            "columns": sorted(table.rows[0]) if table.rows else [],
            "sample": table.rows[:SAMPLE_ROWS],
        }
        for table in tables
    ]
    persona = profile.get("persona")
    who = persona.get("role") if isinstance(persona, dict) else persona
    reply = (
        f"I wrote an eval profile, **{profile.get('profile_id')}**: "
        f"{profile.get('industry') or 'an industry'}"
        + (f", for {who}" if who else "")
        + ". "
        + first_sentence(profile.get("situation") or "")
        + f"\n\nIt has {len(tables)} table(s) and {records:,} records: "
        + ", ".join(f"`{item['table']}` ({item['rows']:,})" for item in summary)
        + "."
    )
    if problems:
        reply += (
            f"\n\nIt does not pass validation yet ({len(problems)} problem(s)), so it is not "
            "a usable test case: " + problems[0][:200]
        )
    if not profile["runnable"]:
        reply += (
            f"\n\nI declined this profile for scoring: {selected_solution['name']} "
            f"({selected_solution['id']}) at level {profile['level']} is not supported "
            f"yet: {profile['issue']}."
        )
    elif snapshot.legacy_fallback:
        reply += "\n\nThis workspace predates the methodology registry, so only M-1 is assumed to run."
    return {
        "ok": True,
        "reply": reply,
        "result": {
            "kind": "eval_profile",
            "profile": profile,
            "tables": summary,
            "problems": problems,
            "prompt_version": PROMPT_VERSION,
            "scoreable": profile["runnable"],
        },
    }


def turn_refusal(authorization: str | None, token: str) -> tuple[int, str] | None:
    """Why `POST /v1/turn` is refused, as `(status, error)`, or None when the caller may proceed.

    The route fails closed: with `AGENT_SERVICE_TOKEN` unset or empty every turn is refused, so a
    service started without it is never open. The bearer is compared in constant time
    (`hmac.compare_digest` over bytes), so the comparison's timing says nothing about the token.
    """
    if not token:
        return 503, "AGENT_SERVICE_TOKEN is not set; this service refuses every turn"
    expected = f"Bearer {token}".encode()
    supplied = (authorization or "").encode("utf-8", "surrogateescape")
    if not hmac.compare_digest(supplied, expected):
        return 401, "unauthorized"
    return None


def make_handler(token: str) -> type[BaseHTTPRequestHandler]:
    """The HTTP handler for `GET /healthz` and `POST /v1/turn`, requiring `token` as the bearer."""

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: dict[str, Any]) -> None:
            payload = json.dumps(body, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 (the stdlib's name)
            if self.path == "/healthz":
                self._send(200, health())
                return
            self._send(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/turn":
                self._send(404, {"ok": False, "error": "not found"})
                return
            refusal = turn_refusal(self.headers.get("Authorization"), token)
            if refusal is not None:
                status, error = refusal
                self._send(status, {"ok": False, "error": error})
                return
            try:
                turn = json.loads(
                    self.rfile.read(int(self.headers.get("Content-Length", "0")))
                )
            except (json.JSONDecodeError, ValueError):
                self._send(400, {"ok": False, "error": "the body is not JSON"})
                return
            try:
                answer = run_turn(turn if isinstance(turn, dict) else {})
            except Exception as error:  # a failed turn is an answer, not a dead worker
                answer = {"ok": False, "error": f"{type(error).__name__}: {error}"}
            self._send(200 if answer.get("ok") else 422, answer)

        def log_message(self, format: str, *args: Any) -> None:
            print(
                json.dumps({"agent": "agent-eval-generator", "request": format % args}),
                flush=True,
            )

    return Handler


def serve() -> int:
    token = os.environ.get("AGENT_SERVICE_TOKEN", "")
    if not token:
        print(
            json.dumps(
                {
                    "agent": "agent-eval-generator",
                    "warning": "AGENT_SERVICE_TOKEN is not set; POST /v1/turn refuses every turn",
                }
            ),
            flush=True,
        )
    port = int(os.environ.get("PORT", "8080"))
    print(json.dumps({"agent": "agent-eval-generator", "listening": port}), flush=True)
    lake_bus.start_from_env(run_turn, "agent-eval-generator")
    ThreadingHTTPServer(("0.0.0.0", port), make_handler(token)).serve_forever()
    return 0
