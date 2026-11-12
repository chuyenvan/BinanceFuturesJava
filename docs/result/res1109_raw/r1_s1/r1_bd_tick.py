"""R1 (chi doc): leg BIG_DOWN B0 x14 DEV 2024-07..2025-12. Sim chon theo bins S1-map; live (SELECTOR_TIER1_NET015=true)
chon theo net015-raw. Voi moi su kien (seed, phut): S = coin sim da vao; H = coin hang map < max hang S ma khong vao
(suy ra dang giu); L = |S| coin dau theo net015 bo H. Dem leg trong S khong thuoc L + PnL."""
import glob
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("r1bd")
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
Q, H7 = 900000, 7 * 3600000
MAPD, NETD = "/home/ubuntu/predwf_map_s1a2_x1", "/home/ubuntu/val_pred_net015"
s2i = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv").set_index("symbol").symId.to_dict()
S1TS = set(pd.read_parquet("/home/ubuntu/ledger/pred_s1a2x1.parquet", columns=["ts"]).ts.unique().tolist())
legs = []
for d in sorted(glob.glob("/home/ubuntu/kaggle_sim/out/tsx-x14-*")):
    x = pd.read_csv(d + "/storage/printDone.csv", index_col=False, usecols=["sym", "level", "pnl", "start"])
    x = x[x.level == "BIG_DOWN"].copy()
    ms = pd.to_datetime(x.start, format="%Y%m%d %H:%M").astype("datetime64[ms]").astype("int64")
    x["minute"] = ms - H7
    x["tick"] = (x.minute // Q) * Q
    x["tag"] = d.rsplit("/", 1)[-1]
    legs.append(x)
L = pd.concat(legs)
L["pnl"] = pd.to_numeric(L.pnl, errors="coerce")
L = L[(L.tick >= 1719792000000) & (L.tick < 1767225600000)]
L["sid"] = L.sym.map(lambda s: s2i.get(str(s) + chr(85) + chr(83) + chr(68) + chr(84)))
log.info("leg BIG_DOWN 2024-07..2025-12: %d (8 seed), thieu symId %d", len(L), L.sid.isna().sum())
need = set(L.tick.unique().tolist())
rows = {}
for fn in sorted(glob.glob(NETD + "/predict_wf_*.bin")):
    b = os.path.basename(fn)
    a = np.fromfile(os.path.join(MAPD, b), dtype=REC)
    n = np.fromfile(fn, dtype=REC)
    ka = np.isin(a["ts"].astype("i8"), list(need))
    kn = np.isin(n["ts"].astype("i8"), list(need))
    A = pd.DataFrame({"ts": a["ts"][ka].astype("i8"), "sym": a["sym"][ka].astype("i8"), "pm": a["p0"][ka].astype("f8")})
    N = pd.DataFrame({"ts": n["ts"][kn].astype("i8"), "sym": n["sym"][kn].astype("i8"), "pn": n["p0"][kn].astype("f8")})
    M = A.merge(N, on=["ts", "sym"]).dropna()
    for t, g in M.groupby("ts"):
        rows[t] = g
log.info("tick co bins: %d / %d", len(rows), len(need))
out = []
for (tag, minute), ev in L.groupby(["tag", "tick"]):
    t = ev.tick.iloc[0]
    g = rows.get(t)
    if g is None:
        continue
    om = g.sort_values("pm", ascending=False).sym.tolist()
    on = g.sort_values("pn", ascending=False).sym.tolist()
    S = [int(s) for s in ev.sid.dropna()]
    rk = {s: i for i, s in enumerate(om)}
    rS = [rk.get(s, 10 ** 6) for s in S]
    mx = max(rS) if rS else -1
    Hs = set(om[:mx + 1]) - set(S)
    Lv = [s for s in on if s not in Hs][:len(S)]
    for _, r in ev.iterrows():
        s = int(r.sid) if not np.isnan(r.sid) else -1
        out.append(dict(tag=tag, year=pd.to_datetime(t, unit="ms").year, s1tick=t in S1TS, map_rank=rk.get(s, -1) + 1,
                        held_inf=len(Hs), diff=s not in Lv, pnl=r.pnl))
O = pd.DataFrame(out)
log.info("leg danh gia duoc: %d; hang map cua leg sim: %s", len(O), O.map_rank.value_counts().sort_index().head(8).to_dict())
for k, g in O.groupby(["year", "s1tick"]):
    log.info("nam=%s tick_co_S1=%s n=%d khac_live=%.3f pnl_leg_khac=%.0f pnl_tong=%.0f (tong 8 seed)", k[0], k[1], len(g),
             g["diff"].mean(), g.loc[g["diff"], "pnl"].sum(), g.pnl.sum())
log.info("TONG: khac_live=%.3f pnl_khac/seed=%.0f pnl_BD/seed=%.0f pnl/leg khac=%.1f vs giong=%.1f", O["diff"].mean(),
         O.loc[O["diff"], "pnl"].sum() / 8, O.pnl.sum() / 8, O.loc[O["diff"], "pnl"].mean(), O.loc[~O["diff"], "pnl"].mean())
