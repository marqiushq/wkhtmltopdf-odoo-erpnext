### ERPNext v15 (ERPNext 15.125.0 with Frappe 15.127.1), x86-64

Image `frappe/erpnext@sha256:5ec74e520071583e8108c39ed7004d223881742f83c1a7fc9b9e6bcce08c6117`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/44932224198.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | ERPNext's image (Debian 12) | 8 of 8 | reference | 10.16 s | reference |
| marqius-wkhtmltopdf 0.12.13 | ERPNext's image (Debian 12) | 8 of 8 | GO: nothing blocking and nothing to look at | 3.68 s (2.8× the reference) | yes |
