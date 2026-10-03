#!/usr/bin/env python3
"""label_firsthit_build.py — LABEL_FIRSTHIT (docs/prereg/PREREG_LABEL_FIRSTHIT.md): sinh nhan first-hit FLAT3.

Nhan tai tick ts (luoi 15', UTC ms = tEpochMs cua ds_label15m):
  entry  P = close nen 1m MO tai ts (nen ke tick, dong luc ts+1').
  duong  nen 1m mo tai ts+1' .. ts+10080' (168h ke tu close entry), high/low 1m.
  arm    = high >= 1.07 P ; sl = low <= 0.90 P. First-hit theo phut.
  cung phut cham ca hai (tie) => SL (bi quan), y=0, hit=3.
  khong cham trong 168h => y = 1[ret168 > 0], ret168 = close hop le cuoi trong cua so / P - 1.
  nen vol<=0 hoac gia <=0 = KHONG HOP LE (phut ma sau delist, DATA_AUDIT 1003) => bo qua (khong cham).
  entry khong hop le / khong co nen hop le nao sau entry / cua so vuot 2025-12-31 23:59 => NaN (bo).
Nguon: Aerospike test.kline_1m_opt (stream 1 luot theo thang UTC + 10080' fwd). DEV <= 2025-12-31.
Ra: OUT/fh_YYYYMM.parquet (ts int64 ms, symId int16, y int8, hit int8 [0 none,1 arm,2 sl,3 tie],
    khit int16 phut, ret168 float32, P float32) + meta_YYYYMM.json.
Chay: python3 label_firsthit_build.py --months 202101-202512 --procs 3 [--probe-days 2]
"""
import argparse, json, logging, os, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
OUT = os.environ.get("FH_OUT", "/home/ubuntu/claude_master/1003/fh/labels")
MAP_CSV = "/home/ubuntu/claudedata/oi/symbol_map.csv"
MIN = 60000
DEV_M1 = 1767225600000 // MIN - 1      # 2025-12-31 23:59 UTC (phut cuoi duoc doc)
HZ = 10080                             # 168h
ARM, SL = 1.07, 0.90
GRID = 15
KLV = 14                               # 2^13 = 8192 < 10080 < 16384
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT"}
log = logging.getLogger("fh")


def setup_log():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(process)d %(levelname)s %(message)s")


def key_of(m):
    """phut UTC m (gio mo) -> key Aerospike TZ+7 (y het short_v3_r1_fade.key_of)."""
    return time.strftime("%Y%m%d-%H%M", time.gmtime(m * 60 + 7 * 3600))


def stream(b0, b1, tag):
    """Doc phut b0..b1 (UTC) -> H, L, C (N,S) float32 (khong hop le = NaN), names."""
    import aerospike, cramjam
    from short_pathexit_sim import parse_min
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    N = b1 - b0 + 1
    cap = 640
    arr = np.full((4, N, cap), np.nan, np.float32)   # H L C V
    names = {}
    t0 = time.time(); nrec = 0
    for d0 in range(b0, b1 + 1, 1440):
        ms = list(range(d0, min(d0 + 1440, b1 + 1)))
        keys = [("test", "kline_1m_opt", key_of(m)) for m in ms]
        brs = None
        for _att in range(3):
            try:
                brs = cli.batch_read(keys).batch_records
                break
            except Exception as e:
                log.warning("%s batch_read loi %s, thu lai", tag, e); time.sleep(5)
        if brs is None:
            raise RuntimeError("batch_read that bai")
        for k, rr in enumerate(brs):
            if rr.result != 0 or rr.record is None:
                continue
            bins = rr.record[2]
            if not bins or "data" not in bins:
                continue
            d = parse_min(bytes(dec(bins["data"])))
            rows = []; vals = []
            for nm, v in d.items():
                if nm in STABLE:
                    continue
                r = names.get(nm)
                if r is None:
                    r = len(names); names[nm] = r
                rows.append(r); vals.append((v[1], v[2], v[3], v[4]))   # O H L C V -> H L C V
            if len(names) > cap:
                cap2 = len(names) + 128
                a2 = np.full((4, N, cap2), np.nan, np.float32)
                a2[:, :, :cap] = arr
                arr = a2; cap = cap2
            if rows:
                arr[:, ms[k] - b0, rows] = np.asarray(vals, np.float32).T
                nrec += 1
    cli.close()
    S = len(names)
    arr = np.ascontiguousarray(arr[:, :, :S])
    H, L, C, V = arr
    bad = ~((V > 0) & (H > 0) & (L > 0) & (C > 0))
    H[bad] = np.nan; L[bad] = np.nan; C[bad] = np.nan
    log.info("%s stream %d phut nrec=%d nsym=%d bad=%.4f %.0fs", tag, N, nrec, S, float(bad.mean()), time.time() - t0)
    return H, L, C, [n for n, _ in sorted(names.items(), key=lambda z: z[1])], nrec


