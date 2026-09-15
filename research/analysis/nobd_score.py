"""RESULT_NOBD: cham 3 ban NOBD theo luat du an, CI_INFLATE = sqrt(2 ln 2) (k=2). Khong sua c3_rates.py."""
import math, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

NOBD = [("T100_NOBD","NB_T100_NOBD"),("T130_NOBD","NB_T130_NOBD"),("T170_NOBD","NB_T170_NOBD")]
ORIG = [("T100","X1_C3_FULL_2021"),("T130","X1_GS_T130_2021"),("T170","X1_GS_T170_2021")]
F177, F121 = math.sqrt(2*math.log(2)), 1.21

print("=== 0. CONG ZERO-LEG (ON phai co 0 BIG_DOWN va 0 DCA_LEVEL1) ===")
ok = True
for nm, t in NOBD:
    d = C.trades(t); vc = d.level.value_counts().to_dict()
    bd, dc = vc.get("BIG_DOWN",0), vc.get("DCA_LEVEL1",0)
    good = (bd==0 and dc==0)
    ok &= good
    print("  %-11s n=%5d  BIG_DOWN=%d  DCA_LEVEL1=%d  PREDICT=%d  => %s" % (
        nm, len(d), bd, dc, vc.get("PREDICT_SYMBOL_TRADE",0), "PASS" if good else "**FAIL**"))
print("  CONG ZERO-LEG: %s\n" % ("PASS" if ok else "**FAIL**"))

def stats(t):
    d = C.trades(t); s = C.equity(t); r = C.rates(d)
    dd=(s/s.cummax()-1)*100; uw=s<s.cummax()
    yrs=(s.index[-1]-s.index[0]).days/365.25
    r.update(end=s.iloc[-1], cagr=((s.iloc[-1]/s.iloc[0])**(1/yrs)-1)*100,
             maxDD=dd.min(), uw=int(uw.groupby((~uw).cumsum()).sum().max()))
    return r, d, s

print("=== 1. BANG CHINH: 3 NOBD vs 3 BAN GOC (co BIG_DOWN) ===")
print("%-11s %6s %7s %8s %8s %8s %8s %6s %9s %8s" % ("tag","n","win%","TSloss%","meanP","mMargin","maxDD%","UW","equity","CAGR%"))
S={}
for nm,t in ORIG+NOBD:
    r,_,_ = stats(t); S[nm]=r
    print("%-11s %6.0f %7.2f %8.2f %8.3f %8.0f %8.2f %6d %9.0f %8.2f" % (
        nm,r["n"],r["win"],r["tsloss"],r["meanP"],r["margin"],r["maxDD"],r["uw"],r["end"],r["cagr"]))
print()
print("=== 2. MAT BAO NHIEU khi bo BIG_DOWN+DCA (NOBD vs goc, cung scale) ===")
print("%-8s %10s %10s %9s | %8s %8s %8s" % ("scale","eq goc","eq NOBD","d_eq%","CAGR goc","CAGR NOBD","d_pp"))
for a,b in (("T100","T100_NOBD"),("T130","T130_NOBD"),("T170","T170_NOBD")):
    x,y=S[a],S[b]
    print("%-8s %10.0f %10.0f %+9.1f | %8.2f %9.2f %+8.2f" % (
        a, x["end"], y["end"], 100*(y["end"]/x["end"]-1), x["cagr"], y["cagr"], y["cagr"]-x["cagr"]))
print()

print("=== 3. THEO NAM (NOBD) ===")
print("%-11s %5s %8s %9s %8s %6s %7s %8s" % ("tag","nam","ret%","pnl$","maxDD%","UW","qmin%","n_leg"))
HARD={}
for nm,t in NOBD:
    _,d,s = stats(t); bad=[]
    for y,sy in s.groupby(s.index.year):
        u=sy<sy.cummax(); uwm=int(u.groupby((~u).cumsum()).sum().max()) if len(u) else 0
        ddm=((sy/sy.cummax()-1)*100).min(); ry=(sy.iloc[-1]/sy.iloc[0]-1)*100
        qe=sy.resample("QE").last(); q0=pd.concat([pd.Series([sy.iloc[0]],index=[sy.index[0]]),qe]).iloc[:-1]
        qm=((qe.values/q0.values-1)*100).min()
        e=pd.to_datetime(d["end"],format="%Y%m%d %H:%M",errors="coerce")
        n=int((e.dt.year==y).sum())
        v=(ddm<-15) or (uwm>120) or (ry<0) or (qm<-5)
        if v: bad.append(str(y))
        print("%-11s %5d %8.2f %9.0f %8.2f %6d %7.2f %8d%s" % (nm,y,ry,sy.iloc[-1]-sy.iloc[0],ddm,uwm,qm,n," *" if v else ""))
    HARD[nm]=bad
    print("  => hard-constraint: %s\n" % ("PASS" if not bad else "**FAIL** nam "+",".join(bad)))

def raw_ci(da,db):
    blocks=np.union1d(da.blk.unique(),db.blk.unique())
    ga={k:v for k,v in da.groupby("blk")}; gb={k:v for k,v in db.groupby("blk")}
    rng=np.random.default_rng(C.SEED); obs={k:C.rates(da)[k]-C.rates(db)[k] for k in C.KEYS}
    dr={k:[] for k in C.KEYS}
    for _ in range(C.NREP):
        p=rng.choice(blocks,size=len(blocks),replace=True)
        la=[ga[b] for b in p if b in ga]; lb=[gb[b] for b in p if b in gb]
        ra=C.rates(pd.concat(la) if la else da.iloc[:0]); rb=C.rates(pd.concat(lb) if lb else db.iloc[:0])
        for k in C.KEYS: dr[k].append(ra[k]-rb[k])
    o={}
    for k in C.KEYS:
        a=np.asarray(dr[k],float); a=a[np.isfinite(a)]
        lo,hi=np.percentile(a,[2.5,97.5]); o[k]=(obs[k],lo,hi)
    return o

GOOD={"win":+1,"tsloss":-1,"meanP":+1}
base=C.trades("NB_T100_NOBD")
print("=== 4. CI (hieu = variant - T100_NOBD). k=2 => CI_INFLATE=sqrt(2 ln2)=%.4f ===" % F177)
for nm,t in (("T170_NOBD","NB_T170_NOBD"),("T130_NOBD","NB_T130_NOBD")):
    r=raw_ci(C.trades(t),base)
    print("--- %s - T100_NOBD ---" % nm)
    for lbl,f in (("1.177 (k=2, CHINH THUC)",F177),("1.210 (doi chieu lich su)",F121)):
        g=[];b=[]
        for k in ("win","tsloss","meanP"):
            o,lo,hi=r[k]; c=(lo+hi)/2; l2,h2=c-(c-lo)*f,c+(hi-c)*f
            if not (l2<=0<=h2): (g if o*GOOD[k]>0 else b).append("%s=%+.3f[%+.3f,%+.3f]"%(k,o,l2,h2))
        print("   %-26s -> %d TOT / %d XAU %s" % (lbl,len(g),len(b),("| "+"; ".join(g)) if g else ""))
    for k in ("win","tsloss","meanP"):
        o,lo,hi=r[k]; c=(lo+hi)/2
        print("      %-8s hieu %+8.3f  CI1.177 [%+8.3f,%+8.3f]"%(k,o,c-(c-lo)*F177,c+(hi-c)*F177))
    print()
