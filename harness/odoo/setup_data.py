# Run as: odoo shell -d DB < setup_data.py   (Odoo 18, 19 and 20, a fresh database with demo data)
# Makes the documents the test prints, with fixed dates, and writes their ids and the print cases to
# $SETUP_OUT (default /results/setup.json). The database is then copied once per side, so every side
# prints the same records and nothing one side saves can change what another prints.
import datetime
import json
import os
import traceback

admin = env.ref('base.user_admin')
env = env(user=admin, context=dict(env.context, tz='UTC', lang='en_US'))  # noqa: F821  (env comes from odoo shell)
notes = []


def note(*a):
    msg = ' '.join(str(x) for x in a)
    notes.append(msg)
    print('SETUP', msg, flush=True)


ICP = env['ir.config_parameter'].sudo()
for k, v in [('report.url', 'http://127.0.0.1:8069'), ('web.base.url', 'http://127.0.0.1:8069'), ('web.base.url.freeze', 'True')]:
    if hasattr(ICP, 'set_param'):
        ICP.set_param(k, v)  # Odoo 18 and 19
    elif k == 'web.base.url.freeze':
        ICP.set_bool(k, True)  # Odoo 20 names the type
    else:
        ICP.set_str(k, v)

c1 = env.company
note('company', c1.name, 'layout', c1.external_report_layout_id.key if c1.external_report_layout_id else None,
     'font', getattr(c1, 'font', None), 'paperformat', c1.paperformat_id.name)
products = env['product.product'].search([('sale_ok', '=', True), ('type', '=', 'consu'), ('company_id', '=', False)], order='default_code, id')
products = products.filtered(lambda p: p.list_price > 0)[:12]
note('products', products.mapped('display_name'))
partners = env['res.partner'].search([('is_company', '=', True), ('parent_id', '=', False), ('id', 'not in', env['res.company'].search([]).partner_id.ids)], order='id', limit=8)
note('partners', partners.mapped('name'))

D = datetime.date(2026, 11, 2)
T = datetime.datetime(2026, 11, 2, 9, 0)


def so_lines(n, offset):
    return [(0, 0, {'product_id': products[(i + offset) % len(products)].id, 'product_uom_qty': 1 + (i * 3) % 7}) for i in range(n)]


def make_so(partner, n, offset, confirm=False):
    o = env['sale.order'].create({'partner_id': partner.id, 'date_order': T, 'validity_date': D + datetime.timedelta(days=30), 'order_line': so_lines(n, offset)})
    if confirm:
        o.action_confirm()
        o.date_order = T
    return o


so1 = make_so(partners[0], 4, 0)
so2 = make_so(partners[1], 45, 1)
so3 = make_so(partners[2], 3, 2)
so4 = make_so(partners[3], 6, 3, confirm=True)
so5 = make_so(partners[4], 5, 4, confirm=True)
so6 = make_so(partners[5], 4, 5, confirm=True)
note('sale orders', [(o.name, o.state, len(o.order_line)) for o in (so1, so2, so3, so4, so5, so6)])

picks = {}
for key, o in (('pick4', so4), ('pick5', so5), ('pick6', so6)):
    p = o.picking_ids.filtered(lambda x: x.picking_type_code == 'outgoing')[:1]
    if p:
        p.scheduled_date = T + datetime.timedelta(days=1)
        picks[key] = p
note('pickings', {k: (p.name, p.state) for k, p in picks.items()})
if 'pick6' in picks:
    p = picks['pick6']
    try:
        p.action_assign()
        for m in p.move_ids:
            m.quantity = m.product_uom_qty
            m.picked = True
        res = p.button_validate()
        if isinstance(res, dict) and res.get('res_model'):
            note('validation asked for', res.get('res_model'))
            wiz = env[res['res_model']].with_context(**(res.get('context') or {})).create({})
            for meth in ('process', 'process_cancel_backorder', 'action_confirm'):
                if hasattr(wiz, meth):
                    getattr(wiz, meth)()
                    break
        p.date_done = T + datetime.timedelta(days=1, hours=2)
        note('pick6 validated', p.state)
    except Exception:
        note('pick6 not validated', traceback.format_exc()[-600:])


def make_inv(partner, n, offset, narration=None, company=None):
    M = env['account.move'].with_company(company) if company else env['account.move']
    vals = {'move_type': 'out_invoice', 'partner_id': partner.id, 'invoice_date': D,
            'invoice_line_ids': [(0, 0, {'product_id': products[(i + offset) % len(products)].id, 'quantity': 1 + i % 5}) for i in range(n)]}
    if narration:
        vals['narration'] = narration
    m = M.create(vals)
    m.action_post()
    return m


# two pictures that are not there: a .png (wkhtmltopdf counts it, marqius-wkhtmltopdf ignores media) and an .svg (both count it)
missing = ('<p>Terms: payment within 30 days.</p><p><img src="/web/static/img/marqius-test-missing.png" alt="missing png"/>'
           '<img src="/web/static/img/marqius-test-missing.svg" alt="missing svg"/></p>')
