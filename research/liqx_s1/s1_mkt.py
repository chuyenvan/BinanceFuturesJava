"""LIQX_S1 step 2: MKT buckets (prereg §5), thresholds theta (§6, from A only), convention census by month (§2),
I distribution (descriptive). Out: S1/mkt.parquet, S1/thresholds.json, S1/conv_month.csv, S1/idist.json."""
import json
import numpy as np
import pandas as pd
from common import S1, B5, DAY, T_A0, T_B0, T_END, months, maxrss_mb, ms, nxt

PCTS = (98.0, 99.0, 99.5)


def main():
    mk, acc, cm = [], {}, []
    for y, m in months():
        tag = "%04d-%02d" % (y, m)
        g = pd.read_parquet(S1 + "/coin/%s.parquet" % tag,
                            columns=["sym", "T", "day", "valid", "P2", "oiv0", "oidrop", "tsx", "r5", "cum60", "I", "alt"])
        g["sym"] = g.sym.astype(str)
        v = g[g.valid]
        va = v[v.alt]
        a = v.groupby("T").agg(sP2=("P2", "sum"), sOIV0=("oiv0", "sum"), sOIdrop=("oidrop", "sum"),
                               sTSX=("tsx", "sum"), n_valid=("P2", "size"))
        b = va.groupby("T").agg(r_mkt=("r5", "mean"), cum60_mkt=("cum60", "mean"), n_alt=("r5", "size"))
        bt = v[v.sym == "BTCUSDT"].set_index("T")[["r5", "cum60"]].rename(columns={"r5": "r5_btc", "cum60": "cum60_btc"})
        grid = pd.Index(np.sort(g["T"].unique()), name="T")
        x = pd.concat([a, b, bt], axis=1).reindex(grid)
        x["n_valid"] = x.n_valid.fillna(0).astype("int64")
        mk.append(x.reset_index())
        if (y, m) < (2024, 1):
            for s, arr in v.groupby("sym").I:
                acc.setdefault(s, []).append(arr.values)
            dd = v.groupby("sym").day.nunique()
            for s, n in dd.items():
                acc.setdefault("__days__" + s, []).append(n)
        c = pd.read_parquet(S1 + "/conv/%s.parquet" % tag)
        M, Mn = ms(y, m), ms(*nxt(y, m))
        c = c[(c.day >= M) & (c.day < Mn)]
        cm.append(dict(month=tag, NEW=int((c.conv == "NEW").sum()), OLD=int((c.conv == "OLD").sum()),
                       AMBIG=int((c.conv == "AMBIG").sum()), via_price=int((c.via == "price").sum()),
                       old_syms=";".join(sorted(c[c.conv == "OLD"].sym.unique())[:12]) if (y, m) >= (2024, 3) else "",
                       new_before_switch=int(((c.conv == "NEW") & (c.day < ms(2024, 3, 4))).sum())))
        print(tag, len(x), round(maxrss_mb()), flush=True)
    K = pd.concat(mk, ignore_index=True).sort_values("T").reset_index(drop=True)
    exp = np.arange(T_A0 + B5, T_END + 1, B5, dtype=np.int64)
    assert K["T"].dtype == np.int64 and len(K) == len(exp) and (K["T"].values == exp).all()
    med = K.n_valid.rolling(2016, min_periods=1).median()
    K["mkt_valid"] = (K.n_valid >= 0.85 * med) & (K.n_valid > 0)
    K["I_mkt"] = np.where(K.mkt_valid, K.sP2 / K.sOIV0, np.nan)
    for col in ("r_mkt", "cum60_mkt"):
        K.loc[~K.mkt_valid, col] = np.nan
    K["period"] = np.where(K["T"] <= T_B0, "A", "B")
    K.to_parquet(S1 + "/mkt.parquet", index=False)
    A = K[(K.period == "A") & K.mkt_valid].I_mkt.values
    th = {"mkt": {str(p): float(np.percentile(A, p)) for p in PCTS}, "coin": {}, "coin_days": {}}
    for s in sorted(k for k in acc if not k.startswith("__days__")):
        arr = np.concatenate(acc[s])
        nd = int(sum(acc["__days__" + s]))
        th["coin_days"][s] = nd
        if nd >= 90:
            q = {str(p): float(np.percentile(arr, p)) for p in PCTS}
            if q["99.0"] > 0:
                th["coin"][s] = q
    json.dump(th, open(S1 + "/thresholds.json", "w"), indent=1)
    pd.DataFrame(cm).to_csv(S1 + "/conv_month.csv", index=False)
    inv = K[~K.mkt_valid]
    idist = {}
    for per in ("A", "B"):
        z = K[(K.period == per) & K.mkt_valid]
        idist[per] = dict(n=int(len(z)), frac_pos=float((z.I_mkt > 0).mean()),
                          q={str(q): float(np.quantile(z.I_mkt, q)) for q in (0.5, 0.9, 0.95, 0.98, 0.99, 0.995, 0.999, 1.0)},
                          frac_ge_th99=float((z.I_mkt >= th["mkt"]["99.0"]).mean()),
                          frac_ge_th99_and_dd=float(((z.I_mkt >= th["mkt"]["99.0"]) & (z.cum60_mkt <= np.log(0.97))).mean()))
    idist["invalid_mkt_buckets"] = int(len(inv))
    idist["invalid_days"] = {str(pd.Timestamp(d, unit="ms").date()): int(n) for d, n in
                             ((inv["T"] - 1) // DAY * DAY).value_counts().sort_index().items()}
    idist["n_coin_theta"] = len(th["coin"])
    idist["n_coin_lt90d"] = int(sum(1 for s, n in th["coin_days"].items() if n < 90))
    idist["maxrss_mb"] = round(maxrss_mb(), 1)
    json.dump(idist, open(S1 + "/idist.json", "w"), indent=1)
    print(json.dumps(th["mkt"]), json.dumps(idist)[:2000])


if __name__ == "__main__":
    main()
