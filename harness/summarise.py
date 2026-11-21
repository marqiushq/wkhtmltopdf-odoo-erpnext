#!/usr/bin/env python3
"""Reads what one cell left in OUT_DIR and writes OUT_DIR/cell.json: for each side, which documents
it printed through the application's own route, their pages, the time each took (through the route,
and in the program itself, from the stand-in's records), the program's exit statuses, what the program
and the application say about it; for each replacement, compare's verdict against the reference.

    python3 harness/summarise.py OUT_DIR PROGRAMS_JSON
"""
import csv
import glob
import json
import os
import re
import statistics
import sys
import unicodedata

out, programs_json = sys.argv[1:3]


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def text(path):
    try:
        with open(path, errors='replace') as f:
            return f.read()
    except OSError:
        return ''


run = load(os.path.join(out, 'run.json'), {})
setup = load(os.path.join(out, 'setup.json'), {})
programs = load(programs_json, {})
arch = run.get('arch')
rows = {f['program']: f for f in programs.get('files', []) if f.get('arch') == arch}


def seconds(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {'total': round(sum(values), 2), 'median': round(statistics.median(values), 3), 'count': len(values)}


cell = {k: run.get(k) for k in ('app', 'series', 'release', 'image', 'arch', 'started', 'ended', 'reference')}
cell['programs'] = {p: {k: r.get(k) for k in ('version', 'file', 'sha256', 'url', 'checked', 'attestation')} for p, r in rows.items()}
cell['cases'] = [{k: c.get(k) for k in ('name', 'report', 'names')} for c in setup.get('cases', [])]
cell['setup_notes'] = setup.get('notes', [])
cell['sides'] = {}
for side in run.get('sides', []):
    d = os.path.join(out, side)
    system, program = side.split('-', 1)
    pr = load(os.path.join(d, 'prints.json'), {})
    pages = {}
    for line in text(os.path.join(d, 'pages.tsv')).splitlines():
        name, _, n = line.partition('\t')
        pages[name] = int(n) if n.strip().isdigit() else None
    # the stand-in's records: one folder per call, named by the time it began (ns)
    calls = []
    for c in sorted(glob.glob(os.path.join(d, 'calls', '*'))):
        rc = text(os.path.join(c, 'rc.txt')).split()
        if len(rc) != 3:
            continue
        status, s, e = int(rc[0]), float(rc[1]), float(rc[2])
        calls.append({'status': status, 'start': s, 'seconds': round(e - s, 3),
                      'stderr': text(os.path.join(c, 'stderr.txt'))[-600:]})
    # each call belongs to one document: the one being printed when it began (or, for a clock a
    # little apart, the one that began last before it, within a second)
    prints = sorted(pr.get('prints', []), key=lambda p: p.get('started', 0))
    owner = {}
    for i, c in enumerate(calls):
        inside = [p['case'] for p in prints if p.get('started', 0) <= c['start'] <= p.get('ended', 0)]
        before = [p['case'] for p in prints if p.get('started', 0) - 1 <= c['start']]
        if inside or before:
            owner[i] = (inside or before)[-1]
    per_case = {}
    for p in pr.get('prints', []):
        mine = [c for i, c in enumerate(calls) if owner.get(i) == p['case']]
        per_case[p['case']] = {
            'printed': p.get('status') == 200 and bool(p.get('bytes')),
            'status': p.get('status'), 'seconds': p.get('seconds'), 'pages': pages.get(p['case']),
            'error': p.get('error'), 'error_name': p.get('error_name'), 'calls': len(mine),
            'program_seconds': round(sum(c['seconds'] for c in mine), 3) if mine else None,
            'exit_statuses': sorted({c['status'] for c in mine}),
        }
    probe = text(os.path.join(d, 'odoo-wkhtml.txt')).strip()
    probe = probe.split(' ', 1)[1] if probe.startswith('ODOO-WKHTML ') else probe
    try:
        probe = json.loads(probe)
    except ValueError:
        pass
    statuses = {}
    for c in calls:
        statuses[str(c['status'])] = statuses.get(str(c['status']), 0) + 1
    cell['sides'][side] = {
        'system': system, 'program': program,
        'says': text(os.path.join(d, 'version.txt')).strip()[:300],
        'application_check': pr.get('state_check'), 'application_view': probe or None,
        'cases': len(per_case), 'printed': sum(1 for v in per_case.values() if v['printed']),
        'route_seconds': seconds([v['seconds'] for v in per_case.values() if v['printed']]),
        'program_seconds': seconds([v['program_seconds'] for v in per_case.values() if v['printed']]),
        'exit_statuses': statuses, 'per_case': per_case,
    }

def invisible(s):
    """True when s shows nothing: only spaces and format characters (Unicode category Cf)"""
    return all(c.isspace() or unicodedata.category(c) == 'Cf' for c in s or '')


# compare's findings for each document, with the pictures it called changed checked again pixel by
# pixel (pictures.py): a picture that looks the same counts as stored differently, not as changed
cell['compare'] = {}
for side in run.get('sides', []):
    t = text(os.path.join(out, f'compare-{side}.txt'))
    if not t:
        continue
    said = next((ln.strip() for ln in t.splitlines() if re.match(r'\s*(GO|REVIEW|NO-GO)\b', ln)), None)
    cdir = os.path.join(out, f'compare-{side}')
    pics = (load(os.path.join(cdir, 'pictures.json'), {}) or {}).get('pairs', {})
    pairs = {}
    try:
        with open(os.path.join(cdir, 'summary.csv'), newline='') as f:
            for r in csv.DictReader(f):
                pairs[r['pair']] = {'level': 'missing' if not r.get('level') else r['level'], 'compare_level': r.get('level'),
                                    'compare_verdict': r.get('verdict'), 'pages': [r.get('pages_old'), r.get('pages_new')],
                                    'reasons': [r.get('first')] if r.get('first') else []}
    except OSError:
        pass
    for pj in sorted(glob.glob(os.path.join(cdir, 'pairs', '*.json'))):
        name = os.path.basename(pj)[:-5]
        pr = load(pj, {})
        po, pn = (pr.get('pages') or {}).get('old'), (pr.get('pages') or {}).get('new')
        follows = f"the same lines on {pn} page{'s' if pn != 1 else ''} instead of {po}: page numbers follow"
        found = []
        for d in pr.get('differences', []):
            level, note = d.get('level'), d.get('note', '')
            kind, was, now = d.get('kind'), (d.get('was') or '').strip(), (d.get('now') or '').strip()
            if kind == 'picture-changed' and (pics.get(name) or {}).get('same'):
                level, note = 'cosmetic', 'a picture stored differently, the same pixel by pixel'
            elif level == 'blocking' and kind in ('added', 'missing', 'text') and invisible(was) and invisible(now):
                # only characters nobody sees: a zero-width space, a joiner, a soft hyphen
                level, note = 'cosmetic', 'an invisible character (' + ', '.join(sorted({f'U+{ord(c):04X}' for c in was + now if not c.isspace()})) + ')'
            elif level == 'blocking' and po and pn and po != pn and (
                    # a page count, or a page's "Page N / M" line, that only follows from the number of pages
                    (kind == 'number' and str(d.get('cause', '')).startswith('number after "Page'))
                    or (kind in ('added', 'missing') and (was or now) in (str(po), str(pn)))
                    or (kind == 'missing' and re.search(r'\bPage \d+ (/|of) \d+\b', was) and pn < po)
                    or (kind == 'added' and re.search(r'\bPage \d+ (/|of) \d+\b', now) and pn > po)):
                level, note = 'review', follows
            found.append([level, note, kind, ' '.join((now if kind == 'added' else was).split())])
        # the same words both added and gone in one document were not added or lost: they moved
        # (a label that wraps at another word, a number now in the next row's line)
        gone = {}
        for i, f in enumerate(found):
            if f[0] == 'blocking' and f[2] == 'missing' and f[3]:
                gone.setdefault(f[3], []).append(i)
        for f in found:
            if f[0] == 'blocking' and f[2] == 'added' and f[3] and gone.get(f[3]):
                j = gone[f[3]].pop()
                f[0] = found[j][0] = 'review'
                f[1] = found[j][1] = f'"{f[3]}" stands elsewhere: the same words, broken across lines differently'
        found = [(f[0], f[1]) for f in found]
        levels = {lv for lv, _ in found}
        level = next((lv for lv in ('blocking', 'review', 'cosmetic') if lv in levels), 'same')
        reasons = []
        for lv, n in found:
            if lv == level and n not in reasons:
                reasons.append(n)
        p = pairs.setdefault(name, {})
        p.update({'level': level, 'compare_level': pr.get('level'), 'compare_verdict': pr.get('verdict'),
                  'pages': [(pr.get('pages') or {}).get('old'), (pr.get('pages') or {}).get('new')],
                  'reasons': reasons[:4], 'pictures': pics.get(name)})
    blocking = sorted(n for n, p in pairs.items() if p['level'] == 'blocking')
    review = sorted(n for n, p in pairs.items() if p['level'] == 'review')
    if blocking:
        verdict = f"NO-GO: {len(blocking)} document{'s' if len(blocking) != 1 else ''} with blocking differences"
    elif review:
        verdict = f"REVIEW: nothing blocking; {len(review)} document{'s' if len(review) != 1 else ''} to look at"
    else:
        verdict = 'GO: nothing blocking and nothing to look at'
    cell['compare'][side] = {'verdict': verdict, 'compare_said': said, 'blocking': len(blocking), 'review': len(review),
                             'pictures_rechecked': len(pics), 'pairs': pairs}

with open(os.path.join(out, 'cell.json'), 'w') as f:
    json.dump(cell, f, indent=1, sort_keys=False)

ref = cell['sides'].get(cell.get('reference') or '', {})
print(f"{cell.get('app')} {cell.get('series')} on {arch}: {len(cell['cases'])} cases")
for side, s in cell['sides'].items():
    rs = (s['route_seconds'] or {}).get('total')
    ratio = ''
    if ref and side != cell.get('reference') and rs and (ref.get('route_seconds') or {}).get('total'):
        ratio = f" ({ref['route_seconds']['total'] / rs:.1f}x the reference's speed through the route)"
    print(f"  {side:24} printed {s['printed']}/{s['cases']} in {rs} s{ratio}; exit statuses {s['exit_statuses']}")
    if side in cell['compare']:
        print(f"  {'':24} compare: {cell['compare'][side]['verdict']}")
