# predictive-maintenance-senior-analyst-large

**Senior Analyst** · equipment rental · catalogue **S-8**

Reports to Finance; writes SQL daily.

Measured on: forecast accuracy, month-end close time.

Constraints:
- Anything shipped must be reproducible by a colleague from the query alone.

## Connections

- `fleet_pg` (postgres) — **captured**
- `telemetry_s3` (s3) — **discovered**

## Tables

- `fleet.assets` — 33,600 rows · acquired_at, asset_id, depot_id, model, year
- `fleet.work_orders` — 244,000 rows · asset_id, closed_at, fault_code, is_breakdown, labour_hours, opened_at, work_order_id