#!/usr/bin/env python3
"""HO2 — stage + upload bundle Kaggle `sim-ho26a-bundle` (phuong an A: bins 2026 tu net015 GOC ONNX). Tai dung
ho1_stage_bundle.bundle() qua cay symlink (market.bin, pred s42 cua HO1 giu nguyen; funding.bin + bins 2026 moi).
Usage: python3 ho2_stage_bundle.py stage <code_sha> | upload"""
import json
import logging
import os
import sys
import time

R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R)
sys.path.insert(0, R + "/research/analysis")
import ho1_stage_bundle as S  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho2stg")
W = "/home/ubuntu/claude_master/1009/ho26"
H1 = "/home/ubuntu/claude_master/1003/ho1"
ROOT = W + "/stage_root"
NAME = "sim-ho26a-bundle"
OUT = W + "/kaggle/" + NAME


def sl(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.lexists(dst):
        os.remove(dst)
    os.symlink(src, dst)


def stage(code_sha):
    sl(W + "/bins2026Ax", ROOT + "/bins2026x")
    sl(H1 + "/ds/market.bin", ROOT + "/ds/market.bin")
    sl(W + "/ds/funding.bin", ROOT + "/ds/funding.bin")
    sl(W + "/ds/funding.bin.json", ROOT + "/ds/funding.bin.json")
    sl(H1 + "/gate/pred_s42/pred.bin", ROOT + "/gate/pred_s42/pred.bin")
    S.H, S.OUT = ROOT, OUT
    allm = S.bundle(code_sha)
    json.dump({"title": NAME, "id": S.USER + "/" + NAME, "licenses": [{"name": "CC0-1.0"}]},
              open(OUT + "/dataset-metadata.json", "w"))
    man = dict(bundle=allm, preds={str(k): v for k, v in json.load(open(H1 + "/kaggle/stage_manifest.json"))["preds"].items()},
               bundle_name=NAME)
    assert man["preds"]["42"] == allm["pred.bin"]["md5"]
    json.dump(man, open(W + "/kaggle/stage_manifest.json", "w"), indent=1)
    log.info("STAGED %s: %s", NAME, {k: v["md5"] for k, v in allm.items() if not k.startswith("predict_wf_20")})


def upload():
    import gate_ablation_driver as GA
    ks = GA.ks_mod()
    t0 = time.time()
    r = ks._api().dataset_create_new(OUT, public=False, quiet=True, dir_mode="skip")
    log.info("UPLOAD %s -> %s (%.0fs)", NAME, getattr(r, "url", r), time.time() - t0)
    st = "?"
    for _ in range(240):
        try:
            st = str(ks._api().dataset_status(ks.USER + "/" + NAME)).lower()
        except Exception as e:  # noqa: BLE001
            st = "err:%s" % e
        if st == "ready":
            break
        time.sleep(30)
    log.info("DATASET %s status %s", NAME, st)


if __name__ == "__main__":
    if sys.argv[1] == "stage":
        stage(sys.argv[2])
    else:
        upload()
