#!/usr/bin/env python3
"""ADD24 ERRATA3 A10: ban rig ghi ra dia (ngoai /dev/shm) KHONG co truong equity / PnL. legs.csv bo cot eq, eq_at, capital;
result.json bo moi khoa chua equity/realized/pnl/balance/X6 (de quy). fills.csv KHONG chep. usage: sanitize.py <lane_src> <dst>"""
import csv, json, os, re, shutil, sys

BAD = re.compile(r'(equity|realized|pnl|balance|^X6$|^eq$|eq_at|capital|truth)', re.I)


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items() if not BAD.search(str(k))}
    if isinstance(o, list):
        return [clean(x) for x in o]
    return o


def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    if os.path.exists(src + '/legs.csv'):
        r = list(csv.DictReader(open(src + '/legs.csv')))
        cols = [c for c in (r[0].keys() if r else []) if not BAD.search(c)]
        with open(dst + '/legs.csv', 'w') as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore', lineterminator='\n'); w.writeheader(); w.writerows(r)
    if os.path.exists(src + '/result.json'):
        json.dump(clean(json.load(open(src + '/result.json'))), open(dst + '/result.json', 'w'), indent=1)
    for f in ('events.csv', 'env_used.sh', 'outcomes.csv'):
        if os.path.exists(src + '/' + f):
            shutil.copy(src + '/' + f, dst + '/' + f)
    if os.path.exists(src + '/run.log'):
        with open(src + '/run.log', errors='replace') as fi, open(dst + '/run.log', 'w') as fo:
            for ln in fi:
                if not re.search(r'(equity|realized|pnl|balance)', ln, re.I):
                    fo.write(ln)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
