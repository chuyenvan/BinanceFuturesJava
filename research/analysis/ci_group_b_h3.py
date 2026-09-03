"""Nhom B (#10): CI cua HIEU spearman(pred, g1lite) — H3/A3a vs G015, tren CUNG hang.
Block-bootstrap khoi 72h. PREREG_CI section 3.
LUU Y phuong phap (ghi ro, khong che): spearman pooled KHONG phai thong ke cong tinh theo tick,
nen de bootstrap re toi DONG BANG HANG (rank tinh mot lan tren toan pool) roi bootstrap
Pearson cua cap (u,v) da rank-hoa. Day la xap xi tieu chuan cho spearman-bootstrap.
Kiem chung xap xi: sd cua rho_G015 phai ra ~0.0187 nhu LEAK_L1_REPORT section 3.3 do bang
bootstrap tho 400 rep. Neu khong khop thi ghi ro la khong khop."""
import logging
import numpy as np, pandas as pd
from scipy.stats import rankdata, spearmanr

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/ci/ciB2.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("ciB2")
SEED, NREP, H = 20260903, 2000, 3600_000
BLOCKS_H = [72, 24, 168]

Ph = pd.read_parquet("/home/ubuntu/ledger/h3/full/pred_h3a.parquet")
L.info("pred_h3a cols=%s shape=%s", list(Ph.columns), Ph.shape)
pcol = [c for c in Ph.columns if c not in ("ts", "sym")]
L.info("cot du doan dung: %s", pcol[0])
Ph = Ph[["ts", "sym", pcol[0]]].rename(columns={pcol[0]: "ph3"})

G = pd.read_parquet("/home/ubuntu/ledger/cand_dev3.parquet",
                    columns=["ts", "sym", "p_g015", "g1lite"])
M = Ph.merge(G, on=["ts", "sym"], how="inner").dropna(subset=["ph3", "p_g015", "g1lite"])
del Ph, G
L.info("n hang ghep = %d  (h3_metrics.json ghi n=14320746)", len(M))
L.info("ts range %s .. %s", pd.to_datetime(M.ts.min(), unit="ms"),
       pd.to_datetime(M.ts.max(), unit="ms"))

rho_h3 = spearmanr(M.ph3.values, M.g1lite.values).correlation
rho_g0 = spearmanr(M.p_g015.values, M.g1lite.values).correlation
L.info("[#10] rho(H3a, g1lite)=%+.5f  rho(G015, g1lite)=%+.5f  hieu=%+.5f",
       rho_h3, rho_g0, rho_h3 - rho_g0)
L.info("      (so cu trong AUDIT_APPLIED: 0.1667 vs 0.1675)")

n = len(M)
u = rankdata(M.ph3.values) / n
w = rankdata(M.p_g015.values) / n
v = rankdata(M.g1lite.values) / n
ts = M.ts.values
TS_MIN = ts.min()
del M

L.info("\n%-5s %4s %10s %10s %10s %10s %8s %6s", "id", "Lh", "d_diem", "lo95", "hi95",
       "sd", "P(d>0)", "n_blk")
res = {}
for bh in BLOCKS_H:
    bid = ((ts - TS_MIN) // (bh * H)).astype(np.int64)
    nb = bid.max() + 1
    acc = {}
    for nm, x in [("u", u), ("w", w), ("v", v)]:
        acc[nm] = np.bincount(bid, weights=x, minlength=nb)
        acc[nm + "2"] = np.bincount(bid, weights=x * x, minlength=nb)
    acc["uv"] = np.bincount(bid, weights=u * v, minlength=nb)
    acc["wv"] = np.bincount(bid, weights=w * v, minlength=nb)
    acc["n"] = np.bincount(bid, minlength=nb).astype(float)

    rng = np.random.default_rng(SEED)
    draw = rng.integers(0, nb, size=(NREP, nb))
    S = {k: acc[k][draw].sum(axis=1) for k in acc}

    def pear(xk, xk2, xkv):
        N_ = S["n"]
        cov = S[xkv] / N_ - (S[xk] / N_) * (S["v"] / N_)
        vx = S[xk2] / N_ - (S[xk] / N_) ** 2
        vy = S["v2"] / N_ - (S["v"] / N_) ** 2
        return cov / np.sqrt(vx * vy)

    r_h3 = pear("u", "u2", "uv")
    r_g0 = pear("w", "w2", "wv")
    d = r_h3 - r_g0
    lo, hi = np.percentile(d, [2.5, 97.5])
    res[bh] = (rho_h3 - rho_g0, lo, hi, d.std(ddof=1), (d > 0).mean())
    L.info("B10   %4d %+10.5f %+10.5f %+10.5f %10.5f %8.3f %6d", bh,
           rho_h3 - rho_g0, lo, hi, d.std(ddof=1), (d > 0).mean(), nb)
    L.info("      KIEM CHUNG: sd(rho_G015)=%.5f (LEAK_L1_REPORT ghi 0.0187 o block 72h); "
           "CI95 rho_G015=[%.4f, %.4f] (bao cao ghi [0.1260, 0.2005])",
           r_g0.std(ddof=1), *np.percentile(r_g0, [2.5, 97.5]))
    L.info("      CI95 rho_H3a=[%.4f, %.4f]", *np.percentile(r_h3, [2.5, 97.5]))

excl = [not (res[b][1] <= 0 <= res[b][2]) for b in BLOCKS_H]
L.info("\n=== PHAN LOAI B10: loai_tru0=%s -> %s",
       "".join("Y" if e else "n" for e in excl),
       "SONG/DAO CHIEU" if all(excl) else "KHONG PHAN BIET DUOC")
L.info("hieu = %+.5f = %.3f sd (sd block 72h = %.5f)",
       res[72][0], res[72][0] / res[72][3], res[72][3])
