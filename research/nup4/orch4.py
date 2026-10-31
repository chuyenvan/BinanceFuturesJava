#!/usr/bin/env python3
"""NUP4 orchestrator (PREREG_NUP4 feac2d5e). Chi push / poll / fetch / cong KY THUAT. KHONG cham diem.

Duong chay: pipeline HO2026 A1 (nt-chain-y26 + nt-tk26 + pred_s<seed>) voi jar NUP4; mot run phu
DEV 2021-07..2025-12 VA HO 2026 den 2026-09-30. X14 = HOP 42 khoang 2021-25 + 5 khoang 2026.

  python3 orch4.py jards      # tao dataset private sim-jar-nup4 (sha + kiem bao mat)
  python3 orch4.py run        # vong lap: gate b0union (seed 42) -> PASS -> Pha 1a 28 run
  python3 orch4.py gates      # tinh lai cong tu output da keo
  python3 orch4.py status
State ~/claude_master/nup4_wk/state.json, manifest.jsonl (config/seed/md5 jar+dataset/kernel id).
Toi da 2 kernel cua ta cung luc.
"""
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time

R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R)
sys.path.insert(0, R + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
import ho4p1_queue as Q            # noqa: E402  (template + ARTS + FUND + UNSEAL)
import gate_skipfull_driver as G   # noqa: E402

W = "/home/ubuntu/claude_master/nup4_wk"
os.makedirs(W, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout, force=True)
_fh = logging.FileHandler(W + "/orch.log")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(_fh)
log = logging.getLogger("nup4")

STATE = W + "/state.json"
MANIFEST = W + "/manifest.jsonl"
OUT = GA.OUT
KS = Q.GA.ks_mod()
USER = KS.USER

JAR_DS = "sim-jar-nup4b"
JAR_SRC = "/home/ubuntu/src_nup3/target/binance-java-sdk-1.2.4.jar"
JAR_SHA = "9f6f028b76261659579ee1eaf82f287173ccd6c5cb891cf08ebac5606fe2e347"
PROF = "/home/ubuntu/kaggle_sim/push_jar_nsel/prof_r4_kg0_k16_f015_g155.properties"
SEC = "/home/ubuntu/claude_master/vz_e1_wt/research/nup3/jar_sec_check.py"
CODE_SHA = "nup4-phase0"
ARTS = json.load(open("/home/ubuntu/claude_master/ho_tradfi_wk/arts_nt.json"))
CHAIN, TKK = ARTS["chain_slug"], ARTS["tk_slug"]
PRED_BASE = Q.PRED_BASE
FUND = dict(Q.FUND, bins_md5=ARTS["bins_md5"])
MAXPAR, POLL_S = 2, 240
END = "20261001"

FLAGS25 = json.load(open("/home/ubuntu/claude_master/tsx/flags.json"))["ranges"]
FLAGS26 = "20260205-20260214,20260216-20260217,20260224-20260225,20260606-20260607,20260610-20260611"
X14 = FLAGS25 + "," + FLAGS26

BASE = dict(GA.B0OV, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true",
            SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=X14)
SLV = dict(SLEEVE_ENABLED="true", SLEEVE_PCT=0.99985, SLEEVE_U_MAX=0.35, SLEEVE_ARM="V1",
           SLEEVE_BURST_N=10, SLEEVE_BURST_MIN=60)


def arm_ov(arm):
    if arm == "b0union":
        return dict(BASE, SLEEVE_ENABLED="false", MERGE_MODE="NONE")
    if arm == "s1b":
        return dict(BASE, SLEEVE_SIZE_MULT=0.574, MERGE_MODE="NONE", **SLV)
    mode = {"m1a": ("M1", 0.574), "m1b": ("M1", 0.45), "m2a": ("M2", 0.574), "m2b": ("M2", 0.45),
            "m3a": ("M3", 0.574), "m3b": ("M3", 0.45)}[arm]
    return dict(BASE, SLEEVE_SIZE_MULT=mode[1], MERGE_MODE=mode[0], **SLV)


SEED_NAME = {42: "a1", 7: "s7", 13: "s13", 21: "s21", 99: "s99", 123: "s123", 777: "s777", 2024: "s2024"}
P1 = [42, 7, 21, 99]
P2 = [13, 123, 777, 2024]
ARMS_P1 = ["b0union", "s1b", "m1a", "m1b", "m2a", "m2b", "m3a", "m3b"]


def tag_of(arm, seed):
    return "n4b-%s-%s" % (arm, SEED_NAME[seed])


def finalists():
    """Chi push Pha 1b khi co W/finalists.json = {"arms":["m1a","m3b"]} (toi da 2, do buoc cham chon)."""
    p = W + "/finalists.json"
    return json.load(open(p))["arms"] if os.path.exists(p) else []


def plan():
    P = [dict(tag=tag_of("b0union", 42), arm="b0union", seed=42, phase="gate")]
    for s in P1:
        for a in ARMS_P1:
            if a == "b0union":
                continue
            P.append(dict(tag=tag_of(a, s), arm=a, seed=s, phase="p1a"))
    for s in P2:
        for a in finalists():
            assert a != "b0union"
            P.append(dict(tag=tag_of(a, s), arm=a, seed=s, phase="p1b"))
    return P


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(st):
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ dataset jar
def jards():
    assert sha256f(JAR_SRC) == JAR_SHA, "jar sha lech JAR_SHA"
    assert md5f(PROF) == G.PROF_MD5, "profile la (md5 lech)"
    fol = W + "/ds_" + JAR_DS
    if not os.path.exists(fol + "/JAR_SHA.json"):
        os.makedirs(fol, exist_ok=True)
        shutil.copy(JAR_SRC, fol + "/sim.jar")
        shutil.copy(PROF, fol + "/" + os.path.basename(PROF))
        rc = subprocess.call([sys.executable, "-I", SEC, fol + "/sim.jar", W + "/jar_sec_upload.json"])
        assert rc == 0 and json.load(open(W + "/jar_sec_upload.json"))["ok"] is True, "JAR SEC CHECK FAIL"
        json.dump({"sim.jar_sha256": JAR_SHA, "profile": os.path.basename(PROF),
                   "privateconfig": "STUB", "code_sha": CODE_SHA}, open(fol + "/JAR_SHA.json", "w"))
        json.dump({"title": JAR_DS, "id": USER + "/" + JAR_DS, "licenses": [{"name": "CC0-1.0"}]},
                  open(fol + "/dataset-metadata.json", "w"))
        a = KS._api()
        r = a.dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
        log.info("dataset %s -> %s", JAR_DS, getattr(r, "url", r))
    for _ in range(60):
        try:
            s = str(KS._api().dataset_status(USER + "/" + JAR_DS))
        except Exception as e:  # noqa: BLE001
            s = "err " + str(e)[:40]
        if "ready" in s.lower():
            log.info("dataset %s ready", JAR_DS)
            return True
        time.sleep(30)
    raise SystemExit("dataset jar khong ready")


# ------------------------------------------------------------------ push
def template():
    t = GA.template()
    assert t.count(GA.PATCH_ANCHOR) == 1
    t = t.replace(GA.PATCH_ANCHOR, Q.BLK + GA.PATCH_ANCHOR)
    assert "TICKER_HO4P1_FAIL" in t and "FUND_HO4_OK" in t
    compile(t.replace("__CFG_JSON__", repr("{}")), "kernel", "exec")
    return t


def push(e):
    tag, arm, seed = e["tag"], e["arm"], e["seed"]
    ov = arm_ov(arm)
    ref = KS.kernel_ref(tag)
    folder = os.path.join(KS.WORKDIR, KS.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": ov, "sim_end_date": END, "xmx": "22g",
           "timeout_s": 10800, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": CHAIN,
           "market_align": False, "extra_env": {"HOLDOUT_UNSEAL": Q.UNSEAL}, "ticker_min_days": 2099,
           "pred_ds": "pred_s%d" % seed, "want_pred_md5": ARTS["preds"][str(seed)],
           "want_pred_base": PRED_BASE, "tk_ho4p1": {"src": TKK, "md5": ARTS["tk_md5"]},
           "fund_rebuild_ho4p1": FUND}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [USER + "/" + Q.BUNDLE] + KS.TICKER_DS + [USER + "/" + JAR_DS],
          "competition_sources": [], "kernel_sources": [USER + "/" + CHAIN, USER + "/" + TKK]}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(md, f, indent=1)
    r = KS._api().kernels_push(folder)
    err = getattr(r, "error", None) or getattr(r, "errorMessage", None)
    if err or not getattr(r, "url", None):
        raise RuntimeError("kernels_push %s bi tu choi: %s" % (tag, err or r))
    st = load_state()
    st[tag] = {"state": "PUSHED", "arm": arm, "seed": seed, "phase": e["phase"], "ov": ov,
               "at": time.strftime("%F %T"), "t": time.time(), "ref": ref}
    save_state(st)
    with open(MANIFEST, "a") as f:
        f.write(json.dumps({"tag": tag, "ref": ref, "arm": arm, "seed": seed, "phase": e["phase"],
                            "overrides": ov, "sim_end_date": END, "jar_ds": JAR_DS, "jar_sha256": JAR_SHA,
                            "chain": CHAIN, "tk": TKK, "pred_md5": ARTS["preds"][str(seed)],
                            "x14_days": "47 ranges", "at": time.strftime("%F %T")}) + "\n")
    log.info("PUSHED %s seed=%s end=%s arm=%s", tag, seed, END, arm)


