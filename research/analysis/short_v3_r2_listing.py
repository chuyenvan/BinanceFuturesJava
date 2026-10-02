#!/usr/bin/env python3
"""short_v3_r2_listing.py — R2 (LISTING EFFECT) cua PROGRAM_SHORT_V3 (0-sim daily + 1h).

Pre-reg: docs/prereg/PREREG_SHORT_V3_R2.md @ ffe806b2 (KHOA). DEV 2022-01-01..2025-12-31; chi doc ts <= 2026-01-01 00:00 UTC.
Nguon: CLOSES_1H.bin (listing_day, gia, SL), p0a_cache/qv (doi chieu Aerospike kline_1m_opt, CHI DOC),
       /tmp/fund_cache.npz (funding exact, rate>0 => SHORT NHAN).
Out: docs/result/RESULT_SHORT_V3_R2.json ; bang markdown -> ~/claude_master/1002/r2_tables.md
"""
import glob, json, logging, os, time
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
H = 3600000
DAY = 86400000
DEV_END_MS = 1767225600000            # 2026-01-01 00:00 UTC
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
FUND = "/tmp/fund_cache.npz"
QVDIR = "/home/ubuntu/claude_master/1002/p0a_cache/qv"
OUT_JSON = os.path.join(REPO, "docs/result/RESULT_SHORT_V3_R2.json")
OUT_MD = "/home/ubuntu/claude_master/1002/r2_tables.md"
PREREG = "docs/prereg/PREREG_SHORT_V3_R2.md@ffe806b2"
D_FIRST = pd.Timestamp("2022-01-01").value // 10**6 // DAY
D_LAST = pd.Timestamp("2025-12-24").value // 10**6 // DAY
HOLD = 168
FEE, SL_X, SL_LOSS, SLIP = 0.00112, 0.15, 0.152, 0.002
NREP, SEED, INFL = 2000, 20260905, 1.18
HORIZ = (1, 3, 7, 14, 30)
YEARS = (2022, 2023, 2024, 2025)
STABLE = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT"}
log = logging.getLogger("r2")


def eday(ts_ms):
    """epoch-day UTC cua nen 1h co close-known ts (nen phu (ts-1h, ts])."""
    return (np.asarray(ts_ms, dtype=np.int64) - H) // DAY


def dstr(d):
    return str(pd.Timestamp(int(d) * DAY, unit="ms").date())


