#!/usr/bin/env python3
"""ISO_RISK bang cho owner (legs, PnL) + cham lai BURST_COOLDOWN V2/V3 bang MTM Vision (addendum 1)."""
import json
import logging
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402,F401
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import iso_risk_driver as I  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tab")
B = I.B
import reset_rule_score as R  # noqa: E402
import flat3_crashpen_driver as F3  # noqa: E402
import n700_driver as N  # noqa: E402

raw = json.load(open(I.D + "/mtm_vision.json"))
keys = {}
for s in I.SEEDS:
    keys["OFF_" + s] = I.OFF[s]
    for arm in ("V1", "V2", "V3"):
        keys["R1" + arm + "_" + s] = B.tag_on(arm, s)
    for arm in I.ARMS:
        keys[arm + "_" + s] = I.tag(arm, s)
legs = {k: R.load_legs(t) for k, t in keys.items()}
miss = {k: legs[k] for k in keys if k not in raw}
log.info("can tinh MTM Vision: %s", sorted(miss))
if miss:
    new = R.run_mtm(miss, workers=3, chunk=30)
    for k, v in new.items():
        v["md5"] = R.md5_of(keys[k])
        raw[k] = v
    json.dump(raw, open(I.D + "/mtm_vision.json", "w"))
out = {}
for k, t in keys.items():
    N.TAG[k], N.DESC[k] = t, "ISO_RISK " + k
    m = N.arm_metrics(R, F3, k, legs[k], R.load_daily(t), raw[k]["legacy"])
    L = legs[k]
    m.update(n_legs=int(len(L)), sum_pnl=float(L["pnl"].sum()), missing=int(raw[k]["legacy"]["missing"]))
    out[k] = m
order = ["OFF", "R1V1", "R1V2", "R1V3", "B15", "V1S2", "V1S3", "V1S4", "V1K32"]
tab = {}
for arm in order:
    rows = [out[arm + "_" + s] for s in I.SEEDS]
    g = lambda f: np.array([r[f] for r in rows], float)  # noqa: E731
    tab[arm] = dict(n_per_year=g("n_per_year").mean(), n_legs=g("n_legs").mean(), sum_pnl=g("sum_pnl").mean(),
                    sum_pnl_sd=g("sum_pnl").std(ddof=1), cagr22=g("cagr22").mean(), dd_mtm22=g("dd_mtm22").mean(),
                    dd_mtm=g("dd_mtm").mean(), worst_dd=g("dd_mtm").min(), calmar22=g("calmar22").mean(),
                    uw22=g("uw_mtm22").mean(), missing=int(g("missing").max()))
    log.info("TAB %-5s %s", arm, " ".join("%s=%.2f" % (a, b) for a, b in tab[arm].items()))
# Calmar so voi OFF tung seed (ghep cap) cho R1V1..V3 va cac arm
for arm in order[1:]:
    d = np.array([out[arm + "_" + s]["calmar22"] - out["OFF_" + s]["calmar22"] for s in I.SEEDS])
    hw = I.T995_DF7 * d.std(ddof=1) / np.sqrt(8)
    log.info("dCAL %-5s mean %.3f CI99 [%.3f, %.3f] pos %d/8", arm, d.mean(), d.mean() - hw, d.mean() + hw, int((d > 0).sum()))
json.dump(dict(per_key=out, table=tab), open(I.D + "/iso_tab2.json", "w"), indent=1, default=float)
