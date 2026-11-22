#!/usr/bin/env python3
"""LUOT7 EB25: loc mkt.csv.gz chi giu cac PHUT can cho nhanh DCA cua rig: moi phut gia sim cham bac (pricedue.csv) va 16 phut truoc (d15),
trong [from_ms, to_ms). Bo nho rig KHONG theo so dong ma theo n_sym x 5 x (END - mkt.from)/1phut float (ReplayData.loadMkt); OOM truoc day do manifest mkt.from = START. EB24 assert.
usage: mkt_filter.py <mkt_in.csv.gz> <pricedue.csv> <out.csv.gz> <from_ms> <to_ms> [max_rows=4800000] [--truncate]
--truncate: neu vuot tran, giu cac phut SOM nhat toi tran va bao phut cuoi co mkt (coverage_end)."""
import csv, gzip, sys, json
mi, pd, mo, a, b = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
mx = int(sys.argv[6]) if len(sys.argv) > 6 else 4800000
keep = set()
for r in csv.DictReader(open(pd)):
    t = int(r['t'])
    if a <= t < b:
        for k in range(17): keep.add(t - k * 60000)
import collections
trunc = '--truncate' in sys.argv
if trunc:
    cnt = collections.Counter()
    for ln in gzip.open(mi, 'rt'):
        if not ln.startswith('symbol'):
            t = int(ln.split(',', 2)[1])
            if t in keep: cnt[t] += 1
    acc = 0; k2 = set()
    for t in sorted(cnt):
        if acc + cnt[t] > mx: break
        acc += cnt[t]; k2.add(t)
    keep = k2
n = 0
with gzip.open(mo, 'wt') as fo:
    for ln in gzip.open(mi, 'rt'):
        if ln.startswith('symbol'): fo.write(ln); continue
        t = int(ln.split(',', 2)[1])
        assert t <= 1790787599999, 'EB24'
        if t in keep: fo.write(ln); n += 1
print(json.dumps(dict(minutes=len(keep), rows=n, cap=mx, ok=n <= mx, truncate=trunc, coverage_end=(max(keep) if keep else None))))
sys.exit(0 if n <= mx else 3)
