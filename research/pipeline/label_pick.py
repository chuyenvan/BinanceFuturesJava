"""CHON LABEL bang DU LIEU: label nao mo ta dung nhat cai sim THUC SU kiem duoc?
(A) Tren LENH THAT (printDone cac run da co): tuong quan Spearman giua tung label ung vien va ROI thuc (pnl/margin),
    + bang decile ROI theo label. Sym printDone = 'STMX' -> can + 'USDT'.
(B) Tren POOL (8.3M dong): rank-corr TRONG TICK giua tung ung vien va g1_replay (muc tieu that) -> train tren ung vien nao gan g1_replay nhat.
Ung vien: maxFav_72h (label hien tai, nguong 6%), maxFav_h, retEnd_72h, g1lite (proxy cu), nH_above_6, nH_above_3, frac_above_6, g1_replay."""

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

import sys, numpy as np, pandas as pd
from scipy.stats import spearmanr
LED="/home/ubuntu/ledger"; Q=900000; TZ=7*3600000
P=pd.read_parquet(f"{LED}/path_labels.parquet")
C=pd.read_parquet(f"{LED}/cand_dev3.parquet",columns=["ts","sym","p15","maxFav_72h","retEnd_72h","g1lite"])
D=P.merge(C,on=["ts","sym"],how="left")
CAND=["maxFav_72h","maxFav_h","retEnd_72h","g1lite","nH_above_6","nH_above_3","frac_above_6","g1_replay"]
_p("=== (A) TREN LENH THAT: Spearman(label, ROI thuc = pnl/margin) ===")
mp=pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); s2i=dict(zip(mp.symbol,mp.symId))
rows=[]
for t in sys.argv[1:]:
    d=pd.read_csv(f"/home/ubuntu/java/devrun/{t}/storage/printDone.csv")
    st=pd.to_datetime(d.start,format="%Y%m%d %H:%M").astype("int64")//10**6 - TZ
    d["ts"]=(st//Q)*Q; d["sym"]=d.sym.astype(str).apply(lambda s: s2i.get(s+"USDT", s2i.get(s, np.nan)))
    d=d.dropna(subset=["sym"]); d["sym"]=d.sym.astype(int); d["roi"]=d.pnl/d.margin
    M=d.merge(D,on=["ts","sym"],how="inner")
    r={"run":t,"lenh":len(d),"khop_label":len(M),"ROI_tb%":100*M.roi.mean()}
    for c in CAND:
        v=M[[c,"roi"]].dropna(); r[c]=round(spearmanr(v[c],v.roi).correlation,3) if len(v)>50 else np.nan
    rows.append(r)
    if t==sys.argv[1]:
        _p(f"\n  [{t}] decile ROI thuc theo label (label cao = decile 9):")
        for c in ["maxFav_72h","nH_above_6","g1_replay"]:
            v=M[[c,"roi"]].dropna(); q=pd.qcut(v[c].rank(method="first"),10,labels=False)
            _p(f"   {c:12s}", [round(100*x,1) for x in v.groupby(q).roi.mean().tolist()])
pd.set_option("display.width",240); _p(pd.DataFrame(rows).round(3).to_string(index=False))
_p("\n=== (B) TREN POOL: rank-corr TRONG TICK giua ung vien va g1_replay (muc tieu that) ===")
S=D.dropna(subset=["g1_replay"]).sample(min(1_500_000,len(D)),random_state=0)
S["gr"]=S.groupby("ts").g1_replay.rank(pct=True)
out=[]
for c in CAND:
    v=S[[c,"gr","ts"]].dropna(); v["cr"]=v.groupby("ts")[c].rank(pct=True)
    out.append({"label":c,"rank_corr_vs_g1replay":round(spearmanr(v.cr,v.gr).correlation,4),"n":len(v)})
_p(pd.DataFrame(out).to_string(index=False))
_p("\n=== (C) top-5 theo tung label: g1_replay TRUNG BINH thuc te (trong tick, pool day) ===")
res=[]
for c in CAND:
    v=S[["ts",c,"g1_replay"]].dropna().copy(); v["r"]=v.groupby("ts")[c].rank(ascending=False,method="first")
    pool=v.groupby("ts").g1_replay.mean(); top=v[v.r<=5].groupby("ts").g1_replay.mean()
    res.append({"label":c,"top5_g1replay%":100*top.mean(),"pool%":100*pool.mean(),"edge%":100*(top-pool).mean()})
_p(pd.DataFrame(res).round(3).to_string(index=False))
