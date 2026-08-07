---
license: other
tags: [eval, agent, profile, synthetic]
---

# agent-eval-profiles

**Evaluation profiles for Orama Studio's agents.** Private. Internal-confidential.

A **profile is a situation plus its data**: who someone is, what they are responsible for, what
data they can reach, and the actual schemas and records. It is a *tool for evaluating models*, not
a fixture for an engine — everything here is scoreable without a running Zetta node.

## What it evaluates

```
profile  ──►  Auto-Suggest model  ──►  a set of candidate TASKS
                                            │
profile + chosen intent  ──►  Project-creation agent  ──►  a Pipeline / Project
```

- **Auto-Suggest** is scored on whether the tasks it proposes are the right set **for that
  situation**. This is why the role and its constraints are part of the profile: the same data has
  different correct answers for a fleet director who can dispatch 40 jobs a month and one who can
  dispatch 400.
- **Project creation** takes the profile plus a chosen intent and is scored on whether the Pipeline
  it builds is correct and production-grade for that data.

## Layout

```
<profile>/situation.md      the person, their responsibilities, their connections
<profile>/schema.json       tables, row counts, columns
<profile>/records/*.jsonl   the actual records
```

## The rule that makes these worth running

**Awkwardness is generated, never annotated.** If subscriptions are paused rather than cancelled,
the records really are like that — the profile does not say so. Whether a model notices is exactly
what is being measured.

The quality bar: **perturb one fact and the correct answer must change.** If it does not, the
profile tests recall of the ask rather than reading of the data.

## Profiles

| Profile | Situation | Structure that matters |
|---|---|---|
| `coffee-subscription` | Dana, Head of Supply Chain, DTC coffee, 2 people, roasting orders lock every Tuesday | Subscriptions largely **determine** daily orders. A model that reads the subscription table predicts most of `orders_daily` from cadence alone; one that forecasts the aggregate produces a backtest a spreadsheet beats. |

## Limitations — read before using

- **One profile so far.** Two more (fleet maintenance, insurance claims triage) are drafted as
  situations but their records are not generated.
- **Nothing has been scored against these yet.** No model has been evaluated, so there is no
  baseline and no evidence the profiles discriminate. Until then this is a dataset, not a benchmark.
- **Synthetic.** The structure is deliberate and the schemas are plausible, but no profile is drawn
  from a real customer's data.
