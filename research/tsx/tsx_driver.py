#!/usr/bin/env python3
"""TS_MKT_EXT driver (PREREG_TS_MKT_EXT). Tai dung ha tang burst_cooldown_driver (monkeypatch hang so).
Usage: jards | p0 | orch2 [--cpu 5 --gpu 2] | parity | score
"""
import argparse
import json
import logging
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import burst_cooldown_driver as B  # noqa: E402

GA, G = B.GA, B.G
log = logging.getLogger("tsx")
D = "/home/ubuntu/claude_master/tsx"
FLAGS = json.load(open(D + "/flags.json"))
CODE_SHA = open(D + "/code_sha.txt").read().strip() if os.path.exists(D + "/code_sha.txt") else "nocode"
OV_ON = dict(B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=FLAGS["ranges"])
T995 = 3.499483
SEEDS = B.SEEDS
OFF = B.OFF

B.D = D
B.JAR_DS = "sim-jar-tsx"
B.CODE_SHA = CODE_SHA
B.P0_TAG = "tsx-p0"
B.GPU_CHK = "tsx-gpuchk-s7"
B.ARMS = {"X14": None}
B.tag_on = lambda arm, s: "tsx-%s-%s" % (arm.lower(), s.lower())
B.ov_on = lambda arm: dict(OV_ON)


def parity():
    res = {}
    for s in SEEDS:
        t = B.tag_on("X14", s)
        if not os.path.exists(GA.OUT % t + "storage/printDone.csv"):
            continue
        rj, pr, txt = GA.result_json(t), GA.prof_run(t), B.logtxt(t)
        m = re.findall(r"\[TSX\] extHours=(\d+) extDays=(\d+) deferTicks=(\d+) deferClusters=(\d+) cutAfterDefer=(\d+)", txt)
        chk = dict(jar=rj.get("jar_sha256") == B.jar_sha(), ok=rj.get("ok") is True,
                   topk24=pr.get("SELECTOR_RANK_TOPK") == "24", skipfull=pr.get(G.KEY) == "true",
                   key=pr.get("SIM_LOSER_TS_EXT_HOURS") == "336" and pr.get("SIM_LOSER_TS_EXT_DAYS") == FLAGS["ranges"],
                   log=bool(m) and m[-1][0] == "336" and int(m[-1][1]) == FLAGS["n_days"],
                   b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()))
        res[t] = dict(ok=all(chk.values()), checks=chk, n=rj.get("n_trades"), eq=rj.get("equity_final"),
                      tsx=[int(x) for x in m[-1][2:]] if m else None)
        log.info("PARITY %-16s %s n=%s eq=%s tsx(deferTicks,clusters,cutAfter)=%s %s", t,
                 "PASS" if res[t]["ok"] else "*** VOID ***", res[t]["n"], res[t]["eq"], res[t]["tsx"], chk)
    json.dump(res, open(D + "/parity.json", "w"), indent=1)
    return res


B.parity_on = parity


def p0():
    r = B.p0_check()
    pr = GA.prof_run(B.P0_TAG) if os.path.exists(GA.OUT % B.P0_TAG + "storage/printDone.csv") else {}
    r["tsx_key_absent"] = "SIM_LOSER_TS_EXT_HOURS" not in pr
    r["ok"] = bool(r.get("ok") and r["tsx_key_absent"])
    json.dump(r, open(D + "/p0.json", "w"), indent=1)
    log.info("P0 %s", r)
    return r