def load_hourly():
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    ts = a["ts"].astype(np.int64); sid = a["sym"].astype(np.int64); c = a["c"].astype(np.float32)
    info = dict(n_rows=int(len(a)), n_rows_after_dev=int((ts > DEV_END_MS).sum()))
    del a
    m = (ts <= DEV_END_MS) & np.isfinite(c) & (c > 0)
    info["n_rows_bad"] = int(((ts <= DEV_END_MS) & ~(np.isfinite(c) & (c > 0))).sum())
    ts, sid, c = ts[m], sid[m], c[m]
    t_start = int(ts.min())
    assert ((ts - t_start) % H == 0).all(), "ts khong tren luoi 1h"
    mp = pd.read_csv(MAP)
    id2 = dict(zip(mp.symId.astype(int), mp.symbol.astype(str)))
    ids = np.unique(sid)
    names = [id2[int(i)] for i in ids]
    col = np.searchsorted(ids, sid)
    nh = (DEV_END_MS - t_start) // H + 1
    C = np.full((nh, len(ids)), np.nan, dtype=np.float32)
    C[(ts - t_start) // H, col] = c
    info.update(t_start=str(pd.Timestamp(t_start, unit="ms")), n_sym=len(ids), shape=list(C.shape))
    log.info("hourly %s", info)
    return C, names, t_start, info


class Fund:
    """Cach cong nhu lop Fund cua short_v3_score.py: sum rate co settle ts in (t0, t1]."""
    def __init__(self):
        z = np.load(FUND, allow_pickle=True)
        syms = [str(s) for s in z["syms"]]
        ts = z["ts"].astype(np.int64); rt = z["rt"].astype(np.float64); sid = z["sid"].astype(np.int64)
        o = np.lexsort((ts, sid)); ts, rt, sid = ts[o], rt[o], sid[o]
        self.n_dup = int(((np.diff(sid) == 0) & (np.diff(ts) == 0)).sum())
        b = np.searchsorted(sid, np.arange(len(syms) + 1))
        self.d = {}
        for i, s in enumerate(syms):
            if b[i + 1] > b[i]:
                tt = ts[b[i]:b[i + 1]]; rr = rt[b[i]:b[i + 1]]
                self.d[s] = (tt, rr, np.concatenate([[0.0], np.cumsum(rr)]))
        log.info("funding syms=%d events=%d dup(sid,ts)=%d", len(self.d), len(ts), self.n_dup)

    def window(self, s, t0, t1):
        if s not in self.d:
            return 0, 0, 0.0, None, None
        tt, rr, cs = self.d[s]
        lo = int(np.searchsorted(tt, t0, "right")); hi = int(np.searchsorted(tt, t1, "right"))
        return lo, hi, float(cs[hi] - cs[lo]), tt, rr


def day_last(C, j, D, t_start):
    """(k, so nen) cua close 1h cuoi cung trong ngay UTC D cua cot j."""
    k0 = (D * DAY + H - t_start) // H
    a, b = max(k0, 0), min(k0 + 23, C.shape[0] - 1)
    if b < a:
        return None, 0
    f = np.where(np.isfinite(C[a:b + 1, j]))[0]
    return (None, 0) if len(f) == 0 else (a + int(f[-1]), int(len(f)))


def trade(C, j, k0, sym, fund, t_start, path=False):
    P0 = float(C[k0, j]); t0 = t_start + k0 * H
    W = C[k0 + 1:k0 + HOLD + 1, j].astype(np.float64)
    assert len(W) == HOLD
    fin = np.isfinite(W)
    hit = fin & (W >= (1 + SL_X) * P0)
    sl = bool(hit.any())
    pend = W[np.where(fin)[0][-1]] if fin.any() else P0
    ret7 = pend / P0 - 1
    mf7 = float(np.nanmax(W) / P0 - 1) if fin.any() else 0.0
    kx = int(np.argmax(hit)) + 1 if sl else HOLD
    t_exit = t0 + kx * H
    lo, hi, f, _, _ = fund.window(sym, t0, t_exit)
    pnl = (-SL_LOSS if sl else -ret7) - FEE + f
    pnl_slc = (-(W[kx - 1] / P0 - 1) - SLIP if sl else -ret7) - FEE + f
    pnl_nof = (-SL_LOSS if sl else -ret7) - FEE
    r = dict(sym=sym, k0=int(k0), t0=int(t0), P0=P0, ret7=float(ret7), maxfav7=mf7, sl=sl, kx=kx, fund=f,
             nfund=hi - lo, hasf=bool(hi > lo), trunc=bool(not fin[-1]), pnl=float(pnl), pnl_slc=float(pnl_slc),
             pnl_nof=float(pnl_nof))
    if path:
        for h in HORIZ:
            L = 24 * h
            if t0 + L * H > DEV_END_MS:
                continue
            V = C[k0 + 1:k0 + L + 1, j].astype(np.float64)
            fv = np.isfinite(V)
            if not fv.any():
                continue
            r["ret_%d" % h] = float(V[np.where(fv)[0][-1]] / P0 - 1)
            r["mf_%d" % h] = float(np.nanmax(V) / P0 - 1)
    return r


def all_ret7(C, k0, ucols, cache):
    """mean ret_7d raw cua moi coin universe co close dung tai ts t0 (ke ca chinh listing)."""
    if k0 not in cache:
        P = C[k0, ucols].astype(np.float64)
        W = C[k0 + 1:k0 + HOLD + 1][:, ucols].astype(np.float64)
        E = pd.DataFrame(W).ffill().to_numpy()[-1]
        ok = np.isfinite(P) & np.isfinite(E)
        cache[k0] = (float(np.mean(E[ok] / P[ok] - 1)), int(ok.sum()))
    return cache[k0]


def ci_block(v, mi, nb):
    s = np.bincount(mi, weights=v, minlength=nb); c = np.bincount(mi, minlength=nb).astype(float)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, nb, (NREP, nb))
    cs = c[idx].sum(axis=1)
    bs = np.where(cs > 0, s[idx].sum(axis=1) / np.maximum(cs, 1), np.nan)
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    mu = float(np.mean(v))
    return [float(lo), float(hi)], [mu - INFL * (mu - lo), mu + INFL * (hi - mu)]


