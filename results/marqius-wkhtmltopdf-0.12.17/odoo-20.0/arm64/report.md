### Odoo 20.0 (20.0.20261112), arm64

Image `odoo@sha256:c7352c766b245b3c0e5c7b7a57e7660dde3265872be9566870d44bdb974f44cf`. Run: https://github.com/marqiushq/wkhtmltopdf-odoo-erpnext/actions/runs/45405829029.

| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |
|---|---|---|---|---|---|
| wkhtmltopdf 0.12.6.1-3 | Odoo's image (Ubuntu 24.04) | 13 of 13 | reference | 54.1 s | reference |
| marqius-wkhtmltopdf 0.12.17 | Odoo's image (Ubuntu 24.04) | 13 of 13 | REVIEW: nothing blocking; 3 documents to look at | 5.31 s (10.2× the reference) | yes |
| marqius-wkhtmltopdf 0.12.17 | Debian 13 | 13 of 13 | REVIEW: nothing blocking; 3 documents to look at | 5.28 s (10.2× the reference) | yes |

**What compare found, document by document:**

- marqius-wkhtmltopdf 0.12.17 on Odoo's image (Ubuntu 24.04), delivery-slip (review): "�" stands against "phone_f": one side draws letters with no meaning given, so they cannot be compared; 1 of the 394 letters of the old document are drawn with no word of what they are (the file gives its font no map to letters): they cannot be compared
- marqius-wkhtmltopdf 0.12.17 on Odoo's image (Ubuntu 24.04), delivery-slips-3-at-once (review): "�" stands against "phone_f": one side draws letters with no meaning given, so they cannot be compared; 3 of the 1245 letters of the old document are drawn with no word of what they are (the file gives its font no map to letters): they cannot be compared
- marqius-wkhtmltopdf 0.12.17 on Odoo's image (Ubuntu 24.04), picking-operations (review): "�" stands against "phone_f": one side draws letters with no meaning given, so they cannot be compared; 1 of the 375 letters of the old document are drawn with no word of what they are (the file gives its font no map to letters): they cannot be compared
- marqius-wkhtmltopdf 0.12.17 on Debian 13, delivery-slip (review): "�" stands against "phone_f": one side draws letters with no meaning given, so they cannot be compared; 1 of the 394 letters of the old document are drawn with no word of what they are (the file gives its font no map to letters): they cannot be compared
- marqius-wkhtmltopdf 0.12.17 on Debian 13, delivery-slips-3-at-once (review): "�" stands against "phone_f": one side draws letters with no meaning given, so they cannot be compared; 3 of the 1245 letters of the old document are drawn with no word of what they are (the file gives its font no map to letters): they cannot be compared
- marqius-wkhtmltopdf 0.12.17 on Debian 13, picking-operations (review): "�" stands against "phone_f": one side draws letters with no meaning given, so they cannot be compared; 1 of the 375 letters of the old document are drawn with no word of what they are (the file gives its font no map to letters): they cannot be compared
