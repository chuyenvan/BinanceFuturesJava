"""LIQX_S0 V5 (prereg) + POST-HOC diagnostics (no verdict change): create_time semantics on more days; per-year M1;
lag structure on ALL valid buckets (no union subset); OI-vs-price alignment (no liquidation)."""
import pandas as pd, numpy as np, pyarrow.parquet as pq, os, json, sys
from scipy.stats import spearmanr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score import proxies
WK = os.path.expanduser("~/claude_master/liqx_wk"); OUT = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/liqx_s0")
res = {"V5": {}, "posthoc": {}}
# V5
for day in ["2022-07-01", "2023-07-01", "2024-07-01", "2025-08-01", "2025-12-01"]:
    for sym in ["BTCUSDT", "ETHUSDT"]:
        f = f"{WK}/probe/dt_{sym}_{day}.csv.gz"
        if not os.path.exists(f):
            os.system(f"curl -s -o {f} https://datasets.tardis.dev/v1/binance-futures/derivative_ticker/{day.replace('-', '/')}/{sym}.csv.gz")
        t = pd.read_csv(f, usecols=["timestamp", "open_interest"]).dropna()
        if len(t) == 0:
            res["V5"][f"{sym}_{day}"] = "no OI"; continue
        t["ms"] = (t.timestamp // 1000).astype("int64"); t = t.sort_values("ms")
        y, m = int(day[:4]), int(day[5:7]); t0 = int(pd.Timestamp(day, tz="UTC").value // 10**6)
        v = pq.read_table(f"/home/ubuntu/vz/out/metrics5m/{y}/{y}-{m:02d}.parquet", columns=["ts", "sym", "oi"],
                          filters=[("ts", ">=", t0 + 3600_000), ("ts", "<", t0 + 82800_000)]).to_pandas()
        v = v[v.sym.astype(str) == sym]
        sc = {}
        for L in range(-600_000, 600_001, 30_000):
            idx = np.searchsorted(t.ms.values, v.ts.values + L, side="right") - 1
            sc[L // 1000] = float(np.median(np.abs(v.oi.values - t.open_interest.values[idx]) / v.oi.values))
        best = min(sc, key=sc.get)
        res["V5"][f"{sym}_{day}"] = {"best_L_s": best, "err_best": sc[best], "err_0": sc[0], "err_m300": sc[-300], "err_p300": sc[300],
                                     "tardis_oi_update_med_s": float(np.median(np.diff(t.ms[t.open_interest.diff() != 0].values)) / 1000)}
        print(sym, day, res["V5"][f"{sym}_{day}"], flush=True)
# post-hoc on buckets
G = proxies(pd.read_parquet(WK + "/buckets_AB.parquet"))
G["year"] = pd.to_datetime(G.day, unit="ms").dt.year
v = G[G.valid]
py = {}
for yr, t in v.groupby("year"):
    s1 = t[t.r5 < -0.01]
    py[int(yr)] = {p: float(spearmanr(s1[p], s1.liq_long).correlation) for p in ("P1", "P2", "P3")}
    py[int(yr)]["n"] = int(len(s1))
    py[int(yr)]["frac_oidrop_pos_M1"] = float((s1.oidrop > 0).mean())
res["posthoc"]["M1_by_year"] = py; print(py)
lag = {}
gb = G.groupby(["sym", "day"])
for smp in ("A", "B"):
    lag[smp] = {}
    for k in range(-3, 4):
        lk = gb.liq_long.shift(-k); vk = gb.valid.shift(-k, fill_value=False).astype(bool)
        r5k = gb.r5.shift(-k)
        mk = G.valid & vk & (G["sample"] == smp)
        doi = (G.oiv1 - G.oiv0) / G.oiv0
        lag[smp][k * 5] = {"sp_P1_liq_all": float(spearmanr(G.P1[mk], lk[mk]).correlation),
                           "sp_dOI_r5_all": float(spearmanr(doi[mk], r5k[mk]).correlation),
                           "sp_negr5_liq_all": float(spearmanr(-G.r5[mk], lk[mk]).correlation)}
    print(smp, lag[smp], flush=True)
res["posthoc"]["lags_all_buckets"] = lag
json.dump(res, open(OUT + "/v5_posthoc.json", "w"), indent=1)
