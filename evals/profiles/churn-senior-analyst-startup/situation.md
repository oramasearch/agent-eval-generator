# churn-senior-analyst-startup

**Senior Analyst** · B2B SaaS · catalogue **S-1**

Reports to Finance; writes SQL daily.

Measured on: forecast accuracy, month-end close time.

Constraints:
- Anything shipped must be reproducible by a colleague from the query alone.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `zendesk_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 960 rows · account_id, churn_date, last_churn_reason, mrr, segment, signed_at
- `crm.comm_events` — 11,200 rows · channel, event_id, event_updated_datetime_pt, occurred_at, sentiment, sfdc_account_id