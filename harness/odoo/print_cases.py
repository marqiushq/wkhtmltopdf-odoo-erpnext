"""Prints every case the way Odoo's web client does: signed in as admin, the check Odoo makes before
printing (/report/check_wkhtmltopdf in 19, /report/get_pdf_engine_state in 20), then
/report/download for each case. Keeps each PDF, or the error Odoo would show, with the time it took.

    python3 print_cases.py BASE_URL DB OUT_DIR SETUP_JSON [CASE ...]
"""
import html
import json
import os
import sys
import time
import urllib.parse

import requests

base, db, out, setup_path = sys.argv[1:5]
only = set(sys.argv[5:])
setup = json.load(open(setup_path))
os.makedirs(out, exist_ok=True)
s = requests.Session()
for _ in range(150):
    try:
        if s.get(base + '/web/login', timeout=5).status_code == 200:
            break
    except requests.RequestException:
        pass
    time.sleep(2)


def jsonrpc(path, params, timeout=120):
    r = s.post(base + path, json={'jsonrpc': '2.0', 'method': 'call', 'params': params}, timeout=timeout)
    j = r.json()
    if 'error' in j:
        raise RuntimeError(json.dumps(j['error'])[:3000])
    return j.get('result')


res = {'db': db, 'base': base}
res['login'] = (jsonrpc('/web/session/authenticate', {'db': db, 'login': 'admin', 'password': 'admin'}) or {}).get('uid')
for path, params in [('/report/check_wkhtmltopdf', {}), ('/report/get_pdf_engine_state', {'engine_name': 'wkhtmltopdf'})]:
    try:
        res['state_check'] = {'route': path, 'state': jsonrpc(path, params)}
        break
    except Exception as e:  # the route of the other version
        res.setdefault('state_check_errors', []).append(f'{path}: {e}'[:400])
ctx = {'allowed_company_ids': setup['company_ids'], 'lang': 'en_US', 'tz': 'UTC'}
res['prints'] = []
for case in setup['cases']:
    if only and case['name'] not in only:
        continue
    url = '/report/pdf/%s/%s' % (case['report_name'], ','.join(map(str, case['ids'])))
    q = urllib.parse.urlencode({'data': json.dumps([url, 'qweb-pdf']), 'context': json.dumps(ctx)})
    t0 = time.time()
    try:
        r = s.get(base + '/report/download?' + q, timeout=900)
    except requests.RequestException as e:
        rec = {'case': case['name'], 'status': None, 'error': repr(e)}
    else:
        rec = {'case': case['name'], 'status': r.status_code, 'content_type': r.headers.get('Content-Type', '')}
        if r.status_code == 200 and r.content[:5] == b'%PDF-':
            with open(os.path.join(out, case['name'] + '.pdf'), 'wb') as f:
                f.write(r.content)
            rec['bytes'] = len(r.content)
        else:
            body = html.unescape(r.text)
            try:
                e = json.loads(body)
                rec['error'] = (e.get('data') or {}).get('message') or e.get('message')
                rec['error_name'] = (e.get('data') or {}).get('name')
            except ValueError:
                rec['error'] = body[:1500]
    rec.update(started=round(t0, 3), ended=round(time.time(), 3), seconds=round(time.time() - t0, 2), records=case['names'])
    res['prints'].append(rec)
    print(json.dumps(rec), flush=True)
with open(os.path.join(out, 'prints.json'), 'w') as f:
    json.dump(res, f, indent=1)
