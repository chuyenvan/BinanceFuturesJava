import sys, logging, numpy as np, pandas as pd
from grr_lib import load, ms, f
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("mm")
def frame(n):
    t, r, _ = load(n + ".bin"); return pd.DataFrame({"t": t // 60000, "r": np.round(r, 9)})
A, B, C = frame("bc3"), frame("b242_k16"), frame("bc3b")
lo, hi = max(A.t.min(), B.t.min()), min(A.t.max(), B.t.max())
ga = A[(A.t >= lo) & (A.t <= hi)].groupby("t").r.apply(lambda s: tuple(sorted(s)))
gb = B[(B.t >= lo) & (B.t <= hi)].groupby("t").r.apply(lambda s: tuple(sorted(s)))
J = pd.concat([ga.rename("a"), gb.rename("b")], axis=1)
J["same"] = [x == y for x, y in zip(J.a, J.b)]
J["na"] = J.a.apply(lambda x: len(x) if isinstance(x, tuple) else 0); J["nb"] = J.b.apply(lambda x: len(x) if isinstance(x, tuple) else 0)
log.info("phut chung: %d ; chi Oracle %d ; chi 242 %d ; khop hoan toan %d (%.1f%%)", ((J.na > 0) & (J.nb > 0)).sum(), ((J.na > 0) & (J.nb == 0)).sum(), ((J.na == 0) & (J.nb > 0)).sum(), J.same.sum(), 100 * J.same.mean())
J["day"] = pd.to_datetime(J.index * 60000 + 7 * 3600000, unit="ms").strftime("%m-%d")
both = J[(J.na > 0) & (J.nb > 0)]
for d, g in both.groupby("day"):
    # lech theo ty le: median r_a/r_b khi cung so record
    same_n = g[g.na == g.nb]
    rat = [np.median(np.array(x) / np.array(y)) for x, y in zip(same_n.a, same_n.b)]
    log.info("%s chung %4d khop %4d (%.1f%%) | cung n %4d, ty le med %.4f p5 %.4f p95 %.4f | n khac nhau %d", d, len(g), g.same.sum(), 100 * g.same.mean(), len(same_n), np.median(rat), np.quantile(rat, .05), np.quantile(rat, .95), (g.na != g.nb).sum())
# phut lech nhieu nhat
bad = both[~both.same]
big = [(i, np.max(np.abs(np.log(np.array(x) / np.array(y))))) for i, x, y in zip(bad.index, bad.a, bad.b) if len(x) == len(y)]
big.sort(key=lambda z: -z[1])
log.info("top lech log-ratio: %s", "; ".join("%s %.3f" % (f(i * 60000), v) for i, v in big[:15]))
