# demand-forecasting-director-of-operations-smb

**Director of Operations** · DTC subscription · catalogue **S-5**

Eight years in the business; not technical.

Measured on: utilization, unplanned downtime.

Constraints:
- Can action roughly 40 items a month and no more.

## Connections

- `shopify_bq` (bigquery) — **captured**
- `ga4_bq` (bigquery) — **discovered**

## Tables

- `coffee.subscriptions` — 14,100 rows · cadence_days, cancelled_at, pause_until, sku, started_at, sub_id
- `coffee.orders_daily` — 1,635 rows · date, promo_flag, revenue, sku, units
- `coffee.inventory_snapshots` — 1,635 rows · date, on_hand, on_order, sku