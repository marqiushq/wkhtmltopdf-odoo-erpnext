#!/usr/bin/env python3
"""Checks again, pixel by pixel, every picture compare calls changed.

compare reads the colour values a PDF stores for a picture. Two programs can store the same picture
differently: one attaches a colour profile, another keeps other values under the fully transparent
part of a picture with transparency. compare then calls the picture changed, though it looks the same.
So for each pair of PDFs where compare found a changed picture, every picture of both PDFs is laid on
white through its own transparency mask, as a viewer shows it, and compared pixel by pixel. The pair's
pictures count as the same when every one matches its counterpart (same pages, same order) within a
few levels. Writes COMPARE_DIR/pictures.json.

    python3 pictures.py COMPARE_DIR OLD_PDF_DIR NEW_PDF_DIR
"""
import glob
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops

LEVELS = 8          # a pixel differs when one of its colours is more than this many levels apart (of 255)
SHARE = 0.005       # pictures are the same when fewer than this share of their pixels differ

cmp_dir, old_dir, new_dir = sys.argv[1:4]


def pictures(pdf, tmp):
    """[(page, picture laid on white)] in the order the PDF draws them."""
    rows = subprocess.run(['pdfimages', '-list', pdf], capture_output=True, text=True, check=True).stdout.splitlines()[2:]
    subprocess.run(['pdfimages', '-png', pdf, os.path.join(tmp, 'p')], check=True)
    files = sorted(glob.glob(os.path.join(tmp, 'p-*.png')))
    found = []
    for row, f in zip(rows, files):
        cols = row.split()
        page, kind = int(cols[0]), cols[2]
        if kind == 'image':
            found.append([page, Image.open(f).convert('RGB'), None])
        elif kind in ('smask', 'mask') and found:
            found[-1][2] = Image.open(f).convert('L')
    shown = []
    for page, rgb, mask in found:
        if mask is not None:
            if mask.size != rgb.size:
                mask = mask.resize(rgb.size)
            rgb = Image.composite(rgb, Image.new('RGB', rgb.size, (255, 255, 255)), mask)
        shown.append((page, rgb))
    return shown


def differ(a, b):
    """(largest difference in levels, share of pixels that differ)"""
    if a.size != b.size:
        b = b.resize(a.size, Image.LANCZOS)
    d = ImageChops.difference(a, b)
    px = d.getdata()
    worst = 0
    over = 0
    for p in px:
        m = max(p)
        worst = max(worst, m)
        if m > LEVELS:
            over += 1
    return worst, over / max(1, len(px))


result = {}
for pj in sorted(glob.glob(os.path.join(cmp_dir, 'pairs', '*.json'))):
    name = os.path.basename(pj)[:-5]
    pair = json.load(open(pj))
    if not any(d.get('kind') == 'picture-changed' for d in pair.get('differences', [])):
        continue
    old_pdf, new_pdf = os.path.join(old_dir, name + '.pdf'), os.path.join(new_dir, name + '.pdf')
    if not (os.path.exists(old_pdf) and os.path.exists(new_pdf)):
        continue
    with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
        a, b = pictures(old_pdf, t1), pictures(new_pdf, t2)
    rec = {'pictures': [len(a), len(b)], 'same': False}
    # like with like: on each page, each picture with the first unused one of the same size in the
    # other PDF, then any left in order; compare's own count of pictures added or missing stands
    pairs = []
    for page in sorted({p for p, _ in a} | {p for p, _ in b}):
        pa, pb = [x for p, x in a if p == page], [x for p, x in b if p == page]
        left = []
        for x in pa:
            j = next((i for i, y in enumerate(pb) if y.size == x.size), None)
            if j is None:
                left.append(x)
            else:
                pairs.append((x, pb.pop(j)))
        if len(left) == len(pb):
            pairs += list(zip(left, pb))
    if pairs:
        diffs = [differ(x, y) for x, y in pairs]
        rec['largest_difference'] = max(d[0] for d in diffs)
        rec['largest_share_differing'] = round(max(d[1] for d in diffs), 4)
        rec['same'] = all(d[1] < SHARE for d in diffs)
    rec['checked'] = len(pairs)
    result[name] = rec

with open(os.path.join(cmp_dir, 'pictures.json'), 'w') as f:
    json.dump({'levels': LEVELS, 'share': SHARE, 'pairs': result}, f, indent=1)
same = sum(1 for r in result.values() if r['same'])
print(f'pictures compare called changed: {len(result)} documents checked, {same} look the same pixel by pixel')
