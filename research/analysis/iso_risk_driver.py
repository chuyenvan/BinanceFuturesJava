#!/usr/bin/env python3
"""ISO_RISK driver (PREREG_ISO_RISK). Tai dung ha tang burst_cooldown_driver (jar sim-jar-bcd, P0 da PASS).
Usage: check | orch2 [--cpu 5 --gpu 2] | parity | score
"""
import argparse
import json
import logging
import math
import os
import re
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import burst_cooldown_driver as B  # noqa: E402

GA, G = B.GA, B.G
log = logging.getLogger("iso")
D = "/home/ubuntu/claude_master/iso"
SEEDS = B.SEEDS
OFF = B.OFF
R1 = dict(SIM_BURST_COOLDOWN_N=13, SIM_BURST_COOLDOWN_MIN=120)
ARMS = {
    "B15": dict(SIM_F_BASE="0.0225"),
    "V1S2": dict(R1, SIM_F_BASE="0.03"),
    "V1S3": dict(R1, SIM_F_BASE="0.045"),
    "V1S4": dict(R1, SIM_F_BASE="0.06"),
    "V1K32": dict(R1, SELECTOR_RANK_TOPK=32),
}
T995_DF7 = 3.499483
PREREG = "docs/prereg/PREREG_ISO_RISK.md"
PREREG_COMMIT = open(D + "/prereg_commit.txt").read().strip() if os.path.exists(D + "/prereg_commit.txt") else None
JSON_OUT = D + "/iso_risk.json"
MTM_FILE = D + "/mtm.json"


def tag(arm, s):
    return "iso-%s-%s" % (arm.lower(), s.lower())


def ov(arm):
    o = dict(B.OV_BASE)
    o.update(ARMS[arm])
    return o


def check(a=None):
    log.info("prereg_commit %s jar %s profile %s", PREREG_COMMIT, B.jar_sha(), GA.PROFILE)
    for arm in ARMS:
        log.info("ARM %s ov=%s", arm, json.dumps(ov(arm)))
    p0 = B.p0_check()
    assert p0["ok"], "P0 bcd khong PASS"
    assert PREREG_COMMIT, "chua co prereg_commit.txt"


def parity():
    res = {}
    for arm in ARMS:
        for s in SEEDS:
            t = tag(arm, s)
            if not os.path.exists(GA.OUT % t + "storage/printDone.csv"):
                continue
            rj, pr, txt = GA.result_json(t), GA.prof_run(t), B.logtxt(t)
            want = ov(arm)
            keyok = all(str(pr.get(k)) == str(v) for k, v in want.items())
            bc = re.findall(r"\[BURST-COOLDOWN\] N=(\d+) MIN=(\d+) triggers=(\d+) blocked=(\d+)", txt)
            logok = (not arm.startswith("V1")) or (bool(bc) and bc[-1][0] == "13" and bc[-1][1] == "120")
            chk = dict(jar=rj.get("jar_sha256") == B.jar_sha(), ok=rj.get("ok") is True, keys=keyok, log=logok,
                       b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()))
            res[t] = dict(ok=all(chk.values()), checks=chk, n=rj.get("n_trades"), eq=rj.get("equity_final"),
                          triggers=int(bc[-1][2]) if bc else None, blocked=int(bc[-1][3]) if bc else None)
            log.info("PARITY %-16s %s n=%s eq=%s trig=%s blk=%s %s", t, "PASS" if res[t]["ok"] else "*** VOID ***",
                     res[t]["n"], res[t]["eq"], res[t]["triggers"], res[t]["blocked"], chk)
    json.dump(res, open(D + "/parity.json", "w"), indent=1)
    return res


def orch2(a):
    check()
    ks = GA.ks_mod()
    term = ks.TERMINAL
    gchk = B.gpu_ok()
    log.info("GPU-CHK (bcd) = %s", gchk)
    queue, run_cpu, run_gpu = [], [], []
    for s in SEEDS:
        for arm in ARMS:
            t = tag(arm, s)
            if os.path.exists(GA.OUT % t + "storage/printDone.csv"):
                continue
            try:
                st = ks._status(ks.kernel_ref(t))
            except Exception:  # noqa: BLE001
                st = None
            if st in ("RUNNING", "QUEUED"):
                run_cpu.append(t)
            elif st == "COMPLETE":
                ks.fetch(t)
            else:
                queue.append((arm, s))
    log.info("ORCH2 queue=%d running=%s", len(queue), run_cpu)
    while queue or run_cpu or run_gpu:
        while queue and len(run_cpu) < a.cpu:
            arm, s = queue.pop(0)
            B.push(tag(arm, s), ov(arm), s)
            run_cpu.append(tag(arm, s))
            time.sleep(45)
        if gchk:
            for i in range(len(queue) - 1, -1, -1):
                if len(run_gpu) >= a.gpu:
                    break
                arm, s = queue[i]
                if s == "A1":
                    continue
                queue.pop(i)
                B.push_gpu(tag(arm, s), ov(arm), s)
                run_gpu.append(tag(arm, s))
                time.sleep(45)
        time.sleep(120)
        for lst in (run_cpu, run_gpu):
            for t in list(lst):
                try:
                    st = ks._status(ks.kernel_ref(t))
                except Exception as e:  # noqa: BLE001
                    log.info("status %s loi %s", t, e)
                    continue
                if st in term:
                    log.info("%s -> %s", t, st)
                    try:
                        ks.fetch(t)
                    except Exception as e:  # noqa: BLE001
                        log.error("fetch %s loi %s", t, e)
                    lst.remove(t)
    parity()
    log.info("ORCH2 XONG")


