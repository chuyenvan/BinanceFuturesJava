"""NBETS buoc 4: sd/MDE80 theo MOI do dai khoi (cho Cau 4 va Cau 5)."""
import logging, sys, json
import numpy as np
sys.path.insert(0, "/home/ubuntu/nbets")
import nb_lib as N

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/nbets/step4.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("s4")
SINGLE = ["C2b", "C2_g015", "N4_a8s175", "A6_ts96", "D1_full_ts", "A6_ts336",
          "R2_ts120", "R0_parity", "R2_ts240", "S3_ts168", "S4_ts720"]
PAIRS = [("Q1", "C2b", "C2_g015"), ("Q2", "C2b", "N4_a8s175"),
         ("T1", "A6_ts96", "A6_ts336"), ("T2", "R2_ts120", "R2_ts240"),
         ("T3", "S3_ts168", "S4_ts720")]
LR = {t: N.logret(t)[0] for t in SINGLE}
n = len(LR["C2b"])
out = {}

L.info("=== HIEU CAGR (dCAGR, pp) theo do dai khoi — 2000 rep, seed 20260903 ===")
L.info("%-4s %-11s %-11s %4s %6s %9s %9s %8s %8s", "ma", "A", "B", "L", "n_kh",
       "d(pp)", "sd(pp)", "MDE80", "CI95")
for pid, a, b in PAIRS:
    for bl in N.GRID:
        st, nb = N.boot_starts(n, bl, N.NREP, N.SEED)
        ca = np.exp(N.boot_sum(LR[a], bl, st, nb) * 365.0 / n) - 1.0
        cb = np.exp(N.boot_sum(LR[b], bl, st, nb) * 365.0 / n) - 1.0
        d = ca - cb
        dpt = np.exp(LR[a].sum() * 365.0 / n) - np.exp(LR[b].sum() * 365.0 / n)
        lo, hi = np.percentile(d, [2.5, 97.5])
        sd = d.std(ddof=1)
        dgv = 365.0 * (LR[a] - LR[b]).mean()
        stg = N.boot_sum(LR[a] - LR[b], bl, st, nb) * 365.0 / n
        out["%s|%d" % (pid, bl)] = dict(d=float(dpt), sd=float(sd), lo=float(lo),
                                        hi=float(hi), mde=float(N.Z80 * sd),
                                        dg=float(dgv), sd_dg=float(stg.std(ddof=1)),
                                        mde_dg=float(N.Z80 * stg.std(ddof=1)))
        L.info("%-4s %-11s %-11s %4d %6d %+8.3f %9.4f %8.3f [%+.2f,%+.2f]", pid, a, b,
               bl, nb, dpt * 100, sd * 100, N.Z80 * sd * 100, lo * 100, hi * 100)


L.info("\n=== dg = 365*mean(log-hieu) (%%/nam) theo do dai khoi ===")
L.info("%-4s %4s %6s %9s %9s %8s", "ma", "L", "n_kh", "dg", "sd_dg", "MDE80_dg")
for pid, a, b in PAIRS:
    for bl in N.GRID:
        r = out["%s|%d" % (pid, bl)]
        L.info("%-4s %4d %6d %+9.3f %9.4f %8.3f", pid, bl, int(np.ceil(n / bl)),
               r["dg"] * 100, r["sd_dg"] * 100, r["mde_dg"] * 100)

L.info("\n=== sd(CAGR) chuoi DON theo do dai khoi (pp) ===")
hdr = "%-12s" + " %7d" * len(N.GRID)
L.info(("%-12s" + " %7s" * len(N.GRID)) % tuple(["run"] + N.GRID))
sng = {}
for t in SINGLE:
    row = []
    for bl in N.GRID:
        st, nb = N.boot_starts(n, bl, N.NREP, N.SEED)
        c = np.exp(N.boot_sum(LR[t], bl, st, nb) * 365.0 / n) - 1.0
        sd = c.std(ddof=1)
        sng["%s|%d" % (t, bl)] = float(sd)
        row.append(sd * 100)
    L.info(("%-12s" + " %7.3f" * len(N.GRID)) % tuple([t] + row))

json.dump(dict(pairs=out, single=sng), open("/home/ubuntu/nbets/step4.json", "w"),
          indent=1)
L.info("\nDONE step4")
