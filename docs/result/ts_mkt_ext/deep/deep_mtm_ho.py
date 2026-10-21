#!/usr/bin/env python3
"""TS_MKT_EXT DEEP - buoc A (HO): MTM phut W9 bang dung ham ecm_mtm_h / ho4_score_a (gia Vision), GHI LAI equity phut.
Tu kiem: W9/Q1..Q3 n, sum_pnl, roi, maxdd == tsx/ho/ho_mtm.json. Out: deep_cache/eq_ho.npz + mtm_check_ho.json
"""
import json
import logging
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ecm_mtm_h as E  # noqa: E402

SA = E.SA
log = logging.getLogger("deep_mtm_ho")
C = "/home/ubuntu/claude_master/tsx/deep_cache"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
TAGS = ["ho4-k24-b-s%d" % s for s in SEEDS] + ["tsx-ho-x14-s%d" % s for s in SEEDS]


def main():
    W = SA.W
    W["dry"], W["DL"] = False, "20260930"
    WINS = E.WINS
    W["T0"] = min(SA.ms_local(v[0]) for v in WINS.values())
    W["NW"] = (max(SA.ms_local(v[1]) for v in WINS.values()) - W["T0"]) // 60000
    W["win"] = {k: (int((SA.ms_local(a) - W["T0"]) // 60000), int((SA.ms_local(b) - SA.ms_local(a)) // 60000),
                    int((SA.ms_local(b) - SA.ms_local(a)) // 86400000), SA.pd.Timestamp(a).normalize())
                for k, (a, b) in WINS.items()}
    D, UPS, RJ = {}, {}, {}
    for t in TAGS:
        D[t], _ = SA.load(t)
        UPS[t] = SA.updates(t)
        RJ[t] = json.load(open(SA.OUT + t + "/result.json"))
    NE = W["NW"]
    for t in TAGS:
        ls = [u for u in UPS[t] if u[0][:8] == str(RJ[t].get("date_last"))]
        if ls:
            NE = max(NE, (ls[-1][1] - W["T0"]) // 60000 + 1)
    W["NE"] = int(min(NE, W["NW"] + 2 * 1440))
    U, mt = SA.build(TAGS, D, 8)
    ref = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_mtm.json"))["runs"]
    arrs, chk = {}, {}
    for i, t in enumerate(TAGS):
        eq = SA.equity(D[t], RJ[t]["equity_start"], U[i])
        arrs[t] = eq.astype(np.float64)
        dif = 0.0
        for wk in WINS:
            m, _ = SA.metr(D[t], eq, wk)
            for k in ("n", "sum_pnl", "roi", "maxdd"):
                dif = max(dif, abs(float(m[k]) - float(ref[t][wk][k])))
        chk[t] = dict(max_abs_diff_vs_ref=dif, U_open_legmin=int(mt["legmin"]))
        log.info("CHK %s diff=%.3g", t, dif)
    arrs["__T0"] = np.array([W["T0"]], np.int64)
    np.savez(C + "/eq_ho.npz", **arrs)
    ok = mt["miss"] == 0 and all(c["max_abs_diff_vs_ref"] < 1e-6 for c in chk.values())
    json.dump(dict(T0=int(W["T0"]), NE=W["NE"], mtm_check={k: v for k, v in mt.items() if k != "tail"}, check=chk, ok=ok),
              open(C + "/mtm_check_ho.json", "w"), indent=1, default=str)
    log.info("DONE ok=%s miss=%s", ok, mt["miss"])


if __name__ == "__main__":
    main()
