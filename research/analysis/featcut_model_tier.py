#!/usr/bin/env python3
"""FEAT_CUT_RVOL15M — TANG MODEL: rank-IC WFO moi fold, M_cut(A44, 44 cot) vs M_base (45 cot), ghep cap.

Pre-reg: docs/prereg/PREREG_FEAT_CUT_RVOL15M.md (md5 445c4528ea322d38476f7a48f9bcb35d).
TAI DUNG artifact A44 (KHONG retrain): per-tick ruler parquet cua vong ARM44 (thuoc do selector: Spearman cross-section
p0 vs retEnd_4h, tick >= 2 coin, THR 0.015, 16 fold OOS 2022-2025, KHONG 2026). Doc lai + tinh CI moi tai day.
  M_base  = 45deploy (predwf_G015x26, chinh la bins ma B0 = G2+FLAT3 dang dung)  [CHINH]
  A45     = retrain 45 cot cung kernel/seed (doi chung nhieu retrain)             [chan doan]
  M_cut   = A44 (45 - rvol15m, retrain cung recipe)
CI: PAIRED block-72h (khoi chung theo ts), 2000 rep, seed 20260905, CI95 percentile. k=1 => inflate 1.0.
DINH HUONG (quan trong): rank-IC cua p0 ÂM o ca 16 fold cho ca 3 model (cau truc) => chat luong q = -IC (lon = tot).
  Delta chat luong dq = q_cut - q_base = -(IC_cut - IC_base). lift@8 (top-8 win-rate lift) khong phu thuoc dau => doi chung.
Usage: python3 featcut_model_tier.py [--out OUT.json]
"""
import argparse
import json
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("featcut_tier")
D = "/home/ubuntu/kaggle_sim/out/a44out/"
SRC = {"base45": "45deploy_perfold_ticks.parquet", "A45": "A45_perfold_ticks.parquet", "A44": "A44_perfold_ticks.parquet"}
NREP, SEED = 2000, 20260905
BLK = 72 * 3600 * 1000


def load():
    dfs = {}
    for k, fn in SRC.items():
        d = pd.read_parquet(D + fn).sort_values("ts").reset_index(drop=True)
        dfs[k] = d
    ref = dfs["base45"]
    for k, d in dfs.items():
        assert len(d) == len(ref) and (d["ts"].to_numpy() == ref["ts"].to_numpy()).all(), k
        assert (d["fold"].to_numpy() == ref["fold"].to_numpy()).all(), k
    return dfs


