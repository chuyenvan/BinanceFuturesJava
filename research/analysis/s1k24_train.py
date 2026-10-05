#!/usr/bin/env python3
"""S1_K24 — train S1 ranker (recipe research/pipeline/x1/x1_s1_rank.py 2x1) voi tham so CLI topk/rel/seed/feats.
Pre-reg docs/prereg/PREREG_S1_K24.md (15ec9e18). CHI Python; khong sua .java; DEV <= 2025.
Duong mac dinh (--topk 8 --rel 5 --seed 42 --feats keep9) = x1_s1_rank.py 2x1 nguyen van (bo phan shuffle/IC chan doan,
khong anh huong model chinh) => cong G0: pred trung GIA TRI ~/ledger/pred_s1a2x1.parquet (sha 2618fe1a).
ARM-B: --topk 24 --rel 10 --feats keep9 --seed {42,7}; ARM-C: --topk 24 --rel 10 --feats keep9geom --seed {42,7}.
Usage: python3 s1k24_train.py train --name NAME [--topk 8] [--rel 5] [--seed 42] [--feats keep9]
       python3 s1k24_train.py g0 --name NAME     (so pred NAME voi pred_s1a2x1 goc)
"""
import argparse
import hashlib
import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("s1k24_train")
H = 3600000
TZ = 7 * H
PURGE = 72 * H
LEDGER = "/home/ubuntu/ledger/cand_dev_x1.parquet"
KEEP9_PQ = "/home/ubuntu/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet"
GEOM_PQ = "/home/ubuntu/claude_master/1003/geom_live/kds/geom_x1.parquet"
MD5 = {KEEP9_PQ: "1aa3b97490cb68d6ce654051184eae7c", GEOM_PQ: "6903e178f2f27e192701ddb36ba627b8"}
ORIG_PRED = "/home/ubuntu/ledger/pred_s1a2x1.parquet"
ORIG_SHA = "2618fe1a0235d8ed3602f7b4bf37d8ba611e4e6c923854e10184d036065309fe"
OUTD = "/home/ubuntu/claude_master/1004/s1k24/pred"
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global",
        "rk_oi_delta24h"]
GEOM = ["pos24", "pos7d", "dist_high24", "dist_low24", "atr_ratio", "range7d", "rk_pos24", "rk_dist_low24",
        "rk_atr_ratio"]
CUTS16 = ("20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401 20240701 "
          "20241001 20250101 20250401 20250701 20251001").split()


