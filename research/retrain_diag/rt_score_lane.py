#!/usr/bin/env python3
"""rt_score_lane.py - cham MO TA lane U4a (PREREG_RETRAIN_DIAG 436977c1 muc 2.1/2.4; HOLDOUT_UNSEAL_2026_1121 (U4a)).
Dinh nghia = SCORE_DEFS_L5 qua rt_score_n.lane() (khong sua). Seed a1, s123 (P1). Lane: LLL (ho5 Lane L), P/S/M (out/lane/sim), NNN (Lane N).
Quy ket 2.4: Delta_X = mean_seed(ROI_D5 X - ROI_D5 LLL) (pp); Delta_tot = NNN - LLL (cung 2 seed); tuong tac = Delta_tot - sum Delta_X;
X 'nguyen nhan chinh' <=> sign(Delta_X) == sign(Delta_tot) VA |Delta_X| >= 0,5 |Delta_tot|. Mo ta: lenh chung (sym,start) voi L, PnL nhom chung vs
chi-o-lane (theo PnL tung lenh, start trong Q3), theo thang, pass gate theo quy (out/diag/DGATE_*.json).
Usage: rt_score_lane.py selftest | score --allow-pnl"""
import datetime as dt, json, logging, os, sys
import numpy as np
sys.path.insert(0, "/home/ubuntu/claude_master/w3/retrain/work/score")
import rt_score_n as RS  # noqa: E402
S = RS.S
L = logging.getLogger("rtlane")
L.info("HOLDOUT_UNSEAL_REF HOLDOUT_UNSEAL_2026_1121 (U4a)")
SEEDS = ["a1", "s123"]
DIRS = {"LLL": "/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-%s", "NNN": "/home/ubuntu/claude_master/w3/retrain/out/nsim/rt-n-l26-%s",
        "P": "/home/ubuntu/claude_master/w3/retrain/out/lane/sim/rt-p-l26-%s", "S": "/home/ubuntu/claude_master/w3/retrain/out/lane/sim/rt-s-l26-%s",
        "M": "/home/ubuntu/claude_master/w3/retrain/out/lane/sim/rt-m-l26-%s",
        "PS": "/home/ubuntu/claude_master/w3/retrain/out/lane/sim/rt-ps-l26-%s", "PM": "/home/ubuntu/claude_master/w3/retrain/out/lane/sim/rt-pm-l26-%s",
        "SM": "/home/ubuntu/claude_master/w3/retrain/out/lane/sim/rt-sm-l26-%s"}
OUT = "/home/ubuntu/claude_master/w3/retrain/out/score/score_lanes_U4a.json"
Q3a, Q3b = S.day("2026-07-01"), S.day("2026-09-30") + dt.timedelta(days=1)


def trades(d):
    out = {}
    for x in S.rows(d):
        st = S.F(x["start"])
        if Q3a <= st < Q3b:
            out[(x["symbol"] if "symbol" in x else x.get("sym"), x["start"])] = float(x["pnl"])
    return out


def checks(lanes):
    for s in SEEDS:
        assert json.load(open(DIRS["LLL"] % s + "/check_l5.json"))["PASS"] is True
        assert json.load(open(DIRS["NNN"] % s + "/check_n.json"))["PASS"] is True
        for x in lanes:
            if x in ("P", "S", "M", "PS", "PM", "SM"):
                assert json.load(open(DIRS[x] % s + "/check_lane.json"))["PASS"] is True, (x, s)


