#!/usr/bin/env python3
# Phan tich EXIT-CLAMP-118: phan bo hold-time + top symbol. Xac dinh data vs logic.
import re, sys
from datetime import datetime
from collections import Counter, defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "logs/worstn_invert.log"
rx = re.compile(r"EXIT-CLAMP-118.*?sym=(\S+).*?start=(\d{8} \d{2}:\d{2}).*?trigger=(\d{8} \d{2}:\d{2})")
buckets = Counter()
sym_cnt = Counter()
sym_longhold = Counter()
holds = []
n = 0
for line in open(path, encoding="utf-8", errors="ignore"):
    if "EXIT-CLAMP-118" not in line:
        continue
    m = rx.search(line)
    if not m:
        continue
    sym, s, t = m.group(1), m.group(2), m.group(3)
    try:
        ds = datetime.strptime(s, "%Y%m%d %H:%M")
        dt = datetime.strptime(t, "%Y%m%d %H:%M")
    except Exception:
        continue
    days = (dt - ds).total_seconds() / 86400.0
    holds.append(days)
    n += 1
    sym_cnt[sym] += 1
    if days < 1: buckets["<1d"] += 1
    elif days < 7: buckets["1-7d"] += 1
    elif days < 30: buckets["7-30d"] += 1
    else:
        buckets[">30d"] += 1
        sym_longhold[sym] += 1

print("TONG EXIT-CLAMP parsed:", n)
print("PHAN BO HOLD-TIME:")
for k in ["<1d", "1-7d", "7-30d", ">30d"]:
    print(f"  {k:6s}: {buckets[k]:5d}  ({100.0*buckets[k]/max(1,n):.1f}%)")
if holds:
    holds.sort()
    print(f"HOLD days: min={holds[0]:.2f} median={holds[len(holds)//2]:.2f} max={holds[-1]:.2f} mean={sum(holds)/len(holds):.2f}")
print("TOP 12 symbol theo so clamp:")
for s, c in sym_cnt.most_common(12):
    print(f"  {s:14s} clamp={c:4d} longhold>30d={sym_longhold.get(s,0)}")
print("TOP 10 symbol co clamp hold >30d (nghi data-gap/ghost neu dong vao vai coin):")
for s, c in sym_longhold.most_common(10):
    print(f"  {s:14s} >30d={c}")
print("So symbol distinct co clamp:", len(sym_cnt))
