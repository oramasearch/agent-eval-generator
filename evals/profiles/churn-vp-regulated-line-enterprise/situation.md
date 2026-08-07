# churn-vp-regulated-line-enterprise

**VP, regulated line** · B2B SaaS · catalogue **S-1**

Answers to a regulator and a reinsurer.

Measured on: cycle time, leakage.

Constraints:
- Must be able to explain any individual decision on request.
- No decision may be taken without a named human approving that instance.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `zendesk_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 192,000 rows · account_id, churn_date, last_churn_reason, mrr, segment, signed_at
- `crm.comm_events` — 2,240,000 rows · channel, event_id, event_updated_datetime_pt, occurred_at, sentiment, sfdc_account_id