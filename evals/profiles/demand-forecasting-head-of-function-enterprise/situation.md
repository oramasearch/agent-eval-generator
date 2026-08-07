# demand-forecasting-head-of-function-enterprise

**Head of Function** · DTC subscription · catalogue **S-5**

Third hire; two people including them.

Measured on: stockouts, waste.

Constraints:
- Orders are placed weekly on a fixed day and cannot be changed once placed.

## Connections

- `shopify_bq` (bigquery) — **captured**
- `ga4_bq` (bigquery) — **discovered**

## Tables

- `coffee.subscriptions` — 752,000 rows · cadence_days, cancelled_at, pause_until, sku, started_at, sub_id
- `coffee.orders_daily` — 16,350 rows · date, promo_flag, revenue, sku, units
- `coffee.inventory_snapshots` — 16,350 rows · date, on_hand, on_order, sku