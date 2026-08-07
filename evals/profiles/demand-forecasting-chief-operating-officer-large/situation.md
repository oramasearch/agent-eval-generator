# demand-forecasting-chief-operating-officer-large

**Chief Operating Officer** · DTC subscription · catalogue **S-5**

Reads one number a week; delegates the rest.

Measured on: margin, on-time delivery.

Constraints:
- Will only act on something that names the single account or asset to touch.

## Connections

- `shopify_bq` (bigquery) — **captured**
- `ga4_bq` (bigquery) — **discovered**

## Tables

- `coffee.subscriptions` — 56,400 rows · cadence_days, cancelled_at, pause_until, sku, started_at, sub_id
- `coffee.orders_daily` — 6,540 rows · date, promo_flag, revenue, sku, units
- `coffee.inventory_snapshots` — 6,540 rows · date, on_hand, on_order, sku