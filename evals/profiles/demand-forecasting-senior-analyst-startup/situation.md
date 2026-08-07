# demand-forecasting-senior-analyst-startup

**Senior Analyst** · DTC subscription · catalogue **S-5**

Reports to Finance; writes SQL daily.

Measured on: forecast accuracy, month-end close time.

Constraints:
- Anything shipped must be reproducible by a colleague from the query alone.

## Connections

- `shopify_bq` (bigquery) — **captured**
- `ga4_bq` (bigquery) — **discovered**

## Tables

- `coffee.subscriptions` — 2,350 rows · cadence_days, cancelled_at, pause_until, sku, started_at, sub_id
- `coffee.orders_daily` — 270 rows · date, promo_flag, revenue, sku, units
- `coffee.inventory_snapshots` — 270 rows · date, on_hand, on_order, sku