#!/usr/bin/env python3
"""NUP2 runner — push/queue/fetch cho B1-B5 + A7 (PREREG_NUP2 + ADDENDUM TECH).

DEV dung tsx_driver.B.push (bundle sim-x1-2021-bundle, end 20251231, CPU 5 slot).
HO  dung ho4p1_queue.push (bundle 2026, unseal, end 20261001).
State: ~/claude_master/nup_wk/state.json

Usage:
  python3 run.py push-dev <arm|b0chk> <seed...>
  python3 run.py push-ho  <arm> <seed...>
  python3 run.py poll
  python3 run.py fetch <tag...>
  python3 run.py status
"""
import json
import logging
import socket
import os
import sys
import time
import datetime

W = "/home/ubuntu/claude_master/nup2_wk"
STATE = W + "/state.json"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
MAXPAR = 5
POLL = 60
SLOT_WINDOW_H = 4
_TERM = {}

socket.setdefaulttimeout(30)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("nup")

sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402

JAR_OLD = "cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe"
JAR_DS_OLD = "sim-jar-tsx"
JAR_NEW_PATH = "/home/ubuntu/claude_master/nup2_wk/sim.jar"
JAR_DS_NEW = "sim-jar-nup-tier2"


def sha256(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def jar_new_sha():
    if not os.path.exists(JAR_NEW_PATH):
        return None
    return sha256(JAR_NEW_PATH)


def free_slots():
    """Slot CPU con trong account, dem theo dateRun trong cua so 4h (sua loi ks.free_slots()).

    ks.free_slots() goc xep theo 'hotness' nen khong thay sim-* moi push va goi status
    moi kernel => 429. O day: kernels_list(mine, sort_by=dateRun), chi xet kernel co
    lastRunTime trong SLOT_WINDOW_H gio, cache trang thai ket thuc theo (ref,lastRunTime).
    Loi/429 khi hoi status => tinh la DANG CHAY (than trong).
    """
    ks = T.GA.ks_mod()
    api = ks._api()
    L = api.kernels_list(mine=True, page_size=50, sort_by="dateRun")
    now = datetime.datetime.utcnow()
    used = unknown = 0
    for k in L:
        lr = k.lastRunTime
        if lr is None or (now - lr).total_seconds() > SLOT_WINDOW_H * 3600:
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
    log.info("free_slots: listed=%d cached_term=%d used=%d unknown=%d", len(L), len(_TERM), used, unknown)
    return max(0, ks.MAX_CONCURRENT - used - unknown)


ARMS = {
    "b1": {"SIM_F_BASE": 0.006305},
    "b2": {"DCA_GRID_LEVELS": "-0.335,-0.5025,-0.603"},
    "b3": {"DCA_GRID_LEVELS": "-0.50,-0.60,-0.70,-0.80,-0.90",
           "DCA_GRID_WEIGHTS": "1,1,1,1,1,1"},
    "b4": {"SIM_U_MAX": 0.75},
    "b5": {"SIM_MIN_MOMENTUM_15M": 0.005},
    "a7": {"GATE_TIER2_ENABLED": "true", "GATE_TIER2_PCT": 0.99985, "GATE_TIER2_U_MAX": 0.20,
           "GATE_TIER2_CRASH_RET": -0.01, "GATE_TIER2_SIZE_MULT": 0.5},
}
NEWJAR_ARMS = {"a7"}


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(st):
    os.makedirs(W, exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def b1_fbase():
    f = W + "/b1_fbase.json"
    if not os.path.exists(f):
        raise SystemExit("B1 chua hieu chuan SIM_F_BASE (thieu %s)" % f)
    return float(json.load(open(f))["f_base"])


def ov_dev(arm, seed):
    ov = dict(T.B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=T.FLAGS["ranges"])
    if arm in ARMS:
        ov.update(ARMS[arm])
    return ov


def ov_ho(arm, seed, fl):
    q = ho_q()
    ov = dict(q.CFGS["k24"], SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=fl["ranges"])
    if arm in ARMS:
        ov.update(ARMS[arm])
    return ov


def push_dev(arm, seed):
    st = load_state()
    tag = ("nup-b0chk-" + seed.lower()) if arm == "b0chk" else ("nup-%s-%s" % (arm, seed.lower()))
    if st.get(tag, {}).get("state") in ("PUSHED", "DONE"):
        log.info("SKIP %s state=%s", tag, st[tag]["state"])
        return tag
    ov = ov_dev(arm, seed)
    jards = JAR_DS_NEW if arm in NEWJAR_ARMS else JAR_DS_OLD
    if jards == JAR_DS_NEW and jar_new_sha() is None:
        raise SystemExit("A7 jar chua build: %s" % JAR_NEW_PATH)
    T.B.JAR_DS = jards
    T.B.push(tag, ov, seed.upper() if not seed.isdigit() else int(seed))
    st[tag] = {"state": "PUSHED", "scope": "DEV", "arm": arm, "seed": seed, "ov": ov,
               "jar_ds": jards, "at": time.strftime("%F %T")}
    save_state(st)
    log.info("PUSHED %s jar_ds=%s", tag, jards)
    return tag


def push_dev_ov(tag, seed, ov_cell, jards="sim-jar-tsx"):
    st = load_state()
    if st.get(tag, {}).get("state") in ("PUSHED", "DONE"):
        log.info("SKIP %s state=%s", tag, st[tag]["state"])
        return tag
    ov = ov_dev("none", seed)
    ov.update(ov_cell)
    if jards == JAR_DS_NEW and jar_new_sha() is None:
        raise SystemExit("A7 jar chua build: %s" % JAR_NEW_PATH)
    T.B.JAR_DS = jards
    T.B.push(tag, ov, seed.upper() if not seed.isdigit() else int(seed))
    st[tag] = {"state": "PUSHED", "scope": "DEV", "arm": tag, "seed": seed, "ov": ov,
               "jar_ds": jards, "at": time.strftime("%F %T")}
    save_state(st)
    log.info("PUSHED %s jar_ds=%s", tag, jards)
    return tag


def orch_plan2(name):
    ks = T.GA.ks_mod()
    plan = json.load(open(W + "/plan_%s.json" % name))
    log.info("ORCH2 %s start plan=%d", name, len(plan))
    while True:
        try:
            st = poll()
            todo = [e for e in plan if st.get(e["tag"], {}).get("state") not in ("DONE", "FAILED")]
            pending = [e for e in todo if st.get(e["tag"], {}).get("state") != "PUSHED"]
            free = free_slots()
            done = len([e for e in plan if st.get(e["tag"], {}).get("state") == "DONE"])
            log.info("ORCH2 %s free=%d pending=%d active=%d done=%d", name, free, len(pending), len(todo) - len(pending), done)
            for e in pending:
                if free <= 0:
                    break
                if e.get("ov"):
                    push_dev_ov(e["tag"], e["seed"], e["ov"], e.get("jar", "sim-jar-tsx"))
                elif e["scope"] == "DEV":
                    push_dev(e["arm"], e["seed"])
                else:
                    fl = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))
                    push_ho(e["arm"], e["seed"], fl)
                free -= 1
                time.sleep(15)
            if not todo:
                log.info("ORCH2 %s XONG done=%d/%d", name, done, len(plan))
                return
        except Exception as ex:  # noqa: BLE001
            log.error("ORCH2 loi: %s", str(ex)[:300])
        time.sleep(90)


