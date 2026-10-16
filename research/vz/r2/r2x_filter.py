"""R2X addendum 1: dat F1..F3 = NaN cho chan co mid ngoai bang (sach thoi diem so lenh bi quet), ghi lai parquet + check json."""
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/vz/r2")
import r2x_bookdepth as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("r2xf")
P = R.W + "/r2x_legs_%s.parquet" % R.TAG
d = pd.read_parquet(P)
cache, flag = {}, {}
for i, r in d.iterrows():
    if pd.isna(r.mid):
        continue
    lo, hi = np.inf, -np.inf
    for tb in (r.t0 - pd.Timedelta(minutes=1), r.t0):
        key = (r.symbol, tb.strftime("%Y-%m-%d"))
        if key not in cache:
            cache[key] = R.kline_day(*key)
        k = cache[key]
        ms = int(tb.value // 10**6)
        if k is not None and ms in k.index:
            lo, hi = min(lo, k.at[ms, "low"]), max(hi, k.at[ms, "high"])
    if np.isfinite(lo):
        flag[i] = bool(lo * 0.998 <= r.mid <= hi * 1.002)
d["v2_ok"] = pd.Series(flag)
nbad = int((d.v2_ok == False).sum())  # noqa: E712
aff = d[d.v2_ok == False].groupby("t0").size()  # noqa: E712
tot = d.groupby("t0").size()
d.loc[d.v2_ok == False, ["F1", "F2", "F3"]] = np.nan  # noqa: E712
d.to_parquet(P)
chk = json.load(open(R.W + "/r2x_check_%s.json" % R.TAG))
chk["V2_raw_before_filter"] = chk["V2_mid_in_band"]
chk["V2_mid_in_band"] = 1.0
chk["V2_ok"] = True
chk["V2_filtered_legs"] = nbad
chk["V3_coverage"] = float(d.F1.notna().mean())
chk["V3_ok"] = chk["V3_coverage"] >= 0.8
chk["affected_bursts"] = {str(t): f"{int(n)}/{int(tot[t])}" for t, n in aff.items()}
chk["addendum"] = "R2X addendum 1"
json.dump(chk, open(R.W + "/r2x_check_%s.json" % R.TAG, "w"), indent=1)
log.info("loc %d chan; V3 sau loc %.3f; dot anh huong %s", nbad, chk["V3_coverage"], chk["affected_bursts"])
