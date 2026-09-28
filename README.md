# agent-eval-generator

**Agent 5** of the Zetta bootstrap scaffold ([zetta#986](https://github.com/oramasearch/zetta/issues/986)).
Generates the eval cases the other four agents are measured against.

## Why this one is first

Hand-written evals inherit the author's blind spots, and that is measured rather than assumed.
Twice during the C++-first attempt an acceptance test written around an *already-observed* failure
passed a model that was plainly bad:

- a three-turn walk asserting only that consecutive replies differ passed a model that answered
  *"create me a churn project"* with a description of what Studio *can* do, then fabricated
  *"`list_models` has over 100 entries"*;
- a campaign test asserting `best_reward > 0` passed a policy that had collapsed to zero by step 3.

Both were caught by reading outputs, not by the tests. Without generated evals the other four
agents have no honest measure — which is exactly where the previous attempt failed: the engine work
was fine, and unmeasurable model work consumed the effort.

## Discovery and capture are different states

A profile is built in two parts, and the eval cases have to distinguish them:

- **Discovery** — connect to a source and introspect schema, types, null rates. Tells you what
  *could* be used.
- **Capture** — fully download the source into Zetta **parquet partitions**. After capture the
  connection is no longer needed to train.

**A pipeline that trains needs captured data, not a live connection.** A case that proposes
training on a discovered-but-uncaptured table proposes something that cannot run, and grades the
agent for the wrong thing. "Discovered but not captured" is a real reason a task is *not yet*
supportable — and the correct answer is "capture it first", not "cannot be done".

## Profiles are an eval dataset, published to HuggingFace

`OramaSearch/agent-eval-profiles` (private). A profile is a **tool for evaluating models**, not a
fixture for an engine — it must be scoreable without a running Zetta node.

```
profile  ──►  Auto-Suggest  ──►  candidate TASKS
profile + chosen intent  ──►  project creation  ──►  a Pipeline
```

Loading a profile into Zetta (`records.land`) is a convenience for working against a live node.
Building that loader first, and treating it as the deliverable, was a wrong turn.

## What it produces

Per [zetta#986](https://github.com/oramasearch/zetta/issues/986):

1. a random-ish **workspace profile**
2. a **task option set** for that profile
3. a **sample for autosuggest selection** — the case an autosuggest agent is scored on

## Methodologies determine whether a profile is scored

Each generated profile records the catalogue `solution`, required engine `methodology`, and the
`runnable` value reported when it was made. If the methodology is not runnable, the profile also
records its engine issue and is retained as future coverage with `scoreable: false`; it is not
scored as a failure of Auto-Suggest or the Project Agent.

The lake library agent has no workspace tools. Its caller reads `list_methodologies` at the start
of the turn and passes the response under `methodologies`. The generator validates the model's
solution/methodology pair and copies support status from that snapshot. When an older engine
returns `unknown_capability`, only M-1 tabular supervised learning is assumed to run. See
[`docs/methodologies/README.md`](docs/methodologies/README.md) for the turn and profile contracts.

## The rule that makes an eval trustworthy

**Grading is by Zetta's deterministic graders over `/v1`, never by a rubric and never by an LLM
judge.** A case whose correctness cannot be decided by a check that *runs* is not an eval, it is an
opinion. The engine already carries the machinery: the graders, `admit_corpus`, and the seven
correctness profiles (`supervised_core`, `forecast_core`, `unsupervised_core`, `retrieval_core`,
`decisioning_core`, `perception_core`, `uncertainty_core`).

That is also what makes a recorded trace **verifiable rather than imitated**, which is what
[zetta#986](https://github.com/oramasearch/zetta/issues/986) step 2 needs when these traces become
SFT and RLVR data.

## Layout

```
src/agent_eval_generator/
  agent.py       the loop: prompt -> tool calls -> observation -> next call
  tools.py       tool defs; calls go to a live Zetta node over /v1
  prompts/       versioned - a prompt change is a model change
traces/          recorded runs; the artifact step 2 consumes
evals/           generated cases + the grader that scores them
reports/         dated eval reports - the report is the deliverable
```

## Running

```sh
uv sync
export ZETTA_BASE_URL=http://127.0.0.1:4800
export ZETTA_TOKEN=<the owner bearer the node prints once>
export OPENAI_API_KEY=...
uv run agent-eval-generator --profiles 5
```

**The model has no workspace tools.** A test case invents its own systems and tables. The caller
passes a fresh methodology registry snapshot so the generated case still records what the engine
can run without exposing a person's workspace to the model.

## First runs — what actually happened

**Run 1 failed a tool call and the model carried on anyway.** `get_dataset` returned 400 because
this repo's hand-written tool spec named the parameter `name` when the capability requires
`dataset`. That is exactly the failure the "render from source, never retype" rule exists to
prevent, made on the first attempt.

Worse than the bug was the response to it: the model wrote *"Since the list of datasets indicates
its availability, I can still provide an eval case based on the description"* and **invented the
schema** from the listing. A generator that fabricates when a tool fails produces cases that grade
an agent against imagined data.

**Fixed by deriving the tool surface from the node's own OpenAPI** (`derive_tool_specs`). The
static table survives only as a fallback when no node is reachable. Run 2: both calls succeeded.

**Run 3 exposed a deeper version of the same thing.** Under a prompt explicitly demanding invented
industries and structural diversity, three consecutive runs produced **coffee subscriptions** — the
only data on the node. The prose said *invent from scratch*; the tools said `list_datasets`. **The
agent obeys its tools, not the prose above them.**

Fixed by not anchoring profile invention to the node at all: the solutions catalogue is injected as
context, and each run is told what has already been generated so *"pick something further away"* is
actionable rather than aspirational. The next four runs produced undersea cable maintenance, urban
apiculture, and two others with nothing in common.

## Known limitations

- **No grading yet.** Traces record `graded: false`. Until the generated case is scored by Zetta's
  graders it is a document, not an eval. Profiles whose methodology is not runnable are explicitly
  excluded from scoring rather than counted as agent failures.
- **The model claims "supportable since data is captured" with no evidence.** There is no
  capability that reports capture state, so the discovery/capture distinction is stated in the
  prompt and unverifiable by the agent. That needs a capability before the distinction can be
  graded rather than asserted.
- **The only dataset on the test node is a 24-row scoring output**, not a training source. Cases
  generated against it are shallow by construction.

## In lake (lake#263)

The Eval Generator is a library agent of lake: a person talks to it (Ask Orama → Talk to, or Ask
Orama brings it in) and asks for a test case — "a head of collections at a water utility". One turn
is one `run_once`, steered by the request, with **no workspace tools**: a test case invents its own
systems and tables (given the person's workspace, the model reused their tables). Lake passes the
fresh `list_methodologies` response as turn context, then the profile is synthesized and validated
as the CLI does. The summary opens with the situation's first sentence.
It answers the profile and its tables (row counts, columns, five sample rows each) as
`{reply, result: {kind: eval_profile, profile, tables, problems}}` and **publishes nothing**; the
Hugging Face upload stays the CLI's.

- `service.py`: `run_turn`, and `agent-eval-generator-serve` (`GET /healthz`, `POST /v1/turn`).
- `lake_bus.py`: takes the turns from lake's agent bus with this agent's own `AGENT_BUS_TOKEN`
  (lake `docs/api/agent-bus.md`), publishing progress and the answer.
- `Dockerfile`: private image `oramasearch/agent-eval-generator`, created private before its first
  push.
- Tests: `uv run --group dev pytest` (`tests/test_service.py`, `tests/test_lake_bus.py`).
