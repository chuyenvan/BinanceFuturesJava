"""CEIL — tran oracle theo TUNG outcome, va % tran ma tung ranker bat duoc.
MO TA (descriptive), KHONG phai kiem gia thuyet: khong chon ung vien, khong co verdict
pass/fail, chi la tinh chat cua NHAN + du doan da co. Vi vay khong can pre-reg.
Ly do lam: tran 38.34% da cong bo duoc do tren `g1lite` — chinh la nhan ma
SELECTOR_FEATURES C.4 chung minh la BI VOL-CONFOUND (vol_7d tho thang S1 tren no).
Tran tren `g1_replay` (nhan sat tien that) CHUA TUNG duoc tinh.
CHI DEV.
"""
import logging

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/cov/CEIL.out", "w"),
                              logging.StreamHandler()])
LG = logging.getLogger("ceil")
H = 3600_000
SEED, NREP = 20260904, 2000
F_COV = 1.21   # he so hieu chinh do phu tu docs/COV_RESULT.md cho ho chuoi DAY

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet",
                    columns=["ts", "sym", "g1lite", "retEnd_72h", "maxFav_72h", "score_g015"])
P = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
R = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet",
                    columns=["ts", "sym", "g1_replay"])
Fv = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet", columns=["ts", "sym", "vol_7d"])
M = C.merge(P, on=["ts", "sym"], how="inner").merge(R, on=["ts", "sym"], how="left")
M["ts_h"] = (M.ts // H) * H
M = M.merge(Fv.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
M = M.dropna(subset=["g1_replay", "g1lite", "retEnd_72h", "vol_7d"])
LG.info("rows=%d ticks=%d syms=%d  ts %s .. %s", len(M), M.ts.nunique(), M.sym.nunique(),
        pd.to_datetime(M.ts.min(), unit="ms"), pd.to_datetime(M.ts.max(), unit="ms"))

# chi tick >= 10 dong (y PREREG_CI 3.2 / gate_vs_rank3)
cnt = M.groupby("ts").size()
M = M[M.ts.isin(cnt[cnt >= 10].index)].copy()
LG.info("sau loc tick>=10 dong: rows=%d ticks=%d", len(M), M.ts.nunique())

# rankers: score THAP = TOT cho S1/G015; vol_7d CAO = TOT (doi chung C.4 xep giam)
M["r_s1"] = M.groupby("ts").score.rank(ascending=True, method="first")
M["r_g015"] = M.groupby("ts").score_g015.rank(ascending=True, method="first")
M["r_vol"] = M.groupby("ts").vol_7d.rank(ascending=False, method="first")

OUTS = ["g1lite", "g1_replay", "retEnd_72h", "maxFav_72h"]
RANKERS = {"S1": "r_s1", "G015": "r_g015", "vol_7d_tho": "r_vol"}
K = 5

# per-tick: edge5 cua tung ranker + tran ORACLE cho tung outcome
rows = {}
for o in OUTS:
    M[f"r_or_{o}"] = M.groupby("ts")[o].rank(ascending=False, method="first")
g = M.groupby("ts")
pool_mean = g[OUTS].mean()
tab = {"pool_" + o: pool_mean[o] for o in OUTS}
for o in OUTS:
    for nm, rc in RANKERS.items():
        sel = M[M[rc] <= K]
        tab[f"{nm}|{o}"] = sel.groupby("ts")[o].mean() - pool_mean[o]
    sel = M[M[f"r_or_{o}"] <= K]
    tab[f"ORACLE|{o}"] = sel.groupby("ts")[o].mean() - pool_mean[o]
T = pd.DataFrame(tab).dropna()
LG.info("bang per-tick %s", T.shape)

ts_arr = T.index.values.astype(np.int64)
TS_MIN = ts_arr.min()
nb = int((ts_arr.max() - TS_MIN) // (72 * H)) + 1
bid = ((ts_arr - TS_MIN) // (72 * H)).astype(np.int64)
rng = np.random.default_rng(SEED)
draw = rng.integers(0, nb, size=(NREP, nb))


def boot_ratio(num, den):
    """CI cua TI SO hai trung binh theo tick, cung danh sach khoi (ghep cap)."""
    sn = np.bincount(bid, weights=num, minlength=nb)[:nb]
    sd_ = np.bincount(bid, weights=den, minlength=nb)[:nb]
    cn = np.bincount(bid, minlength=nb)[:nb].astype(float)
    a = sn[draw].sum(axis=1) / np.maximum(cn[draw].sum(axis=1), 1e-12)
    b = sd_[draw].sum(axis=1) / np.maximum(cn[draw].sum(axis=1), 1e-12)
    return a / np.where(np.abs(b) < 1e-12, np.nan, b)


LG.info("\n=== TRAN ORACLE VA %% BAT DUOC, theo TUNG outcome (edge5, K=5, %d tick, %d khoi 72h) ===",
        len(T), nb)
LG.info("%-12s %-12s %10s %10s %9s %-22s", "outcome", "ranker", "edge5", "tran", "%bat", "CI95 cua %bat")
res = {}
for o in OUTS:
    orc = T[f"ORACLE|{o}"].values
    tran = orc.mean()
    for nm in RANKERS:
        v = T[f"{nm}|{o}"].values
        share = v.mean() / tran
        rb = boot_ratio(v, orc)
        lo, hi = np.nanpercentile(rb, [2.5, 97.5])
        res[(o, nm)] = (v.mean(), tran, share, lo, hi)
        LG.info("%-12s %-12s %+9.4f%% %+9.4f%% %8.1f%% [%6.1f%%, %6.1f%%]",
                o, nm, 100 * v.mean(), 100 * tran, 100 * share, 100 * lo, 100 * hi)
    LG.info("%-12s %-12s %+9.4f%% %+9.4f%% %8.1f%% %s", o, "(ORACLE)", 100 * tran, 100 * tran,
            100.0, "-")
    LG.info("%-12s pool mean = %+.4f%%", o, 100 * pool_mean[o].mean())
    LG.info("")

LG.info("=== HIEU S1 - vol_7d tho theo tung outcome (ghep cap, khoi 72h) ===")
for o in OUTS:
    d = T[f"S1|{o}"].values - T[f"vol_7d_tho|{o}"].values
    s = np.bincount(bid, weights=d, minlength=nb)[:nb]
    c = np.bincount(bid, minlength=nb)[:nb].astype(float)
    st = s[draw].sum(axis=1) / np.maximum(c[draw].sum(axis=1), 1e-12)
    lo, hi = np.percentile(st, [2.5, 97.5])
    sd = st.std(ddof=1)
    loc, hic = d.mean() - 1.96 * sd * F_COV, d.mean() + 1.96 * sd * F_COV
    LG.info("%-12s d=%+.4f%% CI[%+.4f%%,%+.4f%%] sd=%.5f | sau hieu chinh f=1.21: [%+.4f%%,%+.4f%%] %s",
            o, 100 * d.mean(), 100 * lo, 100 * hi, sd, 100 * loc, 100 * hic,
            "LOAI TRU 0" if loc * hic > 0 else "chua 0")
LG.info("\nDONE_CEIL")
