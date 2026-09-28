import numpy as np, pandas as pd, onnxruntime as ort, struct, os
V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike"]
raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read(); n=struct.unpack(">i",raw[:4])[0]
a=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
pb=pd.DataFrame({"ts":a["ts"].astype(np.int64),"ref":a["p15"].astype(np.float64)}).set_index("ts")
C=int(pd.Timestamp(year=2025,month=10,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
E=int(pd.Timestamp(year=2026,month=1,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
t=pd.read_csv("/home/ubuntu/claudedata/gate_dataset_full.csv.gz",usecols=["timestamp"]+V3FULL)
sub=t[(t.timestamp>=C)&(t.timestamp<E)].set_index("timestamp")
ref=pb.loc[(pb.index>=C)&(pb.index<E),"ref"]
X=sub.values.astype(np.float32)
print("window 2025Q4 rows=%d"%len(sub))
for d,label in [("/home/ubuntu/claudedata/wfo_models",None),("/home/ubuntu/claudedata/gate_ab_full/models","label_oldbasket")]:
    print("== %s %s"%(d,label or ""))
    best=[]
    for k in range(21):
        mp=f"{d}/{label}/fold_{k}/Model_Regressor_Return15M.onnx" if label else f"{d}/fold_{k}/Model_Regressor_Return15M.onnx"
        if not os.path.exists(mp): continue
        s=ort.InferenceSession(mp,providers=["CPUExecutionProvider"])
        p=s.run(None,{s.get_inputs()[0].name:X})[0].ravel().astype(np.float64)
        c=float(np.corrcoef(p,ref.values)[0,1])
        best.append((k,c,float(np.percentile(p,50))))
    best.sort(key=lambda z:-z[1])
    print("  top5 by corr with pred.bin@2025Q4:",[(k,round(c,5),round(p50,6)) for k,c,p50 in best[:5]])
