# churn-head-of-function-smb

**Head of Function** · B2B SaaS · catalogue **S-1**

Third hire; two people including them.

Measured on: stockouts, waste.

Constraints:
- Orders are placed weekly on a fixed day and cannot be changed once placed.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `zendesk_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 3,600 rows · account_id, churn_date, last_churn_reason, mrr, segment, signed_at
- `crm.comm_events` — 42,000 rows · channel, event_id, event_updated_datetime_pt, occurred_at, sentiment, sfdc_account_id