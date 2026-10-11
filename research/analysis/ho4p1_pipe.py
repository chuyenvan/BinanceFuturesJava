#!/usr/bin/env python3
"""HO4-P1 scheduler nen (ADDENDUM-6 §6.3/§6.5): day kernel theo thu tu uu tien khi co slot (<= 2 kernel TOAN tai khoan),
tu chay cong P3-DET (ho4p1_detcmp) khi du cap. Cong exporter FAIL => khong day q*/chain-y26. Cong OI/chain FAIL => khong day
chain-y26. KHONG doc so 2026 (chi trang thai/md5). State resume pipe_state.json. Dung khi het viec hoac cong FAIL.
Usage: cd ~/claude_master/1011/ho4p1 && setsid nohup python3 <repo>/research/analysis/ho4p1_pipe.py > pipe.out 2>&1 < /dev/null &"""
import json, logging, os, subprocess, sys, time
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis"
W = "/home/ubuntu/claude_master/1011/ho4p1"
sys.path.insert(0, A)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
_fh = logging.FileHandler(W + "/pipe.log")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(_fh)
log = logging.getLogger("pipe")
ST = W + "/pipe_state.json"
PY = sys.executable
CH_DET = lambda e, o: ["push", "ho4p1-chdet-%s" % e, "det", json.dumps({"det_src": "ho4p1-det-%s" % e, "oi_src": "ho4p1-oi-%s" % o})]
Y26 = {"q_src": {"q1": "ho4p1-x26-q1", "q2": "ho4p1-x26-q2", "q3": "ho4p1-x26-q3"}, "oi_src": "ho4p1-oi-a"}
Y26R = {"q_src": {"q1": "ho4p1-x26-q1r", "q2": "ho4p1-x26-q2", "q3": "ho4p1-x26-q3"}, "oi_src": "ho4p1-oi-a"}  # S5
# (slug, lenh push, phu thuoc COMPLETE, cong can PASS)
STEPS = [
    ("ho4p1-det-a", None, [], []),
    ("ho4p1-det-b", None, [], []),
    ("ho4p1-x26-q1", ["ops", "push", W + "/cfg_ho4p1-x26-q1.json"], [], ["exp"]),
    ("ho4p1-oi-a", ["ops", "oipush", "ho4p1-oi-a"], [], []),
    ("ho4p1-chdet-a", ["chainops"] + CH_DET("a", "a"), ["ho4p1-det-a", "ho4p1-oi-a"], []),
    ("ho4p1-x26-q2", ["ops", "push", W + "/cfg_ho4p1-x26-q2.json"], [], ["exp"]),
    ("ho4p1-oi-b", ["ops", "oipush", "ho4p1-oi-b"], [], []),
    ("ho4p1-x26-q3", ["ops", "push", W + "/cfg_ho4p1-x26-q3.json"], [], ["exp"]),
    ("ho4p1-chdet-b", ["chainops"] + CH_DET("b", "b"), ["ho4p1-det-b", "ho4p1-oi-b"], []),
    ("ho4p1-x26-q1r", ["ops", "push", W + "/cfg_ho4p1-x26-q1r.json"], ["ho4p1-x26-q1"], ["exp"]),
    ("ho4p1-tk26", ["stage", "tk26"], ["ho4p1-x26-q1", "ho4p1-x26-q2", "ho4p1-x26-q3"], ["exp"]),
    ("ho4p1-chain-y26", ["chainops", "push", "ho4p1-chain-y26", "y26", json.dumps(Y26)],
     ["ho4p1-x26-q1", "ho4p1-x26-q2", "ho4p1-x26-q3", "ho4p1-oi-a"], ["exp", "oi", "chain"]),
    ("ho4p1-chain-y26r", ["chainops", "push", "ho4p1-chain-y26r", "y26", json.dumps(Y26R)],
     ["ho4p1-x26-q1r", "ho4p1-x26-q2", "ho4p1-x26-q3", "ho4p1-oi-a"], ["exp", "oi", "chain"]),
    ("ho4p1-tkdev", ["simdev", "tkdev"], ["ho4p1-det-a"], []),
    ("ho4p1-devcmp", ["chainops", "push", "ho4p1-devcmp", "devcmp", json.dumps({"det_src": "ho4p1-det-a", "chain_src": "ho4p1-chdet-a"})],
     ["ho4p1-det-a", "ho4p1-chdet-a"], []),
]
GATES = {"exp": ("ho4p1-det-a", "ho4p1-det-b", "exp"), "oi": ("ho4p1-oi-a", "ho4p1-oi-b", "oi"),
         "chain": ("ho4p1-chdet-a", "ho4p1-chdet-b", "chain"),
         "s5q1": ("ho4p1-x26-q1", "ho4p1-x26-q1r", "exp"), "s5chain": ("ho4p1-chain-y26", "ho4p1-chain-y26r", "chain")}
SCRIPT = {"ops": A + "/ho4p1_ops.py", "chainops": A + "/ho4p1_chainops.py", "stage": A + "/ho4p1_stage.py", "simdev": A + "/ho4p1_simdev.py"}
TERM = {"COMPLETE", "ERROR", "CANCELACKNOWLEDGED", "CANCELLED"}


