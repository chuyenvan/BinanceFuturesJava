#!/usr/bin/env python3
"""short_v3_r1_fade.py — PREREG_SHORT_V3_R1 (a58f9929): INTRADAY FADE 1m first-hit.

Stage scan  : stream Aerospike test.kline_1m_opt theo THANG UTC (warm-up 1500', fwd 1441'), tim ung vien tho
              (r60>=8%, volclimax 5x median 24x60', newhigh 24h, co gia entry t+1) + exit 6 o SHORT + 6 o LONG
              -> CACHE/cand_YYYYMM.parquet (+ meta). Sanity (b),(c) chay o thang thu (--sanity).
Stage report: cooldown 24h, funding settle thuc, CI block 72h, GO-R1 -> docs/result/RESULT_SHORT_V3_R1.json
              + per-trade CSV / bang md o CACHE (ngoai repo).
V (field 5 pb) = totalUsdt = QUOTE volume USDT (DataMigrator.java; BTCUSDT 1m ~2e7) -> quoteVol = V.
Chay: python3 short_v3_r1_fade.py scan --months 202403 --sanity ; ... scan --months all ; ... report
"""
import argparse, glob, json, logging, os, statistics, sys, time
from multiprocessing import Pool
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
CACHE = "/home/ubuntu/claude_master/1002/r1_cache"
OUT_JSON = os.path.join(REPO, "docs/result/RESULT_SHORT_V3_R1.json")
FUND = "/tmp/fund_cache.npz"
QVDIR = "/home/ubuntu/claude_master/1002/p0a_cache/qv"
MIN = 60000
H72 = 72 * 3600000
DEV_M0 = 1640995200000 // MIN          # 2022-01-01 00:00 UTC
DEV_M1 = 1767225600000 // MIN - 1      # 2025-12-31 23:59 UTC = phut cuoi duoc doc
T_MAX = DEV_M1 - 1441                  # trigger cuoi: t+1+1440 <= DEV_M1
WARM, FWD, WLEN = 1500, 1441, 1440
R60, VOLX, NH_W, NH_MIN, WIN_MIN, NWIN_MIN = 0.08, 5.0, 1440, 1368, 30, 20
FEE = 0.00112
NREP, SEED, INFL = 2000, 20260905, 1.89
CFG = {"A": (0.03, 0.02, 0.06), "B": (0.05, 0.03, 0.10)}
TS_LIST = (240, 720, 1440)
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT"}
log = logging.getLogger("r1")


def setup_log():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(process)d %(levelname)s %(message)s")


def key_of(m):
    """phut UTC m (gio mo) -> key Aerospike TZ+7."""
    return time.strftime("%Y%m%d-%H%M", time.gmtime(m * 60 + 7 * 3600))


