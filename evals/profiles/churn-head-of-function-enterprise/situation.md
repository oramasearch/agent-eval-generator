# churn-head-of-function-enterprise

**Head of Function** · B2B SaaS · catalogue **S-1**

Third hire; two people including them.

Measured on: stockouts, waste.

Constraints:
- Orders are placed weekly on a fixed day and cannot be changed once placed.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `zendesk_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 192,000 rows · account_id, churn_date, last_churn_reason, mrr, segment, signed_at
- `crm.comm_events` — 2,240,000 rows · channel, event_id, event_updated_datetime_pt, occurred_at, sentiment, sfdc_account_id