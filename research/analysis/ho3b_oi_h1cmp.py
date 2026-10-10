#!/usr/bin/env python3
"""HO3b bao kem cong 3 (§4a, khong vao cong): ty le khop tung cot OI dung lai (Vision) vs file ghim e3887f63 tren H1,
theo thang (+07). O khop = float32 bang nhau hoac ca hai NaN. Chi dem/ty le. RAM thap (tung thang)."""
import glob, json, sys
import numpy as np
import pandas as pd
ODT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
PIN = "/home/ubuntu/claude_master/1003/ho3b/../../../claudedata/oi/oi_percoin_full.bin"
PIN = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
RB = "/home/ubuntu/claude_master/1003/ho3b/oi_rebuild"
NM = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
TZ = "Asia/Ho_Chi_Minh"
files = sorted(glob.glob(RB + "/*.bin"))
res = {}
for m in range(1, 7):
    lo = pd.Timestamp("2026-%02d-01" % m, tz=TZ).value // 10**6
    hi = pd.Timestamp("2026-%02d-01" % (m + 1), tz=TZ).value // 10**6
    R = np.concatenate([x[(x["ts"] >= lo) & (x["ts"] < hi)] for x in (np.fromfile(f, dtype=ODT) for f in files)])
    n = 140924110
    P = []
    for k in range(0, n, 10_000_000):
        c = np.fromfile(PIN, dtype=ODT, count=min(10_000_000, n - k), offset=k * 30)
        P.append(c[(c["ts"] >= lo) & (c["ts"] < hi)].copy())
    P = np.concatenate(P)
    kr = R["ts"].astype(np.int64) * 10000 + R["sym"]
    kp = P["ts"].astype(np.int64) * 10000 + P["sym"]
    com, ir, ip = np.intersect1d(kr, kp, return_indices=True)
    r = dict(rows_rebuild=int(len(R)), rows_pin=int(len(P)), both=int(len(com)))
    for j, nm in enumerate(NM):
        a = R["oi"][ir, j].astype(np.float32); b = P["oi"][ip, j].astype(np.float32)
        r[nm] = round(float(((a == b) | (np.isnan(a) & np.isnan(b))).mean()), 6)
    res["2026-%02d" % m] = r
    print(m, json.dumps(r), flush=True)
tot = {nm: float(np.average([res[k][nm] for k in res], weights=[res[k]["both"] for k in res])) for nm in NM}
res["H1_weighted"] = tot
json.dump(res, open(sys.argv[1], "w"), indent=1)
print("H1", json.dumps(tot))
