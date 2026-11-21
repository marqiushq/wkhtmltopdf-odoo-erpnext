#!/usr/bin/env python3
"""The report: reads the cells a run left and files them.

    python3 harness/publish.py --cell CELL_JSON
        prints one cell's verdict; exits 1 when a replacement missed a document the reference printed,
        when compare found a difference that blocks, or when the cell left no result
    python3 harness/publish.py ARTIFACTS PROGRAMS_JSON [--summary FILE] [--dry-run] [--message FILE] [--subjects FILE]
        writes the run's report (to FILE, e.g. $GITHUB_STEP_SUMMARY); unless --dry-run, files each cell
        as results/marqius-wkhtmltopdf-VERSION/APP-SERIES/ARCH/{cell.json,report.md}, adds its rows to
        results/history.tsv, rewrites the README's table from the newest result of every cell, and
        writes the commit message and the SHA-256 list of the filed files (for the attestation)

A side keeps up when it prints every document the reference prints, and compare finds nothing that
blocks between its PDF and the reference's: no words, numbers, dates or pages missing or changed.
"""
import argparse
import glob
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = json.load(open(os.path.join(ROOT, 'apps.json')))['apps']
PROGRAM = {'wkhtmltopdf': 'wkhtmltopdf', 'marqius': 'marqius-wkhtmltopdf'}
START, END = '<!-- results:start -->', '<!-- results:end -->'


def side_name(cell, side):
    s = cell['sides'][side]
    v = (cell.get('programs', {}).get(s['program']) or {}).get('version') or ''
    labels = APPS.get(cell.get('app'), {}).get('labels', {})
    return f"{PROGRAM.get(s['program'], s['program'])} {v}".strip(), labels.get(s['system'], s['system'])


def judge(cell):
    """(side -> verdict dict, troubles list) for one cell."""
    ref = cell.get('reference')
    sides = cell.get('sides', {})
    ref_ok = {c for c, v in (sides.get(ref, {}).get('per_case') or {}).items() if v.get('printed')}
    verdicts, troubles = {}, []
    for side, s in sides.items():
        printed = {c for c, v in (s.get('per_case') or {}).items() if v.get('printed')}
        missed = sorted(ref_ok - printed) if side != ref else []
        # the stand-in counts every call: a document printed with no call was made some other way
        # (an older copy, or another PDF maker), so it says nothing about the program
        uncalled = sorted(c for c, v in (s.get('per_case') or {}).items() if v.get('printed') and not v.get('calls'))
        cmp = (cell.get('compare') or {}).get(side) or {}
        blocking = [p for p, v in (cmp.get('pairs') or {}).items() if v.get('level') == 'blocking']
        keeps_up = (side == ref or (not missed and not blocking and bool(cmp))) and not uncalled
        ref_s = ((sides.get(ref) or {}).get('route_seconds') or {}).get('total')
        my_s = (s.get('route_seconds') or {}).get('total')
        verdicts[side] = {'printed': s.get('printed'), 'cases': s.get('cases'), 'missed': missed, 'blocking': blocking,
                          'compare': cmp.get('verdict'), 'keeps_up': keeps_up, 'seconds': my_s,
                          'times_faster': round(ref_s / my_s, 1) if ref_s and my_s and side != ref else None}
        name = ' on '.join(side_name(cell, side))
        if uncalled:
            troubles.append(f'{name} printed {", ".join(uncalled)} without calling the program')
        if missed:
            troubles.append(f'{name} did not print {", ".join(missed)}')
        if blocking:
            troubles.append(f'{name}: compare blocks on {", ".join(blocking)}')
        if side != ref and not cmp and ref_ok:
            troubles.append(f'{name}: no comparison')
    if ref and len(ref_ok) < (sides.get(ref, {}).get('cases') or 0):
        failed = sorted(c for c, v in sides[ref]['per_case'].items() if not v.get('printed'))
        troubles.append(f'the reference did not print {", ".join(failed)} (not held against anyone)')
    return verdicts, troubles