# ------------------------------------------------------------------ check
def check_run(tag, e):
    o = OUT % tag
    try:
        rj = json.load(open(o + "result.json"))
    except Exception:  # noqa: BLE001
        return {"ok": False, "why": "no result.json"}
    pr = GA.prof_run(tag)
    b0 = GA.prof_run("nt-x14-s%d" % e["seed"])
    X14K = "SIM_LOSER_TS_EXT_DAYS"      # khac nt-x14 (2026-only) la CHU DINH: ta dung hop 47 khoang
    diff = sorted(k for k in set(pr) | set(b0) if pr.get(k) != b0.get(k) and k != X14K)
    want = sorted(k for k in arm_ov(e["arm"]) if k.startswith("SLEEVE") or k == "MERGE_MODE")
    c = {"ok": rj.get("ok") is True, "jar": rj.get("jar_sha256") == JAR_SHA,
         "keys": diff == want, "pdone": os.path.exists(o + "storage/printDone.csv"),
         "eq": os.path.exists(o + "storage/equity_summary.json"),
         "x14": len(pr.get(X14K, "").split(",")) == 47}
    if e["arm"] != "b0union":
        c["owners"] = os.path.exists(o + "storage/leg_owner.csv")
        c["mergelog"] = os.path.exists(o + "storage/merge_log.csv")
    out = {"ok": all(c.values()), "checks": c, "diff_keys": diff, "x14_n": len(pr.get(X14K, "").split(",")),
           "n_trades": rj.get("n_trades"), "secs": rj.get("secs")}
    return out


