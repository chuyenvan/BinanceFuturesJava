import numpy as np, pandas as pd, struct, os, gzip, onnxruntime as ort
from scipy.stats import spearmanr

V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike"]

raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read()
n=struct.unpack(">i",raw[:4])[0]
arr=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
pb=pd.DataFrame({"ts":arr["ts"].astype(np.int64),"pb":arr["p15"].astype(np.float64)})
print("pred.bin n=%d" % n)

TZ="Asia/Ho_Chi_Minh"
def tsx(y,m,d=1):
    return pd.Timestamp(year=y,month=m,day=d,tz=TZ).value//10**6
folds=[]
y,m=2021,4
for k in range(21):
    c=tsx(y,m); m2=m+3; y2=y+(m2-1)//12; m2=(m2-1)%12+1
    e=tsx(y2,m2); folds.append((c,e,k)); y,m=y2,m2
END=tsx(2026,1)

print("loading gate_dataset_full.csv.gz ...")
t=pd.read_csv("/home/ubuntu/claudedata/gate_dataset_full.csv.gz",usecols=["timestamp"]+V3FULL)
t=t[t.timestamp<END]
print("store rows(DEV)=",len(t),"ts",pd.to_datetime(t.timestamp.min(),unit="ms"),"->",pd.to_datetime(t.timestamp.max(),unit="ms"))
t=t.set_index("timestamp")

rows=[]
for c,e,k in folds:
    if c>=END: break
    e=min(e,END)
    sub=t.loc[(t.index>=c)&(t.index<e)]
    if len(sub)==0: continue
    mp=f"/home/ubuntu/claudedata/wfo_models/fold_{k}/Model_Regressor_Return15M.onnx"
    sess=ort.InferenceSession(mp,providers=["CPUExecutionProvider"])
    p=sess.run(None,{sess.get_inputs()[0].name:sub.values.astype(np.float32)})[0].ravel().astype(np.float64)
    pr=pd.DataFrame({"ts":sub.index.values,"re":p})
    j=pb.merge(pr,on="ts")
    rho=spearmanr(j.pb,j.re).correlation
    maxd=float(np.max(np.abs(j.pb-j.re)))
    rows.append(dict(fold=k,win=str(pd.to_datetime(c,unit="ms").date()),n=len(j),spearman=round(rho,6),
                     pearson=round(float(np.corrcoef(j.pb,j.re)[0,1]),6),maxabsd=maxd))
    print(f"  fold {k:2d} [{pd.to_datetime(c,unit='ms').date()}..{pd.to_datetime(e,unit='ms').date()}) n={len(j)} spearman={rho:.6f} max|d|={maxd:.3e}")
df=pd.DataFrame(rows)
df.to_csv("/tmp/pbrepro/step3_perfold.csv",index=False)
print("ALL: mean spearman=%.6f min=%.6f  n_fold_pass(>=0.999)=%d/%d"%(df.spearman.mean(),df.spearman.min(),(df.spearman>=0.999).sum(),len(df)))
j2=pb.merge(t.reset_index().rename(columns={"timestamp":"ts"}),on="ts")
print("j2 rows",len(j2))
# per-year of the assembled repro
allp=[]
for c,e,k in folds:
    if c>=END: break
    e=min(e,END)
    sub=t.loc[(t.index>=c)&(t.index<e)]
    if len(sub)==0: continue
    sess=ort.InferenceSession(f"/home/ubuntu/claudedata/wfo_models/fold_{k}/Model_Regressor_Return15M.onnx",providers=["CPUExecutionProvider"])
    p=sess.run(None,{sess.get_inputs()[0].name:sub.values.astype(np.float32)})[0].ravel()
    allp.append(pd.Series(p,index=sub.index))
s=pd.concat(allp)
j=pb.set_index("ts").join(pd.DataFrame({"re":s}),how="inner")
j["year"]=pd.to_datetime(j.index,unit="ms",utc=True).year
print("assembled: n=%d corr=%.5f ratio=%.3f"%(len(j),np.corrcoef(j.pb,j.re)[0,1],j.re.abs().sum()/j.pb.abs().sum()))
print("per-year pearson:",j.groupby("year").apply(lambda g:float(np.corrcoef(g.pb,g.re)[0,1]),include_groups=False).round(4).to_dict())
print("p50 pb=%.6f re=%.6f | p99 pb=%.6f re=%.6f | max pb=%.5f re=%.5f"%(np.percentile(j.pb,50),np.percentile(j.re,50),np.percentile(j.pb,99),np.percentile(j.re,99),j.pb.max(),j.re.max()))
