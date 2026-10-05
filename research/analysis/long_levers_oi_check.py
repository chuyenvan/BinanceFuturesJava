#!/usr/bin/env python3
"""AUDIT LONG_LEVERS 2026-10-02 — MO TA (post-hoc, KHONG phai ket luan): OI tai luc vao cua lenh B0.
Kiem xem tin hieu H3 cua RESULT_OI_STUDY (dOI24h thap tot hon tai su kien MOM15) co hien dien tren tap lenh B0 khong.
Nguon: printDone B0 (de-p1) + /home/ubuntu/claudedata/oi/oi_percoin_full.bin (>i8 ts ms, >i2 sym, 5x>f4; c0=oi_delta24h, c1=oi_z).
Causal: lay ban ghi OI GAN NHAT co ts <= t_entry (tolerance 30 phut). Gio printDone = UTC+7 (offset -7h, xem anatomy).
"""
import sys, json
import numpy as np, pandas as pd

PD = "/home/ubuntu/kaggle_sim/out/de-p1/storage/printDone.csv"
OI = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
SM = "/home/ubuntu/claudedata/oi/symbol_map.csv"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ll_oi.json"
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", (5,))])
TOL = 30 * 60 * 1000
d = pd.read_csv(PD)
d["t0"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
d["t0ms"] = d.t0.astype("int64") // 10**6
m = pd.read_csv(SM)
mp = dict(zip(m.symbol.str.replace("USDT$", "", regex=True), m.symId))
d["oid"] = d.sym.map(mp)
print("map rate", d.oid.notna().mean())
need = set(int(x) for x in d.oid.dropna())
wins = np.sort(d.t0ms.unique())
mm = np.memmap(OI, dtype=DT, mode="r")
keep = []
CH = 10_000_000
for s in range(0, len(mm), CH):
    b = mm[s:s + CH]
    ts = np.asarray(b["ts"], dtype=np.int64)
    j = np.searchsorted(wins, ts, side="left")  # cua so dau tien co t0 >= ts
    j = np.minimum(j, len(wins) - 1)
    ok = (wins[j] >= ts) & (wins[j] - ts <= TOL)
    if not ok.any(): continue
    sy = np.asarray(b["sym"][ok], dtype=np.int64)
    sel = np.isin(sy, list(need))
    oi = np.asarray(b["oi"][ok], dtype=np.float64)[sel]
    keep.append(pd.DataFrame({"ts": ts[ok][sel], "oid": sy[sel], "d24": oi[:, 0], "oiz": oi[:, 1]}))
K = pd.concat(keep).sort_values("ts")
print("kept", len(K))

d = d[d.oid.notna()].copy(); d["oid"] = d.oid.astype(np.int64)
d = pd.merge_asof(d.sort_values("t0ms"), K.rename(columns={"ts": "t0ms"}).sort_values("t0ms"),
                  on="t0ms", by="oid", direction="backward", tolerance=TOL)
R = {"n": int(len(d)), "cov_d24": float(d.d24.notna().mean()), "cov_oiz": float(d.oiz.notna().mean())}
print(R)
rng = np.random.default_rng(20260905)
d["blk"] = ((d.t0 - pd.Timestamp("2021-07-01")).dt.total_seconds() // (72 * 3600)).astype(int)
d["yr"] = d.t0.dt.year
TOT = d.pnl.sum()


def bsum(v):
    s = pd.Series(v.values, index=d.loc[v.index, "blk"].values).groupby(level=0).sum()
    arr = s.values
    bs = [arr[rng.integers(0, len(arr), len(arr))].sum() for _ in range(2000)]
    return [float(v.sum()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]


for col in ("d24", "oiz"):
    g = d[d[col].notna()].copy()
    g["ter"] = pd.qcut(g[col], 3, labels=["T0low", "T1", "T2high"])
    t = g.groupby("ter").agg(n=("pnl", "size"), pnl=("pnl", "sum"), mean_profit=("profit", "mean"),
                             med_profit=("profit", "median"), tsloss=("status", lambda x: (x == "STOP_LOSS_DONE").mean()))
    print("\n##", col); print(t.round(3).to_string())
    R[col + "_tercile"] = t.round(4).reset_index().astype({"ter": str}).to_dict("records")
    yr = g.groupby(["yr", "ter"]).profit.mean().unstack().round(2)
    print(yr.to_string()); R[col + "_tercile_by_year_meanprofit"] = {int(k): v for k, v in yr.T.to_dict().items()}
    rk = (-g[col]).rank(pct=True); w = 0.5 + rk
    w = w / (w * g.notional_ if False else w).mean() if False else w / w.mean()
    dl = (w - 1) * g.pnl
    R[col + "_sizing_dPnL_ci"] = bsum(dl)
    lowcut = g[g.ter != "T2high"]
    R[col + "_drop_T2high"] = {"n_left": int(len(lowcut)), "pnl_left": float(lowcut.pnl.sum()),
                               "pnl_dropped": float(g[g.ter == "T2high"].pnl.sum()),
                               "dropped_ci": bsum(g.pnl.where(g.ter == "T2high", 0.0))}
    print(col, "sizing dPnL CI", R[col + "_sizing_dPnL_ci"], "drop T2high", R[col + "_drop_T2high"])
json.dump(R, open(OUT, "w"), indent=1, default=str)
print("WROTE", OUT)
