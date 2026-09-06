import numpy as np, hashlib, os
from scipy.stats import spearmanr
CUTS=["20220101","20220401","20220701","20221001","20230101","20230401","20230701","20231001",
      "20240101","20240401","20240701","20241001","20250101","20250401","20250701","20251001"]
def load(p):
    a=np.fromfile(p,dtype=np.uint8); n=len(a)//26; a=a[:n*26].reshape(n,26)
    ts=np.frombuffer(a[:,0:8].tobytes(),dtype=">i8").astype(np.int64)
    sym=np.frombuffer(a[:,8:10].tobytes(),dtype=">i2").astype(np.int64)
    p0=np.frombuffer(a[:,10:14].tobytes(),dtype=">f4").astype(np.float64)
    return ts,sym,p0
print("%-10s %10s %10s %6s %12s %12s %10s"%("cutoff","n_orig","n_regen","keys","spearman","max|d|","sha_eq"))
rows=[]
for c in CUTS:
    po="/home/ubuntu/claudedata/predwf_G015x26/predict_wf_%s.bin"%c
    pr="/home/ubuntu/g3x26/regen/predict_wf_%s.bin"%c
    if not os.path.exists(pr): print("%-10s MISSING"%c); continue
    t1,s1,p1=load(po); t2,s2,p2=load(pr)
    k1=t1*100000+(s1+1); k2=t2*100000+(s2+1)
    o1=np.argsort(k1,kind="stable"); o2=np.argsort(k2,kind="stable")
    keq=np.array_equal(k1[o1],k2[o2])
    a=p1[o1]; b=p2[o2]; m=np.isfinite(a)&np.isfinite(b)
    d=np.abs(a[m]-b[m]); mx=float(d.max()) if m.any() else float("nan")
    idx=np.random.default_rng(0).choice(np.flatnonzero(m),size=min(400000,int(m.sum())),replace=False)
    sp=float(spearmanr(a[idx],b[idx]).statistic)
    shq=hashlib.sha256(open(po,"rb").read()).hexdigest()==hashlib.sha256(open(pr,"rb").read()).hexdigest()
    print("%-10s %10d %10d %6s %12.8f %12.3e %10s"%(c,len(t1),len(t2),keq,sp,mx,shq))
    rows.append((c,len(t1),len(t2),keq,sp,mx))
if rows:
    print("SUMMARY: folds=%d keys_all_equal=%s min_spearman=%.8f max_of_max|d|=%.3e"%(
        len(rows),all(r[3] for r in rows),min(r[4] for r in rows),max(r[5] for r in rows)))
