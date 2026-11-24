### ERPNext v15 (ERPNext 15.126.0 with Frappe 15.127.1), x86-64

Image `frappe/erpnext@sha256:5386132243cc562ab52af7b11d152a0596a611fed868dcc54174a9867eab1806`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/45363151857.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | ERPNext's image (Debian 12) | 8 of 8 | reference | 10.2 s | reference |
| marqius-wkhtmltopdf 0.12.15 | ERPNext's image (Debian 12) | 8 of 8 | GO: nothing blocking and nothing to look at | 3.74 s (2.7× the reference) | yes |
