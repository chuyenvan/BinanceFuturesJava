#!/usr/bin/env python3
"""R1 orchestrator 2: A1 NET (8 seed) roi A2 RND (4 seed) tuan tu tren 1 slot Kaggle. Dung khi kernel loi/validate truot.
State: orch2_state.json."""
import hashlib
import json
import logging
import os
import sys
import time

sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r1_s1")
import r1_arm_driver as A  # noqa: E402
import r1_orch as O  # noqa: E402  (st, gate_line)

D = A.R.D
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler(D + "/orch2.log"), logging.StreamHandler(sys.stdout)], force=True)
log = logging.getLogger("orch2")
SEEDS8 = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
QUEUE = [("A1", s) for s in SEEDS8] + [("A2", s) for s in ("A1", "S7", "S13", "S21")]
SF = D + "/orch2_state.json"
RUNNING = ("running", "queued")


def validate(ks, arm, seed, tag, want):
    out = A.R.GA.OUT % tag
    f = ks.fetch(tag, out_dir=out)
    res = f["result"] or {}
    pdn = out + "storage/printDone.csv"
    md5 = hashlib.md5(open(pdn, "rb").read()).hexdigest() if os.path.exists(pdn) else None
    ref = A.R.GA.OUT % ("tsx-x14-" + seed.lower())
    a3 = res.get("r1_a3") or {}
    v = dict(tag=tag, arm=arm, ok=res.get("ok"), date_last=res.get("date_last"), n_trades=res.get("n_trades"),
             equity_final=res.get("equity_final"), md5=md5, gate=O.gate_line(out), gate_ref=O.gate_line(ref),
             jar=res.get("jar_sha256"), bins=a3)
    v["valid"] = bool(res.get("ok") is True and res.get("date_last") == "20251230" and md5 is not None
                      and a3.get("bins_sha256") == want and a3.get("md5_printdone") == md5)
    return v


def main():
    ks = A.R.GA.ks_mod()
    S = json.load(open(SF)) if os.path.exists(SF) else {"done": {}}
    tags = [A.tag_of(a, s) for a, s in QUEUE]
    for arm, seed in QUEUE:
        tag = A.tag_of(arm, seed)
        if tag in S["done"]:
            continue
        want = A.bins_sha(arm)
        s0 = O.st(ks, tag)
        if not s0.startswith(RUNNING + ("complete",)):
            while True:
                busy = [t for t in tags + O.__dict__.get("EXTRA", []) if t != tag and O.st(ks, t).startswith(RUNNING)]
                fs = ks.free_slots()
                if not busy and fs >= 1:
                    break
                log.info("cho slot: busy=%s free=%s", busy, fs)
                time.sleep(300)
            A.push(arm, seed)
            time.sleep(90)
        t0 = time.time()
        while True:
            s = O.st(ks, tag)
            if not s.startswith(RUNNING):
                break
            if time.time() - t0 > 4 * 3600:
                log.error("TIMEOUT %s", tag)
                sys.exit(3)
            time.sleep(180)
        log.info("%s ket thuc status=%s sau %.0f phut", tag, s, (time.time() - t0) / 60)
        if not s.startswith("complete"):
            log.error("DUNG: %s status=%s", tag, s)
            sys.exit(2)
        v = validate(ks, arm, seed, tag, want)
        log.info("VALIDATE %s", json.dumps(v))
        S["done"][tag] = v
        json.dump(S, open(SF, "w"), indent=1)
        if not v["valid"]:
            log.error("DUNG: validate truot %s", tag)
            sys.exit(4)
    log.info("HANG DOI XONG")


if __name__ == "__main__":
    main()