def build_st(A):
    """Sparse table range-max: st[k][i] = max A[i : i+2^k] (day du khi i+2^k <= N)."""
    N = A.shape[0]
    st = [A]
    for k in range(1, KLV):
        h = 1 << (k - 1)
        prev = st[-1]
        cur = np.full_like(prev, -np.inf)
        if N > h:
            cur[:N - h] = np.maximum(prev[:N - h], prev[h:])
        st.append(cur)
    return st


def first_ge(st, starts, ends, cols, thr):
    """Vi tri dau tien p in [start, end] voi A[p] >= thr (binary lifting); khong co -> -1."""
    A = st[0]
    N = A.shape[0]
    pos = starts.copy()
    for k in range(KLV - 1, -1, -1):
        step = 1 << k
        ok = (pos + step - 1) <= ends
        v = st[k][np.minimum(pos, N - 1), cols]
        pos = pos + step * (ok & (v < thr))
    hit = (pos <= ends) & (A[np.minimum(pos, N - 1), cols] >= thr)
    return np.where(hit, pos, -1)


def month_ticks(ym):
    y, mo = divmod(ym, 100)
    s0 = pd.Timestamp(year=y, month=mo, day=1, tz="UTC")
    s1 = s0 + pd.offsets.MonthBegin(1)
    m_lo = int(s0.value // 10 ** 9 // 60)
    m_hi = int(s1.value // 10 ** 9 // 60) - 1
    m_hi = min(m_hi, DEV_M1)
    t0 = ((m_lo + GRID - 1) // GRID) * GRID
    return np.arange(t0, m_hi + 1, GRID, dtype=np.int64), m_lo, m_hi


def label_month(args):
    ym, probe_days = args
    setup_log()
    t00 = time.time()
    ticks, m_lo, m_hi = month_ticks(ym)
    if probe_days:
        ticks = ticks[ticks < m_lo + probe_days * 1440]
    b0 = int(ticks[0]); b1 = min(int(ticks[-1]) + HZ, DEV_M1)
    H, L, C, names, nrec = stream(b0, b1, str(ym))
    N, S = C.shape
    smap = pd.read_csv(MAP_CSV)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int64)))
    sid = np.array([s2i.get(n, -1) for n in names], np.int64)
    # chi so phut hop le cuoi <= i (de lay close cuoi cua so); -1 neu chua co
    idx = np.where(np.isfinite(C), np.arange(N)[:, None], -1)
    LV = np.maximum.accumulate(idx, axis=0)
    del idx
    e_all = ticks - b0                                   # chi so nen entry (mo tai ts)
    parts = []
    n_trunc = 0
    for c0 in range(0, S, 64):
        c1 = min(c0 + 64, S)
        Hc = np.where(np.isfinite(H[:, c0:c1]), H[:, c0:c1], -np.inf).astype(np.float32)
        Lc = np.where(np.isfinite(L[:, c0:c1]), -L[:, c0:c1], -np.inf).astype(np.float32)
        stH = build_st(Hc); stL = build_st(Lc)
        ee, cc = np.meshgrid(e_all, np.arange(c1 - c0), indexing="ij")
        ee = ee.ravel(); cc = cc.ravel()
        P = C[ee, cc + c0]
        ok = np.isfinite(P) & (sid[cc + c0] > 0)
        ends = ee + HZ
        trunc = ok & (ends > N - 1)
        n_trunc += int(trunc.sum())
        ok &= ~trunc
        ee, cc, P, ends = ee[ok], cc[ok], P[ok].astype(np.float64), ends[ok]
        lv = LV[ends, cc + c0]
        has = lv >= ee + 1
        ee, cc, P, ends, lv = ee[has], cc[has], P[has], ends[has], lv[has]
        ka = first_ge(stH, ee + 1, ends, cc, (ARM * P).astype(np.float32))
        ks = first_ge(stL, ee + 1, ends, cc, (-SL * P).astype(np.float32))
        del stH, stL, Hc, Lc
        ret = (C[lv, cc + c0].astype(np.float64) / P - 1.0)
        a_ = ka >= 0; s_ = ks >= 0
        tie = a_ & s_ & (ka == ks)
        armf = a_ & (~s_ | (ka < ks))
        slf = s_ & (~a_ | (ks < ka))
        hit = np.zeros(len(ee), np.int8)
        hit[armf] = 1; hit[slf] = 2; hit[tie] = 3
        y = np.where(hit == 1, 1, np.where(hit == 0, (ret > 0).astype(np.int8), 0)).astype(np.int8)
        kh = np.where(hit == 1, ka, np.where(hit >= 2, ks, -1))
        khit = np.where(kh >= 0, kh - ee, -1).astype(np.int16)
        parts.append(pd.DataFrame({"ts": (ee + b0).astype(np.int64) * MIN, "symId": sid[cc + c0].astype(np.int16),
                                   "y": y, "hit": hit, "khit": khit, "ret168": ret.astype(np.float32),
                                   "P": P.astype(np.float32)}))
    D = pd.concat(parts, ignore_index=True).sort_values(["ts", "symId"]).reset_index(drop=True)
    assert not D.duplicated(["ts", "symId"]).any()
    assert int(D.ts.max()) // MIN + HZ <= DEV_M1
    nchk, nbad = check_rows(D, H, L, C, b0, names)
    assert nbad == 0, "BRUTE lech %d/%d" % (nbad, nchk)
    os.makedirs(OUT, exist_ok=True)
    tag = ("probe_%d" % ym) if probe_days else ("fh_%d" % ym)
    D.to_parquet(os.path.join(OUT, tag + ".parquet"), index=False)
    hc = D.hit.value_counts().to_dict()
    meta = dict(ym=ym, nsym=S, nsym_mapped=int((sid > 0).sum()), nrec=nrec, nmin=N, nticks=int(len(ticks)),
                rows=int(len(D)), y_rate=float(D.y.mean()), hit_counts={int(k): int(v) for k, v in hc.items()},
                n_trunc=n_trunc, brute_n=nchk, brute_bad=nbad, secs=round(time.time() - t00, 1))
    json.dump(meta, open(os.path.join(OUT, "meta_%s.json" % tag), "w"), indent=1)
    log.info("%s XONG %s", ym, json.dumps(meta))
    return meta


