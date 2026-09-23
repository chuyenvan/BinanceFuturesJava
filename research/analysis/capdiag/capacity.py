"""VIEC A: do muc do 'kin cho' tu sim.out cua T170 + cac bien the."""
import json, statistics
S=json.load(open("/home/ubuntu/capdiag/simout_series.json"))
UMAX=0.60
print("tag  n_days  maxU   daysU>=0.54  daysU>=0.30  medU   p90U  maxRunLegs  meanRun  daysRun0  fracDaysRun0  gate_ncand  gate_npass  pass_rate%%")
for tag in ["P0","L1","L2","L3","F3","V1","V2","V3"]:
    rows=S[tag]["rows"]
    Us=[]; runs=[]; 
    for d,mpeak,b,run,maxrun,unpm in rows:
        if b>0: Us.append(mpeak/b)
        runs.append(run)
    n=len(rows)
    print("%-4s %6d %6.3f %10d %11d %6.3f %6.3f %10d %8.3f %9d %12.4f %11d %11d %9.4f" % (
        tag,n,max(Us),sum(1 for u in Us if u>=0.9*UMAX),sum(1 for u in Us if u>=0.30),
        statistics.median(Us), sorted(Us)[int(.9*len(Us))],
        max(r[4] for r in rows), statistics.mean(runs), sum(1 for r in runs if r==0),
        100*sum(1 for r in runs if r==0)/n,
        S[tag]["gate"]["n_cand"],S[tag]["gate"]["n_pass"],100*S[tag]["gate"]["n_pass"]/S[tag]["gate"]["n_cand"]))
print()
# so ung vien / phut cho T170
for tag in ["P0"]:
    g=S[tag]["gate"]; days=len(S[tag]["rows"])
    print("T170: n_cand=%d over %d days => %.2f ung vien/phut (1440 phut/ngay); n_pass=%d => %.4f%% " % (
        g["n_cand"],days,g["n_cand"]/(days*1440),g["n_pass"],100*g["n_pass"]/g["n_cand"]))