def cell_report(cell):
    app = APPS.get(cell.get('app'), {}).get('name', cell.get('app'))
    verdicts, troubles = judge(cell)
    ref = cell.get('reference')
    lines = [f"### {app} {cell.get('series')} ({cell.get('release')}), {cell.get('arch')}", '',
             f"Image `{cell.get('image')}`. Run: {cell.get('run_url', 'local')}.", '',
             '| Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Keeps up |',
             '|---|---|---|---|---|---|']
    for side, v in verdicts.items():
        prog, system = side_name(cell, side)
        speed = f"{v['seconds']} s" if v['seconds'] is not None else '–'
        if v['times_faster']:
            speed += f" ({v['times_faster']}× the reference)"
        verdict = 'reference' if side == ref else (v['compare'] or '–')
        lines.append(f"| {prog} | {system} | {v['printed']} of {v['cases']} | {verdict} | {speed} | "
                     f"{'reference' if side == ref else ('yes' if v['keeps_up'] else 'no')} |")
    if troubles:
        lines += ['', '**To look at:**', ''] + [f'- {t}' for t in troubles]
    why = []
    for side, cmp in (cell.get('compare') or {}).items():
        for doc, p in sorted((cmp.get('pairs') or {}).items()):
            if p.get('level') in ('blocking', 'review') and p.get('reasons'):
                why.append(f"- {' on '.join(side_name(cell, side))}, {doc} ({p['level']}): {'; '.join(p['reasons'][:3])[:300]}")
    if why:
        lines += ['', '**What compare found, document by document:**', ''] + why
    errors = []
    for side, s in cell.get('sides', {}).items():
        for case, c in (s.get('per_case') or {}).items():
            if not c.get('printed') and c.get('error'):
                name = str(c.get('error_name') or '').replace('builtins.', '')
                errors.append(f"- {' on '.join(side_name(cell, side))}, {case}: {name + ': ' if name else ''}{str(c['error'])[:300]}")
    if errors:
        lines += ['', '**What the application said when a document did not print:**', ''] + errors
    return '\n'.join(lines) + '\n'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('artifacts', nargs='?')
    ap.add_argument('programs', nargs='?')
    ap.add_argument('--cell')
    ap.add_argument('--summary')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--message')
    ap.add_argument('--subjects')
    a = ap.parse_args()

    if a.cell:
        if not os.path.exists(a.cell):
            print('::error::this cell left no result')
            return 1
        cell = json.load(open(a.cell))
        print(cell_report(cell))
        # a program's miss is a result, filed and shown in the report; the cell fails only when it could
        # not test: no result, or a reference that printed nothing to compare with
        _, troubles = judge(cell)
        for t in troubles:
            print(f'::notice::{t}')
        ref = (cell.get('sides') or {}).get(cell.get('reference') or '') or {}
        if not ref.get('printed'):
            print('::error::the reference printed nothing, so nothing could be compared')
            return 1
        return 0

    cells = []
    for p in sorted(glob.glob(os.path.join(a.artifacts, 'cell-*', 'cell.json'))):
        try:
            cells.append(json.load(open(p)))
        except ValueError:
            print(f'::warning::{p} is not readable')
    if not cells:
        print('::error::no cell left a result')
        return 1
    progs = json.load(open(a.programs))
    ver = {f['program']: f['version'] for f in progs.get('files', [])}
    folder = f"marqius-wkhtmltopdf-{ver.get('marqius')}"
    report = f'## Reports: marqius-wkhtmltopdf {ver.get("marqius")} against wkhtmltopdf 0.12.6\n\n'
    report += '\n'.join(cell_report(c) for c in cells)
    if a.summary:
        with open(a.summary, 'a') as f:
            f.write(report)
    print(report)
    if a.dry_run:
        return 0

    filed, rows = [], []
    for c in cells:
        d = os.path.join(ROOT, 'results', folder, f"{c['app']}-{c['series']}", c['arch'])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'cell.json'), 'w') as f:
            json.dump(c, f, indent=1)
        with open(os.path.join(d, 'report.md'), 'w') as f:
            f.write(cell_report(c))
        filed += [os.path.join(d, 'cell.json'), os.path.join(d, 'report.md')]
        verdicts, _ = judge(c)
        for side, v in verdicts.items():
            s = c['sides'][side]
            rows.append('\t'.join(str(x) for x in (c.get('ended', ''), folder, c['app'], c['series'], c.get('release', ''), c['arch'],
                                                   s['system'], s['program'], (c.get('programs', {}).get(s['program']) or {}).get('version', ''),
                                                   v['printed'], v['cases'], v['compare'] or '', v['keeps_up'], v['seconds'], c.get('run_url', ''))))
    hist = os.path.join(ROOT, 'results', 'history.tsv')
    new = not os.path.exists(hist)
    with open(hist, 'a') as f:
        if new:
            f.write('ended\tfolder\tapp\tseries\trelease\tarch\tsystem\tprogram\tversion\tprinted\tcases\tcompare\tkeeps_up\tseconds\trun\n')
        f.write(''.join(r + '\n' for r in rows))
    filed.append(hist)

    # the README's table: the newest filed result of every cell
    readme = os.path.join(ROOT, 'README.md')
    if os.path.exists(readme):
        latest = {}
        for p in glob.glob(os.path.join(ROOT, 'results', '*', '*', '*', 'cell.json')):
            c = json.load(open(p))
            k = (c['app'], c['series'], c['arch'])
            if k not in latest or c.get('ended', '') > latest[k].get('ended', ''):
                latest[k] = c
        table = ['| Application | Machine | Program | System | Printed | compare against wkhtmltopdf 0.12.6 | Through the Print route | Run |',
                 '|---|---|---|---|---|---|---|---|']
        for k in sorted(latest, key=lambda k: (k[0], [int(x) if x.isdigit() else x for x in k[1].replace('v', '').split('.')], k[2])):
            c = latest[k]
            verdicts, _ = judge(c)
            for side, v in verdicts.items():
                prog, system = side_name(c, side)
                speed = f"{v['seconds']} s" if v['seconds'] is not None else '–'
                if v['times_faster']:
                    speed += f" ({v['times_faster']}×)"
                verdict = 'reference' if side == c.get('reference') else (v['compare'] or '–')
                table.append(f"| {APPS[c['app']]['name']} {c['series']} | {c['arch']} | {prog} | {system} | {v['printed']} of {v['cases']} | "
                             f"{verdict} | {speed} | [log]({c.get('run_url', '')}) |")
        t = open(readme).read()
        if START in t and END in t:
            t = t.split(START)[0] + START + '\n' + '\n'.join(table) + '\n' + END + t.split(END, 1)[1]
            with open(readme, 'w') as f:
                f.write(t)
            filed.append(readme)
        else:
            print('::warning::README.md has no results markers; its table is not updated')

    if a.message:
        with open(a.message, 'w') as f:
            f.write(f"Results for {folder} ({len(cells)} cell{'s' if len(cells) != 1 else ''})\n\n"
                    + '\n'.join(f"- {APPS[c['app']]['name']} {c['series']}, {c['arch']}" for c in cells)
                    + f"\n\nRun: {cells[0].get('run_url', '')}\n")
    if a.subjects:
        with open(a.subjects, 'w') as f:
            for p in filed:
                f.write(f'{sha256(p)}  {os.path.relpath(p, ROOT)}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
