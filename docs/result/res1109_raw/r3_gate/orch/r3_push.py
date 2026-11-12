#!/usr/bin/env python3
"""R3 Pha 1: day DUNG 1 kernel sim (arm, seed). Module orchestrator chon qua env R3_ORCH_MOD (mac dinh r3_orch = jar cu;
r3_orch_m = jar AS-FILE). Khoa push.lock (fcntl) de seq va lenh tay khong day cung luc.
Dieu kien: kernel R3 cua ta dang chay = 0 (1 slot) VA tong account dang chay <= 1 (sau push <= 2).
Usage: r3_push.py <arm> <seed>"""
import fcntl, importlib, os, sys, time
sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r3_gate/orch")
O = importlib.import_module(os.environ.get("R3_ORCH_MOD", "r3_orch"))
arm, seed = sys.argv[1], int(sys.argv[2])
assert arm in O.ARMS and arm in ("g0", "g3", "g0m", "g3m", "g0n"), arm
lk = open("/home/ubuntu/claude_master/res1109/r3_gate/orch/push.lock", "w")
fcntl.flock(lk, fcntl.LOCK_EX)
st = O.load_state()
ours = [t for t, v in st.items() if not t.startswith("_") and v.get("kind") == "sim" and v.get("state") == "PUSHED"]
for t in list(ours):
    s = O.KS._status(O.KS.kernel_ref(t))
    st[t]["kstatus"] = s
    if s in O.KS.TERMINAL:
        ours.remove(t)
O.save_state(st)
running = O.account_running()
O.log.info("R3 push check (%s): ours_running=%s account_running=%d", O.__name__, ours, running)
if ours or running > 1:
    O.log.error("KHONG push: slot khong du (ours=%s, account=%d)", ours, running); sys.exit(2)
O.jards()
e = dict(tag=O.tag_of(arm, seed), arm=arm, seed=seed, phase="r3")
if e["tag"] in st:
    O.log.error("tag %s da co trong state => khong push lai", e["tag"]); sys.exit(3)
O.push_sim(st, e)
O.log.info("DONE push %s at %s", e["tag"], time.strftime("%FT%TZ", time.gmtime()))
