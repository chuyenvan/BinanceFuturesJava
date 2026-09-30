#!/usr/bin/env python3
"""netthr_metrics.py — TANG MODEL cho sweep NET_THR (PREREG_LABEL_NETTHR.md).
Target do CO DINH = retEnd_4h (win_ref = retEnd_4h > 0.015 cho lift/AUC). DEV <= 2025-12-31 (16 fold).
Moi fold: per-timestamp cross-section rank-IC (Spearman), AUC_cs, lift@8; paired delta vs M_015;
CI block-72h 2000 rep seed 20260905; inflate k=2 -> x1.177."""
import argparse, glob, json, logging, math, os, sys
import numpy as np
import pandas as pd
from scipy.stats import rankdata

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("netthr_metrics")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import funding_label_pb as FLPB

CUTS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701", "20231001",
        "20240101", "20240401", "20240701", "20241001", "20250101", "20250401", "20250701", "20251001"]
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4"), ("n", ">f4", 3)])
LB_DIR = "/home/ubuntu/label_15m"
MAP_CSV = "/home/ubuntu/claudedata/oi/symbol_map.csv"
WIN = 0.015
TOPK = 8
MIN_N = 30
BLOCK_MS = 72 * 3600 * 1000
NREP = 2000
SEED = 20260905
INFL = math.sqrt(2 * math.log(2))


def load_bin(path):
    a = np.fromfile(path, dtype=DT)
    return pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32),
                         "p": a["p"].astype(np.float64)})


def load_ret():
    fs = sorted(glob.glob(LB_DIR + "/funding_label_*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20260101"]   # HOLDOUT SEAL
    smap = pd.read_csv(MAP_CSV)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    parts = []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=["tEpochMs", "symbol", "retEnd_4h", "nBars_4h"])
        d = d[(d["nBars_4h"] >= 16) & d["retEnd_4h"].notna()]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        parts.append(pd.DataFrame({"ts": d.tEpochMs.to_numpy(np.int64)[k],
                                   "symId": sid[k].to_numpy(np.int32),
                                   "r": d["retEnd_4h"].to_numpy(np.float64)[k]}))
    L = pd.concat(parts, ignore_index=True)
    log.info("retEnd_4h labels (pre-2026): %d rows", len(L))
    return L


def xs_metrics(ts, rmat, r):
    """ts sorted; rmat dict arm->p array. Tra ve DataFrame per-timestamp."""
    bnd = np.flatnonzero(np.diff(ts)) + 1
    starts = np.concatenate([[0], bnd])
    ends = np.concatenate([bnd, [len(ts)]])
    arms = list(rmat.keys())
    rows = []
    for s, e in zip(starts, ends):
        n = e - s
        if n < MIN_N:
            continue
        rr = r[s:e]
        win = rr > WIN
        n1 = int(win.sum())
        rk_r = rankdata(rr)
        rec = {"ts": int(ts[s]), "n": n, "univ_ret": float(rr.mean()), "univ_win": n1 / n}
        ranks = {}
        for a in arms:
            p = rmat[a][s:e]
            rp = rankdata(p)
            ranks[a] = rp
            rec[a + "_ic"] = float(np.corrcoef(rp, rk_r)[0, 1])
            if 0 < n1 < n:
                rec[a + "_auc"] = float((rk_r_win(rp, win) - n1 * (n1 + 1) / 2) / (n1 * (n - n1)))
            else:
                rec[a + "_auc"] = np.nan
            top = np.argsort(-p, kind="stable")[:TOPK]
            rec[a + "_t8win"] = float(win[top].mean())
            rec[a + "_t8ret"] = float(rr[top].mean())
        for a in arms:
            if a != arms[0]:
                rec[a + "_xc"] = float(np.corrcoef(ranks[a], ranks[arms[0]])[0, 1])
        rows.append(rec)
    return pd.DataFrame(rows)


def rk_r_win(rp, win):
    return float(rp[win].sum())


