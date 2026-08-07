"""The eval generator loop.

Deliberately thin. The value is not in orchestration cleverness — it is in (a) every tool call
hitting a real node, (b) every run being recorded as a trace, and (c) the generated case being
gradeable by a check that runs. Those three are what make this a bootstrap rather than a demo.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from agent_eval_generator.tools import ZettaClient, derive_tool_specs, dispatch
from agent_eval_generator.trace import Trace

PROMPT_VERSION = "v1"
PROMPTS = Path(__file__).parent / "prompts"


def run_once(zetta: ZettaClient, client: OpenAI, model: str, tools: list[Any],
             max_rounds: int = 8) -> Trace:
    """One generation: prompt -> tool calls -> observations -> a case."""
    system = (PROMPTS / f"{PROMPT_VERSION}.md").read_text()
    trace = Trace.start("eval-generator", model, PROMPT_VERSION, "generate one eval case")
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Generate one eval case from this node's real data."},
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
        for index in range(args.cases):
            trace = run_once(zetta, client, args.model, tools)
            path = trace.write(args.traces)
            state = "no output" if trace.output is None else "generated"
            print(f"[{index + 1}/{args.cases}] {state}, {len(trace.calls)} tool calls -> {path}")
    finally:
        zetta.close()
    return 0