def summ(g, col="pnl", ci=True, year=None):
    v = g[col].to_numpy(float)
    if len(v) == 0:
        return dict(n=0)
    r = dict(n=int(len(v)), mean=float(v.mean()), median=float(np.median(v)), win=float((v > 0).mean()),
             sl_rate=float(g.sl.mean()), min=float(v.min()), p1=float(np.percentile(v, 1)), p5=float(np.percentile(v, 5)),
             fund_mean=float(g.fund.mean()), ret7_mean=float(g.ret7.mean()), ret7_med=float(g.ret7.median()),
             excess_mean=float(g.excess.mean()), excess_med=float(g.excess.median()))
    if ci:
        mi = (g.mi % 12).to_numpy() if year else g.mi.to_numpy()
        nb = 12 if year else 48
        r["ci_raw"], r["ci_infl"] = ci_block(v, mi, nb)
        if not year:
            r["excess_ci_raw"] = ci_block(g.excess.to_numpy(float), mi, nb)[0]
    return r


def find_listings(C, names, t_start, res):
    nh = C.shape[0]
    isu = np.array([n.endswith("USDT") and "_" not in n and n != "BTCUSDT" and n not in STABLE for n in names])
    ucols = np.where(isu)[0]
    fin = np.isfinite(C)
    anyf = fin.any(axis=0)
    fk = np.argmax(fin, axis=0); lk = nh - 1 - np.argmax(fin[::-1], axis=0)
    del fin
    ar = np.arange(len(names))
    first_day = eday(t_start + fk * H); last_day = eday(t_start + lk * H)
    first_px = C[fk, ar].astype(float); last_px = C[lk, ar].astype(float)
    q = pd.concat([pd.read_parquet(f, columns=["date", "sym", "nmin", "lastc"]) for f in sorted(glob.glob(QVDIR + "/*.parquet"))],
                  ignore_index=True)
    q = q[q.nmin > 0].copy()
    q["ed"] = pd.to_datetime(q["date"]).values.astype("datetime64[ms]").astype(np.int64) // DAY
    first_as = q.groupby("sym")["ed"].min().to_dict()
    lastc = {(s, int(e)): float(v) for s, e, v in zip(q.sym, q.ed, q.lastc)}
    file_first = int(eday(t_start))
    S1 = dict(n_sym_file=len(names), n_sym_universe=int(isu.sum()), file_first_day=dstr(file_first),
              n_univ_first_ge_2022=int(((first_day >= D_FIRST) & isu & anyf).sum()),
              n_univ_first_after_last=int(((first_day > D_LAST) & isu & anyf).sum()),
              qv_cache_first=dstr(min(first_as.values())), qv_cache_last=dstr(int(q.ed.max())))
    L, gap = [], []
    for j in ucols:
        if not anyf[j] or first_day[j] < D_FIRST or first_day[j] > D_LAST:
            continue
        s = names[j]; D0 = int(first_day[j]); fa = first_as.get(s)
        rec = dict(sym=s, j=int(j), D0=D0, year=int(dstr(D0)[:4]), first_as=None if fa is None else int(fa),
                   as_diff=None if fa is None else int(fa) - D0, first_px=float(first_px[j]),
                   days_before_in_file=D0 - file_first)
        assert rec["days_before_in_file"] >= 90
        (gap if (fa is not None and fa <= D0 - 2) else L).append(rec)
    S1["n_L2"] = len(L) + len(gap)
    S1["L3b_gap_excluded"] = [dict(sym=r["sym"], D0=dstr(r["D0"]), first_as=dstr(r["first_as"])) for r in gap]
    return L, gap, S1, ucols, (first_day, last_day, first_px, last_px), lastc


