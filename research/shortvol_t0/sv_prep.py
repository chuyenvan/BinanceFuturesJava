"""SHORTVOL_T0 prep (no VRP/PnL here): BTCUSDT/ETHUSDT 1m close grid 2021-12-31 00:00 -> 2025-12-31 23:59 UTC (ffill), coverage.
Outputs WK/close1m_{SYM}.parquet (ts int64 ms, close float64, filled bool), WK/prep_cov.json.
Also X14: daily MTM equity per seed (sim.out) + legs (printDone, start/end +07 -> UTC) -> WK/x14_daily.parquet, WK/x14_legs.parquet.
"""
import os, re, json, glob
import numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow.dataset as ds
WK = os.path.expanduser("~/claude_master/shortvol_t0_wk")
RAW = "/home/ubuntu/vz_e1/raw"
SYMS = ["BTCUSDT", "ETHUSDT"]
T0 = 1640908800000            # 2021-12-31 00:00 UTC
T1 = 1767225600000            # 2026-01-01 00:00 UTC (exclusive)
MIN = 60000
cov = {}
for sym in SYMS:
    parts = []
    for f in sorted(glob.glob(os.path.join(RAW, "kline1m-*.parquet"))):
        ym = f[-15:-8]
        if ym < "2021-12" or ym > "2025-12":
            continue
        t = pq.read_table(f, columns=["ts", "sym", "close"], filters=[("sym", "=", sym)])
        assert str(t.schema.field("ts").type) == "int64", t.schema
        d = pd.DataFrame({"ts": t.column("ts").to_numpy(), "close": t.column("close").to_numpy()})
        parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    assert d.ts.dtype == np.int64
    assert (d.ts % MIN == 0).all(), "non-minute ts"
    ndup = int(d.duplicated("ts").sum())
    assert d.drop_duplicates().duplicated("ts").sum() == 0, "conflicting dup"
    d = d.drop_duplicates("ts")
    d = d[(d.ts >= T0) & (d.ts < T1)].sort_values("ts")
    assert d.close.notna().all() and (d.close > 0).all()
    grid = np.arange(T0, T1, MIN, dtype=np.int64)
    n_exp = (T1 - T0) // MIN
    assert len(grid) == n_exp == 1462 * 1440
    g = pd.DataFrame({"ts": grid}).merge(d, on="ts", how="left")
    g["filled"] = g.close.isna()
    assert not g.close.iloc[0:1].isna().any(), "first minute missing"
    g["close"] = g.close.ffill()
    assert g.ts.is_unique and len(g) == n_exp and g.close.notna().all()
    day = pd.to_datetime(g.ts[g.filled], unit="ms").dt.strftime("%Y-%m-%d")
    cov[sym] = dict(n_grid=int(len(g)), n_raw_in_range=int(len(d)), n_filled=int(g.filled.sum()), dup_removed=ndup,
                    filled_by_day=day.value_counts().sort_index().to_dict())
    g.to_parquet(os.path.join(WK, "close1m_%s.parquet" % sym), index=False)
    print(sym, {k: v for k, v in cov[sym].items() if k != "filled_by_day"}, cov[sym]["filled_by_day"], flush=True)
# X14
OUT = "/home/ubuntu/kaggle_sim/out"
TAGS = ["a1", "s123", "s13", "s2024", "s21", "s7", "s777", "s99"]
RX = re.compile(r"BudgetManagerSimple: Update (\d{8}) 07:00 => b:\s*(-?\d+)\s+pD:.*?unP:\s*(-?\d+)\s")
rows, legs = [], []
for tg in TAGS:
    for line in open(os.path.join(OUT, "tsx-x14-" + tg, "logs", "sim.out"), errors="replace"):
        m = RX.search(line)
        if m:
            rows.append((tg, m.group(1), int(m.group(2)), int(m.group(3))))
    p = pd.read_csv(os.path.join(OUT, "tsx-x14-" + tg, "storage", "printDone.csv"), index_col=False)
    p.columns = [c.strip() for c in p.columns]
    s = pd.to_datetime(p["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
    e = pd.to_datetime(p["end"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
    legs.append(pd.DataFrame(dict(seed=tg, sym=p["sym"].astype(str), level=p["level"].astype(str),
                                  start_ms=(s.astype("int64") // 10**6).astype(np.int64), end_ms=(e.astype("int64") // 10**6).astype(np.int64))))
d = pd.DataFrame(rows, columns=["seed", "date", "b", "unP"])
d["day_ms"] = (pd.to_datetime(d["date"], format="%Y%m%d").astype("int64") // 10**6).astype(np.int64)  # 07:00 +07 = 00:00 UTC of date
assert not d.duplicated(["seed", "day_ms"]).any()
d["E"] = d["b"] + d["unP"]
d.sort_values(["seed", "day_ms"]).to_parquet(os.path.join(WK, "x14_daily.parquet"), index=False)
L = pd.concat(legs, ignore_index=True)
assert (L.end_ms >= L.start_ms).all()
L.to_parquet(os.path.join(WK, "x14_legs.parquet"), index=False)
cov["x14"] = dict(n_daily=int(len(d)), per_seed={k: [int(len(g)), str(g.date.min()), str(g.date.max())] for k, g in d.groupby("seed")},
                  n_legs=int(len(L)), legs_first=str(pd.to_datetime(L.start_ms.min(), unit="ms")), legs_last=str(pd.to_datetime(L.start_ms.max(), unit="ms")))
print(cov["x14"])
json.dump(cov, open(os.path.join(WK, "prep_cov.json"), "w"), indent=1)
