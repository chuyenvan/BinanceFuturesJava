#!/usr/bin/env python3
"""TSX_V3_JAVA - HO 2026 W9 CHI MO TA (PREREG_TSX_V3_JAVA §4-§5). Dau vao: ~/claude_master/tsx_v3_java/ho_mtm.json tu ecm_mtm_h.py
(cung scorer HO4 nhu X14 HO) tren ho4-k24-b-s*, tsx-ho-x14-s*, tsx2-ho-{vt25,vl45,v420}-s*. Kiem: X14 HO tai lap = ts_mkt_ext_ho.json;
parity res_*.json passed + khoa = flags.json. Out: docs/result/tsx_v3_java/ho.json
"""
import json
import logging
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx3j_ho")
WJ, W2 = "/home/ubuntu/claude_master/tsx_v3_java", "/home/ubuntu/claude_master/tsx2sim"
OUTD = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/tsx_v3_java"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
SRC = {"C420": "tsx2-ho-v420-s%d", "T25": "tsx2-ho-vt25-s%d", "L45": "tsx2-ho-vl45-s%d"}


def mmm(v):
    v = np.asarray(v, float)
    return [float(np.median(v)), float(v.min()), float(v.max())] if len(v) else [float("nan")] * 3


def main():
    m = json.load(open(WJ + "/ho_mtm.json"))["runs"]
    FL = json.load(open(WJ + "/flags.json"))["arms"]
    ref = json.load(open("/home/ubuntu/claude_master/tsx/ho/ts_mkt_ext_ho.json"))["rows"]
    chk = {}
    for s in SEEDS:
        x = m["tsx-ho-x14-s%d" % s]["W9"]
        rr = ref[str(s)]["W9"]
        chk[s] = max(abs(x["sum_pnl"] - rr["sum_pnl"][1]), abs(x["roi"] - rr["roi"][1]), abs(x["maxdd"] - rr["maxdd"][1]))
    log.info("KIEM X14 HO tai lap max|d| %.3g", max(chk.values()))
    assert max(chk.values()) < 1e-6, chk
    out = dict(check_x14=chk, arms={}, void=[])
    for arm in ("C420", "T25", "L45"):
        rows = {}
        for s in SEEDS:
            rx = json.load(open("/home/ubuntu/claude_master/tsx/ho/res_tsx-ho-x14-s%d.json" % s))
            x = m["tsx-ho-x14-s%d" % s]
            t = SRC[arm] % s
            try:
                rj = json.load(open(W2 + "/res_%s.json" % t))
            except FileNotFoundError:
                rj = {"passed": False}
            pr = T.GA.prof_run(t) if rj.get("passed") else {}
            kok = pr.get("SIM_LOSER_TS_EXT_DAYS") == FL[arm]["ho"]["ranges"] and pr.get("SIM_LOSER_TS_EXT_HOURS") == str(FL[arm]["ext_hours"])
            if not rj.get("passed") or not kok or t not in m:
                log.error("VOID/thieu %s passed=%s key=%s", t, rj.get("passed"), kok)
                out["void"].append(t)
                continue
            v = m[t]
            rows[s] = {w: {k: [x[w][k], v[w][k]] for k in ("sum_pnl", "roi", "maxdd", "n")} for w in ("W9", "Q1", "Q2", "Q3")}
            rows[s]["defer"] = [rx["tsx"][3] if len(rx["tsx"]) == 5 else rx["tsx"][1], rj["tsx"][3]]
            rows[s]["n_leg_total"] = [rx.get("n"), rj.get("n")]
        d = lambda w, k: [rows[s][w][k][1] - rows[s][w][k][0] for s in rows]  # noqa: E731
        agg = dict(n=len(rows), dPnL=mmm(d("W9", "sum_pnl")), dROI=mmm(d("W9", "roi")), dMaxDD=mmm(d("W9", "maxdd")),
                   dN=mmm(d("W9", "n")), n_ge0=int(sum(x_ >= 0 for x_ in d("W9", "sum_pnl"))),
                   n_dd_ge0=int(sum(x_ >= 0 for x_ in d("W9", "maxdd"))),
                   worst_dd=[min(rows[s]["W9"]["maxdd"][0] for s in rows), min(rows[s]["W9"]["maxdd"][1] for s in rows)] if rows else None,
                   q={q: mmm(d(q, "sum_pnl")) for q in ("Q1", "Q2", "Q3")},
                   defer=[mmm([rows[s]["defer"][0] for s in rows]), mmm([rows[s]["defer"][1] for s in rows])],
                   roi_x14=mmm([rows[s]["W9"]["roi"][0] for s in rows]), roi_v=mmm([rows[s]["W9"]["roi"][1] for s in rows]),
                   dd_x14=mmm([rows[s]["W9"]["maxdd"][0] for s in rows]), dd_v=mmm([rows[s]["W9"]["maxdd"][1] for s in rows]),
                   pnl_seed={s: rows[s]["W9"]["sum_pnl"][1] - rows[s]["W9"]["sum_pnl"][0] for s in rows})
        out["arms"][arm] = dict(agg=agg, rows=rows)
        log.info("HO %s n=%d dPnL %s (>=0 %d/8) dROI %s dMaxDD %s worstDD x14/v %s defer %s dN %s", arm, agg["n"], agg["dPnL"],
                 agg["n_ge0"], agg["dROI"], agg["dMaxDD"], agg["worst_dd"], agg["defer"], agg["dN"])
    json.dump(out, open(OUTD + "/ho.json", "w"), indent=1, default=str)
    log.info("WROTE %s/ho.json", OUTD)


if __name__ == "__main__":
    main()
