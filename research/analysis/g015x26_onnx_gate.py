"""Export ONNX cho fold CUOI cua dai x26 (fold 15 = cutoff 20251001) + cong ONNX-vs-JSON
tren MAU THAT (300k dong feature OOS 2025Q4). Dung duong build memory-light (repro2)."""
import os, sys, hashlib, logging
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log=logging.getLogger("onnx")
sys.path.insert(0,"/home/ubuntu/sel1m_code")
from tool1_col import read_tool1
GRID_MS=15*60*1000; TZ=7*3600*1000; OI_TOL=2*3600*1000
OI_DT=np.dtype([("ts",">i8"),("sym",">i2"),("oi",">f4",5)])
OI_NAMES=["oi_delta24h","oi_z","ls_global","ls_toptrader","taker_buy"]
FIDX=15
c=int(pd.Timestamp("2025-10-01",tz="UTC").value//1_000_000)-TZ
cdt=pd.to_datetime(c+TZ,unit="ms").normalize()
lo_b=c; hi_b=int((cdt+pd.DateOffset(months=3)).value//1_000_000)-TZ
ao=np.memmap("/home/ubuntu/claudedata/oi/oi_percoin_full.bin",dtype=OI_DT,mode="r")
m=pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
a=read_tool1("/home/ubuntu/ds_feat15m/features_2025*",grid_ms=GRID_MS)
F=a["f"]
lo=int(pd.Timestamp("2025-01-01",tz="UTC").value//1_000_000); hi=int(pd.Timestamp("2026-01-01",tz="UTC").value//1_000_000)
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
tsv=mg["ts"].to_numpy(); sub=mg[(tsv>=lo_b)&(tsv<hi_b)]
rng=np.random.default_rng(20260906)
sel=rng.choice(len(sub),size=min(300000,len(sub)),replace=False)
sub=sub.iloc[np.sort(sel)]
X=np.empty((len(sub),45),dtype=np.float32)
X[:,:40]=F[sub["ridx"].to_numpy()]; X[:,40:]=sub[OI_NAMES].to_numpy(np.float32)
del a,F,mg
log.info("sample rows=%d",len(X))
import xgboost as xgb
clf=xgb.XGBClassifier(); clf.load_model("/home/ubuntu/claudedata/predwf_G015/model_f%d_4h.json"%FIDX)
p_json=clf.predict_proba(X)[:,1].astype(np.float64)
from onnxmltools.convert import convert_xgboost
from onnxmltools.convert.common.data_types import FloatTensorType
onx=convert_xgboost(clf,initial_types=[("input",FloatTensorType([None,45]))],target_opset=15)
out="/home/ubuntu/g3x26/g015x26_f15_cut20251001.onnx"
open(out,"wb").write(onx.SerializeToString())
log.info("ONNX -> %s (%d B)",out,os.path.getsize(out))
import onnxruntime as ort
sess=ort.InferenceSession(out,providers=["CPUExecutionProvider"])
iname=sess.get_inputs()[0].name
res=sess.run(None,{iname:X})
prob=res[1]
if isinstance(prob,list): p_onnx=np.array([r[1] for r in prob],dtype=np.float64)
else: p_onnx=np.asarray(prob)[:,1].astype(np.float64)
from scipy.stats import spearmanr
d=np.abs(p_json-p_onnx)
log.info("GATE ONNX-vs-JSON: n=%d max|d|=%.3e mean|d|=%.3e spearman=%.8f",
         len(d),float(d.max()),float(d.mean()),float(spearmanr(p_json,p_onnx).statistic))
log.info("sha256(onnx)=%s",hashlib.sha256(open(out,"rb").read()).hexdigest())
