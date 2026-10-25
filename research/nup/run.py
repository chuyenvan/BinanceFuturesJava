#!/usr/bin/env python3
"""NUP runner — push/queue/fetch cho 7 arm (§1 PREREG_NUP.md).

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
import os
import sys
import time

W = "/home/ubuntu/claude_master/nup_wk"
STATE = W + "/state.json"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
MAXPAR = 5
POLL = 60

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("nup")

sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402

JAR_OLD = "cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe"
JAR_DS_OLD = "sim-jar-tsx"
JAR_NEW_PATH = "/home/ubuntu/src_nup/dist/sim.jar"
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


ARMS = {
    "a1": {"SIM_GATE_ROLLING_PCT": 0.99990},
    "a2": {"SIM_GATE_ROLLING_PCT": 0.99985},
    "a3": {"SELECTOR_RANK_TOPK": 32},
    "a4": {"SELECTOR_RANK_TOPK": 32, "SIM_GATE_ROLLING_PCT": 0.99990},
    "a5": {"SIM_GATE_DYN_SCALE": 1.30},
    "a6": {"SELECTOR_RANK_TOPK": 32, "SIM_GATE_ROLLING_PCT": 0.99990},
    "a7": {"GATE_TIER2_ENABLED": "true", "GATE_TIER2_PCT": 0.99985, "GATE_TIER2_U_MAX": 0.20,
           "GATE_TIER2_CRASH_RET": -0.01, "GATE_TIER2_SIZE_MULT": 0.5},
}
NEWJAR_ARMS = {"a7", "a7off"}


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(st):
    os.makedirs(W, exist_ok=True)
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def a6_fbase():
    f = W + "/a6_fbase.json"
    if not os.path.exists(f):
        raise SystemExit("A6 chua hieu chuan SIM_F_BASE (thieu %s)" % f)
    return float(json.load(open(f))["f_base"])


def ov_dev(arm, seed):
    ov = dict(T.B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=T.FLAGS["ranges"])
    if arm in ARMS:
        ov.update(ARMS[arm])
    if arm == "a6":
        ov["SIM_F_BASE"] = a6_fbase()
    return ov


def ov_ho(arm, seed, fl):
    q = T.Q()
    ov = dict(q.CFGS["k24"], SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=fl["ranges"])
    if arm in ARMS:
        ov.update(ARMS[arm])
    if arm == "a6":
        ov["SIM_F_BASE"] = a6_fbase()
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


def push_ho(arm, seed, fl):
    st = load_state()
    tag = "nup-ho-%s-s%d" % (arm, int(seed))
    if st.get(tag, {}).get("state") in ("PUSHED", "DONE"):
        log.info("SKIP %s state=%s", tag, st[tag]["state"])
        return tag
    q = T.Q()
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
            log.warning("status %s %s", tag, str(ex)[:120])
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
    if changed:
        save_state(st)
    return st


def cmd_push(scope, arm, seeds):
    if scope == "dev":
        for s in seeds:
            push_dev(arm, s)
    else:
        fl = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))
        assert fl["v1"]["ok"] and fl["n_days"] > 0
        for s in seeds:
            push_ho(arm, s, fl)


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
