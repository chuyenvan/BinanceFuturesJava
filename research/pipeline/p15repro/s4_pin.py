import numpy as np, pandas as pd, struct, onnxruntime as ort

def load_pb():
    raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read()
    n=struct.unpack(">i",raw[:4])[0]
    a=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
    return pd.DataFrame({"ts":a["ts"].astype(np.int64),"pb":a["p15"].astype(np.float64)})
pb=load_pb()
print("== pred.bin ts grid ==")
print("n=%d unique=%d dup=%d"%(len(pb),pb.ts.nunique(),len(pb)-pb.ts.nunique()))
d=np.diff(pb.ts.values)
vc=pd.Series(d).value_counts().head(8)
print("diff counts (ms):",{int(k):int(v) for k,v in vc.items()})
dups=pb[pb.ts.duplicated(keep=False)].sort_values("ts")
print("dup rows=%d ; vi du ts:"%len(dups), dups.ts.head(6).tolist())
if len(dups): print("  dup value bang nhau?", bool((dups.groupby('ts').pb.nunique()==1).all()))
print("grid alignment: ts %% 60000 ==0 ->", float((pb.ts%60000==0).mean()))

# so voi label_oldbasket csv
lb=pd.read_csv("/home/ubuntu/claudedata/gate_ab_full/wfo_gate_pred_label_oldbasket.csv")
lb=lb.rename(columns={"timestamp":"ts","predReturn15M":"lb"})
m=pb.merge(lb[["ts","lb"]],on="ts",how="inner")
dd=np.abs(m.pb-m.lb)
print("\n== pred.bin vs gate_ab_full/label_oldbasket.csv ==")
print("n=%d corr=%.6f  |d|: mean=%.3e p50=%.3e p99=%.3e max=%.3e ; frac>1e-6=%.4f"%(len(m),np.corrcoef(m.pb,m.lb)[0,1],dd.mean(),dd.quantile(.5),dd.quantile(.99),dd.max(),(dd>1e-6).mean()))

# so sanh model 2 bo tren cung store (fold 18)
V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike"]
LO=int(pd.Timestamp(year=2025,month=10,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
HI=int(pd.Timestamp(year=2026,month=1,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
t=pd.read_csv("/home/ubuntu/claudedata/gate_dataset_full.csv.gz",usecols=["timestamp"]+V3FULL)
t=t[(t.timestamp>=LO)&(t.timestamp<HI)].set_index("timestamp")
X=t.values.astype(np.float32)
out={}
for tag,mp in [("wfo_models/fold_18","/home/ubuntu/claudedata/wfo_models/fold_18/Model_Regressor_Return15M.onnx"),
               ("gate_ab_full/label_oldbasket/fold_18","/home/ubuntu/claudedata/gate_ab_full/models/label_oldbasket/fold_18/Model_Regressor_Return15M.onnx")]:
    s=ort.InferenceSession(mp,providers=["CPUExecutionProvider"])
    p=s.run(None,{s.get_inputs()[0].name:X})[0].ravel().astype(np.float64)
    out[tag]=pd.Series(p,index=t.index)
o=pd.DataFrame(out).reset_index().rename(columns={"timestamp":"ts"})
for ref,name in [(pb,"pred.bin"),(lb,"label_oldbasket.csv")]:
    j=o.merge(ref.rename(columns={ref.columns[-1]:"ref"})[["ts","ref"]] if len(ref.columns)==2 else ref,on="ts",how="inner")
    for tag in out:
        print("fold18 win 2025Q4 | %-34s vs %-20s n=%d corr=%.6f p50=%.6f"%(tag,name,len(j),np.corrcoef(j[tag],j.ref)[0,1],np.percentile(j[tag],50)))
    print("   ref p50=%.6f"%np.percentile(j.ref,50))
print("\ncorr(wfo_models/fold18, gate_ab_full/fold18) =",float(np.corrcoef(o['wfo_models/fold_18'],o['gate_ab_full/label_oldbasket/fold_18'])[0,1]))
