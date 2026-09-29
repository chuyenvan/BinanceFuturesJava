#!/usr/bin/env python3
"""FEAT_CUT_RVOL15M — gop json (tang model + gain + parity FLAT3) thanh docs/result/RESULT_FEAT_CUT_RVOL15M.json."""
import hashlib
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("featcut_assemble")
FC = "/home/ubuntu/featcut/"
OUT = "/home/ubuntu/src/BinanceFuturesJava/docs/result/RESULT_FEAT_CUT_RVOL15M.json"
KS = "/home/ubuntu/kaggle_sim/out/g2flat3-val/"
WANT = "650c386f0d0dfea334af9d55ca2f21d4"


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def main():
    tier = json.load(open(FC + "model_tier.json"))
    gain = json.load(open(FC + "gain_top10.json"))
    res = json.load(open(KS + "result.json"))
    got = md5f(KS + "storage/printDone.csv")
    pf = tier["per_fold"]
    tier["folds_dq_ci_below0"] = int(sum(1 for r in pf if r["dq_A44_vs_base45"]["hi"] < 0))
    tier["folds_dq_ci_above0"] = int(sum(1 for r in pf if r["dq_A44_vs_base45"]["lo"] > 0))
    out = {
        "prereg": {"file": "docs/prereg/PREREG_FEAT_CUT_RVOL15M.md", "md5": "445c4528ea322d38476f7a48f9bcb35d",
                   "commit": "76d9ba06"},
        "step0_flat3_parity": {"profile": "profiles/g2_flat3.properties", "want_md5": WANT, "got_md5": got,
                               "pass": got == WANT, "n_trades": res.get("n_trades"),
                               "equity_final": res.get("equity_final"), "jar_sha256": res.get("jar_sha256"),
                               "kernel": "chuyendinh/sim-g2flat3-val", "ok": res.get("ok")},
        "model_tier": tier, "gain": gain,
        "sim": {"run": False, "reason": "gate tang model: KEM ro (CI dq < 0) => DUNG theo pre-reg"},
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    LOG.info("parity got=%s want=%s pass=%s n=%s eq=%s | folds dq CI<0: %d, >0: %d -> %s", got, WANT, got == WANT,
             res.get("n_trades"), res.get("equity_final"), tier["folds_dq_ci_below0"], tier["folds_dq_ci_above0"], OUT)
    return 0 if got == WANT else 3


if __name__ == "__main__":
    sys.exit(main())
