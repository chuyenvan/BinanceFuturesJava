#!/usr/bin/env python3
"""TSX_V2_SIM - HO W9 CHI MO TA (PREREG_TSX_V2_SIM §5). Dau vao: ho_mtm.json tu ecm_mtm_h.py (cung scorer HO4 nhu X14 HO).
So bien the vs tsx-ho-x14-s* theo seed: dPnL / dROI / dmaxDD W9 (+ Q1-Q3), so cum hoan (log Java). Kiem: X14 HO tai lap
= ts_mkt_ext_ho.json (sum_pnl/roi/maxdd W9). Out: docs/result/tsx_v2_sim/ho.json
"""
import json
import logging
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx2ho")
W = "/home/ubuntu/claude_master/tsx2sim"
OUTD = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/tsx_v2_sim"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
ARMS = ["V336", "V420", "VT25", "VL45"]


def mmm(v):
    v = np.asarray(v, float)
    return [float(np.median(v)), float(v.min()), float(v.max())]


def main():
    m = json.load(open(W + "/ho_mtm.json"))["runs"]
    ref = json.load(open("/home/ubuntu/claude_master/tsx/ho/ts_mkt_ext_ho.json"))["rows"]
    chk = {}
    for s in SEEDS:
        x = m["tsx-ho-x14-s%d" % s]["W9"]
        rr = ref[str(s)]["W9"]
        chk[s] = max(abs(x["sum_pnl"] - rr["sum_pnl"][1]), abs(x["roi"] - rr["roi"][1]), abs(x["maxdd"] - rr["maxdd"][1]))
    log.info("KIEM X14 HO tai lap max|d| %.3g", max(chk.values()))
    assert max(chk.values()) < 1e-6, chk
    out = dict(check_x14=chk, arms={})
    for arm in ARMS:
        rows = {}
        for s in SEEDS:
            t = "tsx2-ho-%s-s%d" % (arm.lower(), s)
            if t not in m:
                log.error("thieu %s", t)
                continue
            rj = json.load(open(W + "/res_%s.json" % t))
            if not rj["passed"]:
                log.error("VOID %s", t)
                continue
            rx = json.load(open("/home/ubuntu/claude_master/tsx/ho/res_tsx-ho-x14-s%d.json" % s))
            x, v, b = m["tsx-ho-x14-s%d" % s], m[t], m["ho4-k24-b-s%d" % s]
            rows[s] = {w: {k: [b[w][k], x[w][k], v[w][k]] for k in ("sum_pnl", "roi", "maxdd", "n")} for w in ("W9", "Q1", "Q2", "Q3")}
            rows[s]["defer"] = [rx["tsx"][3], rj["tsx"][3]]
            rows[s]["eqcheck"] = v["eqcheck"]
        d = lambda w, k: [rows[s][w][k][2] - rows[s][w][k][1] for s in rows]  # noqa: E731
        agg = dict(n=len(rows), dPnL=mmm(d("W9", "sum_pnl")), dROI=mmm(d("W9", "roi")), dMaxDD=mmm(d("W9", "maxdd")),
                   dN=mmm(d("W9", "n")), n_dPnL_pos=int(sum(x > 0 for x in d("W9", "sum_pnl"))),
                   mean_dPnL=float(np.mean(d("W9", "sum_pnl"))), mean_dROI=float(np.mean(d("W9", "roi"))),
                   mean_dMaxDD=float(np.mean(d("W9", "maxdd"))),
                   worst_dd=[min(rows[s]["W9"]["maxdd"][1] for s in rows), min(rows[s]["W9"]["maxdd"][2] for s in rows)],
                   q=dict((q, mmm(d(q, "sum_pnl"))) for q in ("Q1", "Q2", "Q3")),
                   defer=[mmm([rows[s]["defer"][0] for s in rows]), mmm([rows[s]["defer"][1] for s in rows])],
                   roi_x14=mmm([rows[s]["W9"]["roi"][1] for s in rows]), roi_v=mmm([rows[s]["W9"]["roi"][2] for s in rows]))
        out["arms"][arm] = dict(agg=agg, rows=rows)
        log.info("HO %s n=%d dPnL %s (%d/8 >0) dROI %s dMaxDD %s worstDD x14/v %s defer %s Q %s", arm, agg["n"], agg["dPnL"],
                 agg["n_dPnL_pos"], agg["dROI"], agg["dMaxDD"], agg["worst_dd"], agg["defer"], agg["q"])
    json.dump(out, open(OUTD + "/ho.json", "w"), indent=1, default=str)
    log.info("WROTE %s/ho.json", OUTD)


if __name__ == "__main__":
    main()
