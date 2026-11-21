# Run as: odoo shell -d DB < probe.py
# Prints, on one line starting ODOO-WKHTML, what Odoo itself makes of the wkhtmltopdf it finds: the
# state its Print button acts on, the version it read, and whether it believes Qt is patched (Odoo
# refuses to print several records at once with an unpatched Qt).
import json

found = {}
try:  # Odoo 20 moved wkhtmltopdf to a module of its own
    from odoo.addons.base_report_wkhtmltox.models import ir_actions_report as m
except ImportError:  # Odoo 18 and 19
    from odoo.addons.base.models import ir_actions_report as m
if hasattr(m, '_wkhtml'):  # 19 and 20: a cached function
    w = m._wkhtml()
    found = w._asdict() if hasattr(w, '_asdict') else {k: getattr(w, k) for k in dir(w) if not k.startswith('_')}
else:  # 18: worked out once, when the module is imported
    found = {k: getattr(m, k) for k in dir(m) if k.startswith('wkhtmltopdf_')}
print('ODOO-WKHTML', json.dumps(found, default=str), flush=True)
