#!/usr/bin/env python3
"""BURST_COOLDOWN driver. Pre-reg docs/prereg/PREREG_BURST_COOLDOWN.md (branch feat/burst-cooldown 4e42ef59).

Jar = branch feat/burst-cooldown (dataset sim-jar-bcd). OFF = 8 run gqsf-* co san (K24 + skipFull, jar 0944841c).
P0 = jar moi, key vang, seed A1 => md5 printDone PHAI = gqsf-a1. ON = 3 arm x 8 seed.
Usage: jards | p0 | submit ARM SEED.. | status | fetch TAG.. | parity | score | orch
"""
import argparse
import hashlib
import json
import logging
import math
import os
import re
import shutil
import sys
import time

import numpy as np

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import gate_ablation_driver as GA  # noqa: E402
import gate_skipfull_driver as G  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("bcd")

D = "/home/ubuntu/claude_master/1016/bcd"
JAR_SRC = "/home/ubuntu/src_wt_bcd/target/binance-java-sdk-1.2.4.jar"
JAR_DS = "sim-jar-bcd"
CODE_SHA = "128290af"
SEEDS = G.SEEDS  # A1 S7 S13 S21 S99 S123 S777 S2024
OFF = {s: "gqsf-" + s.lower() for s in SEEDS}
ARMS = {"V1": (13, 120), "V2": (13, 360), "V3": (6, 360)}
P0_TAG = "bcd-p0"
OV_BASE = dict(G.OV_ON)  # B0OV + TOPK 24 + GATE_QUOTA_SKIP_WHEN_FULL=true
T975_DF7 = 2.364624
PREREG = "docs/prereg/PREREG_BURST_COOLDOWN.md"
PREREG_COMMIT = "4e42ef59"
JSON_OUT = D + "/burst_cooldown.json"
MTM_FILE = D + "/mtm.json"


def tag_on(arm, s):
    return "bcd-%s-%s" % (arm.lower(), s.lower())


def ov_on(arm):
    n, t = ARMS[arm]
    return dict(OV_BASE, SIM_BURST_COOLDOWN_N=n, SIM_BURST_COOLDOWN_MIN=t)


def jar_sha():
    p = D + "/jar.sha256"
    return open(p).read().split()[0] if os.path.exists(p) else None


def jards(a=None):
    ks = GA.ks_mod()
    G.disk("truoc jards")
    os.makedirs(D, exist_ok=True)
    fol = D + "/ds_" + JAR_DS
    os.makedirs(fol, exist_ok=True)
    shutil.copy(JAR_SRC, fol + "/sim.jar")
    sha = hashlib.sha256(open(fol + "/sim.jar", "rb").read()).hexdigest()
    open(D + "/jar.sha256", "w").write(sha + "  sim.jar\n")
    assert GA.md5f(G.PROF) == G.PROF_MD5
    shutil.copy(G.PROF, fol + "/" + os.path.basename(G.PROF))
    json.dump({"title": JAR_DS, "id": ks.USER + "/" + JAR_DS, "licenses": [{"name": "CC0-1.0"}]},
              open(fol + "/dataset-metadata.json", "w"))
    r = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
    log.info("dataset %s -> %s (jar %s)", JAR_DS, getattr(r, "url", r), sha)
    for _ in range(60):
        try:
            st = ks._api().dataset_status(ks.USER + "/" + JAR_DS)
        except Exception as e:  # noqa: BLE001
            st = "err:%s" % e
        log.info("dataset status %s", st)
        if str(st).lower() == "ready":
            return
        time.sleep(30)


def push(tag, ov, s):
    ks = GA.ks_mod()
    G.disk("truoc push " + tag)
    dsn, md5 = G.pred_of(s)
    if dsn is None:
        r = ks.submit(tag, GA.PROFILE, ov, jar_ds=JAR_DS, bundle_ds=GA.BUNDLE, sim_end_date="20251231",
                      xmx="22g", timeout_s=7200, code_sha=CODE_SHA)
        log.info("PUSHED %s %s ov=%s", tag, r, json.dumps(ov))
        return
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": ov, "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "pred_ds": dsn, "want_pred_md5": md5, "want_pred_base": GA.PRED0_MD5}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(GA.template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS, ks.USER + "/" + dsn],
          "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(md, f, indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s pred=%s md5=%s ov=%s", tag, getattr(r, "url", r), dsn, md5, json.dumps(ov))