def ho_q():
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import ho4p1_queue as q
    logging.getLogger().removeHandler(q._fh)
    q.JAR_DS = JAR_DS_OLD
    q.JAR_SHA = sha256("/home/ubuntu/src_wt_bcd/target/binance-java-sdk-1.2.4.jar")
    return q


def push_ho(arm, seed, fl):
    st = load_state()
    tag = "nup-ho-%s-s%d" % (arm, int(seed))
    if st.get(tag, {}).get("state") in ("PUSHED", "DONE"):
        log.info("SKIP %s state=%s", tag, st[tag]["state"])
        return tag
    q = ho_q()
    ov = ov_ho(arm, seed, fl)
    jards = JAR_DS_NEW if arm in NEWJAR_ARMS else JAR_DS_OLD
    if jards == JAR_DS_NEW:
        js = jar_new_sha()
        if js is None:
            raise SystemExit("A7 jar chua build")
        q.JAR_DS, q.JAR_SHA = JAR_DS_NEW, js
    q.push(q.GA.ks_mod(), tag, ov, int(seed), "20261001", True)
    st[tag] = {"state": "PUSHED", "scope": "HO", "arm": arm, "seed": int(seed), "ov": ov,
               "jar_ds": jards, "at": time.strftime("%F %T")}
    save_state(st)
    log.info("PUSHED-HO %s jar_ds=%s", tag, jards)
    return tag


def ref(tag):
    return T.GA.ks_mod().kernel_ref(tag)


