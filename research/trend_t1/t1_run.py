"""TREND_T1 runner: strategy V1-V6, cost x2, control 100 seed, X14 comparison, descriptive. Output -> WK/run/ and docs/result/trend_t1/."""
import os, sys, json, copy, time
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t1_core as C

OUT = os.path.join(C.WK, "run"); os.makedirs(OUT, exist_ok=True)
PER = {"dev": ("2022-05-01", "2023-12-31"), "test": ("2024-01-01", "2025-12-31")}
NSEED = int(os.environ.get("NSEED", "100"))
t0 = time.time()
d = C.load_daily(); P = C.build_panel(d); del d
I = C.indicators(P)
inU, members = C.universe(P)
usyms = sorted(set(s for v in members.values() for s in v) | {"BTCUSDT", "ETHUSDT", "SOLUSDT"})
F0, Fr, fev, frep = C.funding(P, usyms)
fev.to_parquet(os.path.join(OUT, "funding_events_used.parquet"), index=False)
umo = [(s, m) for m, v in members.items() for s in v]
dl = set(map(tuple, frep["default_list"]))
frep["u_symmonths"] = len(umo); frep["u_symmonths_default"] = sum(1 for x in umo if x in dl)
frep["u_default_list"] = [x for x in umo if x in dl]
frep.pop("default_list")
json.dump(dict(members=members, funding=frep), open(os.path.join(OUT, "universe_funding.json"), "w"), indent=1)
print("setup", round(time.time() - t0), "s; funding", {k: v for k, v in frep.items() if k != "u_default_list"}, flush=True)

