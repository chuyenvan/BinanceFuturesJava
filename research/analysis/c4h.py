"""C4H — do lai o chan troi 4h voi nhan maxFav_4h va nhan NHI PHAN maxFav_4h >= 0.06
(= dung nhan that cua G015), doi chieu voi 72h. MO TA, khong phai kiem gia thuyet.
CHI DEV. Khong train, khong ghi de gi.
"""
import glob
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/cov/C4H.out", "w"),
                              logging.StreamHandler()])
LG = logging.getLogger("c4h")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label

H = 3600_000
Q = 900_000
SEED, NREP, K = 20260904, 2000, 5
THR = 0.06

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet",
                    columns=["ts", "sym", "g1lite", "maxFav_72h", "retEnd_72h", "score_g015"])
P = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
Fv = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet", columns=["ts", "sym", "vol_7d"])
M = C.merge(P, on=["ts", "sym"], how="inner")
M["ts_h"] = (M.ts // H) * H
M = M.merge(Fv.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
LG.info("base rows=%d ticks=%d", len(M), M.ts.nunique())

mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
sym2id = dict(zip(mp.symbol, mp.symId))
keep_ts = set(M.ts.unique())
parts = []
for f in sorted(glob.glob("/home/ubuntu/label_15m/funding_label_202[2-4]*.pb")):
    L = read_label(f, usecols=["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h"])
    L = L[(L.tEpochMs % Q == 0) & (L.tEpochMs.isin(keep_ts))]
    if len(L) == 0:
        continue
    L["sym"] = L.symbol.map(sym2id)
    L = L.dropna(subset=["sym"])
    L["sym"] = L.sym.astype(np.int64)
    parts.append(L.drop(columns=["symbol"]).rename(columns={"tEpochMs": "ts"}))
    LG.info("  %s -> %d dong", f.split("/")[-1], len(L))
L4 = pd.concat(parts)
LG.info("label 4h rows=%d", len(L4))

M = M.merge(L4, on=["ts", "sym"], how="inner")
LG.info("sau join 4h: rows=%d ticks=%d", len(M), M.ts.nunique())
M = M[M.nBars_4h >= 16]
M = M.dropna(subset=["maxFav_4h", "g1lite", "vol_7d", "score", "score_g015"])
LG.info("sau nBars_4h>=16 + dropna: rows=%d ticks=%d", len(M), M.ts.nunique())
cnt = M.groupby("ts").size()
M = M[M.ts.isin(cnt[cnt >= 10].index)].copy()
LG.info("sau tick>=10: rows=%d ticks=%d", len(M), M.ts.nunique())

M["hit6_4h"] = (M.maxFav_4h >= THR).astype(float)
M["r_s1"] = M.groupby("ts").score.rank(ascending=True, method="first")
M["r_g015"] = M.groupby("ts").score_g015.rank(ascending=True, method="first")
M["r_vol"] = M.groupby("ts").vol_7d.rank(ascending=False, method="first")
RANKERS = {"S1": "r_s1", "G015": "r_g015", "vol_7d_tho": "r_vol"}
OUTS = ["maxFav_4h", "hit6_4h", "retEnd_4h", "g1lite", "maxFav_72h"]

LG.info("\n=== ty le nen nhan 4h ===")
LG.info("P(maxFav_4h >= 6%%) tren pool = %.4f%%  | maxFav_4h TB = %+.4f%% | retEnd_4h TB = %+.4f%%",
        100 * M.hit6_4h.mean(), 100 * M.maxFav_4h.mean(), 100 * M.retEnd_4h.mean())
LG.info("tuong quan hang maxFav_4h vs maxFav_72h = %.4f | vs g1lite = %.4f",
        M.maxFav_4h.corr(M.maxFav_72h, method="spearman"),
        M.maxFav_4h.corr(M.g1lite, method="spearman"))

for o in OUTS:
    M[f"r_or_{o}"] = M.groupby("ts")[o].rank(ascending=False, method="first")
g = M.groupby("ts")
pool = g[OUTS].mean()
tab = {}
for o in OUTS:
    for nm, rc in RANKERS.items():
        tab[f"{nm}|{o}"] = M[M[rc] <= K].groupby("ts")[o].mean() - pool[o]
    tab[f"ORACLE|{o}"] = M[M[f"r_or_{o}"] <= K].groupby("ts")[o].mean() - pool[o]
T = pd.DataFrame(tab).dropna()

ts_arr = T.index.values.astype(np.int64)
TS_MIN = ts_arr.min()
nb = int((ts_arr.max() - TS_MIN) // (72 * H)) + 1
bid = ((ts_arr - TS_MIN) // (72 * H)).astype(np.int64)
rng = np.random.default_rng(SEED)
draw = rng.integers(0, nb, size=(NREP, nb))
cn = np.bincount(bid, minlength=nb)[:nb].astype(float)


def bmean(v):
    s = np.bincount(bid, weights=v, minlength=nb)[:nb]
    return s[draw].sum(axis=1) / np.maximum(cn[draw].sum(axis=1), 1e-12)


LG.info("\n=== TRAN ORACLE + %% BAT DUOC (edge5, K=%d, %d tick, %d khoi 72h) ===", K, len(T), nb)
LG.info("%-12s %-12s %11s %11s %9s %-20s", "outcome", "ranker", "edge5", "tran", "%bat", "CI95 %bat")
for o in OUTS:
    orc = T[f"ORACLE|{o}"].values
    tran = orc.mean()
    bo = bmean(orc)
    for nm in RANKERS:
        v = T[f"{nm}|{o}"].values
        bv = bmean(v)
        rb = bv / np.where(np.abs(bo) < 1e-12, np.nan, bo)
        lo, hi = np.nanpercentile(rb, [2.5, 97.5])
        LG.info("%-12s %-12s %+10.4f%% %+10.4f%% %8.1f%% [%6.1f%%, %6.1f%%]",
                o, nm, 100 * v.mean(), 100 * tran, 100 * v.mean() / tran, 100 * lo, 100 * hi)
    LG.info("%-12s %-12s %+10.4f%% %+10.4f%% %8.1f%% -", o, "(ORACLE)", 100 * tran, 100 * tran, 100.0)
    LG.info("%-12s pool = %+.4f%%\n", o, 100 * pool[o].mean())

LG.info("=== HIEU S1 - G015 va S1 - vol_7d (ghep cap, khoi 72h, f_cov=1.21) ===")
for o in OUTS:
    for other in ("G015", "vol_7d_tho"):
        d = T[f"S1|{o}"].values - T[f"{other}|{o}"].values
        st = bmean(d)
        sd = st.std(ddof=1)
        lo, hi = np.percentile(st, [2.5, 97.5])
        loc, hic = d.mean() - 1.96 * sd * 1.21, d.mean() + 1.96 * sd * 1.21
        LG.info("%-12s S1-%-11s d=%+.4f%% CI[%+.4f%%,%+.4f%%] | f=1.21: [%+.4f%%,%+.4f%%] %s",
                o, other, 100 * d.mean(), 100 * lo, 100 * hi, 100 * loc, 100 * hic,
                "LOAI TRU 0" if loc * hic > 0 else "chua 0")

LG.info("\n=== rank-IC theo tick (spearman) ===")
from scipy.stats import spearmanr
rows = []
for ts, gg in M.groupby("ts"):
    if len(gg) < 10:
        continue
    r = {"ts": ts}
    for nm, col, asc in [("S1", "score", True), ("G015", "score_g015", True),
                         ("vol_7d_tho", "vol_7d", False)]:
        x = gg[col].values * (-1.0 if asc else 1.0)
        for o in ("maxFav_4h", "hit6_4h", "g1lite"):
            v = spearmanr(x, gg[o].values).correlation
            r[f"{nm}|{o}"] = v
    rows.append(r)
IC = pd.DataFrame(rows).set_index("ts").dropna()
LG.info("n_tick co rank-IC = %d", len(IC))
for o in ("maxFav_4h", "hit6_4h", "g1lite"):
    line = " | ".join(f"{nm} {IC[f'{nm}|{o}'].mean():+.4f}" for nm in RANKERS)
    LG.info("%-12s %s", o, line)
LG.info("\nDONE_C4H")
