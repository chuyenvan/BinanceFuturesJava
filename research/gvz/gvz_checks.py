#!/usr/bin/env python3
"""GATE_VZ kiem du lieu D2-D5 (PREREG_GATE_VZ.md ee97237b muc 5). Duong code THU HAI (loc truc tiep parquet)."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("gvzc")
D = "/home/ubuntu/claude_master/gvz"
FEAT = D + "/feat/vz_feat.parquet"
STORE = D + "/store/gate_dataset_full.csv"
MET = "/home/ubuntu/claude_master/rex/met"
VZA = ["vzTkr5", "vzTkr15", "vzTkr60", "vzTkr240", "vzTkrBtc15", "vzTkrMed15", "vzQvR60", "vzNtR15"]
VZB = ["vzOiC1h", "vzOiC4h", "vzOiC24h", "vzLsTop", "vzLsAcc"]
SEAL = pd.Timestamp("2026-01-01", tz="Asia/Ho_Chi_Minh").value // 10**6
M = 60_000


def kp(ym):
    return os.path.join(D + "/k2021" if ym < "2021-12" else "/home/ubuntu/vz_e1/raw", "kline1m-%s.parquet" % ym)


def kwin(T, w):
    """nen open time trong [T-w*M, T-M] (doc thang cua T va thang truoc)."""
    lo, hi = T - w * M, T - M
    yms = sorted({pd.Timestamp(lo, unit="ms").strftime("%Y-%m"), pd.Timestamp(hi, unit="ms").strftime("%Y-%m")})
    parts = [pd.read_parquet(kp(y), columns=["ts", "sym", "quote_volume", "taker_buy_quote", "n_trades"],
                             filters=[("ts", ">=", lo), ("ts", "<=", hi)]) for y in yms if y >= "2021-01"]
    d = pd.concat(parts)
    d = d[d.quote_volume > 0].drop_duplicates(["sym", "ts"], keep="last")
    return d


def recompute(T):
    r = {}
    d1440 = kwin(T, 1440)
    for w in (5, 15, 60, 240):
        x = d1440[d1440.ts >= T - w * M]
        r["vzTkr%d" % w] = x.taker_buy_quote.sum() / x.quote_volume.sum()
    x = d1440[(d1440.ts >= T - 15 * M) & (d1440.sym == "BTCUSDT")]
    r["vzTkrBtc15"] = x.taker_buy_quote.sum() / x.quote_volume.sum() if len(x) else np.nan
    x = d1440[d1440.ts >= T - 15 * M].groupby("sym")[["taker_buy_quote", "quote_volume"]].sum()
    x = x[x.quote_volume >= 10_000]
    r["vzTkrMed15"] = float(np.median(x.taker_buy_quote / x.quote_volume))
    q60 = d1440[d1440.ts >= T - 60 * M].quote_volume.sum()
    r["vzQvR60"] = np.log(q60 / (d1440.quote_volume.sum() / 24))
    n15 = d1440[d1440.ts >= T - 15 * M].n_trades.sum()
    r["vzNtR15"] = np.log(n15 / (d1440.n_trades.sum() / 96))
    g = ((T - 10 * M) // 300_000) * 300_000
    y = pd.Timestamp(g, unit="ms").year
    if T >= pd.Timestamp("2021-12-02").value // 10**6:
        fs = [MET + "/metrics5m-%d.parquet" % yy for yy in sorted({y, pd.Timestamp(g - 86_400_000, unit="ms").year})]
        mt = pd.concat([pd.read_parquet(f, columns=["ts", "sym", "oi_value", "toptrader_ls_sum", "ls_cnt"],
                                        filters=[("ts", ">=", g - 86_400_000 - 300_000), ("ts", "<", g + 300_000)])
                        for f in fs])
        mt["g"] = (mt.ts // 300_000) * 300_000
        mt = mt.sort_values(["sym", "ts"]).drop_duplicates(["sym", "g"], keep="last")
        mt = mt[np.isfinite(mt.oi_value) & (mt.oi_value > 0)]
        now = mt[mt.g == g].set_index("sym")
        for name, k in (("vzOiC1h", 12), ("vzOiC4h", 48), ("vzOiC24h", 288)):
            pv = mt[mt.g == g - k * 300_000].set_index("sym")
            s = now.index.intersection(pv.index)
            r[name] = np.log(now.loc[s, "oi_value"].sum() / pv.loc[s, "oi_value"].sum()) if len(s) else np.nan
        big = now[now.oi_value >= 1e6]
        for name, col in (("vzLsTop", "toptrader_ls_sum"), ("vzLsAcc", "ls_cnt")):
            v = big[col]
            v = v[np.isfinite(v) & (v > 0)]
            r[name] = float(np.log(np.median(v))) if len(v) else np.nan
    else:
        for c in VZB:
            r[c] = np.nan
    return r


def main():
    vz = pd.read_parquet(FEAT).set_index("timestamp")
    st = pd.read_csv(STORE, usecols=["timestamp", "momentum15M", "label_oldbasket"])
    st = st[st.timestamp < SEAL].set_index("timestamp")
    v = vz.reindex(st.index)
    res = {}
    t0a, t0b = pd.Timestamp("2021-01-02").value // 10**6, pd.Timestamp("2021-12-02").value // 10**6
    ia, ib = st.index >= t0a, st.index >= t0b
    res["D2"] = {c: float(v.loc[ia, c].notna().mean()) for c in VZA}
    res["D2"].update({c: float(v.loc[ib, c].notna().mean()) for c in VZB})
    res["D2_pass"] = all(res["D2"][c] >= 0.99 for c in VZA) and all(res["D2"][c] >= 0.95 for c in VZB)
    log.info("D2 %s pass=%s", {k: round(x, 4) for k, x in res["D2"].items()}, res["D2_pass"])
    rng = np.random.default_rng(20261017)
    cand = st.index[ia].to_numpy()
    picks = np.sort(rng.choice(cand, 30, replace=False))
    worst, rows = 0.0, []
    for T in picks:
        r = recompute(int(T))
        for c in VZA + VZB:
            a, b = float(v.loc[T, c]), float(r[c])
            if np.isnan(a) and np.isnan(b):
                e = 0.0
            elif np.isnan(a) or np.isnan(b):
                e = np.inf
            else:
                e = abs(a - b) / (0.01 + abs(b))   # addendum 2: |a-b| <= 1e-5*(0.01+|b|) (float32 khi gia tri gan 0)
            worst = max(worst, e)
            if e > 1e-5:
                rows.append((str(pd.Timestamp(int(T), unit="ms")), c, a, b, e))
    res["D3_worst_rel"] = worst
    res["D3_fail_cells"] = rows[:40]
    res["D3_pass"] = worst <= 1e-5
    log.info("D3 worst=%.3g pass=%s fails=%s", worst, res["D3_pass"], rows[:10])
    # D5
    j = v.join(st)
    rng5 = {c: [float(j[c].min()), float(j[c].max())] for c in VZA[:6]}
    res["D5_range_ok"] = all(0 < x[0] and x[1] < 1 for x in rng5.values())
    res["D5_range"] = rng5
    res["D5_corr_btc15_mom15"] = float(j["vzTkrBtc15"].corr(j["momentum15M"]))
    res["corr_label"] = {c: float(j[c].corr(j["label_oldbasket"], method="spearman")) for c in VZA + VZB}
    yr = pd.to_datetime(j.index, unit="ms").year
    res["corr_label_by_year"] = {c: {int(y): float(g[c].corr(g["label_oldbasket"], method="spearman"))
                                     for y, g in j.groupby(yr)} for c in VZA + VZB}
    log.info("D5 range_ok=%s corr(btc15,mom15)=%.3f corr_label=%s", res["D5_range_ok"], res["D5_corr_btc15_mom15"],
             {k: round(x, 4) for k, x in res["corr_label"].items()})
    # D4: vzTkr15 tre 0 (gom nen T) vs tre 1 tren 2022-06 (chi bao cao)
    k = pd.read_parquet(kp("2022-06"), columns=["ts", "quote_volume", "taker_buy_quote"])
    agg = k.groupby("ts")[["quote_volume", "taker_buy_quote"]].sum().sort_index()
    rq, rb = agg.quote_volume.rolling(15).sum(), agg.taker_buy_quote.rolling(15).sum()
    lag0 = rb / rq                                   # gom nen T
    lag1 = lag0.shift(1)                             # = dinh nghia pre-reg
    jj = st.join(pd.DataFrame({"lag0": lag0, "lag1": lag1, "ours": vz["vzTkr15"]}), how="inner").dropna()
    res["D4"] = dict(n=int(len(jj)), sp_lag0_label=float(jj.lag0.corr(jj.label_oldbasket, method="spearman")),
                     sp_lag1_label=float(jj.lag1.corr(jj.label_oldbasket, method="spearman")),
                     max_abs_ours_vs_lag1=float((jj.ours - jj.lag1).abs().max()),
                     max_abs_ours_vs_lag0=float((jj.ours - jj.lag0).abs().max()))
    log.info("D4 %s", res["D4"])
    json.dump(res, open(D + "/checks.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