def rename_like(L, names, ucols_all, fl):
    first_day, last_day, first_px, last_px = fl
    out = {}
    for r in L:
        j, D0 = r["j"], r["D0"]
        for i in ucols_all:
            if i == j or abs(int(last_day[i]) - D0) > 3:
                continue
            ratio = first_px[j] / last_px[i]
            for m in (1.0, 1000.0, 0.001):
                if abs(ratio / m - 1) <= 0.05:
                    out[r["sym"]] = dict(old=names[i], old_last=dstr(last_day[i]), ratio=round(float(ratio), 5))
    return out


def build_arms(C, names, t_start, L, ucols, fund):
    arms = {"D0": [], "D1": []}
    excl = {"L5_D0": [], "L5_D1": [], "L4_D0": [], "L4_D1": []}
    cache = {}
    for rec in L:
        j, D0 = rec["j"], rec["D0"]
        k_d0, n_d0 = day_last(C, j, D0, t_start)
        k_d1, n_d1 = day_last(C, j, D0 + 1, t_start)
        rec.update(n_d0=n_d0, n_d1=n_d1, fallback=bool(n_d0 < 12))
        k_main = k_d0 if n_d0 >= 12 else k_d1
        for arm, k0 in (("D0", k_main), ("D1", k_d1)):
            if k0 is None:
                excl["L5_" + arm].append(rec["sym"]); continue
            if t_start + k0 * H + HOLD * H > DEV_END_MS:
                excl["L4_" + arm].append(rec["sym"]); continue
            tr = trade(C, j, k0, rec["sym"], fund, t_start, path=(arm == "D0"))
            a, na = all_ret7(C, k0, ucols, cache)
            tr.update(D0=dstr(D0), year_D0=rec["year"], fallback=rec["fallback"], n_d0=n_d0, all_ret7=a, n_all=na,
                      excess=a - tr["ret7"], ret_D0intra=float(tr["P0"] / rec["first_px"] - 1))
            arms[arm].append(tr)
    out = {}
    for arm, v in arms.items():
        df = pd.DataFrame(v)
        dt = pd.to_datetime(df.t0, unit="ms")
        df["year"] = dt.dt.year; df["mi"] = (dt.dt.year - 2022) * 12 + dt.dt.month - 1
        assert df.mi.between(0, 47).all()
        out[arm] = df
    return out, excl