def poll():
    st = load_state()
    P = {e["tag"]: e for e in plan()}
    for tag, e in list(st.items()):
        if e.get("state") != "PUSHED":
            continue
        try:
            s = KS._status(KS.kernel_ref(tag))
        except Exception as ex:  # noqa: BLE001
            msg = str(ex)
            if ("404" in msg or "No runs" in msg) and time.time() - e.get("t", 0) > 1800:
                e["state"], e["kstatus"] = "FAILED", "NORUN"
                save_state(st)
            log.warning("status %s %s", tag, msg[:120])
            continue
        if s in KS.TERMINAL:
            e["kstatus"] = s
            try:
                KS.fetch(tag)
            except Exception as ex:  # noqa: BLE001
                log.error("fetch %s %s", tag, str(ex)[:200])
            if s == "COMPLETE" and tag in P:
                e["check"] = check_run(tag, P[tag])
                e["state"] = "DONE" if e["check"]["ok"] else "FAILED"
            else:
                e["state"] = "FAILED"
            log.info("%s -> %s ok=%s", tag, e["state"], (e.get("check") or {}).get("ok"))
            save_state(st)
    return st


def gate_ok(st):
    """G-DEV: DEV cua b0union phai trung tsx-x14-a1. 2026: chi kiem co du lieu (B0 2026 = chinh run nay;
    ADDENDUM_TECH-1: nt-x14 khong dung lam tham chieu duoc vi khac danh sach X14 DEV => khac equity vao 2026)."""
    e = st.get(tag_of("b0union", 42), {})
    if e.get("state") != "DONE":
        return ("PENDING" if e.get("state") != "FAILED" else "FAIL"), {}
    p = OUT % tag_of("b0union", 42) + "storage/printDone.csv"
    lines = open(p, "rb").read().splitlines(keepends=True)
    hdr, body = lines[0], lines[1:]
    dev = [ln for ln in body if ln.decode(errors="ignore").split(",")[6:7] and
           ln.decode(errors="ignore").split(",")[6] < "20260101"]
    y26 = [ln for ln in body if ln.decode(errors="ignore").split(",")[6:7] and
           ln.decode(errors="ignore").split(",")[6] >= "20260101"]
    t = open(OUT % "tsx-x14-a1" + "storage/printDone.csv", "rb").read().splitlines(keepends=True)
    # md5 dc62609b (PREREG §2) la md5 CUA CA FILE tsx (header + dong DEV). Phai so cung pham vi:
    # header cua ta + dong DEV cua ta. Ban cu bo header => luon lech (bug ky thuat, khong phai du lieu).
    mdev = hashlib.md5(hdr + b"".join(dev)).hexdigest()
    rdev = hashlib.md5(t[0] + b"".join(ln for ln in t[1:]
                                          if ln.decode(errors="ignore").split(",")[6:7] and
                                          ln.decode(errors="ignore").split(",")[6] < "20260101")).hexdigest()
    e26 = os.path.exists(OUT % tag_of("b0union", 42) + "storage/equity_summary.json")
    ok = mdev == rdev and len(y26) >= 800 and e26
    # chan doan (ADDENDUM_TECH-1: nt-x14 chi de doi chieu, khong lam cong)
    nref = None
    try:
        r26 = [ln for ln in open(OUT % "nt-x14-s42" + "storage/printDone.csv", "rb").read().splitlines()[1:]
               if ln.decode(errors="ignore").split(",")[6:7] and
               ln.decode(errors="ignore").split(",")[6] >= "20260101"]
        nref = len(r26)
    except Exception:  # noqa: BLE001
        pass
    return ("PASS" if ok else "FAIL"), {"dev_md5": mdev, "dev_ref": rdev,
                                        "n_dev": len(dev), "n_2026": len(y26), "eq26": e26,
                                        "n26_days": len({ln.decode(errors='ignore').split(",")[6][:8] for ln in y26}),
                                        "n26_ref_ntx14": nref}


