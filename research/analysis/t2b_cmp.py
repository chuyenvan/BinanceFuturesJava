"""T2b — bang rate + CI block-bootstrap 72h x1.21 cho hai cap so sanh da dang ky."""
import sys, logging
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
from t2b_legs import load, rates, boot
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("t2b_cmp")

KEYS = [("TSloss", "TSloss%"), ("win", "win%"), ("mSM", "mean(profit|SM)"),
        ("mSL", "mean(profit|SL)"), ("mP", "mean(profit)"), ("mMargin", "mean(margin)")]

def cmp(ta, tb):
    a, b = load(ta), load(tb)
    ra, rb = rates(a), rates(b)
    LOG.info("")
    LOG.info("### %s  -  %s", ta, tb)
    LOG.info("| rate | %s | %s | hieu | CI 95%% (72h x1.21) | ket qua |", ta, tb)
    LOG.info("|---|---|---|---|---|---|")
    out = 0
    for k, lab in KEYS:
        d = ra[k] - rb[k]
        lo, hi = boot(a, b, k)
        ok = "**KHAC**" if (lo > 0 or hi < 0) else "trong CI"
        if lo > 0 or hi < 0: out += 1
        LOG.info("| `%s` | %.3f | %.3f | %+.3f | [%+.3f, %+.3f] | %s |", lab, ra[k], rb[k], d, lo, hi, ok)
    LOG.info("=> %d/6 rate ngoai CI", out)
    return out

if __name__ == "__main__":
    for i in range(1, len(sys.argv), 2):
        cmp(sys.argv[i], sys.argv[i+1])
