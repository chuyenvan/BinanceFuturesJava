import json, itertools, statistics
R=json.load(open("/home/ubuntu/capdiag/metrics.json"))
tags=["L1","L2","L3","F3","V1","V2","V3"]   # bo P0 theo pre-reg 3.4
def rank(key, tags=tags):
    vals={t:(R[t][key] if key in R[t] else R[t]["eq"][key]) for t in tags}
    order=sorted(tags, key=lambda t:-vals[t]); return order, vals
def kendall(a,b,tags=tags):
    n=0; c=0; d=0
    for x,y in itertools.combinations(tags,2):
        sa=(a[x]>a[y])-(a[x]<a[y]); sb=(b[x]>b[y])-(b[x]<b[y])
        if sa==0 or sb==0: continue
        n+=1
        if sa==sb: c+=1
        else: d+=1
    return (c-d)/n, c, d, n
old_order, old_v = rank("mean_p")
new_order, new_v = rank("calmar")
print("hang CU (meanP)  :", " > ".join(old_order))
print("hang MOI (Calmar):", " > ".join(new_order))
tau,c,d,n = kendall(old_v,new_v)
print("Kendall tau(meanP,Calmar)=%.3f  c=%d d=%d n=%d"%(tau,c,d,n))
# cap dao dau
inv=[]
for x,y in itertools.combinations(tags,2):
    so=(old_v[x]>old_v[y]); sn=(new_v[x]>new_v[y])
    if so!=sn: inv.append((x,y,so,sn))
print("so cap dao dau:",len(inv))
for x,y,so,sn in inv:
    print("   %s vs %s: meanP %s  |  Calmar %s"%(x,y,"tot hon" if so else "kem hon","tot hon" if sn else "kem hon"))
# cung tinh voi SumPnL / Sortino
for k,label in [("sum_pnl","SumPnL"),("sortino","Sortino")]:
    o,v = rank(k, tags)
    t2,_,_,_ = kendall(old_v,v)
    print("tau(meanP,%s)=%.3f  hang: %s"%(label,t2," > ".join(o)))
print()
print("bang day du:")
hdr="tag  n_leg  SumPnL  meanP  win%%  TSloss%%  CAGR%%  maxDD%%  Calmar  Sortino  hold_h  turn  leg/day"
print(hdr)
for t in ["P0","L1","L2","L3","F3","V1","V2","V3"]:
    r=R[t]
    turn=r["hold_hours"]/((1643)*24)
    print("%-4s %5d %7.0f %7.3f %6.2f %7.2f %7.2f %7.2f %7.2f %7.2f %7.0f %5.3f %6.3f"%(
        t,r["n_leg"],r["sum_pnl"],r["mean_p"],r["win_pct"],r["tsloss_pct"],r["eq"]["cagr"],r["eq"]["maxdd"],
        r["eq"]["calmar"],r["eq"]["sortino"],r["hold_hours"],turn,r["leg_per_day"]))
print()
print("capture ratio (trailTrace):")
for t in ["P0","L1","L2","L3","F3"]:
    c=R[t].get("cap")
    if not c: print(t,"RO"); continue
    print("  %s  >=20%%: n=%d medcap=%.3f SumPnL=%.0f | >=50%%: n=%d medcap=%.3f SumPnL=%.0f | >=100%%: n=%d medcap=%s SumPnL=%.0f"%(
        t,c["20"]["n"],c["20"]["cap_med"],c["20"]["pnl"],c["50"]["n"],c["50"]["cap_med"],c["50"]["pnl"],
        c["100"]["n"], ("%.3f"%c["100"]["cap_med"] if c["100"]["cap_med"] is not None else "NA"),c["100"]["pnl"]))
