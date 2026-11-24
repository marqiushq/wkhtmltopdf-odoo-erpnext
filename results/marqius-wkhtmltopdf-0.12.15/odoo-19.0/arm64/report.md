### Odoo 19.0 (19.0.20261112), arm64

Image `odoo@sha256:03a47921f9eef2c225ded1167fe7828465d2b3177883f30d173bb1c3c792949b`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/45363151857.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | Odoo's image (Ubuntu 24.04) | 13 of 13 | reference | 49.89 s | reference |
| marqius-wkhtmltopdf 0.12.15 | Odoo's image (Ubuntu 24.04) | 13 of 13 | GO: nothing blocking and nothing to look at | 4.9 s (10.2× the reference) | yes |
| marqius-wkhtmltopdf 0.12.15 | Debian 13 | 13 of 13 | GO: nothing blocking and nothing to look at | 4.96 s (10.1× the reference) | yes |
