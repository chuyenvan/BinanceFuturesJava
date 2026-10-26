#!/usr/bin/env python3
"""NUP3 orchestrator (PREREG_NUP3 c2b4c462 + ADDENDUM_TECH) — CHI push / poll / keo ket qua + cong KY THUAT.
KHONG cham diem, KHONG chon Pha 2 (MASTER duyet).

  python3 orch.py jards    # dataset private sim-jar-nup3-sleeve (sau kiem sha + bao mat)
  python3 orch.py flagds   # dataset private nup3-mkt-flag
  python3 orch.py run      # vong lap (nohup): cong G-OFF a1/s7 + G-INV (= nup3-v0-a1) + smoke V2 -> PASS -> Pha 1
  python3 orch.py gates    # tinh lai cong tu output da keo
  python3 orch.py status
State ~/claude_master/nup3_wk/state.json, cong ~/claude_master/nup3_wk/gates.json, log ~/claude_master/nup3_wk/orch.log
Chi push khi ks.free_slots() > 0 (slot CPU toan account; khong dung toi kernel/tien trinh cua NUP2).
"""
import hashlib
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
import datetime

socket.setdefaulttimeout(60)
sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402  (ha tang B0: OV_BASE, ngay X14, GA/G kaggle)

GA, G = T.GA, T.G
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("nup3")

W = "/home/ubuntu/claude_master/nup3_wk"
STATE, GATES = W + "/state.json", W + "/gates.json"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
JAR_SRC = "/home/ubuntu/src_nup3/target/binance-java-sdk-1.2.4.jar"
JAR_SHA = "b269f96b782275a8089bbae1532f8c68e1aab18cba602bf02ee2a64b3adda051"
JAR_DS, FLAG_DS = "sim-jar-nup3-sleeve", "nup3-mkt-flag"
FLAG_FILE, FLAG_MD5 = "nup3_mkt_flag.csv", "f3435d9baa5841dca541c3b39e4dddb2"
FLAG_INTERVALS, FLAG_MINUTES = 2121, 91482
CODE_SHA = "c80d87c2"
TIMEOUT = 10800
PROF_SRC = "/home/ubuntu/claude_master/tsx/ds_sim-jar-tsx/prof_r4_kg0_k16_f015_g155.properties"
SEC = "/home/ubuntu/claude_master/vz_e1_wt/research/nup3/jar_sec_check.py"
B0 = {"A1": ("tsx-x14-a1", "dc62609b6d7169093c001f2ce0d198ed"),
      "S7": ("tsx-x14-s7", "622b03e264fdd0b59a1673e144f4148f")}
SLEEVE = dict(SLEEVE_ENABLED="true", SLEEVE_PCT=0.99985, SLEEVE_SIZE_MULT=1.0, SLEEVE_U_MAX=0.35,
              SLEEVE_BURST_N=10, SLEEVE_BURST_MIN=60)
ARMS = {"v0": dict(SLEEVE, SLEEVE_ARM="V0"), "v1": dict(SLEEVE, SLEEVE_ARM="V1"),
        "v2": dict(SLEEVE, SLEEVE_ARM="V2", SLEEVE_MKT_FLAG_FILE=FLAG_FILE)}
P1_SEEDS = ["A1", "S7", "S21", "S99"]


def ov_base():
    ov = dict(T.B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=T.FLAGS["ranges"])
    b0 = json.load(open(OUT % B0["A1"][0] + "result.json"))["overrides"]
    assert {k: str(v) for k, v in ov.items()} == {k: str(v) for k, v in b0.items()}, "override nen != B0 tsx-x14-a1"
    return ov


def plan():
    P = [dict(tag="nup3-goff-a1", seed="A1", phase="gate", ov=dict(SLEEVE_ENABLED="false")),
         dict(tag="nup3-goff-s7", seed="S7", phase="gate", ov=dict(SLEEVE_ENABLED="false")),
         dict(tag="nup3-v0-a1", seed="A1", phase="gate", ov=ARMS["v0"]),            # = cong G-INV + run Pha 1
         dict(tag="nup3-smk-v2", seed="A1", phase="gate", ov=ARMS["v2"], end="20210731", extra=[FLAG_DS])]
    for arm in ("v0", "v1", "v2"):
        for s in P1_SEEDS:
            t = "nup3-%s-%s" % (arm, s.lower())
            if t == "nup3-v0-a1":
                continue
            P.append(dict(tag=t, seed=s, phase="p1", arm=arm, ov=ARMS[arm], extra=[FLAG_DS] if arm == "v2" else []))
    return P


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(st):
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def md5b(b):
    return hashlib.md5(b).hexdigest()


