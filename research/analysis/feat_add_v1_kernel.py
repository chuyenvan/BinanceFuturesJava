#!/usr/bin/env python3
"""FEAT_ADD_V1 kernel — sim 2 arm (B0 control / V1) tren nen G2+FLAT3 len Kaggle.

Pre-reg: docs/prereg/PREREG_FEAT_ADD_V1.md (md5 9ce3d65868c053ceaa564c184e6245ff, chot TRUOC).
Tai dung DUONG DA QUA CONG cua Stage 3 (s3_kernel.KERNEL_TEMPLATE: build_map s1a2x1 tu bins arm +
2 fold 2021 cua MOC -> dung lai funding.bin byte-faithful -> sim), chi doi 4 thu:
  1. jar  = dataset sim-jar-gdv2 (sha 7368be46...), profile r4_kg0_k16_f015_g155 + G2 + FLAT3 (overrides)
  2. cong parity cua arm "moc" (= B0 control qua duong REBUILD funding) = md5 650c386f, n 2517, eq 131908
  3. bo buoc MTM phut trong kernel (cham MTM tren Oracle bang reset_rule_score.run_mtm)
  4. ten kernel rieng: sim-featv1-b0 / sim-featv1-v1 (khong ghi de kenh S3)
KHONG Java/sim tren Oracle. Chi Kaggle CPU.

Usage: python3 feat_add_v1_kernel.py submit|wait|fetch|all
"""
from __future__ import annotations

import gzip
import json
import logging
import os
import shutil
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import kaggle_sim as ks  # noqa: E402
import s3_kernel as K  # noqa: E402

LOG = logging.getLogger("featv1")

JAR_DS = "sim-jar-gdv2"
JAR_SHA_WANT = "7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a"
PROFILE = "r4_kg0_k16_f015_g155"
OVERRIDES = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90,
             "SIM_GATE_ROLLING_PCT": 0.999950829,
             "TS_GIVEBACK_RATIO": 1.0, "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03}
B0_MD5, B0_N, B0_EQ = "650c386f0d0dfea334af9d55ca2f21d4", 2517, 131908
# dinh cua S3 V1 (KEEPLEG0): cung bins V1 + cung map + 2 fold 2021 cua MOC => bins/funding phai TRUNG
S3_V1_BINS_SHA_PREFIX, S3_V1_FUND_MD5_PREFIX = "7b4cc34a", "d5acde84"
ARMS = {"b0": "moc", "v1": "V1"}          # tag -> arm noi bo cua template
SC_DS, MOC21_DS, BUNDLE = K.SC_DS, K.MOC21_DS, K.BUNDLE


def _patch(t, old, new, count=1):
    assert t.count(old) == count, ("patch anchor count", t.count(old), old[:80])
    return t.replace(old, new)


def build_template():
    t = K.KERNEL_TEMPLATE
    # 1. jar tu jar_ds + profile theo glob sorted (giong tools/kaggle_sim.py: f1 = sorted(glob)[0])
    t = _patch(t, 'jar = os.path.join(bundle, "sim.jar")\nJAR_SHA = sha256f(jar)\n'
                  'prof_base = os.path.join(bundle, "prof_" + CFG["profile"] + ".properties")\n',
               '_jc = [c for c in find_glob("sim.jar") if ("/" + CFG["jar_ds"] + "/") in c.replace("\\\\", "/")]\n'
               'if not _jc:\n'
               '    LOG.error("MISSING sim.jar cho jar_ds=%r", CFG["jar_ds"])\n'
               '    sys.exit(1)\n'
               'jar = _jc[0]\n'
               'JAR_SHA = sha256f(jar)\n'
               '_pc = find_glob("prof_" + CFG["profile"] + ".properties")\n'
               'if not _pc:\n'
               '    LOG.error("MISSING profile %s", CFG["profile"])\n'
               '    sys.exit(1)\n'
               'prof_base = _pc[0]\n'
               'LOG.info("jar=%s sha=%s prof_base=%s", jar, JAR_SHA, prof_base)\n')
    # 2. cong parity B0 (arm moc) theo mac G2+FLAT3
    t = _patch(t, 'res["checks"]["P1_n"] = n_trades == 1085', 'res["checks"]["P1_n"] = n_trades == CFG["b0_n"]')
    t = _patch(t, 'res["checks"]["P1_eq"] = (last is not None and last[1] == 103083)',
               'res["checks"]["P1_eq"] = (last is not None and last[1] == CFG["b0_eq"])')
    t = _patch(t, 'res["checks"]["jar_sha"] = JAR_SHA == CFG["jar_sha_want"]\n',
               'res["checks"]["jar_sha"] = JAR_SHA == CFG["jar_sha_want"]\n'
               'if ARM == "V1":\n'
               '    res["checks"]["s3v1_bins_sha"] = BINS_SHA.startswith(CFG["s3v1_bins_pref"])\n'
               '    res["checks"]["s3v1_fund_md5"] = F["md5_funding"].startswith(CFG["s3v1_fund_pref"])\n')
    # 3. bo MTM phut trong kernel
    a = t.index("# ---------------- 5. MTM MOC PHUT ----------------")
    b = t.index('with open(WORK + "/result.json", "w") as f:')
    t = t[:a] + "# (MTM phut cham tren Oracle — bo trong kernel)\n" + t[b:]
    return t


