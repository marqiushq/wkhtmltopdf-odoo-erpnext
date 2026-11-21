#!/usr/bin/env python3
"""Prints every case as ERPNext's own Print button does: signed in as Administrator, then Frappe's
PDF route for each case (download_pdf for one document, download_multi_pdf for several), with the
Standard print format, the default letterhead and wkhtmltopdf as the PDF maker. Keeps each PDF, or
what Frappe answered instead, with the time it took. Standard library only.

    python3 print_cases.py BASE_URL OUT_DIR CASES_JSON
"""
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

base, out, cases_path = sys.argv[1:4]
cases = json.load(open(cases_path))['cases']
os.makedirs(out, exist_ok=True)
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(path, params=None, data=None, timeout=300):
    """(status, content type, body)"""
    url = base + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, data=data, headers={'Accept': 'application/pdf, application/json, */*'})
    if data is not None:
        req.add_header('Content-Type', 'application/json')
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, r.headers.get('Content-Type', ''), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read()


def message(body):
    """what Frappe says went wrong, in its own words"""
    try:
        j = json.loads(body)
    except ValueError:
        return body[:1500].decode('utf-8', 'replace')
    for key in ('_server_messages', 'exception', 'exc_type', 'message'):
        if j.get(key):
            v = j[key]
            if key == '_server_messages':
                try:
                    v = ' | '.join(json.loads(m).get('message', m) for m in json.loads(v))
                except (ValueError, AttributeError, TypeError):
                    pass
            return str(v)[:1500]
    return json.dumps(j)[:1500]


for _ in range(90):
    try:
        if call('/api/method/ping', timeout=5)[0] == 200:
            break
    except OSError:
        pass
    time.sleep(2)
res = {'base': base}
status, _, body = call('/api/method/login', data=json.dumps({'usr': 'Administrator', 'pwd': 'admin'}).encode())
res['login'] = status
# what Frappe itself makes of the program: the check its Print dialog makes
status, _, body = call('/api/method/frappe.utils.pdf.is_wkhtmltopdf_valid')
res['state_check'] = {'route': 'frappe.utils.pdf.is_wkhtmltopdf_valid', 'status': status, 'answer': message(body) if status != 200 else json.loads(body).get('message')}
res['prints'] = []
for case in cases:
    common = {'doctype': case['doctype'], 'format': 'Standard', 'no_letterhead': 0, 'pdf_generator': 'wkhtmltopdf'}
    if len(case['names']) == 1:
        path, params = '/api/method/frappe.utils.print_format.download_pdf', dict(common, name=case['names'][0])
    else:
        path, params = '/api/method/frappe.utils.print_format.download_multi_pdf', dict(common, name=json.dumps(case['names']))
    t0 = time.time()
    try:
        status, ctype, body = call(path, params)
    except OSError as e:
        rec = {'case': case['name'], 'status': None, 'error': repr(e)}
    else:
        rec = {'case': case['name'], 'status': status, 'content_type': ctype}
        if status == 200 and body[:5] == b'%PDF-':
            with open(os.path.join(out, case['name'] + '.pdf'), 'wb') as f:
                f.write(body)
            rec['bytes'] = len(body)
        else:
            rec['error'] = message(body)
            try:
                rec['error_name'] = json.loads(body).get('exc_type')
            except ValueError:
                pass
    rec.update(started=round(t0, 3), ended=round(time.time(), 3), seconds=round(time.time() - t0, 2), records=case['names'])
    res['prints'].append(rec)
    print(json.dumps(rec), flush=True)
with open(os.path.join(out, 'prints.json'), 'w') as f:
    json.dump(res, f, indent=1)
