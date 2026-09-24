#!/usr/bin/env python3
"""prefeat_full.py — BUILD bang gia tri 5 feature PASS (Stage 0) tren TOAN BO cua so train Stage 2.

Pre-reg: docs/prereg/PREREG_STAGE2_FEATVAR.md (commit dd27c6c).
Ket qua Stage 0: docs/result/RESULT_PRESCREEN_FEAT.md (commit d0809e0) — 5 feature PASS:
  rvol7d · mom30d · mom7d · daysSinceHigh30D · oi_delta7d

MUC DICH: cung cap 5 COT APPEND (idx 45..49) cho `g015_net_train_add.py --add-feats`.
Dinh nghia feature = COPY NGUYEN VAN `research/analysis/prescreen_build.py` (ban dong bang, d0809e0):
  `sliding_argmax_idx`, `build_coin_A`, cong thuc `oi_delta7d` — de "cung mot dinh nghia feature"
  giua vong do va vong train. KHONG sua prescreen_build.py.

KHAC BIET DUY NHAT so voi prescreen: (i) cua so = 2021-01-01..2026-01-01 (thay vi 3 quy DEV),
(ii) tap dong ra = DUNG cac dong NHAN ma trainer dung (nBars_4h >= 16 & retEnd_4h notna & ts < hi),
(iii) ghi parquet theo tung symbol.

THUAN PYTHON OFFLINE. Khong train, khong sim, khong cham 2026, khong push.
Ra: /tmp/prefeat2/prefeat_full.parquet  (ts, symId, rvol7d, mom30d, mom7d, daysSinceHigh30D, oi_delta7d)
"""
import os, sys, time, json, logging
import numpy as np, pandas as pd
from collections import deque
from multiprocessing import Pool

sys.path.insert(0, "/home/ubuntu/sel1m_code")
import funding_label_pb as FLPB

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("prefeatfull")

RAW = "/home/ubuntu/claudedata/rvb_1m/raw"
OI = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
LB_DIR = "/home/ubuntu/label_15m"
OUT = "/tmp/prefeat2"
os.makedirs(OUT, exist_ok=True)

M15 = 15
G0 = 26824320                     # 2021-01-01 00:00 UTC (phut)
HI_MS = 1767193200000             # = 2026-01-01T00:00Z - 7h = b_hi cua fold 20251001 (ms("20260101"))
NEED = 16
OI_PAD = 9 * 1440
DAYM = 1440
W7, W30, W90 = 672, 2880, 8640
OUT_COLS = ["rvol7d", "mom30d", "mom7d", "daysSinceHigh30D", "oi_delta7d"]   # = idx 45..49

DT1M = np.dtype([("t", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])
DT_OI = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])


