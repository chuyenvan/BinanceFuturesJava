#!/usr/bin/env python3
"""BCAST driver nen (PREREG_BACKCAST_RESERVOIR 596c1ef8): chay tuan tu, <= 1 kernel BCAST, toan tai khoan < 2:
x20-a -> x20-b -> P3-DET exporter -> ch20-a -> ch20-b -> P3-DET chain -> arts -> bcast-tech (sim ky thuat, niem phong) -> check.
Bat ky buoc FAIL => DUNG (ghi state). Resume tu state.json. Usage: setsid nohup python3 bcast_drv.py > drv.out 2>&1 &"""
import json, logging, os, subprocess, sys, time
A = "/home/ubuntu/src/BinanceFuturesJava/research/analysis"
sys.path.insert(0, A)
W = "/home/ubuntu/claude_master/1012/bcast"
os.chdir(W)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("bcast_drv")
import bcast_exp_kernel as E  # noqa: E402
ST = W + "/drv_state.json"
SMALL = r"(MANIFEST\.json|result\.json|ticker_raw_md5\.json|universe_excl\.json|universe_by_month\.json|\.log)$"
PY = [sys.executable]


def st():
    return json.load(open(ST)) if os.path.exists(ST) else {}


def setst(k, v):
    s = st(); s[k] = v
    json.dump(s, open(ST + ".tmp", "w"), indent=1); os.replace(ST + ".tmp", ST)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "outdated API" not in l)
    log.info("CMD %s rc=%s\n%s", " ".join(cmd[1:3] if len(cmd) > 2 else cmd), r.returncode, out[-3000:])
    return r.returncode


def kstatus(tag):
    for i in range(5):
        try:
            r = E.api().kernels_status("%s/%s" % (E.USER, tag))
            return str(r.get("status") if isinstance(r, dict) else getattr(r, "status", r)).split(".")[-1].upper()
        except Exception as e:  # noqa: BLE001
            log.warning("status %s loi %s", tag, str(e)[:120]); time.sleep(30)
    return "ERR"


def wait(tag):
    while True:
        s = kstatus(tag)
        if s in ("COMPLETE", "ERROR", "CANCEL_ACKNOWLEDGED", "CANCELLED"):
            log.info("KERNEL %s -> %s", tag, s)
            return s
        time.sleep(120)


def push_retry(cmd):
    while True:
        rc = run(cmd)
        if rc == 0:
            return
        if rc == 3:
            log.info("cho slot Kaggle"); time.sleep(300); continue
        raise SystemExit("PUSH_FAIL %s" % cmd)


def step(name, push_cmd, tag, fetch_pat):
    s = st()
    if s.get(name) == "done":
        return
    if s.get(name) != "pushed":
        push_retry(push_cmd); setst(name, "pushed"); time.sleep(90)
    k = wait(tag)
    if k != "COMPLETE":
        setst(name, "kernel_" + k); raise SystemExit("KERNEL_FAIL %s %s" % (tag, k))
    if fetch_pat is not None and run(PY + [A + "/bcast_exp_kernel.py", "fetch", tag, fetch_pat]) != 0:
        raise SystemExit("FETCH_FAIL " + tag)
    setst(name, "done")


def det(a, b, key):
    run(PY + [A + "/bcast_det.py", "cmp", a, b])
    r = json.load(open(W + "/det_%s_%s.json" % (a, b)))
    setst(key, r["pass_"])
    if not r["pass_"]:
        raise SystemExit("P3DET_FAIL %s" % key)


def main():
    X = A + "/bcast_exp_kernel.py"
    CH = A + "/bcast_chainops.py"
    step("x_a", PY + [X, "submit", W + "/cfg_bcast-x20-a.json"], "bcast-x20-a", SMALL)
    run(PY + [A + "/bcast_det.py", "x", "bcast-x20-a"])
    step("x_b", PY + [X, "submit", W + "/cfg_bcast-x20-b.json"], "bcast-x20-b", SMALL)
    run(PY + [A + "/bcast_det.py", "x", "bcast-x20-b"])
    det("bcast-x20-a", "bcast-x20-b", "det_x")
    step("ch_a", PY + [CH, "push", "bcast-ch20-a", "bcast-x20-a"], "bcast-ch20-a", r".")
    run(PY + [A + "/bcast_det.py", "ch", "bcast-ch20-a"])
    if not json.load(open(W + "/kaggle/out/bcast-ch20-a/result.json")).get("ok"):
        setst("ch_a_ok", False); raise SystemExit("CHAIN_A_NOT_OK")
    step("ch_b", PY + [CH, "push", "bcast-ch20-b", "bcast-x20-b"], "bcast-ch20-b", SMALL)
    det("bcast-ch20-a", "bcast-ch20-b", "det_ch")
    if run(PY + [A + "/bcast_det.py", "arts", "bcast-x20-a", "bcast-ch20-a"]) != 0:
        raise SystemExit("ARTS_FAIL")
    step("tech", PY + [A + "/bcast_sim.py", "push", W + "/arts.json"], "bcast-tech", None)
    if st().get("tech_fetched") != "done":
        if run(PY + [A + "/bcast_sim.py", "fetch"]) != 0:
            raise SystemExit("TECH_FETCH_FAIL")
        setst("tech_fetched", "done")
    run(PY + [A + "/bcast_sim.py", "check"])
    setst("all", "done")
    log.info("DRV_DONE")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        log.error("DRV_STOP %s", e)
        setst("stop", str(e))
