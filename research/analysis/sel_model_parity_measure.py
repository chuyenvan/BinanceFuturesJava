"""AUDIT parity symbolPred LIVE (Funding_Classifier_Final.onnx) vs SIM (net015 x26
mapped, predwf_map_s1a2_x1). READ-ONLY. Fold 20251001 (OOS 2025Q4)."""
import os, sys, struct, logging
import numpy as np, pandas as pd
from scipy.stats import spearmanr
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("selpar")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from tool1_col import read_tool1
GRID_MS=15*60*1000; TZ=7*3600*1000; OI_TOL=2*3600*1000
OI_DT=np.dtype([("ts",">i8"),("sym",">i2"),("oi",">f4",5)])
OI_NAMES=["oi_delta24h","oi_z","ls_global","ls_toptrader","taker_buy"]
DDIR="/home/ubuntu/ds_feat15m"; OI_FILE="/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
MAP_CSV="/home/ubuntu/claudedata/oi/symbol_map.csv"
FCLF="/home/ubuntu/shadow_c3/storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx"
MAPBIN="/home/ubuntu/predwf_map_s1a2_x1/predict_wf_20251001.bin"
RAWBIN="/home/ubuntu/claudedata/predwf_G015x26/predict_wf_20251001.bin"
GATE="/home/ubuntu/claudedata/wfo_gate_pred.csv"
MM=0.008; DMIN=0.26787; RMAX=0.15; DMULT=1.28760; K=8
def dyn_thr(sp):
    sp=np.asarray(sp,dtype=np.float64)
    return MM*np.maximum(DMIN, sp/RMAX*DMULT)
def load_bin(p):
    a=np.fromfile(p,dtype=np.uint8); n=len(a)//26; a=a[:n*26].reshape(n,26)
    ts=np.frombuffer(a[:,0:8].tobytes(),dtype=">i8").astype(np.int64)
    sym=np.frombuffer(a[:,8:10].tobytes(),dtype=">i2").astype(np.int64)
    p0=np.frombuffer(a[:,10:14].tobytes(),dtype=">f4").astype(np.float64)
    return ts,sym,p0
