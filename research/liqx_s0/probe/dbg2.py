import pandas as pd, numpy as np, pyarrow.parquet as pq, math, os, sys
sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/liqx_s0"))
from score import proxies
D = 1646092800000  # 2022-03-01
G = proxies(pd.read_parquet(os.path.expanduser("~/claude_master/liqx_wk/buckets_AB.parquet")))
P = G[G.valid & (G.day == D) & (G.r5 < -0.01)]
pk = set(zip(P.sym, P["T"]))
close = {}
for f in ["/home/ubuntu/vz_e1/raw/kline1m-2022-02.parquet", "/home/ubuntu/vz_e1/raw/kline1m-2022-03.parquet"]:
    t = pq.read_table(f, columns=["ts", "sym", "close"], filters=[("ts", ">=", D - 360000), ("ts", "<", D + 86400000)]).to_pandas()
    for s, a, b in zip(t.sym.astype(str), t.ts, t.close):
        close[(s, int(a))] = b
mt = pq.read_table("/home/ubuntu/vz/out/metrics5m/2022/2022-03.parquet", columns=["ts", "sym", "oi_value"], filters=[("ts", ">=", D), ("ts", "<=", D + 86400000)]).to_pandas()
oiv = {(s, int(a)): b for s, a, b in zip(mt.sym.astype(str), mt.ts, mt.oi_value) if b == b}
for s, T in sorted(pk):
    need = [(s, T - j * 60000) for j in range(1, 7)]
    miss = [n[1] for n in need if n not in close]
    if miss or (s, T) not in oiv or (s, T - 300000) not in oiv:
        r = P[(P.sym == s) & (P["T"] == T)].iloc[0]
        print(s, pd.Timestamp(T, unit="ms"), "miss_close", [str(pd.Timestamp(x, unit="ms")) for x in miss], "oi", (s, T) in oiv, (s, T - 300000) in oiv, "nbar", r.nbar, r.c0, r.c1)
# also check pipeline universe vs v2-style universe
dq = pd.read_parquet(os.path.expanduser("~/claude_master/liqx_wk/daily_qv.parquet"))
print(sorted(G[G.day == D].sym.unique())[:5], G[G.day == D].sym.nunique())
