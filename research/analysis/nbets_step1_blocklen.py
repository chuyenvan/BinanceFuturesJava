"""NBETS buoc 1: tai lap kiem chung + Cau 1 (do dai phu thuoc bang PW va VR)."""
import logging, sys, json
import numpy as np
sys.path.insert(0, "/home/ubuntu/nbets")
import nb_lib as N

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/nbets/step1.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("s1")

SINGLE = ["C2b", "C2_g015", "N4_a8s175", "A6_ts96", "D1_full_ts", "A6_ts336",
          "R2_ts120", "R0_parity", "R2_ts240", "S3_ts168", "S4_ts720"]
PAIRS = [("Q1", "C2b", "C2_g015"), ("Q2", "C2b", "N4_a8s175"),
         ("T1", "A6_ts96", "A6_ts336"), ("T2", "R2_ts120", "R2_ts240"),
         ("T3", "S3_ts168", "S4_ts720")]

LR, EQ = {}, {}
for t in SINGLE:
    LR[t], EQ[t] = N.logret(t)
n = len(LR["C2b"])
assert all(len(LR[t]) == n for t in SINGLE)
L.info("n ngay = %d (%.4f nam)", n, n / 365.0)
for t in SINGLE:
    L.info("  %-12s eq_cuoi=%7d CAGR=%+7.3f%%", t, int(EQ[t].iloc[-1]),
           (np.exp(LR[t].sum() * 365.0 / n) - 1.0) * 100)

L.info("\n=== KIEM CHUNG 0: boot_sum == x[idxmat].sum(axis=1) ===")
for bl in [3, 21, 42]:
    ix = N.idxmat(n, bl, 50, N.SEED)
    st, nb = N.boot_starts(n, bl, 50, N.SEED)
    a = LR["C2b"][ix].sum(axis=1)
    b = N.boot_sum(LR["C2b"], bl, st, nb)
    L.info("  L=%2d maxdiff=%.3e", bl, np.abs(a - b).max())
    assert np.abs(a - b).max() < 1e-9


def cagr_ci(a, b, bl, nrep=N.NREP, seed=N.SEED):
    st, nb = N.boot_starts(n, bl, nrep, seed)
    ca = np.exp(N.boot_sum(LR[a], bl, st, nb) * 365.0 / n) - 1.0
    cb = np.exp(N.boot_sum(LR[b], bl, st, nb) * 365.0 / n) - 1.0
    d = ca - cb
    dpt = np.exp(LR[a].sum() * 365.0 / n) - np.exp(LR[b].sum() * 365.0 / n)
    lo, hi = np.percentile(d, [2.5, 97.5])
    return dpt, lo, hi, d.std(ddof=1)


L.info("\n=== KIEM CHUNG 1 (PREREG_NBETS section 8.3a): C2b vs C2_g015, khoi 21 ===")
dpt, lo, hi, sd = cagr_ci("C2b", "C2_g015", 21)
L.info("  d=%+.3fpp CI95=[%+.3f, %+.3f] sd=%.4fpp   (cho: +7.33 / [-1.72,+15.61] / 4.45)",
       dpt * 100, lo * 100, hi * 100, sd * 100)
L.info("\n=== KIEM CHUNG 2 (section 8.3b): A6_ts96 vs A6_ts336 MDE80 khoi 21 ===")
dpt2, lo2, hi2, sd2 = cagr_ci("A6_ts96", "A6_ts336", 21)
L.info("  d=%+.3fpp CI95=[%+.3f, %+.3f] sd=%.4fpp MDE80=%.3fpp  (cho MDE80=6.437)",
       dpt2 * 100, lo2 * 100, hi2 * 100, sd2 * 100, N.Z80 * sd2 * 100)

L.info("\n=== CAU 1: do dai phu thuoc — chuoi DON (log(1+r)) ===")
L.info("%-12s %6s %6s %5s %6s %8s %8s", "run", "L_PW", "m", "M", "L_VR", "plateau", "ESS(L_VR)")
q1 = {}
for t in SINGLE:
    bpw, m, M = N.pw_blocklen(LR[t])
    vr, _, _ = N.var_ratio(LR[t])
    lvr, ok = N.vr_plateau(vr)
    q1[t] = dict(L_PW=bpw, L_VR=lvr, plateau=bool(ok),
                 vr={str(k): round(v, 4) for k, v in vr.items()})
    L.info("%-12s %6d %6d %5d %6d %8s %8.1f", t, bpw, m, M, lvr, ok,
           N.ess_from_vr(n, vr, lvr))
L.info("  VR(L) cua C2b: %s", {k: round(v, 3) for k, v in
                               N.var_ratio(LR["C2b"])[0].items()})


L.info("\n=== CAU 1: do dai phu thuoc — chuoi HIEU d_t = log(1+rA) - log(1+rB) ===")
L.info("%-4s %-12s %-12s %6s %6s %8s %8s %8s", "ma", "A", "B", "L_PW", "L_VR",
       "plateau", "L_est", "phi_lag1")
q1p = {}
for pid, a, b in PAIRS:
    d = LR[a] - LR[b]
    bpw, m, M = N.pw_blocklen(d)
    vr, _, _ = N.var_ratio(d)
    lvr, ok = N.vr_plateau(vr)
    lest = N.snap_up(max(bpw, lvr))
    phi = np.corrcoef(d[:-1], d[1:])[0, 1]
    q1p[pid] = dict(A=a, B=b, L_PW=bpw, L_VR=lvr, plateau=bool(ok), L_est=lest,
                    phi=float(phi), sd_d=float(d.std(ddof=1)),
                    vr={str(k): round(v, 4) for k, v in vr.items()})
    L.info("%-4s %-12s %-12s %6d %6d %8s %8d %8.4f", pid, a, b, bpw, lvr, ok, lest, phi)
    L.info("     VR: %s", {k: round(v, 3) for k, v in vr.items()})

L.info("\n=== phi lag-1 cua chuoi DON (dung hieu chuan generator G4) ===")
for t in SINGLE:
    x = LR[t]
    q1[t]["phi"] = float(np.corrcoef(x[:-1], x[1:])[0, 1])
    q1[t]["sd"] = float(x.std(ddof=1))
    L.info("  %-12s phi=%+.4f sd_ngay=%.5f", t, q1[t]["phi"], q1[t]["sd"])

json.dump(dict(n=n, single=q1, pairs=q1p), open("/home/ubuntu/nbets/step1.json", "w"),
          indent=1)
L.info("\nDONE step1")
