#!/usr/bin/env python3
"""FUNDNEG_T1 run: events, trades (4 variants), overlap flags, controls (100 seeds), stats.
Prereg: docs/prereg/PREREG_FUNDNEG_T1.md (commit 66862db3)."""
import json, os, sys, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import *  # noqa

OUTD = WK + "/out"
os.makedirs(OUTD, exist_ok=True)
THRS = [-0.0005, -0.0010]
HS = [24, 72]
NSEED = 100
X14_STOP = None
t00 = time.time()


def log(*a):
    print("[%6.0fs]" % (time.time() - t00), *a, flush=True)


P = Panel(); log("panel", len(P.key), "syms", len(P.syms))
F = Funding(P); log("funding", len(F.tau), "no-kline rows", F.n_nokline)
U = universe(P); log("universe sizes min/max", U.sum(1).min(), U.sum(1).max())
TER, VOL = vol_terciles(P, U); log("terciles")
L, Linfo = x14_legs(P); log("x14", Linfo)
X14_STOP = int(L.st_ms.max())
BTC = P.code("BTCUSDT")

meta = {"universe_size_min": int(U.sum(1).min()), "universe_size_max": int(U.sum(1).max()),
        "funding_rows": int(len(F.tau)), "funding_rows_no_kline": F.n_nokline, "x14": Linfo,
        "panel_hours": int(len(P.key)), "nsym": int(len(P.syms))}
