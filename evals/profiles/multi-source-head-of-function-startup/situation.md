# multi-source-head-of-function-startup

**Head of Function** · B2B SaaS with several systems · catalogue **S-1/S-4/S-11**

Third hire; two people including them.

Measured on: stockouts, waste.

Constraints:
- Orders are placed weekly on a fixed day and cannot be changed once placed.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `netsuite_billing` (rest) — **captured**
- `zendesk_pg` (postgres) — **captured**
- `ga4_bq` (bigquery) — **captured**
- `product_kafka` (kafka) — **discovered**
- `hubspot_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 720 rows · account_id, churn_date, company_name, mrr, segment, signed_at
- `billing.invoices` — 720 rows · amount, billing_customer_id, customer_name, days_late, invoice_id, issued_at, written_off
- `support.tickets` — 3,840 rows · account_id, csat, opened_at, priority, resolved_hours, ticket_id
- `web.sessions` — 9,600 rows · account_id, duration_s, pages, session_id, started_at
- `product.telemetry` — 1,600 rows · account_id, event_id, feature, used_at