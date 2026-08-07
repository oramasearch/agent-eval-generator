# claims-triage-head-of-function-enterprise

**Head of Function** · specialty insurance · catalogue **S-12**

Third hire; two people including them.

Measured on: stockouts, waste.

Constraints:
- Orders are placed weekly on a fixed day and cannot be changed once placed.

## Connections

- `guidewire_replica` (postgres) — **captured**
- `nicb_api` (rest) — **discovered**

## Tables

- `claims.claims` — 275,000 rows · claim_id, closed_at, line_of_business, loss_date, policy_id, reported_at, reserve_amount, siu_referred, total_paid
- `claims.policies` — 47,500 rows · expiry, inception, policy_id, premium, state