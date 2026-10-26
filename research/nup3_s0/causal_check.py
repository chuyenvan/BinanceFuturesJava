#!/usr/bin/env python3
"""NUP3-S0 kiem nhan qua: 20 lenh them ngau nhien (DEV a1, rng 20261026): t, W_burst va danh sach cum A2 duoc dem (deu < t);
W_book: max start leg B0 dang mo < t, max end leg da realized < t; W_quiet: cum B0 trong 24h truoc < t; W_mkt: bar cuoi = t-1'."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/nup3_s0")
import s0

WK = s0.WK
A = pd.read_parquet(WK + "/A_DEV_a1.parquet")
X = A[~A.common].reset_index(drop=True)
a2c = s0.clusters(s0.load("nup-a2-a1"))
b0d = s0.load("tsx-x14-a1")
b0c = s0.clusters(b0d)
ew = s0.EW()
rng = np.random.default_rng(20261026)
idx = np.sort(rng.choice(len(X), 20, replace=False))
T = a2c.t0.to_numpy(np.int64)
rows, allok = [], True
f = lambda x: str(np.datetime64(int(x), "ms"))[:16]
for i in idx:
    t = int(X.t0[i])
    cnt = T[(T >= t - 3600000) & (T < t)]
    ts, te = b0d.ts_l.to_numpy(np.int64), b0d.te_l.to_numpy(np.int64)
    op = (ts < t) & (te >= t)
    rl = te < t
    U = b0d.notional.to_numpy()[op].sum() / (s0.CAP0 + b0d.pnl.to_numpy()[rl].sum())
    q = b0c.t0.to_numpy(np.int64)
    q = q[(q >= t - s0.DAY) & (q < t)]
    tu = t - s0.H7
    i_last = (tu - ew.g0) // s0.MM - 1
    last_bar = ew.g0 + i_last * s0.MM
    ok = bool(len(cnt) == X.burst[i] and np.all(cnt < t) and abs(U - X.U[i]) < 1e-9 and (not op.any() or ts[op].max() < t)
              and (not rl.any() or te[rl].max() < t) and np.all(q < t) and len(q) == X.b0_cnt24[i] and last_bar == tu - s0.MM)
    allok &= ok
    rows.append(dict(sym=X.sym[i], t_local=f(t), W_burst_cnt=int(X.burst[i]), counted_t0=";".join(f(x) for x in cnt),
                     max_counted=f(cnt.max()) if len(cnt) else "", U=float(X.U[i]), max_open_start=f(ts[op].max()) if op.any() else "",
                     max_realized_end=f(te[rl].max()) if rl.any() else "", b0_cnt24=int(X.b0_cnt24[i]),
                     max_b0_t0_24h=f(q.max()) if len(q) else "", mkt_ret=float(X.mkt_ret[i]), mkt_last_bar_utc=f(last_bar), ok=ok))
df = pd.DataFrame(rows)
df.to_csv(s0.OUTD + "/causal_sample.csv", index=False)
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 80)
print(df.drop(columns=["counted_t0"]).to_string(index=False))
print(df[["t_local", "counted_t0"]].head(5).to_string(index=False))
print("CAUSAL_OK", allok)
