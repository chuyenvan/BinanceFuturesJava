#!/usr/bin/env python3
"""IND_COMBO P0 tu kiem causal: 20 leg DEV ngau nhien (seed 20261114). Tinh TAY tu nen 1h tho CAT tai gio dong <= M:
RSI14 1h (C1), Stoch %K14 4h (C5), close/SMA50-1 1d (C16). So voi legs_x. Khong doc Y."""
import json
import logging
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("cc")
H, D4, DAY = 3600000, 4 * 3600000, 86400000
L = pd.read_parquet("/home/ubuntu/claude_master/ind1114/legs_x.parquet", columns=["seed", "sym", "M", "per", "C1", "C5", "C16"])
L = L[L.per != "H"].reset_index(drop=True)
rng = np.random.default_rng(20261114)
pick = L.iloc[rng.choice(len(L), 20, replace=False)]
dt = np.dtype([("t", ">i8"), ("s", ">i2"), ("o", ">f4"), ("h", ">f4"), ("l", ">f4"), ("c", ">f4"), ("v", ">f4")])
a = np.fromfile("/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin", dtype=dt)
mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
s2id = dict(zip(mp.symbol.astype(str), mp.symId.astype(int)))
res, bad = [], 0
for _, r in pick.iterrows():
    M = int(r.M)
    sid = s2id[r.sym]
    x = a[(a["s"] == sid)]
    t = x["t"].astype(np.int64)
    keep = t <= M                      # CHI nen da dong truoc/tai phut vao
    t = t[keep]
    o, h, l, c = (x[k][keep].astype(np.float32).astype(np.float64) for k in ("o", "h", "l", "c"))
    last_close = int(t.max())
    # luoi gio day du + ffill (cung quy uoc build)
    full = np.arange(t.min(), t.max() + H, H)
    pos = np.searchsorted(full, t)
    C = np.full(len(full), np.nan); O = C.copy(); Hh = C.copy(); Lw = C.copy()
    C[pos], O[pos], Hh[pos], Lw[pos] = c, o, h, l
    for i in range(1, len(full)):
        if np.isnan(C[i]):
            C[i] = C[i - 1]; O[i] = Hh[i] = Lw[i] = C[i]
    # RSI14 Wilder vong lap tay
    au = ad = 0.0
    for i in range(1, len(C)):
        d = C[i] - C[i - 1]
        g, ls = max(d, 0.0), max(-d, 0.0)
        if i == 1:
            au, ad = g, ls
        else:
            au += (g - au) / 14; ad += (ls - ad) / 14
    rsi = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    if len(C) <= 42:
        rsi = np.nan
    # 4h: nhom gio dong (k*4h, (k+1)*4h], chi nhom du 4 gio
    k4 = (full - 1) // D4
    b4 = []
    for k in np.unique(k4):
        m = k4 == k
        if m.sum() == 4:
            b4.append((Hh[m].max(), Lw[m].min(), C[m][-1]))
    b4 = np.array(b4[-14:])
    st = 100 * (b4[-1, 2] - b4[:, 1].min()) / (b4[:, 0].max() - b4[:, 1].min()) if len(b4) == 14 else np.nan
    kd = (full - 1) // DAY
    dc = [C[kd == k][-1] for k in np.unique(kd) if (kd == k).sum() == 24]
    sma = (dc[-1] / np.mean(dc[-50:]) - 1) if len(dc) >= 50 else np.nan
    ok = all((np.isnan(u) and np.isnan(v)) or abs(u - v) <= 1e-6 * max(1, abs(u)) for u, v in ((rsi, r.C1), (st, r.C5), (sma, r.C16)))
    bad += (not ok)
    res.append(dict(sym=r.sym, M=M, last_bar_close=last_close, lag_min=(M - last_close) / 60000, c1=(round(rsi, 6), round(r.C1, 6)),
                    c5=(round(st, 6) if st == st else None, round(r.C5, 6) if r.C5 == r.C5 else None),
                    c16=(round(sma, 8) if sma == sma else None, round(r.C16, 8) if r.C16 == r.C16 else None), ok=ok))
for x in res:
    log.info("%s", x)
assert all(0 <= x["lag_min"] < 60 for x in res), "nen cuoi khong nam trong 60' truoc M"
json.dump(dict(n=len(res), bad=bad, rows=res), open("/home/ubuntu/claude_master/ind1114/causal_chk.json", "w"), indent=1, default=str)
log.info("CAUSAL n=%d bad=%d", len(res), bad)
