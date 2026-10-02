#!/usr/bin/env python3
"""short_v3_r3_breakdown.py — R3 PROGRAM_SHORT_V3 (a8eff3fb): BREAKDOWN MOMENTUM (cascade xa).

Pre-reg: docs/prereg/PREREG_SHORT_V3_R3.md (8b3e6202). DEV 2022-01-01..2025-12-31, forward <= 2026-01-01 00:00 UTC.
Tai dung harness P0A (short_v2_p0a_statemap.py, KHONG sua): load_hourly, panels (qv cache chi doc), compute_states (tier/bull),
funding_cum (funding exact), ci_block (CI block-7d raw). BRK = pha day 30d + quoteVol >= 2x median30 + r1d <= -5%, cooldown 7d.
Out: docs/result/RESULT_SHORT_V3_R3.json ; bang markdown -> ~/claude_master/1002/r3_tables.md
"""
import json, logging, os, sys, time
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import short_v2_p0a_statemap as P  # noqa: E402

OUT_JSON = os.path.join(REPO, "docs/result/RESULT_SHORT_V3_R3.json")
OUT_MD = "/home/ubuntu/claude_master/1002/r3_tables.md"
T_LIST = (3, 7)
INFL = 1.18                      # nhan nua-do-rong CI (pre-reg §5)
YEARS = (2022, 2023, 2024, 2025)
H, FEE, SL_X, SL_LOSS = P.H, P.FEE, P.SL_X, P.SL_LOSS
GROUPS = ["BRK", "BNV", "ALL"]
TIERN = {3: "LON", 2: "VUA", 1: "NHO"}
log = logging.getLogger("r3")


def cooldown(raw):
    """Entry tai d neu raw va khong co entry cung coin tai d-1..d-7 (d+8 duoc phep). Chuoi bat dau DEV0."""
    A = raw.to_numpy(bool)
    out = np.zeros_like(A)
    last = np.full(A.shape[1], -10**9)
    i0 = int(raw.index.searchsorted(P.DEV0))
    for i in range(i0, A.shape[0]):
        m = A[i] & ((i - last) > 7)
        out[i] = m
        last[m] = i
    return pd.DataFrame(out, index=raw.index, columns=raw.columns)


def indicators(close, qv, coins):
    """Chi dung ngay <= d cho hang d."""
    cl = close[coins]
    qp = qv[coins].where(qv[coins] > 0)
    lo30 = cl.shift(1).rolling(30, min_periods=30).min()
    r1 = cl / cl.shift(1) - 1
    mqv = qp.shift(1).rolling(30, min_periods=20).median()
    dev = np.asarray((cl.index >= P.DEV0) & (cl.index <= P.DEV1))
    E = (cl.notna() & cl.shift(1).notna() & lo30.notna() & mqv.notna() & qp.notna())
    E.loc[~dev] = False
    core = E & (cl <= lo30) & (r1 <= -0.05)
    rawB = core & (qp >= 2 * mqv)
    rawN = core
    return dict(lo30=lo30, r1=r1, mqv=mqv, qvr=qp / mqv, E=E, rawB=rawB, rawN=rawN,
                entB=cooldown(rawB), entN=cooldown(rawN))


def sanity_causal(close, qv, coins, I):
    rep = {}
    keys = ["lo30", "r1", "mqv", "E", "rawB", "rawN", "entB", "entN"]
    for cut in ("2022-06-15", "2023-09-01", "2025-03-10"):
        cut = pd.Timestamp(cut)
        rng = np.random.default_rng(1)
        c2 = close.copy(); q2 = qv.copy()
        m = c2.index > cut
        c2.loc[m] = rng.uniform(0.01, 100, size=c2.loc[m].shape)
        q2.loc[m] = rng.uniform(1e3, 1e9, size=q2.loc[m].shape)
        I2 = indicators(c2, q2, coins)
        okk = {}
        for k in keys:
            a = I[k].loc[:cut].to_numpy(float); b = I2[k].loc[:cut].to_numpy(float)
            okk[k] = bool(np.array_equal(a, b, equal_nan=True))
        # doi chung: sau ngay cat phai KHAC (test co suc manh)
        okk["_after_differs_rawN"] = bool(not np.array_equal(I["rawN"].loc[cut:].to_numpy(), I2["rawN"].loc[cut:].to_numpy()))
        rep[str(cut.date())] = okk
        assert all(v for k, v in okk.items() if not k.startswith("_")), "CAUSAL FAIL %s: %s" % (cut.date(), okk)
    return rep


