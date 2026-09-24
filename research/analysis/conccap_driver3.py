"""CONC-CAP-HIGHN driver v3 — chiu duoc 429/404 cua Kaggle API.

Boi canh: API Kaggle bi throttle nang (nhieu job cung poll) va push luc het slot co the
tao kernel ma KHONG tao run (`kernels_status` tra 404 "No runs found for this kernel" mai).
Vong nay: kiem tra trang thai tung tag; 404/khong co run => PUSH LAI; 429 => nghi theo Retry-After.

  python3 research/analysis/conccap_driver3.py > /home/ubuntu/conc_cap_driver.log 2>&1 &
"""
import json
import sys
import time

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
from tools import kaggle_sim as ks
import conccap_run as R

ORDER = ["t100", "g92", "g-cp"]
REF = {n: ks.kernel_ref(R.JOBS[n]["tag"]) for n in ORDER}
FIN = ("COMPLETE", "ERROR", "CANCEL_ACKNOWLEDGED", "CANCELLED")


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


def st(ref):
    """-> status, 'NORUN' (404), 'RATELIMIT' (429) hoac 'ERR:...'"""
    for _ in range(4):
        try:
            s = ks._status(ref)
            return s
        except Exception as e:
            m = str(e)
            if m.startswith("(404)"):
                return "NORUN"
            if m.startswith("(429)"):
                time.sleep(30)
                continue
            return "ERR:" + m.splitlines()[0][:60]
    return "RATELIMIT"


state = {n: "TODO" for n in ORDER}
for n in ORDER:
    s = st(REF[n])
    if s in FIN:
        state[n] = s
    elif s in ("RUNNING", "QUEUED"):
        state[n] = s
    log("khoi tao %-5s -> %s" % (n, s))

rounds = 0
while any(state[n] not in FIN for n in ORDER):
    rounds += 1
    for n in ORDER:
        if state[n] in FIN:
            continue
        s = st(REF[n])
        if s in FIN:
            state[n] = s
            log("%-5s -> %s" % (n, s))
            continue
        if s in ("RUNNING", "QUEUED"):
            if state[n] != s:
                log("%-5s -> %s" % (n, s))
            state[n] = s
            continue
        # NORUN / ERR / RATELIMIT => day lai
        if rounds % 2 == 1:
            j = R.JOBS[n]
            try:
                ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=R.BUNDLE,
                                jar_ds=R.JAR_DS, sim_end_date=R.END, code_sha=R.SHA)
                log("PUSH LAI %-5s -> %s (truoc do: %s)" % (n, ref, s))
            except Exception as e:
                log("PUSH FAIL %-5s: %s" % (n, str(e).splitlines()[0][:120]))
    log("vong %d | state=%s" % (rounds, state))
    time.sleep(180)

log("tat ca terminal: %s" % state)
for n in ORDER:
    if state[n] != "COMPLETE":
        log("BO QUA fetch %s (state=%s)" % (n, state[n]))
        continue
    for a in range(5):
        try:
            out = ks.fetch(R.JOBS[n]["tag"])
            log("FETCH %-5s %s" % (n, json.dumps(out["result"])))
            log("      printDone=%s" % out["print_done"])
            break
        except Exception as e:
            log("FETCH FAIL %-5s lan %d: %s" % (n, a, str(e).splitlines()[0][:100]))
            time.sleep(60)
log("DRIVER3 DONE")
