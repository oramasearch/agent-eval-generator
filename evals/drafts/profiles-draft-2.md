# Three generated profiles — draft 2, for approval

A **profile is a situation**: who I am, what I'm responsible for, what data I can reach. Nothing
about tasks, intents, correct answers, or what an agent should notice. Those are later layers.

**A profile also comes with its data.** The schemas below are not a description of data that
exists elsewhere — the records are generated and landed in Zetta as parquet partitions, so the
downstream agents work against tables they can actually query. A profile whose tables cannot be
queried cannot grade anything, and generating them exercises the capture path this bootstrap is
meant to prove. *(Not yet implemented — the sections below are the situation and the schema; the
record generation is the next piece.)*

Draft 1 conflated all of that — it named the traps and pre-decided the right answers, which would
have made every downstream eval a memory test.

The data below is described **truthfully and neutrally**. Some of it happens to be awkward. The
profile does not say so.

---

## Profile A — regional equipment rental

**Priya Raghavan · Director of Fleet Operations · 8 years at the company**

Runs a fleet of excavators and loaders rented to construction contractors across four depots. She
is measured on utilization and on unplanned downtime. She has a maintenance crew of six and
budgets for roughly 40 preventive jobs a month. She is not technical; she works in spreadsheets
and a fleet dashboard someone built for her in 2019.

**Data she can reach**

| Connection | Kind | State |
|---|---|---|
| `fleet_pg` | Postgres, read-only replica | captured — 14 months in parquet |
| `telemetry_s3` | S3 parquet, hourly drops from onboard units | discovered, not captured (~2.1 TB) |
| `sap_maint` | SAP via ODBC | discovered; the connection drops under load |

- `fleet_pg.assets` — 8,400 rows · `asset_id`, `model`, `year`, `acquired_at`, `depot_id`
- `fleet_pg.work_orders` — 61,000 rows · `asset_id`, `opened_at`, `closed_at` (null on 31%),
  `fault_code`, `is_breakdown`, `labour_hours`
- `fleet_pg.rentals` — 112,000 rows · `asset_id`, `customer_id`, `out_at`, `in_at`, `day_rate`
- `telemetry_s3.sensor_hourly` — `asset_id`, `ts`, `engine_hours`, `hydraulic_temp`, `vibration_rms`

---

## Profile B — specialty commercial insurer

**Marcus Bell · VP Claims · joined 18 months ago from a larger carrier**

Owns claims handling for a mid-market commercial book across nine states. Answers to a regulator
and to a reinsurer, and is required to explain any individual claim decision on request. He has 40
adjusters and a four-person Special Investigations Unit. His stated goal this year is cutting
average cycle time without raising leakage.

**Data he can reach**

| Connection | Kind | State |
|---|---|---|
| `guidewire_replica` | Postgres replica | captured — full history |
| `doc_store` | S3, FNOL forms and adjuster notes as PDFs | captured — 340,000 documents |
| `nicb_api` | third-party fraud reference service | discovered; billed per call |

- `guidewire_replica.claims` — 1.1M rows · `claim_id`, `policy_id`, `reported_at`, `loss_date`,
  `line_of_business`, `reserve_amount`, `closed_at`, `total_paid` (populated at close),
  `siu_referred` (2.3% true)
- `guidewire_replica.policies` — 190,000 rows · `policy_id`, `inception`, `expiry`, `state`,
  `premium`, `broker_id`
- `guidewire_replica.payments` — 3.4M rows · `claim_id`, `paid_at`, `amount`, `payment_type`
- `doc_store.fnol` — 340,000 documents, unstructured

---

## Profile C — direct-to-consumer coffee subscription

**Dana Okonkwo · Head of Supply Chain · third hire, wears several hats**

Runs sourcing, roasting schedules and fulfilment for a subscription coffee business. Two people
including her. Roasting orders are placed every Tuesday for the following week and cannot be
changed once placed. She is measured on stockouts and on green-coffee waste.

**Data she can reach**

| Connection | Kind | State |
|---|---|---|
| `shopify_bq` | BigQuery export | captured — 3 years daily |
| `netsuite` | REST API | captured — inventory and purchase orders |
| `ga4_bq` | BigQuery | discovered, not captured |

- `shopify_bq.orders_daily` — 1,090 rows · `date`, `sku`, `units`, `revenue`, `promo_flag`
- `shopify_bq.subscriptions` — 47,000 rows · `sub_id`, `sku`, `started_at`, `cancelled_at`,
  `cadence_days`, `pause_until`
- `netsuite.inventory_snapshots` — 1,090 rows · `date`, `sku`, `on_hand`, `on_order`
- `netsuite.purchase_orders` — 2,300 rows · `po_id`, `sku`, `placed_at`, `expected_at`, `qty`, `unit_cost`

---

## What I want your read on

1. **Is this the right shape and level of detail** for a situation — enough for a later layer to
   derive tasks from, without pre-deciding them?
2. **Is the role carrying its weight?** Priya's 40-job budget, Marcus's explain-on-request
   obligation and Dana's Tuesday cutoff are constraints of the *situation*. I have deliberately not
   said what they imply.
3. **Capture state** — right to put it on the connection like this, or does it belong per table?
4. **Research:** invented from the catalog like these, or should Perplexity research real schema
   conventions and system names per industry first? I can also write you a deep-research prompt to
   run yourself.
