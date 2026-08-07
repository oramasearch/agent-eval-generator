# multi-source-director-of-operations-smb

**Director of Operations** · B2B SaaS with several systems · catalogue **S-1/S-4/S-11**

Eight years in the business; not technical.

Measured on: utilization, unplanned downtime.

Constraints:
- Can action roughly 40 items a month and no more.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `netsuite_billing` (rest) — **captured**
- `zendesk_pg` (postgres) — **captured**
- `ga4_bq` (bigquery) — **captured**
- `product_kafka` (kafka) — **discovered**
- `hubspot_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 1,800 rows · account_id, churn_date, company_name, mrr, segment, signed_at
- `billing.invoices` — 1,800 rows · amount, billing_customer_id, customer_name, days_late, invoice_id, issued_at, written_off
- `support.tickets` — 9,600 rows · account_id, csat, opened_at, priority, resolved_hours, ticket_id
- `web.sessions` — 24,000 rows · account_id, duration_s, pages, session_id, started_at
- `product.telemetry` — 4,000 rows · account_id, event_id, feature, used_at