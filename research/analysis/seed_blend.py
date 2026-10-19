#!/usr/bin/env python3
"""SEED_BLEND (PREREG_SEED_BLEND): blend k run OFF (moi run 1/k von) -> MTM Vision -> metrics."""
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402,F401  (patch R -> Vision) PHAI truoc
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import iso_risk_driver as I  # noqa: E402
import reset_rule_score as R  # noqa: E402
import flat3_crashpen_driver as F3  # noqa: E402
import n700_driver as N  # noqa: E402

assert R._work is MT._work_vision
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("sb")
D = "/home/ubuntu/claude_master/seedblend"
S = I.SEEDS
GROUPS = {"k1": [[s] for s in S], "k2": [S[0:2], S[2:4], S[4:6], S[6:8]], "k4": [S[0:4], S[4:8]], "k8": [S]}
SC = ["quantity", "margin", "notional", "pnl"]

legs1 = {s: R.load_legs(I.OFF[s]) for s in S}
daily1 = {s: R.load_daily(I.OFF[s]) for s in S}


def blend(g):
    k = len(g)
    L = []
    for s in g:
        x = legs1[s].copy()
        for c in SC:
            x[c] = x[c] / k
        x["seed"] = s
        L.append(x)
    L = pd.concat(L, ignore_index=True).sort_values("ts", kind="mergesort").reset_index(drop=True)
    idx = daily1[g[0]].index
    for s in g[1:]:
        idx = idx.intersection(daily1[s].index)
    d = sum(daily1[s].loc[idx, ["b", "unP", "equity"]] for s in g) / k
    d.insert(0, "d", daily1[g[0]].loc[idx, "d"])
    return L, d


keys, LG, DG = {}, {}, {}
for kk, gs in GROUPS.items():
    for i, g in enumerate(gs):
        name = "%s_%s" % (kk, "+".join(g))
        LG[name], DG[name] = blend(g)
        keys[name] = g
log.info("blend %d: %s", len(keys), list(keys))
mtm = R.run_mtm(LG, workers=3, chunk=30)
json.dump(mtm, open(D + "/mtm_blend.json", "w"))
M = {}
for name in keys:
    N.TAG[name], N.DESC[name] = name, "SEED_BLEND " + name
    m = N.arm_metrics(R, F3, name, LG[name], DG[name], mtm[name]["legacy"])
    L = LG[name]
    m.update(missing=int(mtm[name]["legacy"]["missing"]), n_distinct=int(L.drop_duplicates(["sym", "start"]).shape[0]),
             sum_pnl=float(L["pnl"].sum()))
    M[name] = m
# V1: k1 vs ISO_RISK OFF
iso = json.load(open(I.D + "/iso_tab2.json"))["per_key"]
for s in S:
    a, b = M["k1_" + s], iso["OFF_" + s]
    log.info("V1 %s cagr22 %.4f/%.4f dd22 %.4f/%.4f", s, a["cagr22"], b["cagr22"], a["dd_mtm22"], b["dd_mtm22"])
F = ("n_per_year", "n_distinct", "sum_pnl", "cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "missing")
out = {"groups": {}, "metrics": M}
for kk, gs in GROUPS.items():
    if kk == "k1":
        continue
    for g in gs:
        name = "%s_%s" % (kk, "+".join(g))
        bl = M[name]
        mem = {f: float(np.mean([M["k1_" + s][f] for s in g])) for f in F}
        dlt = {f: bl[f] - mem[f] for f in F}
        out["groups"][name] = dict(blend={f: bl[f] for f in F}, members_mean=mem, delta=dlt)
        log.info("G %-30s blend: n/y %.0f distinct %d PnL %.0f CAGR22 %.2f DD22 %.2f DDall %.2f Cal %.3f UW %.0f miss %d | "
                 "dDD22 %+.2f dCal %+.3f dCAGR %+.2f", name, bl["n_per_year"], bl["n_distinct"], bl["sum_pnl"], bl["cagr22"],
                 bl["dd_mtm22"], bl["dd_mtm"], bl["calmar22"], bl["uw_mtm22"], bl["missing"], dlt["dd_mtm22"], dlt["calmar22"],
                 dlt["cagr22"])
# chan doan: tuong quan return ngay giua seed, trung chan
ret = pd.DataFrame({s: daily1[s]["equity"].pct_change() for s in S}).loc["2022-01-01":"2024-12-31"].dropna()
c = ret.corr().to_numpy()
log.info("corr ngay giua seed (2022-24): mean %.3f min %.3f", c[np.triu_indices(8, 1)].mean(), c[np.triu_indices(8, 1)].min())
ov = []
for i in range(8):
    for j in range(i + 1, 8):
        a = set(zip(legs1[S[i]]["sym"], legs1[S[i]]["start"]))
        b = set(zip(legs1[S[j]]["sym"], legs1[S[j]]["start"]))
        ov.append(len(a & b) / min(len(a), len(b)))
log.info("trung chan (sym,start) cap seed: mean %.3f min %.3f max %.3f", np.mean(ov), np.min(ov), np.max(ov))
out["diag"] = dict(corr_mean=float(c[np.triu_indices(8, 1)].mean()), overlap_mean=float(np.mean(ov)))
json.dump(out, open(D + "/seed_blend.json", "w"), indent=1, default=float)
