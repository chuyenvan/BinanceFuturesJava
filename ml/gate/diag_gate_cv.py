#!/usr/bin/env python3
"""TASK-041 H2 chan-doan: purged time-series CV (5 fold) tren toan giai doan co OI,
de biet gate co suc phan biet on dinh khong (OOS 1 nam cuoi qua it su kien -> nhieu).
Moi fold: test = 1 doan lien tuc, train = phan con lai voi embargo H hai ben.
Metric = precision/recall/lift lop SAP o top-1% va top-5%.
"""
import os, glob
import numpy as np, pandas as pd, xgboost as xgb

DATA = os.environ.get("DATA", "/d/claudedata/gate_dataset_v1.csv")
X_CRASH, Y_UP, EMB = -0.15, 0.09, 96
df = pd.read_csv(sorted(glob.glob(DATA, recursive=True))[0]).sort_values("tEpochMs").reset_index(drop=True)
df = df[(df.tEpochMs >= pd.Timestamp("2021-12-01").value//10**6) & df.ret_24h.notna()].reset_index(drop=True)
df["y"] = df.ret_24h.apply(lambda r: 0 if r<=X_CRASH else (2 if r>=Y_UP else 1))
DROP = ["tEpochMs","tDate","ret_4h","ret_12h","ret_24h","n_4h","n_12h","n_24h","y"]
FEATS = [c for c in df.columns if c not in DROP]
N = len(df); folds = 5; sz = N//folds
print(f"N={N} | SAP toan bo={ (df.y==0).sum()} ({(df.y==0).mean()*100:.2f}%) | {folds} fold purged CV (embargo {EMB})")

agg = {1:[],5:[]}
for k in range(folds):
    lo, hi = k*sz, (N if k==folds-1 else (k+1)*sz)
    test_idx = np.arange(lo, hi)
    mask = np.ones(N, bool); mask[max(0,lo-EMB):min(N,hi+EMB)] = False
    tr_idx = np.where(mask)[0]
    ytr = df.y.values[tr_idx]; yte = df.y.values[test_idx]
    if (yte==0).sum() < 5: 
        print(f"fold{k}: test SAP={(yte==0).sum()} <5, bo qua"); continue
    n=len(ytr); cw={c:n/(3*max(1,(ytr==c).sum())) for c in [0,1,2]}
    w=np.array([cw[c] for c in ytr])
    dtr=xgb.DMatrix(df[FEATS].values[tr_idx],label=ytr,weight=w,feature_names=FEATS,missing=np.nan)
    dte=xgb.DMatrix(df[FEATS].values[test_idx],label=yte,feature_names=FEATS,missing=np.nan)
    bst=xgb.train(dict(objective="multi:softprob",num_class=3,max_depth=4,eta=0.03,
        subsample=0.8,colsample_bytree=0.8,min_child_weight=5,eval_metric="mlogloss",seed=42),
        dtr,num_boost_round=250,verbose_eval=False)
    pc=bst.predict(dte)[:,0]; yb=(yte==0).astype(int); base=yb.mean()
    line=f"fold{k} [{pd.to_datetime(df.tEpochMs.values[lo],unit='ms').date()}..{pd.to_datetime(df.tEpochMs.values[hi-1],unit='ms').date()}] base={base*100:.2f}% nSAP={yb.sum()}"
    for tp in [1,5]:
        sel=pc>=np.percentile(pc,100-tp)
        prec=yb[sel].mean() if sel.sum() else 0; lift=prec/base if base>0 else 0
        agg[tp].append(lift); line+=f" | top{tp}%: prec={prec:.3f} lift={lift:.2f}x"
    print(line)
print(f"\n=== lift trung binh qua fold ===")
for tp in [1,5]:
    a=agg[tp]; print(f"top{tp}%: lift median={np.median(a):.2f}x mean={np.mean(a):.2f}x (cac fold: {[round(x,1) for x in a]})")
