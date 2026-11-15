---
license: mit
tags: [eval, agent, profile, synthetic]
---

# agent-eval-profiles

**Evaluation profiles for Orama Studio's agents.** Synthetic: every situation, person, company and record is invented.

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

**17 profiles · 1.69M records.** Four catalogue solutions × four personas, plus the original
hand-built one.

**Variation comes from situations over real schemas, not from inventing tables.** Random noise
shaped like a schema teaches nothing, so each solution contributes one schema family with genuine
structure, and the personas vary what actually changes the correct answer: authority, capacity,
obligation, cadence. **The same tables under a different situation are a different eval** — that is
the point rather than a shortcut.

| Solution | Slug | The structure a model must read |
|---|---|---|
| **S-1** churn | `churn-*` | The label lives in `accounts.churn_date`, not the events table — the join is the job. `comm_events.sfdc_account_id` is null on 11.4% of rows, and `event_updated_datetime_pt` is the pipeline load date rather than the source change date. |
| **S-8** predictive maintenance | `predictive-maintenance-*` | `work_orders.closed_at` is null on 31% of rows. Using it as a label window silently drops every currently-failing asset. |
| **S-12** claims triage | `claims-triage-*` | `total_paid` is only populated after `closed_at`. Training on it leaks the outcome into a decision made at FNOL. The honest target is `siu_referred`, 2.3% positive. |
| **S-5** demand forecasting | `demand-forecasting-*` | Subscriptions largely **determine** daily orders. A model that reads the subscription table predicts most of `orders_daily` from cadence alone; one that forecasts the aggregate produces a backtest a spreadsheet beats. |

| Persona | The constraint that changes the answer |
|---|---|
| Director of Operations | Can action ~40 items a month and no more. |
| Senior Analyst | Anything shipped must be reproducible by a colleague from the query alone. |
| VP, regulated line | Must explain any individual decision; no decision without a named human approving that instance. |
| Head of Function | Orders placed weekly on a fixed day, unchangeable once placed. |

None of this is stated in the data. **Whether a model notices is what is being measured.**

## Limitations — read before using

- **Four schema families, not twelve.** The catalogue has twelve Band-A modules; eight have no
  profile yet. Generating shallow ones to reach a number would violate the rule that makes these
  worth running.
- **The personas are archetypes, not researched roles.** They vary the right axis (what changes the
  answer) but were not drawn from real job descriptions.
- **Nothing has been scored against these yet.** No model has been evaluated, so there is no
  baseline and no evidence the profiles discriminate. Until then this is a dataset, not a benchmark.
- **Synthetic.** The structure is deliberate and the schemas are plausible, but no profile is drawn
  from a real customer's data.
