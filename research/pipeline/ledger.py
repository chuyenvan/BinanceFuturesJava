"""S0 — CANDIDATE LEDGER (DEV 2022-01..2024-06) + EDGE SCORE (check nhanh selector, khong can sim).
Pool(tick) = moi coin co pred G015 tai tick 15m ma gate thi truong MO (predReturn15M >= 0.008 = nguong long nhat; sim thuc te siet them theo
symbolPred: dyn = MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN, symbolPred/RATE_MAX*AI_DYNAMIC_MULTIPLIER)
-- CHI CO CAN DUOI, KHONG CO TRAN; xem gate_cfg.py -> ghi lai de do confound).
Outcome: retEnd_72h, maxFav_72h, maxAdv_72h, g1lite = neu maxFav_72h>=0.05: maxFav_72h - min(0.5*maxFav_72h, 0.08) (trailing xap xi) else retEnd_72h.
edge(tick) = mean outcome(top-K theo score) - mean outcome(pool). San = 0 (random). Tran = top-K theo outcome that.
usage: ledger.py build | score <name>=<bins_dir> ..."""
import sys, os, glob, time, numpy as np, pandas as pd
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger(__name__)
sys.path.insert(0, "/home/ubuntu/featv2")
import gate_cfg
gate_cfg.describe()
sys.path.insert(0,"/home/ubuntu/sel1m_code"); from funding_label_pb import read_label
OUT="/home/ubuntu/ledger"; os.makedirs(OUT,exist_ok=True); Q=900000; H=3600000; TZ=7*H
T0=int(pd.Timestamp("2021-04-01").value//1e6)-TZ; T1=int(pd.Timestamp("2024-07-01").value//1e6)-TZ   # v2: tu 2021-04 de fold 0 co train
dt=np.dtype([("ts",">i8"),("sym",">i2"),("p0",">f4"),("p1",">f4"),("p2",">f4"),("p3",">f4")])
def log(*a): LOG.info(" ".join(str(x) for x in a))
def load_bins(d):
    fs=[f for f in sorted(glob.glob(f"{d}/predict_wf_*.bin")) if "2022" in f or "2023" in f or "20240101" in f or "20240401" in f]
    P=[]
    for f in fs:
        a=np.fromfile(f,dtype=dt); P.append(pd.DataFrame({"ts":a["ts"].astype(np.int64),"sym":a["sym"].astype(np.int64),"p":a["p0"].astype(np.float64)}))
    P=pd.concat(P); P=P[(P.ts>=T0)&(P.ts<T1)&(P.ts%Q==0)].drop_duplicates(["ts","sym"]); return P
if sys.argv[1]=="build":
    G=pd.read_csv("/home/ubuntu/claudedata/wfo_gate_pred.csv",usecols=["timestamp","predReturn15M"]).rename(columns={"timestamp":"ts","predReturn15M":"p15"})
    G=G[(G.ts%Q==0)&(G.ts>=T0)&(G.ts<T1)].drop_duplicates("ts"); open_ts=G[G.p15>=0.008]
    log("gate ticks 15m:",len(G),"mo (>=0.008):",len(open_ts),f"({len(open_ts)/len(G):.3f})")
    mp=pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); sym2id=dict(zip(mp.symbol,mp.symId))
    P=load_bins("/home/ubuntu/claudedata/predwf_G015x26").rename(columns={"p":"p_g015"}); log("G015 recs",len(P))
    parts=[]
    for f in sorted(glob.glob("/home/ubuntu/label_15m/funding_label_202[1-4]*.pb")):
        L=read_label(f,usecols=["tEpochMs","symbol","maxFav_72h","maxAdv_72h","retEnd_72h","nBars_72h"]); L=L[L.tEpochMs%Q==0]
        L=L[L.tEpochMs.isin(open_ts.ts.values)]; L["sym"]=L.symbol.map(sym2id); L=L.dropna(subset=["sym"]); L["sym"]=L.sym.astype(np.int64)
        parts.append(L.drop(columns=["symbol"]).rename(columns={"tEpochMs":"ts"}))
    Lb=pd.concat(parts); Lb=Lb[Lb.nBars_72h>=288]; log("label rows",len(Lb))
    # v2: pool = coin co LABEL tai tick gate mo (moi nam, ke ca 2021 khong co G015); left-merge p_g015 (NaN o 2021)
    D=Lb.merge(open_ts,on="ts",how="inner").merge(P,on=["ts","sym"],how="left"); log("ledger",D.shape,"co p_g015:",D.p_g015.notna().mean().round(3),"ticks",D.ts.nunique())
    D["g1lite"]=np.where(D.maxFav_72h>=0.05, D.maxFav_72h-np.minimum(0.5*D.maxFav_72h,0.08), D.retEnd_72h)
    # symbolPred G015 trong sim = 1 - p? KHONG: bins slot0 = P(win) -> sim score = 1-p. dyn gate theo score.
    D["score_g015"]=1-D.p_g015; D["dyn_thr"]=gate_cfg.dyn_thr(D.score_g015); D["gate_dyn_ok"]=D.p15>=D.dyn_thr
    D.to_parquet(f"{OUT}/cand_dev.parquet"); log("saved", f"{OUT}/cand_dev.parquet", "gate_dyn_ok share:", D.gate_dyn_ok.mean().round(3))
    LOG.info("coins/tick: %s",D.groupby("ts").sym.count().describe()[["min","50%","max"]].to_dict())
