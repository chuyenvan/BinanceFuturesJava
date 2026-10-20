#!/usr/bin/env python3
import json, numpy as np, pandas as pd, datetime as dt
W = "/home/ubuntu/claude_master/parity_1020"
A = json.load(open(W + "/par_a.json"))
X = pd.read_csv(W + "/out_minute_collector.csv.gz")
rs = []
for s in A["restarts"]:
    t = dt.datetime.strptime("2026-" + s + " +0700", "%Y-%m-%d %H:%M %z")
    rs.append(int(t.timestamp() * 1000))
rs = np.array(sorted(rs))
i = np.searchsorted(rs, X["min"].values, "right") - 1
X["h_since"] = np.where(i >= 0, (X["min"].values - rs[np.clip(i, 0, None)]) / 3600000, np.nan)
X["hb"] = pd.cut(X.h_since, [0, 1, 3, 6, 9, 12.5])
f = lambda x: (x <= 1e-3).mean()
print("restarts", A["restarts"])
print(X.groupby("hb").p15_rel.agg(["median", f, "size"]))
X["d15"] = (X.rateDown15MAvg - X.o_rateDown15MAvg).abs() <= 1e-6 * (1 + X.o_rateDown15MAvg.abs())
X["d1"] = (X.rateDownAvg - X.o_rateDownAvg).abs() <= 1e-6 * (1 + X.o_rateDownAvg.abs())
print("rate match by partial", X.groupby("partial")[["d1", "d15"]].mean())
print("rate15 match by h_since", X.groupby("hb").d15.mean())
out = dict(by_hsince=X.groupby("hb").p15_rel.agg(["median", f, "size"]).reset_index().astype(str).to_dict("records"),
           by_partial=X.groupby("partial").p15_rel.agg(["median", f, "size"]).reset_index().astype(str).to_dict("records"),
           rate_by_partial=X.groupby("partial")[["d1", "d15"]].mean().reset_index().astype(str).to_dict("records"),
           partial_share_by_day=X.assign(day=pd.to_datetime(X["min"] + 7 * 3600000, unit="ms").dt.strftime("%m-%d")).groupby("day").partial.mean().round(3).to_dict())
json.dump(out, open(W + "/diag4.json", "w"), indent=1)
