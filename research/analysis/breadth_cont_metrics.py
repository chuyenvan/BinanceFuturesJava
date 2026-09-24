"""BREADTH_CONT_METRICS (TASK B2 Buoc 7, docs/prereg/PREREG_BREADTH_CONT.md) — u1..u5 cho BRC.
Tai dung nguyen van ham cua bigdown_struct.py (icc_for=icc_anova, n_eff, maxdd_decomp, label_trades,
build_bd_flags, load_trades_utc, hourly_grid) + c3_rates.py (equity, stats). Khong sua 2 file goc.
u2 (khau vi) tinh rieng bang x1_rates.py --appetite current --k. Chay: python3 breadth_cont_metrics.py
"""
import json, logging, os, sys
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import bigdown_struct as B
import c3_rates as C
logging.basicConfig(level=logging.INFO, format="%(message)s")
log=logging.getLogger("brc")
TAGS={"T170":"X1_GS_T170_2021","T100":"X1_C3_FULL_2021","BR":"X1_C3_FULL_2021_REGIME_BR",
      "BRC":"X1_C3_FULL_2021_REGIME_BRC","BRC0":"X1_C3_FULL_2021_REGIME_BRC0"}
OUT_JSON=os.path.join(HERE,"out","breadth_cont_metrics.json")

def uw_year(tag):
    s=C.equity(tag); out={}
    for y,sy in s.groupby(s.index.year):
        uw=sy<sy.cummax()
        out[str(y)]=int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
    return out

def uw_total(tag):
    s=C.equity(tag); uw=s<s.cummax()
    rl=uw.groupby((~uw).cumsum()).sum()
    return int(rl.max()) if len(rl) and rl.max()>0 else 0

def main():
    os.makedirs(os.path.join(HERE,"out"),exist_ok=True)
    grid,px=B.hourly_grid(); flags,extra=B.build_bd_flags(grid,px); fb=flags["BD1a_5pct24h"]
    res={}
    for name,tag in TAGS.items():
        p=f"{C.B}/{tag}/storage/printDone.csv"
        if not os.path.exists(p):
            log.info("%s: MISSING (%s) - skip",name,tag); continue
        d=B.load_trades_utc(tag)
        cohort=d.t0.dt.floor("1D")
        icc=B.icc_for(d,"roi",cohort)
        ne=B.n_eff(d,cohort,icc["icc"] if icc else None)
        d2=d.copy()
        en,ex=B.label_trades(d,grid,fb); d2["exposed_bd"]=ex; d2["enter_bd"]=en
        st=C.stats(tag)
        res[name]=dict(tag=tag,n=len(d),n_eff_total=ne["n_eff_total"],
            icc=(icc["icc"] if icc else None),
            maxdd=B.maxdd_decomp(tag,grid,fb,d2), maxDD=st["maxDD"],
            uw=uw_total(tag), uw_year=uw_year(tag),
            cagr=st["cagr"], yr=st["yr"], equity=float(C.equity(tag).iloc[-1]))
        log.info("%-5s n=%4d neff=%7.2f icc=%.4f maxDD=%7.3f UW=%3d CAGR=%6.2f eq=%d uwY=%s yrCAGR=%s",
            name,len(d),res[name]["n_eff_total"] or -1,res[name]["icc"] or -1,res[name]["maxDD"],
            res[name]["uw"],res[name]["cagr"],int(res[name]["equity"]),res[name]["uw_year"],
            {k:round(v,1) for k,v in res[name]["yr"].items()})
    g={}
    if "T170" in res and "BRC" in res:
        nt=res["T170"]["n_eff_total"]; nb=res["BRC"]["n_eff_total"]
        g["u1_thr"]=1.5*nt; g["u1_ratio"]=nb/nt; g["u1_pass"]=bool(nb>=1.5*nt)
        g["u3_maxdd_thr"]=res["T170"]["maxDD"]*1.25; g["u3_uw_thr"]=res["T170"]["uw"]*1.25
        g["u3_pass"]=bool(res["BRC"]["maxDD"]>=res["T170"]["maxDD"]*1.25 and res["BRC"]["uw"]<=res["T170"]["uw"]*1.25)
    if "T100" in res and "BRC" in res:
        y=res["BRC"]["yr"]; t=res["T100"]["yr"]
        g["u5_2023"]=(y.get("2023"),0.9*t.get("2023")); g["u5_2024"]=(y.get("2024"),0.9*t.get("2024"))
        g["u5_pass"]=bool(y.get("2023",-9)>=0.9*t.get("2023",1e9) and y.get("2024",-9)>=0.9*t.get("2024",1e9))
    if "BRC" in res and "BRC0" in res and "BR" in res:
        g["u4_uw_brc"]=res["BRC"]["uw"]; g["u4_uw_brc0"]=res["BRC0"]["uw"]
        g["u4_ret2025_brc"]=res["BRC"]["yr"].get("2025"); g["u4_ret2025_br"]=res["BR"]["yr"].get("2025")
        g["u4_uw_pass"]=bool(res["BRC"]["uw"]<res["BRC0"]["uw"])
        g["u4_ret_pass"]=bool(res["BRC"]["yr"].get("2025",-9)>res["BR"]["yr"].get("2025",1e9))
        g["u4_pass"]=bool(g["u4_uw_pass"] and g["u4_ret_pass"])
    res["gate"]=g
    json.dump(res,open(OUT_JSON,"w"),indent=2,default=str)
    log.info("GATE %s",json.dumps(g,default=str))
    log.info("DONE -> %s",OUT_JSON)

if __name__=="__main__": main()
