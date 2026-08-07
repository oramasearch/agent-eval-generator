# demand-forecasting-director-of-operations-enterprise

**Director of Operations** · DTC subscription · catalogue **S-5**

Eight years in the business; not technical.

Measured on: utilization, unplanned downtime.

Constraints:
- Can action roughly 40 items a month and no more.

## Connections

- `shopify_bq` (bigquery) — **captured**
- `ga4_bq` (bigquery) — **discovered**

## Tables

- `coffee.subscriptions` — 117,500 rows · cadence_days, cancelled_at, pause_until, sku, started_at, sub_id
- `coffee.orders_daily` — 13,625 rows · date, promo_flag, revenue, sku, units
- `coffee.inventory_snapshots` — 13,625 rows · date, on_hand, on_order, sku