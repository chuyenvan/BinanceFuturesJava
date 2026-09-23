"""Doi chieu nguon: daily close tu ticker bins vs CLOSES_1H.bin tren 24 ngay mau 2021-2025."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/altregime")
import altdata  # noqa: E402

VAL = "/home/ubuntu/altregime/daily_val"
dev = altdata.dev_daily()
rows = []
for fn in sorted(os.listdir(VAL)):
    day = pd.Timestamp(fn[:-4])
    d = pd.read_csv(os.path.join(VAL, fn), header=None, names=["sym", "close"])
    d = d.drop_duplicates("sym").set_index("sym")["close"]
    if day not in dev.index:
        continue
    ref = dev.loc[day].dropna()
    com = ref.index.intersection(d.index)
    rd = (d[com] / ref[com] - 1.0).abs()
    rows.append({"day": str(day.date()), "n_common": len(com), "n_ref": len(ref),
                 "median_abs_rel": float(rd.median()), "p90": float(rd.quantile(0.9)),
                 "pct_gt_1pct": float((rd > 0.01).mean()),
                 "btc_ext": float(d.get("BTC", np.nan)), "btc_ref": float(ref.get("BTC", np.nan))})
df = pd.DataFrame(rows)
print(df.to_string(index=False))
print("\nTONG: n_ngay=%d  median_abs_rel max=%.5f  pct_gt_1pct mean=%.4f  "
      "btc rel diff max=%.5f" % (
          len(df), df.median_abs_rel.max(), df.pct_gt_1pct.mean(),
          ((df.btc_ext / df.btc_ref - 1).abs()).max()))
df.to_csv("/home/ubuntu/altregime/align_check.csv", index=False)
