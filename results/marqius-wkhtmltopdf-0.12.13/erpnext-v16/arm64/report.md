### ERPNext v16 (ERPNext 16.60.0 with Frappe 16.60.2), arm64

Image `frappe/erpnext@sha256:3847babae025dae001e638b7fc5503c944fd968216b3074e60edfcc240fb2db6`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/44932224198.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | ERPNext's image (Debian 13) | 8 of 8 | reference | 11.64 s | reference |
| marqius-wkhtmltopdf 0.12.13 | ERPNext's image (Debian 13) | 8 of 8 | REVIEW: nothing blocking; 1 document to look at | 4.43 s (2.6× the reference) | yes |

**What compare found, document by document:**

- marqius-wkhtmltopdf 0.12.13 on ERPNext's image (Debian 13), delivery-note (review): "Amount Eligible" stands elsewhere: the same words, broken across lines differently
