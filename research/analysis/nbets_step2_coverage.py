"""NBETS buoc 2: CONG KIEM PHU (coverage) — PREREG_NBETS section 4."""
import logging, sys, json, time
import numpy as np
sys.path.insert(0, "/home/ubuntu/nbets")
import nb_lib as N

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/nbets/step2.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("s2")
T = 911
N_MC = 1000
N_BOOT = 1000
MU = 0.0002
S0 = 0.01
st1 = json.load(open("/home/ubuntu/nbets/step1.json"))


def gen_iid(rng, s):
    return rng.normal(0.0, s, T)


def gen_ar1(rng, s, phi):
    e = rng.normal(0.0, s * np.sqrt(1.0 - phi * phi), T)
    u = np.empty(T)
    u[0] = rng.normal(0.0, s)
    for t in range(1, T):
        u[t] = phi * u[t - 1] + e[t]
    return u


def gen_ma(rng, s, span):
    e = rng.normal(0.0, 1.0, T + span - 1)
    c = np.concatenate([[0.0], np.cumsum(e)])
    m = (c[span:] - c[:-span]) / span
    return s * np.sqrt(span) * m


GENS = []
GENS.append(("G1_iid", 0, lambda r: gen_iid(r, S0), 1.0))
GENS.append(("G2a_ar.3", 1, lambda r: gen_ar1(r, S0, 0.3), 1.86))
GENS.append(("G2b_ar.6", 2, lambda r: gen_ar1(r, S0, 0.6), 4.00))
GENS.append(("G2c_ar.9", 3, lambda r: gen_ar1(r, S0, 0.9), 19.0))
GENS.append(("G3a_ma7", 4, lambda r: gen_ma(r, S0, 7), 7.0))
GENS.append(("G3b_ma21", 5, lambda r: gen_ma(r, S0, 21), 21.0))
for gi, pid in enumerate(["Q1", "Q2", "T1", "T2", "T3"]):
    p = st1["pairs"][pid]
    ph, sd = p["phi"], p["sd_d"]
    GENS.append(("G4_%s(phi%+.2f)" % (pid, ph), 6 + gi,
                 (lambda ph=ph, sd=sd: (lambda r: gen_ar1(r, sd, ph)))(), (1 + ph) / (1 - ph)))
# BO SUNG (khong pre-reg): AR(1) am tuong minh — vi du lieu that co phu thuoc AM
GENS.append(("X_ar-.3", 20, lambda r: gen_ar1(r, S0, -0.3), 0.538))
GENS.append(("X_ar-.6", 21, lambda r: gen_ar1(r, S0, -0.6), 0.25))


def one_cell(genf, gid, blen):
    rng = np.random.default_rng(N.SEED + 1000 * gid + blen)
    nb = int(np.ceil(T / blen))
    p = T - (nb - 1) * blen
    tgt_dg = 365.0 * MU
    tgt_cg = np.exp(365.0 * MU) - 1.0
    cov_dg = cov_cg = 0
    w_dg = w_cg = 0.0
    for _ in range(N_MC):
        d = MU + genf(rng)
        bs = N._circ_blocksum(d, blen) if nb > 1 else None
        ps = N._circ_blocksum(d, p)
        starts = rng.integers(0, T, size=(N_BOOT, nb))
        tot = ps[starts[:, nb - 1]]
        if nb > 1:
            tot = tot + bs[starts[:, : nb - 1]].sum(axis=1)
        dg = 365.0 * tot / T
        lo, hi = np.percentile(dg, [2.5, 97.5])
        cov_dg += (lo <= tgt_dg <= hi)
        w_dg += hi - lo
        cg = np.exp(365.0 * tot / T) - 1.0
        lo2, hi2 = np.percentile(cg, [2.5, 97.5])
        cov_cg += (lo2 <= tgt_cg <= hi2)
        w_cg += hi2 - lo2
    return cov_dg / N_MC, w_dg / N_MC, cov_cg / N_MC, w_cg / N_MC


L.info("CONG KIEM PHU: N_MC=%d, N_BOOT=%d, T=%d, dai chap nhan [0.92,0.97], "
       "sai so MC=%.4f", N_MC, N_BOOT, T, np.sqrt(0.95 * 0.05 / N_MC))
L.info("Dai luong GATE = dg = 365*mean(d), dich = 365*mu = %+.4f (%.2f%%/nam)",
       365 * MU, 365 * MU * 100)
out = {}
for name, gid, genf, tau in GENS:
    t0 = time.time()
    L.info("\n--- %s  (thoi gian tich phan phu thuoc = %.2f ngay) ---", name, tau)
    L.info("%5s %6s %9s %10s %9s %10s", "L", "n_kh", "phu(dg)", "rongCI(dg)",
           "phu(CAGR)", "rongCI(CAGR)")
    rows = []
    for blen in N.GRID:
        c1, w1, c2, w2 = one_cell(genf, gid, blen)
        nb = int(np.ceil(T / blen))
        flag = "PASS" if 0.92 <= c1 <= 0.97 else ("DUOI-PHU" if c1 < 0.92 else "BAO-THU")
        L.info("%5d %6d %9.3f %10.4f %9.3f %10.4f  %s", blen, nb, c1, w1 * 100,
               c2, w2 * 100, flag)
        rows.append(dict(L=blen, nb=nb, cov_dg=c1, w_dg=w1, cov_cagr=c2, w_cagr=w2,
                         flag=flag))
    out[name] = dict(tau=tau, rows=rows)
    L.info("    (%.0f s)", time.time() - t0)

json.dump(out, open("/home/ubuntu/nbets/step2.json", "w"), indent=1)
L.info("\n=== TOM TAT: do dai khoi PASS (0.92<=phu<=0.97) theo generator ===")
for name in out:
    ok = [r["L"] for r in out[name]["rows"] if r["flag"] == "PASS"]
    lo = [r["L"] for r in out[name]["rows"] if r["flag"] == "DUOI-PHU"]
    L.info("  %-22s PASS=%s  DUOI-PHU=%s", name, ok, lo)
L.info("\nDONE step2")
