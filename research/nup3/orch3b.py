#!/usr/bin/env python3
"""NUP3b orchestrator (PREREG_NUP3B 9b49f7a9 + ADDENDUM_TECH) — tai dung orch.py (NUP3), state rieng nup3b_wk.
CHI push / poll / keo ket qua + cong KY THUAT. KHONG cham, KHONG chon Pha 2.

  python3 orch3b.py jards | run | gates | status
Cong (truoc Pha 1):
  G-OFF-A1  : nup3b-goff-a1   SLEEVE_ENABLED=false            => md5 printDone = B0 tsx-x14-a1
  G-OFF-S7  : nup3b-offv1-s7  V1 (size 1.0) + BASE_SKIP=false => md5 printDone = NUP3 nup3-v1-s7 (jar cu b269f96b)
  G-INV-A1  : nup3b-s0b-a1 VA nup3b-s1b-a1 loc book=sleeve    => md5 = B0 a1 (2 run nay cung la run Pha 1)
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orch as O  # noqa: E402

W = "/home/ubuntu/claude_master/nup3b_wk"
os.makedirs(W, exist_ok=True)
O.W = W
O.STATE, O.GATES = W + "/state.json", W + "/gates.json"
O.JAR_SRC = "/home/ubuntu/src_nup3/target/binance-java-sdk-1.2.4.jar"
O.JAR_SHA = open(W + "/jar.sha256").read().split()[0] if os.path.exists(W + "/jar.sha256") else "NA"
O.JAR_DS = "sim-jar-nup3b"
O.CODE_SHA = open(W + "/code_sha.txt").read().strip() if os.path.exists(W + "/code_sha.txt") else "NA"
OUT = O.OUT
V1_REF = ("nup3-v1-s7", "/home/ubuntu/kaggle_sim/out/nup3-v1-s7/storage/printDone.csv")

S0B = dict(O.ARMS["v0"], SLEEVE_SIZE_MULT=0.525)
S1B = dict(O.ARMS["v1"], SLEEVE_SIZE_MULT=0.574)
S1X = dict(S1B, BASE_SKIP_SLEEVE_SYMBOLS="true")
ARMS = {"s0b": S0B, "s1b": S1B, "s1x": S1X}


def plan():
    P = [dict(tag="nup3b-goff-a1", seed="A1", phase="gate", ov=dict(SLEEVE_ENABLED="false", BASE_SKIP_SLEEVE_SYMBOLS="false")),
         dict(tag="nup3b-offv1-s7", seed="S7", phase="gate", ov=dict(O.ARMS["v1"], BASE_SKIP_SLEEVE_SYMBOLS="false")),
         dict(tag="nup3b-s0b-a1", seed="A1", phase="gate", ov=S0B),
         dict(tag="nup3b-s1b-a1", seed="A1", phase="gate", ov=S1B)]
    for arm in ("s0b", "s1b", "s1x"):
        for s in O.P1_SEEDS:
            t = "nup3b-%s-%s" % (arm, s.lower())
            if any(e["tag"] == t for e in P):
                continue
            P.append(dict(tag=t, seed=s, phase="p1", arm=arm, ov=ARMS[arm], extra=[]))
    # rerun 1 lan: nup3b-s0b-s99 FAILED/NORUN (kernels_push khong tao kernel, 404) — cung cau hinh, cung jar
    P.append(dict(tag="nup3b-s0b-s99r", seed="S99", phase="p1", arm="s0b", ov=ARMS["s0b"], extra=[]))
    return P


def check_run(tag, e):
    rj = OUT % tag + "result.json"
    if not os.path.exists(rj):
        return {"ok": False, "why": "no result.json"}
    r = json.load(open(rj))
    pr = O.GA.prof_run(tag)
    b0 = O.GA.prof_run("tsx-x14-" + e["seed"].lower())
    assert b0, "thieu prof_run B0"
    diff = sorted(k for k in set(pr) | set(b0) if pr.get(k) != b0.get(k))
    want = sorted(k for k in e["ov"] if k.startswith("SLEEVE") or k == "BASE_SKIP_SLEEVE_SYMBOLS")
    c = {"java_ok": r.get("ok") is True, "jar": r.get("jar_sha256") == O.JAR_SHA, "keys": diff == want,
         "pdone": os.path.exists(OUT % tag + "storage/printDone.csv")}
    return {"ok": all(c.values()), "checks": c, "diff_keys": diff, "n_trades": r.get("n_trades"), "secs": r.get("secs")}


def _filtered_md5(tag):
    raw = open(OUT % tag + "storage/printDone.csv", "rb").read().splitlines(keepends=True)
    base = [ln for ln in raw if b"book=sleeve" not in ln]
    return O.md5b(b"".join(base)), len(raw) - len(base)


def gates(st=None):
    st = st or O.load_state()
    g = {}
    e = st.get("nup3b-goff-a1", {})
    if e.get("state") != "DONE":
        g["G-OFF-A1"] = {"status": "FAIL" if e.get("state") == "FAILED" else "PENDING"}
    else:
        m, mb = O.md5f(OUT % "nup3b-goff-a1" + "storage/printDone.csv"), O.md5f(OUT % "tsx-x14-a1" + "storage/printDone.csv")
        g["G-OFF-A1"] = {"status": "PASS" if m == mb == O.B0["A1"][1] else "FAIL", "md5": m, "ref": "tsx-x14-a1", "ref_md5": mb}
    e = st.get("nup3b-offv1-s7", {})
    if e.get("state") != "DONE":
        g["G-OFF-S7"] = {"status": "FAIL" if e.get("state") == "FAILED" else "PENDING"}
    else:
        m, mr = O.md5f(OUT % "nup3b-offv1-s7" + "storage/printDone.csv"), O.md5f(V1_REF[1])
        g["G-OFF-S7"] = {"status": "PASS" if m == mr else "FAIL", "md5": m, "ref": V1_REF[0], "ref_md5": mr}
    sub, stat = {}, []
    for tag in ("nup3b-s0b-a1", "nup3b-s1b-a1"):
        e = st.get(tag, {})
        if e.get("state") != "DONE":
            s = "FAIL" if e.get("state") == "FAILED" else "PENDING"
            sub[tag] = {"status": s}
        else:
            mb, n_sl = _filtered_md5(tag)
            s = "PASS" if (mb == O.B0["A1"][1] and n_sl >= 1) else "FAIL"
            sm = OUT % tag + "storage/sleeve_summary.json"
            summ = json.load(open(sm)) if os.path.exists(sm) else {}
            sub[tag] = {"status": s, "md5_base_filtered": mb, "n_sleeve_rows": n_sl,
                        "u_total_max": summ.get("u_total_max"), "u_total_margin_max": summ.get("u_total_margin_max"),
                        "opened": summ.get("opened"), "overlap": summ.get("overlap_base_opens_sleeve_sym")}
        stat.append(s)
    gs = "FAIL" if "FAIL" in stat else ("PASS" if all(x == "PASS" for x in stat) else "PENDING")
    g["G-INV-A1"] = dict(status=gs, runs=sub, b0_md5=O.B0["A1"][1])
    g["SMOKE-V2"] = {"status": "PASS", "note": "N/A cho NUP3b (khong co V2)"}
    json.dump(g, open(O.GATES, "w"), indent=1)
    return g


def jards():
    O.G.disk("truoc jards")
    fol = W + "/ds_" + O.JAR_DS
    os.makedirs(fol, exist_ok=True)
    shutil.copy(O.JAR_SRC, fol + "/sim.jar")
    sha = O.sha256f(fol + "/sim.jar")
    assert sha == O.JAR_SHA, "jar sha lech jar.sha256"
    rc = subprocess.call([sys.executable, "-I", O.SEC, fol + "/sim.jar", W + "/jar_sec_upload.json"])
    assert rc == 0, "KIEM BAO MAT JAR FAIL -> KHONG upload"
    assert O.md5f(O.PROF_SRC) == O.G.PROF_MD5
    shutil.copy(O.PROF_SRC, fol + "/" + os.path.basename(O.PROF_SRC))
    assert O._create_ds(fol, O.JAR_DS), "dataset jar chua ready"


O.plan, O.check_run, O.gates = plan, check_run, gates

if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    {"jards": jards, "run": O.run, "gates": lambda: print(json.dumps(gates(), indent=1)),
     "status": O.status}.get(c, lambda: sys.exit(__doc__))()
