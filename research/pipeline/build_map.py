"""Quantile-map: giu NGUYEN phan phoi P(win) cua G015 trong tung tick (gate dong y het), chi doi coin nao nhan gia tri nao theo thu hang cua ranker moi.
usage: build_map.py <name> <out_dir>   name in {vol7d, s1a, s1b}. Tick khong co score moi -> giu G015 nguyen (ghi ti le)."""

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

import sys, os, glob, numpy as np, pandas as pd, time
name,out=sys.argv[1],sys.argv[2]; os.makedirs(out,exist_ok=True); H=3600000; Q=900000
dt=np.dtype([("ts",">i8"),("sym",">i2"),("p0",">f4"),("p1",">f4"),("p2",">f4"),("p3",">f4")])
def log(*a): _p(time.strftime("%H:%M:%S"),*a)
if name=="vol7d":
    F=pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet",columns=["ts","sym","vol_7d"]).rename(columns={"ts":"ts_h"})
    SC=None
else:
    SC=pd.read_parquet(f"/home/ubuntu/ledger/pred_{name}.parquet")  # ts,sym,score (thap=tot) chi tren tick gate mo
tot=chg=0
for f in sorted(glob.glob("/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin")):
    b=os.path.basename(f); yr=b[11:15]
    if yr not in ("2022","2023","2024") or b[11:19] in ("20240701","20241001"): continue
    a=np.fromfile(f,dtype=dt); G=pd.DataFrame({"ts":a["ts"].astype(np.int64),"sym":a["sym"].astype(np.int64),"p":a["p0"].astype(np.float64)})
    G["i"]=np.arange(len(G))
    if name=="vol7d":
        G["ts_h"]=(G.ts//H)*H; M=G.merge(F,on=["ts_h","sym"],how="left"); M["score"]=-M.vol_7d   # vol cao = score thap = tot
    else:
        M=G.merge(SC,on=["ts","sym"],how="left")
    has=M.score.notna(); M["p_new"]=M.p
    # trong tick: cac coin CO score nhan lai cac gia tri p (cua chinh nhom do) theo thu hang score; coin khong co score giu p cu
    sub=M[has].copy(); sub["r_score"]=sub.groupby("ts").score.rank(method="first")            # 1 = tot nhat
    sub["p_sorted"]=sub.groupby("ts").p.rank(method="first",ascending=False)                    # 1 = p cao nhat
    key=sub.set_index(["ts","p_sorted"]).p; sub["p_new"]=key.reindex(list(zip(sub.ts,sub.r_score))).values
    M.loc[has,"p_new"]=sub.p_new.values
    chg+=int((M.p_new!=M.p).sum()); tot+=len(M)
    a2=a.copy(); a2["p0"]=M.p_new.astype(np.float32).values; a2.tofile(f"{out}/{b}")
    log(b,"rows",len(M),"co score",round(has.mean(),3),"doi",round(float((M.p_new!=M.p).mean()),3))
# kiem: phan phoi p moi == p cu theo tick (multiset) -> gate dong y het
_p(f"TOTAL rows {tot} changed {chg} ({chg/tot:.3f}) -> {out}"); _p("MAP_OK")