else:
    D=pd.read_parquet(f"{OUT}/cand_dev.parquet"); D["yr"]=pd.to_datetime(D.ts,unit="ms").dt.year
    D=D[D.retEnd_72h.notna()]
    def edge_table(S,name):
        # S: DataFrame ts,sym,score (thap=tot). Merge vao pool; top-K theo score trong pool.
        M=D.merge(S,on=["ts","sym"],how="left")
        rows=[]
        for K in (5,8):
            for outc in ("retEnd_72h","g1lite","maxFav_72h"):
                pool=M.groupby("ts")[outc].mean()
                Ms=M.dropna(subset=["score"]); Ms=Ms.assign(rk=Ms.groupby("ts").score.rank(method="first"))
                top=Ms[Ms.rk<=K].groupby("ts")[outc].mean(); orc=M.assign(rk=M.groupby("ts")[outc].rank(ascending=False,method="first")); orc=orc[orc.rk<=K].groupby("ts")[outc].mean()
                e=(top-pool).dropna(); c=(orc-pool).dropna(); yr=pd.to_datetime(e.index,unit="ms").year
                r={"model":name,"K":K,"outcome":outc,"edge_all%":100*e.mean(),"t":e.mean()/e.std()*np.sqrt(len(e)),"ceiling%":100*c.mean(),"share":e.mean()/c.mean()}
                for y in (2022,2023,2024): r[f"e{y}%"]=100*e[yr==y].mean()
                r["ticks"]=len(e); r["topK_score_mean"]=Ms[Ms.rk<=K].score.mean(); r["topK_gate_dyn_ok"]=Ms[Ms.rk<=K].assign(ok=lambda x: x.p15>=gate_cfg.dyn_thr(x.score)).ok.mean()
                rows.append(r)
        return pd.DataFrame(rows)
    res=[]
    for arg in sys.argv[2:]:
        name,d=arg.split("="); P=load_bins(d); S=P.assign(score=1-P.p)[["ts","sym","score"]]; res.append(edge_table(S,name)); log(name,"done")
    rng=np.random.default_rng(0); S=D[["ts","sym"]].assign(score=rng.random(len(D))); res.append(edge_table(S,"random"))
    R=pd.concat(res); pd.set_option("display.width",250); LOG.info("\n%s", R.round(3).to_string(index=False)); R.to_csv(f"{OUT}/edge_scores.csv",index=False)