def gates(st=None):
    st = st or load_state()
    g = {}
    s, d = gate_ok(st)
    g["G-B0UNION-DEV"] = dict(status=s, **d)
    json.dump(g, open(W + "/gates.json", "w"), indent=1)
    return g


def run():
    plan()
    jards()
    while True:
        try:
            st = poll()
            g = gates(st)
            log.info("GATE %s %s", g["G-B0UNION-DEV"]["status"],
                     json.dumps({k: v for k, v in g["G-B0UNION-DEV"].items() if k != "status"}))
            if g["G-B0UNION-DEV"]["status"] == "FAIL":
                log.error("G-DEV/G-2026 FAIL -> DUNG, bao MASTER")
                return
            p1a_ok = g["G-B0UNION-DEV"]["status"] == "PASS"
            st = load_state()
            todo = [e for e in plan() if st.get(e["tag"], {}).get("state") not in ("PUSHED", "DONE", "FAILED")
                    and (e["phase"] == "gate" or (e["phase"] == "p1a" and p1a_ok) or e["phase"] == "p1b")]
            active = [t for t, v in st.items() if v.get("state") == "PUSHED"]
            log.info("loop active=%d todo=%d", len(active), len(todo))
            for e in todo:
                if len(active) >= MAXPAR:
                    break
                push(e)
                active.append(e["tag"])
                time.sleep(30)
            rem = [e for e in plan() if load_state().get(e["tag"], {}).get("state") not in ("DONE", "FAILED")]
            if not rem:
                log.info("NUP4 XONG")
                return
        except Exception as ex:  # noqa: BLE001
            log.error("ORCH loi: %s", str(ex)[:300])
        time.sleep(POLL_S)


def status():
    st = load_state()
    for e in plan():
        v = st.get(e["tag"], {})
        print("%-16s %-8s %-10s %s" % (e["tag"], v.get("state", "-"), v.get("kstatus", ""),
                                       (v.get("check") or {}).get("checks", "")))
    print(json.dumps(gates(st), indent=1))


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    {"jards": jards, "run": run, "gates": lambda: print(json.dumps(gates(), indent=1)),
     "status": status}.get(c, lambda: sys.exit(__doc__))()
