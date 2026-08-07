# claims-triage-senior-analyst-mid

**Senior Analyst** · specialty insurance · catalogue **S-12**

Reports to Finance; writes SQL daily.

Measured on: forecast accuracy, month-end close time.

Constraints:
- Anything shipped must be reproducible by a colleague from the query alone.

## Connections

- `guidewire_replica` (postgres) — **captured**
- `nicb_api` (rest) — **discovered**

## Tables

- `claims.claims` — 66,000 rows · claim_id, closed_at, line_of_business, loss_date, policy_id, reported_at, reserve_amount, siu_referred, total_paid
- `claims.policies` — 11,400 rows · expiry, inception, policy_id, premium, state