# universe artefact
urows = [(2022 + mi // 12, mi % 12 + 1, P.syms[c]) for mi in range(48) for c in np.nonzero(U[mi])[0]]
pd.DataFrame(urows, columns=["y", "m", "sym"]).to_csv(OUTD + "/universe.csv", index=False)

inper = (F.tau >= T_DISC0) & (F.tau < T_END)
mi_all = np.where(inper, month_idx(np.where(inper, F.tau, T_DISC0)), 0)
inU = inper & U[mi_all, F.code]


def year_of(t):
    return pd.to_datetime(t, unit="ms").year.values


def boot_ci(net, day, B=10000, seed=20261023):
    if len(net) == 0:
        return [np.nan, np.nan]
    ud, inv = np.unique(day, return_inverse=True)
    s = np.bincount(inv, weights=net)
    c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(ud), size=(B, len(ud)))
    m = s[idx].sum(1) / c[idx].sum(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def sleeve(t_in, t_out, net, years):
    ev = sorted([(t_out[i], 0, i) for i in range(len(net))] + [(t_in[i], 1, i) for i in range(len(net))])
    E, alloc, peak, mdd, conc, mconc = 1.0, {}, 1.0, 0.0, 0, 0
    for t, typ, i in ev:
        if typ == 1:
            alloc[i] = 0.02 * E; conc += 1; mconc = max(mconc, conc)
        else:
            E += alloc.pop(i) * net[i]; conc -= 1
            peak = max(peak, E); mdd = min(mdd, E / peak - 1)
    cagr = E ** (1 / years) - 1 if years > 0 else np.nan
    return dict(final_equity=E, cagr=cagr, maxdd=mdd, max_concurrent=mconc)


def stats(T, ctrl, sel, period):
    t0, t1 = (T_DISC0, T_TEST0) if period == "DISC" else (T_TEST0, T_END)
    m = sel & (T.tau.values >= t0) & (T.tau.values < t1)
    x = T[m]
    net = x.net.values
    r = dict(n=int(m.sum()))
    if r["n"] == 0:
        return r
    yrs = year_of(x.tau.values)
    r["n_by_year"] = {int(y): int((yrs == y).sum()) for y in np.unique(yrs)}
    r.update(mean_net=float(net.mean()), median_net=float(np.median(net)), hit=float((net > 0).mean()),
             mean_net2=float(x.net2.mean()), mean_gross=float(x.gross.mean()), mean_fund=float(x.fund.mean()),
             mean_nset=float(x.nset.mean()), sd_net=float(net.std(ddof=1)) if len(net) > 1 else np.nan,
             ci95_day=boot_ci(net, x.tau.values // DMS), n_days=int(len(np.unique(x.tau.values // DMS))),
             mfe_med=float(np.nanmedian(x.mfe)), mae_med=float(np.nanmedian(x.mae)),
             n_delist=int(x.delist.sum()), n_gap=int(x.gap.sum()))
    r["mean_by_year"] = {int(y): float(net[yrs == y].mean()) for y in np.unique(yrs)}
    sym_n = x.groupby("sym").size().sort_values(ascending=False)
    sym_s = x.groupby("sym").net.sum()
    top = sym_n.index[:5]
    r["n_sym"] = int(len(sym_n))
    r["top5_sym"] = {s: [int(sym_n[s]), float(sym_s[s])] for s in top}
    r["top5_share_n"] = float(sym_n.iloc[:5].sum() / len(x))
    tot = float(net.sum())
    r["sum_net"] = tot
    r["top5_share_sumnet"] = float(sym_s[top].sum() / tot) if tot != 0 else np.nan
    r["mean_net_ex_top5"] = float(x[~x.sym.isin(top)].net.mean()) if (~x.sym.isin(top)).any() else np.nan
    ok7 = np.isfinite(x.btc7.values)
    r["corr_btc7_pearson"] = float(np.corrcoef(net[ok7], x.btc7.values[ok7])[0, 1])
    r["corr_btc7_spearman"] = float(pd.Series(net[ok7]).corr(pd.Series(x.btc7.values[ok7]), method="spearman"))
    okh = np.isfinite(x.btch.values)
    r["corr_btchold_pearson"] = float(np.corrcoef(net[okh], x.btch.values[okh])[0, 1])
    r["share_btc7_neg"] = float((x.btc7.values[ok7] < 0).mean())
    r["mean_net_btc7_neg"] = float(net[ok7 & (x.btc7.values < 0)].mean()) if (ok7 & (x.btc7.values < 0)).any() else np.nan
    r["mean_net_btc7_pos"] = float(net[ok7 & (x.btc7.values >= 0)].mean()) if (ok7 & (x.btc7.values >= 0)).any() else np.nan
    r["n_after_x14_stop"] = int((x.tau.values > X14_STOP).sum())
    r["sleeve"] = sleeve(x.t_in.values, x.t_out.values, net, 2.0)
    cm = ctrl[:, m]
    cmeans = np.nanmean(cm, axis=1)
    r["ctrl_mean_p50"] = float(np.percentile(cmeans, 50))
    r["ctrl_mean_p95"] = float(np.percentile(cmeans, 95))
    r["ctrl_nan_events"] = int(np.isnan(cm[0]).sum())
    return r


results = {"meta": meta, "variants": {}}
allT = []
for thr in THRS:
    ev = inU & (F.f8 <= thr)
    raw_cnt = {"all_syms": {int(y): int(c) for y, c in zip(*np.unique(year_of(F.tau[inper & (F.f8 <= thr)]), return_counts=True))},
               "in_universe": {int(y): int(c) for y, c in zip(*np.unique(year_of(F.tau[ev]), return_counts=True))}}
    for Hh in HS:
        name = "thr%.2f_H%d" % (thr * 100, Hh)
        codes, taus = F.code[ev], F.tau[ev]
        beyond = taus + Hh * HMS + MMS > DATA_LAST
        codes, taus = codes[~beyond], taus[~beyond]
        e = evaluate(P, F, codes, taus, Hh, with_path=False)
        okp = np.isfinite(e["P0"]) & np.isfinite(e["P1"])
        n_noentry = int((~np.isfinite(e["P0"])).sum())
        n_noexit = int((np.isfinite(e["P0"]) & ~np.isfinite(e["P1"])).sum())
        codes, taus = codes[okp], taus[okp]
        t_in = taus + 2 * MMS
        t_out = e["t_out"][okp]
        # one position per coin
        o = np.lexsort((taus, codes))
        keep = np.zeros(len(codes), dtype=bool)
        last_c, last_out = -1, -1
        for i in o:
            if codes[i] != last_c:
                last_c, last_out = codes[i], -1
            if t_in[i] >= last_out:
                keep[i] = True
                last_out = t_out[i]
        codes, taus = codes[keep], taus[keep]
        assert len(set(zip(codes.tolist(), taus.tolist()))) == len(codes), "dup (sym,tau) in events"
        e = evaluate(P, F, codes, taus, Hh, with_path=True)
        assert (e["t_in"] > taus).all()
        T = pd.DataFrame({k: v for k, v in e.items()})
        T.insert(0, "tau", taus)
        T.insert(0, "code", codes)
        T.insert(0, "sym", P.syms[codes])
        fi = np.searchsorted(F.fkey, codes * FK + taus)
        assert (F.fkey[fi] == codes * FK + taus).all()
        T["f8"] = F.f8[fi]
        T["rate"] = F.rate[fi]
        T["interval_h"] = F.interval_h[fi]
        th = taus // HMS
        b0 = P.lookup(P.c01, np.full(len(th), BTC), th)
        T["btc7"] = b0 / P.lookup(P.c01, np.full(len(th), BTC), th - 168) - 1
        T["btch"] = P.lookup(P.c01, np.full(len(th), BTC), th + Hh) / b0 - 1
        fa, fb = overlap_flags(L, T.sym.values, taus)
        T["ov_sym24"], T["ov_crashday"] = fa, fb
        T["overlap"] = fa | fb
        di = taus // DMS - DAY0
        mi = month_idx(taus)
        T["ter"] = TER[di, codes]
        # controls
        cand_e, cand_c = [], []
        n_pool_all = 0
        for j in range(len(T)):
            u = U[mi[j]].copy()
            if T.ter.values[j] >= 0:
                u &= TER[di[j]] == T.ter.values[j]
            else:
                n_pool_all += 1
            u[codes[j]] = False
            cc = np.nonzero(u)[0]
            cand_e.append(np.full(len(cc), j)); cand_c.append(cc)
        cand_e = np.concatenate(cand_e); cand_c = np.concatenate(cand_c)
        ce = evaluate(P, F, cand_c, taus[cand_e], Hh, with_path=False)
        okc = np.isfinite(ce["P0"]) & np.isfinite(ce["P1"])
        cand_e, cnet = cand_e[okc], ce["net"][okc]
        o = np.argsort(cand_e, kind="stable")
        cand_e, cnet = cand_e[o], cnet[o]
        start = np.searchsorted(cand_e, np.arange(len(T)))
        size = np.searchsorted(cand_e, np.arange(len(T)), side="right") - start
        ctrl = np.full((NSEED, len(T)), np.nan)
        has = size > 0
        for s in range(NSEED):
            rng = np.random.default_rng(1000 + s)
            dr = rng.integers(0, np.maximum(size, 1))
            ctrl[s, has] = cnet[(start + dr)[has]]
        T["pool_size"] = size
        v = {"raw_counts": raw_cnt, "n_beyond_data": int(beyond.sum()), "n_no_entry": n_noentry,
             "n_no_exit": n_noexit, "n_dropped_onepos": int((~keep).sum()), "n_trades_all": int(len(T)),
             "n_pool_whole_universe": n_pool_all, "pool_size_med": float(np.median(size))}
        non = ~T.overlap.values
        allsel = np.ones(len(T), dtype=bool)
        for setname, sel in [("NON", non), ("ALL", allsel)]:
            for per in ["DISC", "TEST"]:
                v["%s_%s" % (setname, per)] = stats(T, ctrl, sel, per)
        # criteria on NON
        a, b = v["NON_TEST"], v["NON_DISC"]
        F1 = a.get("n", 0) > 0 and a["mean_net"] > 0 and a["ci95_day"][0] > 0
        F2 = b.get("n", 0) > 0 and b["mean_net"] > 0
        F3 = a.get("n", 0) > 0 and all(a["n_by_year"].get(y, 0) >= 50 for y in (2024, 2025))
        F4 = a.get("n", 0) > 0 and b.get("n", 0) > 0 and a["mean_net"] > a["ctrl_mean_p95"] and b["mean_net"] > b["ctrl_mean_p95"]
        F5 = a.get("n", 0) > 0 and a["mean_net2"] > 0
        verdict = "GO" if all([F1, F2, F3, F4, F5]) else ("UNG_VIEN" if (F1 and F2 and F3) else "NO-GO")
        v["criteria"] = dict(F1=bool(F1), F2=bool(F2), F3=bool(F3), F4=bool(F4), F5=bool(F5), verdict=verdict)
        results["variants"][name] = v
        T["variant"] = name
        T.to_parquet(OUTD + "/trades_%s.parquet" % name, index=False)
        np.save(OUTD + "/ctrl_%s.npy" % name, ctrl)
        log(name, "trades", len(T), "NON", int(non.sum()), v["criteria"])

with open(OUTD + "/results.json", "w") as fh:
    json.dump(results, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
log("DONE")
