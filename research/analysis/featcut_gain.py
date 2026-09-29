#!/usr/bin/env python3
"""FEAT_CUT_RVOL15M — gain top-10 cua M_base (deploy45 / A45, 45 cot) vs M_cut (A44, 44 cot bo rvol15m).

Pre-reg: docs/prereg/PREREG_FEAT_CUT_RVOL15M.md (md5 445c4528...). THUAN offline: tai model_f*_4h.json cua
kernel `chuyendinh/g015p2-arm44-gpu` (tai chon loc, ghi vao thu muc MOI /home/ubuntu/featcut/models), doc importance
bang xgboost.Booster.get_score. KHONG train, KHONG sim, KHONG 2026.
deploy45 = 18 model goc /home/ubuntu/claudedata/predwf_G015/model_f{0..17}; CHI dung f0..f15 (16 cutoff DEV
20220101..20251001); f16/f17 (cutoff 2026) KHONG doc.
Importance: 'gain' (gain TRUNG BINH moi split — chinh la con so 34,09% cua EVAL_SELECTOR_FEATURES/DIAG_RVOL15M) [CHINH]
va 'total_gain' (tong gain) [doi chieu]. Share moi fold = imp / sum(imp); trung binh khong trong so qua 16 fold.
Usage: python3 featcut_gain.py [--out OUT.json]
"""
import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
import xgboost as xgb
from kaggle.api.kaggle_api_extended import KaggleApi

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("featcut_gain")
ROOT = "/home/ubuntu/featcut/models"
FS = "/home/ubuntu/src/BinanceFuturesJava/research/pipeline/featuresets/fs_v0_45.json"
DEPLOY = "/home/ubuntu/claudedata/predwf_G015/model_f%d_4h.json"
CUTS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701", "20231001",
        "20240101", "20240401", "20240701", "20241001", "20250101", "20250401", "20250701", "20251001"]
DROP = 36
TYPES = ("gain", "total_gain")


def download():
    api = KaggleApi()
    api.authenticate()
    r = api.kernel_output_with_http_info("chuyendinh", "g015p2-arm44-gpu")[0]
    jobs = []
    for f in r["files"]:
        n = f["fileName"]
        if n.startswith("stage2/A4") and "/model_f" in n:
            jobs.append((f["url"], os.path.join(ROOT, n)))
    LOG.info("model files: %d", len(jobs))

    def get(j):
        url, dest = j
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            return dest, os.path.getsize(dest)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        rr = requests.get(url, timeout=600)
        rr.raise_for_status()
        with open(dest + ".part", "wb") as fh:
            fh.write(rr.content)
        os.replace(dest + ".part", dest)
        return dest, len(rr.content)

    tot = 0
    with ThreadPoolExecutor(max_workers=4) as ex:
        for dest, nb in ex.map(get, jobs):
            tot += nb
    LOG.info("downloaded %.1f MB", tot / 1e6)


def shares(path, nf, typ):
    b = xgb.Booster()
    b.load_model(path)
    sc = b.get_score(importance_type=typ)
    v = np.zeros(nf)
    for k, g in sc.items():
        assert k.startswith("f"), k
        v[int(k[1:])] = g
    return v / v.sum(), b.num_features()


def run_type(typ, names, keep):
    res = {"deploy45": np.zeros((16, 45)), "A45": np.zeros((16, 45)), "A44": np.zeros((16, 45))}
    for fi in range(16):
        s, nfe = shares(DEPLOY % fi, 45, typ)
        assert nfe == 45
        res["deploy45"][fi] = s
    for arm, nf in (("A45", 45), ("A44", 44)):
        for fi in range(16):
            p = "%s/stage2/%s/model_f%d_4h.json" % (ROOT, arm, fi + 3)
            s, nfe = shares(p, nf, typ)
            assert nfe == nf, (arm, fi, nfe)
            if arm == "A45":
                res[arm][fi] = s
            else:
                res[arm][fi, keep] = s
    out = {}
    for arm in ("deploy45", "A45", "A44"):
        m = res[arm].mean(axis=0)
        order = np.argsort(-m)
        out[arm] = {"top10": [{"feature": names[i], "idx": int(i), "share": float(m[i])} for i in order[:10]],
                    "rvol15m_share": float(m[DROP]),
                    "by_fold_rvol15m": [float(x) for x in res[arm][:, DROP]]}
    m45, m44 = res["A45"].mean(axis=0), res["A44"].mean(axis=0)
    dsh = m44 - m45
    order = np.argsort(-dsh)
    out["absorb"] = {
        "note": "share A44 - share A45 (A44 chia lai 100% cho 44 cot). Cot tang nhieu nhat = hap thu rvol15m.",
        "top_gainers": [{"feature": names[i], "share_A45": float(m45[i]), "share_A44": float(m44[i]),
                         "delta": float(dsh[i]),
                         "delta_vs_proportional": float(m44[i] - m45[i] / (1 - m45[DROP]))} for i in order[:10]],
        "rvol15m_share_A45": float(m45[DROP])}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/home/ubuntu/featcut/gain_top10.json")
    a = ap.parse_args()
    t0 = time.time()
    download()
    names = [f["name"] for f in json.load(open(FS))["features"]]
    assert len(names) == 45 and names[DROP] == "rvol15m", names[DROP]
    keep = [i for i in range(45) if i != DROP]
    out = {"pre_reg": "docs/prereg/PREREG_FEAT_CUT_RVOL15M.md", "folds": 16, "primary": "gain"}
    for typ in TYPES:
        o = run_type(typ, names, keep)
        out[typ] = o
        for arm in ("deploy45", "A45", "A44"):
            LOG.info("[%s] %s top10: %s", typ, arm,
                     ", ".join("%s %.2f%%" % (t["feature"], 100 * t["share"]) for t in o[arm]["top10"]))
        LOG.info("[%s] rvol15m share deploy45 %.2f%% | A45 %.2f%%", typ, 100 * o["deploy45"]["rvol15m_share"],
                 100 * o["A45"]["rvol15m_share"])
        LOG.info("[%s] absorb (A44-A45): %s", typ, ", ".join(
            "%s %+.2fpp" % (t["feature"], 100 * t["delta"]) for t in o["absorb"]["top_gainers"]))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    LOG.info("done %.0fs -> %s", time.time() - t0, a.out)


if __name__ == "__main__":
    sys.exit(main())
