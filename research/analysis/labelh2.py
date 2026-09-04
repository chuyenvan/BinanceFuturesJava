"""LABELH2 — sua theo PREREG_LABELH SUA DOI 1. Tach cong kiem lam HAI PHA:
  PHA A (kiem HARNESS): chay dung recipe s1_rank.py tren POOL GOC (khong cat) => phai trung
          pred_s1a2 >= 0.999. Chung minh harness trung thuc.
  PHA B (so 3 bien the): tren pool DA CAT (co du 3 nhan), moc so la L72_g1lite train tren
          CHINH pool cat do — KHONG so voi ban deploy.
Sua so voi ban truoc: (1) khong `dropna` tren feature — s1_rank.py merge LEFT va de NaN cho
XGBoost tu xu ly; (2) cong kiem dung dau (score cung quy uoc THAP=TOT). CPU. CHI DEV.
"""
import glob
import logging
import sys
import time

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/cov/LABELH2.out", "w"),
                              logging.StreamHandler()])
LG = logging.getLogger("labelh2")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label

H, Q, TZ, PURGE = 3600_000, 900_000, 7 * 3600_000, 72 * 3600_000
SEED_B, NREP, F_COV = 20260904, 2000, 1.21
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
        "ret_14d", "ls_global", "rk_oi_delta24h"]
CUTD = ["20220101", "20220401", "20220701", "20221001", "20230101",
        "20230401", "20230701", "20231001", "20240101", "20240401"]
CUT = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in CUTD]
FEAT = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet")


def add_rel5(D, col, out):
    med = D.groupby("ts")[col].transform("median")
    rel = D[col] - med
    rk = rel.groupby(D.ts).rank(pct=True, method="first")
    D[out] = np.minimum((rk * 5).astype(int), 4)
    return D


def wfo(D, ycol, tag):
    t0, preds = time.time(), []
    for i, c in enumerate(CUT):
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = D[D.ts < c - PURGE].sort_values("ts")
        oos = D[(D.ts >= c) & (D.ts < hi)].sort_values("ts")
        if len(tr) < 5000 or not len(oos):
            LG.info("%s fold %d SKIP (tr=%d oos=%d)", tag, i, len(tr), len(oos))
            continue
        assert tr.ts.max() < c, "LEAK"
        m = xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4,
                          learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                          min_child_weight=50, n_jobs=4, tree_method="hist", random_state=42,
                          lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=8)
        m.fit(tr[KEEP], tr[ycol], qid=pd.factorize(tr.ts, sort=True)[0])
        preds.append(oos[["ts", "sym"]].assign(**{tag: -m.predict(oos[KEEP])}))
    P = pd.concat(preds)
    LG.info("%s: %d dong pred | %.0f s", tag, len(P), time.time() - t0)
    return P