def score(a):
    sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
    import gvz_mtm as MT  # noqa: F401  (patch R -> Vision)
    import reset_rule_score as R
    import flat3_crashpen_driver as F3
    import n700_driver as N
    assert R._work is MT._work_vision
    assert p0()["ok"], "P0 chua PASS"
    par = parity()
    keys = {"OFF_" + s: OFF[s] for s in SEEDS}
    for s in SEEDS:
        t = B.tag_on("X14", s)
        if par.get(t, {}).get("ok"):
            keys["X14_" + s] = t
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "TS_MKT_EXT " + k
    legs = {k: R.load_legs(t) for k, t in keys.items()}
    daily = {k: R.load_daily(t) for k, t in keys.items()}
    md5 = {k: R.md5_of(t) for k, t in keys.items()}
    mf = D + "/mtm_vision.json"
    raw = json.load(open(mf)) if os.path.exists(mf) else {}
    iso = json.load(open("/home/ubuntu/claude_master/iso/mtm_vision.json"))
    for s in SEEDS:
        k = "OFF_" + s
        if k not in raw and iso.get(k, {}).get("md5") == md5[k]:
            raw[k] = iso[k]
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM can tinh: %s", sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=3, chunk=30)
        for k, v in new.items():
            v["md5"] = md5[k]
            raw[k] = v
        json.dump(raw, open(mf, "w"))
    assert all(raw[k]["legacy"]["missing"] == 0 for k in keys), "MTM thieu gia"
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"]) for k in keys}
    ok = [s for s in SEEDS if "X14_" + s in M]
    n = len(ok)
    on = lambda s, f: M["X14_" + s][f]  # noqa: E731
    off = lambda s, f: M["OFF_" + s][f]  # noqa: E731
    dcg = np.array([on(s, "cagr22") - off(s, "cagr22") for s in ok])
    ddd = np.array([on(s, "dd_mtm22") - off(s, "dd_mtm22") for s in ok])
    dny = np.array([on(s, "n_per_year") / off(s, "n_per_year") - 1 for s in ok])
    hw = T995 * dcg.std(ddof=1) / math.sqrt(n) if n == 8 else float("nan")
    yrs = {}
    for y in (2022, 2023, 2024, 2025):
        yrs[y] = float(np.mean([on(s, "per_year")[y]["sum_pnl"] - off(s, "per_year")[y]["sum_pnl"] for s in ok]))
    rule = dict(G1=dict(mean=float(dcg.mean()), ci99=[float(dcg.mean() - hw), float(dcg.mean() + hw)],
                        ok=bool(n == 8 and dcg.mean() > 0 and dcg.mean() - hw > 0)),
                G2=dict(dDD=float(ddd.mean()), worst=float(min(on(s, "dd_mtm") for s in ok)),
                        ok=bool(n == 8 and ddd.mean() >= -3 and all(abs(on(s, "dd_mtm")) <= 40 for s in ok))),
                G3=dict(per_year=yrs, pos=int(sum(v > 0 for v in yrs.values())), ok=bool(sum(v > 0 for v in yrs.values()) >= 3)),
                G4=dict(dn=float(dny.mean()), ok=bool(dny.mean() >= -0.05)))
    rule["GO"] = all(rule[g]["ok"] for g in ("G1", "G2", "G3", "G4"))
    agg = {}
    for arm in ("OFF", "X14"):
        agg[arm] = {f: float(np.mean([M[arm + "_" + s][f] for s in ok]))
                    for f in ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "n_per_year", "sum_pnl")}
        log.info("AGG %s %s", arm, {k: round(v, 2) for k, v in agg[arm].items()})
    for s in ok:
        log.info("ROW %-5s CAGR22 %.2f->%.2f DD22 %.2f->%.2f Cal %.3f->%.3f UW %.0f->%.0f PnL %.0f->%.0f tsx %s", s,
                 off(s, "cagr22"), on(s, "cagr22"), off(s, "dd_mtm22"), on(s, "dd_mtm22"), off(s, "calmar22"),
                 on(s, "calmar22"), off(s, "uw_mtm22"), on(s, "uw_mtm22"), off(s, "sum_pnl"), on(s, "sum_pnl"),
                 par[B.tag_on("X14", s)]["tsx"])
    # mo ta: chan giu qua 168h
    ext = []
    for s in ok:
        L = R.load_legs_minute(legs["X14_" + s])
        h = (L["m1"] - L["m0"]) / 60.0
        x = L[h > 168.5]
        ext.append(dict(n=int(len(x)), pnl=float(x["pnl"].sum()), win=int((x["pnl"] > 0).sum()),
                        ts_cut=int((x["status"].astype(str) == "STOP_LOSS_DONE").sum())))
    desc = {k: float(np.mean([e[k] for e in ext])) for k in ext[0]}
    log.info("CHAN GIU >168h (TB/seed): %s", desc)
    log.info("RULE %s", json.dumps(rule))
    json.dump(dict(prereg_commit=open(D + "/prereg_commit.txt").read().strip(), jar_sha=B.jar_sha(), rule=rule, agg=agg,
                   extended_legs=desc, parity=par, rows={s: {f: [off(s, f), on(s, f)] for f in
                   ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "n_per_year", "sum_pnl")} for s in ok}),
              open(D + "/ts_mkt_ext.json", "w"), indent=1, default=float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--cpu", type=int, default=5)
    ap.add_argument("--gpu", type=int, default=2)
    ap.add_argument("--no-p0-push", action="store_true")
    a = ap.parse_args()
    if a.cmd == "jards":
        B.jards(a)
    elif a.cmd == "p0":
        B.push(B.P0_TAG, dict(B.OV_BASE), "A1")
    elif a.cmd == "p0wait":
        ks = GA.ks_mod()
        log.info("P0 status %s", ks.wait([ks.kernel_ref(B.P0_TAG)]))
        ks.fetch(B.P0_TAG)
        p0()
    elif a.cmd == "orch2":
        assert p0()["ok"], "P0 chua PASS"
        B.orch2(a)
    elif a.cmd == "parity":
        parity()
    elif a.cmd == "score":
        score(a)


if __name__ == "__main__":
    main()
