### ERPNext v15 (ERPNext 15.126.0 with Frappe 15.127.1), x86-64

Image `frappe/erpnext@sha256:ed58a17690a90dc68b07630f98f60800e1fe0f4aec7a65efc4f83f9fd462f6cf`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/45132937753.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | ERPNext's image (Debian 12) | 8 of 8 | reference | 10.21 s | reference |
| marqius-wkhtmltopdf 0.12.13 | ERPNext's image (Debian 12) | 8 of 8 | GO: nothing blocking and nothing to look at | 3.72 s (2.7× the reference) | yes |