def md5f(p):
    return md5b(open(p, "rb").read())


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ datasets
def _create_ds(fol, name):
    ks = GA.ks_mod()
    json.dump({"title": name, "id": ks.USER + "/" + name, "licenses": [{"name": "CC0-1.0"}]},
              open(fol + "/dataset-metadata.json", "w"))
    r = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
    log.info("dataset %s -> %s", name, getattr(r, "url", r) or getattr(r, "error", r))
    for _ in range(60):
        try:
            s = ks._api().dataset_status(ks.USER + "/" + name)
        except Exception as e:  # noqa: BLE001
            s = "err:%s" % str(e)[:80]
        log.info("dataset %s status %s", name, s)
        if str(s).lower() == "ready":
            return True
        time.sleep(30)
    return False


def jards():
    G.disk("truoc jards")
    fol = W + "/ds_" + JAR_DS
    os.makedirs(fol, exist_ok=True)
    shutil.copy(JAR_SRC, fol + "/sim.jar")
    assert sha256f(fol + "/sim.jar") == JAR_SHA, "jar sha lech"
    rc = subprocess.call([sys.executable, "-I", SEC, fol + "/sim.jar", W + "/jar_sec_upload.json"])
    assert rc == 0, "KIEM BAO MAT JAR FAIL -> KHONG upload"
    assert md5f(PROF_SRC) == G.PROF_MD5
    shutil.copy(PROF_SRC, fol + "/" + os.path.basename(PROF_SRC))
    assert _create_ds(fol, JAR_DS), "dataset jar chua ready"


def flagds():
    fol = W + "/ds_" + FLAG_DS
    assert md5f(fol + "/" + FLAG_FILE) == FLAG_MD5
    m = json.load(open(fol + "/nup3_mkt_flag_meta.json"))
    assert m["n_intervals"] == FLAG_INTERVALS and m["n_flag_minutes"] == FLAG_MINUTES and m["indep_mismatch"] == 0
    assert _create_ds(fol, FLAG_DS), "dataset co chua ready"


