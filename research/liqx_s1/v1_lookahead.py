"""LIQX_S1 V1 look-ahead (prereg §12): for 3 MKT main episodes (deepest), multiply raw data AFTER T* (=T_exh, or onset+30')
by 3 and rebuild buckets of [day_on-7, day_on+1] with the pipeline functions; all bucket values with T<=T* must be identical
and ONSET/EXH unchanged. Also checks unperturbed rebuild == mkt.parquet."""
import json
import numpy as np
import pandas as pd
from common import S1, WK, DAY, B5, M1, MAJ, ms, universe, read_kline, read_metrics, detect_conv, apply_conv, build_buckets
from s1_episodes import raw_episodes, exh_idx, LND

H = 3_600_000


def mkt(g, n_hist_med=2016):
    v = g[g.valid]
    va = v[~v.sym.isin(MAJ)]
    a = v.groupby("T").agg(sP2=("P2", "sum"), sOIV0=("oiv0", "sum"), n_valid=("P2", "size"))
    b = va.groupby("T").agg(r_mkt=("r5", "mean"), cum60_mkt=("cum60", "mean"))
    x = pd.concat([a, b], axis=1).reindex(np.sort(g["T"].unique()))
    x["n_valid"] = x.n_valid.fillna(0)
    med = x.n_valid.rolling(n_hist_med, min_periods=1).median()
    ok = (x.n_valid >= 0.85 * med) & (x.n_valid > 0)
    x["I_mkt"] = np.where(ok, x.sP2 / x.sOIV0, np.nan)
    x.loc[~ok, ["r_mkt", "cum60_mkt"]] = np.nan
    return x


def build(day_on, tstar, perturb):
    d0 = day_on - 7 * DAY
    M = ms(pd.Timestamp(day_on, unit="ms").year, pd.Timestamp(day_on, unit="ms").month)
    dq = pd.read_parquet(WK + "/daily_qv.parquet")
    frames = []
    # universe per month of each day
    days = list(range(d0, day_on + 2 * DAY, DAY))
    by_m = {}
    for d in days:
        t = pd.Timestamp(d, unit="ms")
        by_m.setdefault((t.year, t.month), []).append(d)
    for (y, m), dl in by_m.items():
        uni, _ = universe(dq, ms(y, m))
        kl = read_kline(set(uni), dl[0] - DAY - 10 * M1, dl[-1] + 2 * DAY + 10 * M1)
        met = read_metrics(set(uni), dl[0] - DAY, dl[-1] + 2 * DAY)
        conv = detect_conv(met, kl, list(range(dl[0] - DAY, dl[-1] + 2 * DAY, DAY)))
        meff, _ = apply_conv(met, conv)
        if perturb:
            ka = kl.ts >= tstar
            for c in ("close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"):
                kl.loc[ka, c] = kl.loc[ka, c] * 3.0
            ma = meff.ts > tstar
            for c in ("oi", "oi_value"):
                meff.loc[ma, c] = meff.loc[ma, c] * 3.0
        meff = meff[(meff.ts >= dl[0] - B5) & (meff.ts <= dl[-1] + DAY)]
        frames.append(build_buckets(kl, meff, uni, dl))
    return pd.concat(frames, ignore_index=True)


def main():
    th = json.load(open(S1 + "/thresholds.json"))["mkt"]["99.0"]
    E = pd.read_parquet(S1 + "/episodes.parquet")
    em = E[(E.level == "MKT") & (E.variant == "main")].sort_values("depth").head(3)
    K = pd.read_parquet(S1 + "/mkt.parquet").set_index("T")
    out = []
    for _, e in em.iterrows():
        day_on = (e.T_on - 1) // DAY * DAY
        tstar = e.T_exh if e.T_exh >= 0 else e.T_on + 30 * M1
        g0 = build(day_on, tstar, False)
        g1 = build(day_on, tstar, True)
        x0, x1 = mkt(g0), mkt(g1)
        pre = x0.index <= tstar
        cols = ["sP2", "sOIV0", "n_valid", "r_mkt", "cum60_mkt", "I_mkt"]
        a, b = x0.loc[pre, cols].values, x1.loc[pre, cols].values
        same = bool(np.array_equal(np.nan_to_num(a, nan=-9e99), np.nan_to_num(b, nan=-9e99)))
        cb = ["valid", "P2", "oiv0", "r5", "cum60", "I"]
        c0 = g0[g0["T"] <= tstar].sort_values(["sym", "T"])[cb].values.astype(float)
        c1 = g1[g1["T"] <= tstar].sort_values(["sym", "T"])[cb].values.astype(float)
        same_coin = bool(np.array_equal(np.nan_to_num(c0, nan=-9e99), np.nan_to_num(c1, nan=-9e99)))
        post_changed = int((np.nan_to_num(x0.loc[~pre, "I_mkt"].values, nan=-1) != np.nan_to_num(x1.loc[~pre, "I_mkt"].values, nan=-1)).sum())
        # unperturbed vs pipeline (buckets from day_on 00:00 on, full 7d history available)
        sel = x0.index >= day_on
        pk = K.loc[x0.index[sel], "I_mkt"].values
        dpipe = float(np.nanmax(np.abs(pk - x0.loc[sel, "I_mkt"].values))) if np.isfinite(pk).any() else np.nan
        nan_mis = int((np.isnan(pk) != np.isnan(x0.loc[sel, "I_mkt"].values)).sum())
        res = {}
        for tag, x in (("orig", x0), ("x3", x1)):
            xs = x[x.index > day_on - DAY]
            T = xs.index.values.astype(np.int64)
            I = xs.I_mkt.values
            eps = raw_episodes(T, I, np.nan_to_num(xs.cum60_mkt.values, nan=1.0) <= LND["MKT"], th)
            hit = [(int(T[s]), int(T[exh_idx(T, I, xs.r_mkt.values, s, 4.0)]) if exh_idx(T, I, xs.r_mkt.values, s, 4.0) >= 0 else -1)
                   for s, _, _ in eps if T[s] <= tstar]
            res[tag] = hit
        on_ok = any(h[0] == e.T_on for h in res["orig"]) and res["orig"] == res["x3"]
        exh_ok = any(h == (e.T_on, e.T_exh) for h in res["x3"])
        out.append(dict(T_on=pd.Timestamp(e.T_on, unit="ms").isoformat(), T_star=pd.Timestamp(tstar, unit="ms").isoformat(),
                        mkt_pre_identical=same, coin_pre_identical=same_coin, n_pre=int(pre.sum()),
                        post_buckets_changed=post_changed, onset_exh_orig=res["orig"], onset_exh_x3=res["x3"],
                        onset_exh_unchanged=bool(on_ok and exh_ok), max_abs_vs_pipeline=dpipe, nan_mismatch_vs_pipeline=nan_mis,
                        PASS=bool(same and same_coin and on_ok and exh_ok and post_changed > 0)))
        print(json.dumps(out[-1]), flush=True)
    json.dump(out, open(S1 + "/v1.json", "w"), indent=1)


if __name__ == "__main__":
    main()
