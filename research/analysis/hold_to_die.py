"""HOLD-TO-DIE: lenh bi time-stop 168h cua X1_C3 (48 thang) — neu KHONG cat ma giu tiep thi sao?
Do tu CLOSES_1H.bin (hourly close): % ve breakeven, % cham +7% (arm), MDD tiep sau khi cat, delist.
Gioi han: hourly close (khong bat duoc intraday); khong tinh funding/phi; chi la counterfactual gia."""
import logging, sys, numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout); L=logging.getLogger()
H=3600000
PD="/home/ubuntu/java/devrun/X1_C3/storage/printDone.csv"
d=pd.read_csv(PD,on_bad_lines="skip")
for c in ["entry","profit","margin","pnl"]: d[c]=pd.to_numeric(d[c],errors="coerce")
d["ts"]=pd.to_datetime(d["start"],format="%Y%m%d %H:%M")-pd.Timedelta(hours=7)
d["tend"]=pd.to_datetime(d["end"].astype(str).str.replace("'",""),format="%Y%m%d %H:%M",errors="coerce")-pd.Timedelta(hours=7)
sl=d[d.status=="STOP_LOSS_DONE"].copy(); L.info("time-stop losers: %d / %d (%.1f%%)  meanP %.2f  p10 %.2f  min %.2f",len(sl),len(d),100*len(sl)/len(d),sl.profit.mean(),sl.profit.quantile(.1),sl.profit.min())
# symbol map
sm=None
m=pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); m.columns=[c.lower() for c in m.columns]
mp=dict(zip(m["symbol"].astype(str).str.replace("USDT$","",regex=True),m["symid"].astype(int)))
hit=sl.sym.astype(str).isin(mp).mean(); L.info("map khop %.1f%%",100*hit)
if hit>0.9: sm=mp
if sm is None: L.info("KHONG co symbol map khop"); sys.exit(1)
DT=np.dtype([("ts",">i8"),("sym",">i2"),("c",">f4")]); a=np.fromfile("/home/ubuntu/java/fsrun/CLOSES_1H.bin",dtype=DT)
P=pd.DataFrame({"ts":a["ts"].astype(np.int64),"sym":a["sym"].astype(np.int32),"c":a["c"].astype(np.float64)}); del a
last=P.groupby("sym").ts.max(); TEND=P.ts.max()
sl["sid"]=sl.sym.astype(str).map(sm)
rows=[]
for _,r in sl.iterrows():
    s=P[P.sym==r.sid].set_index("ts").c.sort_index()
    t0=int(r.tend.value//1e6)
    fut=s[s.index>t0]
    rec={"sym":r.sym,"profit":r.profit,"entry":r.entry,"delist_gap_d":(TEND-last.get(r.sid,TEND))/H/24}
    for D in [14,30,60,90,180]:
        w=fut[fut.index<=t0+D*24*H]
        if len(w)==0: rec[f"be{D}"]=np.nan; rec[f"arm{D}"]=np.nan; rec[f"mdd{D}"]=np.nan; continue
        rec[f"be{D}"]=float((w.max()>=r.entry)); rec[f"arm{D}"]=float((w.max()>=r.entry*1.07)); rec[f"mdd{D}"]=100*(w.min()/r.entry-1)
    rows.append(rec)
X=pd.DataFrame(rows)
L.info("\n=== NEU GIU TIEP sau khi bi time-stop (n=%d, hourly close):",len(X))
L.info("%-6s %8s %8s %10s","ngay","ve_BE%","cham+7%%","MDD_tiep_med")
for D in [14,30,60,90,180]:
    L.info("%-6d %8.1f %8.1f %10.1f",D,100*X[f"be{D}"].mean(),100*X[f"arm{D}"].mean(),X[f"mdd{D}"].median())
L.info("\n=== DELIST: coin het gia truoc cuoi CLOSES (>30 ngay): %d / %d = %.1f%%  | >90 ngay: %.1f%%",
       (X.delist_gap_d>30).sum(),len(X),100*(X.delist_gap_d>30).mean(),100*(X.delist_gap_d>90).mean())
L.info("delist trong nhom loser sau nhat (p10, profit<=%.1f): %.1f%%",sl.profit.quantile(.1),100*X[X.profit<=sl.profit.quantile(.1)].delist_gap_d.gt(30).mean())
L.info("\n=== theo do sau lo luc cat:")
X["bin"]=pd.cut(X.profit,[-100,-50,-30,-20,-10,0],labels=["<-50","-50..-30","-30..-20","-20..-10","-10..0"])
g=X.groupby("bin",observed=True).agg(n=("profit","size"),be30=("be30","mean"),be90=("be90","mean"),arm90=("arm90","mean"),mdd90=("mdd90","median"),delist=("delist_gap_d",lambda s:(s>30).mean()))
g[["be30","be90","arm90","delist"]]*=100; L.info("%s",g.round(1).to_string())
L.info("\n=== theo nam:")
X["yr"]=sl.ts.dt.year.values
g2=X.groupby("yr").agg(n=("profit","size"),meanP=("profit","mean"),be90=("be90","mean"),arm90=("arm90","mean"),delist=("delist_gap_d",lambda s:(s>30).mean()))
g2[["be90","arm90","delist"]]*=100; L.info("%s",g2.round(1).to_string())
