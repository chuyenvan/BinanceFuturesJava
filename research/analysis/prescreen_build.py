#!/usr/bin/env python3
"""PRESCREEN Stage 0 — BUILD feature moi (nhom A coin-level + OI) tren luoi 15m.
Pre-reg: docs/prereg/PREREG_PRESCREEN_FEAT.md (commit 6695a8c). THUAN PYTHON OFFLINE.
Nguon: /home/ubuntu/claudedata/rvb_1m/raw/<SYM>.f32 (1m OHLCV) + oi_percoin_full.bin.
Ra: /tmp/prefeat/A.parquet (ts, symId, <feature>). Khong train, khong sim.
"""
import os, sys, time, json, logging
import numpy as np, pandas as pd
from collections import deque

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("buildA")

RAW = "/home/ubuntu/claudedata/rvb_1m/raw"
OI = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
JOINED = "/tmp/evfeat/joined.parquet"
OUT = "/tmp/prefeat"; os.makedirs(OUT, exist_ok=True)

M15 = 15            # phut
GRID0 = 1646092800000      # 2022-03-01 00:00 UTC
GRID1 = 1719792000000      # 2024-07-01 00:00 UTC
OI_PAD = 9 * 1440          # 9 ngay warmup cho oi_delta7d/oiPersistence
DAYM = 1440
W7, W30, W90 = 672, 2880, 8640      # so nen 15m

DT1M = np.dtype([("t", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])
DT_OI = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])


def load_joined():
    j = pd.read_parquet(JOINED, columns=["ts", "symId"])
    return j


def sliding_argmax_idx(a, W, minp):
    """index cua max trong cua so [i-W+1, i] (monotonic deque, O(n)). -1 neu thieu du lieu."""
    n = len(a)
    out = np.full(n, -1, dtype=np.int64)
    dq = deque()
    run_valid = 0
    for i in range(n):
        x = a[i]
        if np.isnan(x):
            run_valid = 0
            dq.clear()
            continue
        run_valid += 1
        while dq and a[dq[-1]] <= x:
            dq.pop()
        dq.append(i)
        while dq[0] <= i - W:
            dq.popleft()
        if run_valid >= minp:
            out[i] = dq[0]
    return out


