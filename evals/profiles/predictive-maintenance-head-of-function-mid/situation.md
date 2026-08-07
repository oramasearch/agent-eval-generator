# predictive-maintenance-head-of-function-mid

**Head of Function** · equipment rental · catalogue **S-8**

Third hire; two people including them.

Measured on: stockouts, waste.

Constraints:
- Orders are placed weekly on a fixed day and cannot be changed once placed.

## Connections

- `fleet_pg` (postgres) — **captured**
- `telemetry_s3` (s3) — **discovered**

## Tables

- `fleet.assets` — 5,040 rows · acquired_at, asset_id, depot_id, model, year
- `fleet.work_orders` — 36,600 rows · asset_id, closed_at, fault_code, is_breakdown, labour_hours, opened_at, work_order_id