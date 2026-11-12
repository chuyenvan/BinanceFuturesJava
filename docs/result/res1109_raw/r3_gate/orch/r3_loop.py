#!/usr/bin/env python3
"""Vong tu chay R3/R3b tren Oracle (MASTER 11-11). Jar va + enable_internet=False ONLY. Tong kernel account <= 2 (kiem truoc MOI push).
Nhanh (moi nhanh DUNG khi co loi/verdict FAIL, ghi loop.log + loop_state.json):
  G0' : cho g0n_verdict.json (verify_g0n.py). FAIL => DUNG TOAN BO.
  G3  : r3-mtm-b1 COMPLETE -> fetch -> r3_score r3g3 (futility >=2/4 dCalmar<=0 => DUNG G3). Qua => push g3m 13/123/777/2024
        (r3_orch_m) -> MTM (doi chung r3g0n-a1) -> DUNG (MASTER cham 8 seed).
  B2  : push g0s-a1 (r3_orch_s) -> so byte n4f-b0-a1 + log AS_FILE. FAIL => DUNG B2. PASS => b2 42/7/21/99 -> MTM (doi chung g0s)
        -> r3_score r3b2 cua so 2023..2026 -> futility. Qua => b2 13/123/777/2024 -> MTM -> DUNG.
Dung khan: tao file loop.STOP. Han cung 48 h."""
import hashlib, json, os, re, subprocess, sys, time
sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r3_gate/orch")
import r3_orch_m as M
import r3_orch_s as S
OD = "/home/ubuntu/claude_master/res1109/r3_gate/orch/"
RES = "/home/ubuntu/claude_master/res1109/r3_gate/results/"
SC = "/home/ubuntu/claude_master/vz_e1_wt/research/r3_gate/r3_score.py"
LS = OD + "loop_state.json"
REF = "/home/ubuntu/claude_master/nup4_fix/results/n4f-b0-a1/storage/"
T_END = time.time() + 48 * 3600
log = M.log
ls = json.load(open(LS)) if os.path.exists(LS) else {"g3": "wait_mtm", "b2": "wait_g0n", "pushed": []}


def save():
    json.dump(ls, open(LS + ".tmp", "w"), indent=1); os.replace(LS + ".tmp", LS)


def L(msg):
    log.info("LOOP %s", msg)
    with open(OD + "loop.log", "a") as f:
        f.write(time.strftime("%FT%TZ ", time.gmtime()) + msg + "\n")


def status(tag):
    try:
        return M.KS._status(M.KS.kernel_ref(tag))
    except Exception as e:  # noqa: BLE001
        return "ERR?" + str(e)[:40]


def can_push():
    try:
        n = M.account_running()
    except Exception:  # noqa: BLE001
        return False
    return n <= 1


def push_sim(mod, arm, seed):
    st = mod.load_state()
    tag = mod.tag_of(arm, seed)
    if tag in st:
        return tag
    if not can_push():
        return None
    mod.jards()
    mod.push_sim(st, dict(tag=tag, arm=arm, seed=seed, phase="r3loop"))
    ls["pushed"].append(tag); save(); L("PUSH sim %s (%s)" % (tag, mod.__name__))
    return tag


def push_mtm(mod, tag, runs):
    st = mod.load_state()
    if tag in st:
        return True
    if not can_push():
        return False
    mod.push_mtm(st, dict(tag=tag, runs=runs))
    ls["pushed"].append(tag); save(); L("PUSH mtm %s runs=%s" % (tag, runs))
    return True


def all_done(tags):
    s = {t: status(t) for t in tags}
    if any(v in ("ERROR", "CANCEL_ACKNOWLEDGED", "CANCELLED") for v in s.values()):
        return "ERROR", s
    return ("DONE" if all(v == "COMPLETE" for v in s.values()) else "WAIT"), s


