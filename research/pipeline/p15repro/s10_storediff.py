import numpy as np, pandas as pd, onnxruntime as ort
V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike"]
def w(y,m): return int(pd.Timestamp(year=y,month=m,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
C,E=w(2025,10),w(2026,1)
print("== A. so 33 feature giua cac store (cung ts, cua so 2025Q4) ==")
base=None
for name,p in [("gate_dataset_full.csv.gz","/home/ubuntu/claudedata/gate_dataset_full.csv.gz"),
               ("gate_ab_full/fs_full.csv","/home/ubuntu/claudedata/gate_ab_full/fs_full.csv"),
               ("gate15m_v2_full.csv","/home/ubuntu/claudedata/gate15m_v2_full.csv"),
               ("gate_ab_full2/fs_full2.csv","/home/ubuntu/claudedata/gate_ab_full2/fs_full2.csv")]:
    d=pd.read_csv(p,usecols=["timestamp"]+V3FULL)
    d=d[(d.timestamp>=C)&(d.timestamp<E)].set_index("timestamp").astype(np.float64)
    if base is None: base=d; print("  [ref] %s rows=%d"%(name,len(d)))
    else:
        j=base.join(d,lsuffix="_a",rsuffix="_b",how="inner")
        md=max(float((j[f+"_a"]-j[f+"_b"]).abs().max()) for f in V3FULL)
        print("  %s rows=%d joint=%d max|dF| tren 33 feature = %.3e"%(name,len(d),len(j),md))
# B: on-disk ONNX vs fresh tren tung store
print("\n== B. corr(fold18 ONNX, pred.bin) va corr(fold18 ONNX, fresh) theo store ==")
import struct
raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read(); n=struct.unpack(">i",raw[:4])[0]
a=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
pb=pd.DataFrame({"ts":a["ts"].astype(np.int64),"ref":a["p15"].astype(np.float64)}).set_index("ts")
ref=pb.loc[(pb.index>=C)&(pb.index<E),"ref"]
s=ort.InferenceSession("/home/ubuntu/claudedata/wfo_models/fold_18/Model_Regressor_Return15M.onnx",providers=["CPUExecutionProvider"])
for name,p in [("gate_dataset_full.csv.gz","/home/ubuntu/claudedata/gate_dataset_full.csv.gz"),
               ("gate_ab_full/fs_full.csv","/home/ubuntu/claudedata/gate_ab_full/fs_full.csv"),
               ("gate_ab_full2/fs_full2.csv","/home/ubuntu/claudedata/gate_ab_full2/fs_full2.csv")]:
    d=pd.read_csv(p,usecols=["timestamp"]+V3FULL); d=d[(d.timestamp>=C)&(d.timestamp<E)].set_index("timestamp")
    pr=pd.Series(s.run(None,{s.get_inputs()[0].name:d.values.astype(np.float32)})[0].ravel().astype(np.float64),index=d.index)
    j=pd.DataFrame({"m":pr}).join(ref)
    print("  %-26s n=%d corr(ONNX,pred.bin)=%.5f"%(name,len(j),np.corrcoef(j.m,j.ref)[0,1]))
