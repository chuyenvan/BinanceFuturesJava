#!/usr/bin/env python3
import sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
from tick_paired import read_stream, DT_TICK, DT_POS, DT_CAND, TICK, load_daily_equity

for tag, dev in (("R5_TL", "R5_TL"), ("R6_TL", "R6_TL"), ("C2b_TLON", "C2b_TLON")):
    tk = read_stream("%s/%s/tick.bin.gz" % (TICK, tag), DT_TICK)
    eq = tk["bal"].astype(np.float64) + tk["prof"].astype(np.float64) + tk["unreal"].astype(np.float64)
    d, e = load_daily_equity(dev)
    print("%-9s tick.bin: n=%d  eq_dau=%.1f eq_cuoi=%.1f | sim.out: n=%d eq_cuoi=%.1f | lech=%.1f"
          % (tag, len(tk), eq[0], eq[-1], len(e), e[-1], eq[-1] - e[-1]))
    print("           nActive: med=%.1f max=%d | pool: med=%.0f min=%d max=%d"
          % (np.median(tk["nactive"]), tk["nactive"].max(),
             np.median(tk["pool"]), tk["pool"].min(), tk["pool"].max()))

# phan ra quyet dinh: hai run khac nhau o dau
a = read_stream("%s/R5_TL/cand.bin.gz" % TICK, DT_CAND)
b = read_stream("%s/R6_TL/cand.bin.gz" % TICK, DT_CAND)
print("\ncand ts+sym trung khop:", np.array_equal(a["ts"], b["ts"]) and np.array_equal(a["sym"], b["sym"]))
diff = a["dec"] != b["dec"]
print("so dong (tick,symbol) co QUYET DINH KHAC nhau: %d / %d = %.4f%%"
      % (diff.sum(), len(a), 100.0 * diff.sum() / len(a)))
u, c = np.unique(np.stack([a["dec"][diff], b["dec"][diff]]).T, axis=0, return_counts=True)
NM = {0: "ENTERED", 1: "ALREADY_OPEN", 2: "NO_TICKER", 3: "NO_PRED", 4: "GATE_REJECT",
      5: "NO_BUDGET", 6: "TIER3_DCA", 7: "GRID_EXHAUSTED", 8: "TOPK_CUT"}
for (x, y), n in zip(u, c):
    print("   A=%-13s B=%-13s %d" % (NM[int(x)], NM[int(y)], n))
