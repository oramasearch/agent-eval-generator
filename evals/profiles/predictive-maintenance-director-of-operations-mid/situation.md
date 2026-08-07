# predictive-maintenance-director-of-operations-mid

**Director of Operations** · equipment rental · catalogue **S-8**

Eight years in the business; not technical.

Measured on: utilization, unplanned downtime.

Constraints:
- Can action roughly 40 items a month and no more.

## Connections

- `fleet_pg` (postgres) — **captured**
- `telemetry_s3` (s3) — **discovered**

## Tables

- `fleet.assets` — 8,400 rows · acquired_at, asset_id, depot_id, model, year
- `fleet.work_orders` — 61,000 rows · asset_id, closed_at, fault_code, is_breakdown, labour_hours, opened_at, work_order_id