import numpy as np, pandas as pd, struct, os, onnxruntime as ort, glob

V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14",
"basketVolSpike"]

raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read()
n=struct.unpack(">i",raw[:4])[0]
arr=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
pb=pd.DataFrame({"ts":arr["ts"].astype(np.int64),"pb":arr["p15"].astype(np.float32)}).set_index("ts")
pb["year"]=pd.to_datetime(pb.index,unit="ms",utc=True).year

# folds: firstOos=20210401, step 3 months, end 20251231 (local +07 => ms utc)
folds=[]
y,m=2021,4
for k in range(21):
    c=pd.Timestamp(year=y,month=m,day=1,tz="Asia/Ho_Chi_Minh").value//10**6
    m2=m+3; y2=y+(m2-1)//12; m2=(m2-1)%12+1
    e=pd.Timestamp(year=y2,month=m2,day=1,tz="Asia/Ho_Chi_Minh").value//10**6
    folds.append((c,e)); y,m=y2,m2
END=pd.Timestamp(year=2026,month=1,day=1,tz="Asia/Ho_Chi_Minh").value//10**6

def run_store(name, path, modeldir, label):
    t=pd.read_csv(path, usecols=["timestamp"]+V3FULL)
    t=t[t.timestamp<END]
    t=t.set_index("timestamp")
    print(f"\n### STORE={name} rows={len(t)} ts {pd.to_datetime(t.index.min(),unit='ms')} -> {pd.to_datetime(t.index.max(),unit='ms')}")
    preds=[]
    for k,(c,e) in enumerate(folds):
        md=f"{modeldir}/{label}/fold_{k}" if label else f"{modeldir}/fold_{k}"
        if c>=END: break
        e=min(e,END)
        sub=t.loc[(t.index>=c)&(t.index<e)]
        if len(sub)==0: continue
        mp=f"{md}/Model_Regressor_Return15M.onnx"
        if not os.path.exists(mp): print("  missing model",mp); continue
        sess=ort.InferenceSession(mp,providers=["CPUExecutionProvider"])
        X=sub.values.astype(np.float32)
        p=sess.run(None,{sess.get_inputs()[0].name:X})[0].ravel()
        preds.append(pd.Series(p,index=sub.index))
    pr=pd.concat(preds)
    j=pb.join(pd.DataFrame({"re":pr}),how="inner")
    j["year"]=pb["year"]
    corr=float(np.corrcoef(j.pb,j.re)[0,1])
    per=j.groupby("year").apply(lambda g: float(np.corrcoef(g.pb,g.re)[0,1]),include_groups=False).round(4).to_dict()
    print(f"  joint={len(j)} corr={corr:.5f} meanratio={j.re.abs().sum()/j.pb.abs().sum():.3f}")
    print(f"  p50 pb={np.percentile(j.pb,50):.6f} re={np.percentile(j.re,50):.6f} | p99 pb={np.percentile(j.pb,99):.6f} re={np.percentile(j.re,99):.6f} | max pb={j.pb.max():.5f} re={j.re.max():.5f}")
    print("  per-year corr:",per)
    return dict(store=name,modeldir=modeldir,label=label,n=len(j),corr=corr,per=per)

res=[]
res.append(run_store("fs_full.csv","/home/ubuntu/claudedata/gate_ab_full/fs_full.csv","/home/ubuntu/claudedata/gate_ab_full/models","label_oldbasket"))
res.append(run_store("gate15m_v2_full.csv","/home/ubuntu/claudedata/gate15m_v2_full.csv","/home/ubuntu/claudedata/gate_ab_full/models","label_oldbasket"))
res.append(run_store("fs_full.csv","/home/ubuntu/claudedata/gate_ab_full/fs_full.csv","/home/ubuntu/claudedata/wfo_models",None))
res.append(run_store("gate15m_v2_full.csv","/home/ubuntu/claudedata/gate15m_v2_full.csv","/home/ubuntu/claudedata/wfo_models",None))
pd.DataFrame([{k:v for k,v in r.items() if k!='per'} for r in res]).to_csv("/tmp/pbrepro/step2.csv",index=False)
import json; json.dump(res,open("/tmp/pbrepro/step2.json","w"),indent=1)
print("\nDONE")
