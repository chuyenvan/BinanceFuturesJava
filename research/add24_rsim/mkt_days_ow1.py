#!/usr/bin/env python3
"""LUOT7 EB25: chon NGAY UTC can mkt toan san cho OW1 = ngay co phut gia sim cham bac grid (Add24PriceDue) cua cum sim co leg0 trong
[lo, hi) (= cum rig theo vet) + ngay UTC lien truoc (d15). usage: mkt_days_ow1.py <cums.csv> <lo_ms> <hi_ms> <cums_out.csv> [pricedue.csv]
- che do 1 (khong co pricedue): ghi cums_out (loc leg0 trong [lo,hi)); che do 2: in danh sach ngay (stdout)."""
import csv, sys
from datetime import datetime, timezone, timedelta
c, lo, hi, co = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
if len(sys.argv) == 5:
    rs = [r for r in csv.DictReader(open(c)) if lo <= int(r['t0']) < hi]
    with open(co, 'w') as f:
        w = csv.DictWriter(f, fieldnames=list(rs[0].keys()) if rs else ['cid','sym','first','t0','tEnd','nlegs','lv0','legs']); w.writeheader(); [w.writerow(r) for r in rs]
    print(len(rs))
else:
    ds = set()
    for r in csv.DictReader(open(sys.argv[5])):
        d = datetime.fromtimestamp(int(r['t']) / 1000, timezone.utc).date(); ds.add(d); ds.add(d - timedelta(days=1))
    print(','.join(sorted(x.isoformat() for x in ds)))
