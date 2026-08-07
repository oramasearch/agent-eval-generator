# multi-source-vp-regulated-line-enterprise

**VP, regulated line** · B2B SaaS with several systems · catalogue **S-1/S-4/S-11**

Answers to a regulator and a reinsurer.

Measured on: cycle time, leakage.

Constraints:
- Must be able to explain any individual decision on request.
- No decision may be taken without a named human approving that instance.

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