missing_png = '<p>Terms: payment within 30 days.</p><p><img src="/web/static/img/marqius-test-missing.png" alt="missing png"/></p>'
inv = {}
inv['A'] = make_inv(partners[0], 3, 0)
inv['B'] = make_inv(partners[1], 50, 1)
inv['C'] = make_inv(partners[2], 2, 2)
inv['D'] = make_inv(partners[3], 30, 3)
inv['E'] = make_inv(partners[4], 3, 4)
inv['F'] = make_inv(partners[5], 3, 5)
inv['H'] = make_inv(partners[6 % len(partners)], 3, 6, narration=missing)
inv['J'] = make_inv(partners[7 % len(partners)], 2, 7, narration=missing)
inv['K'] = make_inv(partners[0], 4, 8, narration=missing)
inv['L'] = make_inv(partners[1], 2, 9, narration=missing_png)
note('narration kept as', inv['H'].narration)

c2 = None
try:
    c2 = env['res.company'].create({'name': 'Northwind Trading Inc', 'street': '400 Lake Shore Drive', 'city': 'Chicago', 'zip': '60611',
                                    'country_id': env.ref('base.us').id, 'phone': '+1 312 555 0142', 'email': 'accounts@northwind.example',
                                    'currency_id': c1.currency_id.id})
    admin.write({'company_ids': [(4, c2.id)]})
    # Odoo gives a new company its chart of accounts when the transaction is committed
    env.cr.commit()
    env2 = env(context=dict(env.context, allowed_company_ids=[c1.id, c2.id]))
    if not env2['account.journal'].search([('company_id', '=', c2.id), ('type', '=', 'sale')], limit=1):
        env2['account.chart.template'].try_loading('generic_coa', c2, install_demo=False)
        env.cr.commit()
    env = env2
    inv['G'] = make_inv(partners[1], 3, 9, company=c2)
    note('second company', c2.name, inv['G'].name, inv['G'].company_id.name)
except Exception:
    note('second company not made', traceback.format_exc()[-800:])
note('invoices', {k: (m.name, m.company_id.name, len(m.invoice_line_ids)) for k, m in inv.items()})

reports = {}
for key, xmlid in [('invoice', 'account.account_invoices'), ('quotation', 'sale.action_report_saleorder'),
                   ('delivery', 'stock.action_report_delivery'), ('picking', 'stock.action_report_picking')]:
    r = env.ref(xmlid, raise_if_not_found=False)
    if r:
        reports[key] = dict(xmlid=xmlid, report_name=r.report_name, attachment=r.attachment or '', attachment_use=bool(r.attachment_use),
                            paperformat=(r.paperformat_id or c1.paperformat_id).name)
pf = c1.paperformat_id
note('paper format', pf.name, dict(format=pf.format, margin_top=pf.margin_top, margin_bottom=pf.margin_bottom, margin_left=pf.margin_left,
                                    margin_right=pf.margin_right, header_spacing=pf.header_spacing, dpi=pf.dpi, orientation=pf.orientation,
                                    disable_shrinking=pf.disable_shrinking, header_line=pf.header_line))

cases = [
    ('invoice-1-page', 'invoice', [inv['A']]),
    ('invoice-3-pages', 'invoice', [inv['B']]),
    ('invoices-3-at-once', 'invoice', [inv['C'], inv['D'], inv['E']]),
    ('invoices-2-companies', 'invoice', [inv['F'], inv['G']] if 'G' in inv else []),
    ('quotation', 'quotation', [so1]),
    ('quotation-long', 'quotation', [so2]),
    ('quotations-3-at-once', 'quotation', [so3, so4, so5]),
    ('delivery-slip', 'delivery', [picks.get('pick6')]),
    ('delivery-slips-3-at-once', 'delivery', [picks.get('pick4'), picks.get('pick5'), picks.get('pick6')]),
    ('picking-operations', 'picking', [picks.get('pick4')]),
    ('invoice-missing-image', 'invoice', [inv['H']]),
    ('invoices-missing-image-2-at-once', 'invoice', [inv['J'], inv['K']]),
    ('invoice-missing-png-only', 'invoice', [inv['L']]),
]
out = dict(db=env.cr.dbname, company_ids=[c.id for c in (c1, c2) if c], reports=reports, notes=notes,
           invoice_ids=[m.id for m in inv.values()], invoices={k: dict(id=m.id, name=m.name) for k, m in inv.items()},
           cases=[dict(name=n, report=k, report_name=reports[k]['report_name'], ids=[r.id for r in recs if r], names=[r.name for r in recs if r])
                  for n, k, recs in cases if k in reports and recs and all(recs)])
env.cr.commit()
with open(os.environ.get('SETUP_OUT', '/results/setup.json'), 'w') as f:
    json.dump(out, f, indent=1, default=str)
note('written', len(out['cases']), 'cases')
