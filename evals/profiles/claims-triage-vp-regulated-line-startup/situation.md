# claims-triage-vp-regulated-line-startup

**VP, regulated line** · specialty insurance · catalogue **S-12**

Answers to a regulator and a reinsurer.

Measured on: cycle time, leakage.

Constraints:
- Must be able to explain any individual decision on request.
- No decision may be taken without a named human approving that instance.

## Connections

- `guidewire_replica` (postgres) — **captured**
- `nicb_api` (rest) — **discovered**

## Tables

- `claims.claims` — 5,500 rows · claim_id, closed_at, line_of_business, loss_date, policy_id, reported_at, reserve_amount, siu_referred, total_paid
- `claims.policies` — 950 rows · expiry, inception, policy_id, premium, state