def forward(I, S, C, names, t_start, cumF, hasF, coins):
    """1 quan sat / coin-ngay E (ALL); co flag BRK/BNV (sau cooldown)."""
    n2c = {n: j for j, n in enumerate(names)}
    cj = np.array([n2c.get(c, -1) for c in coins])
    E = I["E"]; eB = I["entB"]; eN = I["entN"]; tier = S["tier"][coins]; bull = S["bull"]
    out = []
    for d in pd.date_range(P.DEV0, P.DEV1, freq="D"):
        ok = E.loc[d].to_numpy(bool) & (cj >= 0)
        if not ok.any():
            continue
        t0 = int((d + pd.Timedelta(days=1)).value // 10**6)
        h0 = (t0 - t_start) // H
        cols = cj[ok]
        P0 = C[h0, cols].astype(np.float64)
        for T in T_LIST:
            L = 24 * T
            if t0 + L * H > P.DEV_END_MS:
                continue
            W = C[h0 + 1:h0 + L + 1, cols].astype(np.float64)
            anyv = np.isfinite(W).any(axis=0) & np.isfinite(P0)
            Wf = pd.DataFrame(W).ffill().to_numpy()
            ret = Wf[-1] / P0 - 1
            trunc = ~np.isfinite(W[-1])
            mf = np.nanmax(np.where(np.isfinite(W), W, -np.inf), axis=0) / P0 - 1
            hit = W >= (1 + SL_X) * P0[None, :]
            sl = hit.any(axis=0)
            kx = np.where(sl, np.argmax(hit, axis=0) + 1, L)
            fund = cumF[h0 + kx, cols] - cumF[h0, cols]
            fund_full = cumF[h0 + L, cols] - cumF[h0, cols]
            pnl = np.where(sl, -SL_LOSS, -ret) - FEE + fund
            pnl_nosl = -ret - FEE + fund_full
            o = pd.DataFrame(dict(date=d, T=T, sym=np.array(coins)[ok], B=eB.loc[d].to_numpy(bool)[ok],
                                  N=eN.loc[d].to_numpy(bool)[ok], tier=tier.loc[d].to_numpy()[ok], bull=float(bull.loc[d]),
                                  ret=ret.astype(np.float32), maxfav=mf.astype(np.float32), sl=sl,
                                  fund=fund.astype(np.float32), fund_full=fund_full.astype(np.float32),
                                  pnl=pnl.astype(np.float32), pnl_nosl=pnl_nosl.astype(np.float32),
                                  trunc=trunc, hasf=hasF[cols]))
            out.append(o[anyv])
    df = pd.concat(out, ignore_index=True)
    df["year"] = df["date"].dt.year
    g = df.groupby(["T", "date"])
    df["excess"] = df["ret"] - g["ret"].transform("mean")
    df["excess_pnl"] = df["pnl"] - g["pnl"].transform("mean")
    df["sq_all_day"] = g["maxfav"].transform(lambda x: (x >= 0.10).mean())
    return df


def ci(pnl, dates):
    lo, hi, _, _ = P.ci_block(np.asarray(pnl, np.float64), dates)
    if lo is None:
        return None, None
    mu = float(np.mean(np.asarray(pnl, np.float64)))
    return [lo, hi], [mu - (mu - lo) * INFL, mu + (hi - mu) * INFL]


def stats(g, full=True):
    if len(g) == 0:
        return dict(n=0)
    ret = g.ret.to_numpy(np.float64); pnl = g.pnl.to_numpy(np.float64); sl = g.sl.to_numpy(bool)
    r = dict(n=int(len(g)), bleed_mean=float(ret.mean()), bleed_med=float(np.median(ret)),
             excess=float(g.excess.astype(np.float64).mean()), excess_short=float(-g.excess.astype(np.float64).mean()),
             excess_pnl=float(g.excess_pnl.astype(np.float64).mean()),
             pSQ10=float((g.maxfav >= 0.10).mean()), pSQ20=float((g.maxfav >= 0.20).mean()),
             pSQ10_all_matched=float(g.sq_all_day.mean()), p_ret_le_m10=float((ret <= -0.10).mean()),
             fund=float(g.fund.astype(np.float64).mean()), sl_rate=float(sl.mean()), netproxy=float(pnl.mean()),
             netproxy_noSL=float(g.pnl_nosl.astype(np.float64).mean()),
             E_ret_SL=float(ret[sl].mean()) if sl.any() else None)
    if full:
        r["ci_raw"], r["ci_infl"] = ci(pnl, g.date)
        r["ci_raw_noSL"], _ = ci(g.pnl_nosl.to_numpy(np.float64), g.date)
        r["ci_raw_excess_short"], _ = ci(-g.excess.to_numpy(np.float64), g.date)
    return r


def gmask(df, g):
    if g == "ALL":
        return np.ones(len(df), bool)
    return df[{"BRK": "B", "BNV": "N"}[g]].to_numpy(bool)


def pc(x, nd=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else ("%+.*f" % (nd, 100 * x))


def ci_s(c):
    return "—" if not c or c[0] is None else "[%s;%s]" % (pc(c[0]), pc(c[1]))


def run():
    t00 = time.time()
    C, names, t_start = P.load_hourly()
    close, qv, lastc, nrec, coins = P.panels(C, names, t_start)
    del lastc
    log.info("panel %s coins=%d", close.shape, len(coins))
    I = indicators(close, qv, coins)
    res = dict(prereg="docs/prereg/PREREG_SHORT_V3_R3.md@8b3e6202", program="docs/research/PROGRAM_SHORT_V3.md@a8eff3fb",
               infl=INFL, sanity={})
    San = res["sanity"]
    San["S_b_causal"] = sanity_causal(close, qv, coins, I)
    log.info("S-b causal OK %s", San["S_b_causal"])
    # S-d (phan 1): BRK ⊆ BNV ; cooldown
    assert not (I["rawB"] & ~I["rawN"]).to_numpy().any(), "BRK not subset BNV"
    for k in ("entB", "entN"):
        A = I[k].to_numpy(bool)
        for j in np.where(A.any(axis=0))[0]:
            ix = np.where(A[:, j])[0]
            assert (np.diff(ix) > 7).all(), "cooldown fail %s %s" % (k, coins[j])
    S = P.compute_states(close, qv, coins)
    Sa = {}
    yr = I["E"].index.year
    for y in YEARS:
        m = yr == y
        Sa[str(y)] = {k: int(I[k].loc[m].to_numpy().sum()) for k in ("E", "rawB", "entB", "rawN", "entN")}
        Sa[str(y)]["days_with_BRK"] = int(I["entB"].loc[m].any(axis=1).sum())
        Sa[str(y)]["max_BRK_per_day"] = int(I["entB"].loc[m].sum(axis=1).max())
    nE = int(I["E"].to_numpy().sum())
    res["cover"] = dict(BRK=int(I["entB"].to_numpy().sum()) / nE, BNV=int(I["entN"].to_numpy().sum()) / nE, ALL=1.0,
                        BRK_raw=int(I["rawB"].to_numpy().sum()) / nE, BNV_raw=int(I["rawN"].to_numpy().sum()) / nE)
    San["S_a"] = dict(n_E_dev=nE, by_year=Sa)
    log.info("S-a %s cover %s", Sa, res["cover"])
    cumF, hasF = P.funding_cum(names, t_start, C.shape[0])
    df = forward(I, S, C, names, t_start, cumF, hasF, coins)
    del cumF
    log.info("forward obs=%d (%.0fs)", len(df), time.time() - t00)
    ob = {}
    for T in T_LIST:
        x = df[df["T"] == T]
        ob[int(T)] = dict(n_all=int(len(x)), n_brk=int(x.B.sum()), n_bnv=int(x.N.sum()), n_trunc=int(x.trunc.sum()),
                          n_trunc_brk=int(x.trunc[x.B].sum()), frac_has_funding=float(x.hasf.mean()),
                          n_sl_ne_pSQ10=int(((x.maxfav >= 0.10) != x.sl).sum()), n_brk_tier_na=int(x.tier[x.B].isna().sum()),
                          brk_by_year={str(y): int(x.B[x.year == y].sum()) for y in YEARS})
    San["obs_by_T"] = ob
    log.info("obs %s", ob)
    # S-c: 10 BRK mau (T=7), rai deu theo thoi gian
    b7 = df[(df["T"] == 7) & df.B].sort_values(["date", "sym"]).reset_index(drop=True)
    smp = []
    for i in np.linspace(0, len(b7) - 1, 10).astype(int):
        r = b7.iloc[i]; d = r.date; s = r.sym
        smp.append(dict(date=str(d.date()), sym=s, close_prev=float(close.at[d - pd.Timedelta(days=1), s]),
                        close=float(close.at[d, s]), r1=round(float(I["r1"].at[d, s]), 4), lo30=float(I["lo30"].at[d, s]),
                        qv_ratio=round(float(I["qvr"].at[d, s]), 2), tier=None if pd.isna(r.tier) else TIERN[int(r.tier)],
                        ret7=round(float(r.ret), 4), maxfav7=round(float(r.maxfav), 4), sl=bool(r.sl)))
    San["S_c_samples"] = smp
    for x in smp:
        log.info("S-c %s", x)
    return res, df


def tables(res, df):
    A = {}; B = {}
    for g in GROUPS:
        mg = gmask(df, g)
        for T in T_LIST:
            sub = df[mg & (df["T"] == T).to_numpy()]
            a = stats(sub)
            yb = {}
            for y in YEARS:
                yb[y] = stats(sub[sub.year == y], full=(T == 7))
                B["%s|%d|%d" % (g, T, y)] = yb[y]
            a["years_pos"] = int(sum(1 for y in YEARS if yb[y].get("n") and yb[y]["netproxy"] > 0))
            a["years_gt_0p5"] = int(sum(1 for y in YEARS if yb[y].get("n") and yb[y]["netproxy"] > 0.005))
            a["years_pos_noSL"] = int(sum(1 for y in YEARS if yb[y].get("n") and yb[y]["netproxy_noSL"] > 0))
            A["%s|%d" % (g, T)] = a
        log.info("A %s done", g)
    res["A"] = A; res["B"] = B
    Cs = {}
    for T in T_LIST:
        sub = df[df.B & (df["T"] == T)]
        for tv, tn in TIERN.items():
            Cs["%d|tier_%s" % (T, tn)] = stats(sub[sub.tier == tv])
        Cs["%d|bull" % T] = stats(sub[sub.bull == 1.0]); Cs["%d|notbull" % T] = stats(sub[sub.bull == 0.0])
    res["C_slices"] = Cs
    Dd = {}
    for g in GROUPS:
        for T in T_LIST:
            a = A["%s|%d" % (g, T)]
            Dd["%s|%d" % (g, T)] = dict(neg_bleed=-a["bleed_mean"], sl_convexity=a["sl_rate"] * ((a["E_ret_SL"] or 0) - SL_LOSS),
                                        fund=a["fund"], fee=-FEE, netproxy=a["netproxy"], netproxy_noSL=a["netproxy_noSL"])
    res["D_decomp"] = Dd
    G = {}
    for T in T_LIST:
        a = A["BRK|%d" % T]; al = A["ALL|%d" % T]
        g1 = a["netproxy"] > 0.005
        g2 = a["ci_raw"][0] is not None and a["ci_raw"][0] > 0 and a["ci_infl"][0] > 0
        g3 = a["years_pos"] >= 3
        g4 = a["excess_short"] > 0.003
        g5 = a["pSQ10"] <= 0.8 * al["pSQ10"]
        G["BRK|%d" % T] = dict(netproxy=a["netproxy"], G1=bool(g1), ci_raw=a["ci_raw"], ci_infl=a["ci_infl"], G2=bool(g2),
                               years_pos=a["years_pos"], G3=bool(g3), excess_short=a["excess_short"], G4=bool(g4),
                               pSQ10=a["pSQ10"], pSQ10_ALL=al["pSQ10"], ratio=a["pSQ10"] / al["pSQ10"], G5=bool(g5),
                               PASS=bool(g1 and g2 and g3 and g4 and g5),
                               info_ci_lo_gt_0p5=bool(a["ci_raw"][0] is not None and a["ci_infl"][0] > 0.005),
                               info_years_gt_0p5=a["years_gt_0p5"], info_pSQ10_ALL_matched=a["pSQ10_all_matched"])
    res["E_go"] = G
    res["verdict"] = "GO" if any(v["PASS"] for v in G.values()) else "NO-GO"
    log.info("VERDICT %s %s", res["verdict"], G)
    return res


def write_md(res):
    L = ["## A. [BRK, BNV, ALL] × T (toàn DEV; %; maxFav/SL trên 1h closes = cận dưới squeeze)", "",
         "| nhóm | T | n | cover | bleed mean | bleed med | excess_short | excess pnl | pSQ10 | pSQ20 | P(ret≤−10%) | funding | SL% | "
         "netproxy | CI raw | CI infl ×1,18 | netproxy noSL | CI raw noSL | năm >0 | năm >0,5 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for g in GROUPS:
        for T in T_LIST:
            a = res["A"]["%s|%d" % (g, T)]
            L.append("| %s | %d | %d | %.2f | %s | %s | %s | %s | %.1f | %.1f | %.1f | %s | %.1f | **%s** | %s | %s | %s | %s | %d/4 | %d/4 |" % (
                g, T, a["n"], 100 * res["cover"][g], pc(a["bleed_mean"]), pc(a["bleed_med"]), pc(a["excess_short"]),
                pc(a["excess_pnl"]), 100 * a["pSQ10"], 100 * a["pSQ20"], 100 * a["p_ret_le_m10"], pc(a["fund"], 3),
                100 * a["sl_rate"], pc(a["netproxy"]), ci_s(a["ci_raw"]), ci_s(a["ci_infl"]), pc(a["netproxy_noSL"]),
                ci_s(a["ci_raw_noSL"]), a["years_pos"], a["years_gt_0p5"]))
    L += ["", "## B. Theo năm (np = netproxy; nS = netproxy noSL; bl = bleed mean; ex = excess_short; sq = pSQ10; %)", "",
          "| nhóm | T | 2022 | 2023 | 2024 | 2025 |", "|---|---|---|---|---|---|"]
    for g in GROUPS:
        for T in T_LIST:
            cells = []
            for y in YEARS:
                b = res["B"]["%s|%d|%d" % (g, T, y)]
                if not b.get("n"):
                    cells.append("—"); continue
                s = "np %s · nS %s · bl %s · ex %s · sq %.1f · n %d" % (pc(b["netproxy"]), pc(b["netproxy_noSL"]), pc(b["bleed_mean"]),
                                                                      pc(b["excess_short"]), 100 * b["pSQ10"], b["n"])
                if T == 7:
                    s += " · CI %s" % ci_s(b.get("ci_raw"))
                cells.append(s)
            L.append("| %s | %d | %s |" % (g, T, " | ".join(cells)))
    L += ["", "## C. BRK theo tier / regime (CHỈ báo cáo)", "",
          "| T | lát | n | bleed mean | excess_short | pSQ10 | funding | netproxy | CI raw | netproxy noSL |", "|---|---|---|---|---|---|---|---|---|---|"]
    for k, a in res["C_slices"].items():
        T, sl = k.split("|")
        if a.get("n"):
            L.append("| %s | %s | %d | %s | %s | %.1f | %s | **%s** | %s | %s |" % (T, sl, a["n"], pc(a["bleed_mean"]), pc(a["excess_short"]),
                     100 * a["pSQ10"], pc(a["fund"], 3), pc(a["netproxy"]), ci_s(a["ci_raw"]), pc(a["netproxy_noSL"])))
        else:
            L.append("| %s | %s | 0 | | | | | | | |" % (T, sl))
    L += ["", "## D. Phân rã netproxy = −bleed + SL-convexity + funding − phí (%)", "",
          "| nhóm | T | −bleed | SL-convexity | funding | phí | = netproxy | netproxy noSL |", "|---|---|---|---|---|---|---|---|"]
    for k, d in res["D_decomp"].items():
        g, T = k.split("|")
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (g, T, pc(d["neg_bleed"]), pc(d["sl_convexity"]), pc(d["fund"], 3),
                                                             pc(d["fee"], 3), pc(d["netproxy"]), pc(d["netproxy_noSL"])))
    L += ["", "## E. Luật GO-R3", "",
          "| ô | netproxy | G1 >+0,5% | CI raw | CI infl | G2 lo>0 | năm>0 | G3 ≥3/4 | excess_short | G4 >+0,3% | pSQ10 | pSQ10 ALL | tỉ lệ | G5 ≤0,8 | PASS |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in res["E_go"].items():
        L.append("| %s | %s | %s | %s | %s | %s | %d/4 | %s | %s | %s | %.1f | %.1f | %.2f | %s | **%s** |" % (
            k, pc(v["netproxy"]), v["G1"], ci_s(v["ci_raw"]), ci_s(v["ci_infl"]), v["G2"], v["years_pos"], v["G3"],
            pc(v["excess_short"]), v["G4"], 100 * v["pSQ10"], 100 * v["pSQ10_ALL"], v["ratio"], v["G5"], v["PASS"]))
    L += ["", "**VERDICT: %s**" % res["verdict"]]
    return "\n".join(L)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    res, df = run()
    res = tables(res, df)
    md = write_md(res)
    open(OUT_MD, "w").write(md)
    json.dump(res, open(OUT_JSON, "w"), indent=1, ensure_ascii=False, default=float)
    log.info("WROTE %s + %s", OUT_JSON, OUT_MD)
    print(md)


if __name__ == "__main__":
    main()