def cfg_names():
    return ["%s_%s%d" % (sd, br, ts // 60) for br in ("A", "B") for sd in ("S", "L") for ts in TS_LIST]


# ───────────────────────── stream 1 luot ─────────────────────────
def stream(b0, b1, tag):
    """Doc phut b0..b1 (UTC) -> arr (5, N, S) float32 [O,H,L,C,V], names. Gia <= 0 -> NaN."""
    import aerospike, cramjam
    from short_pathexit_sim import parse_min
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    N = b1 - b0 + 1
    cap = 512
    arr = np.full((5, N, cap), np.nan, np.float32)
    names = {}
    t0 = time.time(); nrec = 0
    nday = (N + 1439) // 1440
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
                rows.append(r); vals.append(v)
            if len(names) > cap:
                cap2 = len(names) + 128
                a2 = np.full((5, N, cap2), np.nan, np.float32)
                a2[:, :, :cap] = arr
                arr = a2; cap = cap2
            if rows:
                arr[:, ms[k] - b0, rows] = np.asarray(vals, np.float32).T
                nrec += 1
        di = (d0 - b0) // 1440 + 1
        if di % 5 == 0 or di == nday:
            log.info("%s ngay %d/%d nrec=%d nsym=%d %.0fs", tag, di, nday, nrec, len(names), time.time() - t0)
    cli.close()
    S = len(names)
    arr = np.ascontiguousarray(arr[:, :, :S])
    for f in range(4):
        x = arr[f]
        x[~(x > 0)] = np.nan
    return arr, [n for n, _ in sorted(names.items(), key=lambda z: z[1])], nrec


# ───────────────────────── feature (vectorized) ─────────────────────────
def feats_vec(C, Cf, csV, csP, ti, si, do_nh=True):
    """ti, si: chi so phut (buffer) va cot. CHI doc chi so <= ti (csV/csP[ti+1] = tong den ti)."""
    ti = np.asarray(ti, np.int64); si = np.asarray(si, np.int64)
    c_t = C[ti, si].astype(np.float64)
    cf60 = Cf[ti - 60, si].astype(np.float64)
    with np.errstate(all="ignore"):
        r60 = c_t / cf60 - 1
    ends = ti[:, None] - 60 * np.arange(25)[None, :]
    sc = si[:, None]
    W = csV[ends + 1, sc] - csV[ends - 59, sc]
    cnt = csP[ends + 1, sc] - csP[ends - 59, sc]
    Wk = np.where(cnt[:, 1:] >= WIN_MIN, W[:, 1:], np.nan)
    nv = np.isfinite(Wk).sum(1)
    Mn = np.full(len(ti), np.nan)
    okm = nv > 0
    if okm.any():
        Mn[okm] = np.nanmedian(Wk[okm], axis=1)
    W0 = W[:, 0]
    with np.errstate(all="ignore"):
        volok = (nv >= NWIN_MIN) & (Mn > 0) & (W0 >= VOLX * Mn)
    mx = np.full(len(ti), np.nan); npres = np.zeros(len(ti), np.int64)
    for i in np.nonzero(volok & (r60 >= R60))[0] if do_nh else range(len(ti)):
        seg = C[ti[i] - NH_W: ti[i], si[i]]
        ok = np.isfinite(seg); npres[i] = int(ok.sum())
        if npres[i]:
            mx[i] = float(seg[ok].max())
    with np.errstate(all="ignore"):
        trig = (r60 >= R60) & volok & (npres >= NH_MIN) & (c_t >= mx)
    return dict(c_t=c_t, cf60=cf60, r60=r60, W0=W0, Mnen=Mn, nvalid=nv, maxprev=mx, npres=npres, trig=trig)


# ───────────────────────── feature (loop thuan, tham chieu) ─────────────────────────
def feat_loop(cl, vl, t):
    """cl, vl: list python CAT tai t+1 (khong co phan tu > t). Tra dict feature hoac None."""
    assert len(cl) == t + 1 and len(vl) == t + 1
    ct = cl[t]
    if ct != ct:
        return None
    j = t - 60
    while j >= 0 and cl[j] != cl[j]:
        j -= 1
    if j < 0:
        return None
    r60 = ct / cl[j] - 1
    W0 = 0.0
    for x in vl[t - 59:t + 1]:
        if x == x:
            W0 += x
    Ws = []
    for k in range(1, 25):
        e = t - 60 * k
        npz = 0; sv = 0.0
        for q in range(e - 59, e + 1):
            if cl[q] == cl[q]:
                npz += 1
            if vl[q] == vl[q]:
                sv += vl[q]
        if npz >= WIN_MIN:
            Ws.append(sv)
    med = statistics.median(Ws) if Ws else float("nan")
    prev = [x for x in cl[t - NH_W:t] if x == x]
    mx = max(prev) if prev else float("nan")
    trig = (r60 >= R60 and len(Ws) >= NWIN_MIN and med > 0 and W0 >= VOLX * med
            and len(prev) >= NH_MIN and ct >= mx)
    return dict(r60=r60, W0=W0, Mnen=med, maxprev=mx, trig=bool(trig))


# ───────────────────────── exit (vectorized) ─────────────────────────
def exit_vec(Hw, Lw, Ow, Cw, P, a, g, s, side):
    """Cua so = phut t+2..t+1+1440 (float64). side -1 SHORT, +1 LONG.
    Muc stop phut j tinh tu du lieu den j-1; fill gap = max/min(level, open). -> {TS: (pnl, k_exit, reason 0TIME/1SL/2TRAIL)}"""
    n = len(Hw)
    with np.errstate(all="ignore"):
        if side < 0:
            lw = np.where(np.isfinite(Lw), Lw, np.inf)
            run = np.minimum.accumulate(np.concatenate(([P], lw)))[:-1]
            armed = run <= P * (1 - a)
            level = np.where(armed, run * (1 + g), P * (1 + s))
            hit = np.greater_equal(Hw, level)
        else:
            hw = np.where(np.isfinite(Hw), Hw, -np.inf)
            run = np.maximum.accumulate(np.concatenate(([P], hw)))[:-1]
            armed = run >= P * (1 + a)
            level = np.where(armed, run * (1 - g), P * (1 - s))
            hit = np.less_equal(Lw, level)
    k = int(np.argmax(hit)) if hit.any() else n
    res = {}
    for TS in TS_LIST:
        if k < TS:
            o = Ow[k]; lv = float(level[k])
            if side < 0:
                px = max(lv, o) if np.isfinite(o) else lv
            else:
                px = min(lv, o) if np.isfinite(o) else lv
            rs = 2 if armed[k] else 1; ke = k
        else:
            px = float(Cw[TS - 1]); rs = 0; ke = TS - 1
        res[TS] = ((1 - px / P) if side < 0 else (px / P - 1), ke, rs)
    return res


def exit_loop(Hw, Lw, Ow, Cw, P, a, g, s, side):
    """Tham chieu loop thuan (list python)."""
    run = P; hitk = None
    for j in range(len(Hw)):
        h, l, o = Hw[j], Lw[j], Ow[j]
        if side < 0:
            armed = run <= P * (1 - a)
            lv = run * (1 + g) if armed else P * (1 + s)
            if h == h and h >= lv:
                hitk = (j, (max(lv, o) if o == o else lv), armed); break
            if l == l and l < run:
                run = l
        else:
            armed = run >= P * (1 + a)
            lv = run * (1 - g) if armed else P * (1 - s)
            if l == l and l <= lv:
                hitk = (j, (min(lv, o) if o == o else lv), armed); break
            if h == h and h > run:
                run = h
    res = {}
    for TS in TS_LIST:
        if hitk is not None and hitk[0] < TS:
            px, ke, rs = hitk[1], hitk[0], (2 if hitk[2] else 1)
        else:
            px, ke, rs = Cw[TS - 1], TS - 1, 0
        res[TS] = ((1 - px / P) if side < 0 else (px / P - 1), ke, rs)
    return res


def sim_trade(arrs, t, s, P):
    """arrs = (O,H,L,Cf). Entry tai t+1 (gia P = C[t+1]); duong gia t+2..t+1+1440."""
    O, Hh, L, Cf = arrs
    w0 = t + 2
    assert w0 - 1 == t + 1
    Hw = Hh[w0:w0 + WLEN, s].astype(np.float64); Lw = L[w0:w0 + WLEN, s].astype(np.float64)
    Ow = O[w0:w0 + WLEN, s].astype(np.float64); Cw = Cf[w0:w0 + WLEN, s].astype(np.float64)
    assert len(Hw) == WLEN
    out = {"cov": float(np.isfinite(Hw).mean())}
    for br, (a, g, sl) in CFG.items():
        for side, sn in ((-1, "S"), (1, "L")):
            r = exit_vec(Hw, Lw, Ow, Cw, P, a, g, sl, side)
            for TS, (pnl, ke, rs) in r.items():
                nm = "%s_%s%d" % (sn, br, TS // 60)
                out[nm + "_p"] = pnl; out[nm + "_k"] = ke; out[nm + "_r"] = rs
    return out, (Hw, Lw, Ow, Cw)


def month_bounds(ym):
    y, mo = divmod(ym, 100)
    s0 = pd.Timestamp(year=y, month=mo, day=1, tz="UTC")
    s1 = s0 + pd.offsets.MonthBegin(1)
    m_lo = max(int(s0.value // 10 ** 9 // 60), DEV_M0)
    m_hi = min(int(s1.value // 10 ** 9 // 60) - 1, T_MAX)
    b0 = m_lo - WARM
    b1 = min(m_hi + FWD, DEV_M1)
    assert b1 <= DEV_M1 and m_hi + 1 + WLEN <= b1
    return m_lo, m_hi, b0, b1


def scan_month(args):
    ym, sanity = args
    setup_log()
    t0 = time.time()
    m_lo, m_hi, b0, b1 = month_bounds(ym)
    arr, names, nrec = stream(b0, b1, str(ym))
    O, Hh, L, C, V = arr
    N, S = C.shape
    pres = np.isfinite(C)
    Cf = pd.DataFrame(C).ffill().to_numpy(np.float32)
    csV = np.zeros((N + 1, S), np.float64)
    np.cumsum(np.nan_to_num(V, nan=0.0), axis=0, dtype=np.float64, out=csV[1:])
    csP = np.zeros((N + 1, S), np.int32)
    np.cumsum(pres, axis=0, dtype=np.int32, out=csP[1:])
    t_lo, t_hi = m_lo - b0, m_hi - b0
    TI, SI, TX, SX = [], [], [], []
    for c0 in range(t_lo, t_hi + 1, 4000):
        c1 = min(c0 + 4000, t_hi + 1)
        with np.errstate(all="ignore"):
            r60 = C[c0:c1].astype(np.float64) / Cf[c0 - 60:c1 - 60].astype(np.float64) - 1
        base = pres[c0:c1] & (r60 >= R60)
        ent = pres[c0 + 1:c1 + 1]
        a_, b_ = np.nonzero(base & ent); TI.append(a_ + c0); SI.append(b_)
        a_, b_ = np.nonzero(base & ~ent); TX.append(a_ + c0); SX.append(b_)
    ti = np.concatenate(TI); si = np.concatenate(SI)
    tx = np.concatenate(TX); sx = np.concatenate(SX)
    F = feats_vec(C, Cf, csV, csP, ti, si)
    n_noentry = int(feats_vec(C, Cf, csV, csP, tx, sx)["trig"].sum()) if len(tx) else 0
    k = np.nonzero(F["trig"])[0]
    log.info("%s stream xong nsym=%d nrec=%d r60pass=%d cand=%d noentry=%d %.0fs", ym, S, nrec, len(ti), len(k), n_noentry, time.time() - t0)
    rows = []
    arrs = (O, Hh, L, Cf)
    for i in k:
        t, s = int(ti[i]), int(si[i])
        P = float(C[t + 1, s])
        assert np.isfinite(P) and P > 0
        rec = dict(sym=names[s], t=t + b0, r60=F["r60"][i], c_t=F["c_t"][i], cf60=F["cf60"][i], W0=F["W0"][i],
                   Mnen=F["Mnen"][i], nvalid=int(F["nvalid"][i]), maxprev=F["maxprev"][i], npres=int(F["npres"][i]), P=P)
        ex, _w = sim_trade(arrs, t, s, P)
        for kk, v in ex.items():
            rec[kk] = (v + t + 2 + b0) if kk.endswith("_k") else v   # _k -> phut exit tuyet doi
        rows.append(rec)
    df = pd.DataFrame(rows)
    df["ym"] = ym
    os.makedirs(CACHE, exist_ok=True)
    df.to_parquet(os.path.join(CACHE, "cand_%d.parquet" % ym), index=False)
    meta = dict(ym=ym, nsym=S, nrec=nrec, nmin=N, r60pass=int(len(ti)), cand=int(len(k)), cand_noentry=n_noentry,
                secs=round(time.time() - t0, 1))
    if sanity:
        meta["sanity"] = run_sanity(arr, Cf, csV, csP, names, b0, ti, si, F, k, ym)
    json.dump(meta, open(os.path.join(CACHE, "meta_%d.json" % ym), "w"), indent=1, default=str)
    log.info("%s XONG cand=%d %.0fs", ym, len(k), time.time() - t0)
    return meta


# ───────────────────────── sanity (b), (c) ─────────────────────────
def run_sanity(arr, Cf, csV, csP, names, b0, ti, si, F, k, ym):
    O, Hh, L, C, V = arr
    N, S = C.shape
    out = {}
    # (c) ngay co nhieu ung vien tho nhat: vectorized vs loop thuan
    days = (ti[k] + b0) // 1440
    vals, cnts = np.unique(days, return_counts=True)
    dsel = int(vals[np.argmax(cnts)])
    dlo, dhi = dsel * 1440 - b0, dsel * 1440 + 1439 - b0
    vec_set = {(int(si[i]), int(ti[i])) for i in k if dlo <= ti[i] <= dhi}
    lo = dlo - WARM
    loop_set = {}
    t1 = time.time()
    for s in range(S):
        cl = C[lo:dhi + 2, s].astype(np.float64).tolist()
        vl = V[lo:dhi + 2, s].astype(np.float64).tolist()
        for t in range(dlo, dhi + 1):
            tl = t - lo
            ct = cl[tl]
            if ct != ct or cl[tl + 1] != cl[tl + 1]:
                continue
            j = tl - 60
            while j >= 0 and cl[j] != cl[j]:
                j -= 1
            if j < 0 or ct / cl[j] - 1 < R60:
                continue
            f = feat_loop(cl[:tl + 1], vl[:tl + 1], tl)
            if f is not None and f["trig"]:
                loop_set[(s, t)] = f
    out["c_day_utc"] = str(pd.Timestamp(dsel * 1440 * MIN, unit="ms").date())
    out["c_n_vec"] = len(vec_set); out["c_n_loop"] = len(loop_set)
    out["c_set_equal"] = bool(vec_set == set(loop_set))
    out["c_loop_secs"] = round(time.time() - t1, 1)
    idx = {(int(si[i]), int(ti[i])): i for i in k}
    fd = 0.0; pd_max = 0.0; kmis = 0; ncmp = 0
    for key in sorted(vec_set & set(loop_set)):
        i = idx[key]; f = loop_set[key]
        for nm in ("r60", "W0", "Mnen", "maxprev"):
            fd = max(fd, abs(F[nm][i] - f[nm]) / max(abs(f[nm]), 1e-12))
        s, t = key
        P = float(C[t + 1, s])
        _ex, (Hw, Lw, Ow, Cw) = sim_trade((O, Hh, L, Cf), t, s, P)
        lists = [x.tolist() for x in (Hw, Lw, Ow, Cw)]
        for br, (a, g, sl) in CFG.items():
            for side in (-1, 1):
                rv = exit_vec(Hw, Lw, Ow, Cw, P, a, g, sl, side)
                rl = exit_loop(*lists, P, a, g, sl, side)
                for TS in TS_LIST:
                    ncmp += 1
                    pd_max = max(pd_max, abs(rv[TS][0] - rl[TS][0]))
                    kmis += int(rv[TS][1] != rl[TS][1] or rv[TS][2] != rl[TS][2])
    out["c_feat_maxreldiff"] = fd; out["c_exit_ncmp"] = ncmp
    out["c_exit_pnl_maxabsdiff"] = pd_max; out["c_exit_k_reason_mismatch"] = kmis
    out["c_PASS"] = bool(out["c_set_equal"] and fd < 1e-5 and pd_max < 1e-6 and kmis == 0 and ncmp > 0)
    # (b) nhieu tuong lai: thay toan bo du lieu > t bang rac -> feature/trigger khong doi
    rng = np.random.default_rng(SEED)
    pool_t = list(k[:100]) + list(rng.choice(len(ti), size=min(200, len(ti)), replace=False))
    nb = 0; bad = 0
    for i in pool_t:
        t, s = int(ti[i]), int(si[i])
        C1 = C[:, s].astype(np.float32).copy(); V1 = V[:, s].astype(np.float32).copy()
        nfut = N - t - 1
        C1[t + 1:] = C[t, s] * rng.uniform(0.5, 2.0, nfut).astype(np.float32)
        V1[t + 1:] = rng.uniform(0, 1e9, nfut).astype(np.float32)
        Cf1 = pd.Series(C1).ffill().to_numpy(np.float32)
        csV1 = np.zeros(N + 1); np.cumsum(np.nan_to_num(V1, nan=0.0), dtype=np.float64, out=csV1[1:])
        csP1 = np.zeros(N + 1, np.int32); np.cumsum(np.isfinite(C1), dtype=np.int32, out=csP1[1:])
        f1 = feats_vec(C1[:, None], Cf1[:, None], csV1[:, None], csP1[:, None], [t], [0])
        nb += 1
        same = bool(f1["trig"][0] == F["trig"][i])
        for nm in ("r60", "W0", "Mnen", "maxprev"):
            a_, b_ = f1[nm][0], F[nm][i]
            same &= bool((np.isnan(a_) and np.isnan(b_)) or abs(a_ - b_) <= 1e-9 * max(1.0, abs(b_)))
        bad += int(not same)
    out["b_noise_n"] = nb; out["b_noise_mismatch"] = bad
    out["b_entry_assert"] = "sim_trade: assert w0-1 == t+1, P = C[t+1]; feats_vec chi doc chi so <= t"
    out["b_PASS"] = bool(nb >= 200 and bad == 0)
    log.info("SANITY %s", out)
    return out


# ───────────────────────── report ─────────────────────────
def cooldown(df):
    df = df.sort_values(["sym", "t"], kind="stable").reset_index(drop=True)
    keep = np.zeros(len(df), bool); last = {}
    for i, (s, t) in enumerate(zip(df["sym"].to_numpy(), df["t"].to_numpy())):
        lt = last.get(s)
        if lt is None or t >= lt + 1 + 1440:
            keep[i] = True; last[s] = t
    return df[keep].sort_values("t", kind="stable").reset_index(drop=True)


def funding_sums(tr, cols_k):
    """F[c] = sum rate su kien funding co fundingTime in (entry_ms, exit_ms] cho tung cot exit-minute."""
    z = np.load(FUND, allow_pickle=True)
    fsy = [str(x) for x in z["syms"]]
    fts = z["ts"].astype(np.int64); frt = z["rt"].astype(np.float64); fsid = z["sid"].astype(np.int64)
    m = fts > 0
    fts, frt, fsid = fts[m], frt[m], fsid[m]
    o = np.lexsort((fts, fsid)); fts, frt, fsid = fts[o], frt[o], fsid[o]
    bnd = np.searchsorted(fsid, np.arange(len(fsy) + 1))
    n2i = {n: i for i, n in enumerate(fsy)}
    ent = (tr["t"].to_numpy(np.int64) + 2) * MIN - 1
    res = {c: np.zeros(len(tr)) for c in cols_k}
    has = np.zeros(len(tr), bool)
    for sym, g in tr.groupby("sym").groups.items():
        j = n2i.get(sym)
        if j is None or bnd[j + 1] == bnd[j]:
            continue
        ts = fts[bnd[j]:bnd[j + 1]]; cum = np.concatenate(([0.0], np.cumsum(frt[bnd[j]:bnd[j + 1]])))
        gi = np.asarray(g); has[gi] = True
        a = np.searchsorted(ts, ent[gi], "right")
        for c in cols_k:
            ex = (tr[c].to_numpy(np.int64)[gi] + 1) * MIN - 1
            res[c][gi] = cum[np.searchsorted(ts, ex, "right")] - cum[a]
    return res, has


def ci_block(v, ems):
    v = np.asarray(v, np.float64)
    blk = np.asarray(ems, np.int64) // H72
    _, inv = np.unique(blk, return_inverse=True)
    sums = np.bincount(inv, weights=v); cnts = np.bincount(inv).astype(np.float64)
    rng = np.random.default_rng(SEED)
    nb = len(sums)
    bs = np.empty(NREP)
    for b in range(NREP):
        p = rng.integers(0, nb, nb)
        bs[b] = sums[p].sum() / cnts[p].sum()
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    mu = float(v.mean())
    return dict(raw=[lo, hi], infl=[mu - (mu - lo) * INFL, mu + (hi - mu) * INFL], nblock=int(nb))


def yr_of(ems):
    return pd.to_datetime(ems, unit="ms", utc=True).year.to_numpy()


def cell_stats(net, gross, fund, rsn, held, ems):
    net = np.asarray(net, np.float64)
    ci = ci_block(net, ems)
    yr = yr_of(ems)
    by = {str(y): (float(net[yr == y].mean()) if (yr == y).any() else None) for y in (2022, 2023, 2024, 2025)}
    byn = {str(y): int((yr == y).sum()) for y in (2022, 2023, 2024, 2025)}
    return dict(n=int(len(net)), mean=float(net.mean()), median=float(np.median(net)), win=float((net > 0).mean()),
                sl_rate=float((rsn == 1).mean()), trail_rate=float((rsn == 2).mean()), time_rate=float((rsn == 0).mean()),
                gross_mean=float(np.mean(gross)), fund_mean=float(np.mean(fund)), held_mean_h=float(np.mean(held) / 60.0),
                ci_raw=ci["raw"], ci_infl=ci["infl"], nblock=ci["nblock"], by_year=by, n_by_year=byn,
                years_pos=int(sum(1 for x in by.values() if x is not None and x > 0)),
                net_min=float(net.min()), net_p1=float(np.percentile(net, 1)), net_p99=float(np.percentile(net, 99)))


def tier_regime(tr):
    q = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(QVDIR, "*.parquet")))], ignore_index=True)
    q["date"] = pd.to_datetime(q["date"]).dt.normalize()
    qv = q.pivot_table(index="date", columns="sym", values="qv", aggfunc="sum")
    qv = qv.reindex(pd.date_range(qv.index.min(), qv.index.max(), freq="D"))
    qv = qv[[c for c in qv.columns if c not in STABLE]]
    qv30 = qv.rolling(30, min_periods=20).mean().shift(1)
    pr = qv30.rank(axis=1, pct=True)
    lc = q.pivot_table(index="date", columns="sym", values="lastc", aggfunc="last").reindex(qv.index)["BTCUSDT"]
    bull = (lc.shift(1) > lc.rolling(50).mean().shift(1))
    bull[lc.rolling(50).mean().shift(1).isna()] = np.nan
    d = pd.to_datetime(tr["t"].to_numpy(np.int64) * MIN, unit="ms").normalize()
    st = pr.stack()
    p = pd.Series(st.reindex(pd.MultiIndex.from_arrays([d, tr["sym"].to_numpy()])).to_numpy(), index=tr.index)
    tier = np.where(p > 2 / 3, "LON", np.where(p > 1 / 3, "VUA", np.where(p.notna(), "NHO", "NA")))
    b = bull.reindex(d).to_numpy(dtype=object)
    reg = np.where(pd.isna(b), "NA", np.where(b == True, "BULL", "BEAR"))   # noqa: E712
    return tier, reg


def reread_check(rows):
    """Doc doc lap Aerospike cho phut t-60, t, t+1 cua mau -> so voi gia da luu."""
    import aerospike, cramjam
    from short_pathexit_sim import parse_min
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    out = []
    for r in rows:
        vals = {}
        for lab, m in (("t-60", r["t"] - 60), ("t", r["t"]), ("t+1", r["t"] + 1)):
            rec = _get(cli, ("test", "kline_1m_opt", key_of(int(m))))
            d = parse_min(bytes(dec(rec[2]["data"]))) if rec and rec[2] and "data" in rec[2] else {}
            v = d.get(r["sym"])
            vals[lab] = None if v is None else [float(x) for x in v]
        out.append(dict(sym=r["sym"], t_utc=str(pd.Timestamp(int(r["t"]) * MIN, unit="ms")), key_t=key_of(int(r["t"])),
                        raw=vals, stored=dict(cf60=float(r["cf60"]), c_t=float(r["c_t"]), P=float(r["P"])),
                        match_c_t=bool(vals["t"] is not None and abs(vals["t"][3] - r["c_t"]) < 1e-6 * r["c_t"]),
                        match_P=bool(vals["t+1"] is not None and abs(vals["t+1"][3] - r["P"]) < 1e-6 * r["P"]),
                        match_cf60=(None if vals["t-60"] is None else bool(abs(vals["t-60"][3] - r["cf60"]) < 1e-6 * r["cf60"]))))
    cli.close()
    return out


def _get(cli, key):
    try:
        return cli.get(key)
    except Exception:
        return None


def report(months_expected):
    fs = sorted(glob.glob(os.path.join(CACHE, "cand_*.parquet")))
    yms = sorted(int(os.path.basename(f)[5:11]) for f in fs)
    assert yms == months_expected, "thieu thang: %s" % sorted(set(months_expected) - set(yms))
    raw = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    metas = [json.load(open(os.path.join(CACHE, "meta_%d.json" % y))) for y in yms]
    assert raw["t"].min() >= DEV_M0 and raw["t"].max() <= T_MAX
    tr = cooldown(raw)
    names = cfg_names()
    assert (tr[[c + "_k" for c in names]].to_numpy() <= DEV_M1).all()
    Fd, has = funding_sums(tr, [c + "_k" for c in names])
    ems = (tr["t"].to_numpy(np.int64) + 2) * MIN - 1
    cells = {}
    for c in names:
        side = -1 if c.startswith("S") else 1
        fund = side * -1 * Fd[c + "_k"]          # short: +sum rate ; long: -sum rate
        gross = tr[c + "_p"].to_numpy(np.float64)
        net = gross - FEE + fund
        tr[c + "_net"] = net
        held = tr[c + "_k"].to_numpy(np.int64) - (tr["t"].to_numpy(np.int64) + 1)
        cells[c] = cell_stats(net, gross, fund, tr[c + "_r"].to_numpy(), held, ems)
        log.info("%s n=%d mean=%.5f ci=%s infl=%s yrs=%d sl=%.3f", c, cells[c]["n"], cells[c]["mean"],
                 cells[c]["ci_raw"], cells[c]["ci_infl"], cells[c]["years_pos"], cells[c]["sl_rate"])
    go = {}
    for br in ("A", "B"):
        npos = sum(1 for ts in TS_LIST if cells["S_%s%d" % (br, ts // 60)]["mean"] > 0)
        for ts in TS_LIST:
            c = "S_%s%d" % (br, ts // 60); x = cells[c]; xl = cells["L_%s%d" % (br, ts // 60)]
            g = dict(G1=bool(x["mean"] > 0 and x["ci_raw"][0] > 0 and x["ci_infl"][0] > 0), G2=bool(x["years_pos"] >= 3),
                     G3=bool(x["n"] >= 1500), G4=bool(x["sl_rate"] <= 0.25), G5=bool(x["mean"] > 0 and npos >= 2),
                     G6=bool(xl["mean"] <= 0))
            g["ALL"] = bool(all(g.values()))
            go[c] = g
    passing = [c for c in go if go[c]["ALL"]]
    verdict = "GO" if passing else "NO-GO"
    shorts = [c for c in names if c.startswith("S")]
    best = max(passing, key=lambda c: cells[c]["mean"]) if passing else max(shorts, key=lambda c: cells[c]["mean"])
    tier, reg = tier_regime(tr)
    tr["tier"] = tier; tr["regime"] = reg
    slices = {}
    for col in ("tier", "regime"):
        for v, g in tr.groupby(col):
            e = (g["t"].to_numpy(np.int64) + 2) * MIN - 1
            nb = g[best + "_net"].to_numpy(); nl = g[best.replace("S_", "L_") + "_net"].to_numpy()
            slices["%s=%s" % (col, v)] = dict(n=int(len(g)), short_mean=float(nb.mean()), short_median=float(np.median(nb)),
                                            short_ci_raw=ci_block(nb, e)["raw"] if len(g) > 5 else None,
                                            short_sl_rate=float((g[best + "_r"] == 1).mean()), long_mean=float(nl.mean()),
                                            years_pos=int(sum(1 for y in (2022, 2023, 2024, 2025)
                                                              if (yr_of(e) == y).any() and nb[yr_of(e) == y].mean() > 0)))
    r60 = tr["r60"].to_numpy(); ratio = (tr["W0"] / tr["Mnen"]).to_numpy()
    dist = dict(r60_pct={str(p): float(np.percentile(r60, p)) for p in (10, 25, 50, 75, 90, 99)}, r60_max=float(r60.max()),
                volratio_p50=float(np.median(ratio)), volratio_p90=float(np.percentile(ratio, 90)))
    dd = pd.to_datetime(tr["t"].to_numpy(np.int64) * MIN, unit="ms").normalize()
    cnt = pd.Series(1, index=dd).groupby(level=0).sum().reindex(
        pd.date_range("2022-01-01", pd.Timestamp(T_MAX * MIN, unit="ms").normalize(), freq="D"), fill_value=0)
    perday = dict(n_days=int(len(cnt)), mean=float(cnt.mean()), median=float(cnt.median()), p90=float(cnt.quantile(0.9)),
                  max=int(cnt.max()), max_day=str(cnt.idxmax().date()), frac_days_zero=float((cnt == 0).mean()),
                  per_year={str(y): int(cnt[cnt.index.year == y].sum()) for y in (2022, 2023, 2024, 2025)})
    by_year_best = {c: cells[c]["by_year"] for c in (best, best.replace("S_", "L_"))}
    rng = np.random.default_rng(SEED)
    m3 = tr[(tr["ym"] == 202403)].head(5)
    rnd = tr.iloc[np.sort(rng.choice(len(tr), 5, replace=False))]
    samp = pd.concat([m3, rnd])
    scols = ["sym", "t", "cf60", "c_t", "r60", "P", "maxprev", "W0", "Mnen", "nvalid", "npres",
             best + "_p", best + "_r", best + "_k", best + "_net"]
    samples = []
    for _, r in samp.iterrows():
        d = {c: (r[c].item() if hasattr(r[c], "item") else r[c]) for c in scols}
        d["t_utc"] = str(pd.Timestamp(int(r["t"]) * MIN, unit="ms")); samples.append(d)
    rr = reread_check([dict(sym=r["sym"], t=int(r["t"]), cf60=r["cf60"], c_t=r["c_t"], P=r["P"]) for _, r in samp.iterrows()])
    meta_sum = dict(r60pass=int(sum(m["r60pass"] for m in metas)), cand_raw=int(sum(m["cand"] for m in metas)),
                    cand_noentry=int(sum(m["cand_noentry"] for m in metas)), n_after_cooldown=int(len(tr)),
                    nsym_max=int(max(m["nsym"] for m in metas)), scan_secs=float(sum(m["secs"] for m in metas)),
                    sanity=[m["sanity"] for m in metas if "sanity" in m],
                    frac_trade_has_funding=float(has.mean()), frac_cov_lt90=float((tr["cov"] < 0.9).mean()))
    res = dict(prereg="PREREG_SHORT_V3_R1 (a58f9929)", program="PROGRAM_SHORT_V3 a8eff3fb",
               conv=dict(fee=FEE, nrep=NREP, seed=SEED, infl=INFL, block_h=72, cfg=CFG, ts_min=TS_LIST,
                         quotevol="V=field5 totalUsdt (quote)", dev_last_minute_utc=str(pd.Timestamp(DEV_M1 * MIN, unit="ms")),
                         t_max_utc=str(pd.Timestamp(T_MAX * MIN, unit="ms"))),
               verdict=verdict, passing=passing, best_cell=best, go_table=go, cells=cells,
               by_year_best=by_year_best, slices_best=slices, dist=dist, per_day=perday, counts=meta_sum,
               samples=samples, reread=rr, months=[{k: v for k, v in m.items() if k != "sanity"} for m in metas])
    json.dump(res, open(OUT_JSON, "w"), indent=1, default=float)
    keep = ["sym", "t", "r60", "W0", "Mnen", "P", "cov", "tier", "regime"] + [c + s for c in names for s in ("_net", "_r", "_k")]
    tr[keep].to_csv(os.path.join(CACHE, "trades_r1.csv"), index=False)
    log.info("VERDICT %s passing=%s best=%s -> %s", verdict, passing, best, OUT_JSON)


def main():
    setup_log()
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["scan", "report"])
    ap.add_argument("--months", default="all")
    ap.add_argument("--sanity", action="store_true")
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    allm = [y * 100 + m for y in (2022, 2023, 2024, 2025) for m in range(1, 13)]
    if a.stage == "report":
        report(allm); return
    months = allm if a.months == "all" else [int(x) for x in a.months.split(",")]
    todo = [m for m in months if a.force or not os.path.exists(os.path.join(CACHE, "cand_%d.parquet" % m))]
    log.info("scan %d thang (bo qua %d da co), procs=%d", len(todo), len(months) - len(todo), a.procs)
    os.makedirs(CACHE, exist_ok=True)
    if a.procs <= 1:
        for m in todo:
            scan_month((m, a.sanity and m == 202403))
    else:
        with Pool(a.procs, maxtasksperchild=1) as p:
            for meta in p.imap_unordered(scan_month, [(m, a.sanity and m == 202403) for m in todo]):
                log.info("DONE %s cand=%s secs=%s", meta["ym"], meta["cand"], meta["secs"])


if __name__ == "__main__":
    main()
