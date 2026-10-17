#!/usr/bin/env python3
"""GATE_VZ retrain (PREREG_GATE_VZ.md ee97237b muc 4-5). Recipe = gate_ablation_driver.retrain, them cot VZ.
Usage: python3 gvz_train.py g0 | checks | train VA|VB SEED [SEED..]
Out: ~/claude_master/gvz/pred_<ARM>_S<seed>/{pred.bin,meta.json,retrain.json}
"""
import json
import logging
import os
import shutil
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gvzt")
D = "/home/ubuntu/claude_master/gvz"
GA.STORE = D + "/store/gate_dataset_full.csv"
FEAT = D + "/feat/vz_feat.parquet"
VZA = ["vzTkr5", "vzTkr15", "vzTkr60", "vzTkr240", "vzTkrBtc15", "vzTkrMed15", "vzQvR60", "vzNtR15"]
VZB = ["vzOiC1h", "vzOiC4h", "vzOiC24h", "vzLsTop", "vzLsAcc"]
ARMF = {"B": GA.V3FULL, "VA": GA.V3FULL + VZA, "VB": GA.V3FULL + VZA + VZB}
G0_REF = "/home/ubuntu/claude_master/1004/gabl/p15_G0.npy"


def disk():
    mb = shutil.disk_usage("/home/ubuntu").free // (1 << 20)
    assert mb > 500, "DIA < 500MB"
    return mb


def load(arm):
    df = GA.load_store(GA.V3FULL + ["label_oldbasket"])
    if arm != "B":
        vz = pd.read_parquet(FEAT)
        assert vz["timestamp"].is_unique
        cols = [c for c in ARMF[arm] if c.startswith("vz")]
        v = vz.set_index("timestamp")[cols].reindex(df["timestamp"].to_numpy())
        for c in cols:
            df[c] = v[c].to_numpy(np.float32)
    return df


def train(arm, seed, save_model_gain=True):
    from xgboost import XGBRegressor
    from scipy.stats import pearsonr, spearmanr
    disk()
    feats = ARMF[arm]
    df = load(arm)
    sts = df["timestamp"].to_numpy()
    raw, a = GA.read_pred()
    assert GA.md5f(GA.PRED0) == GA.PRED0_MD5
    pts = a["ts"].astype(np.int64)
    p0 = a["p15"].astype(np.float32)
    out = p0.copy()
    jj = GA.align(sts, pts)
    X = df[feats].to_numpy(np.float32)
    y = df["label_oldbasket"].to_numpy(np.float32)
    folds = []
    for i, cut in enumerate(GA.FOLD_CUTS):
        tr_cut = pd.Timestamp(cut).value // 10**6 - 15 * 60_000
        m = (sts < tr_cut) & np.isfinite(y)
        assert sts[m].max() < tr_cut
        model = XGBRegressor(objective="reg:squarederror", max_depth=4, n_estimators=150, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, min_child_weight=10, random_state=seed, n_jobs=4)
        model.fit(X[m], y[m])
        lo, hi = GA.fold_bounds(i)
        pi = np.where((pts >= lo) & (pts < hi))[0]
        si = jj[pi]
        ok = si >= 0
        out[pi[ok]] = model.predict(X[si[ok]]).astype(np.float32)
        q, r = out[pi], p0[pi]
        g = model.get_booster().get_score(importance_type="total_gain")
        tot = sum(g.values()) or 1.0
        assert all(str(k).startswith("f") and str(k)[1:].isdigit() for k in g), list(g)[:3]
        vzg = sum(v for k, v in g.items() if feats[int(k[1:])].startswith("vz")) / tot
        f = dict(fold=i, cutoff=cut, n_train=int(m.sum()), n_oos=int(len(pi)), miss=int((~ok).sum()),
                 pearson_vs_pred0=float(pearsonr(q, r)[0]), spearman_vs_pred0=float(spearmanr(q, r).correlation),
                 vz_gain_share=float(vzg), p50=float(np.median(q)))
        folds.append(f)
        log.info("%s S%d fold %2d %s ntr=%d noos=%d miss=%d r=%.4f vzgain=%.3f", arm, seed, i, cut, f["n_train"],
                 f["n_oos"], f["miss"], f["pearson_vs_pred0"], vzg)
    od = D + "/pred_%s_S%d" % (arm, seed)
    os.makedirs(od, exist_ok=True)
    b = a.copy()
    b["p15"] = out.astype(">f4")
    assert np.isfinite(out).all()
    with open(od + "/pred.bin", "wb") as fh:
        fh.write(raw[:4])
        fh.write(b.tobytes())
    md5 = GA.md5f(od + "/pred.bin")
    np.save(od + "/p15.npy", out)
    meta = dict(arm=arm, seed=seed, md5=md5, n=int(len(b)), feats=feats, prereg="ee97237b")
    json.dump(meta, open(od + "/meta.json", "w"), indent=1)
    json.dump(dict(meta, folds=folds), open(od + "/retrain.json", "w"), indent=1)
    log.info("PRED %s S%d md5=%s min r=%.4f mean vzgain=%.3f", arm, seed, md5,
             min(f["pearson_vs_pred0"] for f in folds), float(np.mean([f["vz_gain_share"] for f in folds])))
    return out, folds


def g0():
    out, folds = train("B", 42)
    ref = np.load(G0_REF)
    d = np.abs(out.astype(np.float64) - ref.astype(np.float64))
    res = dict(min_pearson_vs_pred0=min(f["pearson_vs_pred0"] for f in folds), max_abs_vs_gabl_G0=float(d.max()),
               n_diff_gt_1e6=int((d > 1e-6).sum()))
    res["D1_pass_pearson"] = res["min_pearson_vs_pred0"] >= 0.99
    res["D1_bit_identical"] = res["max_abs_vs_gabl_G0"] <= 1e-6
    json.dump(res, open(D + "/d1.json", "w"), indent=1)
    log.info("D1 %s", res)


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "g0":
        g0()
    elif c == "train":
        for s in sys.argv[3:]:
            train(sys.argv[2], int(s))