# ================= PHA A — KIEM HARNESS tren POOL GOC =================
LG.info("=== PHA A: kiem harness tren POOL GOC (recipe s1_rank.py, KHONG dropna feature) ===")
A = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet")
A = A[A.g1lite.notna()].copy()
A = add_rel5(A, "g1lite", "y")
A["ts_h"] = (A.ts // H) * H
A = A.merge(FEAT.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
LG.info("pool goc: rows=%d ticks=%d | co vol_7d=%.3f", len(A), A.ts.nunique(),
        A.vol_7d.notna().mean())
PA = wfo(A, "y", "s_harness")
S1 = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
chk = PA.merge(S1, on=["ts", "sym"], how="inner").dropna()
rho_h = spearmanr(chk.s_harness, chk.score).correlation
LG.info("*** PHA A: spearman(harness, score pred_s1a2) = %.6f tren %d dong ***", rho_h, len(chk))
if rho_h < 0.999:
    LG.error("*** HARNESS KHONG TRUNG THUC (%.6f < 0.999) -> DUNG. Khong bao cao bien the. ***",
             rho_h)
    sys.exit(2)
LG.info("PHA A PASS => harness trung thuc voi s1_rank.py\n")

# ================= PHA B — SO 3 BIEN THE tren POOL GHEP CAP =================
LG.info("=== PHA B: 3 bien the tren pool ghep cap (co du 3 nhan) ===")
mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
sym2id = dict(zip(mp.symbol, mp.symId))
keep_ts = set(A.ts.unique())
parts = []
for f in sorted(glob.glob("/home/ubuntu/label_15m/funding_label_202[1-4]*.pb")):
    L = read_label(f, usecols=["tEpochMs", "symbol", "maxFav_4h", "nBars_4h"])
    L = L[(L.tEpochMs % Q == 0) & (L.tEpochMs.isin(keep_ts)) & (L.nBars_4h >= 16)]
    if not len(L):
        continue
    L["sym"] = L.symbol.map(sym2id)
    L = L.dropna(subset=["sym"])
    L["sym"] = L.sym.astype(np.int64)
    parts.append(L[["tEpochMs", "sym", "maxFav_4h"]].rename(columns={"tEpochMs": "ts"}))
B = A.merge(pd.concat(parts), on=["ts", "sym"], how="inner")
B = B.dropna(subset=["g1lite", "maxFav_72h", "maxFav_4h"])
LG.info("pool ghep cap: rows=%d ticks=%d (pool goc %d / %d)", len(B), B.ts.nunique(),
        len(A), A.ts.nunique())

LABELS = {"L72_g1lite": "g1lite", "L72_maxfav": "maxFav_72h", "L4_maxfav": "maxFav_4h"}
for nm, col in LABELS.items():
    B = add_rel5(B, col, f"y_{nm}")
SC = []
for nm in LABELS:
    P = wfo(B, f"y_{nm}", f"s_{nm}")
    B = B.merge(P, on=["ts", "sym"], how="left")
    SC.append(f"s_{nm}")

PL = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet",
                     columns=["ts", "sym", "g1_replay"])
B = B.merge(PL, on=["ts", "sym"], how="left")
B["pathq_72h"] = B.maxFav_72h / (B.maxAdv_72h.abs() + 0.01)

VN = 7 * 3600 * 1000
td = pd.read_csv("/home/ubuntu/java/devrun/C2b/storage/printDone.csv")
td = td[td.level == "PREDICT_SYMBOL_TRADE"].copy()
td["ts"] = ((pd.to_datetime(td.start, format="%Y%m%d %H:%M").astype("int64") // 10**6 - VN)
            // Q) * Q
td["sym"] = (td.sym + "USDT").map(sym2id)
td["roi"] = td.pnl / td.margin
TD = td[["ts", "sym", "roi"]].dropna()
Btr = B.merge(TD, on=["ts", "sym"], how="inner")
LG.info("join lenh C2b <-> pool: %d dong / %d lenh", len(Btr), len(TD))


def per_tick_ic(frame, outcome, minrow):
    rows = []
    for ts, g in frame.groupby("ts"):
        g = g.dropna(subset=[outcome] + SC)
        if len(g) < minrow or g[outcome].nunique() < 2:
            continue
        r, bad = {"ts": ts}, False
        for s in SC:
            v = spearmanr(-g[s].values, g[outcome].values).correlation
            if np.isnan(v):
                bad = True
                break
            r[s] = v
        if not bad:
            rows.append(r)
    return pd.DataFrame(rows).set_index("ts")


for tag, frame, outcome, minrow, bias in [
        ("A_g1_replay", B, "g1_replay", 10, "ho 72h"),
        ("B_pathq_72h", B, "pathq_72h", 10, "ho 72h"),
        ("C_ROI_that", Btr, "roi", 4, "tap do S1 hien tai chon")]:
    IC = per_tick_ic(frame, outcome, minrow)
    if len(IC) < 20:
        LG.info("\n[%s] chi %d tick -> bo qua", tag, len(IC))
        continue
    LG.info("\n=== [%s] rank-IC vs %s | n_tick=%d | THIEN VI: %s ===", tag, outcome, len(IC), bias)
    for s in SC:
        LG.info("   %-16s %+.5f", s, IC[s].mean())
    ts_a = IC.index.values.astype(np.int64)
    tmin = ts_a.min()
    for bh in (72, 24, 168):
        nb = int((ts_a.max() - tmin) // (bh * H)) + 1
        bid = ((ts_a - tmin) // (bh * H)).astype(np.int64)
        cn = np.bincount(bid, minlength=nb)[:nb].astype(float)
        draw = np.random.default_rng(SEED_B).integers(0, nb, size=(NREP, nb))
        for s in SC[1:]:
            d = IC[s].values - IC["s_L72_g1lite"].values
            sm = np.bincount(bid, weights=d, minlength=nb)[:nb]
            st = sm[draw].sum(axis=1) / np.maximum(cn[draw].sum(axis=1), 1e-12)
            sd, dm = st.std(ddof=1), d.mean()
            lo, hi = dm - 1.96 * F_COV * sd, dm + 1.96 * F_COV * sd
            LG.info("   [%3dh] %-12s - L72_g1lite d=%+.5f CI_f=[%+.5f,%+.5f] %s | |d|>k*f*sd? %s",
                    bh, s, dm, lo, hi, "LOAI TRU 0" if lo * hi > 0 else "chua 0",
                    "CO" if abs(dm) > 1.1774 * F_COV * sd else "khong")
LG.info("\nDONE_LABELH2")
