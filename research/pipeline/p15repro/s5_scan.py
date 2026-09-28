import numpy as np, pandas as pd, onnxruntime as ort, struct, os
V3FULL = ["momentum1M","momentum5M","momentum15M","momentum1H","momentum4H","momentum24H","momentumAcceleration",
"trendStrengthETH","trendConsistency","volatility1M","volatility15M","volatility1H","volatility24H",
"volatilityTermStructure","advanceDeclineRatio","percentAboveMA20","volumeRatioUpDown","marketBreadthStrength",
"btcDominance","rsi14","volumeSpike","distMA20","fundingRateRaw","fundingRateAvg24H","fundingRateTrend",
"hourOfDay","dayOfWeek","weekOfMonth","monthOfYear","basketMomentum15M","basketMomentum1H","basketRsi14","basketVolSpike"]
raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read()
n=struct.unpack(">i",raw[:4])[0]
a=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
pb=pd.DataFrame({"ts":a["ts"].astype(np.int64),"pred.bin":a["p15"].astype(np.float64)})
csvs={
 "gate_ab_full/label_oldbasket":"/home/ubuntu/claudedata/gate_ab_full/wfo_gate_pred_label_oldbasket.csv",
 "gate_push_ds/wfo_gate_pred":"/home/ubuntu/claudedata/gate_push_ds/wfo_gate_pred.csv",
 "claudedata/wfo_gate_pred":"/home/ubuntu/claudedata/wfo_gate_pred.csv",
}
refs={k:pd.read_csv(v).rename(columns={"timestamp":"ts","predReturn15M":"ref"})[["ts","ref"]] for k,v in csvs.items()}
refs["pred.bin"]=pb.rename(columns={"pred.bin":"ref"})
print("loading store (feature only)...")
t=pd.read_csv("/home/ubuntu/claudedata/gate_dataset_full.csv.gz",usecols=["timestamp"]+V3FULL).set_index("timestamp")

# fold windows (local +07)
def tsx(y,m):
    return int(pd.Timestamp(year=y,month=m,day=1,tz="Asia/Ho_Chi_Minh").value//10**6)
wins={}
yy,mm=2021,4
for k in range(21):
    c=tsx(yy,mm); m2=mm+3; y2=yy+(m2-1)//12; m2=(m2-1)%12+1
    wins[k]=(c,tsx(y2,m2)); yy,mm=y2,m2

def rep(tag, mdir, fold, label=None):
    mp=f"{mdir}/{label}/fold_{fold}/Model_Regressor_Return15M.onnx" if label else f"{mdir}/fold_{fold}/Model_Regressor_Return15M.onnx"
    if not os.path.exists(mp): return None
    sess=ort.InferenceSession(mp,providers=["CPUExecutionProvider"])
    out={}
    for k in ([fold] if fold is not None else range(19)):
        c,e=wins[k]
        sub=t.loc[(t.index>=c)&(t.index<e)]
        if len(sub)==0: continue
        p=sess.run(None,{sess.get_inputs()[0].name:sub.values.astype(np.float32)})[0].ravel().astype(np.float64)
        out[k]=pd.DataFrame({"ts":sub.index.values,"m":p})
    return out

FOLD=18
for mdir,label in [("/home/ubuntu/claudedata/gate_ab_full/models","label_oldbasket"),
                   ("/home/ubuntu/claudedata/wfo_models",None),
                   ("/home/ubuntu/claudedata/gatemodels","label_oldbasket"),
                   ("/home/ubuntu/claudedata/gatemodels_v4v5","label_ret15m"),
                   ("/home/ubuntu/claudedata/gate_ab_full/models","label_ret15m")]:
    r=rep("x",mdir,FOLD,label)
    if r is None: print("MISS",mdir,label); continue
    o=r[FOLD]
    line=f"{mdir}/{label or ''} fold{FOLD}: n={len(o)} p50_model={np.percentile(o.m,50):.6f} | "
    for name,ref in refs.items():
        j=o.merge(ref,on="ts")
        if len(j)==0: line+="%s:no-join "%name; continue
        line+="%s corr=%.5f "%(name,np.corrcoef(j.m,j.ref)[0,1])
    print(line)
print("ref p50: pred.bin=%.6f  label_oldbasket.csv=%.6f"%(np.percentile(pb['pred.bin'],50),np.percentile(refs['gate_ab_full/label_oldbasket'].ref,50)))
