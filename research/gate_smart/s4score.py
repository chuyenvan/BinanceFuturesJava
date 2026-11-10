#!/usr/bin/env python3
"""GATE_SMART S4 cham (prereg 6d92cdba ?2.3-2.5): fwd return 24h/72h rong phi 0,2 % (round-trip) tu close phut sau,
near-miss (0,8<=r/q<1) vs pass [1;1,1). Gop 8 seed (trong so n_seed), CI90 bootstrap cum NGAY(+07) 2000 lan, seed RNG 20261110.
S4 TRUE <=> mean72(near) >= mean72(pass_low) VA CI90 hieu (near - pass_low) khong chua 0 ve phia near tot hon (lo > 0)."""
import json, logging, sys
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("s4score")
F = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/claude_master/gsmart/out/gsm-s4-fwd/s4_fwd.parquet"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/ubuntu/claude_master/gsmart/s4_score.json"
FEE, SEED, NB, TZ = 0.002, 20261110, 2000, 7 * 3600000
R = pd.read_parquet(F)
meta = dict(n=len(R), nan0=int(R.c0.isna().sum()), nan24=int(R.c24.isna().sum()), nan72=int(R.c72.isna().sum()),
            by_kind=R.kind.value_counts().to_dict(), nan72_by_kind=R[R.c72.isna()].kind.value_counts().to_dict())
log.info("meta %s", meta)
assert meta["by_kind"] == {"near": 18981, "pass_low": 3273}, meta["by_kind"]
R["day"] = (R.ts.astype(np.int64) + TZ) // 86400000
out = dict(prereg="6d92cdba", fee_roundtrip=FEE, rng_seed=SEED, n_boot=NB, cluster="ngay(+07) cua o", weight="n_seed (gop 8 seed)", meta=meta)
rng = np.random.default_rng(SEED)
days = np.unique(R.day.to_numpy())
BS = [rng.choice(days, len(days), replace=True) for _ in range(NB)]
for H in ("24", "72"):
    X = R[R["c" + H].notna() & R.c0.notna()].copy()
    X["ret"] = X["c" + H] / X.c0 - 1.0 - FEE
    X["w"] = X.n_seed.astype(float)
    g = X.groupby(["day", "kind"]).apply(lambda d: pd.Series(dict(sw=d.w.sum(), swr=(d.w * d.ret).sum()))).unstack("kind").fillna(0.0)
    g = g.reindex(days).fillna(0.0)
    sw_n, swr_n = g[("sw", "near")].to_numpy(), g[("swr", "near")].to_numpy()
    sw_p, swr_p = g[("sw", "pass_low")].to_numpy(), g[("swr", "pass_low")].to_numpy()
    di = {d: i for i, d in enumerate(days)}
    mn, mp = swr_n.sum() / sw_n.sum(), swr_p.sum() / sw_p.sum()
    diffs, bn, bp = [], [], []
    for b in BS:
        ix = np.fromiter((di[d] for d in b), int, len(b))
        a1, a2 = swr_n[ix].sum() / sw_n[ix].sum(), swr_p[ix].sum() / sw_p[ix].sum()
        bn.append(a1); bp.append(a2); diffs.append(a1 - a2)
    lo, hi = np.percentile(diffs, [5, 95])
    res = dict(n_near=int((X.kind == "near").sum()), n_pass_low=int((X.kind == "pass_low").sum()),
               mean_near=round(float(mn), 5), ci90_near=[round(float(v), 5) for v in np.percentile(bn, [5, 95])],
               mean_pass_low=round(float(mp), 5), ci90_pass_low=[round(float(v), 5) for v in np.percentile(bp, [5, 95])],
               diff=round(float(mn - mp), 5), ci90_diff=[round(float(lo), 5), round(float(hi), 5)],
               med_near=round(float(X[X.kind == "near"].ret.median()), 5), med_pass_low=round(float(X[X.kind == "pass_low"].ret.median()), 5))
    out["H" + H] = res
    log.info("H%s %s", H, res)
r72 = out["H72"]
out["S4"] = bool(r72["mean_near"] >= r72["mean_pass_low"] and r72["ci90_diff"][0] > 0)
json.dump(out, open(OUT, "w"), indent=1)
log.info("S4 = %s", out["S4"])
