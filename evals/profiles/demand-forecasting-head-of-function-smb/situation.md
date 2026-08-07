# demand-forecasting-head-of-function-smb

**Head of Function** · DTC subscription · catalogue **S-5**

Third hire; two people including them.

Measured on: stockouts, waste.

Constraints:
- Orders are placed weekly on a fixed day and cannot be changed once placed.

## Connections

- `shopify_bq` (bigquery) — **captured**
- `ga4_bq` (bigquery) — **discovered**

## Tables

- `coffee.subscriptions` — 9,400 rows · cadence_days, cancelled_at, pause_until, sku, started_at, sub_id
- `coffee.orders_daily` — 1,090 rows · date, promo_flag, revenue, sku, units
- `coffee.inventory_snapshots` — 1,090 rows · date, on_hand, on_order, sku