c=int(pd.Timestamp("2025-10-01",tz="UTC").value//1_000_000)-TZ
cdt=pd.to_datetime(c+TZ,unit="ms").normalize()
lo_b=c; hi_b=int((cdt+pd.DateOffset(months=3)).value//1_000_000)-TZ
log.info("block=[%s .. %s)",pd.to_datetime(lo_b,unit="ms"),pd.to_datetime(hi_b,unit="ms"))
ao=np.memmap(OI_FILE,dtype=OI_DT,mode="r"); m=pd.read_csv(MAP_CSV)
a=read_tool1(os.path.join(DDIR,"features_2025*"),grid_ms=GRID_MS); F=a["f"]
lo=int(pd.Timestamp("2025-01-01",tz="UTC").value//1_000_000)
hi=int(pd.Timestamp("2026-01-01",tz="UTC").value//1_000_000)
aots=np.asarray(ao["ts"]); msk=(aots>=lo-OI_TOL)&(aots<hi); del aots
aoc=np.array(ao[msk]); del msk, ao
t=pd.DataFrame({"ts":a["ts"].astype(np.int64),"symId":a["sym"].astype(np.int32),"ridx":np.arange(len(a),dtype=np.int64)})
o=pd.DataFrame({"ts":aoc["ts"].astype(np.int64),"symId":aoc["sym"].astype(np.int32)})
O=np.asarray(aoc["oi"],dtype=np.float32)
for j,nm in enumerate(OI_NAMES): o[nm]=O[:,j]
del aoc,O
t=t.sort_values("ts").reset_index(drop=True); o=o.sort_values("ts").reset_index(drop=True)
mg=pd.merge_asof(t,o,on="ts",by="symId",direction="backward",tolerance=OI_TOL); del t,o
mg=mg.merge(m,on="symId",how="left").dropna(subset=["symbol"]).sort_values("ts").reset_index(drop=True)
tsv=mg["ts"].to_numpy(); sub=mg[(tsv>=lo_b)&(tsv<hi_b)].copy(); n=len(sub)
X=np.empty((n,45),dtype=np.float32)
X[:,:40]=F[sub["ridx"].to_numpy()]; X[:,40:]=sub[OI_NAMES].to_numpy(np.float32)
kts=sub["ts"].to_numpy(np.int64); ksid=sub["symId"].to_numpy(np.int64)
del a,F,mg,sub
log.info("rebuilt rows=%d",n)
import onnxruntime as ort
sess=ort.InferenceSession(FCLF,providers=["CPUExecutionProvider"])
iname=sess.get_inputs()[0].name
live=np.empty(n,dtype=np.float64); B=400000
for s in range(0,n,B):
    e=min(s+B,n); r=sess.run(None,{iname:X[s:e]}); prob=r[1]
    if isinstance(prob,list): pa=np.array([row[0] for row in prob],dtype=np.float64)
    else: pa=np.asarray(prob)[:,0].astype(np.float64)
    live[s:e]=pa
log.info("live_sp mean=%.5f std=%.5f (P class0=fail)",live.mean(),live.std())
key=kts*1000+ksid
mts,msid,mp0=load_bin(MAPBIN); mkey=mts*1000+msid; sim_map=1.0-mp0
rts,rsid,rp0=load_bin(RAWBIN); rkey=rts*1000+rsid; net_raw=1.0-rp0
dsim=dict(zip(mkey,sim_map)); draw=dict(zip(rkey,net_raw))
sim=np.array([dsim.get(k,np.nan) for k in key])
raw=np.array([draw.get(k,np.nan) for k in key])
ok=np.isfinite(sim)&np.isfinite(raw)&np.isfinite(live)
log.info("join coverage: %d/%d = %.3f%% keys matched",ok.sum(),n,100*ok.mean())
live,sim,raw,kts2,ksid2=live[ok],sim[ok],raw[ok],kts[ok],ksid[ok]
g=pd.read_csv(GATE,usecols=["timestamp","predReturn15M"]).drop_duplicates("timestamp")
gd=dict(zip(g["timestamp"].to_numpy(np.int64),g["predReturn15M"].to_numpy(np.float64)))
p15=np.array([gd.get(int(t),np.nan) for t in kts2])
log.info("p15 coverage: %.3f%%",100*np.isfinite(p15).mean())
def spr(a,b,lab):
    idx=np.random.default_rng(0).choice(len(a),size=min(300000,len(a)),replace=False)
    print("  spearman %-22s = %.5f"%(lab,spearmanr(a[idx],b[idx]).statistic))
print("\n===== 1. DISTRIBUTION (symbolPred, low=good) =====")
for nm,v in [("live (FundingClf P0)",live),("sim (net015 mapped 1-p0)",sim),("net_raw (net015 raw)",raw)]:
    print("  %-26s mean=%.5f std=%.5f p10=%.5f p50=%.5f p90=%.5f"%(nm,v.mean(),v.std(),np.percentile(v,10),np.percentile(v,50),np.percentile(v,90)))
print("===== 2. MONOTONICITY (spearman) =====")
spr(live,sim,"live vs sim(mapped)"); spr(live,raw,"live vs net_raw"); spr(sim,raw,"sim(map) vs net_raw")
print("===== 3. dyn_thr distribution (all rows) =====")
for nm,v in [("live",live),("sim",sim)]:
    d=dyn_thr(v); print("  dyn_thr %-5s mean=%.5f p10=%.5f p50=%.5f p90=%.5f min=%.5f max=%.5f"%(nm,d.mean(),np.percentile(d,10),np.percentile(d,50),np.percentile(d,90),d.min(),d.max()))
df=pd.DataFrame({"ts":kts2,"sid":ksid2,"live":live,"sim":sim,"p15":p15}).dropna(subset=["p15"])
print("===== 4. PER-TICK TOP-8 (sim ranking), swap gate VALUE model =====")
flips=0; slots=0; pass_sim=0; pass_live=0; jac=[]; nps=[]; npl=[]
for ts,x in df.groupby("ts"):
    t8=x.nsmallest(K,"sim")
    ds=dyn_thr(t8["sim"].to_numpy()); dl=dyn_thr(t8["live"].to_numpy()); pv=t8["p15"].to_numpy()
    dec_s=ds<=pv; dec_l=dl<=pv
    flips+=int((dec_s!=dec_l).sum()); slots+=len(t8)
    pass_sim+=int(dec_s.sum()); pass_live+=int(dec_l.sum())
    nps.append(int(dec_s.sum())); npl.append(int(dec_l.sum()))
    ls=set(t8["sid"]); ll=set(x.nsmallest(K,"live")["sid"]); jac.append(len(ls&ll)/max(len(ls|ll),1))
print("  ticks=%d  top8 slots=%d"%(df["ts"].nunique(),slots))
print("  pass_sim=%d (%.2f%%)  pass_live=%d (%.2f%%)"%(pass_sim,100*pass_sim/slots,pass_live,100*pass_live/slots))
print("  DECISION FLIPS (same coin, swap value model): %d / %d = %.2f%% of top-8 slots"%(flips,slots,100*flips/slots))
print("  mean passes/tick: sim=%.3f live=%.3f (K=%d)"%(np.mean(nps),np.mean(npl),K))
print("  top-8 SET overlap (Jaccard sim-rank vs live-rank): mean=%.3f median=%.3f"%(np.mean(jac),np.median(jac)))
