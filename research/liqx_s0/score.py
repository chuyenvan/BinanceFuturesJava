"""LIQX_S0 step 3: score proxies P1/P2/P3 (+V4 P1c contracts) vs real liquidations. Prereg docs/prereg/PREREG_LIQX_S0.md §6-7."""
import pandas as pd, numpy as np, json, os, sys
from scipy.stats import spearmanr, rankdata
WK = os.path.expanduser("~/claude_master/liqx_wk")
OUT = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/liqx_s0")
os.makedirs(OUT, exist_ok=True)
B5 = 300_000


def proxies(g):
    g = g.sort_values(["sym", "day", "T"]).reset_index(drop=True)
    g["r5"] = np.log(g.c1 / g.c0)
    drop = (g.oiv0 - g.oiv1).clip(lower=0)
    neg = (g.r5 < 0).astype(float)
    g["oidrop"] = drop
    g["tsx"] = (g.qv - 2.0 * g.tbq).clip(lower=0)
    g["P1"] = drop * neg
    g["P2"] = np.minimum(drop, g.tsx)
    g["P3"] = np.where(g.qv > 0, drop * g.tsx / g.qv.where(g.qv > 0, 1.0), 0.0) * neg
    g["P1c"] = (g.oi0 - g.oi1).clip(lower=0) * neg  # V4: contracts
    return g


def sp(x, y):
    if len(x) < 3:
        return float("nan")
    return float(spearmanr(x, y).correlation)


