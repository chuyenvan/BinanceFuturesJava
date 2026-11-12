"""Patch a3_build.py: G-FULL(b) mau so = key pool cu CO MAT trong bin net015 (ADDENDUM2)."""
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("patch2")
fn = "a3_build.py"
s = open(fn).read()
old1 = '        n_ref = int(((P.ts >= V.ts.min()) & (P.ts <= V.ts.max())).sum())\n'
new1 = ('        Pr = P[(P.ts >= V.ts.min()) & (P.ts <= V.ts.max())][["ts", "sym"]]\n'
        '        n_ref = int(len(Pr))\n'
        '        n_absent = int((Pr.merge(D[["ts", "sym"]], on=["ts", "sym"], how="left", indicator=True)._merge\n'
        '                        == "left_only").sum())\n')
old2 = '                 pool_ref=n_ref, pool_maxd=maxd,'
new2 = '                 pool_ref=n_ref, pool_absent_in_bin=n_absent, pool_maxd=maxd,'
old3 = ('    ok_full = all(f["coverage_score"] >= 0.99 and f["pool_matched"] >= 0.999 * f["pool_ref"] and f["pool_maxd"] <= 1e-6\n'
        '                  for f in rep["folds"])\n')
new3 = ('    rep["G_FULL_ADD1_raw"] = all(f["coverage_score"] >= 0.99 and f["pool_matched"] >= 0.999 * f["pool_ref"]\n'
        '                                 and f["pool_maxd"] <= 1e-6 for f in rep["folds"])\n'
        '    ok_full = all(f["coverage_score"] >= 0.99\n'
        '                  and f["pool_matched"] >= 0.999 * (f["pool_ref"] - f["pool_absent_in_bin"])\n'
        '                  and f["pool_maxd"] <= 1e-6 for f in rep["folds"])\n')
for o, n in ((old1, new1), (old2, new2), (old3, new3)):
    assert s.count(o) == 1, o
    s = s.replace(o, n)
open(fn, "w").write(s)
log.info("patched")
