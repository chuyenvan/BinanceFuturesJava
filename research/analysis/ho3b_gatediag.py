import sys, glob
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_ablation_driver as GA
TZ = "Asia/Ho_Chi_Minh"
A0 = pd.Timestamp("2026-03-01", tz=TZ).value // 10**6
A1 = pd.Timestamp("2026-03-08", tz=TZ).value // 10**6
use = ["timestamp"] + GA.V3FULL
ref = pd.read_csv(GA.STORE, usecols=use)
ref = ref[(ref.timestamp >= A0) & (ref.timestamp < A1)]
new = pd.read_csv(glob.glob("/home/ubuntu/claude_master/1003/ho3b/kaggle/out/ho3b-x-h1slice/out/gate/*.csv*")[0], usecols=use)
M = ref.merge(new, on="timestamp", suffixes=("_r", "_n"))
M["day"] = pd.to_datetime(M.timestamp, unit="ms", utc=True).dt.tz_convert(TZ).dt.strftime("%m-%d %H")
bad = np.zeros(len(M), bool)
for c in ["advanceDeclineRatio", "basketRsi14", "fundingRateRaw", "btcDominance"]:
    a, b = M[c + "_n"].to_numpy(float), M[c + "_r"].to_numpy(float)
    bb = ~((np.abs(a - b) <= 1e-6 * np.maximum(1, np.abs(b))) | (np.isnan(a) & np.isnan(b)))
    print(c, "bad frac", round(bb.mean(), 4))
    bad |= bb
M["bad"] = bad
g = M.groupby(M.day.str[:5]).bad.mean().round(3).to_dict()
print("bad by day", g)
h = M.groupby(M.day.str[6:8]).bad.mean().round(3).to_dict()
print("bad by hour", h)