def sanity(C, t_start, L, D, lastc, fund, res):
    S = res["sanity"]
    yrs = pd.Series([r["year"] for r in L]).value_counts().sort_index()
    S["S1"]["n_listing_after_L3b_by_yearD0"] = {str(k): int(v) for k, v in yrs.items()}
    for arm in ("D0", "D1"):
        S["S1"]["n_trades_%s_by_year_t0" % arm] = {str(k): int(v) for k, v in D[arm].year.value_counts().sort_index().items()}
    S["S1"]["n_fallback_D1"] = int(sum(r["fallback"] for r in L))
    # S2: 10 mau
    d0 = D["D0"]
    rng = np.random.default_rng(SEED)
    pick = sorted(rng.choice(len(d0), size=min(10, len(d0)), replace=False), key=lambda i: d0.t0.iloc[i])
    l2 = {r["sym"]: r for r in L}
    S2 = []
    for i in pick:
        t = d0.iloc[i]; r = l2[t.sym]
        px = []
        for dd in range(0, 8):
            k, _ = day_last(C, r["j"], r["D0"] + dd, t_start)
            px.append(None if k is None else round(float(C[k, r["j"]]), 6))
        S2.append(dict(sym=t.sym, D0=t.D0, n_d0=int(r["n_d0"]), first_as=None if r["first_as"] is None else dstr(r["first_as"]),
                       t0=str(pd.Timestamp(int(t.t0), unit="ms")), P0=round(float(t.P0), 6), close_D0_to_D7=px,
                       ret7=round(float(t.ret7), 4), sl=bool(t.sl), fund=round(float(t.fund), 5), pnl=round(float(t.pnl), 4)))
    S["S2_samples"] = S2
    # S3: Aerospike
    dif = np.array([r["as_diff"] for r in L if r["as_diff"] is not None])
    rel = []
    for r in L:
        k, _ = day_last(C, r["j"], r["D0"], t_start)
        lc = lastc.get((r["sym"], r["D0"]))
        if k is not None and lc:
            rel.append(abs(lc / float(C[k, r["j"]]) - 1))
    rel = np.array(rel)
    S["S3"] = dict(n=len(L), n_no_aerospike=int(sum(r["as_diff"] is None for r in L)),
                   frac_match_pm1=float((np.abs(dif) <= 1).mean()) if len(dif) else None,
                   as_diff_hist={str(k): int(v) for k, v in pd.Series(dif).clip(-5, 5).value_counts().sort_index().items()},
                   lastc_rel_n=int(len(rel)), lastc_rel_med=float(np.median(rel)) if len(rel) else None,
                   lastc_rel_p99=float(np.percentile(rel, 99)) if len(rel) else None)
    S["S4"] = {arm: dict(frac_hasf=float(D[arm].hasf.mean()), n_trunc=int(D[arm].trunc.sum()),
                         n_sl_ne_mf15=int(((D[arm].maxfav7 >= SL_X) != D[arm].sl).sum()),
                         n_all_min=int(D[arm].n_all.min()), n_all_med=float(D[arm].n_all.median())) for arm in D}
    S["S4"]["funding_dup_sid_ts_global"] = fund.n_dup


def path_table(d0):
    P = {}
    for h in HORIZ:
        rc, mc = "ret_%d" % h, "mf_%d" % h
        if rc not in d0:
            continue
        g = d0[d0[rc].notna()]
        P[str(h)] = dict(n=int(len(g)), ret_mean=float(g[rc].mean()), ret_med=float(g[rc].median()),
                         mf_mean=float(g[mc].mean()), mf_med=float(g[mc].median()), pSQ10=float((g[mc] >= 0.10).mean()),
                         p_ret_le_m10=float((g[rc] <= -0.10).mean()))
    P["D0intra"] = dict(n=int(len(d0)), mean=float(d0.ret_D0intra.mean()), med=float(d0.ret_D0intra.median()))
    return P


def funding_table(L, d0, fund):
    rates, gaps = [], []
    ok = set(d0.sym)
    for r in L:
        if r["sym"] not in ok:
            continue
        lo, hi, _, tt, rr = fund.window(r["sym"], r["D0"] * DAY, (r["D0"] + 8) * DAY)
        if hi > lo:
            rates.append(rr[lo:hi]); gaps.append(np.diff(tt[lo:hi]) / H)
    R = np.concatenate(rates) if rates else np.array([]); G = np.concatenate(gaps) if gaps else np.array([])
    F = dict(n_listing_with_events=len(rates), n_events=int(len(R)), mean=float(R.mean()),
             pct={str(p): float(np.percentile(R, p)) for p in (1, 5, 25, 50, 75, 95, 99)},
             frac_neg=float((R < 0).mean()), frac_abs_ge_0p1pct=float((np.abs(R) >= 0.001).mean()),
             gap_h_med=float(np.median(G)) if len(G) else None,
             gap_h_hist={str(k): int(v) for k, v in pd.Series(np.round(G)).value_counts().head(6).items()})
    F["per_trade_D0"] = dict(mean=float(d0.fund.mean()), median=float(d0.fund.median()),
                             p5=float(np.percentile(d0.fund, 5)), p95=float(np.percentile(d0.fund, 95)),
                             by_year={str(y): float(d0[d0.year == y].fund.mean()) for y in YEARS if (d0.year == y).any()})
    return F


