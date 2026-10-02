import sys, os, json, logging
import numpy as np, pandas as pd
REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import short_v2_p0a_statemap as P
import short_v3_r3_breakdown as R
logging.basicConfig(level=logging.WARNING)
res, df = R.run()
YE = (2022, 2023, 2024, 2025)
out = {}
def gates(b, al, label):
    """b: rows BRK (1 T); al: rows ALL same T. Tra G1..G5 tren tap b."""
    lo, hi, _, _ = P.ci_block(b.pnl.to_numpy(float), b.date)
    mu = float(b.pnl.mean())
    yp = int(sum(b[b.year == y].pnl.mean() > 0 for y in YE if (b.year == y).any()))
    exs = float(-b.excess.mean()); sq = float((b.maxfav >= 0.1).mean()); sqa = float((al.maxfav >= 0.1).mean())
    return dict(label=label, n=len(b), ndays=int(b.date.nunique()), bleed=float(b.ret.mean()), netproxy=mu, noSL=float(b.pnl_nosl.mean()),
                ci_raw=[lo, hi], ci_infl=[mu - (mu - lo) * 1.18, mu + (hi - mu) * 1.18], years_pos=yp, excess_short=exs, pSQ10=sq,
                ratio=sq / sqa, G1=mu > .005, G2=lo > 0 and mu - (mu - lo) * 1.18 > 0, G3=yp >= 3, G4=exs > .003, G5=sq <= .8 * sqa)
def dayw(b, al, label):
    g = b.groupby("date")
    dd = pd.DataFrame(dict(pnl=g.pnl.mean(), nosl=g.pnl_nosl.mean(), ret=g.ret.mean(), ex=-g.excess.mean(),
                           sq=g.maxfav.apply(lambda x: (x >= .1).mean())))
    dd["year"] = dd.index.year
    # CI block-7d tren chuoi ngay (moi ngay trong so 1)
    lo, hi, _, _ = P.ci_block(dd.pnl.to_numpy(float), pd.Series(dd.index))
    yp = int(sum(dd[dd.year == y].pnl.mean() > 0 for y in YE))
    sqa = al.groupby("date").maxfav.apply(lambda x: (x >= .1).mean()).mean()
    mu = float(dd.pnl.mean())
    return dict(label=label, ndays=len(dd), bleed=float(dd.ret.mean()), netproxy=mu, noSL=float(dd.nosl.mean()), ci_raw=[lo, hi],
                years_pos=yp, yearly={int(y): round(float(dd[dd.year == y].pnl.mean()), 4) for y in YE},
                excess_short=float(dd.ex.mean()), pSQ10=float(dd.sq.mean()), pSQ10_ALL_dayw=float(sqa),
                G1=mu > .005, G2=lo > 0 and mu - (mu - lo) * 1.18 > 0, G3=yp >= 3, G4=float(dd.ex.mean()) > .003, G5=float(dd.sq.mean()) <= .8 * sqa)
for T in (3, 7):
    x = df[df["T"] == T]; b = x[x.B]; n_ = x[x.N]
    top = b.groupby("date").size().sort_values(ascending=False)
    t2 = top.index[:2]
    out[T] = dict(base=gates(b, x, "pooled (=script)"),
                  excl_2days=gates(b[~b.date.isin(t2)], x, "excl %s" % [str(d.date()) for d in t2]),
                  excl_2days_ALLmatched=gates(b[~b.date.isin(t2)], x[~x.date.isin(t2)], "excl 2 days, ALL also excl"),
                  dayweighted=dayw(b, x, "day-weighted BRK"),
                  BNV_dayweighted=dayw(n_, x, "day-weighted BNV"),
                  cap_per_day_20=gates(b.groupby("date", group_keys=False).apply(lambda g: g.sample(min(len(g), 20), random_state=1)), x, "cap 20 obs/day (random)"))
    # tier NA / bull NaN
print(json.dumps(out, indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o)))
json.dump(out, open("/home/ubuntu/claude_master/1002/audit_r3_cluster.json", "w"), indent=1, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o))
