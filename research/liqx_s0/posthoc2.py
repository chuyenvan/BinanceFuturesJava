"""LIQX_S0 POST-HOC 2 (no verdict change): (a) pin create_time switch date by implied price oi_value/oi vs kline close at T or T+5m
(independent of Tardis & liquidations), Feb-Apr 2024 every day + day-01 2022..2025; (b) on FIXED buckets: lags on all buckets, per-year M1, V1 detail."""
import pandas as pd, numpy as np, pyarrow.parquet as pq, os, json, sys
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import proxies
WK = os.path.expanduser("~/claude_master/liqx_wk"); OUT = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/liqx_s0")
res = {"implied_price_switch": {}, "fixed": {}}
def ip_check(y, m, days, sym="BTCUSDT"):
    met = pq.read_table(f"/home/ubuntu/vz/out/metrics5m/{y}/{y}-{m:02d}.parquet", columns=["ts", "sym", "oi", "oi_value"], filters=[("sym", "=", sym)]).to_pandas()
    kl = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{y}-{m:02d}.parquet", columns=["ts", "sym", "close"], filters=[("sym", "=", sym)]).to_pandas()
    c = dict(zip(kl.ts.values, kl.close.values))
    met["px"] = met.oi_value / met.oi; met["d"] = pd.to_datetime(met.ts, unit="ms").dt.day
    out = {}
    for d in days:
        t = met[met.d == d]
        cT = np.array([c.get(x - 60000, np.nan) for x in t.ts]); c5 = np.array([c.get(x + 240000, np.nan) for x in t.ts])
        e0 = np.nanmedian(np.abs(t.px - cT) / cT); e5 = np.nanmedian(np.abs(t.px - c5) / c5)
        out[f"{y}-{m:02d}-{d:02d}"] = {"err_T": float(e0), "err_T5": float(e5), "sem": "T+5m" if e5 < 0.5 * e0 else ("T" if e0 < 0.5 * e5 else "UNCLEAR")}
    return out
for (y, m) in [(2024, 2), (2024, 3), (2024, 4)]:
    res["implied_price_switch"].update(ip_check(y, m, range(1, 32)))
for y in (2022, 2023, 2024, 2025):
    for m in range(1, 13):
        res["implied_price_switch"].update(ip_check(y, m, [1]))
sw = res["implied_price_switch"]
print({k: v["sem"] for k, v in sorted(sw.items())})
G = proxies(pd.read_parquet(WK + "/buckets_AB_fix.parquet")); G["year"] = pd.to_datetime(G.day, unit="ms").dt.year
v = G[G.valid]; py = {}
for yr, t in v.groupby("year"):
    s1 = t[t.r5 < -0.01]
    py[int(yr)] = {p: float(spearmanr(s1[p], s1.liq_long).correlation) for p in ("P1", "P2", "P3")}; py[int(yr)]["n"] = int(len(s1))
res["fixed"]["M1_by_year"] = py; print(py)
gb = G.groupby(["sym", "day"]); lag = {}
for smp in ("A", "B"):
    lag[smp] = {}
    for k in range(-3, 4):
        lk = gb.liq_long.shift(-k); vk = gb.valid.shift(-k, fill_value=False).astype(bool); r5k = gb.r5.shift(-k)
        mk = G.valid & vk & (G["sample"] == smp)
        doi = (G.oiv1 - G.oiv0) / G.oiv0
        ok = mk & np.isfinite(doi) & np.isfinite(r5k)
        lag[smp][k * 5] = {"sp_P2_liq_all": float(spearmanr(G.P2[mk], lk[mk]).correlation),
                           "sp_P1_liq_all": float(spearmanr(G.P1[mk], lk[mk]).correlation),
                           "sp_dOIval_r5_all": float(spearmanr(doi[ok], r5k[ok]).correlation), "n_nonfinite": int((mk & ~ok).sum())}
    print(smp, lag[smp], flush=True)
res["fixed"]["lags_all_buckets"] = lag
v1 = G.groupby(["sym", "day"]).valid.sum(); bad = v1[v1 < 288].reset_index()
bad["day"] = pd.to_datetime(bad.day, unit="ms").dt.date.astype(str)
res["fixed"]["V1_lt288_by_day"] = bad.groupby("day").agg(n=("sym", "size"), valid_sum=("valid", "sum")).reset_index().values.tolist()
res["fixed"]["P2_quantiles_M1_vs_liq"] = None
json.dump(res, open(OUT + "/posthoc2.json", "w"), indent=1, default=str)
print(res["fixed"]["V1_lt288_by_day"])
