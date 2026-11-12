#!/usr/bin/env python3
"""Vong tu chay R5P2 (prereg f2222d05) tren Oracle. Jar af97f2ae (AS-FILE, internet off). Tong kernel account <= 2 truoc MOI push.
Buoc: G0q (co tat) -> so byte n4f-b0-a1 (FAIL => DUNG) -> M1 + M0 seed 42/7/21/99 -> MTM r3-mtm-r5a (doi chung g0q)
-> cham futility M1 (>=2/4 dCalmar<=0 => DUNG) + M0 mo ta -> qua: M1 13/123/777/2024 -> MTM r3-mtm-r5b -> DUNG (MASTER cham).
Dung khan: file r5p2.STOP. Han 36 h. Log r5p2_loop.log, trang thai r5p2_state.json."""
import hashlib, json, os, re, subprocess, sys, time
sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r3_gate/orch")
import r3_orch_q as Q
OD = "/home/ubuntu/claude_master/res1109/r3_gate/orch/"
SC = "/home/ubuntu/claude_master/vz_e1_wt/research/r3_gate/r3_score.py"
LS = OD + "r5p2_state.json"
REF = "/home/ubuntu/claude_master/nup4_fix/results/n4f-b0-a1/storage/"
T_END = time.time() + 36 * 3600
ls = json.load(open(LS)) if os.path.exists(LS) else {"st": "g0_push", "pushed": []}


def save():
    json.dump(ls, open(LS + ".tmp", "w"), indent=1); os.replace(LS + ".tmp", LS)


def L(msg):
    Q.log.info("R5P2 %s", msg)
    with open(OD + "r5p2_loop.log", "a") as f:
        f.write(time.strftime("%FT%TZ ", time.gmtime()) + msg + "\n")


def status(tag):
    try:
        return Q.KS._status(Q.KS.kernel_ref(tag))
    except Exception as e:  # noqa: BLE001
        return "ERR?" + str(e)[:40]


def can_push():
    try:
        return Q.account_running() <= 1
    except Exception:  # noqa: BLE001
        return False


def push_sim(arm, seed):
    st = Q.load_state(); tag = Q.tag_of(arm, seed)
    if tag in st:
        return tag
    if not can_push():
        return None
    Q.jards(); Q.push_sim(st, dict(tag=tag, arm=arm, seed=seed, phase="r5p2"))
    ls["pushed"].append(tag); save(); L("PUSH sim %s" % tag)
    return tag


def push_mtm(tag, runs):
    st = Q.load_state()
    if tag in st:
        return True
    if not can_push():
        return False
    Q.push_mtm(st, dict(tag=tag, runs=runs)); ls["pushed"].append(tag); save(); L("PUSH mtm %s %s" % (tag, runs))
    return True


def done(tags):
    s = {t: status(t) for t in tags}
    if any(v in ("ERROR", "CANCEL_ACKNOWLEDGED", "CANCELLED") for v in s.values()):
        return "ERROR", s
    return ("DONE" if all(v == "COMPLETE" for v in s.values()) else "WAIT"), s


def mtm_ok(tag):
    o = Q.fetch_small(tag); r = json.load(open(o + "/mtm_result.json"))
    miss = {k: v["missing"] for k, v in r["runs"].items() if v["missing"]}
    return bool(r.get("ok")) and not miss and all(v["ok"] for v in r["controls"].values()) and len(r["controls"]) >= 1, miss


def score(prefix, out):
    rc = subprocess.call([sys.executable, SC, prefix, out], stdout=open(OD + "score.log", "a"), stderr=subprocess.STDOUT)
    return json.load(open(out)) if rc == 0 else None


