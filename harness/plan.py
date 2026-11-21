#!/usr/bin/env python3
"""Picks what a run tests and prints it as GITHUB_OUTPUT lines: whether to run at all, the
marqius-wkhtmltopdf version, the programs, the machines, and the cells (one application version on
one kind of machine each).

Read from the environment (each may be empty; every value is checked before it is used):
  EVENT             the event that started the run (scheduled, daily: skipped while the repository is private;
                    once public, it only starts a run by hand, dispatch=true, for a version no run has filed,
                    and on Mondays)
  INPUT_MARQIUS     marqius-wkhtmltopdf version (empty: the latest, from marqius.com)
  INPUT_APPS        applications, separated by spaces (empty: all in apps.json)
  INPUT_SERIES      versions of them to keep, separated by spaces (empty: every supported one)
  INPUT_ARCHS       x86-64, arm64 or both (empty: both)
  INPUT_PROGRAMS    wkhtmltopdf, marqius or both (empty: both; wkhtmltopdf is the reference)
  GH_TOKEN, GITHUB_REPOSITORY
"""
import datetime
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
apps = json.load(open(os.path.join(ROOT, 'apps.json')))
env = os.environ.get
VERSION = re.compile(r'^[0-9]+(\.[0-9]+){1,3}$')


def fail(msg):
    print(f'::error::{msg}', file=sys.stderr)
    sys.exit(1)


def get(url, token=None):
    req = urllib.request.Request(url, headers={'User-Agent': 'wkhtmltopdf-odoo-erpnext', 'Accept': 'application/vnd.github+json'})
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def words(name):
    return (env(name) or '').replace(',', ' ').split()


out = {}
token = env('GH_TOKEN')
repo = env('GITHUB_REPOSITORY')

# a scheduled run (daily) is for the public repository only: while it is private, its minutes are kept
# for runs asked for. Once public, it tests nothing itself: when the latest version has no filed
# results yet (a release the dispatch missed), and on Mondays in any case, it starts a run by hand
# (dispatch=true), because a
# scheduled event does not say whether the repository is public, and GitHub signs the results'
# attestation according to that (a scheduled run's would be refused)
weekly = env('EVENT') == 'schedule'
if weekly:
    if not repo or json.loads(get(f'https://api.github.com/repos/{repo}', token)).get('private', True):
        print('run=false')
        print('dispatch=false')
        print('weekly runs wait until the repository is public', file=sys.stderr)
        sys.exit(0)

mq = (env('INPUT_MARQIUS') or '').strip() or get('https://marqius.com/download/marqius-wkhtmltopdf/latest').strip()
if not VERSION.match(mq):
    fail(f'marqius-wkhtmltopdf version {mq!r} is not a version')

programs = words('INPUT_PROGRAMS') or ['wkhtmltopdf', 'marqius']
for p in programs:
    if p not in ('wkhtmltopdf', 'marqius'):
        fail(f'unknown program {p!r}')
archs = words('INPUT_ARCHS') or list(apps['machines'])
for a in archs:
    if a not in apps['machines']:
        fail(f'unknown machine {a!r}: x86-64 or arm64')
chosen = words('INPUT_APPS') or [k for k, a in apps['apps'].items() if a['series']]
for a in chosen:
    if a not in apps['apps']:
        fail(f'unknown application {a!r}')
keep = words('INPUT_SERIES')
cells = []
for a in chosen:
    app = apps['apps'][a]
    series = [s for s in app['series'] if not keep or s in keep]
    for s in series:
        for m in archs:
            cells.append({'app': a, 'series': s, 'arch': m, 'runner': apps['machines'][m], 'title': f"{app['name']} {s}, {m}"})
unknown = [s for s in keep if not any(s in apps['apps'][a]['series'] for a in chosen)]
if unknown:
    fail(f'no chosen application has the version(s) {" ".join(unknown)}')
if not cells:
    fail('nothing to test')

dispatch = False
if weekly:
    folder = f'marqius-wkhtmltopdf-{mq}'
    filed = os.path.isdir(os.path.join(ROOT, 'results', folder))
    monday = datetime.datetime.now(datetime.timezone.utc).weekday() == 0
    dispatch = not filed or monday
    print(f'{folder}: {"filed" if filed else "not filed yet"}; {"Monday" if monday else "not Monday"}; '
          f'{"starting a run" if dispatch else "nothing to run"}', file=sys.stderr)
out = {'run': 'false' if weekly else 'true', 'dispatch': 'true' if dispatch else 'false', 'marqius': mq,
       'programs': ' '.join(programs), 'archs': json.dumps(archs), 'matrix': json.dumps(cells)}
for k, v in out.items():
    print(f'{k}={v}')
print(f'marqius-wkhtmltopdf {mq}; {len(cells)} cells: ' + '; '.join(c['title'] for c in cells), file=sys.stderr)
