#!/usr/bin/env python3
"""R1 orchestrator: chay tuan tu tren 1 slot Kaggle. Hang doi: G-P0 (A0 seed A1) roi A3 7 seed con lai.
Dung lai khi kernel loi hoac validate truot. State: orch_state.json."""
import hashlib
import json
import logging
import os
import re
import sys
import time

sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r1_s1")
import r1_a3_driver as R  # noqa: E402

D = R.D
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler(D + "/orch.log"), logging.StreamHandler(sys.stdout)], force=True)
log = logging.getLogger("orch")
QUEUE = [("A3", "A1"), ("P0", "A1"), ("A3", "S7"), ("A3", "S13"), ("A3", "S21"), ("A3", "S99"), ("A3", "S123"),
         ("A3", "S777"), ("A3", "S2024")]
SF = D + "/orch_state.json"
WANT = R.a3_sha()


def tag_of(arm, seed):
    return ("r1-a3-" if arm == "A3" else "r1-p0-") + seed.lower()


def st(ks, tag):
    try:
        return str(ks._status(ks.kernel_ref(tag))).lower()
    except Exception as e:  # noqa: BLE001
        return "none:" + type(e).__name__


def gate_line(out):
    p = out + "logs/sim.out"
    if not os.path.exists(p):
        return None
    txt = open(p, errors="replace").read()
    g = re.findall(r"\[GATE\] scale=\S+ base=\S+ n_cand=(\d+) n_pass=(\d+)", txt)
    r = re.findall(r"\[GATE-RATIO\] GATE-RATIO on .*? seen=(\d+) pass=(\d+)", txt)
    t = re.findall(r"\[TSX\] extHours=(\d+) extDays=(\d+)", txt)
    return dict(n_cand=int(g[-1][0]) if g else None, n_pass=int(g[-1][1]) if g else None,
                ratio_pass=int(r[-1][1]) if r else None, tsx=list(t[-1]) if t else None)


def validate(ks, arm, seed, tag):
    out = R.GA.OUT % tag
    f = ks.fetch(tag, out_dir=out)
    res = f["result"] or {}
    pdn = out + "storage/printDone.csv"
    md5 = hashlib.md5(open(pdn, "rb").read()).hexdigest() if os.path.exists(pdn) else None
    ref = R.GA.OUT % ("tsx-x14-" + seed.lower())
    md5_ref = hashlib.md5(open(ref + "storage/printDone.csv", "rb").read()).hexdigest()
    v = dict(tag=tag, ok=res.get("ok"), date_last=res.get("date_last"), n_trades=res.get("n_trades"),
             equity_final=res.get("equity_final"), md5=md5, md5_ref=md5_ref, gate=gate_line(out),
             gate_ref=gate_line(ref), jar=res.get("jar_sha256"))
    good = res.get("ok") is True and res.get("date_last") == "20251230" and md5 is not None
    if arm == "A3":
        a3 = res.get("r1_a3") or {}
        v["a3"] = a3
        good = good and a3.get("bins_sha256") == WANT and a3.get("md5_printdone") == md5
    else:
        v["G_P0"] = md5 == md5_ref
    v["valid"] = bool(good)
    return v


def main():
    ks = R.GA.ks_mod()
    S = json.load(open(SF)) if os.path.exists(SF) else {"done": {}}
    for arm, seed in QUEUE:
        tag = tag_of(arm, seed)
        if tag in S["done"]:
            continue
        s0 = st(ks, tag)
        if not s0.startswith(("running", "queued", "complete")):
            while True:
                busy = [t for a, sd in QUEUE for t in [tag_of(a, sd)] if t != tag and st(ks, t).startswith(("running", "queued"))]
                fs = ks.free_slots()
                if not busy and fs >= 1:
                    break
                log.info("cho slot: busy=%s free=%s", busy, fs)
                time.sleep(300)
            R.push(seed, arm)
            time.sleep(90)
        t0 = time.time()
        while True:
            s = st(ks, tag)
            if not s.startswith(("running", "queued")):
                break
            if time.time() - t0 > 4 * 3600:
                log.error("TIMEOUT %s", tag)
                sys.exit(3)
            time.sleep(180)
        log.info("%s ket thuc status=%s sau %.0f phut", tag, s, (time.time() - t0) / 60)
        if not s.startswith("complete"):
            log.error("DUNG: %s status=%s", tag, s)
            sys.exit(2)
        v = validate(ks, arm, seed, tag)
        log.info("VALIDATE %s", json.dumps(v))
        S["done"][tag] = v
        json.dump(S, open(SF, "w"), indent=1)
        if not v["valid"]:
            log.error("DUNG: validate truot %s", tag)
            sys.exit(4)
    log.info("HANG DOI XONG")


if __name__ == "__main__":
    main()