def logtxt(tag):
    return G.logtxt(tag)


def p0_check():
    import reset_rule_score as R
    if not os.path.exists(GA.OUT % P0_TAG + "storage/printDone.csv"):
        return dict(ok=False, why="chua co output")
    rj, pr = GA.result_json(P0_TAG), GA.prof_run(P0_TAG)
    want = R.md5_of(OFF["A1"])
    got = R.md5_of(P0_TAG)
    chk = dict(md5=got == want, jar=rj.get("jar_sha256") == jar_sha(), ok=rj.get("ok") is True,
               key_absent="SIM_BURST_COOLDOWN_N" not in pr, n=rj.get("n_trades") == GA.result_json(OFF["A1"]).get("n_trades"))
    res = dict(ok=all(chk.values()), checks=chk, md5=got, want=want, n=rj.get("n_trades"), eq=rj.get("equity_final"))
    log.info("P0 %s", res)
    return res


def parity_on():
    res = {}
    for arm in ARMS:
        for s in SEEDS:
            tag = tag_on(arm, s)
            if not os.path.exists(GA.OUT % tag + "storage/printDone.csv"):
                continue
            rj, pr, txt = GA.result_json(tag), GA.prof_run(tag), logtxt(tag)
            n, t = ARMS[arm]
            bc = re.findall(r"\[BURST-COOLDOWN\] N=(\d+) MIN=(\d+) triggers=(\d+) blocked=(\d+)", txt)
            chk = dict(jar=rj.get("jar_sha256") == jar_sha(), ok=rj.get("ok") is True,
                       topk24=pr.get("SELECTOR_RANK_TOPK") == "24", skipfull=pr.get(G.KEY) == "true",
                       key=pr.get("SIM_BURST_COOLDOWN_N") == str(n) and pr.get("SIM_BURST_COOLDOWN_MIN") == str(t),
                       log=bool(bc) and bc[-1][0] == str(n) and bc[-1][1] == str(t),
                       b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()))
            res[tag] = dict(ok=all(chk.values()), checks=chk, n=rj.get("n_trades"), eq=rj.get("equity_final"),
                            triggers=int(bc[-1][2]) if bc else None, blocked=int(bc[-1][3]) if bc else None)
            log.info("PARITY %-14s %s n=%s eq=%s trig=%s blocked=%s", tag, "PASS" if res[tag]["ok"] else "*** VOID ***",
                     res[tag]["n"], res[tag]["eq"], res[tag]["triggers"], res[tag]["blocked"])
    return res


def orch(a):
    ks = GA.ks_mod()
    term = ks.TERMINAL
    os.makedirs(D, exist_ok=True)
    if not os.path.exists(GA.OUT % P0_TAG + "storage/printDone.csv"):
        if not a.no_p0_push:
            push(P0_TAG, dict(OV_BASE), "A1")
            time.sleep(120)
        st = ks.wait([ks.kernel_ref(P0_TAG)])
        log.info("P0 status %s", st)
        ks.fetch(P0_TAG)
    p0 = p0_check()
    json.dump(p0, open(D + "/p0.json", "w"), indent=1)
    if not p0["ok"]:
        log.error("P0 FAIL -> DUNG, khong chay ON")
        sys.exit(2)
    queue = [(arm, s) for s in SEEDS for arm in ARMS
             if not os.path.exists(GA.OUT % tag_on(arm, s) + "storage/printDone.csv")]
    running = []
    while queue or running:
        while queue and len(running) < 2:
            if ks.free_slots() < 1:
                log.info("account het slot -> cho")
                break
            arm, s = queue.pop(0)
            push(tag_on(arm, s), ov_on(arm), s)
            running.append(tag_on(arm, s))
            time.sleep(60)
        time.sleep(120)
        for t in list(running):
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
                running.remove(t)
    parity_on()
    log.info("ORCH XONG")


