"""FEE0: X14 daily return (MTM b+unP at 00:00 UTC) per seed, doc nhu research/trend_t1/t1_x14.py; median seed = rank 4/8 theo
Sharpe MTM full 2022-05-01..2025-12-31 (tang dan) - y nguyen quy uoc t1_x14."""
import os, re
import numpy as np, pandas as pd
OUT = "/home/ubuntu/kaggle_sim/out"
WK = os.path.expanduser("~/claude_master/fee0_wk")
TAGS = ["a1", "s123", "s13", "s2024", "s21", "s7", "s777", "s99"]
RX = re.compile(r"BudgetManagerSimple: Update (\d{8}) 07:00 => b:\s*(-?\d+)\s+pD:.*?unP:\s*(-?\d+)\s")
rows = []
for tg in TAGS:
    for line in open(os.path.join(OUT, "tsx-x14-" + tg, "logs", "sim.out"), errors="replace"):
        m = RX.search(line)
        if m:
            rows.append((tg, m.group(1), int(m.group(2)), int(m.group(3))))
d = pd.DataFrame(rows, columns=["seed", "date", "b", "unP"])
d["day"] = pd.to_datetime(d["date"], format="%Y%m%d")
assert not d.duplicated(["seed", "day"]).any()
d["E"] = d.b + d.unP
d = d.sort_values(["seed", "day"])
d["ret"] = d.groupby("seed").E.shift(-1) / d.E - 1
sh = {}
for tg, g in d.groupby("seed"):
    r = g.set_index("day").loc["2022-05-01":"2025-12-31", "ret"].dropna()
    sh[tg] = r.mean() / r.std() * np.sqrt(365)
rk = sorted(TAGS, key=lambda t: sh[t])
med = rk[3]
print("sharpe full", {k: round(v, 3) for k, v in sh.items()}, "median seed", med)
P = d.pivot(index="day", columns="seed", values="ret")
P["median_seed"] = P[med]
P.attrs["median_seed"] = med
P.to_parquet(WK + "/x14_daily.parquet")
print("days", P.index.min(), P.index.max(), len(P))
