"""R5_SIGNAL_QUALITY kernel r5q-fwd (prereg 200a29a3 §2): Y_H(t) = TB deu ret_H tren ro top-24 sp tai phut t,
ret = close(t+1'+H)/close(t+1') - 1 - 0,002, gia = ban ghi cuoi <= moc cach <= 5'. Can >= 12 coin. Vector hoa theo thang.
Input: dataset r5q-basket (r5q_basket.parquet, r5q_symmap.csv), vz-kline1m-2022..2026. Output /kaggle/working/r5q_y.parquet."""
import glob
import json
import logging
import time
import warnings

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

warnings.filterwarnings("ignore", category=RuntimeWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("r5k")
M1, FEE, MINC = 60000, 0.002, 12
HS = {"24": 86400000, "72": 3 * 86400000}
bp = glob.glob("/kaggle/input/**/r5q_basket.parquet", recursive=True)
sp = glob.glob("/kaggle/input/**/r5q_symmap.csv", recursive=True)
assert bp and sp, "thieu input"
BK = pd.read_parquet(bp[0])
SM = pd.read_csv(sp[0])
sid2sym = dict(zip(SM.sid.astype(int), SM.sym.astype(str)))
F = {p.split("kline1m-")[-1][:7]: p for p in glob.glob("/kaggle/input/**/kline1m-*.parquet", recursive=True)}
log.info("phut %d thang kline %d %s..%s", len(BK), len(F), min(F), max(F))
syms = sorted(set(sid2sym.values()))
code = {s: i for i, s in enumerate(syms)}
SH = np.int64(1) << 42
cols = ["b%d" % j for j in range(24)]
sid_code = np.full(max(sid2sym) + 2, -1, np.int64)
for k, v in sid2sym.items():
    sid_code[k] = code[v]
cache = {}


def month(k):
    if k in cache:
        return cache[k]
    if k not in F:
        cache[k] = None
        return None
    t = pq.read_table(F[k], columns=["ts", "sym", "close"])
    c = t.column("sym").combine_chunks()
    if not pa.types.is_dictionary(c.type):
        c = c.dictionary_encode()
    lut = np.array([code.get(str(x), -1) for x in c.dictionary.to_pylist()], np.int64)
    sy = lut[c.indices.to_numpy(zero_copy_only=False).astype(np.int64)]
    ts = t.column("ts").to_numpy().astype(np.int64)
    cl = t.column("close").to_numpy().astype(np.float64)
    ok = sy >= 0
    cache[k] = (sy[ok], ts[ok], cl[ok])
    return cache[k]


BK["ym"] = pd.to_datetime(BK.ts, unit="ms").dt.strftime("%Y-%m")
out = []
t0 = time.time()
for ym, g in BK.groupby("ym", sort=True):
    y, m = int(ym[:4]), int(ym[5:])
    nx = "%04d-%02d" % (y + (m == 12), 1 if m == 12 else m + 1)
    parts = [x for x in (month(ym), month(nx)) if x is not None]
    sy = np.concatenate([p[0] for p in parts])
    ts = np.concatenate([p[1] for p in parts])
    cl = np.concatenate([p[2] for p in parts])
    key = sy * SH + ts
    o = np.argsort(key, kind="stable")
    key, cl = key[o], cl[o]
    _, last = np.unique(key[::-1], return_index=True)
    keep = len(key) - 1 - last
    key, cl = key[keep], cl[keep]
    S = g[cols].to_numpy().astype(np.int64)
    T = g.ts.to_numpy().astype(np.int64)
    cc = np.where(S >= 0, sid_code[np.clip(S, 0, len(sid_code) - 1)], -1)
    valid = cc >= 0
    tq = np.broadcast_to(T[:, None], S.shape)

    def px(off):
        q = cc * SH + tq + off
        j = np.searchsorted(key, q.ravel(), "right").reshape(q.shape) - 1
        jj = np.clip(j, 0, len(key) - 1)
        same = (j >= 0) & ((key[jj] // SH) == cc) & ((q - key[jj]) <= 5 * M1) & valid
        return np.where(same, cl[jj], np.nan)
    c0 = px(M1)
    res = dict(ts=T)
    for hk, hv in HS.items():
        r = px(M1 + hv) / c0 - 1.0 - FEE
        n = np.isfinite(r).sum(1)
        res["y" + hk] = np.where(n >= MINC, np.nanmean(r, axis=1), np.nan)
        res["n" + hk] = n
    out.append(pd.DataFrame(res))
    for k in list(cache):
        if k != nx:
            del cache[k]
    log.info("%s phut %d nanY72 %d %ds", ym, len(g), int(np.isnan(res["y72"]).sum()), round(time.time() - t0))
R = pd.concat(out, ignore_index=True)
R.to_parquet("/kaggle/working/r5q_y.parquet", index=False)
json.dump(dict(n=len(R), nan72=int(R.y72.isna().sum()), nan24=int(R.y24.isna().sum())), open("/kaggle/working/r5q_meta.json", "w"))
log.info("R5Q_DONE %d", len(R))