def strategy(D, ren):
    T = {}
    for arm, df in D.items():
        a = dict(all=summ(df), by_year={str(y): summ(df[df.year == y], year=y) for y in YEARS})
        a["sens_SLclose"] = summ(df, col="pnl_slc", ci=True)
        a["sens_nofund"] = summ(df, col="pnl_nof", ci=True)
        a["sens_no_rename"] = summ(df[~df.sym.isin(list(ren))], ci=True)
        for k in ("sens_SLclose", "sens_nofund", "sens_no_rename"):
            sub = df if k != "sens_no_rename" else df[~df.sym.isin(list(ren))]
            col = {"sens_SLclose": "pnl_slc", "sens_nofund": "pnl_nof", "sens_no_rename": "pnl"}[k]
            a[k]["years_pos"] = int(sum(1 for y in YEARS if (sub.year == y).any() and sub[sub.year == y][col].mean() > 0))
        a["fallback_n"] = int(df.fallback.sum())
        x = a["all"]
        yp = [a["by_year"][str(y)].get("mean") for y in YEARS]
        G1 = bool(x["mean"] > 0 and x["ci_raw"][0] > 0 and x["ci_infl"][0] > 0)
        G2n = int(sum(1 for v in yp if v is not None and v > 0)); G2 = G2n >= 3
        G3 = x["n"] >= 120
        G4 = bool(x["excess_mean"] > 0)
        a["GO"] = dict(G1=G1, G1_detail=dict(mean=x["mean"], ci_raw_lo=x["ci_raw"][0], ci_infl_lo=x["ci_infl"][0]),
                       G2=G2, G2_years_pos=G2n, G3=bool(G3), G3_n=x["n"], G4=G4, G4_excess=x["excess_mean"],
                       PASS=bool(G1 and G2 and G3 and G4))
        T[arm] = a
    return T


