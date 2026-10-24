"""SHORTVOL_T0 V2v: independent re-implementation (does NOT import sv_*; reads raw kline parquet + raw Deribit JSON pages).
(a) mean VRP30 over t in 2023 (BTC), (b) straddle proxy PnL for 10 Mondays 2023-01-02..2023-03-06. Compare vs pipeline outputs WK/run/*.csv."""
import glob, json, os, math
import numpy as np, pandas as pd, pyarrow.parquet as pq
WK = os.path.expanduser("~/claude_master/shortvol_t0_wk")
# DVOL from raw JSON pages
dv = {}
for f in sorted(glob.glob(os.path.join(WK, "dvol", "raw", "BTC_1D_p*.json"))):
    for row in json.load(open(f))["result"]["data"]:
        dv[int(row[0])] = float(row[4])
def dvol_at(day):  # value at 00:00 UTC of `day` = close of candle opened the day before
    return dv[int((day - pd.Timedelta(days=1)).value // 10**6)]
# raw 1m BTCUSDT 2022-12 .. 2024-01
fr = []
for ym in ["2022-12"] + ["2023-%02d" % m for m in range(1, 13)] + ["2024-01"]:
    t = pq.read_table("/home/ubuntu/vz_e1/raw/kline1m-%s.parquet" % ym, columns=["ts", "sym", "close"]).to_pandas()
    t = t[t.sym.astype(str) == "BTCUSDT"][["ts", "close"]]
    fr.append(t)
k = pd.concat(fr).drop_duplicates("ts").set_index("ts").sort_index()
assert k.index.dtype == np.int64
k.index = pd.to_datetime(k.index, unit="ms")
full = pd.date_range(k.index[0], k.index[-1], freq="1min")
assert len(full) == len(k), "gap in 1m"
# price at instant T = close of candle opened at T-1min; 5-minute marks
inst = pd.Series(k.close.values, index=k.index + pd.Timedelta(minutes=1))
p5 = inst[inst.index.minute % 5 == 0]
r2 = (np.log(p5).diff() ** 2).dropna()          # indexed by mark (end of 5m interval)
res = []
for d in pd.date_range("2023-01-01", "2023-12-31", freq="D"):
    w = r2[(r2.index > d) & (r2.index <= d + pd.Timedelta(days=30))]
    assert len(w) == 8640
    rv = 100 * math.sqrt(365 / 30 * w.sum())
    res.append(dvol_at(d) - rv)
vrp23 = float(np.mean(res))
dl = pd.read_csv(os.path.join(WK, "run", "daily_BTC.csv"))
dl["d"] = pd.to_datetime(dl.day_ms, unit="ms")
pipe23 = float(dl[dl.d.dt.year == 2023].vrp30.mean())
print("VRP30 2023 BTC indep %.12f pipeline %.12f delta %.3e" % (vrp23, pipe23, abs(vrp23 - pipe23)))
assert abs(vrp23 - pipe23) < 1e-9
# weekly
wk = pd.read_csv(os.path.join(WK, "run", "weekly_BTC.csv"))
wk["mon"] = pd.to_datetime(wk.mon_ms, unit="ms")
mx = 0.0
for m in pd.date_range("2023-01-02", "2023-03-06", freq="7D"):
    s0 = float(k.close.loc[m + pd.Timedelta(hours=8)]); sT = float(k.close.loc[m + pd.Timedelta(days=7, hours=8)])
    sg = dvol_at(m) / 100
    prem = 0.8 * sg * math.sqrt(7 / 365) * s0
    fee = 2 * min(0.00024 * s0, 0.1 * prem / 2)
    p = (prem - fee - 0.05 * prem - abs(sT - s0)) / s0
    q = float(wk.loc[wk.mon == m, "pnl"].iloc[0])
    mx = max(mx, abs(p - q))
    print(m.date(), "S0 %.2f ST %.2f dvol %.2f pnl_indep %.10f pipe %.10f" % (s0, sT, sg * 100, p, q))
print("max |delta| weekly %.3e" % mx)
assert mx < 1e-9
print("V2v PASS")
