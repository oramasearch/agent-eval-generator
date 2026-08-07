# predictive-maintenance-chief-operating-officer-large

**Chief Operating Officer** · equipment rental · catalogue **S-8**

Reads one number a week; delegates the rest.

Measured on: margin, on-time delivery.

Constraints:
- Will only act on something that names the single account or asset to touch.

## Connections

- `fleet_pg` (postgres) — **captured**
- `telemetry_s3` (s3) — **discovered**

## Tables

- `fleet.assets` — 33,600 rows · acquired_at, asset_id, depot_id, model, year
- `fleet.work_orders` — 244,000 rows · asset_id, closed_at, fault_code, is_breakdown, labour_hours, opened_at, work_order_id