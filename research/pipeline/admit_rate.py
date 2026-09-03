"""DINH CHINH: "gate mo X%" truoc day do bang NGUONG CO DINH 0.008 — nhung sim thuc te dung NGUONG DONG:
   dyn_thr = MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN, score/RATE_MAX*AI_DYNAMIC_MULTIPLIER),
   score = 1 - P(win). CHI CO CAN DUOI -- ban cu ghi clamp co tran 2.14135 la SAI (dinh chinh 2026-09-03).
Tinh TY LE VAO THAT SU (admission) theo quy: %% cap (tick,coin) co p15 >= dyn_thr, va rieng cho TOP-8 theo score.
Neu admission cua TOP-8 troi manh -> gate that su mat loc; neu on dinh -> ket luan drift cua toi phai sua."""
import numpy as np, pandas as pd, glob, os, sys
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger(__name__)
sys.path.insert(0, "/home/ubuntu/featv2")
import gate_cfg
gate_cfg.describe()
SEAL=1767225600000; Q=900000
G=pd.read_csv("/home/ubuntu/claudedata/wfo_gate_pred.csv",usecols=["timestamp","predReturn15M"]).rename(columns={"timestamp":"ts","predReturn15M":"p15"})
G=G[(G.ts%Q==0)&(G.ts<SEAL)].drop_duplicates("ts")
dt=np.dtype([("ts",">i8"),("sym",">i2"),("p0",">f4"),("p1",">f4"),("p2",">f4"),("p3",">f4")])
out=[]
for f in sorted(glob.glob("/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin")):
    a=np.fromfile(f,dtype=dt)
    D=pd.DataFrame({"ts":a["ts"].astype(np.int64),"sym":a["sym"].astype(np.int64),"score":1-a["p0"].astype(np.float64)})
    D=D[D.ts<SEAL].merge(G,on="ts",how="inner")
    if not len(D): continue
    D["dyn"]=gate_cfg.dyn_thr(D.score)
    D["ok"]=D.p15>=D.dyn
    D["r"]=D.groupby("ts").score.rank(method="first")
    t8=D[D.r<=8]
    out.append({"fold":os.path.basename(f)[11:19],"rows":len(D),"coin/tick":round(len(D)/D.ts.nunique(),0),
        "dyn_thr_p50%":round(100*D.dyn.median(),3),"p15_p50%":round(100*D.p15.median(),3),
        "admit_all%":round(100*D.ok.mean(),2),"admit_top8%":round(100*t8.ok.mean(),2),
        "tick co >=1 admit%":round(100*D.groupby("ts").ok.any().mean(),1),
        "tick co >=1 top8 admit%":round(100*t8.groupby("ts").ok.any().mean(),1)})
R=pd.DataFrame(out); pd.set_option("display.width",250); LOG.info("\n%s", R.to_string(index=False))
d=R[R.fold<"20240701"]; v=R[R.fold>="20240701"]
LOG.info("DEV admit_top8%% TB %.2f | VAL %.2f | tick co top8 admit: DEV %.1f%% VAL %.1f%%",
             d["admit_top8%"].mean(), v["admit_top8%"].mean(),
             d["tick co >=1 top8 admit%"].mean(), v["tick co >=1 top8 admit%"].mean())
