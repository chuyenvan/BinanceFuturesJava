#!/usr/bin/env python3
"""GRID_T1 report: basket metrics E/C, control p95, LOO, crash-buy correlation, episodes."""
import json
import os
import numpy as np
import pandas as pd

WK = os.path.expanduser("~/claude_master/grid_t1_wk")
OUT = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/grid_t1")
TS0 = 1638316800000
DAYMS = 86400000
C_START = pd.Timestamp("2024-01-01")
EPISODES = {"LUNA 2022-05": ("2022-05-07", "2022-05-14"), "3AC 2022-06": ("2022-06-10", "2022-06-19"),
            "FTX 2022-11": ("2022-11-06", "2022-11-13"), "2024-04": ("2024-04-12", "2024-04-17"),
            "2024-08-05": ("2024-08-02", "2024-08-06"), "2025-02-03": ("2025-02-02", "2025-02-04"),
            "2025-03": ("2025-03-03", "2025-03-11"), "2025-10-10": ("2025-10-10", "2025-10-11")}
VAR = ["range_gross", "range_maker", "range_taker", "dyn_g", "dyn_a", "dyn_g_taker"]


def sharpe(r):
    r = np.asarray(r)
    r = r[~np.isnan(r)]
    return float(r.mean() / r.std(ddof=1) * np.sqrt(365)) if len(r) > 5 and r.std() > 0 else float("nan")


def stats(r):
    r = np.asarray(r)
    m = ~np.isnan(r)
    r = r[m]
    if len(r) < 5:
        return {}
    eq = np.cumprod(1 + r)
    dd = float((eq / np.maximum.accumulate(eq) - 1).min())
    wk = pd.Series(r).rolling(7).apply(lambda x: np.prod(1 + x) - 1, raw=True).min()
    return {"sharpe": sharpe(r), "cagr": float(eq[-1] ** (365 / len(r)) - 1), "ret": float(eq[-1] - 1),
            "maxdd": dd, "worst_week": float(wk) if wk == wk else None, "n": int(len(r))}


def basket(R, mask):
    """R: (n_assets, ndays); mask same shape bool. equal-weight daily."""
    x = np.where(mask, R, np.nan)
    with np.errstate(invalid="ignore"):
        return np.nanmean(x, axis=0)


def control_basket(C, mask):
    """C: (n_assets, nseed, ndays) -> (nseed, ndays)"""
    x = np.where(mask[:, None, :], C, np.nan)
    with np.errstate(invalid="ignore"):
        return np.nanmean(x, axis=0)


