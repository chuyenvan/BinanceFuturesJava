#!/usr/bin/env python3
"""HO3b chan doan oi_z tren DEV (2025-12-29..31): tim moc bat dau expanding khop file ghim. Chi DEV."""
import json, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import ho3b_oi_rebuild as M
sym, sid = sys.argv[1], int(sys.argv[2])
dates = M.list_dates(sym)
with ThreadPoolExecutor(16) as ex:
    rs = list(ex.map(lambda d: M.parse_day(sym, d), dates))
T = np.concatenate([r[0] for r in rs if r]); V = np.concatenate([r[1][:, 0] for r in rs if r])
ok = ~np.isnan(V); T, V = T[ok], V[ok]
u, i0 = np.unique(T[::-1], return_index=True); v = V[::-1][i0]
ODT = M.ODT
P = []
n = 140924110
LO, HI = M.EMIT_LO, int(pd.Timestamp("2026-01-01", tz="UTC").value // 10**6)
for k in range(0, n, 10_000_000):
    c = np.fromfile("/home/ubuntu/claudedata/oi/oi_percoin_full.bin", dtype=ODT, count=min(10_000_000, n - k), offset=k * 30)
    m = (c["sym"] == sid) & (c["ts"] >= LO) & (c["ts"] < HI)
    P.append(c[m].copy())
P = np.concatenate(P)
# moc dau tien cua file ghim cho symbol nay
first_pin = None
for k in range(0, n, 10_000_000):
    c = np.fromfile("/home/ubuntu/claudedata/oi/oi_percoin_full.bin", dtype=ODT, count=min(10_000_000, n - k), offset=k * 30)
    m = c["sym"] == sid
    if m.any():
        first_pin = int(c["ts"][m].min()); break
res = dict(first_vision=dates[0], first_pin=str(pd.to_datetime(first_pin, unit="ms")), n_hist=int(len(u)))
pt = P["ts"].astype(np.int64); pz = P["oi"][:, 1].astype(np.float32)
for lab, s0 in [("all", None), ("pin_first", first_pin), ("2021-01-01 07+07", int(pd.Timestamp("2021-01-01").value // 10**6))]:
    m = np.ones(len(u), bool) if s0 is None else (u >= s0)
    uu, vv = u[m], v[m].astype(np.float64)
    s1, s2 = np.cumsum(vv), np.cumsum(vv * vv); nn = np.arange(1, len(uu) + 1)
    j = np.searchsorted(uu, pt)
    ok = (j < len(uu)) & (uu[np.clip(j, 0, len(uu) - 1)] == pt)
    jj = np.clip(j, 0, len(uu) - 1)
    mean = s1[jj] / nn[jj]; var = (s2[jj] - s1[jj] ** 2 / nn[jj]) / (nn[jj] - 1)
    z = ((vv[jj] - mean) / np.sqrt(var)).astype(np.float32)
    res[lab] = dict(eq=float(((z == pz) & ok).mean()), maxrel=float(np.nanmax(np.abs(z - pz) / np.maximum(np.abs(pz), 1e-9))),
                    n_at_t=int(nn[jj][0]))
print(json.dumps(res, indent=1))
