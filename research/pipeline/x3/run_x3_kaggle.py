"""X3 — day 5 kernel Kaggle SONG SONG (dung 5 slot). Doc docs/KAGGLE_SIM.md truoc.

Chi chay duoc sau khi `sim-c2b-bundle` da co jar X3 + dataset WFO 48 thang. Ba dataset ticker
2024h2/2025h1/2025h2 da co san tren Kaggle (X2 muc 10); `tools/kaggle_sim.TICKER_DS` da them.

usage: python3 run_x3_kaggle.py submit|wait|fetch
"""
import logging
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks   # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout)
LOG = logging.getLogger("x3-kaggle")

SIM_END = "20251231"
ARMS = [("x3-parity", "x3_parity"), ("x3-r2", "x3_r2"), ("x3-r4", "x3_r4"),
        ("x3-r6", "x3_r6"), ("x3-s50", "x3_s50")]


def submit(code_sha):
    free = ks.free_slots()
    LOG.info("free_slots=%d (can 5)", free)
    if free < len(ARMS):
        LOG.error("khong du slot: %d < %d — DUNG", free, len(ARMS))
        raise SystemExit(2)
    refs = [ks.submit(tag, prof, {}, code_sha=code_sha, sim_end_date=SIM_END)
            for tag, prof in ARMS]
    LOG.info("pushed=%s", refs)
    return refs


def main(argv):
    cmd = argv[0] if argv else "submit"
    if cmd == "submit":
        submit(argv[1] if len(argv) > 1 else "head")
    elif cmd == "wait":
        LOG.info("%s", ks.wait([ks.kernel_ref(t) for t, _ in ARMS]))
    elif cmd == "fetch":
        for tag, _ in ARMS:
            LOG.info("%s -> %s", tag, ks.fetch(tag)["result"])
    else:
        LOG.error("cmd khong biet: %s", cmd)
        raise SystemExit(2)


if __name__ == "__main__":
    main(sys.argv[1:])
