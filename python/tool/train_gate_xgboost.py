# TASK-026 Kaggle: gate 3-class. SO SANH nhan ±3% co dinh vs ±k·σ adaptive (no-leak).
# Moi nhan: purged walk-forward 5-fold + embargo 24h, regime moi fold, lift decile, importance.
import pandas as pd, numpy as np, xgboost as xgb, glob
from sklearn.metrics import f1_score
from collections import Counter
print("INPUTS:", glob.glob("/kaggle/input/*"))
_c=glob.glob("/kaggle/input/**/gate_dataset_v1.csv", recursive=True)
assert _c, "khong thay gate_dataset_v1.csv"
df=pd.read_csv(_c[0]).sort_values("tEpochMs").reset_index(drop=True)
df=df[~df["ret_24h"].isna()].reset_index(drop=True)
r=df["ret_24h"].values; ts=df["tEpochMs"].values
dt=pd.to_datetime(ts,unit="ms")
label_cols=["ret_4h","ret_12h","ret_24h","n_4h","n_12h","n_24h"]
drop=set(label_cols+["tEpochMs","tDate","b6_oiPriceDiverge"])
feat=[c for c in df.columns if c not in drop]
X=df[feat].astype(float).values
EMBARGO_MS=24*3600*1000; N_FOLD=5

# --- nhan 1: co dinh ±3% ---
yf=np.where(r>=0.03,2,np.where(r<=-0.03,0,1)).astype(int)
# --- nhan 2: adaptive ±k·σ, σ = rolling std backward 30 ngay (2880 moc 15m), shift 24h (96 moc) de no-leak ---
K=0.7
sigma=pd.Series(r).rolling(2880,min_periods=500).std().shift(96).values
ya=np.where(r>=K*sigma,2,np.where(r<=-K*sigma,0,1)).astype(int)
mask_a=~np.isnan(sigma)

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

def run(y, idx, tag):
    print(f"\n################## {tag} ##################")
    yy=y[idx]; XX=X[idx]; tss=ts[idx]; rr=r[idx]; dd=dt[idx]
    print(f"n={len(yy)} class_dist(DOWN,FLAT,UP)={np.bincount(yy,minlength=3).tolist()} "
          f"({np.bincount(yy,minlength=3)/len(yy)})")
    f1s=[]; oof_va=[]; oof_p=[]; bst=None
    for fold,(tr,va) in enumerate(folds(tss,N_FOLD)):
        if len(tr)<2000 or len(va)<500: print(f"fold{fold}: skip"); continue
        dtr=xgb.DMatrix(XX[tr],label=yy[tr],weight=sw(yy[tr]),missing=np.nan)
        dva=xgb.DMatrix(XX[va],label=yy[va],missing=np.nan)
        bst=xgb.train(params,dtr,num_boost_round=400,evals=[(dva,"va")],early_stopping_rounds=30,verbose_eval=False)
        proba=bst.predict(dva); pred=proba.argmax(1); f1=f1_score(yy[va],pred,average="macro"); f1s.append(f1)
        flat=(yy[va]==1).mean()
        print(f"  fold{fold}: {dd.iloc[va].min().date()}..{dd.iloc[va].max().date()} "
              f"FLAT={flat:.2f} std={rr[va].std():.4f} macroF1={f1:.4f}")
        oof_va.append(va); oof_p.append(proba)
    print(f"  >>> CV macro-F1 mean={np.mean(f1s):.4f} std={np.std(f1s):.4f}")
    base=np.full(len(yy),1); print(f"  baseline always-FLAT macroF1={f1_score(yy,base,average='macro'):.4f}")
    # lift
    va=np.concatenate(oof_va); P=np.concatenate(oof_p,axis=0)
    oy=yy[va]; oret=rr[va]; pup=P[:,2]; pdn=P[:,0]
    def dec(score,name):
        d=pd.DataFrame({"s":score,"ret":oret,"y":oy}); d["dec"]=pd.qcut(d["s"].rank(method="first"),10,labels=False)
        g=d.groupby("dec").agg(ret_mean=("ret","mean"),UP=("y",lambda s:(s==2).mean()),DOWN=("y",lambda s:(s==0).mean()))
        print(f"  -- lift decile theo {name} (dec0=thap..dec9=model tu tin) --")
        print("   dec9(tu tin):",g.loc[9].round(4).to_dict()," | dec0:",g.loc[0].round(4).to_dict())
    dec(pup,"P_up"); dec(pdn,"P_down")
    if bst is not None:
        imp=sorted(bst.get_score(importance_type="gain").items(),key=lambda x:-x[1])[:10]
        print("  top10 feature gain:", [(feat[int(k[1:])] if k[1:].isdigit() and int(k[1:])<len(feat) else k, round(v,1)) for k,v in imp])
    return np.mean(f1s)

mf=run(yf, np.arange(len(df)), "FIXED ±3%")
ma=run(ya, np.where(mask_a)[0], "ADAPT ±0.7σ (rolling 30d backward, shift 24h)")
print(f"\n=== SO SANH CV macro-F1: FIXED={mf:.4f} vs ADAPT={ma:.4f} ===")
