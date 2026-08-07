"""Trace recording — the artifact, not logging.

zetta#986 step 2 turns these into SFT and RLVR data, so a run that was not recorded did not
happen. Each trace holds the prompt, every tool call and the observation it returned, the final
output, and the grade — enough to replay the run and to score it later without re-running it.

The grade is deliberately part of the trace. A trace with no grade cannot be used as training data
without someone deciding, after the fact, whether it was good — and that decision is the exact
judgement call the deterministic graders exist to remove.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ToolInvocation:
    tool: str
    arguments: dict[str, Any]
    observation: Any
    ok: bool
    error: str | None = None


@dataclass
class Trace:
    agent: str
    model: str
    prompt_version: str
    task: str
    started_at: str
    calls: list[ToolInvocation] = field(default_factory=list)
    output: Any = None
    graded: bool = False
    passed: bool | None = None
    grade_detail: str = ""

    @classmethod
    def start(cls, agent: str, model: str, prompt_version: str, task: str) -> "Trace":
        return cls(
            agent=agent,
            model=model,
            prompt_version=prompt_version,
            task=task,
            started_at=datetime.now(timezone.utc).isoformat(),
        )

    def record(self, tool: str, arguments: dict[str, Any], observation: Any,
               ok: bool = True, error: str | None = None) -> None:
        self.calls.append(ToolInvocation(tool, arguments, observation, ok, error))

    def grade(self, passed: bool, detail: str) -> None:
        self.graded = True
        self.passed = passed
        self.grade_detail = detail

    def write(self, directory: Path) -> Path:
        """Append to a dated JSONL. One file per day keeps a run reviewable as a diff."""
        directory.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = directory / f"{self.agent}-{day}.jsonl"
        with path.open("a") as handle:
            handle.write(json.dumps(asdict(self)) + "\n")
        return path
