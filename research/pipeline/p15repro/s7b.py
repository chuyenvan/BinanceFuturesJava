import numpy as np, pandas as pd, struct, xgboost as xgb, json, os, time
from scipy.stats import spearmanr
V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike"]
raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read(); n=struct.unpack(">i",raw[:4])[0]
arr=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
pb=pd.DataFrame({"ts":arr["ts"].astype(np.int64),"ref":arr["p15"].astype(np.float64)})
t=pd.read_csv("/home/ubuntu/claudedata/gate_dataset_full.csv.gz",usecols=["timestamp"]+V3FULL+["label_oldbasket"])
END=int(pd.Timestamp(year=2026,month=1,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
def tsx(y,m): return int(pd.Timestamp(year=y,month=m,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
PARAMS=dict(objective="reg:squarederror",max_depth=4,n_estimators=150,learning_rate=0.05,subsample=0.8,
            colsample_bytree=0.8,min_child_weight=10,random_state=42,n_jobs=2)
yy,mm=2021,4; folds=[]
for k in range(21):
    c=tsx(yy,mm); m2=mm+3; y2=yy+(m2-1)//12; m2=(m2-1)%12+1; e=tsx(y2,m2); yy,mm=y2,m2
    folds.append((k,c,min(e,END)))
rows=[]; parts=[]
for k,c,e in folds:
    if c>=END: break
    if k<8:
        continue
    st=time.time()
    tr=t[t.timestamp<c-15*60_000]; oo=t[(t.timestamp>=c)&(t.timestamp<e)]
    m=xgb.XGBRegressor(**PARAMS); m.fit(tr[V3FULL].values.astype(np.float32),tr.label_oldbasket.values.astype(np.float32))
    p=m.predict(oo[V3FULL].values.astype(np.float32)).astype(np.float64)
    pr=pd.DataFrame({"ts":oo.timestamp.values,"fresh":p}); parts.append(pr)
    j=pr.merge(pb,on="ts")
    rows.append(dict(fold=k,win=pd.to_datetime(c,unit="ms").date().isoformat(),n=len(j),
        pearson=round(float(np.corrcoef(j.fresh,j.ref)[0,1]),5),
        spearman=round(float(spearmanr(j.fresh,j.ref).correlation),6),
        p50_ref=round(float(np.percentile(j.ref,50)),6),p50_new=round(float(np.percentile(j.fresh,50)),6),
        p99_ref=round(float(np.percentile(j.ref,99)),6),p99_new=round(float(np.percentile(j.fresh,99)),6),
        max_ref=round(float(j.ref.max()),5),max_new=round(float(j.fresh.max()),5)))
    print("fold %2d %s n=%d pearson=%.5f spearman=%.6f p50 %.6f/%.6f max %.4f/%.4f (%.0fs)"%(k,rows[-1]["win"],len(j),rows[-1]["pearson"],rows[-1]["spearman"],rows[-1]["p50_ref"],rows[-1]["p50_new"],rows[-1]["max_ref"],rows[-1]["max_new"],time.time()-st),flush=True)
pd.DataFrame(rows).to_csv("/tmp/pbrepro/step7b_folds8_18.csv",index=False)
s=pd.concat(parts).set_index("ts")
j=pb.set_index("ts").join(s,how="inner"); j["year"]=pd.to_datetime(j.index,unit="ms",utc=True).year
per={}
for y,g in j.groupby("year"):
    per[int(y)]=dict(n=len(g),pearson=round(float(np.corrcoef(g.fresh,g.ref)[0,1]),5),
      spearman=round(float(pd.Series(g.fresh).corr(pd.Series(g.ref),method="spearman")),6),
      p50_ref=round(float(np.percentile(g.ref,50)),6),p50_new=round(float(np.percentile(g.fresh,50)),6),
      p99_ref=round(float(np.percentile(g.ref,99)),6),p99_new=round(float(np.percentile(g.fresh,99)),6),
      max_ref=round(float(g.ref.max()),5),max_new=round(float(g.fresh.max()),5))
print("PER-YEAR(folds8-18):",json.dumps(per,indent=1)); json.dump(per,open("/tmp/pbrepro/step7b_peryear.json","w"),indent=1)
print("DONE_B")