def poll(fetch_done=True):
    ks = T.GA.ks_mod()
    st = load_state()
    changed = False
    for tag, e in list(st.items()):
        if e.get("state") != "PUSHED":
            continue
        try:
            s = ks._status(ref(tag))
        except Exception as ex:  # noqa: BLE001
            msg = str(ex)
            if "404" in msg or "No runs found" in msg:
                # 404 ngay sau push la Kaggle chua dang ky version (transient) -> cho 20 phut
                age = (time.time() - time.mktime(time.strptime(e.get("at", "2026-01-01 00:00"), "%Y-%m-%d %H:%M"))) / 60
                if age < 20:
                    log.warning("status %s 404 nhung moi push %.1f phut -> thu lai", tag, age)
                else:
                    log.warning("status %s 404 -> FAILED", tag)
                    e["state"] = "FAILED"
                    e["kstatus"] = "NORUN"
                    changed = True
                    save_state(st)
            else:
                log.warning("status %s %s", tag, msg[:120])
            continue
        if s in ks.TERMINAL:
            log.info("%s -> %s", tag, s)
            e["kstatus"] = s
            if s == "COMPLETE":
                if fetch_done:
                    try:
                        ks.fetch(tag)
                        e["state"] = "DONE"
                    except Exception as ex:  # noqa: BLE001
                        log.error("fetch %s %s", tag, str(ex)[:200])
                        e["state"] = "FETCH_ERR"
            else:
                e["state"] = "FAILED"
            changed = True
            save_state(st)
    return st


def orch(name):
    ks = T.GA.ks_mod()
    plan = json.load(open(W + "/plan_%s.json" % name))
    fl = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))
    log.info("ORCH %s start plan=%d", name, len(plan))
    while True:
        try:
            st = poll()
            alltodo = [e for e in plan if st.get(e["tag"], {}).get("state") not in ("DONE", "FAILED")]
            pending = [e for e in alltodo if st.get(e["tag"], {}).get("state") not in ("PUSHED",)]
            active = len([e for e in alltodo if st.get(e["tag"], {}).get("state") == "PUSHED"])
            done = len([e for e in plan if st.get(e["tag"], {}).get("state") == "DONE"])
            if not alltodo:
                log.info("ORCH %s XONG done=%d/%d", name, done, len(plan))
                return
            free = max(0, MAXPAR - active)
            log.info("ORCH %s free=%d pending=%d active=%d done=%d", name, free, len(pending), active, done)
            for e in pending:
                if free <= 0:
                    break
                if e["scope"] == "DEV":
                    push_dev(e["arm"], e["seed"])
                else:
                    push_ho(e["arm"], e["seed"], fl)
                free -= 1
                time.sleep(20)
        except Exception as ex:  # noqa: BLE001
            log.error("ORCH loi: %s", str(ex)[:300])
        time.sleep(90)


def cmd_push(scope, arm, seeds):
    if scope == "dev":
        for s in seeds:
            push_dev(arm, s)
    else:
        fl = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))
        assert fl["v1"]["ok"] and fl["n_days"] > 0
        for s in seeds:
            push_ho(arm, s, fl)


def orch(name):
    ks = T.GA.ks_mod()
    plan = json.load(open(W + "/plan_%s.json" % name))
    fl = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))
    while True:
        st = poll()
        alltodo = [e for e in plan if st.get(e["tag"], {}).get("state") not in ("DONE", "FAILED")]
        pending = [e for e in alltodo if st.get(e["tag"], {}).get("state") not in ("PUSHED",)]
        done = [e for e in plan if st.get(e["tag"], {}).get("state") == "DONE"]
        if not alltodo:
            log.info("ORCH %s XONG done=%d/%d", name, len(done), len(plan))
            return
        free = free_slots()
        log.info("ORCH %s free=%d pending=%d active=%d done=%d", name, free, len(pending), len(alltodo) - len(pending), len(done))
        for e in pending:
            if free <= 0:
                break
            if e["scope"] == "DEV":
                push_dev(e["arm"], e["seed"])
            else:
                push_ho(e["arm"], e["seed"], fl)
            free -= 1
            time.sleep(30)
        time.sleep(180)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    c = sys.argv[1]
    if c == "push-dev":
        cmd_push("dev", sys.argv[2], sys.argv[3:])
    elif c == "push-ho":
        cmd_push("ho", sys.argv[2], sys.argv[3:])
    elif c == "poll":
        poll()
    elif c == "fetch":
        ks = T.GA.ks_mod()
        for t in sys.argv[2:]:
            ks.fetch(t)
    elif c == "orch":
        orch(sys.argv[2])
    elif c == "orch2":
        orch_plan2(sys.argv[2])
    elif c == "status":
        st = load_state()
        from collections import Counter
        print(Counter(v.get("state") for v in st.values()))
        for k, v in sorted(st.items()):
            if v.get("state") != "DONE":
                print(k, v.get("state"), v.get("kstatus", ""))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
