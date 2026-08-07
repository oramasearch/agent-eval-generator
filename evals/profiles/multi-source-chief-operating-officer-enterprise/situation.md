# multi-source-chief-operating-officer-enterprise

**Chief Operating Officer** · B2B SaaS with several systems · catalogue **S-1/S-4/S-11**

Reads one number a week; delegates the rest.

Measured on: margin, on-time delivery.

Constraints:
- Will only act on something that names the single account or asset to touch.

## Connections

- `sfdc_pg` (postgres) — **captured**
- `netsuite_billing` (rest) — **captured**
- `zendesk_pg` (postgres) — **captured**
- `ga4_bq` (bigquery) — **captured**
- `product_kafka` (kafka) — **discovered**
- `hubspot_api` (rest) — **discovered**

## Tables

- `crm.accounts` — 22,500 rows · account_id, churn_date, company_name, mrr, segment, signed_at
- `billing.invoices` — 22,500 rows · amount, billing_customer_id, customer_name, days_late, invoice_id, issued_at, written_off
- `support.tickets` — 120,000 rows · account_id, csat, opened_at, priority, resolved_hours, ticket_id
- `web.sessions` — 300,000 rows · account_id, duration_s, pages, session_id, started_at
- `product.telemetry` — 50,000 rows · account_id, event_id, feature, used_at