def score(a):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401
    import flat3_crashpen_driver as F3
    import selector_ablation_driver as SAD
    import n700_driver as N
    R.MTM_COSTS = {"legacy": R.LEGACY}
    p0 = p0_check()
    assert p0["ok"], "P0 chua PASS"
    par = parity_on()
    keys = {"OFF_" + s: OFF[s] for s in SEEDS}
    for arm in ARMS:
        for s in SEEDS:
            t = tag_on(arm, s)
            if par.get(t, {}).get("ok"):
                keys[arm + "_" + s] = t
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "BURST_COOLDOWN " + k
    legs, daily, md5 = {}, {}, {}
    for k, t in keys.items():
        legs[k], daily[k], md5[k] = R.load_legs(t), R.load_daily(t), R.md5_of(t)
    raw = json.load(open(MTM_FILE)) if os.path.exists(MTM_FILE) else {}
    gq = json.load(open(G.D + "/mtm.json")) if os.path.exists(G.D + "/mtm.json") else {}
    for s in SEEDS:
        k = "OFF_" + s
        if k not in raw and gq.get("ON_" + s, {}).get("md5") == md5[k]:
            raw[k] = gq["ON_" + s]
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %d; can tinh %s", len(raw), sorted(miss))
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
    out = dict(prereg=PREREG, prereg_commit=PREREG_COMMIT, jar_sha256=jar_sha(), p0=p0, parity=par, arms={})
    for arm in ARMS:
        ok = [s for s in SEEDS if (arm + "_" + s) in M]
        on = lambda s, m: M[arm + "_" + s][m]  # noqa: E731
        off = lambda s, m: M["OFF_" + s][m]  # noqa: E731
        ddd = np.array([on(s, "dd_mtm22") - off(s, "dd_mtm22") for s in ok])
        dcg = np.array([on(s, "cagr22") - off(s, "cagr22") for s in ok])
        cal_on = float(np.mean([on(s, "calmar22") for s in ok])) if ok else float("nan")
        cal_off = float(np.mean([off(s, "calmar22") for s in ok])) if ok else float("nan")
        n = len(ok)
        hw = T975_DF7 * ddd.std(ddof=1) / math.sqrt(n) if n == 8 else float("nan")
        rule = dict(
            G1=dict(mean=float(ddd.mean()) if n else None, ci=[float(ddd.mean() - hw), float(ddd.mean() + hw)] if n == 8 else None,
                    ok=bool(n == 8 and ddd.mean() >= 2.0 and ddd.mean() - hw > 0)),
            G2=dict(cal_on=cal_on, cal_off=cal_off, ok=bool(n == 8 and cal_on >= cal_off)),
            G3=dict(mean=float(dcg.mean()) if n else None, ok=bool(n == 8 and dcg.mean() >= -3.0)),
            G4=dict(worst=min(on(s, "dd_mtm") for s in ok) if ok else None,
                    ok=bool(n == 8 and all(abs(on(s, "dd_mtm")) <= 40 for s in ok))))
        rule["GO"] = all(rule[g]["ok"] for g in ("G1", "G2", "G3", "G4"))
        rows = {s: dict(dd22=[off(s, "dd_mtm22"), on(s, "dd_mtm22")], cagr22=[off(s, "cagr22"), on(s, "cagr22")],
                        cal22=[off(s, "calmar22"), on(s, "calmar22")], uw22=[off(s, "uw_mtm22"), on(s, "uw_mtm22")],
                        dd_all=[off(s, "dd_mtm"), on(s, "dd_mtm")], n_yr=[off(s, "n_per_year"), on(s, "n_per_year")],
                        blocked=par[tag_on(arm, s)]["blocked"], triggers=par[tag_on(arm, s)]["triggers"]) for s in ok}
        for s, r in rows.items():
            log.info("ROW %s %-5s dd22 %6.2f->%6.2f CAGR22 %6.2f->%6.2f Cal %5.3f->%5.3f UW %4.0f->%4.0f n/y %4.0f->%4.0f trig %s blk %s",
                     arm, s, *r["dd22"], *r["cagr22"], *r["cal22"], *r["uw22"], *r["n_yr"], r["triggers"], r["blocked"])
        log.info("RULE %s %s", arm, json.dumps(rule))
        out["arms"][arm] = dict(nt=ARMS[arm], seeds_ok=ok, rows=rows, rule=rule)
    go = [arm for arm in ARMS if out["arms"][arm]["rule"]["GO"]]
    out["winner"] = max(go, key=lambda x: out["arms"][x]["rule"]["G2"]["cal_on"]) if go else None
    log.info("WINNER %s", out["winner"])
    json.dump(out, open(JSON_OUT, "w"), indent=1, default=str)
    log.info("JSON -> %s", JSON_OUT)


