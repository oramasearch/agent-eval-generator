"""The eval generator loop.

Deliberately thin. The value is not in orchestration cleverness — it is in (a) every tool call
hitting a real node, (b) every run being recorded as a trace, and (c) the generated case being
gradeable by a check that runs. Those three are what make this a bootstrap rather than a demo.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from openai import OpenAI

from agent_eval_generator.tools import ZettaClient, derive_tool_specs, dispatch
from agent_eval_generator.records import package
from agent_eval_generator.synth import synthesize
from agent_eval_generator.validate import validate
from agent_eval_generator.trace import Trace

def _parse(output: str | None) -> dict[str, Any] | None:
    """Pull the JSON object out of the reply. Returns None rather than guessing — a profile we
    cannot parse must not become a half-built artifact."""
    if not output:
        return None
    text = output.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        text = text[start:end + 1]
    try:
        profile = json.loads(text)
    except json.JSONDecodeError:
        return None
    return profile if profile.get("profile_id") and profile.get("tables") else None


PROMPT_VERSION = "v1"
PROMPTS = Path(__file__).parent / "prompts"


# The solutions catalogue, as context rather than as a tool. A profile is INVENTED from an
# industry, not read off a node — and giving the agent `list_datasets` anchored it completely: the
# first three runs under the curiosity prompt all produced coffee subscriptions, because that is
# what happened to be on the node. The agent obeys its tools, not the prose above them.
CATALOGUE = """Band-A solution modules (inspiration, not a menu to copy):
S-1 churn & retention · S-2 lead & opportunity scoring · S-3 customer lifetime value
S-4 collections prioritization · S-5 demand forecasting · S-6 replenishment & inventory action
S-7 KPI anomaly & driver analysis · S-8 predictive maintenance · S-9 automated outbound
S-10 fraud & financial-crime decisioning · S-11 next-best-action · S-12 claims triage"""


def run_once(zetta: ZettaClient, client: OpenAI, model: str, tools: list[Any],
             seen: list[str] | None = None, max_rounds: int = 8, request: str = "") -> Trace:
    """One generation: prompt -> tool calls -> observations -> a case."""
    system = (PROMPTS / f"{PROMPT_VERSION}.md").read_text()
    trace = Trace.start("eval-generator", model, PROMPT_VERSION, "generate one eval case")
    # Tell it what has already been made, so "pick something further away" is actionable rather
    # than aspirational — it cannot avoid repeating itself if it cannot see what it produced.
    avoid = ""
    if seen:
        avoid = ("\n\nAlready generated, so pick something structurally further away than any of "
                 "these:\n" + "\n".join(f"- {entry}" for entry in seen))
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system + "\n\n" + CATALOGUE},
        {"role": "user", "content":
            "Invent one eval profile from scratch. Choose an industry nobody would guess, research "
            "what its systems and tables are really called, and write the situation and schema."
            + avoid
            # A person in lake names what they want (lake#263): their words steer the choice.
            + (f"\n\nThe person asking wants: {request}\nMake the profile about that." if request
               else "")},
    ]

    for _ in range(max_rounds):
        response = client.chat.completions.create(
            model=model, messages=messages, tools=tools
        )
        choice = response.choices[0].message
        messages.append(choice.model_dump(exclude_none=True))

        if not choice.tool_calls:
            trace.output = choice.content
            break

        for call in choice.tool_calls:
            arguments = json.loads(call.function.arguments or "{}")
            try:
                observation = dispatch(zetta, call.function.name, arguments)
                trace.record(call.function.name, arguments, observation)
            except Exception as error:  # noqa: BLE001 - the failure IS the observation
                # A failed call is recorded, not swallowed. An agent that never sees its own
                # failures cannot learn to avoid them, and the trace is training data.
                trace.record(call.function.name, arguments, None, ok=False, error=str(error))
                observation = {"error": str(error)}
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(observation, default=str),
            })
    else:
        trace.output = None
        trace.grade(False, f"did not finish within {max_rounds} rounds")

    return trace


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate eval cases from a live Zetta node.")
    parser.add_argument("--cases", type=int, default=1)
    parser.add_argument("--model", default=os.environ.get("EVAL_GEN_MODEL", "gpt-4o"))
    parser.add_argument("--traces", type=Path, default=Path("traces"))
    args = parser.parse_args()

    zetta = ZettaClient()
    client = OpenAI()
    # Read the tool surface from the node rather than trusting a hand-written table.
    tools = derive_tool_specs(zetta)
    try:
        seen: list[str] = []
        out = Path("evals/profiles")
        for index in range(args.cases):
            trace = run_once(zetta, client, args.model, tools, seen)
            trace.write(args.traces)

            profile = _parse(trace.output)
            if profile is None:
                print(f"[{index + 1}/{args.cases}] no parseable profile — skipped")
                continue
            seen.append(f"{profile.get('profile_id')} ({profile.get('industry')})")

            tables = synthesize(profile)
            directory = package(profile["profile_id"], profile.get("situation", ""), tables, out)
            (directory / "profile.json").write_text(json.dumps(profile, indent=2))
            rows = sum(len(table.rows) for table in tables)

            # Validate BEFORE publishing. Two defects reached the Hub without this — a stale
            # coffee table inside an agricultural profile, and `"sku": "alpha"` — and neither was
            # caught because nothing looked. A generator that cannot check its own output
            # publishes its mistakes at the speed it makes them.
            problems = validate(directory)
            if problems:
                print(f"[{index + 1}/{args.cases}] {profile['profile_id']} REJECTED · "
                      f"{problems[0][:100]}", flush=True)
                continue

            # Upload EACH profile as it finishes. A run that dies at profile 90 should leave 89
            # published, not nothing — one upload at the end is a single failure away from losing
            # the whole batch.
            upload = subprocess.run(
                ["hf", "upload", "OramaSearch/agent-eval-profiles", str(directory),
                 profile["profile_id"], "--repo-type=dataset",
                 f"--commit-message={profile['profile_id']}: {rows} records"],
                capture_output=True, text=True)
            state = "uploaded" if upload.returncode == 0 else f"UPLOAD FAILED {upload.stderr[-120:]}"
            print(f"[{index + 1}/{args.cases}] {profile['profile_id']} · "
                  f"{profile.get('industry')} · {rows:,} records · {state}", flush=True)
    finally:
        zetta.close()
    return 0