def fetch_mtm(mod, tag):
    o = mod.fetch_small(tag)
    r = json.load(open(o + "/mtm_result.json"))
    miss = {k: v["missing"] for k, v in r["runs"].items() if v["missing"]}
    ok = bool(r.get("ok")) and not miss and all(v["ok"] for v in r["controls"].values()) and len(r["controls"]) >= 1
    return ok, {"ok": r.get("ok"), "miss": miss, "controls": {k: (round(v["dd_dev"], 4), round(v["ref"], 4)) for k, v in r["controls"].items()}}


def score(prefix, out, win=None):
    cmd = [sys.executable, SC, prefix, out] + (list(win) if win else [])
    rc = subprocess.call(cmd, stdout=open(OD + "score.log", "a"), stderr=subprocess.STDOUT)
    if rc != 0:
        return None
    return json.load(open(out))


def verify_g0(mod, tag, out):
    o = mod.fetch_small(tag)
    rj = json.load(open(o + "/result.json"))
    md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
    a = mod.KS._api()
    r = a.process_response(a.kernel_output_with_http_info(user_name="chuyendinh", kernel_slug=mod.kslug(tag)))
    lg = r.get("log") or ""
    m = re.search(r"AS_FILE_CHECK OK ([^\"\\\\]*)", lg)
    v = dict(tag=tag, ok=rj.get("ok"), jar=rj.get("jar_sha256") == mod.JAR_SHA, pd=md5(o + "/storage/printDone.csv"),
             pd_ref=md5(REF + "printDone.csv"),
             es_same=open(o + "/storage/equity_summary.json", "rb").read() == open(REF + "equity_summary.json", "rb").read(),
             as_check=m.group(1) if m else None, preflight_tcp="PREFLIGHT mapper host" in lg)
    v["PASS"] = bool(v["ok"] and v["jar"] and v["pd"] == v["pd_ref"] and v["es_same"] and v["as_check"] and not v["preflight_tcp"])
    json.dump(v, open(out, "w"), indent=1)
    return v


