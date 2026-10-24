"""LIQX_S1 V4 (manual print of 1 big MKT episode) + V5 (episodes with ONSET on a day-01 vs Tardis real liquidations)."""
import json
import numpy as np
import pandas as pd
from common import S1, WK, DAY, B5

H = 3_600_000


def spear(a, b):
    a, b = pd.Series(a).rank().values, pd.Series(b).rank().values
    return float(np.corrcoef(a, b)[0, 1]) if len(a) > 2 else np.nan


def coin_month(t):
    ts = pd.Timestamp(t - 1, unit="ms")
    return pd.read_parquet(S1 + "/coin/%04d-%02d.parquet" % (ts.year, ts.month))


def main():
    E = pd.read_parquet(S1 + "/episodes.parquet")
    E = E[E.variant == "main"]
    K = pd.read_parquet(S1 + "/mkt.parquet").set_index("T")
    em = E[E.level == "MKT"].sort_values("depth")
    e = em.iloc[0]
    w = K.loc[e.T_on - 30 * 60000: e.T_end + 30 * 60000]
    cols = ["I_mkt", "r_mkt", "cum60_mkt", "r5_btc", "sOIV0", "sOIdrop", "sTSX", "sP2", "n_valid", "mkt_valid"]
    v4 = w[cols].copy()
    v4.index = [pd.Timestamp(t, unit="ms").strftime("%m-%d %H:%M") for t in w.index]
    g = coin_month(e.T_peak)
    g["sym"] = g.sym.astype(str)
    pk = g[(g["T"] == e.T_peak) & g.valid].sort_values("P2", ascending=False)
    chk = float(abs(pk.P2.sum() - K.loc[e.T_peak, "sP2"]))
    out = dict(V4=dict(T_on=pd.Timestamp(e.T_on, unit="ms").isoformat(), T_peak=pd.Timestamp(e.T_peak, unit="ms").isoformat(),
                       T_exh=pd.Timestamp(e.T_exh, unit="ms").isoformat() if e.T_exh >= 0 else None,
                       T_end=pd.Timestamp(e.T_end, unit="ms").isoformat(), depth=float(e.depth), I_peak=float(e.I_peak),
                       sP2_peak_recomputed_absdiff=chk,
                       top_coins_at_peak=pk.head(8)[["sym", "P2", "oiv0", "oidrop", "tsx", "r5", "I"]].round(6).to_dict("records")))
    print(v4.to_string(float_format=lambda x: "%.5g" % x))
    v4.to_csv(S1 + "/v4_series.csv")
    # V5
    rows = []
    for _, e in E.iterrows():
        d = (e.T_on - 1) // DAY * DAY
        ts = pd.Timestamp(d, unit="ms")
        if ts.day != 1 or not (2022 <= ts.year <= 2025):
            continue
        f = WK + "/tardis/liquidations_%04d-%02d-01_PERPETUALS.csv.gz" % (ts.year, ts.month)
        t = pd.read_csv(f, dtype={"timestamp": "int64"})
        t = t[t.side == "sell"]
        t["T"] = (t.timestamp // 1000 // B5 + 1) * B5
        t["usd"] = t.price * t.amount
        liq = t.groupby(["symbol", "T"]).usd.sum()
        g = coin_month(e.T_on)
        g["sym"] = g.sym.astype(str)
        lo, hi = e.T_on - 30 * 60000, min(e.T_end, d + DAY)
        g = g[(g["T"] >= lo) & (g["T"] <= hi) & g.valid]
        g["liq"] = [liq.get((s, T), 0.0) for s, T in zip(g.sym, g["T"])]
        if e.level == "COIN":
            z = g[g.sym == e.sym]
            rows.append(dict(level="COIN", sym=e.sym, T_on=ts.isoformat()[:10] + pd.Timestamp(e.T_on, unit="ms").strftime(" %H:%M"),
                             n=int(len(z)), spearman_I_vs_liqfrac=spear(z.I, z.liq / z.oiv0), sum_P2=float(z.P2.sum()),
                             sum_liq_long=float(z.liq.sum()), liq_in_onset_bucket=float(z[z["T"] == e.T_on].liq.sum())))
        else:
            a = g.groupby("T").agg(P2=("P2", "sum"), oiv0=("oiv0", "sum"), liq=("liq", "sum"))
            rows.append(dict(level="MKT", sym="MKT", T_on=pd.Timestamp(e.T_on, unit="ms").isoformat(), n=int(len(a)),
                             spearman_I_vs_liqfrac=spear(a.P2 / a.oiv0, a.liq / a.oiv0), sum_P2=float(a.P2.sum()),
                             sum_liq_long=float(a.liq.sum())))
    out["V5"] = rows
    out["V5_n"] = len(rows)
    if rows:
        r = pd.DataFrame(rows)
        out["V5_summary"] = dict(n_coin=int((r.level == "COIN").sum()), n_mkt=int((r.level == "MKT").sum()),
                                 spearman_median=float(r.spearman_I_vs_liqfrac.median()),
                                 ratio_P2_over_liq_median=float((r.sum_P2 / r.sum_liq_long.replace(0, np.nan)).median()),
                                 frac_with_liq=float((r.sum_liq_long > 0).mean()))
    json.dump(out, open(S1 + "/v45.json", "w"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float)[:5000])


if __name__ == "__main__":
    main()