def sliding_argmax_idx(a, W, minp):
    """index cua max trong cua so [i-W+1, i] (monotonic deque, O(n)). -1 neu thieu du lieu.
    COPY NGUYEN VAN tu prescreen_build.py (d0809e0)."""
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
    """COPY NGUYEN VAN tu prescreen_build.py (d0809e0), tru phan OI (tach ra ngoai)."""
    fp = os.path.join(RAW, sym + ".f32")
    a = np.fromfile(fp, dtype=DT1M)
    m = a["t"].astype(np.int64)
    lo = grid_min[0] - 1
    hi = grid_min[-1] + 15
    sel = (m >= lo) & (m <= hi)
    m = m[sel]; o = a["o"][sel].astype(np.float64); h = a["h"][sel].astype(np.float64)
    l = a["l"][sel].astype(np.float64); c = a["c"][sel].astype(np.float64); v = a["v"][sel].astype(np.float64)
    del a
    b = ((m + 14) // 15) * 15
    df = pd.DataFrame({"b": b, "o": o, "h": h, "l": l, "c": c, "v": v}).groupby("b").agg(
        h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum"))
    full = pd.Index(np.arange(grid_min[0], grid_min[-1] + 15, 15), name="b")
    df = df.reindex(full)
    c15, h15, l15 = df["c"], df["h"], df["l"]
    x = {}
    x["mom7d"] = (c15 / c15.shift(W7) - 1.0).values
    x["mom30d"] = (c15 / c15.shift(W30) - 1.0).values
    rmax30 = h15.rolling(W30, min_periods=W30 // 2).max()
    x["distFromHigh30D"] = (rmax30 - c15).div(rmax30).values
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
    x["_rvol7d_1h"] = lr.rolling(168, min_periods=84).std().values
    gmin = grid_min
    karr = (gmin - 59) // 60
    hidx = allk.values
    pos = np.searchsorted(hidx, karr)
    ok = (pos >= 0) & (pos < len(hidx)) & (hidx[np.clip(pos, 0, len(hidx) - 1)] == karr)
    out = np.full(len(gmin), np.nan)
    out[ok] = x["_rvol7d_1h"][pos[ok]]
    x["rvol7d"] = out
    am = sliding_argmax_idx(h15.values, W30, W30 // 2)
    x["daysSinceHigh30D"] = np.where(am >= 0, (np.arange(len(gmin)) - am) / 96.0, np.nan)
    return x


# ----------------------------- du lieu chia se (fork COW) -----------------------------
j_rows = None          # dict symId -> (ts array int64, positions in out array)
oi_by = None
i2s = None


def scan_labels():
    fs = sorted(f for f in os.listdir(LB_DIR)
                if f.startswith("funding_label_") and f.endswith(".pb")
                and f.split("_")[2] < "20260101")
    smap = pd.read_csv(MAP)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    ts_l, si_l = [], []
    tot = 0
    for fn in fs:
        d = FLPB.read_label(os.path.join(LB_DIR, fn),
                            usecols=["tEpochMs", "symbol", "retEnd_4h", "nBars_4h"])
        tot += len(d)
        d = d[(d["nBars_4h"] >= NEED) & d["retEnd_4h"].notna()]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        ts = d.tEpochMs.to_numpy(np.int64)[k]
        keep = ts < HI_MS
        ts_l.append(ts[keep]); si_l.append(sid[k].to_numpy(np.int32)[keep])
        del d
        log.info("  label %s rows=%d (tong doc=%d)", fn, int(keep.sum()), tot)
    ts = np.concatenate(ts_l); si = np.concatenate(si_l)
    log.info("LABEL: %d dong, %d symId, ts[%s..%s]", len(ts), len(np.unique(si)),
             pd.to_datetime(ts.min(), unit="ms"), pd.to_datetime(ts.max(), unit="ms"))
    ordr = np.lexsort((ts, si))
    ts, si = ts[ordr], si[ordr]
    key = si.astype(np.int64) * 10 ** 15 + ts
    assert not np.any(np.diff(key) == 0), "label trung (ts,symId)"
    del key, ordr
    return ts, si


def scan_oi(syms):
    lo_ms = int(G0) * 60000 - OI_PAD * 60000
    hi_ms = G0 * 60000 + (5 * 366 * 1440) * 60000
    need = set(syms)
    ao = np.memmap(OI, dtype=DT_OI, mode="r", shape=(os.path.getsize(OI) // DT_OI.itemsize,))
    ots, osym, ov = [], [], []
    CH = 20_000_000
    t0 = time.time()
    for s in range(0, len(ao), CH):
        c = np.array(ao[s:s + CH])
        msk = (c["ts"] >= lo_ms) & (c["ts"] < hi_ms)
        if not msk.any():
            continue
        c = c[msk]
        sm = set(np.unique(c["sym"]).tolist()) & need
        if not sm:
            continue
        keep = np.isin(c["sym"], list(sm))
        c = c[keep]
        ots.append((c["ts"].astype(np.int64) // 60000))
        osym.append(c["sym"].astype(np.int32))
        ov.append(c["oi"][:, 0].astype(np.float32))
        del c
    del ao
    ots = np.concatenate(ots); osym = np.concatenate(osym); ov = np.concatenate(ov)
    log.info("OI kept rows=%d (%.0fs)", len(ots), time.time() - t0)
    o = np.lexsort((ots, osym))
    ots, osym, ov = ots[o], osym[o], ov[o]
    b0 = np.searchsorted(osym, syms, "left"); b1 = np.searchsorted(osym, syms, "right")
    return {int(sd): (ots[a:b], ov[a:b]) for sd, a, b in zip(syms, b0, b1)}


def oi_feats(sid, grid_min):
    """oi_delta7d tren luoi 15m: prod_{k=0..6}(1+d24(t-24h*k))-1; COPY cong thuc prescreen_build.py."""
    ots, ov = oi_by[sid]
    if len(ots) == 0:
        return np.full(len(grid_min), np.nan)
    oi_start = grid_min[0] - OI_PAD
    d24 = pd.Series(ov.astype(np.float64), index=ots)
    d24 = d24[~d24.index.duplicated(keep="last")].sort_index()
    idx5 = pd.Index(np.arange(oi_start, grid_min[-1] + 5, 5), name="m")
    s5 = d24.reindex(idx5)
    prod = np.ones(len(idx5)); bad = np.zeros(len(idx5), bool)
    for k in range(7):
        vk = s5.shift(k * (DAYM // 5)).values
        prod = prod * (1.0 + np.nan_to_num(vk, nan=0.0))
        bad |= np.isnan(vk)
    o7 = prod - 1.0; o7[bad] = np.nan
    pos15 = ((grid_min - oi_start) // 5).astype(np.int64)
    return o7[pos15]


def work(sid):
    t0 = time.time()
    sym = i2s[sid]
    ts = j_rows[sid]
    g0 = G0
    g1 = int(ts.max() // 60000)
    g1 = ((g1 + 14) // 15) * 15
    grid = np.arange(g0, g1 + 15, 15, dtype=np.int64)
    x = build_coin_A(sym, grid, None)
    x["oi_delta7d"] = oi_feats(sid, grid)
    pos = np.searchsorted(grid, (ts // 60000).astype(np.int64))
    bad = (pos >= len(grid))
    ip = np.where(bad, 0, pos).astype(np.int64)
    out = {}
    for c in OUT_COLS:
        v = np.asarray(x[c], dtype=np.float64)[ip]
        v = np.where(bad | ~np.isfinite(v), np.nan, v)
        out[c] = v.astype(np.float32)
    del x
    return sid, ts, out, time.time() - t0


def main():
    global j_rows, oi_by, i2s
    t0 = time.time()
    smap = pd.read_csv(MAP)
    i2s = dict(zip(smap.symId.astype(np.int32), smap.symbol))
    ts, si = scan_labels()
    syms = [int(s) for s in np.unique(si) if int(s) in i2s]
    log.info("symbols co nhan: %d", len(syms))
    oi_by = scan_oi(syms)
    b0 = np.searchsorted(si, np.array(syms, np.int32), "left")
    b1 = np.searchsorted(si, np.array(syms, np.int32), "right")
    j_rows = {s: ts[a:b] for s, a, b in zip(syms, b0, b1)}
    assert sum(len(v) for v in j_rows.values()) == len(ts)
    del ts, si

    import pyarrow as pa, pyarrow.parquet as pq
    schema = pa.schema([("ts", pa.int64()), ("symId", pa.int16())] +
                       [(c, pa.float32()) for c in OUT_COLS])
    path = os.path.join(OUT, "prefeat_full.parquet")
    w = pq.ParquetWriter(path, schema, compression="zstd")
    n_tot = 0
    with Pool(int(os.environ.get("NPROC", "6"))) as p:
        for i, (sid, tsv, out, dt) in enumerate(p.imap_unordered(work, syms, chunksize=1)):
            cols = {"ts": pa.array(tsv, pa.int64()), "symId": pa.array(np.full(len(tsv), sid, np.int16))}
            for c in OUT_COLS:
                cols[c] = pa.array(out[c], pa.float32())
            w.write_table(pa.table(cols, schema=schema))
            n_tot += len(tsv)
            if i % 25 == 0:
                log.info("  %d/%d %s rows=%d tot=%d (%.0fs) last=%.1fs", i, len(syms), i2s[sid],
                         len(tsv), n_tot, time.time() - t0, dt)
    w.close()
    log.info("WROTE %s rows=%d (%.0fs)", path, n_tot, time.time() - t0)
    # kiem tra lai bang doc parquet
    d = pq.read_table(path, columns=["ts", "symId"] + OUT_COLS).to_pandas()
    log.info("VERIFY rows=%d cols=%s", len(d), list(d.columns))
    log.info("nan rate:\n%s", d[OUT_COLS].isna().mean().round(4).to_string())
    json.dump({"rows": int(len(d)), "cols": OUT_COLS, "hi_ms": HI_MS, "g0": G0,
               "nan_rate": {c: float(d[c].isna().mean()) for c in OUT_COLS},
               "ts_min": int(d.ts.min()), "ts_max": int(d.ts.max())},
              open(os.path.join(OUT, "prefeat_full.meta.json"), "w"), indent=1)
    log.info("DONE %.0fs", time.time() - t0)


if __name__ == "__main__":
    main()