def filehash(p, algo="md5"):
    h = hashlib.new(algo)
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def load_pool(feats, rel):
    D = pd.read_parquet(LEDGER, columns=["ts", "sym", "g1lite"])
    D = D[D.g1lite.notna()].copy()
    assert D.ts.max() < int(pd.Timestamp("2026-01-01").value // 10 ** 6) - TZ, "du lieu 2026 trong ledger"
    D["med"] = D.groupby("ts").g1lite.transform("median")
    D["rel"] = D.g1lite - D.med
    D["rk"] = D.groupby("ts").rel.rank(pct=True, method="first")
    D["lab"] = np.minimum((D.rk * rel).astype(int), rel - 1)
    D["ts_h"] = (D.ts // H) * H
    D = D.drop(columns=["med", "rel", "rk"])
    for p in [KEEP9_PQ] + ([GEOM_PQ] if feats == "keep9geom" else []):
        m = filehash(p)
        assert m == MD5[p], (p, m)
    F = pd.read_parquet(KEEP9_PQ)
    FE = list(KEEP)
    if feats == "keep9geom":
        G = pd.read_parquet(GEOM_PQ, columns=["ts", "sym"] + GEOM)
        assert len(F) == len(G) and (F.ts.to_numpy() == G.ts.to_numpy()).all() and (
            F.sym.to_numpy() == G.sym.to_numpy()).all(), "keep9/geom lech hang"
        F = pd.concat([F, G[GEOM]], axis=1)
        del G
        FE += GEOM
    n0 = len(D)
    D = D.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    assert len(D) == n0
    del F
    log.info("pool %s feats %d cov vol_7d %.4f%s", D.shape, len(FE), D.vol_7d.notna().mean(),
             (" pos24 %.4f" % D.pos24.notna().mean()) if "pos24" in D else "")
    return D, FE


def train(name, topk, rel, seed, feats):
    import xgboost as xgb
    assert xgb.__version__ == "3.2.0", xgb.__version__
    os.makedirs(OUTD, exist_ok=True)
    t0 = time.time()
    D, FE = load_pool(feats, rel)
    cut = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in CUTS16]
    preds, folds = [], []
    for i, c in enumerate(cut):
        lo, hi = c, int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = D[D.ts < c - PURGE].sort_values("ts")
        oos = D[(D.ts >= lo) & (D.ts < hi)].sort_values("ts")
        if len(tr) < 5000 or len(oos) == 0:
            log.info("%s fold %d skip", name, i)
            continue
        assert tr.ts.max() < c, "LEAK"
        tf = time.time()
        m = xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                          colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method="hist",
                          random_state=seed, lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=topk)
        m.fit(tr[FE], tr.lab, qid=pd.factorize(tr.ts, sort=True)[0])
        p = m.predict(oos[FE])
        o = oos[["ts", "sym", "g1lite"]].assign(score=-p)
        o["rk"] = o.groupby("ts").score.rank(method="first")
        e = o[o.rk <= 5].groupby("ts").g1lite.mean() - o.groupby("ts").g1lite.mean()
        gain = m.get_booster().get_score(importance_type="gain")
        folds.append(dict(fold=i, cut=CUTS16[i], n_train=int(len(tr)), n_oos=int(len(oos)), edge5=float(100 * e.mean()),
                          secs=round(time.time() - tf, 1), gain={k: float(v) for k, v in gain.items()}))
        log.info("%s fold %d %s train %d oos %d ticks %d edge5 %+.2f%% %.0fs", name, i, CUTS16[i], len(tr), len(oos),
                 oos.ts.nunique(), 100 * e.mean(), time.time() - tf)
        preds.append(o.drop(columns=["rk"]))
        del tr, oos, m
    P = pd.concat(preds)
    out = f"{OUTD}/pred_{name}.parquet"
    P[["ts", "sym", "score"]].to_parquet(out)
    summ = dict(name=name, topk=topk, rel=rel, seed=seed, feats=feats, FE=FE, xgb=xgb.__version__,
                pandas=pd.__version__, numpy=np.__version__, rows=int(len(P)), secs=round(time.time() - t0, 1),
                md5=filehash(out), sha256=filehash(out, "sha256"), folds=folds)
    json.dump(summ, open(f"{OUTD}/summary_{name}.json", "w"), indent=1)
    log.info("DONE %s rows %d md5 %s %.0fs", name, len(P), summ["md5"], time.time() - t0)


def g0(name):
    """Cong G0: pred NAME (cau hinh mac dinh) vs pred_s1a2x1 goc — trung GIA TRI tuyet doi (thu tu, ts, sym, score bit)."""
    assert filehash(ORIG_PRED, "sha256") == ORIG_SHA, "pred_s1a2x1 goc da doi"
    A = pd.read_parquet(ORIG_PRED)
    B = pd.read_parquet(f"{OUTD}/pred_{name}.parquet")
    res = dict(rows_orig=int(len(A)), rows_new=int(len(B)), cols_orig=list(A.columns), cols_new=list(B.columns),
               sha_new=filehash(f"{OUTD}/pred_{name}.parquet", "sha256"), sha_orig=ORIG_SHA)
    res["byte_identical"] = res["sha_new"] == ORIG_SHA
    ok = len(A) == len(B)
    if ok:
        for c in ("ts", "sym", "score"):
            a, b = A[c].to_numpy(), B[c].to_numpy()
            res["eq_" + c] = bool(a.dtype == b.dtype and np.array_equal(a, b))
            if c == "score" and not res["eq_" + c]:
                res["score_maxabs"] = float(np.nanmax(np.abs(a.astype(np.float64) - b.astype(np.float64))))
            ok = ok and res["eq_" + c]
        res["index_equal"] = bool(A.index.equals(B.index))
    res["ok"] = bool(ok)
    json.dump(res, open(f"{OUTD}/g0_{name}.json", "w"), indent=1)
    log.info("G0 %s %s", "PASS" if ok else "*** FAIL ***", res)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["train", "g0"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--topk", type=int, default=8)
    ap.add_argument("--rel", type=int, default=5, choices=[5, 10])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--feats", default="keep9", choices=["keep9", "keep9geom"])
    a = ap.parse_args()
    if a.cmd == "train":
        train(a.name, a.topk, a.rel, a.seed, a.feats)
    else:
        sys.exit(0 if g0(a.name) else 3)


if __name__ == "__main__":
    main()
