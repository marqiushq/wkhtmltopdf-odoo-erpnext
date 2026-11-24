### Odoo 18.0 (18.0.20261112), arm64

Image `odoo@sha256:0bd79cf07f59105c5697667c2241b86447e99c6adb036200df0e4e295785bdf3`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/45405829029.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | Odoo's image (Ubuntu 24.04) | 13 of 13 | reference | 50.73 s | reference |
| marqius-wkhtmltopdf 0.12.17 | Odoo's image (Ubuntu 24.04) | 13 of 13 | GO: nothing blocking and nothing to look at | 4.86 s (10.4× the reference) | yes |
| marqius-wkhtmltopdf 0.12.17 | Debian 13 | 13 of 13 | GO: nothing blocking and nothing to look at | 4.59 s (11.1× the reference) | yes |
