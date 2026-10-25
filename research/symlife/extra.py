import os, json, pandas as pd, numpy as np
WK = os.path.expanduser("~/claude_master/symlife_wk")
OUTR = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/symlife")
P = pd.read_parquet(WK + "/legs_checked.parquet")
T = pd.read_parquet(WK + "/lifecycle.parquet").set_index("symbol")
A = pd.read_parquet(WK + "/vision_act.parquet")
DAY = 86400000
N, NP = len(P), P.pnl.sum()
fin = np.isfinite(P.last_ts)
for d in (1, 3, 7, 14):
    m = fin & (P.last_ts - P.t_in < d * DAY) & (P.t_in <= P.last_ts)
    q = P[m]
    print(f"entry trong {d} ngay truoc last_trade (pre-delist): legs={len(q)} ({100*len(q)/N:.2f}%) pnl={q.pnl.sum():.0f} ({100*q.pnl.sum()/NP:.2f}%) n_sym={q.symbol.nunique()} syms={sorted(q.symbol.unique())[:30]}")
# early listing: phan bo theo gio tu niem yet
h = (P.t_in - P.first_ts) / 3600000
for lo, hi in ((0, 24), (24, 72), (72, 168), (168, 720)):
    q = P[(h >= lo) & (h < hi)]
    print(f"entry {lo}-{hi}h sau niem yet: legs={len(q)} ({100*len(q)/N:.2f}%) pnl={q.pnl.sum():.0f} ({100*q.pnl.sum()/NP:.2f}%) n_sym={q.symbol.nunique()} winrate={(q.pnl>0).mean():.3f} pnl/notional={q.pnl.sum()/q.notional.sum():.4f}")
q = P[h >= 720]; print(f"entry >=30d: legs={len(q)} pnl/notional={q.pnl.sum()/q.notional.sum():.4f} winrate={(q.pnl>0).mean():.3f}")
# 2025-10-10 cum
q = P[(P.t_in >= pd.Timestamp('2025-10-10').value//10**6) & (P.t_in < pd.Timestamp('2025-10-12').value//10**6)]
print("2025-10-10/11: legs", len(q), "pnl", round(q.pnl.sum()), "early7d legs", int(q.early7d.sum()), "early7d pnl", round(q[q.early7d].pnl.sum()))
# per-seed early7d pnl share
ps = P.groupby("seed").apply(lambda g: pd.Series(dict(e7=100*g[g.early7d].pnl.sum()/g.pnl.sum(), e1=100*g[(g.t_in-g.first_ts)<DAY].pnl.sum()/g.pnl.sum())))
print(ps.round(2).to_string())
# TradFi / non-24h symbols in live: Vision 10-23 n_tr
a = A[(A.day == "2026-10-23") & A.ok & (A.n_tr > 0)].set_index("sym")
low = a[a.n_tr < 1200]
low = low.join(T[["first_utc"]])
print("TRADING 10-23 voi <1200 phut co trade:", len(low), "; trong do niem yet 2025-12+ :", int((low.first_utc >= "2025-12-01").sum()))
print(low.sort_values("n_tr")[["n_tr", "first_utc"]].head(130).to_string())
low[["n_tr", "first_utc"]].to_csv(OUTR + "/live_low_activity_1023.csv")
print("so symbol niem yet 2026 (TRADING):", int(((T.status_now == "TRADING") & (T.first_utc >= "2026-01-01")).sum()))