def main():
    u = json.load(open(os.path.join(WK, "universe.json")))
    vr = json.load(open(os.path.join(OUT, "vr.json")))
    cb = np.load(os.path.expanduser("~/claude_master/tsx/deep_cache/eq_dev.npz"))
    seeds = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
    eqs = []
    for s in seeds:
        a = cb["X14_" + s].astype(np.float64)
        eqs.append(a / a[0])
    eq14m = np.mean(eqs, axis=0)
    eq14 = eq14m[::1440]
    d14 = pd.Timestamp("2021-07-01")
    dates14 = pd.date_range(d14, periods=len(eq14), freq="D")
    r14 = pd.Series(eq14[1:] / eq14[:-1] - 1, index=dates14[1:])

    out = {"prereg_sha256": "75e6d1089f157858bdca96227de88630739c79558af487143b4a351161f85488",
           "vr_gate": {}, "periods": {}}
    for per in ("E", "C"):
        z = np.load(os.path.join(WK, "sim_" + per + ".npz"), allow_pickle=True)
        syms = [str(s) for s in z["syms"]]
        nd = int(z["ndays"])
        start = pd.Timestamp("2022-01-01") if per == "E" else pd.Timestamp("2024-01-01")
        dates = pd.date_range(start, periods=nd, freq="D")
        months = pd.Series(dates).dt.to_period("M").astype(str).values
        picks = u[per]["picks"]
        M = np.zeros((len(syms), nd), bool)
        for i, s in enumerate(syms):
            for k in range(nd):
                if s in ("BTCUSDT", "ETHUSDT") or s in picks.get(months[k], []):
                    M[i, k] = True
        # require data
        for k in VAR:
            M2 = M & ~np.isnan(z[k])
        res = {"n_assets": len(syms), "ndays": nd, "variants": {}, "control": {}, "loo": {}}
        for k in VAR:
            R = z[k]
            msk = M & ~np.isnan(R)
            r = basket(R, msk)
            res["variants"][k] = stats(r)
            res["variants"][k]["n_assets_avg"] = float(np.sum(msk, axis=0).mean())
        # control p95 for range_maker and dyn_g
        for k in ("range_maker", "dyn_g"):
            C = z["ctrl_" + k]
            msk = M & ~np.isnan(z[k])
            cbk = control_basket(C, msk)
            sh = np.array([sharpe(x) for x in cbk])
            real = res["variants"][k]["sharpe"]
            res["control"][k] = {"p05": float(np.nanpercentile(sh, 5)), "p50": float(np.nanmedian(sh)),
                                 "p95": float(np.nanpercentile(sh, 95)),
                                 "frac_above_real": float(np.mean(sh > real)),
                                 "pctile_of_real": float(np.mean(sh < real))}
        # LOO on maker
        for k in ("range_maker", "dyn_g"):
            vals = {}
            R = z[k]
            for i, s in enumerate(syms):
                m2 = (M & ~np.isnan(R)).copy()
                m2[i, :] = False
                vals[s] = sharpe(basket(R, m2))
            res["loo"][k] = {"min": float(np.nanmin(list(vals.values()))),
                             "worst_asset": min(vals, key=lambda x: (vals[x] if vals[x] == vals[x] else 9e9)),
                             "n": len(vals)}
        # correlation with crash-buy X14
        for k in ("range_maker", "dyn_g"):
            r = pd.Series(basket(z[k], M & ~np.isnan(z[k])), index=dates)
            j = pd.concat([r.rename("g"), r14.rename("x")], axis=1).dropna()
            res.setdefault("corr_x14", {})[k] = float(j["g"].corr(j["x"])) if len(j) > 30 else None
            res["corr_x14"][k + "_n"] = int(len(j))
        # episodes
        for k in ("range_maker", "dyn_g"):
            r = pd.Series(basket(z[k], M & ~np.isnan(z[k])), index=dates)
            res.setdefault("episodes", {})[k] = {}
            for nm, (a, b) in EPISODES.items():
                x = r.loc[a:b].dropna()
                if len(x) > 0:
                    res["episodes"][k][nm] = float(np.prod(1 + x) - 1)
        # stats sum
        st = json.loads(str(z["stats"]))
        agg = {}
        for k in VAR:
            agg[k] = {"trades": int(sum(v[k][0] for v in st.values())),
                      "stops": int(sum(v[k][1] for v in st.values())),
                      "fees": float(sum(v[k][2] for v in st.values())),
                      "funding": float(sum(v[k][3] for v in st.values())),
                      "turnover": float(sum(v[k][4] for v in st.values())),
                      "stops_lo": int(sum(v[k][8] for v in st.values())),
                      "stops_hi": int(sum(v[k][9] for v in st.values())),
                      "stops_adx": int(sum(v[k][10] for v in st.values())),
                      "builds": int(sum(v[k][11] for v in st.values())),
                      "active_frac": float(sum(v[k][12] for v in st.values()) / max(1, sum(v[k][14] for v in st.values()))),
                      "avg_gross": float(sum(v[k][13] for v in st.values()) / len(st))}
        res["agg_stats"] = agg
        out["periods"][per] = res

    # VR gate
    for per in ("E", "C"):
        s = vr[per + "_summary"]
        ok = any(s["frac_z_lt_196"][str(q)] >= 0.5 for q in (60, 240, 1440))
        out["vr_gate"][per] = {"pass": bool(ok),
                               "frac": {k: float(v) for k, v in s["frac_z_lt_196"].items()},
                               "median_vr": {k: float(v) for k, v in s["median_vr"].items()},
                               "n_assets": int(s["n_assets"])}
    out["vr_gate"]["pass_both"] = bool(out["vr_gate"]["E"]["pass"] and out["vr_gate"]["C"]["pass"])

    # survival checks
    live = {}
    for k in ("range_maker", "dyn_g"):
        e, c = out["periods"]["E"]["variants"][k], out["periods"]["C"]["variants"][k]
        te, tc = out["periods"]["E"]["variants"][k.replace("maker", "taker") if "range" in k else "dyn_g_taker"], \
                 out["periods"]["C"]["variants"][k.replace("maker", "taker") if "range" in k else "dyn_g_taker"]
        chk = {
            "sharpe_E>=1": e["sharpe"] >= 1.0, "sharpe_C>=1": c["sharpe"] >= 1.0,
            "gt_p95_E": e["sharpe"] > out["periods"]["E"]["control"][k]["p95"],
            "gt_p95_C": c["sharpe"] > out["periods"]["C"]["control"][k]["p95"],
            "maxdd<=20": e["maxdd"] >= -0.20 and c["maxdd"] >= -0.20,
            "taker_pos_E": te["sharpe"] > 0, "taker_pos_C": tc["sharpe"] > 0,
            "loo>=0.5": out["periods"]["E"]["loo"][k]["min"] >= 0.5 and out["periods"]["C"]["loo"][k]["min"] >= 0.5,
        }
        live[k] = {"checks": chk, "alive": bool(all(chk.values())) and out["vr_gate"]["pass_both"]}
    out["survival"] = live
    out["verdict"] = "GO" if any(v["alive"] for v in live.values()) else "NO-GO"
    json.dump(out, open(os.path.join(OUT, "grid_t1_metrics.json"), "w"), indent=1, default=float)
    print(json.dumps({p: {k: {kk: round(vv, 3) if isinstance(vv, float) else vv for kk, vv in v.items() if kk in ("sharpe", "cagr", "maxdd", "worst_week", "n")} for k, v in out["periods"][p]["variants"].items()} for p in ("E", "C")}, indent=1))
    print("VR gate", out["vr_gate"])
    print("survival", json.dumps(out["survival"], indent=1))
    print("verdict", out["verdict"])


if __name__ == "__main__":
    main()
