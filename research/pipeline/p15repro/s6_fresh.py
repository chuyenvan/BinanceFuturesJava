import numpy as np, pandas as pd, onnxruntime as ort, struct, xgboost as xgb
V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike"]
raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read(); n=struct.unpack(">i",raw[:4])[0]
arr=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
pb=pd.DataFrame({"ts":arr["ts"].astype(np.int64),"ref":arr["p15"].astype(np.float64)})
t=pd.read_csv("/home/ubuntu/claudedata/gate_dataset_full.csv.gz",usecols=["timestamp"]+V3FULL+["label_oldbasket"])
CUT=int(pd.Timestamp(year=2025,month=10,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
OOSE=int(pd.Timestamp(year=2026,month=1,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
tr=t[t.timestamp<CUT-15*60_000]
oo=t[(t.timestamp>=CUT)&(t.timestamp<OOSE)].reset_index(drop=True)
print("train rows=%d oos rows=%d"%(len(tr),len(oo)))
PARAMS=dict(objective="reg:squarederror",max_depth=4,n_estimators=150,learning_rate=0.05,subsample=0.8,
            colsample_bytree=0.8,min_child_weight=10,random_state=42,n_jobs=4)
m=xgb.XGBRegressor(**PARAMS); m.fit(tr[V3FULL].values.astype(np.float32),tr.label_oldbasket.values.astype(np.float32))
pf=m.predict(oo[V3FULL].values.astype(np.float32)).astype(np.float64)
j=pd.DataFrame({"ts":oo.timestamp.values,"fresh":pf}).merge(pb,on="ts")
print("FRESH(xgb native) vs pred.bin : n=%d pearson=%.6f spearman=%.6f p50=%.6f (ref p50=%.6f)"%(
  len(j),np.corrcoef(j.fresh,j.ref)[0,1],pd.Series(j.fresh).corr(pd.Series(j.ref),method="spearman"),np.percentile(j.fresh,50),np.percentile(j.ref,50)))
for tag,mp in [("ONNX wfo_models/fold_18","/home/ubuntu/claudedata/wfo_models/fold_18/Model_Regressor_Return15M.onnx"),
               ("ONNX gate_ab_full/label_oldbasket/fold_18","/home/ubuntu/claudedata/gate_ab_full/models/label_oldbasket/fold_18/Model_Regressor_Return15M.onnx")]:
    s=ort.InferenceSession(mp,providers=["CPUExecutionProvider"])
    po=s.run(None,{s.get_inputs()[0].name:oo[V3FULL].values.astype(np.float32)})[0].ravel().astype(np.float64)
    k=pd.DataFrame({"ts":oo.timestamp.values,"onnx":po}).merge(pb,on="ts")
    print("%s: vs pred.bin pearson=%.6f | vs FRESH xgb pearson=%.6f max|d|=%.3e | p50=%.6f"%(
      tag,np.corrcoef(k.onnx,k.ref)[0,1],np.corrcoef(k.onnx,k.fresh)[0,1],np.max(np.abs(k.onnx-k.fresh)),np.percentile(k.onnx,50)))
