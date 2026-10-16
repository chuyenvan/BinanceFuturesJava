import sys, logging, numpy as np
from grr_lib import load, q_of, ms, f
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("grr3")
B = {n: load(n + ".bin")[:2] for n in ["b242", "bc3b", "bc3", "b242_k16"]}
for n, (t, r) in B.items():
    log.info("%-8s n=%6d %s..%s q=%.5f", n, len(r), f(t.min()), f(t.max()), q_of(r))
t, r = B["b242"]
for a, b in [("10-08 22:00", "10-09 00:00"), ("10-08 22:00", "10-09 02:00")]:
    keep = ~((t >= ms(a)) & (t < ms(b)))
    log.info("b242 q bo [%s,%s) = %.5f (bo %d rec)", a, b, q_of(r[keep]), (~keep).sum())
for d in range(8, 17):
    s = ms("10-%02d 00:00" % d); w = (t >= s) & (t < s + 86400000)
    if w.sum(): log.info("  10-%02d n=%6d max %.5f p99.99 %.5f n>=q %d", d, w.sum(), r[w].max(), np.quantile(r[w], .9999), (r[w] >= q_of(r)).sum())
nat = t >= ms("10-16 14:57")
log.info("242-native >=10-16 14:57: n=%d max %.5f p99.9 %.5f", nat.sum(), r[nat].max() if nat.sum() else -1, np.quantile(r[nat], .999) if nat.sum() else -1)
# so khop c3b vs b242 tren cung ts (phan copy)
t2, r2 = B["bc3b"]
c = (t <= t2.max())
log.info("b242 phan <= c3b.max: %d rec; c3b %d rec; trung r? %s", c.sum(), len(r2), np.allclose(np.sort(r[c])[-200:], np.sort(r2[t2 <= t[c].max()])[-200:]))
# K16 c3 (Oracle) vs 242_k16 (242 native) cung ky: top r o 10-08 22-24h
for n in ["bc3", "b242_k16"]:
    tt, rr = B[n]; w = (tt >= ms("10-08 22:00")) & (tt < ms("10-09 00:00"))
    log.info("%-8s 10-08 22-24h: n=%d max %.5f | toan bo max %.5f q %.5f", n, w.sum(), rr[w].max() if w.sum() else -1, rr.max(), q_of(rr))
# cung cua so chung [max(first), min(last)] cho c3 vs 242_k16: q tung ben
for (a, b) in [("bc3", "b242_k16")]:
    ta, ra = B[a]; tb, rb = B[b]; lo = max(ta.min(), tb.min()); hi = min(ta.max(), tb.max())
    wa = (ta >= lo) & (ta <= hi); wb = (tb >= lo) & (tb <= hi)
    log.info("cua so chung %s..%s: %s n=%d q=%.5f max %.5f | %s n=%d q=%.5f max %.5f", f(lo), f(hi), a, wa.sum(), q_of(ra[wa]), ra[wa].max(), b, wb.sum(), q_of(rb[wb]), rb[wb].max())
    for d in range(8, 17):
        s = ms("10-%02d 00:00" % d)
        xa = ra[(ta >= s) & (ta < s + 86400000)]; xb = rb[(tb >= s) & (tb < s + 86400000)]
        if len(xa) and len(xb): log.info("  10-%02d max c3 %.5f vs 242 %.5f | p99.9 %.5f vs %.5f | n %d vs %d", d, xa.max(), xb.max(), np.quantile(xa, .999), np.quantile(xb, .999), len(xa), len(xb))
