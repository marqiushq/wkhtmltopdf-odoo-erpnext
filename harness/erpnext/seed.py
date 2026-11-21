"""The documents ERPNext prints in this test, with fixed names and dates.

Copied into the backend as erpnext/wkt_seed.py and run once, before any side prints:
    bench --site frontend execute erpnext.wkt_seed.run

Completes the setup wizard (a company with the standard chart of accounts), chooses wkhtmltopdf for
PDFs (ERPNext 16 uses Chrome unless told otherwise), adds a letterhead with a header and a footer that
carries the page numbers, and makes invoices, a quotation, a sales order, a delivery note and a
purchase order. Every name and date is fixed, so every run prints the same documents.
"""
import json

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

COMPANY, ABBR = "Northwind Traders", "NWT"
D, D2 = "2025-03-14", "2025-04-13"

HEADER = """<div style="font-family: sans-serif; border-bottom: 1px solid #888; padding-bottom: 6px;">
<div style="font-size: 18px; font-weight: bold;">Northwind Traders</div>
<div style="font-size: 10px;">400 Lake Shore Drive, Chicago IL 60611, United States &middot; accounts@northwind.example</div>
</div>"""
FOOTER = """<div style="font-family: sans-serif; font-size: 9px; border-top: 1px solid #888; padding-top: 4px;">
Northwind Traders &middot; Registered in Illinois &middot; Bank: First Lake Bank, account 0042 1234 5678
</div>"""
MISSING = '<p>Payment within 30 days.</p><p><img src="/files/wkt-missing-picture.png" alt="missing png"></p>'


def fields(doctype, values):
    """only the fields this version's doctype has"""
    meta = frappe.get_meta(doctype)
    return {k: v for k, v in values.items() if k == "doctype" or meta.has_field(k)}


def first(doctype, **filters):
    return frappe.db.get_value(doctype, dict(filters, is_group=0), "name", order_by="creation asc")


def make(values, name):
    if frappe.db.exists(values["doctype"], name):
        return frappe.get_doc(values["doctype"], name)
    doc = frappe.get_doc(fields(values["doctype"], values))
    doc.insert(set_name=name)
    if doc.meta.is_submittable:
        doc.submit()
    return doc


