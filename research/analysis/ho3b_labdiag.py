import sys, glob
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label
TZ = "Asia/Ho_Chi_Minh"
T0 = pd.Timestamp("2026-03-01 07:00", tz=TZ).value // 10**6
T1 = pd.Timestamp("2026-03-08 07:00", tz=TZ).value // 10**6
cols = ["tEpochMs", "symbol", "nBars_72h"]
ref = read_label("/home/ubuntu/ds_label15m/funding_label_20260101_to_20260401.pb", usecols=cols)
ref = ref[(ref.tEpochMs >= T0) & (ref.tEpochMs < T1)]
new = read_label(glob.glob("/home/ubuntu/claude_master/1003/ho3b/kaggle/out/ho3b-x-h1slice/out/lab/*.pb")[0], usecols=cols)
new = new[(new.tEpochMs >= T0) & (new.tEpochMs < T1)]
M = ref.merge(new, on=["tEpochMs", "symbol"], suffixes=("_r", "_n"))
d = M.nBars_72h_n.astype(int) - M.nBars_72h_r.astype(int)
print("n", len(M), "eq", float((d == 0).mean()))
print("diff quantiles", d.quantile([0, .01, .1, .5, .9, .99, 1]).to_dict())
M["day"] = pd.to_datetime(M.tEpochMs, unit="ms", utc=True).dt.tz_convert(TZ).dt.strftime("%m-%d")
print("eq by day", M.assign(e=(d == 0)).groupby("day").e.mean().round(4).to_dict())
print("ref ge288", float((M.nBars_72h_r >= 288).mean()), "new ge288", float((M.nBars_72h_n >= 288).mean()),
      "pool agree", float(((M.nBars_72h_r >= 288) == (M.nBars_72h_n >= 288)).mean()))
print("ref nBars max", int(M.nBars_72h_r.max()), "new max", int(M.nBars_72h_n.max()))