G3R = [13, 123, 777, 2024]
B2A, B2B = [42, 7, 21, 99], [13, 123, 777, 2024]
L("START state=%s" % {k: v for k, v in ls.items() if k != "pushed"})
while True:
    if os.path.exists(OD + "loop.STOP") or time.time() > T_END:
        L("DUNG: loop.STOP/han"); break
    # ---- G0'
    if not os.path.exists(OD + "g0n_verdict.json"):
        time.sleep(120); continue
    g0n = json.load(open(OD + "g0n_verdict.json"))
    if not g0n.get("PASS"):
        L("DUNG TOAN BO: G0' FAIL %s" % g0n); ls["g3"] = ls["b2"] = "STOP_G0N_FAIL"; save(); break
    if ls["b2"] == "wait_g0n":
        ls["b2"] = "g0s_push"; save(); L("G0' PASS -> mo nhanh B2")
    # ---- G3
    if ls["g3"] == "wait_mtm":
        s = status("r3-mtm-b1")
        if s == "COMPLETE":
            ok, info = fetch_mtm(M, "r3-mtm-b1")
            if not ok:
                ls["g3"] = "STOP_MTM_BAD"; save(); L("G3 DUNG: MTM b1 khong hop le %s" % info)
            else:
                f = score("r3g3", OD + "g3_futility.json")
                if f is None:
                    ls["g3"] = "STOP_SCORE_ERR"; save(); L("G3 DUNG: loi cham")
                else:
                    L("G3 FUTILITY %s dCalmar=%s" % (f["futility"], {k: v["d_calmar"] for k, v in f["seeds"].items()}))
                    ls["g3"] = "STOP_FUTILITY" if f["futility"]["STOP"] else "push_rest"; save()
        elif s in ("ERROR", "CANCEL_ACKNOWLEDGED"):
            ls["g3"] = "STOP_MTM_ERR"; save(); L("G3 DUNG: MTM b1 %s" % s)
    if ls["g3"] == "push_rest":
        tags = [push_sim(M, "g3m", s_) for s_ in G3R]
        if all(tags):
            ls["g3"] = "wait_rest"; ls["g3_rest"] = tags; save()
    if ls["g3"] == "wait_rest":
        st_, d = all_done(ls["g3_rest"])
        if st_ == "ERROR":
            ls["g3"] = "STOP_KERNEL_ERR"; save(); L("G3 DUNG: kernel loi %s" % d)
        elif st_ == "DONE" and push_mtm(M, "r3-mtm-g3r", ["r3g0n-a1"] + ls["g3_rest"]):
            ls["g3"] = "wait_mtm_rest"; save()
    if ls["g3"] == "wait_mtm_rest":
        s = status("r3-mtm-g3r")
        if s == "COMPLETE":
            ok, info = fetch_mtm(M, "r3-mtm-g3r")
            ls["g3"] = "DONE_8SEED_CHO_MASTER" if ok else "STOP_MTM_BAD"; save(); L("G3 MTM rest %s %s -> DUNG nhanh G3" % (ok, info))
        elif s in ("ERROR", "CANCEL_ACKNOWLEDGED"):
            ls["g3"] = "STOP_MTM_ERR"; save(); L("G3 DUNG: MTM rest %s" % s)
    # ---- B2
    if ls["b2"] == "g0s_push" and push_sim(S, "g0s", 42):
        ls["b2"] = "g0s_wait"; save()
    if ls["b2"] == "g0s_wait":
        s = status("r3g0s-a1")
        if s == "COMPLETE":
            time.sleep(60)
            v = verify_g0(S, "r3g0s-a1", OD + "g0s_verdict.json")
            L("G0s VERDICT %s" % v)
            ls["b2"] = "push_a" if v["PASS"] else "STOP_G0S_FAIL"; save()
        elif s in ("ERROR", "CANCEL_ACKNOWLEDGED"):
            ls["b2"] = "STOP_G0S_ERR"; save(); L("B2 DUNG: g0s %s" % s)
    for ph, seeds, nxt, mt in (("a", B2A, "futility", "r3-mtm-b2a"), ("b", B2B, "DONE_8SEED_CHO_MASTER", "r3-mtm-b2b")):
        if ls["b2"] == "push_" + ph:
            tags = [push_sim(S, "b2", s_) for s_ in seeds]
            if all(tags):
                ls["b2"] = "wait_" + ph; ls["b2_" + ph] = tags; save()
        if ls["b2"] == "wait_" + ph:
            st_, d = all_done(ls["b2_" + ph])
            if st_ == "ERROR":
                ls["b2"] = "STOP_KERNEL_ERR"; save(); L("B2 DUNG: kernel loi %s" % d)
            elif st_ == "DONE" and push_mtm(S, mt, ["r3g0s-a1"] + ls["b2_" + ph]):
                ls["b2"] = "mtm_" + ph; save()
        if ls["b2"] == "mtm_" + ph:
            s = status(mt)
            if s == "COMPLETE":
                ok, info = fetch_mtm(S, mt)
                if not ok:
                    ls["b2"] = "STOP_MTM_BAD"; save(); L("B2 DUNG: MTM %s %s" % (mt, info)); continue
                if ph == "a":
                    f = score("r3b2", OD + "b2_futility.json", ("2023-01-01", "2026-01-01"))
                    if f is None:
                        ls["b2"] = "STOP_SCORE_ERR"; save(); L("B2 DUNG: loi cham"); continue
                    L("B2 FUTILITY %s dCalmar=%s" % (f["futility"], {k: v["d_calmar"] for k, v in f["seeds"].items()}))
                    ls["b2"] = "STOP_FUTILITY" if f["futility"]["STOP"] else "push_b"; save()
                else:
                    ls["b2"] = nxt; save(); L("B2 MTM b xong -> DUNG nhanh B2, cho MASTER cham 8 seed")
            elif s in ("ERROR", "CANCEL_ACKNOWLEDGED"):
                ls["b2"] = "STOP_MTM_ERR"; save(); L("B2 DUNG: MTM %s %s" % (mt, s))
    term = lambda x: x.startswith("STOP") or x.startswith("DONE")
    if term(ls["g3"]) and term(ls["b2"]):
        L("KET THUC: g3=%s b2=%s" % (ls["g3"], ls["b2"])); break
    time.sleep(120)