def boot_delta(T, arm, base, metric, rng_draws):
    """T: per-ts df cua 1 fold. Tra ve mang NREP cua mean(delta) theo block 72h."""
    x = (T[arm + "_" + metric] - T[base + "_" + metric]).to_numpy()
    ok = ~np.isnan(x)
    blk = (T["ts"].to_numpy() // BLOCK_MS)
    ub, inv = np.unique(blk, return_inverse=True)
    S = np.bincount(inv, weights=np.where(ok, x, 0.0), minlength=len(ub))
    N = np.bincount(inv, weights=ok.astype(float), minlength=len(ub))
    idx = rng_draws
    return S[idx].sum(1) / np.maximum(N[idx].sum(1), 1)


def ci(dist, point):
    lo, hi = np.percentile(dist, [2.5, 97.5])
    return {"lo": float(lo), "hi": float(hi),
            "lo_infl": float(point - INFL * (point - lo)), "hi_infl": float(point + INFL * (hi - point))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", required=True, help="M_015=dir,M_010=dir,M_020=dir")
    ap.add_argument("--orig", default="/home/ubuntu/claudedata/predwf_G015x26")
    ap.add_argument("--cuts", default=",".join(CUTS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--tsdump", default=None)
    a = ap.parse_args()
    dirs = dict(x.split("=") for x in a.dirs.split(","))
    arms = list(dirs.keys())
    base = arms[0]
    cuts = a.cuts.split(",")
    assert all(c in CUTS for c in cuts)
    L = load_ret()
    res = {"arms": arms, "base": base, "win_ref": WIN, "topk": TOPK, "min_n": MIN_N, "nrep": NREP,
           "seed": SEED, "infl": INFL, "folds": {}}
    per_fold_T = {}
    for c in cuts:
        D = None
        for k in arms:
            b = load_bin(os.path.join(dirs[k], "predict_wf_%s.bin" % c)).rename(columns={"p": k})
            D = b if D is None else D.merge(b, on=["ts", "symId"], how="inner", validate="1:1")
            if D is not b:
                assert len(D) == len(b), "%s %s key mismatch" % (k, c)
        o = load_bin(os.path.join(a.orig, "predict_wf_%s.bin" % c)).rename(columns={"p": "ORIG"})
        D = D.merge(o, on=["ts", "symId"], how="inner", validate="1:1")
        D = D.merge(L, on=["ts", "symId"], how="inner")
        assert int(D.ts.max()) < 1767225600000, "2026 leak"
        D = D.sort_values(["ts", "symId"], kind="stable").reset_index(drop=True)
        pm = {k: D[k].to_numpy() for k in arms + ["ORIG"]}
        T = xs_metrics(D.ts.to_numpy(), pm, D.r.to_numpy())
        per_fold_T[c] = T
        f = {"n_rows": int(len(D)), "n_ts": int(len(T)), "univ_win": float(T.univ_win.mean()),
             "orig_vs_" + base + "_spearman_xs": float(T["ORIG_xc"].mean()) if "ORIG_xc" in T else None}
        for k in arms + ["ORIG"]:
            f[k] = {"rank_ic": float(T[k + "_ic"].mean()), "auc_cs": float(T[k + "_auc"].mean()),
                    "t8win": float(T[k + "_t8win"].mean()), "lift8": float(T[k + "_t8win"].mean() / T.univ_win.mean()),
                    "t8ret_spread": float((T[k + "_t8ret"] - T["univ_ret"]).mean()),
                    "p_mean": float(D[k].mean()), "p_std": float(D[k].std())}
            if k != base:
                f[k]["xs_rank_corr_vs_" + base] = float(T[k + "_xc"].mean())
        res["folds"][c] = f
        log.info("fold %s rows=%d ts=%d | IC %s", c, len(D), len(T),
                 {k: round(f[k]["rank_ic"], 5) for k in arms + ["ORIG"]})
        del D
    # ---- bootstrap paired
    metrics = ["ic", "auc", "t8win", "t8ret"]
    boot = {}
    for arm in [x for x in arms + ["ORIG"] if x != base]:
        rng = np.random.default_rng(SEED)
        per_fold = {m: {} for m in metrics}
        allrep = {m: [] for m in metrics}
        for c in cuts:
            T = per_fold_T[c]
            blk = (T["ts"].to_numpy() // BLOCK_MS)
            nb = len(np.unique(blk))
            idx = rng.integers(0, nb, size=(NREP, nb))
            for m in metrics:
                d = boot_delta(T, arm, base, m, idx)
                pt = float((T[arm + "_" + m] - T[base + "_" + m]).mean())
                per_fold[m][c] = dict(delta=pt, **ci(d, pt))
                allrep[m].append(d)
        boot[arm] = {"per_fold": per_fold, "overall": {}}
        for m in metrics:
            dist = np.mean(np.vstack(allrep[m]), axis=0)
            pt = float(np.mean([per_fold[m][c]["delta"] for c in cuts]))
            boot[arm]["overall"][m] = dict(delta=pt, **ci(dist, pt))
        # lift delta (chia base rate trung binh cac fold)
        bw = float(np.mean([res["folds"][c]["univ_win"] for c in cuts]))
        ov = boot[arm]["overall"]["t8win"]
        boot[arm]["overall"]["lift8"] = {k: v / bw for k, v in ov.items()}
        npos = sum(1 for c in cuts if per_fold["ic"][c]["delta"] > 0)
        boot[arm]["n_folds_ic_pos"] = npos
        boot[arm]["n_folds_ic_ci_pos"] = sum(1 for c in cuts if per_fold["ic"][c]["lo"] > 0)
    res["boot"] = boot
    gate = {}
    for arm in [x for x in arms if x != base]:
        o = boot[arm]["overall"]["ic"]
        gate[arm] = {"delta_ic": o["delta"], "ci_raw": [o["lo"], o["hi"]], "ci_infl": [o["lo_infl"], o["hi_infl"]],
                     "pass_infl": bool(o["lo_infl"] > 0), "pass_raw": bool(o["lo"] > 0)}
    res["gate"] = gate
    res["overall_means"] = {k: {m: float(np.mean([res["folds"][c][k][m] for c in cuts]))
                                for m in ["rank_ic", "auc_cs", "lift8", "t8ret_spread", "p_mean", "p_std"]}
                            for k in arms + ["ORIG"]}
    res["overall_xs_rank_corr"] = {k: float(np.mean([res["folds"][c][k]["xs_rank_corr_vs_" + base] for c in cuts]))
                                   for k in arms[1:] + ["ORIG"]}
    json.dump(res, open(a.out, "w"), indent=1)
    if a.tsdump:
        pd.concat([t.assign(fold=c) for c, t in per_fold_T.items()]).to_parquet(a.tsdump)
    log.info("GATE %s", json.dumps(gate))
    log.info("overall IC %s", json.dumps({k: v["rank_ic"] for k, v in res["overall_means"].items()}))


if __name__ == "__main__":
    main()
