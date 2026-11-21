### Odoo 19.0 (19.0.20261112), x86-64

Image `odoo@sha256:03a47921f9eef2c225ded1167fe7828465d2b3177883f30d173bb1c3c792949b`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/44932224198.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | Odoo's image (Ubuntu 24.04) | 13 of 13 | reference | 48.64 s | reference |
| marqius-wkhtmltopdf 0.12.13 | Odoo's image (Ubuntu 24.04) | 13 of 13 | GO: nothing blocking and nothing to look at | 3.85 s (12.6× the reference) | yes |
| marqius-wkhtmltopdf 0.12.13 | Debian 13 | 13 of 13 | GO: nothing blocking and nothing to look at | 3.74 s (13.0× the reference) | yes |
