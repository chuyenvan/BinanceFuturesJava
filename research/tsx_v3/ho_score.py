#!/usr/bin/env python3
"""TSX_V3 - HO W9 CHI MO TA (PREREG_TSX_V3 §4-5 (v)). Dau vao: ~/claude_master/tsx_v3/ho_mtm.json tu ecm_mtm_h.py (cung scorer HO4
nhu X14 HO) tren ho4-k24-b-s*, tsx-ho-x14-s*, tsx2-ho-{v420,vt25,vl45}-s*. V2 HO = V0 HO (khong ngay HO nao bi tat -> overrides
trung) -> dPnL = 0 tuyet doi (kiem chuoi ngay). Kiem: X14 HO tai lap = ts_mkt_ext_ho.json. Out: docs/result/tsx_v3/ho.json
"""
import json
import logging
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx3ho")
W3, W2 = "/home/ubuntu/claude_master/tsx_v3", "/home/ubuntu/claude_master/tsx2sim"
OUTD = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/tsx_v3"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
SRC = {"V1": "tsx2-ho-v420-s%d", "V3": "tsx2-ho-vt25-s%d", "V4": "tsx2-ho-vl45-s%d"}


def mmm(v):
    v = np.asarray(v, float)
    return [float(np.median(v)), float(v.min()), float(v.max())] if len(v) else [float("nan")] * 3


def main():
    m = json.load(open(W3 + "/ho_mtm.json"))["runs"]
    FL = json.load(open(W3 + "/flags_v3.json"))["arms"]
    ref = json.load(open("/home/ubuntu/claude_master/tsx/ho/ts_mkt_ext_ho.json"))["rows"]
    chk = {}
    for s in SEEDS:
        x = m["tsx-ho-x14-s%d" % s]["W9"]
        rr = ref[str(s)]["W9"]
        chk[s] = max(abs(x["sum_pnl"] - rr["sum_pnl"][1]), abs(x["roi"] - rr["roi"][1]), abs(x["maxdd"] - rr["maxdd"][1]))
    log.info("KIEM X14 HO tai lap max|d| %.3g", max(chk.values()))
    assert max(chk.values()) < 1e-6, chk
    v2_same = FL["V2"]["ho"]["ranges"] == FL["V0"]["ho"]["ranges"] and FL["V2"]["ext_hours"] == FL["V0"]["ext_hours"]
    assert v2_same, "V2 HO khac V0 -> phai chay kernel"
    out = dict(check_x14=chk, v2_ho_identical_v0=v2_same, arms={})
    for arm in ("V1", "V2", "V3", "V4"):
        rows = {}
        for s in SEEDS:
            rx = json.load(open("/home/ubuntu/claude_master/tsx/ho/res_tsx-ho-x14-s%d.json" % s))
            x, b = m["tsx-ho-x14-s%d" % s], m["ho4-k24-b-s%d" % s]
            if arm == "V2":
                v, dv = x, rx["tsx"][3] if len(rx["tsx"]) == 5 else rx["tsx"][1]
            else:
                t = SRC[arm] % s
                rj = json.load(open(W2 + "/res_%s.json" % t))
                if not rj["passed"] or t not in m:
                    log.error("VOID/thieu %s", t)
                    continue
                v, dv = m[t], rj["tsx"][3]
            rows[s] = {w: {k: [b[w][k], x[w][k], v[w][k]] for k in ("sum_pnl", "roi", "maxdd", "n")} for w in ("W9", "Q1", "Q2", "Q3")}
            rows[s]["defer"] = [rx["tsx"][3] if len(rx["tsx"]) == 5 else rx["tsx"][1], dv]
        d = lambda w, k: [rows[s][w][k][2] - rows[s][w][k][1] for s in rows]  # noqa: E731
        agg = dict(n=len(rows), dPnL=mmm(d("W9", "sum_pnl")), dROI=mmm(d("W9", "roi")), dMaxDD=mmm(d("W9", "maxdd")),
                   dN=mmm(d("W9", "n")), n_ge0=int(sum(x_ >= 0 for x_ in d("W9", "sum_pnl"))) if len(rows) == 8 else None,
                   n_pos=int(sum(x_ > 0 for x_ in d("W9", "sum_pnl"))),
                   mean_dPnL=float(np.mean(d("W9", "sum_pnl"))), mean_dROI=float(np.mean(d("W9", "roi"))),
                   worst_dd=[min(rows[s]["W9"]["maxdd"][1] for s in rows), min(rows[s]["W9"]["maxdd"][2] for s in rows)],
                   q={q: mmm(d(q, "sum_pnl")) for q in ("Q1", "Q2", "Q3")},
                   defer=[mmm([rows[s]["defer"][0] for s in rows]), mmm([rows[s]["defer"][1] for s in rows])],
                   roi_v0=mmm([rows[s]["W9"]["roi"][1] for s in rows]), roi_v=mmm([rows[s]["W9"]["roi"][2] for s in rows]),
                   pnl_seed={s: d("W9", "sum_pnl")[i] for i, s in enumerate(rows)})
        out["arms"][arm] = dict(agg=agg, rows=rows)
        log.info("HO %s n=%d dPnL %s (>=0 %s/8, >0 %d) dROI %s dMaxDD %s worstDD v0/v %s defer %s Q %s", arm, agg["n"], agg["dPnL"],
                 agg["n_ge0"], agg["n_pos"], agg["dROI"], agg["dMaxDD"], agg["worst_dd"], agg["defer"], agg["q"])
    json.dump(out, open(OUTD + "/ho.json", "w"), indent=1, default=str)
    log.info("WROTE %s/ho.json", OUTD)


if __name__ == "__main__":
    main()
