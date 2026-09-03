"""S1 — LambdaRank tren POOL ledger (pre-reg trong PROCESS_LOG). Output: /home/ubuntu/ledger/pred_s1{a,b}.parquet (ts,sym,score thap=tot) + edge table.
S1a: 9 feat V3. S1b: 9 feat + p_g015. Label relevance = quintile trong tick cua rel = g1lite - median(pool)."""

# --- LUAT LOG CUA REPO: dung module `logging`, KHONG dung ham in san co.
#     Ghi ra STDOUT (khong phai stderr) de giu nguyen hanh vi cac script goi,
#     vi du: `python3 build_map.py s1a2 $P | tail -2`.
#     format="%(message)s" => output giong ban da chay sinh ra bins (xem BINS_MANIFEST.md).
import logging as _logging
import sys as _sys
_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
LOG = _logging.getLogger(__name__)


def _p(*a):
    """Gop cac doi so bang dau cach roi day qua logging (thay cho ham in san co)."""
    LOG.info(" ".join(str(x) for x in a))

import sys, time, numpy as np, pandas as pd, xgboost as xgb
from scipy.stats import spearmanr
def log(*a): _p(time.strftime("%H:%M:%S"),*a)
H=3600000; TZ=7*H; PURGE=72*H; LED="/home/ubuntu/ledger"
KEEP=["vol_7d","dd_7d","rk_dd_7d","hrs_since_high_7d","ret_3d","rk_ret_3d","ret_14d","ls_global","rk_oi_delta24h"]
D=pd.read_parquet(f"{LED}/cand_dev.parquet"); D=D[D.g1lite.notna()].copy(); _p("ledger nam:",D.assign(y=pd.to_datetime(D.ts,unit="ms").dt.year).y.value_counts().sort_index().to_dict()); log("pool",D.shape)
D["med"]=D.groupby("ts").g1lite.transform("median"); D["rel"]=D.g1lite-D.med
D["rk"]=D.groupby("ts").rel.rank(pct=True,method="first"); D["rel5"]=np.minimum((D.rk*5).astype(int),4)
D["ts_h"]=(D.ts//H)*H
F=pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet"); feats_all=[c for c in F.columns if c not in ("ts","sym")]
D=D.merge(F.rename(columns={"ts":"ts_h"}),on=["ts_h","sym"],how="left"); log("join feat: co vol_7d",D.vol_7d.notna().mean().round(3))
D["yr"]=pd.to_datetime(D.ts,unit="ms").dt.year
# chan doan rank-IC 37 feat vs rel tren pool theo nam (chi ghi)
rows=[]
for f in feats_all:
    r={"feat":f}
    for y,g in D.groupby("yr"):
        ok=g[f].notna(); r[y]=round(spearmanr(g.loc[ok,f],g.loc[ok,"rel"]).correlation,4) if ok.sum()>1000 else np.nan
    rows.append(r)
IC=pd.DataFrame(rows).set_index("feat"); IC["mean"]=IC.mean(1); IC["consistent"]=(np.sign(IC[[2022,2023,2024]]).nunique(1)==1)
_p("\n== rank-IC feat vs rel (pool) theo nam ==\n",IC.sort_values("mean",key=abs,ascending=False).round(4).to_string()); IC.to_csv(f"{LED}/pool_rankic.csv")
cut_days=["20220101","20220401","20220701","20221001","20230101","20230401","20230701","20231001","20240101","20240401"]
cut=[int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value//1e6)-TZ for c in cut_days]
def run(name,FE):
    preds=[]; edges=[]
    for i,c in enumerate(cut):
        lo,hi=c,int((pd.Timestamp(c+TZ,unit="ms")+pd.DateOffset(months=3)).value//1e6)-TZ
        tr=D[D.ts<c-PURGE].sort_values("ts"); oos=D[(D.ts>=lo)&(D.ts<hi)].sort_values("ts")
        if len(tr)<5000 or len(oos)==0: log(name,"fold",i,"skip"); continue
        assert tr.ts.max()<c, "LEAK"
        m=xgb.XGBRanker(objective="rank:ndcg",n_estimators=300,max_depth=4,learning_rate=0.05,subsample=0.8,colsample_bytree=0.8,min_child_weight=50,n_jobs=4,tree_method="hist",random_state=42,lambdarank_pair_method="topk",lambdarank_num_pair_per_sample=8)
        m.fit(tr[FE],tr.rel5,qid=pd.factorize(tr.ts,sort=True)[0])
        p=m.predict(oos[FE]); o=oos[["ts","sym","g1lite","yr"]].assign(score=-p)
        if i in (0,5,9):
            ysh=tr.groupby("ts").rel5.transform(lambda s: s.sample(frac=1,random_state=1).values); m2=xgb.XGBRanker(objective="rank:ndcg",n_estimators=100,max_depth=4,n_jobs=4,tree_method="hist",random_state=42,lambdarank_pair_method="topk",lambdarank_num_pair_per_sample=8); m2.fit(tr[FE],ysh,qid=pd.factorize(tr.ts,sort=True)[0])
            osh=oos[["ts","g1lite"]].assign(score=-m2.predict(oos[FE])); osh["rk"]=osh.groupby("ts").score.rank(method="first"); esh=(osh[osh.rk<=5].groupby("ts").g1lite.mean()-osh.groupby("ts").g1lite.mean()).mean()
        else: esh=np.nan
        o["rk"]=o.groupby("ts").score.rank(method="first"); e=(o[o.rk<=5].groupby("ts").g1lite.mean()-o.groupby("ts").g1lite.mean())
        log(f"{name} fold {i} {cut_days[i]}: train {len(tr)} oos {len(oos)} ticks {oos.ts.nunique()} edge5 {100*e.mean():+.2f}% shuffle {100*esh if esh==esh else float('nan'):+.2f}%")
        preds.append(o.drop(columns=["rk"])); edges.append(e)
    P=pd.concat(preds); P[["ts","sym","score"]].to_parquet(f"{LED}/pred_{name}.parquet")
    E=pd.concat(edges); yr=pd.to_datetime(E.index,unit="ms").year
    _p(f"\n=== {name}: edge5 g1lite OOS all {100*E.mean():+.2f}% t={E.mean()/E.std()*np.sqrt(len(E)):.1f} | 2022 {100*E[yr==2022].mean():+.2f} 2023 {100*E[yr==2023].mean():+.2f} 2024 {100*E[yr==2024].mean():+.2f} | ticks {len(E)} (G015 +4.55, nguong +6.0 & duong 3 nam & t>=10)")
    imp=pd.Series(m.feature_importances_,index=FE).sort_values(ascending=False); _p(imp.round(3).to_string())
SUF=sys.argv[1] if len(sys.argv)>1 else ""; run("s1a"+SUF,KEEP)
log("DONE")
