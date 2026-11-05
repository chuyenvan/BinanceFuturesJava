import glob, numpy as np, pandas as pd
H = 3600000
o = "/home/ubuntu/kaggle_sim/out/"
tr = sorted(glob.glob(o + "**/gate_trace_A.csv*", recursive=True))
print("trace files", tr)
L = sorted(glob.glob("/home/ubuntu/claude_master/gst1030/seed/out_*/live_labeled.parquet"))
print("live", L)
A = pd.read_csv(tr[-1], dtype={'ts': np.int64, 'sp': np.float32, 'p15': np.float32, 'r': np.float32})
M = pd.read_parquet(L[-1])
print("A cols", list(A.columns), len(A)); print(A.head(3).to_string())
print("M cols", list(M.columns), len(M)); print(M.head(3).to_string())
print("A ts mod 60000:", pd.Series(A.ts % 60000).value_counts().head(3).to_dict())
print("M ts mod 60000:", pd.Series(M.ts % 60000).value_counts().head(3).to_dict())
d0 = 1792195200000 - 7 * H  # 10-17 +07
a = A[(A.ts >= d0 + 3 * 86400000) & (A.ts < d0 + 4 * 86400000)]
m = M[(M.ts >= d0 + 3 * 86400000) & (M.ts < d0 + 4 * 86400000) & (M.clean)]
print("day 10-20: A rows", len(a), "uniq ts", a.ts.nunique(), "| M clean rows", len(m), "uniq ts", m.ts.nunique())
ta = set(a.ts); tm = set(m.ts)
print("ts overlap exact", len(ta & tm), " overlap floor-minute", len({t // 60000 for t in ta} & {t // 60000 for t in tm}))
# per-minute compare by floor minute
a2 = a.assign(mn=a.ts // 60000); m2 = m.assign(mn=m.ts // 60000)
x = a2.groupby('mn').size().rename('nA').to_frame().join(m2.groupby('mn').size().rename('nM'), how='inner')
print("rows/minute A vs M (median):", x.nA.median(), x.nM.median())
mn = x.index[len(x) // 2]
print("sample minute", mn * 60000)
print(a2[a2.mn == mn].sort_values('sp').head(6).to_string())
cols = [c for c in ['ts', 'symbol', 'gateValue', 'sp', 'p15', 'r', 'kind', 'held', 'clean'] if c in m2.columns]
print(m2[m2.mn == mn].sort_values('gateValue').head(6)[cols].to_string())
# match on floor minute + sp
J = a2.merge(m2.assign(sp=m2.gateValue.astype(np.float32))[['mn', 'sp', 'r', 'symbol']], on=['mn', 'sp'], how='inner', suffixes=('_A', '_C'))
print("join (minute, sp float32):", len(J), "of A", len(a2))
if len(J):
    rel = (J.r_A.astype(float) - J.r_C.astype(float)).abs() / J.r_C.astype(float).abs()
    print("rel<=1e-9 frac", (rel <= 1e-9).mean(), "median rel", rel.median())
