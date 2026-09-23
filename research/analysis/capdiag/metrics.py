"""VIEC C: tinh thuoc CU (rate exit) va thuoc MOI (SumPnL/CAGR/maxDD/Calmar/Sortino/turnover/capture)."""
import csv, json, os, math, statistics
from datetime import datetime, timedelta

S = json.load(open("/home/ubuntu/capdiag/simout_series.json"))

PRINT = {
 "P0": "/home/ubuntu/kaggle_sim/out/t170-x1-2021/storage/printDone.csv",
 "L1": "/home/ubuntu/kaggle_sim/out/tl-l1/storage/printDone.csv",
 "L2": "/home/ubuntu/kaggle_sim/out/tl-l2/storage/printDone.csv",
 "L3": "/home/ubuntu/kaggle_sim/out/tl-l3/storage/printDone.csv",
 "F3": "/home/ubuntu/kaggle_sim/out/pc-close/storage/printDone.csv",
 "V1": "/home/ubuntu/java/devrun/X1_TH_GAP05_2021/storage/printDone.csv",
 "V2": "/home/ubuntu/java/devrun/X1_TH_GAP12_2021/storage/printDone.csv",
 "V3": "/home/ubuntu/java/devrun/X1_TH_WEAK17_2021/storage/printDone.csv",
}
TRACE = {  # trailTrace co peak => capture ratio
 "P0": "/home/ubuntu/kaggle_sim/out/tl-part/storage/trailTrace.csv",
 "L1": "/home/ubuntu/kaggle_sim/out/tl-l1/storage/trailTrace.csv",
 "L2": "/home/ubuntu/kaggle_sim/out/tl-l2/storage/trailTrace.csv",
 "L3": "/home/ubuntu/kaggle_sim/out/tl-l3/storage/trailTrace.csv",
 "F3": "/home/ubuntu/kaggle_sim/out/pc-close/storage/trailTrace.csv",
}
def pt(s):
    return datetime(int(s[0:4]), int(s[4:6]), int(s[6:8]), int(s[9:11]), int(s[12:14]))

def equity_stats(rows):
    # rows: [date, mpeak, b, run, maxrun, unPMin]
    d = [(r[0], r[2]) for r in rows if r[2] > 0]
    # b: co the lap lai theo ngay -> giu duong ngay
    dates = [x[0] for x in d]; eq = [x[1] for x in d]
    t0 = datetime.strptime(dates[0], "%Y%m%d"); t1 = datetime.strptime(dates[-1], "%Y%m%d")
    yrs = (t1 - t0).days / 365.0
    cagr = (eq[-1] / eq[0]) ** (1.0 / yrs) - 1 if yrs > 0 else float("nan")
    peak = eq[0]; mdd = 0.0
    for v in eq:
        peak = max(peak, v); mdd = min(mdd, v / peak - 1.0)
    # return ngay
    rets = []
    for i in range(1, len(eq)):
        if eq[i - 1] > 0: rets.append(eq[i] / eq[i - 1] - 1.0)
    mr = statistics.mean(rets)
    dn = [r for r in rets if r < 0]
    dd = math.sqrt(sum(r * r for r in dn) / len(dn)) if dn else float("nan")
    sortino = (mr / dd * math.sqrt(365)) if dd and dd > 0 else float("nan")
    sd = statistics.pstdev(rets)
    sharpe = (mr / sd * math.sqrt(365)) if sd > 0 else float("nan")
    return dict(years=yrs, b_first=eq[0], b_last=eq[-1], cagr=cagr * 100, maxdd=mdd * 100,
                calmar=(cagr * 100) / abs(mdd * 100) if mdd else float("nan"),
                sortino=sortino, sharpe=sharpe)

def capture(path):
    rows = list(csv.DictReader(open(path)))
    out = {}
    for lo in (20, 50, 100):
        g = []
        for r in rows:
            pk = float(r["peakPct"]); rt = float(r["ratePct"])
            if pk >= lo:
                g.append((rt / pk if pk > 0 else None, float(r["pnl"])))
        caps = [c for c, _ in g if c is not None]
        out[lo] = dict(n=len(g), cap_med=statistics.median(caps) if caps else None,
                       pnl=sum(p for _, p in g))
    return out

res = {}
for tag in PRINT:
    legs = list(csv.DictReader(open(PRINT[tag])))
    n = len(legs)
    pnl = [float(r["pnl"]) for r in legs]
    fund = sum(float(r["funding"]) for r in legs)
    nwin = sum(1 for p in pnl if p > 0)
    nsl = sum(1 for r in legs if r["status"] == "STOP_LOSS_DONE")
    dur = sum((pt(r["end"]) - pt(r["start"])).total_seconds() for r in legs)
    cum = len({(r["sym"], r["end"]) for r in legs})
    e = equity_stats(S[tag]["rows"])
    row = dict(tag=tag, n_leg=n, n_cum=cum, sum_pnl=sum(pnl), mean_p=sum(pnl) / n,
               win_pct=100.0 * nwin / n, tsloss_pct=100.0 * nsl / n,
               funding=fund, hold_hours=dur / 3600.0,
               leg_per_day=n / e["years"] / 365.0,
               eq=e, gate=S[tag]["gate"],
               maxrun=max(r[4] for r in S[tag]["rows"]))
    if tag in TRACE and os.path.exists(TRACE[tag]):
        row["cap"] = capture(TRACE[tag])
    res[tag] = row
    print(tag, "n=%d cum=%d SumPnL=%.0f meanP=%.3f win%%=%.2f TSloss%%=%.2f CAGR=%.2f%% maxDD=%.2f%% Calmar=%.2f Sortino=%.2f hold=%.0fh" %
          (n, cum, row["sum_pnl"], row["mean_p"], row["win_pct"], row["tsloss_pct"],
           e["cagr"], e["maxdd"], e["calmar"], e["sortino"], row["hold_hours"]))

json.dump(res, open("/home/ubuntu/capdiag/metrics.json", "w"), indent=1)
# turnover: tong thoi gian giu / (so ngay * 24)
print()
for tag, r in res.items():
    days = datetime.strptime(S[tag]["rows"][-1][0], "%Y%m%d") - datetime.strptime(S[tag]["rows"][0][0], "%Y%m%d")
    print(tag, "turnover=%.3f" % (r["hold_hours"] / (days.days * 24)))
print("saved")
