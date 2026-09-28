"""The Eval Generator as a library agent of lake (lake#263): one profile per turn, on request.

In lake a person talks to it (Ask Orama → Talk to, or through Ask Orama): "a realistic test case
for a head of collections at a water utility". One turn is one `run_once`, steered by the request
and the caller's methodology snapshot, then synthesized and validated exactly as the batch CLI
does. It answers the profile and its tables; it publishes nothing (the Hugging Face upload stays
the CLI's).

Turns arrive on lake's agent bus (lake_bus.py); `POST /v1/turn` answers the same for a direct call.
Standard library only.
"""

from __future__ import annotations

import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from openai import OpenAI

from agent_eval_generator import lake_bus
from agent_eval_generator.agent import PROMPT_VERSION, _parse, run_once
from agent_eval_generator.methodologies import apply_snapshot, snapshot_for_turn
from agent_eval_generator.records import package
from agent_eval_generator.synth import synthesize
from agent_eval_generator.validate import validate

SAMPLE_ROWS = 5


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
    # No model workspace tools: a test case invents its own systems and tables. Lake passes the
    # current methodology registry as turn context instead.
    try:
        snapshot = snapshot_for_turn(turn, zetta)
    except Exception as error:  # a registry failure is an answer, not a dead worker
        return {"ok": False, "error": f"methodology registry: {error}"}
    trace = run_once(
        zetta,
        client or OpenAI(),
        model,
        [],
        request=request,
        methodologies=snapshot.methodologies,
        legacy_fallback=snapshot.legacy_fallback,
    )
    profile = _parse(trace.output)
    if profile is None:
        trace.write(
            trace_dir
            or Path(os.environ.get("TRACE_DIR", "/tmp/agent-eval-generator-traces"))
        )
        return {"ok": False, "error": "no eval profile came back from the model"}
    try:
        selected = apply_snapshot(profile, snapshot)
    except ValueError as error:
        trace.grade(False, str(error))
        trace.write(
            trace_dir
            or Path(os.environ.get("TRACE_DIR", "/tmp/agent-eval-generator-traces"))
        )
        return {"ok": False, "error": f"invalid profile methodology: {error}"}
    trace.output = json.dumps(profile)
    trace.write(
        trace_dir
        or Path(os.environ.get("TRACE_DIR", "/tmp/agent-eval-generator-traces"))
    )
    tables = synthesize(profile)
    with tempfile.TemporaryDirectory() as out:
        directory = package(
            profile.get("profile_id", "profile"),
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
            f"\n\nI declined this profile for scoring: {selected['name']} "
            f"({selected['id']}) is not supported yet: {profile['issue']}."
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


def serve() -> int:
    token = os.environ.get("AGENT_SERVICE_TOKEN", "")

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
                self._send(
                    200,
                    {
                        "ok": True,
                        "agent": "agent-eval-generator",
                        "prompt_version": PROMPT_VERSION,
                    },
                )
                return
            self._send(404, {"ok": False, "error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/turn":
                self._send(404, {"ok": False, "error": "not found"})
                return
            if token and self.headers.get("Authorization") != f"Bearer {token}":
                self._send(401, {"ok": False, "error": "unauthorized"})
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

    port = int(os.environ.get("PORT", "8080"))
    print(json.dumps({"agent": "agent-eval-generator", "listening": port}), flush=True)
    lake_bus.start_from_env(run_turn, "agent-eval-generator")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
    return 0
