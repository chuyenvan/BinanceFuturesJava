"""T1_LABEL3 — bon chan S1 chi khac NHAN, di het tu train den bins.

Tuan `docs/PREREG_T1.md`. CHI DEV. CPU (GPU cam — BENCH_DEVICE). Khong ghi de artifact nao.

PHA A: cong REPRO — train `L_g1` tren POOL GOC bang chinh harness nay, phai cho
       spearman(score, ledger/pred_s1a2.parquet.score) = 1.000000. Truot => exit 2.
PHA B: 4 chan tren POOL GHEP CAP (co du g1lite + maxFav_4h + maxFav_72h),
       ghi pred_t1_<ma>.parquet, do rank-IC/edge5 + block-bootstrap ghep cap.
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
                    handlers=[logging.FileHandler("/home/ubuntu/cov/T1_LABEL3.out", "w"),
                              logging.StreamHandler(sys.stdout)])
LG = logging.getLogger("t1_label3")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label            # noqa: E402

H, Q, TZ, PURGE = 3600_000, 900_000, 7 * 3600_000, 72 * 3600_000
SEED_B, NREP, F_COV = 20260905, 2000, 1.21
K_M = float(np.sqrt(2 * np.log(3)))                # M = 3 phep so vs moc L_g1
LED = "/home/ubuntu/ledger"
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
        "ret_14d", "ls_global", "rk_oi_delta24h"]
CUTD = ["20220101", "20220401", "20220701", "20221001", "20230101",
        "20230401", "20230701", "20231001", "20240101", "20240401"]
CUT = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in CUTD]
FEAT = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet")


def add_rel5(D, col, out):
    """rel5 = ngu phan vi trong tick cua (col - median_tick(col)) — y het s1_rank.py."""
    rel = D[col] - D.groupby("ts")[col].transform("median")
    rk = rel.groupby(D.ts).rank(pct=True, method="first")
    D[out] = np.minimum((rk * 5).astype(int), 4)
    return D


def wfo(D, ycol, tag):
    """10 fold walk-forward, purge 72h. Tra ve ts,sym,<tag> voi <tag> = -pred (THAP = TOT)."""
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
        LG.info("%s fold %d %s: train %d oos %d ticks %d", tag, i, CUTD[i],
                len(tr), len(oos), oos.ts.nunique())
    P = pd.concat(preds)
    LG.info("%s: %d dong pred | %.0f s", tag, len(P), time.time() - t0)
    return P


# ================= PHA A — CONG REPRO tren POOL GOC =================
LG.info("=== PHA A: cong REPRO (recipe s1_rank.py, KHONG dropna feature) ===")
A = pd.read_parquet(f"{LED}/cand_dev.parquet")
A = A[A.g1lite.notna()].copy()
A = add_rel5(A, "g1lite", "y_g1")
A["ts_h"] = (A.ts // H) * H
A = A.merge(FEAT.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
LG.info("pool goc: rows=%d ticks=%d | co vol_7d=%.3f", len(A), A.ts.nunique(),
        A.vol_7d.notna().mean())
PA = wfo(A, "y_g1", "s_repro")
S1 = pd.read_parquet(f"{LED}/pred_s1a2.parquet")
chk = PA.merge(S1, on=["ts", "sym"], how="inner").dropna()
RHO = spearmanr(chk.s_repro, chk.score).correlation
LG.info("*** CONG REPRO: spearman(harness, pred_s1a2.score) = %.6f tren %d dong ***",
        RHO, len(chk))
if RHO < 0.9999:
    LG.error("*** REPRO TRUOT (%.6f < 0.9999) -> DUNG JOB. Khong bao cao chan nao. ***", RHO)
    sys.exit(2)
LG.info("CONG REPRO PASS\n")

# ================= POOL GHEP CAP =================
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
LG.info("pool ghep cap: rows=%d ticks=%d (pool goc %d / %d) | mat %d dong (%.4f)",
        len(B), B.ts.nunique(), len(A), A.ts.nunique(), len(A) - len(B),
        1 - len(B) / len(A))

# ================= BON CHAN =================
B = add_rel5(B, "g1lite", "y_L_g1")
B = add_rel5(B, "maxFav_4h", "y_L_f4q")
B["y_L_f4"] = (B.maxFav_4h >= 0.06).astype(int)
B["y_L_f72"] = (B.maxFav_72h >= 0.06).astype(int)
LG.info("ti le nhan duong: L_f4=%.4f L_f72=%.4f | rel5 L_g1 %s",
        B.y_L_f4.mean(), B.y_L_f72.mean(),
        B.y_L_g1.value_counts().sort_index().to_dict())

LEGS = ["L_g1", "L_f4", "L_f4q", "L_f72"]
SHORT = {"L_g1": "t1_g1", "L_f4": "t1_f4", "L_f4q": "t1_f4q", "L_f72": "t1_f72"}
SC = []
for nm in LEGS:
    P = wfo(B, f"y_{nm}", f"s_{nm}")
    out = P.rename(columns={f"s_{nm}": "score"})[["ts", "sym", "score"]]
    out.to_parquet(f"{LED}/pred_{SHORT[nm]}.parquet")
    LG.info("ghi %s/pred_%s.parquet (%d dong)", LED, SHORT[nm], len(out))
    B = B.merge(P, on=["ts", "sym"], how="left")
    SC.append(f"s_{nm}")

# ================= THUOC DO =================
OUTCOMES = {"g1lite": "g1lite", "maxFav_4h": "maxFav_4h", "maxFav_72h": "maxFav_72h"}
MINROW = 10


def per_tick_ic(frame, outcome):
    """rank-IC theo tick: spearman(pred, outcome). pred = -score (score THAP = TOT)."""
    rows = []
    for ts, g in frame.groupby("ts"):
        g = g.dropna(subset=[outcome] + SC)
        if len(g) < MINROW or g[outcome].nunique() < 2:
            continue
        r, bad = {"ts": ts}, False
        for s in SC:
            v = spearmanr(-g[s].values, g[outcome].values).correlation
            if not np.isfinite(v):
                bad = True
                break
            r[s] = v
        if not bad:
            rows.append(r)
    return pd.DataFrame(rows).set_index("ts")


def per_tick_edge5(frame, outcome):
    """edge5 = mean(outcome | top5 theo score) - mean(outcome | ca tick)."""
    rows = []
    for ts, g in frame.groupby("ts"):
        g = g.dropna(subset=[outcome] + SC)
        if len(g) < MINROW:
            continue
        base = g[outcome].mean()
        r = {"ts": ts}
        for s in SC:
            top = g.nsmallest(5, s)[outcome].mean()
            r[s] = top - base
        rows.append(r)
    return pd.DataFrame(rows).set_index("ts")


def block_boot(M, blen_h):
    """Block-bootstrap ghep cap: cung danh sach khoi cho MOI chan. Tra ve sd cua HIEU."""
    rng = np.random.default_rng(SEED_B)
    blk = (M.index.values // (blen_h * 3600_000)).astype(np.int64)
    uniq, inv = np.unique(blk, return_inverse=True)
    idx_by_blk = [np.where(inv == k)[0] for k in range(len(uniq))]
    V = M[SC].values
    nb = len(uniq)
    out = np.empty((NREP, len(SC)))
    for r in range(NREP):
        pick = rng.integers(0, nb, nb)
        rows = np.concatenate([idx_by_blk[k] for k in pick])
        out[r] = V[rows].mean(axis=0)
    return out


def report(M, title):
    LG.info("\n---- %s | n=%d tick ----", title, len(M))
    base = SC[0]
    pt = {s: M[s].mean() for s in SC}
    LG.info("| chan | %s |", " | ".join(k for k in ["diem"]))
    for s in SC:
        LG.info("  %-10s %+0.5f", s, pt[s])
    for blen in (72, 24, 168):
        BO = block_boot(M, blen)
        for j, s in enumerate(SC):
            if s == base:
                continue
            d = pt[s] - pt[base]
            sd = float(np.std(BO[:, j] - BO[:, 0], ddof=1))
            lo, hi = d - 1.96 * F_COV * sd, d + 1.96 * F_COV * sd
            LG.info("  BOOT%3dh %-10s d=%+0.5f sd=%0.5f f-CI=[%+0.5f,%+0.5f] excl0=%s |d|>k*f*sd=%s",
                    blen, s, d, sd, lo, hi, "YES" if lo * hi > 0 else "no",
                    "YES" if abs(d) > K_M * F_COV * sd else "no")


for onm, ocol in OUTCOMES.items():
    M = per_tick_ic(B, ocol)
    report(M, f"rank-IC vs {onm}")
    M.to_csv(f"/home/ubuntu/cov/T1_ic_{onm}.csv")

E = per_tick_edge5(B, "g1lite")
report(E, "edge5 vs g1lite (thuoc do goc cua s1_rank.py)")
E.to_csv("/home/ubuntu/cov/T1_edge5_g1lite.csv")
LG.info("K_M (M=3) = %.4f ; f = %.2f ; NREP = %d ; seed = %d", K_M, F_COV, NREP, SEED_B)
LG.info("DONE t1_label3")
