#!/usr/bin/env python3
"""PHAN RA QUYET DINH theo tick — ghep dung tren khoa (ts, symbol, levelChange)."""
import sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
from tick_paired import read_stream, DT_CAND, TICK

NM = {0: "ENTERED", 1: "ALREADY_OPEN", 2: "NO_TICKER", 3: "NO_PRED", 4: "GATE_REJECT",
      5: "NO_BUDGET", 6: "TIER3_DCA", 7: "GRID_EXHAUSTED", 8: "TOPK_CUT"}

a = read_stream("%s/R5_TL/cand.bin.gz" % TICK, DT_CAND)
b = read_stream("%s/R6_TL/cand.bin.gz" % TICK, DT_CAND)
print("cand rows A=%d B=%d" % (len(a), len(b)))
for nm, arr in (("R5_TL", a), ("R6_TL", b)):
    u, c = np.unique(arr["lvl"], return_counts=True)
    print("  %s levelChange ordinal -> so dong: %s" % (nm, dict(zip(u.tolist(), c.tolist()))))

def key(x):
    return (x["ts"].astype(np.int64) * 100000 + x["sym"].astype(np.int64) * 100
            + x["lvl"].astype(np.int64))

ka, kb = key(a), key(b)
print("khoa trung lap A=%d B=%d" % (len(ka) - len(np.unique(ka)), len(kb) - len(np.unique(kb))))
common, ia, ib = np.intersect1d(ka, kb, return_indices=True)
print("khoa CHUNG=%d  chi A=%d  chi B=%d" % (len(common), len(ka) - len(common), len(kb) - len(common)))
da, db = a["dec"][ia], b["dec"][ib]
diff = da != db
print("tren khoa CHUNG: quyet dinh KHAC = %d (%.4f%%)" % (diff.sum(), 100.0 * diff.sum() / len(common)))
pairs, cnt = np.unique(np.stack([da[diff], db[diff]]).T, axis=0, return_counts=True)
order = np.argsort(-cnt)
for i in order:
    x, y = pairs[i]
    print("   R5=%-14s R6=%-14s %d" % (NM[int(x)], NM[int(y)], cnt[i]))
print("\nso dong chi co o mot ben (khac tap ung vien duoc XET):")
onlyA = np.setdiff1d(ka, kb); onlyB = np.setdiff1d(kb, ka)
for nm, arr, k, only in (("R5_TL", a, ka, onlyA), ("R6_TL", b, kb, onlyB)):
    m = np.isin(k, only)
    u, c = np.unique(arr["dec"][m], return_counts=True)
    print("  %s: %d dong  %s" % (nm, m.sum(), {NM[int(x)]: int(y) for x, y in zip(u, c)}))
