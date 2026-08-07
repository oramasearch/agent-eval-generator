# predictive-maintenance-vp-regulated-line-large

**VP, regulated line** · equipment rental · catalogue **S-8**

Answers to a regulator and a reinsurer.

Measured on: cycle time, leakage.

Constraints:
- Must be able to explain any individual decision on request.
- No decision may be taken without a named human approving that instance.

## Connections

- `fleet_pg` (postgres) — **captured**
- `telemetry_s3` (s3) — **discovered**

## Tables

- `fleet.assets` — 33,600 rows · acquired_at, asset_id, depot_id, model, year
- `fleet.work_orders` — 244,000 rows · asset_id, closed_at, fault_code, is_breakdown, labour_hours, opened_at, work_order_id