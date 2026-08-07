# agent-eval-generator — Claude rules

**Agent 5** of the Zetta bootstrap scaffold
([zetta#986](https://github.com/oramasearch/zetta/issues/986)). Generates the eval cases the other
four agents are measured against.

**Read [`zetta-bridge/docs/agent-scaffold.md`](../../docs/agent-scaffold.md) first.** It owns the
definitions this repo implements — what a profile is, discovery vs capture, and the five rules that
make this a bootstrap rather than a demo. This file carries only what is specific to *this* agent.

## Why this agent exists, and why it was built first

Hand-written evals inherit the author's blind spots. That is measured, not assumed: twice during
the C++-first attempt an acceptance test written around an already-observed failure passed a model
that was plainly bad — a three-turn walk asserting only that consecutive replies differ passed a
model that answered *"create me a churn project"* with a description and then fabricated
*"`list_models` has over 100 entries"*; a campaign test asserting `best_reward > 0` passed a policy
that had collapsed to zero by step 3. Both were caught by reading outputs, not by the tests.

Without generated evals the other four agents have no honest measure — which is exactly where the
previous attempt failed.

## What it produces

1. A **profile** — a *situation*: who someone is, what they are responsible for, what data they can
   reach, **and the data itself**, materialized as parquet partitions in Zetta.
2. A **task option set** for that profile.
3. A **selection sample** — the case an autosuggest agent is scored on.

**A profile is not a task, an intent, or an RL environment.** Those are later layers. A first
draft that named the traps and pre-decided the correct answers was discarded: every eval built on
it would have been a memory test rather than a reading-the-data test.

## Rules specific to this repo

- **uv, never pip.** `uv sync`, `uv run`, `uv add`.
- **The tool surface is derived from the node's OpenAPI** (`derive_tool_specs`), never
  hand-written. The static table in `tools.py` is a fallback for when no node is reachable. The
  first run failed because a hand-written spec said `name` where the capability required `dataset`.
- **A failed tool call is recorded, not swallowed.** The trace is training data, and an agent that
  never sees its own failures cannot learn to avoid them. It is also how we caught the model
  fabricating a schema after a 400.
- **Describe generated data neutrally.** Awkwardness lives in the data, not the prose. A null rate
  that biases an aggregate is stated as a fact, never flagged as a trap — whether the agent notices
  is what the later layers test.
- **The perturbation test is the quality bar:** change one fact in a profile and the right answer
  must change. If it does not, the case measures recall of the ask rather than reading of the data.
- **`traces/` and `reports/` are committed.** They are the deliverable, not logs.
- **The README states known failures, not only wins.** A README listing intentions as achievements
  is what the model-card rule exists to prevent.

## Prompts are versioned

`src/agent_eval_generator/prompts/vN.md`. **A prompt change is a model change** — a trace records
which version it ran under, and traces from different versions are not comparable.

## Running

```sh
uv sync
export ZETTA_BASE_URL=http://127.0.0.1:4800
export ZETTA_TOKEN=<the owner bearer the node prints once>
export OPENAI_API_KEY=...        # or: source ~/.zshrc
uv run agent-eval-generator --cases 1
```

`--listen` sets the node's **peer** port; the API stays on **4800**. Reads are GET, actions are
POST ([zetta#954](https://github.com/oramasearch/zetta/issues/954)).
