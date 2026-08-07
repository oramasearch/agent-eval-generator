# claims-triage-chief-operating-officer-smb

**Chief Operating Officer** · specialty insurance · catalogue **S-12**

Reads one number a week; delegates the rest.

Measured on: margin, on-time delivery.

Constraints:
- Will only act on something that names the single account or asset to touch.

## Connections

- `guidewire_replica` (postgres) — **captured**
- `nicb_api` (rest) — **discovered**

## Tables

- `claims.claims` — 22,000 rows · claim_id, closed_at, line_of_business, loss_date, policy_id, reported_at, reserve_amount, siu_referred, total_paid
- `claims.policies` — 3,800 rows · expiry, inception, policy_id, premium, state