def months_of(spec):
    a, b = spec.split("-") if "-" in spec else (spec, spec)
    out = []
    y, m = divmod(int(a), 100)
    while y * 100 + m <= int(b):
        out.append(y * 100 + m)
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def brute_check(D, H, L, C, b0, n=400, seed=7):
    """Kiem doc lap: lap tung phut cho n dong ngau nhien, so voi y/hit/khit/ret168 vectorized."""
    rng = np.random.default_rng(seed)
    smap = pd.read_csv(MAP_CSV)
    i2s = dict(zip(smap.symId.astype(np.int64), smap.symbol))
    pick = rng.choice(len(D), size=min(n, len(D)), replace=False)
    return pick, i2s


def check_rows(D, H, L, C, b0, names):
    col = {n: i for i, n in enumerate(names)}
    pick, i2s = brute_check(D, H, L, C, b0)
    bad = 0
    for r in pick:
        row = D.iloc[r]
        e = int(row.ts) // MIN - b0
        j = col[i2s[int(row.symId)]]
        P = float(C[e, j])
        hit, kh, last = 0, -1, None
        for p in range(e + 1, e + HZ + 1):
            h, l, c = H[p, j], L[p, j], C[p, j]
            if np.isfinite(c):
                last = c
            ua = np.isfinite(h) and h >= np.float32(ARM * P)
            us = np.isfinite(l) and -l >= np.float32(-SL * P)
            if ua or us:
                hit = 3 if (ua and us) else (1 if ua else 2); kh = p - e
                break
        y = 1 if hit == 1 else (0 if hit >= 2 else int(last / P - 1 > 0))
        if not (y == int(row.y) and hit == int(row.hit) and kh == int(row.khit)):
            bad += 1
            log.warning("BRUTE lech row=%d ts=%d sym=%d vec(y=%d,hit=%d,k=%d) brute(y=%d,hit=%d,k=%d)",
                        r, int(row.ts), int(row.symId), int(row.y), int(row.hit), int(row.khit), y, hit, kh)
    return len(pick), bad


def main():
    setup_log()
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", default="202101-202512")
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--probe-days", type=int, default=0)
    a = ap.parse_args()
    months = months_of(a.months)
    assert max(months) <= 202512, "DEV <= 2025"
    todo = [m for m in months if a.probe_days or not os.path.exists(os.path.join(OUT, "fh_%d.parquet" % m))]
    log.info("FH build %d thang (bo qua %d da co) procs=%d probe_days=%d", len(todo), len(months) - len(todo),
             a.procs, a.probe_days)
    if a.procs <= 1:
        for m in todo:
            label_month((m, a.probe_days))
    else:
        with Pool(a.procs) as p:
            for meta in p.imap_unordered(label_month, [(m, a.probe_days) for m in todo]):
                log.info("done %s rows=%s secs=%s", meta["ym"], meta["rows"], meta["secs"])
    log.info("FH_ALL_DONE")


if __name__ == "__main__":
    main()