def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi(); a.authenticate()
    return a


def kstatus(a, slug):
    r = a.kernels_status("chuyendinh/" + slug)
    return str(r.get("status") if isinstance(r, dict) else getattr(r, "status", r)).split(".")[-1].upper()


def active(a):
    out = []
    for k in a.kernels_list(mine=True, page_size=30, sort_by="dateRun"):
        try:
            s = kstatus(a, k.ref.split("/")[1])
        except Exception:  # noqa: BLE001
            continue
        if s in ("RUNNING", "QUEUED"):
            out.append(k.ref)
    return out


def load():
    st = json.load(open(ST)) if os.path.exists(ST) else {}
    st.setdefault("gates", {g: None for g in GATES})
    for g in GATES:
        st["gates"].setdefault(g, None)
    for slug, cmd, _, _ in STEPS:
        st.setdefault(slug, {"state": "pushed" if cmd is None else "todo", "pushes": 0 if cmd else 1})
    return st


def save(st):
    json.dump(st, open(ST + ".tmp", "w"), indent=1)
    os.replace(ST + ".tmp", ST)


def run_gate(g):
    a, b, kind = GATES[g]
    out = W + "/det_%s.json" % g
    r = subprocess.run([PY, A + "/ho4p1_detcmp.py", a, b, kind, out], capture_output=True, text=True, timeout=1800)
    log.info("GATE %s rc=%s tail=%s", g, r.returncode, (r.stdout + r.stderr)[-600:])
    try:
        return bool(json.load(open(out))["pass"])
    except Exception as e:  # noqa: BLE001
        log.error("GATE %s doc ket qua loi %s", g, e)
        return None


def push(cmd):
    r = subprocess.run([PY, SCRIPT[cmd[0]]] + cmd[1:], capture_output=True, text=True, timeout=900)
    log.info("PUSH %s rc=%s tail=%s", cmd[:3], r.returncode, (r.stdout + r.stderr)[-400:])
    if r.returncode == 3:
        return None                                  # het slot (kiem lai trong submit) -> khong tinh la lan day
    return r.returncode == 0 and "PUSHED" in (r.stdout + r.stderr)


def main():
    open(W + '/pipe.pid', 'w').write(str(os.getpid()))
    st = load(); save(st)
    spec = {s: (c, d, g) for s, c, d, g in STEPS}
    while True:
        a = api()
        for slug, (cmd, deps, gates) in spec.items():
            s = st[slug]
            if s["state"] != "pushed":
                continue
            if time.time() - s.get("pushed_epoch", 0) < 240:
                continue
            try:
                k = kstatus(a, slug)
            except Exception as e:  # noqa: BLE001
                log.info("status %s loi %s", slug, str(e)[:80]); continue
            if k in TERM:
                s["kstatus"] = k
                if k == "COMPLETE":
                    s["state"] = "done"
                elif s["pushes"] < 2 and cmd:
                    s["state"] = "todo"
                    log.warning("KERNEL %s %s -> thu lai 1 lan (loi ha tang, cfg y het)", slug, k)
                else:
                    s["state"] = "failed"
                log.info("KERNEL %s -> %s (%s)", slug, s["state"], k)
                save(st)
        for g, (x, y, _) in GATES.items():
            if st["gates"][g] is None and st[x]["state"] == "done" and st[y]["state"] == "done":
                st["gates"][g] = run_gate(g)
                log.info("CONG P3-DET %s = %s", g, st["gates"][g])
                save(st)
            if st[x]["state"] == "failed" or st[y]["state"] == "failed":
                if st["gates"][g] is None:
                    st["gates"][g] = False; save(st)
        todo = []
        for slug, (cmd, deps, gates) in spec.items():
            s = st[slug]
            if s["state"] != "todo":
                continue
            if any(st["gates"][g] is False for g in gates) or any(st[d]["state"] in ("failed", "blocked") for d in deps):
                s["state"] = "blocked"; save(st)
                log.error("BLOCKED %s (cong/phu thuoc FAIL)", slug)
                continue
            if all(st[d]["state"] == "done" for d in deps) and all(st["gates"][g] is True for g in gates):
                todo.append(slug)
        live = [x for x in spec if st[x]["state"] in ("todo", "pushed")]
        if not live:
            log.info("PIPE KET THUC %s", json.dumps({x: st[x]["state"] for x in spec}))
            break
        if todo:
            try:
                act = active(a)
            except Exception as e:  # noqa: BLE001
                log.warning("active loi %s", e); act = ["?", "?"]
            own = {"chuyendinh/" + x for x in spec if st[x]["state"] == "pushed"}
            if len(set(act) | own) < 2:
                slug = todo[0]
                ok = push(spec[slug][0])
                if ok is None:
                    time.sleep(120); continue
                st[slug]["pushes"] += 1
                if ok:
                    st[slug].update(state="pushed", pushed_epoch=time.time(), pushed_at=time.strftime("%H:%M:%S"))
                elif st[slug]["pushes"] >= 2:
                    st[slug]["state"] = "failed"
                save(st)
                time.sleep(60)
                continue
        time.sleep(120)


if __name__ == "__main__":
    main()
