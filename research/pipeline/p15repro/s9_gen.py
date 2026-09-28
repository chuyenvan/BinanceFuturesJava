import numpy as np, pandas as pd, onnxruntime as ort, os
V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike"]
def win(y,m): return int(pd.Timestamp(year=y,month=m,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
C,E=win(2025,10),win(2026,1)
t=pd.read_csv("/home/ubuntu/claudedata/gate_dataset_full.csv.gz",usecols=["timestamp"]+V3FULL)
sub=t[(t.timestamp>=C)&(t.timestamp<E)].set_index("timestamp"); X=sub.values.astype(np.float32)
def pred(mp):
    s=ort.InferenceSession(mp,providers=["CPUExecutionProvider"])
    return pd.Series(s.run(None,{s.get_inputs()[0].name:X})[0].ravel().astype(np.float64),index=sub.index)

# (a) doi chieu voi ban .bak 11/07
bak=pd.read_csv("/home/ubuntu/claudedata/wfo_gate_pred.csv.bak_20260711_2333").rename(columns={"timestamp":"ts","predReturn15M":"bak"}).set_index("ts")
print("bak rows=%d range %s -> %s"%(len(bak),pd.to_datetime(bak.index.min(),unit="ms"),pd.to_datetime(bak.index.max(),unit="ms")))
p18=pred("/home/ubuntu/claudedata/wfo_models/fold_18/Model_Regressor_Return15M.onnx")
p20=pred("/home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx")
j=p18.to_frame("f18").join(bak,how="inner"); print("(a) fold18 vs .bak(Jul11) n=%d corr=%s"%(len(j),round(float(np.corrcoef(j.f18,j.bak)[0,1]),5) if len(j)>10 else "n/a"))
j=p20.to_frame("f20").join(bak,how="inner"); print("(a) fold20 vs .bak(Jul11) n=%d corr=%s"%(len(j),round(float(np.corrcoef(j.f20,j.bak)[0,1]),5) if len(j)>10 else "n/a"))

# (c) cap (gatemodels_v4v5, wfo_gate_pred_v4v5_label_*)
for L in ["ret15m","ret60m"]:
    mp=f"/home/ubuntu/claudedata/gatemodels_v4v5/label_{L}/fold_18/Model_Regressor_Return15M.onnx"
    cp=f"/home/ubuntu/claudedata/wfo_gate_pred_v4v5_label_{L}.csv"
    if not (os.path.exists(mp) and os.path.exists(cp)): print("MISS",L); continue
    c=pd.read_csv(cp).rename(columns={"timestamp":"ts","predReturn15M":"ref"}).set_index("ts")
    p=pred(mp); j=p.to_frame("m").join(c,how="inner")
    print("(c) gatemodels_v4v5 label_%s fold18 vs %s: n=%d corr=%.6f max|d|=%.3e"%(L,os.path.basename(cp),len(j),np.corrcoef(j.m,j.ref)[0,1],np.max(np.abs(j.m-j.ref))))
# (d) gate_ab_full models label_oldbasket fold_18 vs chinh file CSV cua run do (da lam: 0.68)
# (e) fresh model (khong co san) - ket qua o s6/s7
