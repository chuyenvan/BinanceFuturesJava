#!/usr/bin/env python3
"""ARM44_SIM — day 3 kernel SIM cua vong ARM44 len Kaggle (moc | A45 | A44).

Tai dung NGUYEN template cua vong Stage 3 (`research/analysis/s3_kernel.py`): moi kenh = 1 kernel doc lap
tu lam het (bins -> funding.bin -> dataset -> sim KEEPLEG0 -> MTM moc phut -> xoa file lon).

Khac Stage 3 DUNG 3 diem (ghi ro, xem docs/prereg/PREREG_ARM44.md §1):
  (1) ten kernel `sim-a44-<moc|a45|a44>` (khong ghi de artifact vong Stage 3);
  (2) them `CONC_CAP_PERCOIN_ENABLED=true` + `CONC_CAP_PERCOIN_PCT=0.15` => cau hinh = dung
      `profiles/t170_flat_keepleg0.properties` (KEEPLEG0); cap la NO-OP da do (RESULT_GATESCALE_KEEPLEG0 §4);
  (3) kernel_sources = kernel train `g015p2-arm44-gpu` (chua `stage2/A45` + `stage2/A44` bins) — mount cho
      CA BA kenh de ha tang giong nhau tuyet doi; kenh `moc` van lay bins tu bundle (nhanh `ARM=="moc"`).

API cho agent khac:
    from research.analysis import arm44_sim as K
    K.submit("A44"); K.wait(["chuyendinh/sim-a44-a44"]); K.fetch("A44")
"""
from __future__ import annotations

import base64
import json
import logging
import os
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from research.analysis import s3_kernel as S3  # noqa: E402
from tools import kaggle_sim as ks  # noqa: E402

LOG = logging.getLogger(__name__)

ARMS = ("moc", "A45", "A44")
SLUG = "sim-a44"
TRAIN_KERNEL = "chuyendinh/g015p2-arm44-gpu"
WORKDIR = "/home/ubuntu/kaggle_sim"
OUTDIR = "/home/ubuntu/kaggle_sim/out"
CONC = {"CONC_CAP_PERCOIN_ENABLED": "true", "CONC_CAP_PERCOIN_PCT": "0.15"}


def _ref(arm):
    return "%s/%s-%s" % (ks.USER, SLUG, arm.lower())


def _cfg(arm):
    c = S3._cfg(arm)
    c["overrides"] = dict(c["overrides"], **CONC)
    return c


def submit(arm, push=True):
    assert arm in ARMS, arm
    ref = _ref(arm)
    folder = os.path.join(WORKDIR, "%s-%s" % (SLUG, arm.lower()))
    os.makedirs(folder, exist_ok=True)
    for src, nm in S3._helpers().items():
        with open(src) as f:
            body = f.read()
        with open(os.path.join(folder, nm), "w") as f:
            f.write(body)
    code = (S3.KERNEL_TEMPLATE.replace("__CFG_JSON__", repr(json.dumps(_cfg(arm))))
            .replace("__HELPERS__", repr(json.dumps(S3._helpers_b64()))))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py",
            "language": "python", "kernel_type": "script", "is_private": True,
            "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + S3.BUNDLE, ks.USER + "/" + S3.SC_DS,
                                ks.USER + "/" + S3.MOC21_DS] + ks.TICKER_DS,
            "competition_sources": [], "kernel_sources": [TRAIN_KERNEL]}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = ks._api().kernels_push(folder)
        LOG.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


def wait(refs, poll_s=60, timeout_s=6 * 3600):
    return ks.wait(refs, poll_s=poll_s, timeout_s=timeout_s)


def fetch(arm, out_dir=None):
    dest = out_dir or os.path.join(OUTDIR, "%s-%s" % (SLUG, arm.lower()))
    os.makedirs(dest, exist_ok=True)
    ks._api().kernels_output(_ref(arm), path=dest, force=True, quiet=True)
    hits = S3.glob_free(dest, "result.json")
    return {"ref": _ref(arm), "dir": dest, "result": json.load(open(hits[0])) if hits else None}


def submit_mtm(push=True, md5_want=None):
    ref = "%s/%s-mtm" % (ks.USER, SLUG)
    folder = os.path.join(WORKDIR, "%s-mtm" % SLUG)
    os.makedirs(folder, exist_ok=True)
    hb, hf = {}, {}
    for src, nm in ((os.path.join("/home/ubuntu/src/BinanceFuturesJava/research/analysis/s3_intraday.py"),
                     "s3_intraday.py"),
                    (os.path.join("/home/ubuntu/src/BinanceFuturesJava/research/analysis/jbin.py"),
                     "jbin.py")):
        with open(src, "rb") as f:
            hb[nm] = base64.b64encode(f.read()).decode()
        with open(src) as f:
            hf[nm] = f.read()
        with open(os.path.join(folder, nm), "w") as f:
            f.write(hf[nm])
    cfg = {"arms": list(ARMS), "slug": SLUG, "workers": 4,
           "md5_want": md5_want or {"moc": S3.KEEP_MD5}}
    code = (S3.MTM_TEMPLATE.replace("__CFG_JSON__", repr(json.dumps(cfg)))
            .replace("__HELPERS__", repr(json.dumps(hb))))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False,
            "enable_internet": True, "dataset_sources": list(ks.TICKER_DS),
            "competition_sources": [],
            "kernel_sources": [_ref(a) for a in ARMS]}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = ks._api().kernels_push(folder)
        LOG.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


def _cli():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "wait", "fetch", "all", "mtm"])
    ap.add_argument("--arm", action="append", default=None)
    a = ap.parse_args()
    arms = a.arm or list(ARMS)
    if a.cmd == "submit":
        for x in arms:
            submit(x)
    elif a.cmd == "mtm":
        LOG.info("%s", wait([submit_mtm()]))
    elif a.cmd == "wait":
        LOG.info("%s", wait([_ref(x) for x in arms]))
    elif a.cmd == "fetch":
        for x in arms:
            LOG.info("%s", json.dumps(fetch(x), indent=1))
    else:
        LOG.info("%s", wait([submit(x) for x in arms]))
        for x in arms:
            LOG.info("%s", json.dumps(fetch(x)["result"], indent=1))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _cli()
