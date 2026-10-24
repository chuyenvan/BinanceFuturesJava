import sys, io
import numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/mm_q1")
import mm_core as C
sym, H = sys.argv[1], int(sys.argv[2])
tb, _ = C.fetch(sym, H, "trades")
df = tb.to_pandas(); df["p"] = df.price.astype(float); df["q"] = df.quantity.astype(float)
print("rows", len(df), "order_type", df.order_type.value_counts().to_dict())
print(df.p.describe())
med = df.p.median()
far = df[(df.p / med - 1).abs() > 0.005]
print("trades >0.5% from median:", len(far)); print(far.head(10).to_string())
D = C.load_d(sym, H); info, S = C.replay(D)
E, bb, ba, tt, tp, ibm = S["E"], S["bb"], S["ba"], S["tt"], S["tp"], S["ibm"]
ks = np.arange(300, 3300); t = H + ks * 1000
i = C.state_idx(E, t); lo = np.searchsorted(tt, t); hi = np.searchsorted(tt, t + 1000)
vals = []
for n in range(len(ks)):
    j = i[n]; b, a = bb[j], ba[j]
    if not (b > 0 and a > 0 and b < a) or hi[n] <= lo[n]:
        continue
    m = (a + b) / 2.0; wp = tp[lo[n]:hi[n]]; wb = ibm[lo[n]:hi[n]]
    js = np.flatnonzero(wb & (wp < m))
    if len(js):
        vals.append(((wp[js[0]] - m) / m * 1e4, int(wp[js[0]]), m, b, a, int(tt[lo[n] + js[0]]), int(t[n])))
v = pd.DataFrame(vals, columns=["as0bps", "p", "m", "bb", "ba", "tt", "t"])
print(v.as0bps.describe()); print(v.sort_values("as0bps").head(5).to_string())
print("dtypes", tp.dtype, type(vals[0][0]) if vals else None)
