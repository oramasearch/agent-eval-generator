# demand-forecasting-vp-regulated-line-large

**VP, regulated line** · DTC subscription · catalogue **S-5**

Answers to a regulator and a reinsurer.

Measured on: cycle time, leakage.

Constraints:
- Must be able to explain any individual decision on request.
- No decision may be taken without a named human approving that instance.

## Connections

- `shopify_bq` (bigquery) — **captured**
- `ga4_bq` (bigquery) — **discovered**

## Tables

- `coffee.subscriptions` — 188,000 rows · cadence_days, cancelled_at, pause_until, sku, started_at, sub_id
- `coffee.orders_daily` — 16,350 rows · date, promo_flag, revenue, sku, units
- `coffee.inventory_snapshots` — 16,350 rows · date, on_hand, on_order, sku