# ------------------------------------------------------------------ push / poll
def push(e):
    ks = GA.ks_mod()
    G.disk("truoc push " + e["tag"])
    ov = ov_base()
    ov.update(e["ov"])
    end, extra, tag = e.get("end", "20251231"), e.get("extra") or [], e["tag"]
    dsn, md5 = G.pred_of(e["seed"])
    if dsn is None:
        ks.submit(tag, GA.PROFILE, ov, jar_ds=JAR_DS, bundle_ds=GA.BUNDLE, extra_ds=extra, sim_end_date=end,
                  xmx="22g", timeout_s=TIMEOUT, code_sha=CODE_SHA)
    else:
        ref = ks.kernel_ref(tag)
        folder = os.path.join(ks.WORKDIR, ks.slug(tag))
        os.makedirs(folder, exist_ok=True)
        cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": ov, "sim_end_date": end, "xmx": "22g",
               "timeout_s": TIMEOUT, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
               "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
               "pred_ds": dsn, "want_pred_md5": md5, "want_pred_base": GA.PRED0_MD5}
        with open(os.path.join(folder, "run.py"), "w") as f:
            f.write(GA.template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
        md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
              "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
              "dataset_sources": [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS
              + [ks.USER + "/" + JAR_DS, ks.USER + "/" + dsn] + [ks.USER + "/" + d for d in extra],
              "competition_sources": [], "kernel_sources": []}
        with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
            json.dump(md, f, indent=1)
        ks._api().kernels_push(folder)
    st = load_state()
    st[tag] = {"state": "PUSHED", "seed": e["seed"], "phase": e["phase"], "ov": ov, "end": end, "extra": extra,
               "jar_ds": JAR_DS, "at": time.strftime("%F %T"), "t": time.time()}
    save_state(st)
    log.info("PUSHED %s seed=%s end=%s extra=%s sleeve=%s", tag, e["seed"], end, extra,
             {k: v for k, v in ov.items() if k.startswith("SLEEVE")})


def check_run(tag, e):
    """Kiem ky thuat 1 run da keo: ok, jar sha, prof_run = B0 + DUNG tap key sleeve."""
    rj = OUT % tag + "result.json"
    if not os.path.exists(rj):
        return {"ok": False, "why": "no result.json"}
    r = json.load(open(rj))
    pr = GA.prof_run(tag)
    b0 = GA.prof_run("tsx-x14-" + e["seed"].lower())     # B0 CUNG seed
    assert b0, "thieu prof_run B0 seed %s" % e["seed"]
    diff = sorted(k for k in set(pr) | set(b0) if pr.get(k) != b0.get(k))
    want = sorted(k for k in e["ov"] if k.startswith("SLEEVE"))
    c = {"java_ok": r.get("ok") is True, "jar": r.get("jar_sha256") == JAR_SHA, "keys": diff == want,
         "pdone": os.path.exists(OUT % tag + "storage/printDone.csv")}
    return {"ok": all(c.values()), "checks": c, "diff_keys": diff, "n_trades": r.get("n_trades"),
            "secs": r.get("secs"), "equity_final_base": r.get("equity_final")}


def poll():
    ks = GA.ks_mod()
    st = load_state()
    P = {e["tag"]: e for e in plan()}
    for tag, e in list(st.items()):
        if e.get("state") != "PUSHED":
            continue
        try:
            s = ks._status(ks.kernel_ref(tag))
        except Exception as ex:  # noqa: BLE001
            msg = str(ex)
            if ("404" in msg or "No runs" in msg) and time.time() - e.get("t", 0) > 1800:
                e["state"], e["kstatus"] = "FAILED", "NORUN"
                save_state(st)
            log.warning("status %s %s", tag, msg[:120])
            continue
        if s in ks.TERMINAL:
            e["kstatus"] = s
            log.info("%s -> %s", tag, s)
            try:
                ks.fetch(tag)
            except Exception as ex:  # noqa: BLE001
                log.error("fetch %s %s", tag, str(ex)[:200])
            if s == "COMPLETE" and tag in P:
                e["check"] = check_run(tag, P[tag])
                e["state"] = "DONE" if e["check"]["ok"] else "FAILED"
            else:
                e["state"] = "FAILED"
            save_state(st)
    return st


# ------------------------------------------------------------------ cong
def gates(st=None):
    st = st or load_state()
    g = {}
    for seed, tag in (("A1", "nup3-goff-a1"), ("S7", "nup3-goff-s7")):
        e = st.get(tag, {})
        if e.get("state") != "DONE":
            g["G-OFF-" + seed] = {"status": "FAIL" if e.get("state") == "FAILED" else "PENDING"}
            continue
        b0t, b0m = B0[seed]
        m_b0 = md5f(OUT % b0t + "storage/printDone.csv")
        m = md5f(OUT % tag + "storage/printDone.csv")
        g["G-OFF-" + seed] = {"status": "PASS" if (m == b0m == m_b0) else "FAIL", "md5": m, "b0_md5": m_b0}
    e = st.get("nup3-v0-a1", {})
    if e.get("state") != "DONE":
        g["G-INV-A1"] = {"status": "FAIL" if e.get("state") == "FAILED" else "PENDING"}
    else:
        raw = open(OUT % "nup3-v0-a1" + "storage/printDone.csv", "rb").read().splitlines(keepends=True)
        base = [ln for ln in raw if b"book=sleeve" not in ln]
        n_sl = len(raw) - len(base)
        mb = md5b(b"".join(base))
        sm = OUT % "nup3-v0-a1" + "storage/sleeve_summary.json"
        summ = json.load(open(sm)) if os.path.exists(sm) else {}
        g["G-INV-A1"] = {"status": "PASS" if (mb == B0["A1"][1] and n_sl >= 1) else "FAIL", "md5_base_filtered": mb,
                         "b0_md5": B0["A1"][1], "n_sleeve_rows": n_sl, "n_rows": len(raw) - 1,
                         "u_total_max": summ.get("u_total_max"), "u_total_ok": summ.get("u_total_ok"),
                         "opened": summ.get("opened"), "overlap": summ.get("overlap_base_opens_sleeve_sym")}
    e = st.get("nup3-smk-v2", {})
    if e.get("state") not in ("DONE", "FAILED"):
        g["SMOKE-V2"] = {"status": "PENDING"}
    else:
        lp = OUT % "nup3-smk-v2" + "logs/sim.out"
        txt = open(lp, errors="ignore").read() if os.path.exists(lp) else ""
        ok = ("BAT arm=V2" in txt and ("intervals=%d flagMinutes=%d" % (FLAG_INTERVALS, FLAG_MINUTES)) in txt
              and "FAIL-FAST" not in txt and e.get("state") == "DONE")
        g["SMOKE-V2"] = {"status": "PASS" if ok else "FAIL", "run_state": e.get("state")}
    json.dump(g, open(GATES, "w"), indent=1)
    return g


_TERM = {}


def free_slots():
    """Slot CPU trong cua account. ks.free_slots() goc chi xet 50 kernel theo 'hotness' (khong thay sim-* moi chay)
    va goi status moi kernel => 429. O day: list theo dateRun, chi xet kernel chay trong 12,5h, cache trang thai
    ket thuc theo (ref, lastRunTime); loi/429 => tinh la DANG CHAY (than trong)."""
    ks = GA.ks_mod()
    L = ks._api().kernels_list(mine=True, page_size=50, sort_by="dateRun")
    now = datetime.datetime.utcnow()
    used = unknown = 0
    for k in L:
        lr = k.lastRunTime
        if lr is None or (now - lr).total_seconds() > 12.5 * 3600:
            continue
        key = (k.ref, str(lr))
        if key in _TERM:
            continue
        try:
            s = ks._status(k.ref)
        except Exception:  # noqa: BLE001
            unknown += 1
            time.sleep(5)
            continue
        if s in ks.TERMINAL:
            _TERM[key] = s
        elif s in ("RUNNING", "QUEUED"):
            used += 1
        else:
            unknown += 1
        time.sleep(1)
    return max(0, ks.MAX_CONCURRENT - used - unknown), used, unknown


def run():
    P = plan()
    log.info("ORCH NUP3 start plan=%d jar=%s code=%s", len(P), JAR_SHA[:8], CODE_SHA)
    ov_base()
    while True:
        try:
            st = poll()
            g = gates(st)
            main_ok = all(g[k]["status"] == "PASS" for k in ("G-OFF-A1", "G-OFF-S7", "G-INV-A1"))
            main_fail = any(g[k]["status"] == "FAIL" for k in ("G-OFF-A1", "G-OFF-S7", "G-INV-A1"))
            v2_ok = g["SMOKE-V2"]["status"] == "PASS"
            allowed = [e for e in P if e["phase"] == "gate"
                       or (main_ok and (e.get("arm") != "v2" or v2_ok))]
            todo = [e for e in allowed if st.get(e["tag"], {}).get("state") not in ("PUSHED", "DONE", "FAILED")]
            term = [e for e in P if st.get(e["tag"], {}).get("state") in ("DONE", "FAILED")]
            active = [t for t, v in st.items() if v.get("state") == "PUSHED"]
            free, used, unk = free_slots() if todo else (0, -1, -1)
            log.info("ORCH gates=%s free=%d (used=%d unknown=%d) todo=%d active=%s done/failed=%d/%d",
                     {k: v["status"] for k, v in g.items()}, free, used, unk, len(todo), active, len(term), len(P))
            if main_fail:
                log.error("CONG FAIL -> KHONG push Pha 1 (cho MASTER)")
            for e in todo:
                if free <= 0:
                    break
                push(e)
                free -= 1
                time.sleep(20)
            stop_fail = main_fail and not active
            v2_blocked = g["SMOKE-V2"]["status"] == "FAIL"
            remaining = [e for e in P if st.get(e["tag"], {}).get("state") not in ("DONE", "FAILED")
                         and not (v2_blocked and e.get("arm") == "v2")]
            if stop_fail or not remaining:
                log.info("ORCH NUP3 XONG (stop_fail=%s) states=%s", stop_fail,
                         {t: v.get("state") for t, v in load_state().items()})
                return
        except Exception as ex:  # noqa: BLE001
            log.error("ORCH loi: %s", str(ex)[:300])
        time.sleep(240)


def status():
    st = load_state()
    for e in plan():
        v = st.get(e["tag"], {})
        print("%-14s %-8s %-10s %s" % (e["tag"], v.get("state", "-"), v.get("kstatus", ""), v.get("check", {}).get("checks", "")))
    print(json.dumps(gates(st), indent=1))


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    {"jards": jards, "flagds": flagds, "run": run, "gates": lambda: print(json.dumps(gates(), indent=1)),
     "status": status}.get(c, lambda: sys.exit(__doc__))()