x14 = pd.read_parquet(os.path.join(C.WK, "x14_daily.parquet"))
x14["dms"] = (x14.day.astype("int64") // 10**6).astype(np.int64)
leg = pd.read_parquet(os.path.join(C.WK, "x14_legcov.parquet"))
leg["dms"] = (leg.day.astype("int64") // 10**6).astype(np.int64)
SEEDS = sorted(x14.seed.unique()); MED = "s2024"

def per_stats(ret, days):
    return {k: C.stats(ret, days, a, b) for k, (a, b) in PER.items()}

def x14_cmp(ret, days, seed):
    xs = x14[x14.seed == seed].set_index("dms")["ret"].dropna()
    out = {}
    for k, (a, b) in PER.items():
        m = (days >= int(pd.Timestamp(a).value // 10**6)) & (days <= int(pd.Timestamp(b).value // 10**6))
        s = pd.Series(ret[m], index=days[m])
        j = s.index.intersection(xs.index)
        rt = s.loc[j].values; rx = xs.loc[j].values; rc = 0.7 * rx + 0.3 * rt
        def sh(r): return float(r.mean() / r.std(ddof=1) * np.sqrt(365))
        def dd(r):
            e = np.concatenate([[1.0], np.cumprod(1 + r)]); return float((e / np.maximum.accumulate(e) - 1).min())
        out[k] = dict(n=int(len(j)), first=str(pd.to_datetime(j.min(), unit="ms").date()), last=str(pd.to_datetime(j.max(), unit="ms").date()),
                      corr=float(np.corrcoef(rt, rx)[0, 1]), sh_x14=sh(rx), sh_comb=sh(rc), sh_trend=sh(rt), dd_x14=dd(rx), dd_comb=dd(rc))
    return out

res = {}
for v in C.VARIANTS:
    tv = time.time()
    log = []
    tr = C.select(v, P, I, inU, log=log)
    t1 = copy.deepcopy(tr); R = C.run_engine(t1, P, I, F0, Fr, v)
    t2 = copy.deepcopy(tr); R2 = C.run_engine(t2, P, I, F0, Fr, v, cost=2 * C.COST)
    days = R["days"]
    st = per_stats(R["ret"], days); st2 = per_stats(R2["ret"], days)
    # control
    ctrl = {k: [] for k in PER}
    for sd in range(NSEED):
        rng = np.random.default_rng(10007 + sd)
        ct = C.control_trades(copy.deepcopy(tr), P, I, inU, rng)
        RC = C.run_engine(ct, P, I, F0, Fr, v)
        for k, s in per_stats(RC["ret"], days).items():
            ctrl[k].append(s["sharpe"])
    p95 = {k: float(np.percentile(x, 95)) for k, x in ctrl.items()}
    cmpx = {sd: x14_cmp(R["ret"], days, sd) for sd in SEEDS}
    # descriptive
    T = pd.DataFrame([dict(sym=P["syms"][t["s"]], din=int(P["days"][t["din"]]), dout=(int(P["days"][t["dout"]]) if t["dout"] is not None else None),
                           forced=t["forced"], pnl=t["pnl"], fund=t["fund"], cost=t["cost"], q=t["q"], px_in=t["px_in"], px_out=t["px_out"],
                           w=t.get("w", np.nan), scale=t.get("scale", np.nan), strength=t.get("strength", np.nan), px_fallback=t.get("px_fallback", False)) for t in t1])
    T.to_csv(os.path.join(OUT, "trades_%s.csv" % v), index=False)
    pd.DataFrame(dict(day=days, ret=R["ret"], ret_cost2=R2["ret"], E=R["E"], gross=R["gross"], npos=R["npos"], traded=R["traded"])).to_parquet(os.path.join(OUT, "daily_%s.parquet" % v), index=False)
    desc = {}
    held_day = np.zeros(len(days), bool)
    i0 = int((C.SIM_START - C.DAY0) // C.DAY)
    for t in t1:
        a = t["din"] - i0
        b = (t["dout"] - i0 + (1 if t["forced"] else 0)) if t["dout"] is not None else len(days)
        held_day[max(a, 0):max(b, 0)] = True
    for k, (a, b) in PER.items():
        ams, bms = int(pd.Timestamp(a).value // 10**6), int(pd.Timestamp(b).value // 10**6)
        m = (days >= ams) & (days <= bms); yrs = m.sum() / 365.0
        nt = int(((T.din >= ams) & (T.din <= bms)).sum())
        lg = leg[(leg.seed == MED)].set_index("dms")["has_leg"].reindex(days[m]).fillna(False).values
        nol = ~lg
        desc[k] = dict(cagr=st[k]["cagr"], exposure_days_pct=float(held_day[m].mean() * 100), gross_avg=float(R["gross"][m].mean()),
                       turnover_per_yr=float(R["traded"][m].sum() / R["E"][m].mean() / yrs), trades_per_yr=nt / yrs,
                       x14_noleg_days=int(nol.sum()), trend_pos_on_x14_noleg_pct=float(held_day[m][nol].mean() * 100) if nol.any() else None,
                       x14_noleg_pct_of_days=float(nol.mean() * 100))
    ys = {}
    for y in range(2022, 2026):
        a = "2022-05-01" if y == 2022 else "%d-01-01" % y
        ys[y] = C.stats(R["ret"], days, a, "%d-12-31" % y)["sharpe"]
    T["dt_in"] = pd.to_datetime(T.din, unit="ms")
    coin = {}
    for k, (a, b) in PER.items():
        g = T[(T.dt_in >= a) & (T.dt_in <= b + " 23:59")].groupby("sym").pnl.sum().sort_values()
        coin[k] = dict(top=g.tail(5)[::-1].round(5).to_dict(), bottom=g.head(5).round(5).to_dict())
    nforced = int(T.forced.sum())
    # GO
    m = cmpx[MED]
    G = dict(G1=all(st[k]["sharpe"] >= 0.8 for k in PER), G2=all(st[k]["maxdd"] >= -0.35 for k in PER),
             G3=all(st[k]["sharpe"] > p95[k] for k in PER), G4=all(m[k]["corr"] <= 0.3 for k in PER),
             G5=all(m[k]["sh_comb"] > m[k]["sh_x14"] and m[k]["dd_comb"] >= m[k]["dd_x14"] - 0.03 for k in PER),
             G6=st2["test"]["sharpe"] >= 0.5)
    if all(G.values()): verdict = "GO"
    elif st["test"]["sharpe"] >= 0.8 and 0.5 <= st["dev"]["sharpe"] < 0.8 and all(G[g] for g in ("G2", "G3", "G4", "G5", "G6")): verdict = "UNG_VIEN"
    else: verdict = "NO-GO"
    seedpass = {sd: dict(G4=all(cmpx[sd][k]["corr"] <= 0.3 for k in PER),
                         G5=all(cmpx[sd][k]["sh_comb"] > cmpx[sd][k]["sh_x14"] and cmpx[sd][k]["dd_comb"] >= cmpx[sd][k]["dd_x14"] - 0.03 for k in PER)) for sd in SEEDS}
    res[v] = dict(stats=st, stats_cost2=st2, control_p95=p95, control_median={k: float(np.median(x)) for k, x in ctrl.items()},
                  control_sharpes={k: [round(x, 4) for x in ctrl[k]] for k in PER},
                  x14=cmpx, desc=desc, sharpe_year=ys, coin=coin, n_trades=len(T), n_forced=nforced,
                  n_px_fallback=int(T.px_fallback.sum()), n_scaled=int((T.scale < 1).sum()), gates=G, verdict=verdict, seed_pass=seedpass)
    print(v, verdict, {k: (round(st[k]["sharpe"], 3), round(st[k]["maxdd"], 3), round(p95[k], 3), round(m[k]["corr"], 3), round(m[k]["sh_comb"], 3), round(m[k]["sh_x14"], 3)) for k in PER},
          "cost2 test", round(st2["test"]["sharpe"], 3), G, "secs", round(time.time() - tv), flush=True)
    json.dump(log, open(os.path.join(OUT, "declog_%s.json" % v), "w"))
json.dump(res, open(os.path.join(OUT, "results.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print("DONE", round(time.time() - t0), "s")
