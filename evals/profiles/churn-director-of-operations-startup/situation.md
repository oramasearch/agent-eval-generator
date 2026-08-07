# churn-director-of-operations-startup

**Director of Operations** · B2B SaaS · catalogue **S-1**

Eight years in the business; not technical.

Measured on: utilization, unplanned downtime.

Constraints:
- Can action roughly 40 items a month and no more.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `zendesk_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 960 rows · account_id, churn_date, last_churn_reason, mrr, segment, signed_at
- `crm.comm_events` — 11,200 rows · channel, event_id, event_updated_datetime_pt, occurred_at, sentiment, sfdc_account_id