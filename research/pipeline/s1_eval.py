"""Danh gia S1 vs baseline tam thuong (vol_7d ranker, -rk_dd_7d ranker, G015) tren nhieu outcome: g1lite, maxFav_72h, maxAdv_72h, retEnd_72h.
Muc dich: S1 co hon 'chon coin vol cao' khong? (shuffle-label fold 9 cho +3.0% -> nghi vol-confound cua g1lite)."""

# --- LUAT LOG CUA REPO: dung module `logging`, KHONG dung ham in san co.
#     Ghi ra STDOUT (khong phai stderr) de giu nguyen hanh vi cac script goi,
#     vi du: `python3 build_map.py s1a2 $P | tail -2`.
#     format="%(message)s" => output giong ban da chay sinh ra bins (xem BINS_MANIFEST.md).
import logging as _logging
import sys as _sys
_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
LOG = _logging.getLogger(__name__)


def _p(*a):
    """Gop cac doi so bang dau cach roi day qua logging (thay cho ham in san co)."""
    LOG.info(" ".join(str(x) for x in a))

import numpy as np, pandas as pd, glob
LED="/home/ubuntu/ledger"; H=3600000
D=pd.read_parquet(f"{LED}/cand_dev.parquet"); D=D[D.g1lite.notna()].copy(); D["ts_h"]=(D.ts//H)*H
F=pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet",columns=["ts","sym","vol_7d","rk_dd_7d","dd_7d"]).rename(columns={"ts":"ts_h"})
D=D.merge(F,on=["ts_h","sym"],how="left")
def edge(S,name,K=5):
    M=D.merge(S,on=["ts","sym"],how="inner") if S is not None else D.copy()
    M["rk"]=M.groupby("ts").score.rank(method="first"); top=M[M.rk<=K]
    r={"model":name,"ticks":M.ts.nunique(),"n_top":len(top)}
    for o in ("g1lite","maxFav_72h","maxAdv_72h","retEnd_72h"):
        e=top.groupby("ts")[o].mean()-M.groupby("ts")[o].mean(); r[o]=100*e.mean()
    e=top.groupby("ts").g1lite.mean()-M.groupby("ts").g1lite.mean(); y=pd.to_datetime(e.index,unit="ms").year
    for yy in (2022,2023,2024): r[f"g1_{yy}"]=100*e[y==yy].mean()
    r["top_vol7d_mean"]=top.vol_7d.mean(); r["pool_vol7d_mean"]=M.vol_7d.mean()
    return r
rows=[]
for n in ("s1a","s1b"):
    S=pd.read_parquet(f"{LED}/pred_{n}.parquet"); rows.append(edge(S,n))
    T=S.ts.unique()   # cung tap tick voi S1 cho cac baseline (fold 0 bi skip)
    if n=="s1a": continue
    rows.append(edge(D[D.ts.isin(T)][["ts","sym"]].assign(score=1-D[D.ts.isin(T)].p_g015.values),f"G015@{n}ticks"))
    rows.append(edge(D[D.ts.isin(T)][["ts","sym","vol_7d"]].assign(score=lambda x:-x.vol_7d.fillna(-1))[["ts","sym","score"]],f"vol7d_rank@{n}ticks"))
    rows.append(edge(D[D.ts.isin(T)][["ts","sym","rk_dd_7d"]].assign(score=lambda x:x.rk_dd_7d.fillna(1))[["ts","sym","score"]],f"deepDD_rank@{n}ticks"))
    X=D[D.ts.isin(T)][["ts","sym","vol_7d","rk_dd_7d"]].copy(); X["vr"]=X.groupby("ts").vol_7d.rank(pct=True); X["score"]=-X.vr.fillna(0)+X.rk_dd_7d.fillna(0.5)
    rows.append(edge(X[["ts","sym","score"]],f"vol+DD_rank@{n}ticks"))
    break
pd.set_option("display.width",250); _p(pd.DataFrame(rows).round(3).to_string(index=False))