def run():
    if not frappe.is_setup_complete():
        setup_complete({
            "language": "English", "country": "United States", "timezone": "America/Chicago", "currency": "USD",
            "full_name": "Administrator", "email": "admin@example.com",
            "company_name": COMPANY, "company_abbr": ABBR, "chart_of_accounts": "Standard",
            "fy_start_date": "2025-01-01", "fy_end_date": "2025-12-31",
        })
        frappe.db.commit()
    # wkhtmltopdf for every PDF: ERPNext 16 chooses Chrome by default, 15 knows only wkhtmltopdf
    if frappe.get_meta("Print Settings").has_field("pdf_generator"):
        frappe.db.set_single_value("Print Settings", "pdf_generator", "wkhtmltopdf")
    frappe.db.set_single_value("Print Settings", "repeat_header_footer", 1)

    # the item tables narrowed to the usual six columns, as most companies narrow them: with every
    # column ERPNext prints by default they are wider than A4, and each program cuts or squeezes the
    # overflow its own way (wkhtmltopdf cuts the last columns off at the page's edge)
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    keep = {"item_code", "description", "qty", "uom", "rate", "amount"}
    layout = {"Section Break", "Column Break", "Tab Break", "HTML", "Button", "Table", "Table MultiSelect", "Fold", "Heading"}
    for dt in ("Sales Invoice Item", "Quotation Item", "Sales Order Item", "Delivery Note Item", "Purchase Order Item"):
        for df in frappe.get_meta(dt).fields:
            if df.fieldtype not in layout and df.fieldname not in keep and not df.print_hide:
                make_property_setter(dt, df.fieldname, "print_hide", 1, "Check", validate_fields_for_doctype=False)
    frappe.clear_cache()

    make({"doctype": "Letter Head", "letter_head_name": "WKT Letter Head", "source": "HTML", "content": HEADER,
          "footer_source": "HTML", "footer": FOOTER, "is_default": 1}, "WKT Letter Head")
    frappe.db.set_value("Letter Head", "WKT Letter Head", "is_default", 1)
    for other in frappe.get_all("Letter Head", filters={"name": ["!=", "WKT Letter Head"], "is_default": 1}, pluck="name"):
        frappe.db.set_value("Letter Head", other, "is_default", 0)

    item_group = first("Item Group")
    names = ["Desk Organizer", "Desk Pad", "Monitor Arm", "Office Chair", "Standing Desk", "Filing Cabinet", "Desk Lamp",
             "Whiteboard", "Bookshelf", "Storage Box"]
    for i in range(1, 41):
        make({"doctype": "Item", "item_code": f"WKT-{i:02d}", "item_name": f"{names[i % 10]} {i:02d}",
              "description": f"{names[i % 10]}, model {i:02d}, 120 x {40 + i} cm", "item_group": item_group,
              "stock_uom": "Nos", "is_stock_item": 0}, f"WKT-{i:02d}")
    customers = [("Acme Corporation", "1839 Arbor Way"), ("Globex Retail", "77 Harbour Road"), ("Initech Supplies", "9 Mill Lane")]
    for cname, _ in customers:
        make({"doctype": "Customer", "customer_name": cname, "customer_group": first("Customer Group"),
              "territory": first("Territory")}, cname)
    make({"doctype": "Supplier", "supplier_name": "Contoso Wholesale", "supplier_group": first("Supplier Group")}, "Contoso Wholesale")

    def rows(n, start=1, **x):
        return [dict(item_code=f"WKT-{((start + i - 1) % 40) + 1:02d}", qty=1 + (i * 3) % 7, rate=12.5 + 7 * i, **x) for i in range(n)]

    co = {"company": COMPANY}
    sinv = dict(doctype="Sales Invoice", posting_date=D, set_posting_time=1, due_date=D2, **co)
    make(dict(sinv, customer="Acme Corporation", items=rows(3)), "WKT-SINV-1")
    make(dict(sinv, customer="Globex Retail", items=rows(40, 4)), "WKT-SINV-2")
    make(dict(sinv, customer="Initech Supplies", items=rows(2, 9)), "WKT-SINV-3")
    make(dict(sinv, customer="Acme Corporation", items=rows(5, 12)), "WKT-SINV-4")
    make(dict(sinv, customer="Globex Retail", items=rows(3, 20), terms=MISSING), "WKT-SINV-5")
    make(dict(doctype="Quotation", quotation_to="Customer", party_name="Initech Supplies", transaction_date=D, valid_till=D2,
              items=rows(8, 2), **co), "WKT-QTN-1")
    make(dict(doctype="Sales Order", customer="Acme Corporation", transaction_date=D, delivery_date=D2,
              items=rows(8, 5, delivery_date=D2), **co), "WKT-SO-1")
    make(dict(doctype="Delivery Note", customer="Globex Retail", posting_date=D, set_posting_time=1, items=rows(8, 7), **co), "WKT-DN-1")
    make(dict(doctype="Purchase Order", supplier="Contoso Wholesale", transaction_date=D, schedule_date=D2,
              items=rows(8, 11, schedule_date=D2), **co), "WKT-PO-1")
    frappe.db.commit()
    print("WKT-SEED", json.dumps({
        "frappe": frappe.__version__, "erpnext": frappe.get_attr("erpnext.__version__"),
        "pdf_generator": frappe.db.get_single_value("Print Settings", "pdf_generator")
        if frappe.get_meta("Print Settings").has_field("pdf_generator") else "wkhtmltopdf (the only one)",
        "letter_head": frappe.db.get_value("Letter Head", {"is_default": 1}, "name"),
    }))
