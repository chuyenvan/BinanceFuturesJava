import csv, datetime
SRC="/home/ubuntu/regime_work/btc_daily_close.csv"
OUT="/home/ubuntu/regime_work/regime_daily_x1_2021.csv"
DAY=86400000
close={}
with open(SRC) as f:
    r=csv.DictReader(f)
    for row in r:
        close[int(row["utcDay"])]=float(row["close"])
days=sorted(close)
print("close days",len(days),"range",days[0],days[-1])
# sim tick range: 2021-07-01 .. 2025-12-31 (UTC-day). floor cover from 2021-06-01.
def ud(datestr):
    d=datetime.datetime.strptime(datestr,"%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
    return int(d.timestamp()*1000//DAY)
D0=ud("2021-06-01"); D1=ud("2025-12-31")
SIM0=ud("2021-07-01")
rows=[]; nup=0; nnu=0
for D in range(D0,D1+1):
    c1=close.get(D-1); c31=close.get(D-31)
    if c1 is None or c31 is None:
        raise SystemExit("missing close for D=%d (need %d,%d)"%(D,D-1,D-31))
    ret30=c1/c31-1.0
    reg="UP" if ret30>0 else "NOTUP"
    scale="1.00" if reg=="UP" else "1.70"
    dt=datetime.datetime.utcfromtimestamp(D*DAY/1000).strftime("%Y-%m-%d")
    rows.append((D,dt,"%.6f"%ret30,reg,scale))
    if D>=SIM0:
        if reg=="UP": nup+=1
        else: nnu+=1
with open(OUT,"w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["utcDay","dateUTC","ret30","regime","scale"])
    w.writerows(rows)
tot=nup+nnu
print("wrote",len(rows),"rows ->",OUT)
print("SIM-range(2021-07-01..2025-12-31) days=%d UP=%d(%.1f%%) NOTUP=%d(%.1f%%)"%(tot,nup,100*nup/tot,nnu,100*nnu/tot))
# yearly breakdown
from collections import Counter
yc=Counter(); yu=Counter()
for (D,dt,ret,reg,sc) in rows:
    if D<SIM0: continue
    y=dt[:4]; yc[y]+=1
    if reg=="UP": yu[y]+=1
for y in sorted(yc):
    print("  %s: UP %d/%d = %.1f%%"%(y,yu[y],yc[y],100*yu[y]/yc[y]))
