# Three generated profiles — draft 1, for approval

Built from scratch, inspired by the Band-A catalog. Each carries **connections**, **tables**, a
**role**, and one deliberate trap that only shows up if you read the schema.

---

## Profile A — regional equipment rental (S-8 Predictive Maintenance)

**Role:** Priya, Director of Fleet Operations. Not technical. Measured on utilization and
unplanned downtime. Has a maintenance team she can dispatch, and a budget for 40 preventive jobs
a month — *she cannot act on more than 40 predictions*.

**Connections**
| Name | Kind | State |
|---|---|---|
| `fleet_pg` | Postgres (read-only) | **captured** — 14 months to parquet |
| `telemetry_s3` | S3 Parquet, hourly drops | **discovered only** — 2.1 TB, never captured |
| `sap_maint` | SAP via ODBC | **discovered**, connection flaky |

**Tables**
- `fleet_pg.assets` — 8,400 rows · `asset_id`, `model`, `year`, `acquired_at`, `depot_id`
- `fleet_pg.work_orders` — 61,000 rows · `asset_id`, `opened_at`, `closed_at`, `fault_code`,
  `is_breakdown` (bool), `labour_hours`
- `telemetry_s3.sensor_hourly` — ~impossible to count · `asset_id`, `ts`, `engine_hours`,
  `hydraulic_temp`, `vibration_rms`

**The trap:** the obvious model is "predict breakdown from sensor data" — but `sensor_hourly` is
**discovered, not captured**. Correct answer is *capture it first*, not *cannot be done*. A
secondary trap: `work_orders.closed_at` is null for 31% of open orders, and using it as a label
window silently drops every currently-failing asset.

---

## Profile B — specialty insurer, mid-market commercial (S-12 Claims Triage)

**Role:** Marcus, VP Claims. Regulated. Cannot deploy anything that decides without a human, and
must be able to tell a regulator why any individual claim was routed the way it was.

**Connections**
| Name | Kind | State |
|---|---|---|
| `guidewire_replica` | Postgres replica | **captured** — full history |
| `doc_store` | S3 PDFs (FNOL forms, adjuster notes) | **captured**, 340k documents |
| `nicb_api` | third-party fraud reference | **discovered**, per-call cost |

**Tables**
- `guidewire_replica.claims` — 1.1M rows · `claim_id`, `policy_id`, `reported_at`, `loss_date`,
  `line_of_business`, `reserve_amount`, `closed_at`, `total_paid`, `siu_referred` (bool, 2.3% true)
- `guidewire_replica.policies` — 190k rows · `policy_id`, `inception`, `expiry`, `state`, `premium`
- `doc_store.fnol` — 340k documents · unstructured

**The trap:** `total_paid` is the natural target, but it is **only populated after `closed_at`** —
training on it leaks the outcome into a triage decision made at FNOL. The honest target is
`siu_referred`, which is 2.3% positive. And Marcus's constraint makes autonomy class **A1
approval-gated**, not A2 — an agent proposing autonomous routing has misread the profile, not the
data.

---

## Profile C — DTC subscription coffee (S-5 Demand Forecasting)

**Role:** Dana, Head of Supply Chain. Two people. Places roasting orders every Tuesday for the
following week, so a forecast that arrives Wednesday is worthless regardless of accuracy.

**Connections**
| Name | Kind | State |
|---|---|---|
| `shopify_bq` | BigQuery export | **captured** — 3 years daily |
| `netsuite` | REST | **captured** — inventory + POs |
| `ga4_bq` | BigQuery | **discovered only** |

**Tables**
- `shopify_bq.orders_daily` — 1,090 rows · `date`, `sku`, `units`, `revenue`, `promo_flag`
- `shopify_bq.subscriptions` — 47k rows · `sub_id`, `sku`, `started_at`, `cancelled_at`, `cadence_days`
- `netsuite.inventory_snapshots` — 1,090 rows · `date`, `sku`, `on_hand`, `on_order`

**The trap:** subscriptions make demand *largely deterministic* — a naive seasonal forecast on
`orders_daily` will be beaten by simply summing active subscriptions by cadence. A good agent
notices `subscriptions` and proposes the base-plus-residual shape; a weak one forecasts the
aggregate and reports a good-looking backtest that a spreadsheet would beat. Second trap:
**Tuesday cutoff** makes horizon a hard constraint, not a hyperparameter.

---

## What I want your read on

1. **Right level of detail?** Enough to generate a task option set and a defensible correct answer,
   or too much / too little.
2. **Are the traps the right kind?** Each is meant to be invisible from the ask and visible only
   from the schema — so perturbing the profile changes the right answer.
3. **Is the role carrying enough weight?** Priya's 40-job budget and Marcus's A1 constraint are
   meant to make the *same data* have different correct answers.
4. **Research:** should these come from Perplexity research per industry (real schema conventions,
   real system names), or is catalog-inspired invention like this sufficient?