def build_coin_A(sym, grid_min, tick_min):
    """Tra ve dict ten->array gia tri tai cac tick_min (phut) cua symbol."""
    fp = os.path.join(RAW, sym + ".f32")
    a = np.fromfile(fp, dtype=DT1M)
    m = a["t"].astype(np.int64)
    lo = grid_min[0] - 1
    hi = grid_min[-1] + 15
    sel = (m >= lo) & (m <= hi)
    m = m[sel]; o = a["o"][sel].astype(np.float64); h = a["h"][sel].astype(np.float64)
    l = a["l"][sel].astype(np.float64); c = a["c"][sel].astype(np.float64); v = a["v"][sel].astype(np.float64)
    # bucket 15m: bucket b phu (b-14..b), close = c[b]
    b = ((m + 14) // 15) * 15
    df = pd.DataFrame({"b": b, "o": o, "h": h, "l": l, "c": c, "v": v}).groupby("b").agg(
        h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum"))
    full = pd.Index(np.arange(grid_min[0], grid_min[-1] + 15, 15), name="b")
    df = df.reindex(full)
    c15, h15, l15, v15 = df["c"], df["h"], df["l"], df["v"]
    x = {}
    x["mom7d"] = (c15 / c15.shift(W7) - 1.0).values
    x["mom30d"] = (c15 / c15.shift(W30) - 1.0).values
    rmax30 = h15.rolling(W30, min_periods=W30 // 2).max()
    rmax90 = h15.rolling(W90, min_periods=W90 // 2).max()
    x["distFromHigh30D"] = (rmax30 - c15) .div(rmax30).values
    x["distFromHigh90D"] = (rmax90 - c15).div(rmax90).values
    rmin7 = l15.rolling(W7, min_periods=W7 // 2).min()
    rmax7 = h15.rolling(W7, min_periods=W7 // 2).max()
    x["rangePosition7D"] = ((c15 - rmin7) / (rmax7 - rmin7)).values
    rng = (h15 - l15)
    m1 = rng.rolling(96, min_periods=48).mean()
    m7 = rng.rolling(W7, min_periods=W7 // 2).mean()
    x["squeezeLong"] = (m1 / m7).values
    # --- 1h bars: o1h = o[60k], c1h = c[60k+59] ---
    hm = m // 60
    isopen = (m % 60) == 0
    isclose = (m % 60) == 59
    ho = pd.Series(o[isopen], index=hm[isopen])
    hc = pd.Series(c[isclose], index=hm[isclose])
    ho = ho[~ho.index.duplicated(keep="last")].sort_index()
    hc = hc[~hc.index.duplicated(keep="last")].sort_index()
    allk = pd.Index(np.arange(grid_min[0] // 60 - 1, grid_min[-1] // 60 + 2), name="k")
    ho = ho.reindex(allk); hc = hc.reindex(allk)
    lr = np.log(hc / hc.shift(1))
    x["rvol7d"] = lr.rolling(168, min_periods=84).std().values
    x["trendConsistency7d"] = (hc > ho).astype(float).where(hc.notna() & ho.notna()).rolling(168, min_periods=84).mean().values
    # map 1h -> 15m grid: k_max(m) = (m-59)//60
    gmin = grid_min
    karr = (gmin - 59) // 60
    hidx = allk.values
    pos = np.searchsorted(hidx, karr)
    ok = (pos >= 0) & (pos < len(hidx)) & (hidx[np.clip(pos, 0, len(hidx) - 1)] == karr)
    for k, name in (("rvol7d", "rvol7d"), ("trendConsistency7d", "trendConsistency7d")):
        arr = x[k]
        out = np.full(len(gmin), np.nan)
        out[ok] = arr[pos[ok]]
        x[name + "_g"] = out
    x["rvol7d"] = x.pop("rvol7d_g"); x["trendConsistency7d"] = x.pop("trendConsistency7d_g")
    # days since 30d high
    am = sliding_argmax_idx(h15.values, W30, W30 // 2)
    x["daysSinceHigh30D"] = np.where(am >= 0, (np.arange(len(gmin)) - am) / 96.0, np.nan)
    # --- OI: da co san trong dict oi_sym ---
    return x


def main():
    t0 = time.time()
    j = load_joined()
    m = pd.read_csv(MAP)
    i2s = dict(zip(m.symId, m.symbol))
    syms = sorted(j.symId.unique())
    _lim = int(os.environ.get("LIMIT", "0"))
    if _lim:
        syms = syms[:_lim]
    log.info("joined rows=%d syms=%d ts[%s..%s]", len(j), len(syms),
             pd.to_datetime(j.ts.min(), unit="ms"), pd.to_datetime(j.ts.max(), unit="ms"))
    grid_min = np.arange(GRID0 // 60000, GRID1 // 60000 + 1, 15).astype(np.int64)
    gmap = pd.Series(np.arange(len(grid_min)), index=grid_min)
    # tick minutes per symbol + vi tri dong trong joined
    j["_m"] = (j.ts.values // 60000).astype(np.int64)
    order = {}
    featA = {}
    for sid in syms:
        sub = j.index[j.symId.values == sid]
        order[sid] = sub.values
    # ---- OI: mot lan quet ----
    log.info("scan OI ...")
    need = set(syms)
    lo_ms = GRID0 - OI_PAD * 60000
    ao = np.memmap(OI, dtype=DT_OI, mode="r", shape=(os.path.getsize(OI) // DT_OI.itemsize,))
    oi_ts, oi_sym, oi_v = [], [], []
    CH = 20_000_000
    for s in range(0, len(ao), CH):
        c = np.array(ao[s:s + CH])
        msk = (c["ts"] >= lo_ms) & (c["ts"] < GRID1 + 86400000)
        if not msk.any():
            continue
        c = c[msk]
        sm = set(np.unique(c["sym"]).tolist())
        sm &= need
        if not sm:
            continue
        keep = np.isin(c["sym"], list(sm))
        c = c[keep]
        oi_ts.append((c["ts"].astype(np.int64) // 60000).astype(np.int64))
        oi_sym.append(c["sym"].astype(np.int32))
        oi_v.append(c["oi"][:, 0].astype(np.float32))
        del c
        log.info("  OI scanned %d/%d rows kept=%d (%.0fs)", s, len(ao), sum(len(x) for x in oi_ts), time.time() - t0)
    oi_ts = np.concatenate(oi_ts); oi_sym = np.concatenate(oi_sym); oi_v = np.concatenate(oi_v)
    log.info("OI kept rows=%d (%.0fs)", len(oi_ts), time.time() - t0)
    ord_s = np.argsort(oi_sym.astype(np.int64) * (10 ** 9) + oi_ts, kind="stable")
    oi_ts, oi_sym, oi_v = oi_ts[ord_s], oi_sym[ord_s], oi_v[ord_s]
    bnd = np.searchsorted(oi_sym, syms, side="left"), np.searchsorted(oi_sym, syms, side="right")
    oi_by = {sid: (oi_ts[b0:b1], oi_v[b0:b1]) for sid, b0, b1 in zip(syms, bnd[0], bnd[1])}
    del ao
    log.info("OI indexed (%.0fs)", time.time() - t0)

    allf = {}
    for n, sid in enumerate(syms):
        sym = i2s[sid]
        x = build_coin_A(sym, grid_min, None)
        # OI features tren luoi 5m (phut)
        ots, ov = oi_by[sid]
        oi_start = grid_min[0] - OI_PAD
        if len(ots) == 0:
            x["oi_delta7d"] = np.full(len(grid_min), np.nan)
            x["oiPersistence"] = np.full(len(grid_min), np.nan)
        else:
            d24 = pd.Series(ov.astype(np.float64), index=ots)
            d24 = d24[~d24.index.duplicated(keep="last")].sort_index()
            idx5 = pd.Index(np.arange(oi_start, grid_min[-1] + 5, 5), name="m")
            s = d24.reindex(idx5)                       # luoi 5m day du (thieu -> NaN)
            sv = s.values
            pos15 = ((grid_min - oi_start) // 5).astype(np.int64)   # 15m grid -> vi tri luoi 5m
            # dong nhat: prod_{k=0..6}(1+d24(t-24h*k)) - 1  (288 buoc 5m = 1440 phut)
            prod = np.ones(len(idx5)); bad = np.zeros(len(idx5), bool)
            for k in range(7):
                v = s.shift(k * (DAYM // 5)).values
                prod = prod * (1.0 + np.nan_to_num(v, nan=0.0))
                bad |= np.isnan(v)
            o7 = prod - 1.0; o7[bad] = np.nan
            # oiPersistence: so ky 24h LIEN TIEP gan nhat co d24>0 (cap 8)
            per = np.zeros(len(idx5)); run = np.ones(len(idx5), bool)
            for k in range(8):
                run = run & (s.shift(k * (DAYM // 5)).values > 0)
                per += run.astype(float)
            per[np.isnan(sv)] = np.nan
            x["oi_delta7d"] = o7[pos15]
            x["oiPersistence"] = per[pos15]
        # lay gia tri tai tick cua symbol
        pos = gmap.reindex(j["_m"].values[order[sid]]).values
        bad = np.isnan(pos)
        ipos = np.where(bad, 0, pos).astype(np.int64)
        for k, arr in x.items():
            if k not in allf:
                allf[k] = np.full(len(j), np.nan, dtype=np.float64)
            vals = np.asarray(arr, dtype=np.float64)[ipos]
            vals = np.where(bad | ~np.isfinite(vals), np.nan, vals)
            allf[k][order[sid]] = vals
        if n % 25 == 0:
            log.info(" coin %d/%d %s (%.0fs)", n, len(syms), sym, time.time() - t0)
    df = pd.DataFrame({"ts": j.ts.values, "symId": j.symId.values})
    for k, v in allf.items():
        df[k] = v.astype(np.float32)
    df.to_parquet(os.path.join(OUT, "A.parquet"), index=False)
    log.info("WROTE A.parquet rows=%d cols=%d (%.0fs)", len(df), len(df.columns), time.time() - t0)
    log.info("nan rate:\n%s", df.drop(columns=["ts", "symId"]).isna().mean().round(4).to_string())


if __name__ == "__main__":
    main()