GPU_CHK = "bcd-gpuchk-s7"


def push_gpu(tag, ov, s):
    """Nhu push() nhung kernel bat GPU (chi de lay them slot; sim chay CPU). Seed A1 khong dung GPU."""
    assert s != "A1"
    ks = GA.ks_mod()
    dsn, md5 = G.pred_of(s)
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": ov, "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "pred_ds": dsn, "want_pred_md5": md5, "want_pred_base": GA.PRED0_MD5}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(GA.template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
          "dataset_sources": [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS, ks.USER + "/" + dsn],
          "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(md, f, indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED-GPU %s %s pred=%s ov=%s", tag, getattr(r, "url", r), dsn, json.dumps(ov))


def gpu_ok():
    """GPU host phai cho printDone giong byte run CPU (gqsf-s7) khi key vang."""
    import reset_rule_score as R
    p = GA.OUT % GPU_CHK + "storage/printDone.csv"
    if not os.path.exists(p):
        return None
    ok = R.md5_of(GPU_CHK) == R.md5_of(OFF["S7"])
    log.info("GPU-CHK md5 %s vs gqsf-s7 %s -> %s", R.md5_of(GPU_CHK), R.md5_of(OFF["S7"]), ok)
    return ok


def orch2(a):
    """Song song: toi da a.cpu kernel CPU + a.gpu kernel GPU. GPU chi dung sau khi GPU-CHK PASS."""
    ks = GA.ks_mod()
    term = ks.TERMINAL
    p0 = p0_check()
    assert p0["ok"], "P0 chua PASS"
    todo = [(arm, s) for s in SEEDS for arm in ARMS]
    run_cpu, run_gpu, queue = [], [], []
    for arm, s in todo:
        t = tag_on(arm, s)
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
    gchk = gpu_ok()
    if gchk is None and a.gpu > 0:
        try:
            st = ks._status(ks.kernel_ref(GPU_CHK))
        except Exception:  # noqa: BLE001
            st = None
        if st not in ("RUNNING", "QUEUED"):
            push_gpu(GPU_CHK, dict(OV_BASE), "S7")
        run_gpu.append(GPU_CHK)
    log.info("ORCH2 start cpu_running=%s gpu_running=%s queue=%d", run_cpu, run_gpu, len(queue))
    while queue or run_cpu or run_gpu:
        while queue and len(run_cpu) < a.cpu:
            arm, s = queue.pop(0)
            push(tag_on(arm, s), ov_on(arm), s)
            run_cpu.append(tag_on(arm, s))
            time.sleep(45)
        if gchk:
            for i in range(len(queue) - 1, -1, -1):
                if len(run_gpu) >= a.gpu:
                    break
                arm, s = queue[i]
                if s == "A1":
                    continue
                queue.pop(i)
                push_gpu(tag_on(arm, s), ov_on(arm), s)
                run_gpu.append(tag_on(arm, s))
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
                    if t == GPU_CHK:
                        gchk = gpu_ok()
                        if not gchk:
                            log.error("GPU-CHK FAIL -> khong dung GPU")
    parity_on()
    log.info("ORCH2 XONG")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--no-p0-push", action="store_true")
    ap.add_argument("--cpu", type=int, default=5)
    ap.add_argument("--gpu", type=int, default=2)
    a = ap.parse_args()
    if a.cmd == "jards":
        jards(a)
    elif a.cmd == "p0":
        push(P0_TAG, dict(OV_BASE), "A1")
    elif a.cmd == "orch":
        orch(a)
    elif a.cmd == "orch2":
        orch2(a)
    elif a.cmd == "parity":
        p0_check()
        parity_on()
    elif a.cmd == "score":
        score(a)
    else:
        raise SystemExit("cmd?")


if __name__ == "__main__":
    main()