def run(lanes, dirs, tag):
    res = {"tag": tag, "seeds": SEEDS, "lanes": {}}
    tl = {s: trades(dirs["LLL"] % s) for s in SEEDS}
    for x in lanes:
        R = res["lanes"][x] = {"seeds": {}}
        for s in SEEDS:
            m = RS.lane(dirs[x], s); m.pop("keys_q3", None)
            t = trades(dirs[x] % s); c = set(t) & set(tl[s])
            m["trades_q3"] = len(t); m["common_with_L"] = len(c)
            m["pnl_common"] = sum(t[k] for k in c); m["pnl_lane_only"] = sum(v for k, v in t.items() if k not in c)
            m["pnl_L_only_missing"] = sum(v for k, v in tl[s].items() if k not in c)
            R["seeds"][s] = m
        g = R["seeds"]
        R["mean"] = {k: float(np.mean([g[s][k] for s in SEEDS])) for k in ("roi_q3_d5", "sum_pnl", "trades_q3", "common_with_L", "pnl_common", "pnl_lane_only",
                                                                         "pnl_L_only_missing", "maxdd")}
        R["mean"]["roi_q3_d5_pct"] = 100 * R["mean"]["roi_q3_d5"]
        R["by_month"] = {nm: {"n_start": float(np.mean([g[s]["split"][nm]["n_start"] for s in SEEDS])),
                              "sum_pnl_end": float(np.mean([g[s]["split"][nm]["sum_pnl_end"] for s in SEEDS]))} for nm in ("07", "08", "09", "0701-0709", "0710-0930")}
    if all(k in res["lanes"] for k in ("LLL", "NNN", "P", "S", "M")):
        r = {x: res["lanes"][x]["mean"]["roi_q3_d5_pct"] for x in res["lanes"]}
        tot = r["NNN"] - r["LLL"]; dX = {x: r[x] - r["LLL"] for x in ("P", "S", "M")}
        res["attribution"] = {"delta_tot_pp": tot, "delta_pp": dX, "interaction_pp": tot - sum(dX.values()),
                              "share": {x: (dX[x] / tot if tot else None) for x in dX},
                              "main_cause": [x for x in dX if tot != 0 and np.sign(dX[x]) == np.sign(tot) and abs(dX[x]) >= 0.5 * abs(tot)]}
        res["attribution"]["any_single_ge_50pct"] = bool(res["attribution"]["main_cause"])
    if all(k in res["lanes"] for k in ("PS", "PM", "SM")):  # [P2] MO TA (khong luat): Shapley 3 model tren 8 lane
        import itertools, math
        r = {x: res["lanes"][x]["mean"]["roi_q3_d5_pct"] for x in res["lanes"]}
        v = lambda S_: r[{"": "LLL", "P": "P", "S": "S", "M": "M", "PS": "PS", "PM": "PM", "SM": "SM", "PSM": "NNN"}["".join(c for c in "PSM" if c in S_)]]
        sh = {}
        for x in "PSM":
            o = [y for y in "PSM" if y != x]; t = 0.0
            for k in range(3):
                for C in itertools.combinations(o, k):
                    w = math.factorial(k) * math.factorial(2 - k) / 6.0
                    t += w * (v(set(C) | {x}) - v(set(C)))
            sh[x] = t
        res["shapley_desc_pp"] = sh
        res["pair_interaction_desc_pp"] = {pq: r[pq] - r[pq[0]] - r[pq[1]] + r["LLL"] for pq in ("PS", "PM", "SM")}
    json.dump(res, open(OUT if tag == "U4a" else OUT.replace(".json", "_%s.json" % tag), "w"), indent=1, default=str)
    return res


if __name__ == "__main__":
    if sys.argv[1] == "selftest":   # moi lane := LLL -> delta 0, chung = toan bo
        d = {k: DIRS["LLL"] for k in DIRS}
        r = run(["LLL", "NNN", "P", "S", "M"], d, "selftest")
        a = r["attribution"]
        ok = a["delta_tot_pp"] == 0 and all(v == 0 for v in a["delta_pp"].values()) and all(
            r["lanes"]["P"]["seeds"][s]["common_with_L"] == r["lanes"]["P"]["seeds"][s]["trades_q3"] for s in SEEDS)
        L.info("SELFTEST ok=%s roi L=%s", ok, r["lanes"]["LLL"]["mean"]["roi_q3_d5_pct"])
    elif sys.argv[1] == "score" and "--allow-pnl" in sys.argv:
        pairs = [x for x in ("PS", "PM", "SM") if all(os.path.exists(DIRS[x] % s_ + "/check_lane.json") for s_ in SEEDS)]
        checks(["P", "S", "M"] + pairs)
        r = run(["LLL", "NNN", "P", "S", "M"] + pairs, DIRS, "U4a")
        L.info("ATTR %s", json.dumps(r.get("attribution")))
    else:
        raise SystemExit("score can --allow-pnl (chi sau khi muc CO CHE da ghi + sha)")