def pc(x, nd=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else ("%+.*f" % (nd, 100 * x))


def ci_s(c):
    return "—" if not c or c[0] is None else "[%s;%s]" % (pc(c[0]), pc(c[1]))


def write_md(res):
    L = ["## Đường giá sau close D0 (anchor nhánh chính; %; maxFav trên 1h close = cận dưới)", "",
         "| horizon | n | retEnd mean | retEnd med | maxFav mean | maxFav med | pSQ10 | P(ret≤−10%) |", "|---|---|---|---|---|---|---|---|"]
    for h, p in res["path"].items():
        if h == "D0intra":
            continue
        L.append("| D+%s | %d | %s | %s | %s | %s | %.1f | %.1f |" % (h, p["n"], pc(p["ret_mean"]), pc(p["ret_med"]), pc(p["mf_mean"]),
                                                                   pc(p["mf_med"]), 100 * p["pSQ10"], 100 * p["p_ret_le_m10"]))
    p = res["path"]["D0intra"]
    L += ["", "ret D0 intraday (P0 / close nến đầu − 1): mean %s, median %s, n %d" % (pc(p["mean"]), pc(p["med"]), p["n"]), "",
          "## Chiến lược (net %/lệnh sau phí 0,112 + funding exact)", "",
          "| nhánh | n | net mean | net med | CI raw | CI inflate ×1,18 | win% | SL-rate | min | p5 | ret7 mean | funding mean | excess vs ALL (mean/med) | excess CI raw |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, a in res["strategy"].items():
        x = a["all"]
        L.append("| %s | %d | **%s** | %s | %s | %s | %.1f | %.1f | %s | %s | %s | %s | %s / %s | %s |" % (
            arm, x["n"], pc(x["mean"]), pc(x["median"]), ci_s(x["ci_raw"]), ci_s(x["ci_infl"]), 100 * x["win"], 100 * x["sl_rate"],
            pc(x["min"]), pc(x["p5"]), pc(x["ret7_mean"]), pc(x["fund_mean"], 3), pc(x["excess_mean"]), pc(x["excess_med"]),
            ci_s(x["excess_ci_raw"])))
    L += ["", "## Theo năm (năm của t0)", "", "| nhánh | năm | n | net mean | net med | CI raw | SL-rate | funding | excess |", "|---|---|---|---|---|---|---|---|---|"]
    for arm, a in res["strategy"].items():
        for y, b in a["by_year"].items():
            if not b.get("n"):
                L.append("| %s | %s | 0 | — | — | — | — | — | — |" % (arm, y)); continue
            L.append("| %s | %s | %d | %s | %s | %s | %.1f | %s | %s |" % (arm, y, b["n"], pc(b["mean"]), pc(b["median"]), ci_s(b["ci_raw"]),
                                                                       100 * b["sl_rate"], pc(b["fund_mean"], 3), pc(b["excess_mean"])))
    L += ["", "## Độ nhạy (CHỈ BÁO, không vào GO)", "", "| nhánh | biến thể | n | net mean | CI raw | năm dương |", "|---|---|---|---|---|---|"]
    for arm, a in res["strategy"].items():
        for k in ("sens_SLclose", "sens_nofund", "sens_no_rename"):
            b = a[k]
            L.append("| %s | %s | %d | %s | %s | %d/4 |" % (arm, k, b["n"], pc(b["mean"]), ci_s(b["ci_raw"]), b["years_pos"]))
    L += ["", "## Luật GO", "", "| nhánh | G1 (mean>0, CI raw & infl lo>0) | G2 (≥3/4 năm) | G3 (n≥120) | G4 (excess>0) | PASS |", "|---|---|---|---|---|---|"]
    for arm, a in res["strategy"].items():
        g = a["GO"]
        L.append("| %s | %s (%s; lo raw %s; lo infl %s) | %s (%d/4) | %s (%d) | %s (%s) | **%s** |" % (
            arm, g["G1"], pc(g["G1_detail"]["mean"]), pc(g["G1_detail"]["ci_raw_lo"]), pc(g["G1_detail"]["ci_infl_lo"]),
            g["G2"], g["G2_years_pos"], g["G3"], g["G3_n"], g["G4"], pc(g["G4_excess"]), g["PASS"]))
    L += ["", "**VERDICT: %s**" % res["verdict"]]
    return "\n".join(L)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t00 = time.time()
    C, names, t_start, finfo = load_hourly()
    fund = Fund()
    res = dict(prereg=PREREG, infl=INFL, fee=FEE, sl=SL_X, hold_h=HOLD, sanity=dict(file=finfo))
    L, gap, S1, ucols, fl, lastc = find_listings(C, names, t_start, res)
    res["sanity"]["S1"] = S1
    log.info("listing L2=%d, L3b gap excluded=%d", S1["n_L2"], len(gap))
    usd_all = np.array([i for i, n in enumerate(names) if n.endswith("USDT") and "_" not in n])
    ren = rename_like(L, names, usd_all, fl)
    res["sanity"]["S5_rename_like"] = ren
    D, excl = build_arms(C, names, t_start, L, ucols, fund)
    res["sanity"]["S1"]["excluded"] = {k: dict(n=len(v), syms=v) for k, v in excl.items()}
    sanity(C, t_start, L, D, lastc, fund, res)
    log.info("S1 %s", json.dumps({k: v for k, v in res["sanity"]["S1"].items() if k != "L3b_gap_excluded"}, default=str))
    log.info("S3 %s", res["sanity"]["S3"]); log.info("S4 %s", res["sanity"]["S4"])
    for s in res["sanity"]["S2_samples"]:
        log.info("S2 %s", s)
    log.info("S5 rename-like %d: %s", len(ren), ren)
    res["path"] = path_table(D["D0"])
    res["funding_D0_D7"] = funding_table(L, D["D0"], fund)
    log.info("funding %s", res["funding_D0_D7"])
    res["strategy"] = strategy(D, ren)
    res["verdict"] = "GO" if any(a["GO"]["PASS"] for a in res["strategy"].values()) else "NO-GO"
    res["trades_D0"] = D["D0"].drop(columns=[c for c in D["D0"].columns if c.startswith("ret_") or c.startswith("mf_")]).round(6).to_dict("records")
    md = write_md(res)
    open(OUT_MD, "w").write(md)
    json.dump(res, open(OUT_JSON, "w"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log.info("WROTE %s + %s (%.0fs)", OUT_JSON, OUT_MD, time.time() - t00)
    print(md)


if __name__ == "__main__":
    main()