def _cfg(tag):
    c = K._cfg(ARMS[tag])
    c.update(profile=PROFILE, overrides=dict(OVERRIDES), jar_ds=JAR_DS, jar_sha_want=JAR_SHA_WANT,
             keep_md5=B0_MD5, b0_n=B0_N, b0_eq=B0_EQ,
             s3v1_bins_pref=S3_V1_BINS_SHA_PREFIX, s3v1_fund_pref=S3_V1_FUND_MD5_PREFIX)
    return c


def submit(tag, push=True):
    ref = ks.kernel_ref("featv1-" + tag)
    folder = os.path.join(K.WORKDIR, "featv1-" + tag)
    os.makedirs(folder, exist_ok=True)
    for src, nm in K._helpers().items():
        shutil.copy(src, os.path.join(folder, nm))
    code = (build_template().replace("__CFG_JSON__", repr(json.dumps(_cfg(tag))))
            .replace("__HELPERS__", repr(json.dumps(K._helpers_b64()))))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + BUNDLE, ks.USER + "/" + SC_DS, ks.USER + "/" + MOC21_DS,
                                ks.USER + "/" + JAR_DS] + ks.TICKER_DS,
            "competition_sources": [],
            "kernel_sources": [K.STAGE2_KERNEL] if tag == "v1" else []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = ks._api().kernels_push(folder)
        LOG.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


def fetch(tag):
    """Keo output ve out/featv1-<tag>/ va dung layout storage/ + logs/sim.out cho reset_rule_score."""
    dest = os.path.join(K.OUTDIR, "featv1-" + tag)
    os.makedirs(dest, exist_ok=True)
    ks._api().kernels_output(ks.kernel_ref("featv1-" + tag), path=dest, force=True, quiet=True)
    arm = ARMS[tag]
    run = os.path.join(dest, "run_" + arm)
    os.makedirs(os.path.join(dest, "storage"), exist_ok=True)
    os.makedirs(os.path.join(dest, "logs"), exist_ok=True)
    pd_src = os.path.join(run, "storage", "printDone.csv")
    if os.path.exists(pd_src):
        shutil.copy(pd_src, os.path.join(dest, "storage", "printDone.csv"))
    gz = os.path.join(run, "logs", "sim.out.gz")
    if os.path.exists(gz):
        with gzip.open(gz, "rb") as fi, open(os.path.join(dest, "logs", "sim.out"), "wb") as fo:
            shutil.copyfileobj(fi, fo)
    hits = K.glob_free(dest, "result.json")
    res = json.load(open(hits[0])) if hits else None
    return {"ref": ks.kernel_ref("featv1-" + tag), "dir": dest, "result": res}


def _cli():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "wait", "fetch", "all"])
    ap.add_argument("--tag", action="append", default=None)
    a = ap.parse_args()
    tags = a.tag or list(ARMS)
    if a.cmd == "submit":
        for x in tags:
            submit(x)
    elif a.cmd == "wait":
        LOG.info("%s", ks.wait([ks.kernel_ref("featv1-" + x) for x in tags], poll_s=60, timeout_s=6 * 3600))
    elif a.cmd == "fetch":
        for x in tags:
            LOG.info("%s", json.dumps(fetch(x)["result"], indent=1))
    else:
        refs = [submit(x) for x in tags]
        LOG.info("%s", ks.wait(refs, poll_s=60, timeout_s=6 * 3600))
        for x in tags:
            LOG.info("%s", json.dumps(fetch(x)["result"], indent=1))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _cli()
