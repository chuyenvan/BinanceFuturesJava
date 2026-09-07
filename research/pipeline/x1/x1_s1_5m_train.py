"""BUOC B -- train THAT S1 tren luoi 5 PHUT (cand_dev_x1_5m.parquet), luu MOI fold model,
ghi pred_s1a2x1_5m.parquet (dinh dang giong x1_s1_rank.py) de dua vao x1_build_map.py.
Copy nguyen tham so tu x1_s1_rank.py / x1_s1_save_all_folds.py (da PASS Buoc A CPU 16/16),
CHI doi nguon ledger (cand_dev_x1 -> cand_dev_x1_5m). Khong co baseline de doi chieu (day
la thi nghiem MOI), nen chi train + luu + predict, khong verify."""
import logging as _logging, sys as _sys
_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
LOG = _logging.getLogger(__name__)
def _p(*a): LOG.info(" ".join(str(x) for x in a))
import os, json, time
import numpy as np, pandas as pd, xgboost as xgb
def log(*a): _p(time.strftime("%H:%M:%S"), *a)

H=3600000; TZ=7*H; PURGE=72*H; LED="/home/ubuntu/ledger"
KEEP=["vol_7d","dd_7d","rk_dd_7d","hrs_since_high_7d","ret_3d","rk_ret_3d","ret_14d","ls_global","rk_oi_delta24h"]
LNAME="cand_dev_x1_5m"; FEAT="/home/ubuntu/featv2/feat_v2_x1.parquet"
OUT="/home/ubuntu/s1_model_5m"; os.makedirs(OUT, exist_ok=True)

D=pd.read_parquet(f"{LED}/{LNAME}.parquet"); D=D[D.g1lite.notna()].copy(); log("pool", D.shape)
D["med"]=D.groupby("ts").g1lite.transform("median"); D["rel"]=D.g1lite-D.med
D["rk"]=D.groupby("ts").rel.rank(pct=True,method="first"); D["rel5"]=np.minimum((D.rk*5).astype(int),4)
D["ts_h"]=(D.ts//H)*H
F=pd.read_parquet(FEAT, columns=["ts","sym"]+KEEP)
D=D.merge(F.rename(columns={"ts":"ts_h"}),on=["ts_h","sym"],how="left")
log("join feat: co vol_7d", D.vol_7d.notna().mean().round(3))

cut_days=["20220101","20220401","20220701","20221001","20230101","20230401","20230701","20231001",
          "20240101","20240401","20240701","20241001","20250101","20250401","20250701","20251001"]
cut=[int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value//1e6)-TZ for c in cut_days]

preds=[]; results=[]
for i,c in enumerate(cut):
    hi=int((pd.Timestamp(c+TZ,unit="ms")+pd.DateOffset(months=3)).value//1e6)-TZ
    tr=D[D.ts<c-PURGE].sort_values("ts"); oos=D[(D.ts>=c)&(D.ts<hi)].sort_values("ts")
    if len(tr)<5000 or len(oos)==0:
        log("fold",i,cut_days[i],"skip"); continue
    assert tr.ts.max()<c, "LEAK"
    m=xgb.XGBRanker(objective="rank:ndcg",n_estimators=300,max_depth=4,learning_rate=0.05,
                     subsample=0.8,colsample_bytree=0.8,min_child_weight=50,n_jobs=4,
                     tree_method="hist",random_state=42,lambdarank_pair_method="topk",
                     lambdarank_num_pair_per_sample=8)
    t0=time.time()
    m.fit(tr[KEEP], tr.rel5, qid=pd.factorize(tr.ts,sort=True)[0])
    fit_s = time.time()-t0
    tag=f"s1a2x1_5m_cut{cut_days[i]}"; jpath=f"{OUT}/{tag}.json"
    m.get_booster().save_model(jpath)
    p = m.predict(oos[KEEP])
    o = oos[["ts","sym"]].assign(score=-p)
    preds.append(o)
    log(f"fold {i} {cut_days[i]}: fit {fit_s:.0f}s train {len(tr)} oos {len(oos)} ticks {oos.ts.nunique()}")
    results.append({"fold":cut_days[i],"n_tr":len(tr),"n_oos":len(oos),"fit_s":fit_s})

P=pd.concat(preds)
P[["ts","sym","score"]].to_parquet(f"{LED}/pred_s1a2x1_5m.parquet")
json.dump(results, open(f"{OUT}/allfold_manifest_5m.json","w"), indent=1)
log(f"=== DONE {len(results)} fold, saved pred_s1a2x1_5m.parquet, models in {OUT} ===")
print("S1_5M_TRAIN_DONE")