def score(a):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401
    import flat3_crashpen_driver as F3
    import n700_driver as N
    R.MTM_COSTS = {"legacy": R.LEGACY}
    par = parity()
    keys = {"OFF_" + s: OFF[s] for s in SEEDS}
    for s in SEEDS:
        keys["R1V1_" + s] = B.tag_on("V1", s)
    for arm in ARMS:
        for s in SEEDS:
            t = tag(arm, s)
            if par.get(t, {}).get("ok"):
                keys[arm + "_" + s] = t
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "ISO_RISK " + k
    legs, daily, md5 = {}, {}, {}
    for k, t in keys.items():
        legs[k], daily[k], md5[k] = R.load_legs(t), R.load_daily(t), R.md5_of(t)
    raw = json.load(open(MTM_FILE)) if os.path.exists(MTM_FILE) else {}
    bc = json.load(open(B.MTM_FILE)) if os.path.exists(B.MTM_FILE) else {}
    for k in keys:
        if k not in raw:
            src = k if k.startswith("OFF_") else ("V1_" + k.split("_")[1] if k.startswith("R1V1_") else None)
            if src and bc.get(src, {}).get("md5") == md5[k]:
                raw[k] = bc[src]
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %d; can tinh %d: %s", len(raw), len(miss), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(MTM_FILE, "w"))
    M = {}
    for k in keys:
        M[k] = N.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"])
        M[k]["md5"] = md5[k]
    out = dict(prereg=PREREG, prereg_commit=PREREG_COMMIT, jar_sha256=B.jar_sha(), parity=par, arms={})
    for arm in ["R1V1"] + list(ARMS):
        ok = [s for s in SEEDS if (arm + "_" + s) in M]
        on = lambda s, m: M[arm + "_" + s][m]  # noqa: E731
        off = lambda s, m: M["OFF_" + s][m]  # noqa: E731
        n = len(ok)
        dcg = np.array([on(s, "cagr22") - off(s, "cagr22") for s in ok])
        hw = T995_DF7 * dcg.std(ddof=1) / math.sqrt(n) if n == 8 else float("nan")
        E = bool(n == 8 and all(abs(on(s, "dd_mtm")) <= 40 for s in ok))
        GO = bool(E and dcg.mean() >= 3.0 and dcg.mean() - hw > 0) if arm != "R1V1" else None
        agg = {m: float(np.mean([on(s, m) for s in ok])) for m in ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "n_per_year")} if ok else {}
        agg["worst_dd_mtm"] = float(min(on(s, "dd_mtm") for s in ok)) if ok else None
        rows = {s: {m: [off(s, m), on(s, m)] for m in ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "n_per_year")} for s in ok}
        out["arms"][arm] = dict(seeds_ok=ok, agg=agg, dcagr=dict(mean=float(dcg.mean()) if n else None,
                                                                   ci99=[float(dcg.mean() - hw), float(dcg.mean() + hw)] if n == 8 else None),
                                E=E, GO=GO, rows=rows)
        log.info("ARM %-6s n=%d CAGR22 %.2f dd22 %.2f ddALL %.2f (worst %.2f) Cal %.3f UW %.0f n/y %.0f | dCAGR %.2f CI99 %s | E=%s GO=%s",
                 arm, n, agg.get("cagr22", float("nan")), agg.get("dd_mtm22", float("nan")), agg.get("dd_mtm", float("nan")),
                 agg.get("worst_dd_mtm") or float("nan"), agg.get("calmar22", float("nan")), agg.get("uw_mtm22", float("nan")),
                 agg.get("n_per_year", float("nan")), dcg.mean() if n else float("nan"), out["arms"][arm]["dcagr"]["ci99"], E, GO)
    off_agg = {m: float(np.mean([M["OFF_" + s][m] for s in SEEDS])) for m in ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "n_per_year")}
    out["OFF"] = off_agg
    log.info("OFF %s", off_agg)
    go = [x for x in ARMS if out["arms"][x]["GO"]]
    out["winner"] = max(go, key=lambda x: (out["arms"][x]["agg"]["cagr22"], out["arms"][x]["agg"]["calmar22"])) if go else None
    log.info("WINNER %s", out["winner"])
    json.dump(out, open(JSON_OUT, "w"), indent=1, default=str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--cpu", type=int, default=5)
    ap.add_argument("--gpu", type=int, default=2)
    a = ap.parse_args()
    {"check": check, "orch2": orch2, "parity": lambda a: parity(), "score": score}[a.cmd](a)


if __name__ == "__main__":
    main()
