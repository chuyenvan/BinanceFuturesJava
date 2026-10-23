"""TREND_T1: X14 daily equity per seed from sim.out 'BudgetManagerSimple: Update YYYYMMDD 07:00 => b:.. unP:..'
07:00 (+07) = 00:00 UTC of YYYYMMDD. E_mtm = b + unP (equity at 00:00 UTC). Daily return of UTC day D = E(D+1)/E(D)-1.
Also leg-coverage per UTC day from printDone (start/end are +07 -> -7h).
"""
import re, os, json, glob
import numpy as np, pandas as pd
OUT = "/home/ubuntu/kaggle_sim/out"
WK = os.path.expanduser("~/claude_master/trend_t1_wk")
TAGS = ["a1", "s123", "s13", "s2024", "s21", "s7", "s777", "s99"]
RX = re.compile(r"BudgetManagerSimple: Update (\d{8}) 07:00 => b:\s*(-?\d+)\s+pD:.*?unP:\s*(-?\d+)\s")
rows = []
cov = []
for tg in TAGS:
    p = os.path.join(OUT, "tsx-x14-" + tg, "logs", "sim.out")
    n = 0
    for line in open(p, errors="replace"):
        m = RX.search(line)
        if m:
            rows.append((tg, m.group(1), int(m.group(2)), int(m.group(3)))); n += 1
    pdn = pd.read_csv(os.path.join(OUT, "tsx-x14-" + tg, "storage", "printDone.csv"), index_col=False)
    pdn.columns = [c.strip() for c in pdn.columns]
    s = pd.to_datetime(pdn["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
    e = pd.to_datetime(pdn["end"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
    days = pd.date_range("2021-07-01", "2025-12-31", freq="D")
    has = np.zeros(len(days), bool)
    d0 = days[0]
    for a, b in zip(s, e):
        i0 = max(0, (a.normalize() - d0).days); i1 = min(len(days) - 1, (b.normalize() - d0).days)
        has[i0:i1 + 1] = True
    cov.append(pd.DataFrame(dict(seed=tg, day=days, has_leg=has)))
    print(tg, "update lines", n, "legs", len(pdn))
d = pd.DataFrame(rows, columns=["seed", "date", "b", "unP"])
d["day"] = pd.to_datetime(d["date"], format="%Y%m%d")
assert not d.duplicated(["seed", "day"]).any()
d["E"] = d["b"] + d["unP"]
d = d.sort_values(["seed", "day"])
d["ret"] = d.groupby("seed")["E"].shift(-1) / d["E"] - 1  # return of UTC day 'day'
d["ret_b"] = d.groupby("seed")["b"].shift(-1) / d["b"] - 1
d.to_parquet(os.path.join(WK, "x14_daily.parquet"), index=False)
pd.concat(cov).to_parquet(os.path.join(WK, "x14_legcov.parquet"), index=False)
def st(r):
    r = r.dropna(); eq = (1 + r).cumprod(); eq = pd.concat([pd.Series([1.0]), eq.reset_index(drop=True)])
    return dict(n=len(r), sh=r.mean() / r.std() * np.sqrt(365), mdd=(eq / eq.cummax() - 1).min(), cagr=eq.iloc[-1] ** (365 / len(r)) - 1)
res = {}
for tg, g in d.groupby("seed"):
    g = g.set_index("day")
    res[tg] = {k: {"mtm": st(g.loc[a:b, "ret"]), "b": st(g.loc[a:b, "ret_b"])} for k, (a, b) in
               dict(full=("2022-05-01", "2025-12-31"), dev=("2022-05-01", "2023-12-31"), test=("2024-01-01", "2025-12-31"), dev2225=("2022-01-01", "2025-12-31")).items()}
    print(tg, {k: (round(v["mtm"]["sh"], 3), round(v["mtm"]["mdd"], 3), round(v["b"]["sh"], 3), round(v["b"]["mdd"], 3), round(v["mtm"]["cagr"], 3)) for k, v in res[tg].items()}, "last day", g.index.max().date())
json.dump(res, open(os.path.join(WK, "x14_stats.json"), "w"), indent=1, default=float)
rk = sorted(TAGS, key=lambda t: res[t]["full"]["mtm"]["sh"])
print("rank by full MTM sharpe asc", rk, "median seed (rank4/8)=", rk[3])
