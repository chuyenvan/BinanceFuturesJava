"""Buoc C — hieu chuan gate 1 chieu (python). Dua admit-rate G015_v2 ve diem van hanh p_old
tren cand_dev3. Tim he so c tren SIM_MIN_MOMENTUM_15M. Xem PREREG_G015REBUILD sec 4."""
import json, logging, numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
L = logging.getLogger("gatecal")
GMM, GAMIN, GAMULT, GRMAX = 0.008, 0.26787, 1.2876, 0.15
pool = pd.read_parquet("/home/ubuntu/g015/pool/pool_dev.parquet")
p15 = pool.p15.to_numpy(np.float64)
y = pool.g1lite.to_numpy(np.float64)
p_old = pool.p_old.to_numpy(np.float64)
p_new = np.load("/home/ubuntu/predwf_G015_v2/pred_pool.npy").astype(np.float64)


def dyn_thr(score, c):
    return c * GMM * np.maximum(GAMIN, score / GRMAX * GAMULT)


def admit(p, c):
    return p15 >= dyn_thr(1.0 - p, c)


def report(tag, p, c):
    a = admit(p, c)
    n = int(a.sum())
    L.info("%-12s c=%.5f MIN_MOM=%.6f n_admit=%7d rate=%.5f q(mean g1lite)=%.5f",
           tag, c, c * GMM, n, n / len(p), float(y[a].mean()) if n else float("nan"))
    return n


n_old = report("p_old c=1", p_old, 1.0)
report("G015_v2 c=1", p_new, 1.0)
# bisection: tim c sao cho n_admit(G015_v2) ~ n_old
lo, hi = 0.2, 20.0
best = None
for _ in range(80):
    mid = 0.5 * (lo + hi)
    n = int(admit(p_new, mid).sum())
    if abs(n - n_old) <= max(1, int(0.005 * n_old)):
        best = mid
        break
    if n > n_old:
        lo = mid
    else:
        hi = mid
if best is None:
    best = 0.5 * (lo + hi)
L.info("=== HIEU CHUAN: c=%.5f -> SIM_MIN_MOMENTUM_15M = %.6f (tu 0.008) ===", best, best * GMM)
n_new = report("G015_v2 cal", p_new, best)
L.info("dung sai: |%d - %d| = %d (<=5%% cua %d = %d? %s)", n_new, n_old, abs(n_new - n_old),
       n_old, int(0.05 * n_old), abs(n_new - n_old) <= 0.05 * n_old)
json.dump({"c": best, "min_momentum_15m": round(best * GMM, 6), "n_admit_target": n_old,
           "n_admit_g015v2_cal": n_new, "n_admit_g015v2_default": int(admit(p_new, 1.0).sum()),
           "q_p_old": float(y[admit(p_old, 1.0)].mean()),
           "q_g015v2_cal": float(y[admit(p_new, best)].mean())},
          open("/home/ubuntu/g015/gatecal.json", "w"), indent=1)
L.info("ghi /home/ubuntu/g015/gatecal.json")
