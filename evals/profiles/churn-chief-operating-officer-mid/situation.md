# churn-chief-operating-officer-mid

**Chief Operating Officer** · B2B SaaS · catalogue **S-1**

Reads one number a week; delegates the rest.

Measured on: margin, on-time delivery.

Constraints:
- Will only act on something that names the single account or asset to touch.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `zendesk_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 12,000 rows · account_id, churn_date, last_churn_reason, mrr, segment, signed_at
- `crm.comm_events` — 140,000 rows · channel, event_id, event_updated_datetime_pt, occurred_at, sentiment, sfdc_account_id