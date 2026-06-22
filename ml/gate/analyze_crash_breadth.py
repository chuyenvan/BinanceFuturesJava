#!/usr/bin/env python3
"""
TASK-041 A0 (v2 - BREADTH): cú sập THỊ TRƯỜNG RỘNG, không phải BTC/ETH.
Tại mỗi mốc t: breadth(t) = % coin có maxAdv_H <= -X (sẽ giảm >=X% trong H giờ tới).
"cú sập rộng" = mốc breadth(t) >= B. Đếm số mốc-sập độc lập (de-overlap theo H).

Dùng label CSV (đã có maxAdv per-coin per-ts). Quét lưới (H, X, B).
Env: LABEL (mac dinh /d/claudedata/funding_label.csv); neu chi co theo thang -> truyen glob.
"""
import os, glob
import numpy as np
import pandas as pd

LABEL = os.environ.get("LABEL", "/d/claudedata/funding_label.csv")
STEP = 15 * 60 * 1000
HS = {"4h": 16, "12h": 48, "24h": 96}
XS = [0.10, 0.15, 0.20]
BS = [0.30, 0.50, 0.70]   # nguong breadth: 30/50/70% coin cung giam
MIN_INDEP = 30

files = sorted(glob.glob(LABEL)) if any(c in LABEL for c in "*?[") else [LABEL]
print(f"doc {len(files)} file label...")

for Hname, steps in HS.items():
    Hms = steps * STEP
    col = f"maxAdv_{Hname}"
    # gom breadth theo ts: voi moi X, dem coin maxAdv<=-X / tong coin co maxAdv
    # doc tung file, chunk de nhe RAM
    cnt = {X: {} for X in XS}   # X -> {ts: [n_crash, n_total]}
    for fp in files:
        for ch in pd.read_csv(fp, usecols=["tEpochMs", col], chunksize=2_000_000):
            ch = ch.dropna(subset=[col])
            ts = ch["tEpochMs"].values
            adv = ch[col].values
            for X in XS:
                crash = adv <= -X
                # gom theo ts
                d = cnt[X]
                # vectorized bincount kho vi ts thua -> groupby
                g = pd.DataFrame({"ts": ts, "c": crash.astype(int)}).groupby("ts")["c"].agg(s="sum", n="count")
                for t, s, n in zip(g.index.values, g["s"].values, g["n"].values):
                    if t in d:
                        d[t][0] += int(s); d[t][1] += int(n)
                    else:
                        d[t] = [int(s), int(n)]
    for X in XS:
        d = cnt[X]
        tss = np.array(sorted(d))
        breadth = np.array([d[t][0] / d[t][1] if d[t][1] > 0 else 0 for t in tss])
        for B in BS:
            crash_ts = tss[breadth >= B]
            indep, last = 0, -10**18
            for t in crash_ts:
                if t > last + Hms:
                    indep += 1; last = t
            pct = 100 * len(crash_ts) / max(1, len(tss))
            v = "OK" if indep >= MIN_INDEP else "THIN"
            print(f"H={Hname:>3} X={int(X*100):>2}% B={int(B*100):>2}%  mocs-sap={len(crash_ts):>6}  indep={indep:>4}  %time={pct:>5.2f}  {v}")
print(f"\n(n_indep>={MIN_INDEP} moi du mau train)")
