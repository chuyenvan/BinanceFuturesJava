#!/usr/bin/env python3
"""R3 Pha 0 probe (nhe): mo ta cau truc pass cua gate B0 tu artefact CO SAN (p0a_legs GATE_SMART, pred.bin A1).
Khong sim, khong PnL moi. Output r3_probe.json."""
import json, logging, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
import gate_offline as GO
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r3")
OUT = "/home/ubuntu/claude_master/res1109/r3_gate/"
L = pd.read_parquet("/home/ubuntu/claude_master/gsmart/p0a_legs.parquet")
R = {}
qs = [0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
R["rq_quantiles_all"] = dict(zip(map(str, qs), np.round(L.rq.quantile(qs).to_numpy(), 4).tolist()))
R["rq_share_ge"] = {str(t): round(float((L.rq >= t).mean()), 4) for t in (1.1, 1.25, 1.5, 2.0, 3.0)}
per = {}
for s, g in L.groupby("seed"):
    t = np.sort(g.ts.unique())
    gap = np.diff(t) / 60000.0
    lpm = g.groupby("ts").size()
    per[s] = dict(legs=len(g), minutes=len(t), legs_per_min_mean=round(float(lpm.mean()), 3), legs_per_min_p90=float(lpm.quantile(0.9)),
                  gap_le1=round(float((gap <= 1).mean()), 3), gap_le5=round(float((gap <= 5).mean()), 3),
                  gap_le15=round(float((gap <= 15).mean()), 3), gap_le60=round(float((gap <= 60).mean()), 3),
                  eps=int(g.ep.nunique()), legs_per_ep_med=float(g.groupby("ep").size().median()),
                  rank_le4=round(float((g["rank"] <= 4).mean()), 3), rank_ge13=round(float((g["rank"] >= 13).mean()), 3))
R["per_seed"] = per
# floor DYN_MIN: r*DYN_MIN*GS == p15 ?
pts, p15 = GO.load_pred(GO.SEEDS["A1"][1])
a1 = L[L.seed == "A1"]
j = np.searchsorted(pts, a1.ts.to_numpy(np.int64))
ok = (j < len(pts)) & (pts[np.minimum(j, len(pts) - 1)] == a1.ts.to_numpy(np.int64))
pp = p15[np.minimum(j, len(pts) - 1)]
rfl = pp / (GO.DYN_MIN * GO.GS)
R["A1_floor_share"] = round(float(np.mean(np.isclose(a1.r.to_numpy(np.float32), rfl, rtol=1e-5)[ok])), 4)
R["A1_match_pred"] = int(ok.sum())
# p15 autocorr & persistence (DEV 2022-2025, phut lien tuc)
m = (pts >= 1640970000000) & (pts < 1767200400000)
t, x = pts[m], p15[m].astype(np.float64)
cont = np.diff(t) == 60000
R["A1_dev_minutes"] = int(m.sum()); R["A1_contiguous_share"] = round(float(cont.mean()), 5)
ac = {}
for lag in (1, 5, 15, 60, 240):
    a, b = x[:-lag], x[lag:]
    okl = (t[lag:] - t[:-lag]) == lag * 60000
    ac[lag] = round(float(np.corrcoef(a[okl], b[okl])[0, 1]), 4)
R["A1_p15_autocorr"] = ac
s = pd.Series(x, index=pd.to_datetime(t, unit="ms"))
for w in (5, 15):
    mw = s.rolling("%dmin" % w).mean().to_numpy()
    R["A1_corr_p15_vs_mean%d" % w] = round(float(np.corrcoef(x, mw)[0, 1]), 4)
thr = np.quantile(x, 0.999)
ex = x >= thr
runs, cur = [], 0
for v, c in zip(ex[1:], np.r_[cont]):
    if v and c: cur += 1
    else:
        if cur: runs.append(cur)
        cur = 1 if v else 0
runs = np.array(runs) if runs else np.zeros(1)
R["A1_p15_top0.1pct_runlen"] = dict(n=int(len(runs)), med=float(np.median(runs)), p90=float(np.quantile(runs, 0.9)), max=int(runs.max()))
# tail: top 0.1% p15 phut -> top 0.1% cua mean15 co trung khong (Jaccard)
for w in (5, 15):
    mw = s.rolling("%dmin" % w).mean().to_numpy()
    e2 = mw >= np.quantile(mw, 0.999)
    R["A1_jaccard_top0.1_p15_vs_mean%d" % w] = round(float((ex & e2).sum() / (ex | e2).sum()), 4)
json.dump(R, open(OUT + "r3_probe.json", "w"), indent=1)
log.info("%s", json.dumps(R, indent=1))
