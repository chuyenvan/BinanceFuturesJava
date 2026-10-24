"""LIQX_S1 step 5: criteria C1-C4 (prereg §10), sensitivity, descriptive tables. Out: S1/score.json + repo artefacts."""
import json
import os
import sys
import numpy as np
import pandas as pd
from common import S1, DAY

FEE = 0.002
OUT = sys.argv[1] if len(sys.argv) > 1 else S1 + "/art"
os.makedirs(OUT, exist_ok=True)


def boot_ci(v, cl, B=10000, seed=7):
    v, cl = np.asarray(v, float), np.asarray(cl)
    if len(v) < 2:
        return [np.nan, np.nan]
    u, inv = np.unique(cl, return_inverse=True)
    s = np.bincount(inv, weights=v)
    c = np.bincount(inv).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(u), size=(B, len(u)))
    m = s[idx].sum(1) / c[idx].sum(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def rank(x, ctrl):
    ok = np.isfinite(ctrl)
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        c = ctrl[i][ok[i]]
        if np.isfinite(x[i]) and len(c):
            out[i] = ((c < x[i]).sum() + 0.5 * (c == x[i]).sum()) / len(c)
    return out


def q(x, f):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(f(x)) if len(x) else np.nan


def main():
    E = pd.read_parquet(S1 + "/episodes.parquet")
    R = pd.read_parquet(S1 + "/ret_entries.parquet")
    RC = np.load(S1 + "/ret_ctrl.npy")
    on = R[R.kind == "ON"].set_index("ep")
    ex = R[R.kind == "EXH"].set_index("ep")
    cols = ["r60", "r240", "r1440", "r4320", "mfe24", "mae24"]
    for c in cols + ["btc_r1440", "n_basket"]:
        if c in on:
            E["on_" + c] = E.ep.map(on[c])
            E["ex_" + c] = E.ep.map(ex[c])
    E["ctrl_mean1440"] = np.nanmean(RC, axis=1)
    E["ctrl_med1440"] = np.nanmedian(RC, axis=1)
    E["rank_exh"] = rank(E.ex_r1440.values, RC)
    E["rank_on"] = rank(E.on_r1440.values, RC)
    E["diff1440"] = E.ex_r1440 - E.on_r1440
    E["day_on"] = (E.T_on - 1) // DAY * DAY
    E["dur_min"] = (E.T_end - E.T_on) / 60000
    E["lag_peak_min"] = (E.T_peak - E.T_on) / 60000
    E["lag_exh_min"] = np.where(E.T_exh >= 0, (E.T_exh - E.T_on) / 60000, np.nan)
    E["lag_exh_after_peak_min"] = np.where(E.T_exh >= 0, (E.T_exh - E.T_peak) / 60000, np.nan)
    res = {}
    for (lvl, vn, per), g in E.groupby(["level", "variant", "period"]):
        ev = g[(g.T_exh >= 0) & g.on_r1440.notna() & g.ex_r1440.notna()]
        cl = ev.ep.values if lvl == "MKT" else ev.day_on.values
        ci = boot_ci(ev.diff1440.values, cl)
        d = dict(n_ep=int(len(g)), n_exh=int((g.T_exh >= 0).sum()), n_eval=int(len(ev)),
                 n_days=int(g.day_on.nunique()),
                 diff_mean=q(ev.diff1440, np.mean), diff_ci=ci, diff_median=q(ev.diff1440, np.median),
                 rank_exh_mean=q(ev.rank_exh, np.mean), rank_exh_median=q(ev.rank_exh, np.median),
                 rank_exh_frac_ge05=q(ev.rank_exh >= 0.5, np.mean), rank_on_mean=q(ev.rank_on, np.mean),
                 mae_exh_median=q(ev.ex_mae24, np.median), mae_on_median=q(ev.on_mae24, np.median),
                 mfe_exh_median=q(ev.ex_mfe24, np.median), mfe_on_median=q(ev.on_mfe24, np.median),
                 dur_median_min=q(g.dur_min, np.median), lag_peak_median_min=q(g.lag_peak_min, np.median),
                 lag_exh_median_min=q(g.lag_exh_min, np.median),
                 lag_exh_after_peak_median_min=q(g.lag_exh_after_peak_min, np.median))
        for k in ("ON", "EXH"):
            p = "on_" if k == "ON" else "ex_"
            for h in ("r60", "r240", "r1440", "r4320"):
                x = ev[p + h]
                d["%s_%s_mean_gross" % (k, h)] = q(x, np.mean)
                d["%s_%s_mean_net" % (k, h)] = q(x - FEE, np.mean)
                d["%s_%s_median_gross" % (k, h)] = q(x, np.median)
                mk = x.notna().values
                d["%s_%s_ci_gross" % (k, h)] = boot_ci(x.values[mk], cl[mk])
                d["%s_%s_hit" % (k, h)] = q(x[mk] > FEE, np.mean)
        d["CTRL_r1440_mean_gross"] = q(ev.ctrl_mean1440, np.mean)
        # ON-only (all episodes with ON ret) for info
        d["ON_all_r1440_mean_gross"] = q(g.on_r1440, np.mean)
        d["ON_all_n"] = int(g.on_r1440.notna().sum())
        d["C1"] = bool(ci[0] > 0)
        d["C2"] = bool(d["rank_exh_mean"] >= 0.6)
        d["C3"] = bool(d["mae_exh_median"] >= d["mae_on_median"])
        d["C4"] = bool(d["n_eval"] >= 15) if lvl == "MKT" else None
        res["%s|%s|%s" % (lvl, vn, per)] = d
    ver = {}
    for lvl in ("MKT", "COIN"):
        for vn in sorted(E.variant.unique()):
            a, b = res.get("%s|%s|A" % (lvl, vn)), res.get("%s|%s|B" % (lvl, vn))
            if a is None or b is None:
                continue
            ok = {c: bool(a[c] and b[c]) for c in ("C1", "C2", "C3")}
            if lvl == "MKT":
                ok["C4"] = bool(a["C4"] and b["C4"])
            ver["%s|%s" % (lvl, vn)] = ok
    m, c = ver.get("MKT|main", {}), ver.get("COIN|main", {})
    if m and not m["C4"]:
        mv = "KHONG_DU_MAU"
    elif m and all(m[k] for k in ("C1", "C2", "C3")):
        mv = "GO"
    else:
        mv = "TRUOT"
    cv = all(c.get(k, False) for k in ("C1", "C2", "C3"))
    verdict = "GO" if mv == "GO" else ("UNG_VIEN_COIN" if cv else ("NO-GO" if mv == "TRUOT" else "KHONG_DU_MAU_MKT" + ("_COIN_DAT" if cv else "")))
    E["year"] = [pd.Timestamp(t, unit="ms").year for t in E.T_on]
    peryear = E.groupby(["level", "variant", "year"]).size().unstack(fill_value=0)
    json.dump(dict(results=res, flags=ver, mkt_verdict=mv, coin_pass=cv, verdict=verdict,
                   per_year={"%s|%s" % k: {str(y): int(n) for y, n in r.items()} for k, r in peryear.iterrows()}),
              open(S1 + "/score.json", "w"), indent=1, default=float)
    em = E[(E.level == "MKT") & (E.variant == "main")].copy()
    for c in ("T_on", "T_end", "T_peak", "T_exh"):
        em[c + "_utc"] = [pd.Timestamp(t, unit="ms").strftime("%Y-%m-%d %H:%M") if t >= 0 else "" for t in em[c]]
    keep = ["ep", "period", "T_on_utc", "T_peak_utc", "T_exh_utc", "T_end_utc", "dur_min", "n_merged", "I_on", "I_peak", "depth",
            "depth_btc", "on_r60", "on_r240", "on_r1440", "on_r4320", "ex_r60", "ex_r240", "ex_r1440", "ex_r4320",
            "on_mae24", "ex_mae24", "on_mfe24", "ex_mfe24", "ctrl_mean1440", "rank_exh", "rank_on", "on_btc_r1440", "on_n_basket"]
    em[keep].to_csv(OUT + "/episodes_mkt_main.csv", index=False, float_format="%.6g")
    em.sort_values("depth").head(20)[keep[:12]].to_csv(OUT + "/top20_mkt.csv", index=False, float_format="%.6g")
    ec = E[E.level == "COIN"]
    ec[["ep", "variant", "period", "sym", "T_on", "T_exh", "T_end", "I_peak", "depth", "on_r1440", "ex_r1440", "rank_exh",
        "on_mae24", "ex_mae24"]].to_parquet(OUT + "/episodes_coin.parquet", index=False)
    print(json.dumps(dict(verdict=verdict, mkt=m, coin=ver.get("COIN|main", {}))))
    for k in sorted(res):
        d = res[k]
        print(k, d["n_ep"], d["n_eval"], "diff %.4f [%.4f, %.4f]" % (d["diff_mean"], *d["diff_ci"]),
              "rank %.3f" % d["rank_exh_mean"], "mae %.4f/%.4f" % (d["mae_exh_median"], d["mae_on_median"]),
              "ON24 %.4f EXH24 %.4f CTRL %.4f" % (d["ON_r1440_mean_gross"], d["EXH_r1440_mean_gross"], d["CTRL_r1440_mean_gross"]))


if __name__ == "__main__":
    main()
