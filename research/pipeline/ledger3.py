"""LEDGER v3 + CHAN DOAN GATE (pre-reg: chi DO, khong doi config).
Pool mo rong: moi tick 15m co p15 >= 0.002 (nguong THAP NHAT ma 1 coin co the vao: dyn_thr =
MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN, score/RATE_MAX*AI_DYNAMIC_MULTIPLIER) -- CHI CAN DUOI,
KHONG CO TRAN (xem gate_cfg.py); score->0 => thr 0.00214). Muc dich:
 (1) GATE co dung cho khong: outcome TRUNG BINH cua pool theo bucket p15 -> gate manh = coin tot hon?
 (2) Con edge XEP HANG duoi nguong gate 0.008 khong: edge cua G015 top-K va TRAN oracle theo tung bucket.
 (3) Xuat ledger v3 de train S1 v3 tren dung pham vi trien khai (moi tick co the vao lenh).
Output: /home/ubuntu/ledger/cand_dev3.parquet + bang chan doan."""
import sys, os, glob, time, numpy as np, pandas as pd
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger(__name__)
sys.path.insert(0, "/home/ubuntu/featv2")
import gate_cfg
gate_cfg.describe()
sys.path.insert(0,"/home/ubuntu/sel1m_code"); from funding_label_pb import read_label
OUT="/home/ubuntu/ledger"; Q=900000; H=3600000; TZ=7*H
T0=int(pd.Timestamp("2021-04-01").value//1e6)-TZ; T1=int(pd.Timestamp("2024-07-01").value//1e6)-TZ
dt=np.dtype([("ts",">i8"),("sym",">i2"),("p0",">f4"),("p1",">f4"),("p2",">f4"),("p3",">f4")])
def log(*a): LOG.info(" ".join(str(x) for x in a))
G=pd.read_csv("/home/ubuntu/claudedata/wfo_gate_pred.csv",usecols=["timestamp","predReturn15M"]).rename(columns={"timestamp":"ts","predReturn15M":"p15"})
G=G[(G.ts%Q==0)&(G.ts>=T0)&(G.ts<T1)].drop_duplicates("ts"); op=G[G.p15>=0.002]
log("tick 15m:",len(G),"| p15>=0.002:",len(op),f"({len(op)/len(G):.3f})","| p15>=0.008:",int((G.p15>=0.008).sum()),f"({(G.p15>=0.008).mean():.3f})")
mp=pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); sym2id=dict(zip(mp.symbol,mp.symId))
P=[]
for f in sorted(glob.glob("/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin")):
    b=os.path.basename(f)
    if b[11:15] not in ("2021","2022","2023","2024") or b[11:19] in ("20240701","20241001"): continue
    a=np.fromfile(f,dtype=dt); P.append(pd.DataFrame({"ts":a["ts"].astype(np.int64),"sym":a["sym"].astype(np.int64),"p_g015":a["p0"].astype(np.float64)}))
P=pd.concat(P); P=P[(P.ts%Q==0)&P.ts.isin(op.ts.values)].drop_duplicates(["ts","sym"]); log("G015 rows tren pool moi",len(P))
parts=[]
for f in sorted(glob.glob("/home/ubuntu/label_15m/funding_label_202[1-4]*.pb")):
    L=read_label(f,usecols=["tEpochMs","symbol","maxFav_72h","maxAdv_72h","retEnd_72h","nBars_72h"]); L=L[L.tEpochMs%Q==0]
    L=L[L.tEpochMs.isin(op.ts.values)]; L["sym"]=L.symbol.map(sym2id); L=L.dropna(subset=["sym"]); L["sym"]=L.sym.astype(np.int64)
    parts.append(L.drop(columns=["symbol"]).rename(columns={"tEpochMs":"ts"}))
Lb=pd.concat(parts); Lb=Lb[Lb.nBars_72h>=288]; log("label rows",len(Lb))
D=Lb.merge(op,on="ts",how="inner").merge(P,on=["ts","sym"],how="left")
D["g1lite"]=np.where(D.maxFav_72h>=0.05, D.maxFav_72h-np.minimum(0.5*D.maxFav_72h,0.08), D.retEnd_72h)
D["score_g015"]=1-D.p_g015; D["dyn_thr"]=gate_cfg.dyn_thr(D.score_g015); D["gate_dyn_ok"]=D.p15>=D.dyn_thr
D.to_parquet(f"{OUT}/cand_dev3.parquet"); log("saved cand_dev3",D.shape,"ticks",D.ts.nunique(),"co p_g015",round(D.p_g015.notna().mean(),3))
# ---- chan doan theo bucket p15 ----
B=[0.002,0.004,0.006,0.008,0.012,0.02,1]; D["bk"]=pd.cut(D.p15,B,right=False)
rows=[]
for bk,g in D[D.g1lite.notna()].groupby("bk",observed=True):
    r={"bucket":str(bk),"ticks":g.ts.nunique(),"rows":len(g),"pool_g1lite%":100*g.g1lite.mean(),"pool_retEnd%":100*g.retEnd_72h.mean(),
       "pool_maxFav%":100*g.maxFav_72h.mean(),"pool_maxAdv%":100*g.maxAdv_72h.mean(),"gate_dyn_ok%":100*g.gate_dyn_ok.mean()}
    for K in (5,):
        gg=g.dropna(subset=["p_g015"]).copy()
        if len(gg):
            gg["rk"]=gg.groupby("ts").score_g015.rank(method="first"); pool=gg.groupby("ts").g1lite.mean()
            r[f"G015_edge{K}%"]=100*(gg[gg.rk<=K].groupby("ts").g1lite.mean()-pool).mean()
        oo=g.copy(); oo["rk"]=oo.groupby("ts").g1lite.rank(ascending=False,method="first")
        r[f"oracle_edge{K}%"]=100*(oo[oo.rk<=K].groupby("ts").g1lite.mean()-g.groupby("ts").g1lite.mean()).mean()
    rows.append(r)
pd.set_option("display.width",260)
LOG.info("=== CHAN DOAN GATE: outcome pool & edge xep hang theo bucket p15 (DEV 2021-04..2024-06) ===")
LOG.info("\n%s", pd.DataFrame(rows).round(2).to_string(index=False))
LOG.info("Doc: pool_* tang theo p15 => gate CO gia tri (chon THOI DIEM). oracle_edge lon o bucket duoi 0.008 => con edge XEP HANG bi gate chan.")