A4, R4 = [42, 7, 21, 99], [13, 123, 777, 2024]
L("START %s" % ls["st"])
while True:
    if os.path.exists(OD + "r5p2.STOP") or time.time() > T_END:
        L("DUNG: STOP/han"); break
    s_ = ls["st"]
    if s_ == "g0_push" and push_sim("g0q", 42):
        ls["st"] = "g0_wait"; save()
    elif s_ == "g0_wait":
        k = status("r3g0q-a1")
        if k == "COMPLETE":
            time.sleep(60)
            o = Q.fetch_small("r3g0q-a1"); rj = json.load(open(o + "/result.json"))
            md5 = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
            a = Q.KS._api(); lg = a.process_response(a.kernel_output_with_http_info(user_name="chuyendinh", kernel_slug=Q.kslug("r3g0q-a1"))).get("log") or ""
            m = re.search(r"AS_FILE_CHECK OK ([^\"\\\\]*)", lg)
            v = dict(ok=rj.get("ok"), jar=rj.get("jar_sha256") == Q.JAR_SHA, pd=md5(o + "/storage/printDone.csv"), pd_ref=md5(REF + "printDone.csv"),
                     es_same=open(o + "/storage/equity_summary.json", "rb").read() == open(REF + "equity_summary.json", "rb").read(),
                     as_check=m.group(1) if m else None, preflight_tcp="PREFLIGHT mapper host" in lg)
            v["PASS"] = bool(v["ok"] and v["jar"] and v["pd"] == v["pd_ref"] and v["es_same"] and v["as_check"] and not v["preflight_tcp"])
            json.dump(v, open(OD + "g0q_verdict.json", "w"), indent=1); L("G0q VERDICT %s" % v)
            ls["st"] = "push_a" if v["PASS"] else "STOP_G0_FAIL"; save()
        elif k in ("ERROR", "CANCEL_ACKNOWLEDGED"):
            ls["st"] = "STOP_G0_ERR"; save(); L("DUNG: g0q %s" % k)
    elif s_ == "push_a":
        tags = [push_sim(a_, sd) for a_ in ("m1", "m0") for sd in A4]
        if all(tags):
            ls["a"] = tags; ls["st"] = "wait_a"; save()
    elif s_ == "wait_a":
        d, info = done(ls["a"])
        if d == "ERROR":
            ls["st"] = "STOP_KERNEL_ERR"; save(); L("DUNG: kernel loi %s" % info)
        elif d == "DONE" and push_mtm("r3-mtm-r5a", ["r3g0q-a1"] + ls["a"]):
            ls["st"] = "mtm_a"; save()
    elif s_ == "mtm_a":
        k = status("r3-mtm-r5a")
        if k == "COMPLETE":
            ok, miss = mtm_ok("r3-mtm-r5a")
            if not ok:
                ls["st"] = "STOP_MTM_BAD"; save(); L("DUNG: MTM a khong hop le %s" % miss); continue
            f1 = score("r3m1", OD + "r5p2_m1_futility.json"); f0 = score("r3m0", OD + "r5p2_m0_diag.json")
            if f1 is None:
                ls["st"] = "STOP_SCORE_ERR"; save(); L("DUNG: loi cham"); continue
            L("M1 FUTILITY %s dCalmar=%s" % (f1["futility"], {k_: v["d_calmar"] for k_, v in f1["seeds"].items()}))
            if f0:
                L("M0 (chan doan) dCalmar=%s" % {k_: v["d_calmar"] for k_, v in f0["seeds"].items()})
            ls["st"] = "STOP_FUTILITY" if f1["futility"]["STOP"] else "push_b"; save()
        elif k in ("ERROR", "CANCEL_ACKNOWLEDGED"):
            ls["st"] = "STOP_MTM_ERR"; save(); L("DUNG: MTM a %s" % k)
    elif s_ == "push_b":
        tags = [push_sim("m1", sd) for sd in R4]
        if all(tags):
            ls["b"] = tags; ls["st"] = "wait_b"; save()
    elif s_ == "wait_b":
        d, info = done(ls["b"])
        if d == "ERROR":
            ls["st"] = "STOP_KERNEL_ERR"; save(); L("DUNG: kernel loi %s" % info)
        elif d == "DONE" and push_mtm("r3-mtm-r5b", ["r3g0q-a1"] + ls["b"]):
            ls["st"] = "mtm_b"; save()
    elif s_ == "mtm_b":
        k = status("r3-mtm-r5b")
        if k == "COMPLETE":
            ok, miss = mtm_ok("r3-mtm-r5b")
            ls["st"] = "DONE_8SEED_CHO_MASTER" if ok else "STOP_MTM_BAD"; save(); L("MTM b %s %s -> DUNG" % (ok, miss))
        elif k in ("ERROR", "CANCEL_ACKNOWLEDGED"):
            ls["st"] = "STOP_MTM_ERR"; save(); L("DUNG: MTM b %s" % k)
    if ls["st"].startswith("STOP") or ls["st"].startswith("DONE"):
        L("KET THUC %s" % ls["st"]); break
    time.sleep(120)
