# TASK-026: train gate 3-class (DOWN/FLAT/UP theo ret_24h +/-3%).
# Purged walk-forward K-fold + embargo 24h, class-weight balanced, giu NaN (XGBoost xu),
# bo cap trung b6_oiPriceDiverge. Beat-rule baseline (always-FLAT + rule don gian).
# Chay 226: cd /home/chuyennd/java/simulator && python3 train_gate_xgboost.py
import pandas as pd, numpy as np, xgboost as xgb
from sklearn.metrics import f1_score, classification_report, confusion_matrix
from collections import Counter

CSV="/home/chuyennd/java/simulator/outputs/gate_dataset_v1.csv"
UP_THR=0.03; DN_THR=-0.03
EMBARGO_MS=24*3600*1000   # = horizon ret_24h, chong leak train/val
N_FOLD=5

df=pd.read_csv(CSV).sort_values("tEpochMs").reset_index(drop=True)
df=df[~df["ret_24h"].isna()].reset_index(drop=True)
r=df["ret_24h"].values
y=np.where(r>=UP_THR,2,np.where(r<=DN_THR,0,1)).astype(int)   # 0=DOWN 1=FLAT 2=UP
label_cols=["ret_4h","ret_12h","ret_24h","n_4h","n_12h","n_24h"]
drop=set(label_cols+["tEpochMs","tDate","b6_oiPriceDiverge"])
feat=[c for c in df.columns if c not in drop]
X=df[feat].astype(float).values
ts=df["tEpochMs"].values
print(f"rows={len(df)} feat={len(feat)} class_dist(DOWN,FLAT,UP)={np.bincount(y).tolist()}")
print("features:", feat)

def purged_folds(ts,n):
    idx=np.arange(len(ts)); b=np.linspace(0,len(ts),n+1).astype(int)
    for k in range(1,n):
        va_s,va_e=b[k],b[k+1]; va_start_ts=ts[va_s]
        tr=idx[:va_s]; tr=tr[ts[tr] < va_start_ts-EMBARGO_MS]
        yield idx[tr] if False else tr, idx[va_s:va_e]

def sw(yy):
    c=Counter(yy); n=len(yy); k=len(c)
    w={cl:n/(k*cnt) for cl,cnt in c.items()}
    return np.array([w[v] for v in yy])

params=dict(objective="multi:softprob",num_class=3,max_depth=5,eta=0.05,
            subsample=0.8,colsample_bytree=0.8,eval_metric="mlogloss",nthread=4,seed=42)
f1s=[]
for fold,(tr,va) in enumerate(purged_folds(ts,N_FOLD)):
    if len(tr)<2000 or len(va)<500: 
        print(f"--- fold {fold}: skip (train={len(tr)} val={len(va)})"); continue
    dtr=xgb.DMatrix(X[tr],label=y[tr],weight=sw(y[tr]),missing=np.nan)
    dva=xgb.DMatrix(X[va],label=y[va],missing=np.nan)
    bst=xgb.train(params,dtr,num_boost_round=400,evals=[(dva,"va")],
                  early_stopping_rounds=30,verbose_eval=False)
    pred=bst.predict(dva).argmax(1)
    f1=f1_score(y[va],pred,average="macro"); f1s.append(f1)
    print(f"--- fold {fold}: train={len(tr)} val={len(va)} best_iter={bst.best_iteration} macroF1={f1:.4f}")
    print(classification_report(y[va],pred,target_names=["DOWN","FLAT","UP"],digits=3,zero_division=0))
    print("confusion(row=true DOWN/FLAT/UP):\n",confusion_matrix(y[va],pred))
print(f"=== CV macro-F1 mean={np.mean(f1s):.4f} std={np.std(f1s):.4f} (folds={len(f1s)}) ===")

# BASELINE 1: luon FLAT
base=np.full(len(y),1)
print(f"=== baseline always-FLAT: macroF1={f1_score(y,base,average='macro'):.4f} acc={(base==y).mean():.3f} ===")
# BASELINE 2 (beat-rule): rule don gian tu feature san co
#   UP neu tren MA200 (b3_distMA200>0) & momentum24H>0 ; DOWN neu duoi MA200 & momentum24H<0 ; else FLAT
if "b3_distMA200" in df.columns and "momentum24H" in df.columns:
    d2=df["b3_distMA200"].values; m24=df["momentum24H"].values
    rule=np.where((d2>0)&(m24>0),2,np.where((d2<0)&(m24<0),0,1))
    msk=~(np.isnan(d2)|np.isnan(m24))
    print(f"=== baseline RULE (MA200&mom24h): macroF1={f1_score(y[msk],rule[msk],average='macro'):.4f} (n={msk.sum()}) ===")
