"""CONC-CAP-HIGHN driver — cho slot Kaggle roi day dan 4 chan, roi wait + fetch.

Slot account dang bi job khac chiem (ofi-v3-build-s0..s4). Driver nay poll `free_slots()`
moi 4 phut, day toi da so slot con trong, va chi ket thuc khi CA 4 chan da COMPLETE+fetch.

  python3 research/analysis/conccap_driver.py > /home/ubuntu/conc_cap_driver.log 2>&1 &
"""
import json
import sys
import time

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
from tools import kaggle_sim as ks
import conccap_run as R

ORDER = ["par1", "t100", "g92", "g-cp"]
REF = {n: ks.kernel_ref(R.JOBS[n]["tag"]) for n in ORDER}
DONE = {}


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


def status_of(ref):
    try:
        return ks._status(ref)
    except Exception as e:
        return "UNKNOWN(%s)" % e


pending = list(ORDER)
while pending:
    slots = ks.free_slots()
    log("free_slots=%d pending=%s" % (slots, pending))
    # chan nao da duoc day (kernel ton tai + dang chay/hoan tat) thi bo khoi pending
    for n in list(pending):
        st = status_of(REF[n])
        if st in ("RUNNING", "QUEUED"):
            log("  %s da chay tren Kaggle (%s) -> bo khoi pending" % (n, st))
            pending.remove(n)
    if slots <= 0:
        time.sleep(240)
        continue
    for n in list(pending)[:slots]:
        j = R.JOBS[n]
        try:
            ref = ks.submit(j["tag"], j["profile"], j["overrides"], bundle_ds=R.BUNDLE,
                            jar_ds=R.JAR_DS, sim_end_date=R.END, code_sha=R.SHA)
            log("SUBMIT %-6s -> %s overrides=%s" % (n, ref, json.dumps(j["overrides"])))
            pending.remove(n)
        except Exception as e:
            log("SUBMIT FAIL %s: %s" % (n, e))
    time.sleep(60)

log("tat ca da day; cho COMPLETE")
st = ks.wait([REF[n] for n in ORDER])
log("STATUS %s" % json.dumps(st))
for n in ORDER:
    try:
        out = ks.fetch(R.JOBS[n]["tag"])
        log("FETCH %-6s %s" % (n, json.dumps(out["result"])))
        log("      printDone=%s" % out["print_done"])
    except Exception as e:
        log("FETCH FAIL %s: %s" % (n, e))
log("DRIVER DONE")