def auc(score, lab):
    lab = np.asarray(lab, bool); n1 = lab.sum(); n0 = (~lab).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = rankdata(score)
    return float((r[lab].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def labels(v):
    lab = np.zeros(len(v), bool); rule = {}
    for s, idx in v.groupby("sym").indices.items():
        x = v.liq_long.values[idx]
        q = np.percentile(x, 99)
        if q > 0:
            lab[idx] = x >= q; rule[s] = "p99"
        else:
            lab[idx] = x >= 1e6; rule[s] = "1M"
    return lab, rule


def m3(v, p, lab):
    num = den = 0.0
    for s, idx in v.groupby("sym").indices.items():
        a = auc(v[p].values[idx], lab[idx]); npos = lab[idx].sum()
        if np.isfinite(a):
            num += a * npos; den += npos
    return num / den if den else float("nan"), auc(v[p].values, lab)


def score_sample(g, name, plist):
    v = g[g.valid].copy()
    lab, rule = labels(v)
    res = {"n_valid": int(len(v)), "n_symday": int(v.groupby(["sym", "day"]).ngroups),
           "n_pos_M3": int(lab.sum()), "rule_counts": pd.Series(rule).value_counts().to_dict(),
           "n_M1": int((v.r5 < -0.01).sum()), "sum_liq_long": float(v.liq_long.sum()), "sum_liq_short": float(v.liq_short.sum())}
    s1 = v[v.r5 < -0.01]
    res["diag_size_M1"] = sp(s1.oiv0, s1.liq_long)
    res["diag_r5_M1"] = sp(-s1.r5, s1.liq_long)
    for p in plist:
        r = {}
        r["M1"] = sp(s1[p], s1.liq_long)
        sub = v[(v[p] > 0) | (v.liq_long > 0)]
        r["M2"] = sp(sub[p], sub.liq_long); r["n_M2"] = int(len(sub))
        r["M3"], r["M3_pooled"] = m3(v, p, lab)
        # M4 lags on full grid (shift inside sym-day)
        xc = {}
        for k in range(-3, 4):
            lk = g.groupby(["sym", "day"]).liq_long.shift(-k)
            vk = g.groupby(["sym", "day"]).valid.shift(-k, fill_value=False).astype(bool)
            mk = g.valid & vk & lk.notna()
            pp, ll = g.loc[mk, p], lk[mk]
            sel = (pp > 0) | (ll > 0)
            xc[k * 5] = sp(pp[sel], ll[sel])
        r["M4"] = xc; r["M4_peak_lag_min"] = int(max(xc, key=lambda z: xc[z]))
        # M5 per tier
        m5 = {}
        for tn, lo, hi in (("t1_10", 1, 10), ("t11_30", 11, 30), ("t31_100", 31, 100)):
            t = sub[(sub["rank"] >= lo) & (sub["rank"] <= hi)]
            if len(t) < 10:
                m5[tn] = None; continue
            X = np.column_stack([np.ones(len(t)), np.log1p(t[p].values)]); Y = np.log1p(t.liq_long.values)
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
            r2 = 1 - ((Y - X @ beta) ** 2).sum() / ((Y - Y.mean()) ** 2).sum()
            m5[tn] = {"a": float(beta[0]), "b": float(beta[1]), "R2": float(r2), "n": int(len(t))}
        r["M5"] = m5
        sub6 = v[(v[p] > 0) | (v.liq_short > 0)]
        r["M6"] = sp(sub6[p], sub6.liq_short)
        r["M6_onM1"] = sp(s1[p], s1.liq_short)
        r["sum_ratio"] = float(v[p].sum() / v.liq_long.sum()) if p != "P1c" else None
        # within-symbol M1 diag
        ws = []
        for s, t in s1.groupby("sym"):
            if len(t) >= 20 and t[p].nunique() > 1 and t.liq_long.nunique() > 1:
                ws.append((sp(t[p], t.liq_long), len(t)))
        r["diag_M1_within_sym"] = float(np.average([a for a, _ in ws], weights=[n for _, n in ws])) if ws else None
        r["diag_n_sym_within"] = len(ws)
        r["frac_pos"] = float((v[p] > 0).mean())
        res[p] = r
    return res


def crash_table(g):
    v = g[g.valid]
    rows = []
    for d, t in v.groupby("day"):
        b = t[t.sym == "BTCUSDT"].sort_values("T")
        btc_day = float(np.log(b.c1.iloc[-1] / b.c0.iloc[0])) if len(b) else float("nan")
        btc_min5 = float(b.r5.min()) if len(b) else float("nan")
        top = t.loc[t.liq_long.idxmax()]
        rows.append(dict(day=pd.Timestamp(d, unit="ms").date().isoformat(), btc_ret_day=btc_day, btc_min_r5=btc_min5,
                         n_r5_lt_1pct=int((t.r5 < -0.01).sum()), n_r5_lt_3pct=int((t.r5 < -0.03).sum()),
                         liq_long_usd=float(t.liq_long.sum()), liq_short_usd=float(t.liq_short.sum()),
                         max_bucket_liq=float(top.liq_long), max_bucket=f"{top.sym}@{pd.Timestamp(int(top['T']), unit='ms'):%H:%M}"))
    return pd.DataFrame(rows)


def verdict(res):
    out = {}
    for p in ("P1", "P2", "P3"):
        A, B = res["A"][p], res["B"][p]
        c = dict(M1=A["M1"] >= 0.40 and B["M1"] >= 0.40, M3=A["M3"] >= 0.80 and B["M3"] >= 0.80,
                 M4=A["M4_peak_lag_min"] == 0 and B["M4_peak_lag_min"] == 0,
                 M6=A["M6"] < 0.5 * A["M1"] and B["M6"] < 0.5 * B["M1"])
        c = {kk: bool(vv) for kk, vv in c.items()}; c["PASS"] = all(c.values()); out[p] = c
    out["ANY_PASS"] = bool(any(out[p]["PASS"] for p in ("P1", "P2", "P3")))
    return out


def main():
    G = proxies(pd.read_parquet(WK + "/buckets_AB.parquet"))
    for c in ("T", "day"):
        assert G[c].dtype == np.int64
    plist = ["P1", "P2", "P3", "P1c"]
    res = {s: score_sample(G[G["sample"] == s], s, plist) for s in ("A", "B")}
    if os.path.exists(WK + "/buckets_F.parquet"):
        F = proxies(pd.read_parquet(WK + "/buckets_F.parquet"))
        res["F"] = score_sample(F, "F", plist)
        crash_table(F).to_csv(OUT + "/crash_days_F.csv", index=False)
    res["verdict"] = verdict(res)
    json.dump(res, open(OUT + "/scores.json", "w"), indent=1, default=float)
    ct = crash_table(G); ct.to_csv(OUT + "/crash_days_AB.csv", index=False)
    # V1
    v1 = G.groupby(["sym", "day"]).valid.sum()
    v1d = {"symday": int(len(v1)), "symday_288": int((v1 == 288).sum()), "symday_lt288": v1[v1 < 288].reset_index().assign(
        day=lambda d: pd.to_datetime(d.day, unit="ms").dt.date.astype(str)).values.tolist()}
    json.dump(v1d, open(OUT + "/v1.json", "w"), indent=1, default=str)
    print(json.dumps(res["verdict"], indent=1))
    for s in res:
        if s == "verdict":
            continue
        print(s, {k: res[s][k] for k in ("n_valid", "n_symday", "n_pos_M3", "n_M1", "rule_counts", "diag_size_M1", "diag_r5_M1")})
        for p in plist:
            r = res[s][p]
            print(f" {s} {p}: M1={r['M1']:.4f} M2={r['M2']:.4f} M3={r['M3']:.4f} (pooled {r['M3_pooled']:.4f}) peak={r['M4_peak_lag_min']} "
                  f"M6={r['M6']:.4f} M6onM1={r['M6_onM1']:.4f} ratio={r['sum_ratio']} wsym={r['diag_M1_within_sym']} fpos={r['frac_pos']:.4f}")
            print("    M4", {k: round(x, 4) for k, x in r["M4"].items()}, "M5", r["M5"])
    print("V1", {k: v1d[k] for k in ("symday", "symday_288")}, "n lt288", len(v1d["symday_lt288"]))
    print(ct.to_string())


if __name__ == "__main__":
    main()
