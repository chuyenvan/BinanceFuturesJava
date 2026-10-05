"""phu D2: lang phi 2022 roi vao luc nao, vi tri von (margin dang mo, so vi the) luc pass bi bo vs luc vao."""
import json, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_offline as g
B = dict(np.load(g.CACHE + "/cand_base.npz"))
mp = pd.read_csv(g.MAPF)
s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
OUT = {}
for arm in g.SEEDS:
    C = g.build(arm, B, s2id)
    G = g.run_g2(C)
    o, x, E = g.d1d2(arm, C, G, g.simlog(g.SEEDS[arm][2]))
    d = C["d"]
    s, e, mg = d["s_ms"].to_numpy(), d["e_ms"].to_numpy(), pd.to_numeric(d["margin"], errors="coerce").fillna(0).to_numpy()
    yr = C["yr"]
    W = G["P"] & ~E & (yr == 2022)[:, None]
    En = E & (yr == 2022)[:, None]
    res = {}
    for nm, Mk in (("waste", W), ("entered", En)):
        ti = C["ts"][np.nonzero(Mk)[0]]
        nopen = np.array([int(((s <= t) & (t < e)).sum()) for t in ti])
        mopen = np.array([float(mg[(s <= t) & (t < e)].sum()) for t in ti])
        mon = pd.to_datetime(ti + g.TZ, unit="ms").month
        res[nm] = dict(n=int(len(ti)), by_month={int(k): int(v) for k, v in pd.Series(mon).value_counts().sort_index().items()},
                       nopen_med=float(np.median(nopen)) if len(ti) else None,
                       margin_open_med=float(np.median(mopen)) if len(ti) else None,
                       first=str(pd.to_datetime(ti.min() + g.TZ, unit="ms")) if len(ti) else None)
    OUT[arm] = res
    print(arm, json.dumps(res))
json.dump(OUT, open(g.CACHE + "/waste2022.json", "w"), indent=1)