def boot(delta, blk, nrep=NREP, seed=SEED):
    """delta: vector (n_tick); blk: block id (n_tick). Tra ve (mean, lo, hi) cua trung binh theo tick, resample khoi."""
    ub, inv = np.unique(blk, return_inverse=True)
    nb = len(ub)
    s = np.bincount(inv, weights=delta, minlength=nb)
    c = np.bincount(inv, minlength=nb).astype(float)
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, nb, size=(nrep, nb))
    m = s[pick].sum(axis=1) / c[pick].sum(axis=1)
    return float(delta.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def verdict(lo, hi):
    if hi < 0:
        return "KEM ro (CI < 0)"
    if lo > 0:
        return "TOT hon ro (CI > 0)"
    return "KHONG khac biet (CI chua 0)"


def compare(dfs, a, b, mask=None):
    """cut=a, base=b. Tra ve dict cho IC (dinh huong q=-IC) va lift8."""
    da, db = dfs[a], dfs[b]
    m = np.ones(len(da), bool) if mask is None else mask
    blk = (da["ts"].to_numpy()[m] // BLK).astype(np.int64)
    dq = -(da["ic"].to_numpy()[m] - db["ic"].to_numpy()[m])
    dl = da["lift8"].to_numpy()[m] - db["lift8"].to_numpy()[m]
    r = {}
    for nm, v in (("d_quality_negIC", dq), ("d_lift8", dl)):
        mu, lo, hi = boot(v, blk)
        r[nm] = {"mean": mu, "lo": lo, "hi": hi, "verdict": verdict(lo, hi)}
    r["d_rawIC_literal"] = {"mean": -r["d_quality_negIC"]["mean"], "lo": -r["d_quality_negIC"]["hi"],
                            "hi": -r["d_quality_negIC"]["lo"]}
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/home/ubuntu/featcut/model_tier.json")
    a = ap.parse_args()
    dfs = load()
    ref = dfs["base45"]
    folds = sorted(ref["fold"].unique())
    assert len(folds) == 16, folds
    out = {"pre_reg": "docs/prereg/PREREG_FEAT_CUT_RVOL15M.md", "n_tick": int(len(ref)), "nrep": NREP, "seed": SEED,
           "block_h": 72, "k": 1, "inflate": 1.0}
    # dinh huong: IC am o moi fold moi model
    neg = {k: bool(all(d.groupby("fold")["ic"].mean() < 0)) for k, d in dfs.items()}
    out["ic_negative_all_folds"] = neg
    LOG.info("IC am o ca 16 fold: %s", neg)
    out["mean"] = {k: {"ic": float(d["ic"].mean()), "lift8": float(d["lift8"].mean())} for k, d in dfs.items()}
    out["overall"] = {
        "A44_vs_base45 [CHINH]": compare(dfs, "A44", "base45"),
        "A44_vs_A45 [chan doan cung phien]": compare(dfs, "A44", "A45"),
        "A45_vs_base45 [nen nhieu retrain]": compare(dfs, "A45", "base45"),
    }
    per = []
    for f in folds:
        m = (ref["fold"] == f).to_numpy()
        row = {"fold": f, "n_tick": int(m.sum())}
        for k in dfs:
            row["ic_" + k] = float(dfs[k]["ic"].to_numpy()[m].mean())
            row["lift8_" + k] = float(dfs[k]["lift8"].to_numpy()[m].mean())
        c = compare(dfs, "A44", "base45", m)
        row["dq_A44_vs_base45"] = c["d_quality_negIC"]
        row["dlift8_A44_vs_base45"] = c["d_lift8"]
        per.append(row)
    out["per_fold"] = per
    out["folds_A44_worse_q"] = int(sum(1 for r in per if r["dq_A44_vs_base45"]["mean"] < 0))
    out["folds_A44_worse_lift8"] = int(sum(1 for r in per if r["dlift8_A44_vs_base45"]["mean"] < 0))
    o = out["overall"]["A44_vs_base45 [CHINH]"]
    q, lf = o["d_quality_negIC"], o["d_lift8"]
    if q["verdict"].startswith("KEM"):
        gate = "STOP (KEM ro): CI dq < 0 => rvol15m can thiet o tang model; KHONG sim"
    elif q["verdict"].startswith("TOT"):
        gate = "SIM + P3 (TOT hon ro)"
    else:
        gate = "SIM (khong kem co y nghia)"
    out["gate"] = {"rule": "pre-reg: dq = -(IC_cut-IC_base); CI dq<0 => STOP; CI chua 0 => sim; CI>0 => sim+P3",
                   "decision": gate, "lift8_agrees": lf["verdict"]}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    LOG.info("mean IC/lift8: %s", json.dumps(out["mean"]))
    for k, v in out["overall"].items():
        LOG.info("%s | dq %+.6f [%+.6f,%+.6f] %s | dlift8 %+.6f [%+.6f,%+.6f] %s", k,
                 v["d_quality_negIC"]["mean"], v["d_quality_negIC"]["lo"], v["d_quality_negIC"]["hi"],
                 v["d_quality_negIC"]["verdict"], v["d_lift8"]["mean"], v["d_lift8"]["lo"], v["d_lift8"]["hi"],
                 v["d_lift8"]["verdict"])
    for r in per:
        LOG.info("fold %s n=%d IC base/A45/A44 %+.4f/%+.4f/%+.4f | dq %+.4f [%+.4f,%+.4f] | dlift8 %+.4f", r["fold"],
                 r["n_tick"], r["ic_base45"], r["ic_A45"], r["ic_A44"], r["dq_A44_vs_base45"]["mean"],
                 r["dq_A44_vs_base45"]["lo"], r["dq_A44_vs_base45"]["hi"], r["dlift8_A44_vs_base45"]["mean"])
    LOG.info("folds A44 worse: q %d/16, lift8 %d/16", out["folds_A44_worse_q"], out["folds_A44_worse_lift8"])
    LOG.info("GATE: %s", gate)


if __name__ == "__main__":
    sys.exit(main())
