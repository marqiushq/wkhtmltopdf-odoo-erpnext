### Odoo 18.0 (18.0.20261112), x86-64

Image `odoo@sha256:0bd79cf07f59105c5697667c2241b86447e99c6adb036200df0e4e295785bdf3`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/44932224198.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | Odoo's image (Ubuntu 24.04) | 13 of 13 | reference | 50.38 s | reference |
| marqius-wkhtmltopdf 0.12.13 | Odoo's image (Ubuntu 24.04) | 13 of 13 | GO: nothing blocking and nothing to look at | 4.66 s (10.8× the reference) | yes |
| marqius-wkhtmltopdf 0.12.13 | Debian 13 | 13 of 13 | GO: nothing blocking and nothing to look at | 4.57 s (11.0× the reference) | yes |
