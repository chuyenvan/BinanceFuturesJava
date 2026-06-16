# TASK-026 Kaggle: gate 3-class. SO SANH HORIZON 4h/12h/24h (deu nhan adaptive ±0.7σ, no-leak).
# Muc dich: chan doan feature co luc o horizon nao; 24h kho (xa), 4h de hon nhung ngan so DCA.
import pandas as pd, numpy as np, xgboost as xgb, glob
from sklearn.metrics import f1_score
from collections import Counter
print("INPUTS:", glob.glob("/kaggle/input/*"))
_c=glob.glob("/kaggle/input/**/gate_dataset_v1.csv", recursive=True)
assert _c, "khong thay gate_dataset_v1.csv"
df=pd.read_csv(_c[0]).sort_values("tEpochMs").reset_index(drop=True)
ts=df["tEpochMs"].values; dt=pd.to_datetime(ts,unit="ms")
label_cols=["ret_4h","ret_12h","ret_24h","n_4h","n_12h","n_24h"]
drop=set(label_cols+["tEpochMs","tDate","b6_oiPriceDiverge"])
feat=[c for c in df.columns if c not in drop]
X=df[feat].astype(float).values
EMBARGO_MS=24*3600*1000; N_FOLD=5; K=0.7
params=dict(objective="multi:softprob",num_class=3,max_depth=5,eta=0.05,subsample=0.8,
            colsample_bytree=0.8,eval_metric="mlogloss",nthread=4,seed=42)
def sw(yy):
    c=Counter(yy); n=len(yy); k=len(c); w={cl:n/(k*v) for cl,v in c.items()}
    return np.array([w[v] for v in yy])
def folds(tss,n):
    idx=np.arange(len(tss)); b=np.linspace(0,len(tss),n+1).astype(int)
    for kk in range(1,n):
        va_s,va_e=b[kk],b[kk+1]; t0=tss[va_s]
        tr=idx[:va_s]; tr=tr[tss[tr]<t0-EMBARGO_MS]
        yield tr, idx[va_s:va_e]

def run(rcol, shiftn):
    print(f"\n################## {rcol} (adaptive ±{K}σ, shift {shiftn} moc) ##################")
    rr=df[rcol].values
    sigma=pd.Series(rr).rolling(2880,min_periods=500).std().shift(shiftn).values
    y=np.where(rr>=K*sigma,2,np.where(rr<=-K*sigma,0,1)).astype(int)
    idx=np.where(~np.isnan(sigma)&~np.isnan(rr))[0]
    yy=y[idx]; XX=X[idx]; tss=ts[idx]; rv=rr[idx]; dd=dt[idx]
    print(f"n={len(yy)} dist(DOWN,FLAT,UP)={(np.bincount(yy,minlength=3)/len(yy)).round(3).tolist()}")
    f1s=[]; oof_va=[]; oof_p=[]; bst=None
    for fold,(tr,va) in enumerate(folds(tss,N_FOLD)):
        if len(tr)<2000 or len(va)<500: continue
        dtr=xgb.DMatrix(XX[tr],label=yy[tr],weight=sw(yy[tr]),missing=np.nan)
        dva=xgb.DMatrix(XX[va],label=yy[va],missing=np.nan)
        bst=xgb.train(params,dtr,num_boost_round=400,evals=[(dva,"va")],early_stopping_rounds=30,verbose_eval=False)
        proba=bst.predict(dva); f1=f1_score(yy[va],proba.argmax(1),average="macro"); f1s.append(f1)
        oof_va.append(va); oof_p.append(proba)
    print(f"  CV macro-F1={np.mean(f1s):.4f} (std {np.std(f1s):.4f}) | baseline-FLAT={f1_score(yy,np.full(len(yy),1),average='macro'):.4f}")
    va=np.concatenate(oof_va); P=np.concatenate(oof_p,axis=0); oy=yy[va]; oret=rv[va]; pup=P[:,2]; pdn=P[:,0]
    for score,nm in [(pup,"P_up"),(pdn,"P_down")]:
        d=pd.DataFrame({"s":score,"ret":oret,"y":oy}); d["dec"]=pd.qcut(d["s"].rank(method="first"),10,labels=False)
        g=d.groupby("dec").agg(ret=("ret","mean"),UP=("y",lambda s:(s==2).mean()),DOWN=("y",lambda s:(s==0).mean()))
        sp=g.loc[9,"ret"]-g.loc[0,"ret"]
        print(f"  {nm}: dec9{g.loc[9].round(4).to_dict()} dec0{g.loc[0].round(4).to_dict()} | spread_ret(dec9-dec0)={sp:.4f}")
    if bst is not None:
        imp=sorted(bst.get_score(importance_type="gain").items(),key=lambda x:-x[1])[:8]
        print("  top8 gain:", [(feat[int(k[1:])] if k[1:].isdigit() and int(k[1:])<len(feat) else k, round(v,1)) for k,v in imp])

run("ret_4h", 16)
run("ret_12h", 48)
run("ret_24h", 96)
