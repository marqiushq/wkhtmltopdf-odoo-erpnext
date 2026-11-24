### ERPNext v15 (ERPNext 15.126.0 with Frappe 15.128.0), arm64

Image `frappe/erpnext@sha256:f1b0ab8cd5c1102503fc91393ff9b90dff1632bedd14f99cd6ff93e3a0fee9e3`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/45405829029.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | ERPNext's image (Debian 12) | 8 of 8 | reference | 11.51 s | reference |
| marqius-wkhtmltopdf 0.12.17 | ERPNext's image (Debian 12) | 8 of 8 | GO: nothing blocking and nothing to look at | 4.83 s (2.4× the reference) | yes |
