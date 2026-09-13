"""PREREG_DYN_COLLAPSE (commit 8b9078b): path feature tai t=entry+D du bao collapse som?
So (A) price-path / (B) oi-funding-path / (C) full. Walk-forward AUC, purge 72h, H0 x10. CHI DO."""
import logging, numpy as np, pandas as pd, xgboost as xgb
from sklearn.metrics import roc_auc_score
logging.basicConfig(level=logging.INFO, format="%(message)s"); L=logging.getLogger("dyn")
TZ="Asia/Ho_Chi_Minh"; H=3600000
LED="/home/ubuntu/java/devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv"
CLO="/home/ubuntu/java/fsrun/CLOSES_1H.bin"
FEATV2="/home/ubuntu/featv2/feat_v2_x1.parquet"
MAP="/home/ubuntu/selector_pred_out/symbol_map.csv"
d=pd.read_csv(LED, usecols=lambda c: c and not c.startswith("Unnamed"))
d["ts"]=pd.to_datetime(d.start,format="%Y%m%d %H:%M").dt.tz_localize(TZ)
d["te"]=pd.to_datetime(d.end,format="%Y%m%d %H:%M").dt.tz_localize(TZ)
d["ts_ms"]=d.ts.astype("int64")//10**6; d["te_ms"]=d.te.astype("int64")//10**6
d=d[(d.level=="PREDICT_SYMBOL_TRADE") & (d.ts.dt.year<=2025)].copy()
d["entry_h"]=(d.ts_ms//H)*H
mp=pd.read_csv(MAP); s2id=dict(zip(mp.symbol,mp.symId))
d["symId"]=(d.sym+"USDT").map(s2id)
d=d[d.symId.notna()].copy(); d["symId"]=d.symId.astype(int)
d["collapse_final"]=((d.status=="STOP_LOSS_DONE") & (d.profit<=-20)).astype(int)
L.info("PST<=2025: n=%d all-BUY=%s collapse_total=%d", len(d), (d.side=="BUY").all(), d.collapse_final.sum())
# --- CLOSES_1H: per-symId sorted (ts,close) for path min/max/last ---
DT=np.dtype([("ts",">i8"),("sym",">i2"),("c",">f4")]); C=np.fromfile(CLO,dtype=DT)
cts=C["ts"].astype(np.int64); csym=C["sym"].astype(np.int64); cc=C["c"].astype(np.float64)
o=np.lexsort((cts,csym)); cts=cts[o]; csym=csym[o]; cc=cc[o]
uniq,start=np.unique(csym,return_index=True); end=np.append(start[1:],len(csym))
SIDX={int(s):(cts[a:b],cc[a:b]) for s,a,b in zip(uniq,start,end)}
def path_stats(sid,eh,t):
    a=SIDX.get(sid)
    if a is None: return (np.nan,)*4
    ts,c=a; lo=np.searchsorted(ts,eh); hi=np.searchsorted(ts,t,side="right")
    seg=c[lo:hi]
    if len(seg)==0: return (np.nan,)*4
    ct=c[hi-1] if hi>0 and ts[hi-1]==t else np.nan
    cprev=c[hi-2] if hi-2>=0 else np.nan
    return (float(seg.min()), float(seg.max()), float(ct), float(cprev))
# --- featv2 lookup keyed by ts*1e5+sym ---
FCOL=["oi_z","oi_delta24h","oi_delta_3d","ls_global","ls_toptrader","taker_buy",
      "fund_last","fund_sum_3d","fund_z_30d","fund_trend","vol_7d","dd_7d"]
Fv=pd.read_parquet(FEATV2, columns=["ts","sym"]+FCOL)
Fv["k"]=Fv["ts"].astype(np.int64)*100000+Fv["sym"].astype(np.int64)
Fv=Fv.drop_duplicates("k").set_index("k")
def fv_rows(ts_ms_arr, sid_arr):
    k=ts_ms_arr.astype(np.int64)*100000+sid_arr.astype(np.int64)
    return Fv.reindex(k)[FCOL].reset_index(drop=True)
PRICE=["ur_at_t","dd_since_entry","max_fav","dd_vel","ret_last_bar"]
OIF=["oi_z_t","oi_delta24h_t","oi_delta_3d_t","ls_global_t","ls_toptrader_t","taker_buy_t",
     "fund_last_t","fund_sum_3d_t","fund_z_30d_t","fund_trend_t",
     "d_oi_z","d_ls_global","d_ls_toptrader","d_fund_sum_3d","fund_flip"]
def build(D):
    g=d[d.te_ms > (d.entry_h + D*H)].copy().reset_index(drop=True)
    t=(g.entry_h + D*H).values
    ps=np.array([path_stats(int(s),int(eh),int(tt)) for s,eh,tt in zip(g.symId.values,g.entry_h.values,t)])
    mn,mx,ct,cprev=ps[:,0],ps[:,1],ps[:,2],ps[:,3]; ep=g.entry.values.astype(float)
    g["ur_at_t"]=ct/ep-1; g["dd_since_entry"]=mn/ep-1; g["max_fav"]=mx/ep-1
    g["dd_vel"]=g["dd_since_entry"]/D; g["ret_last_bar"]=ct/cprev-1
    ft=fv_rows(t.astype(np.int64), g.symId.values)
    fe=fv_rows(g.entry_h.values.astype(np.int64), g.symId.values)
    for c in ["oi_z","oi_delta24h","oi_delta_3d","ls_global","ls_toptrader","taker_buy",
              "fund_last","fund_sum_3d","fund_z_30d","fund_trend"]:
        g[c+"_t"]=ft[c].values
    g["d_oi_z"]=ft["oi_z"].values-fe["oi_z"].values
    g["d_ls_global"]=ft["ls_global"].values-fe["ls_global"].values
    g["d_ls_toptrader"]=ft["ls_toptrader"].values-fe["ls_toptrader"].values
    g["d_fund_sum_3d"]=ft["fund_sum_3d"].values-fe["fund_sum_3d"].values
    g["fund_flip"]=(np.sign(ft["fund_last"].values)!=np.sign(fe["fund_last"].values)).astype(float)
    g["yr"]=g.ts.dt.year; g["y"]=g["collapse_final"]
    return g
CUTS=[int(pd.Timestamp(f"{s[:4]}-{s[4:6]}-{s[6:]}",tz=TZ).value//10**6) for s in
      "20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001".split()]
def mk(): return xgb.XGBClassifier(n_estimators=200,max_depth=3,learning_rate=0.05,subsample=0.8,
    colsample_bytree=0.8,min_child_weight=20,random_state=42,n_jobs=4,verbosity=0)
def auc(y,p):
    ok=p.notna(); return roc_auc_score(y[ok],p[ok]) if ok.sum()>20 and y[ok].nunique()==2 else np.nan
def wf(g,cols,seed=None):
    X=g[cols].astype(float); y=g["y"]; pred=pd.Series(np.nan,index=g.index)
    rng=np.random.default_rng(seed) if seed is not None else None
    for c in CUTS:
        hi=int((pd.Timestamp(c,unit="ms",tz="UTC")+pd.DateOffset(months=3)).value//10**6)
        tr=g.index[g.te_ms < c-72*H]; te=g.index[(g.ts_ms>=c)&(g.ts_ms<hi)]
        if len(tr)<120 or len(te)==0 or y[tr].sum()<8: continue
        ytr=y[tr].values.copy()
        if rng is not None: rng.shuffle(ytr)
        m=mk(); m.fit(X.loc[tr,cols],ytr); pred[te]=m.predict_proba(X.loc[te,cols])[:,1]
    return pred
def run(g,D):
    L.info("\n===== D=%dh  n_open=%d  collapse=%d (%.1f%%) =====",D,len(g),g.y.sum(),100*g.y.mean())
    res={}
    for nm,cols in [("A price-path",PRICE),("B oi-funding",OIF),("C full",PRICE+OIF)]:
        a=auc(g.y,wf(g,cols)); res[nm[0]]=a
        L.info("  %-14s AUC=%.3f (n_feat=%d, oos=%d)",nm,a,len(cols),wf(g,cols).notna().sum())
    nulls=[auc(g.y,wf(g,PRICE+OIF,seed=s)) for s in range(10)]
    L.info("  H0(C) mean=%.3f sd=%.3f max=%.3f",np.nanmean(nulls),np.nanstd(nulls),np.nanmax(nulls))
    L.info("  single-feat AUC OI/funding:")
    for f in OIF:
        v=g[f]; ok=v.notna()
        if ok.sum()>30 and g.y[ok].nunique()==2:
            a=roc_auc_score(g.y[ok],v[ok]); L.info("    %-16s %.3f (%s)",f,max(a,1-a),"+" if a>=.5 else "-")
    return res,np.nanmean(nulls),np.nanstd(nulls)
ALL={}
for D in (4,12,24):
    g=build(D)
    nn=g[PRICE+OIF].isna().sum().sum(); L.info("D=%dh total NaN cells in feats=%d",D,nn)
    ALL[D]=run(g,D)
L.info("\n===== SUMMARY =====")
for D in (4,12,24):
    r,nm,ns=ALL[D]; green=(r["C"]>=0.65) and (r["C"]-r["A"]>=0.03) and (r["C"]>nm+3*ns)
    L.info("D=%2dh A=%.3f B=%.3f C=%.3f  C-A=%+.3f  H0=%.3f+-%.3f  => %s",
        D,r["A"],r["B"],r["C"],r["C"]-r["A"],nm,ns,"GREEN" if green else "DONG")
