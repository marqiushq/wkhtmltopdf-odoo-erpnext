### ERPNext v16 (ERPNext 16.60.0 with Frappe 16.60.2), x86-64

Image `frappe/erpnext@sha256:a64a155445a39b29cc47071f01bc484d489108785178f5691a55c13e9dd98c83`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/45405829029.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | ERPNext's image (Debian 13) | 8 of 8 | reference | 10.74 s | reference |
| marqius-wkhtmltopdf 0.12.17 | ERPNext's image (Debian 13) | 8 of 8 | REVIEW: nothing blocking; 1 document to look at | 3.86 s (2.8× the reference) | yes |

**What compare found, document by document:**

- marqius-wkhtmltopdf 0.12.17 on ERPNext's image (Debian 13), delivery-note (review): "Amount Eligible" stands elsewhere: the same words, broken across lines differently
