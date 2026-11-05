import glob, numpy as np, pandas as pd
H, MIN, DAY = 3600000, 60000, 86400000
A = pd.read_csv("/home/ubuntu/kaggle_sim/out/gs-x14-s42/gate_trace_A.csv", dtype={'ts': np.int64, 'sp': np.float32, 'p15': np.float32, 'r': np.float32})
M = pd.read_parquet(sorted(glob.glob("/home/ubuntu/claude_master/gst1030/seed/out_*/live_labeled.parquet"))[-1])
d0 = 1792195200000 - 7 * H
pa = A[(A.ts >= d0) & (A.ts < d0 + 15 * DAY)].groupby('ts').p15.first()
pm = M[(M.ts >= d0) & (M.ts < d0 + 15 * DAY)].groupby('ts').p15.first().astype(np.float32)
print("minutes A", len(pa), "M", len(pm))
for sh in range(-5, 6):
    x = pd.concat([pa.rename('a'), pm.rename('m').set_axis(pm.index + sh * MIN)], axis=1, join='inner')
    rel = (x.a.astype(float) - x.m.astype(float)).abs() / x.m.abs()
    print("shift %+d min: n=%d exact=%.4f rel<=1e-6=%.4f median_rel=%.2e" % (sh, len(x), (x.a == x.m).mean(), (rel <= 1e-6).mean(), rel.median()))
# per-day exact p15 at best shift 0
x = pd.concat([pa.rename('a'), pm.rename('m')], axis=1, join='inner')
x['day'] = pd.to_datetime(x.index + 7 * H, unit='ms').strftime('%m-%d')
print(x.groupby('day').apply(lambda g: round(float(((g.a - g.m).abs() / g.m <= 1e-6).mean()), 3)).to_dict())
# do sp sets match ignoring order? minute where p15 equal
eq = x[(x.a - x.m).abs() / x.m <= 1e-6].index
print("minutes p15 equal:", len(eq))
if len(eq):
    t = eq[len(eq) // 2]
    sa = np.sort(A[A.ts == t].sp.values); sm = np.sort(M[M.ts == t].gateValue.astype(np.float32).values)
    print("t", t, "A sp", sa[:6], "\nM sp", sm[:6], "\nM clean", M[M.ts == t].clean.mean())
