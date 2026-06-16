# TASK-025: ghép gate dataset (label 012 + A 015 + B-now 017 + B-crowd 018) theo tEpochMs + validate.
# Chạy trên 226: cd /home/chuyennd/java/simulator && python3 merge_gate_dataset.py
import pandas as pd, numpy as np, hashlib, itertools
OUT="/home/chuyennd/java/simulator/outputs"
label=pd.read_csv(f"{OUT}/gate_return.csv")
A=pd.read_csv(f"{OUT}/gate_features_groupA.csv")
now=pd.read_csv(f"{OUT}/gate_features_groupB_now.csv")
crowd=pd.read_csv(f"{OUT}/gate_features_groupB_crowd.csv")
for df in (A,now,crowd):
    if "tDate" in df.columns: df.drop(columns=["tDate"],inplace=True)
allc={}
for nm_,df in [("A",A),("now",now),("crowd",crowd)]:
    for c in df.columns:
        if c=="tEpochMs": continue
        allc.setdefault(c,[]).append(nm_)
dup=[c for c,v in allc.items() if len(v)>1]
print("=== ten cot trung giua nhom (canh bao) ===", dup if dup else "khong")
m=label.merge(A,on="tEpochMs",how="left").merge(now,on="tEpochMs",how="left").merge(crowd,on="tEpochMs",how="left")
m=m.sort_values("tEpochMs").reset_index(drop=True)
label_cols=["ret_4h","ret_12h","ret_24h","n_4h","n_12h","n_24h"]
feat=[c for c in m.columns if c not in (["tEpochMs","tDate"]+label_cols)]
print("=== shape ===", m.shape, "| rows(label)=",len(label),"| #feature=",len(feat))
print("=== range tEpochMs ===", int(m.tEpochMs.min()), int(m.tEpochMs.max()))
na=m[feat].isna().sum(); na=na[na>0].sort_values(ascending=False)
print("=== cot co NaN (top15) ===\n"+na.head(15).to_string() if len(na) else "=== khong cot nao NaN ===")
const=[c for c in feat if m[c].nunique(dropna=True)<=1]
print("=== SCREEN cot hang-so/toan-NaN ===", const if const else "khong")
num=m[feat].select_dtypes(include=[np.number])
corr=num.corr().abs()
hi=[(a,b,round(corr.loc[a,b],3)) for a,b in itertools.combinations(corr.columns,2) if corr.loc[a,b]>0.95]
print(f"=== cap feature |corr|>0.95 (TRUNG): {len(hi)} ===")
for a,b,c in sorted(hi,key=lambda x:-x[2])[:15]: print(f"  {a} ~ {b}: {c}")
cl=num.corrwith(m["ret_24h"]).abs().sort_values(ascending=False)
print("=== |corr| feature vs ret_24h (top10, leak-sanity) ===\n"+cl.head(10).to_string())
m2=m.copy(); m2["year"]=pd.to_datetime(m2.tEpochMs,unit="ms").dt.year
print("=== b6_oiMarketTotal NaN/nam ===\n"+m2.groupby("year")["b6_oiMarketTotal"].apply(lambda s:f"{int(s.isna().sum())}/{len(s)}").to_string())
outf=f"{OUT}/gate_dataset_v1.csv"
m.to_csv(outf,index=False)
h=hashlib.md5(open(outf,"rb").read()).hexdigest()
print("=== WROTE ===",outf,"shape",m.shape,"md5",h)
