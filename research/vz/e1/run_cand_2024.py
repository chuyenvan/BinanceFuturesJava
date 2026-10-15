#!/usr/bin/env python3
"""P4/QUEUE_1015 (MASTER 10-15 14:19) — dong goi + chay 1 kernel nam 2024 sinh TAP UNG VIEN.

Jar = ban build branch feat/sim-export-candidates (sha256 68057d25...), key SIM_EXPORT_CANDIDATES.
Jar + profile r4_kg0_k16_f015_g155 -> dataset PRIVATE chuyendinh/sim-jar-cand (mirror sim-jar-nsel).
Kernel: tag vz-cand-2024 = K24 + GATE_QUOTA_SKIP_WHEN_FULL=true, sim_end_date=20241231, jar_ds=sim-jar-cand.
Output kernel: cands.csv (ung vien) -> tai ve -> dataset PRIVATE chuyendinh/vz-cand-2024.

Chi chay 1 kernel. Nam xac nhan (2025) KHONG chay.

Usage: python3 run_cand_2024.py ds | submit | status | fetch
"""
import hashlib
import json
import logging
import os
import shutil
import sys
import time

REPO = "/home/ubuntu/claude_master/cand_wt"
sys.path.insert(0, REPO)
from tools import kaggle_sim as ks  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("cand2024")

JAR_LOCAL = REPO + "/target/binance-java-sdk-1.2.4.jar"
JAR_SHA = "68057d25a96adadef47edf3f452fbda2b038960fa27ad75b31089e4ac97cd2b3"
PROF = "/home/ubuntu/kaggle_sim/jar_gdv2/prof_r4_kg0_k16_f015_g155.properties"
PROF_MD5 = "0e0caef09e47931b706c696d587a5184"
JAR_DS = "sim-jar-cand"
BUNDLE = "sim-x1-2021-bundle"
PROFILE = "r4_kg0_k16_f015_g155"
TAG = "vz-cand-2024"
CAND_FILE = "cands.csv"
DS_DIR = REPO + "/ds_" + JAR_DS
OUT_DS_DIR = "/home/ubuntu/kaggle_sim/out/" + TAG
OUT_DATASET = "vz-cand-2024"

B0OV = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90, "SIM_GATE_ROLLING_PCT": 0.999950829,
        "TS_GIVEBACK_RATIO": 1.0, "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03}
OV = dict(B0OV, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true",
          SIM_EXPORT_CANDIDATES=CAND_FILE)
END = "20241231"
CODE_SHA = "feat/sim-export-candidates@e64da9d6+jarcand-68057d25"
# [MAPAUD 2026-10-11] Oracle Aerospike symbol_mapper co 8 id trung (843..850 = 16 symbol moi tu 2026-07-16).
# Jar module HEAD fail-fast (SymbolIdRules.assertUniqueIds). 16 symbol do KHONG ton tai trong du lieu <=2024
# (docs/audit/MAPPER_AUDIT_20261011.md M1/M2) => WARN an toan cho run nay.
EXTRA_ENV = {"SYMBOL_MAPPER_DUP_POLICY": "WARN"}


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def check_disk(tag=""):
    mb = shutil.disk_usage("/home/ubuntu").free // (1 << 20)
    log.info("DF %s avail=%d MB", tag, mb)
    if mb < 30000:
        log.error("DIA < 30000 MB -> DUNG")
        sys.exit(3)


def make_ds():
    check_disk("truoc make_ds")
    assert sha256f(JAR_LOCAL) == JAR_SHA, "jar sha khong khop"
    assert md5f(PROF) == PROF_MD5, "prof md5 khong khop"
    os.makedirs(DS_DIR, exist_ok=True)
    shutil.copy(JAR_LOCAL, DS_DIR + "/sim.jar")
    shutil.copy(PROF, DS_DIR + "/" + os.path.basename(PROF))
    json.dump({"title": JAR_DS, "id": ks.USER + "/" + JAR_DS, "licenses": [{"name": "CC0-1.0"}]},
              open(DS_DIR + "/dataset-metadata.json", "w"))
    log.info("ds folder ready: %s", os.listdir(DS_DIR))


def create_ds():
    make_ds()
    api = ks._api()
    ref = ks.USER + "/" + JAR_DS
    try:
        st = str(api.dataset_status(ref))
    except Exception:
        st = "missing"
    if st.lower() == "ready":
        r = api.dataset_create_version(DS_DIR, version_notes="P4 cand jar 68057d25", quiet=True)
        log.info("dataset version -> %s", getattr(r, "url", r))
    else:
        r = api.dataset_create_new(DS_DIR, public=False, quiet=True, dir_mode="skip")
        log.info("dataset create -> %s", getattr(r, "url", r))
    for _ in range(80):
        try:
            st = str(api.dataset_status(ref))
        except Exception as e:
            st = "err:%s" % e
        log.info("dataset status %s", st)
        if st.lower() == "ready":
            return


def submit():
    check_disk("truoc submit")
    log.info("free_slots=%d", ks.free_slots())
    ref = ks.submit(TAG, PROFILE, OV, jar_ds=JAR_DS, bundle_ds=BUNDLE, sim_end_date=END,
                    xmx="22g", timeout_s=7200, code_sha=CODE_SHA, extra_env=EXTRA_ENV)
    log.info("PUSHED ref=%s ov=%s extra_env=%s", ref, json.dumps(OV), json.dumps(EXTRA_ENV))
    return ref


def status():
    log.info("%s -> %s", ks.kernel_ref(TAG), ks._status(ks.kernel_ref(TAG)))


def fetch():
    check_disk("truoc fetch")
    o = ks.fetch(TAG)
    log.info("FETCH %s", json.dumps(o, default=str))
    return o


def _find_cands(root):
    import glob
    m = sorted(glob.glob(os.path.join(root, "**", CAND_FILE), recursive=True))
    return m[0] if m else None


TS_2024_LO = 1704067200000   # 2024-01-01 00:00 UTC
TS_2024_HI = 1735689600000   # 2025-01-01 00:00 UTC


def filter2024(src, dst_gz):
    import gzip
    n_all = n_2024 = 0
    with open(src, errors="ignore") as fi, gzip.open(dst_gz, "wt") as fo:
        fo.write(fi.readline())
        for ln in fi:
            if not ln.strip():
                continue
            n_all += 1
            try:
                ts = int(ln.split(",", 1)[0])
            except ValueError:
                continue
            if TS_2024_LO <= ts < TS_2024_HI:
                fo.write(ln)
                n_2024 += 1
    return n_all, n_2024


def upload():
    check_disk("truoc upload")
    src = _find_cands(OUT_DS_DIR)
    assert src, "khong thay %s trong %s" % (CAND_FILE, OUT_DS_DIR)
    os.makedirs(OUT_DS_DIR + "/ds", exist_ok=True)
    dst = OUT_DS_DIR + "/ds/cands_2024.csv.gz"
    n_all, n_2024 = filter2024(src, dst)
    log.info("cands rows all=%d -> 2024=%d -> %s", n_all, n_2024, dst)
    open(OUT_DS_DIR + "/ds/README.md", "w").write(
        "# vz-cand-2024 — tap UNG VIEN cua he (2024, nam kham pha)\n\n"
        "Nguon: kernel chuyendinh/sim-vz-cand-2024 (K24 + GATE_QUOTA_SKIP_WHEN_FULL=true, SIM_END_DATE=20241231),\n"
        "jar chuyendinh/sim-jar-cand (sha256 %s, branch feat/sim-export-candidates, key SIM_EXPORT_CANDIDATES).\n\n"
        "File cands_2024.csv.gz: loc ts trong 2024 (UTC) tu cands.csv cua kernel.\n"
        "Cot: ts,symbol,bar_ret,p15,thr_base,q_t,gate_pass,gate_reason,s1,rank,topk,entered.\n"
        "Khong tinh outcome (de MASTER pre-reg sau).\n" % JAR_SHA)
    json.dump({"title": OUT_DATASET, "id": ks.USER + "/" + OUT_DATASET, "licenses": [{"name": "CC0-1.0"}]},
              open(OUT_DS_DIR + "/ds/dataset-metadata.json", "w"))
    api = ks._api()
    ref = ks.USER + "/" + OUT_DATASET
    try:
        st = str(api.dataset_status(ref))
    except Exception:
        st = "missing"
    if st.lower() == "ready":
        r = api.dataset_create_version(OUT_DS_DIR + "/ds", version_notes="P4 cand 2024 rows=%d" % n_2024, quiet=True)
    else:
        r = api.dataset_create_new(OUT_DS_DIR + "/ds", public=False, quiet=True, dir_mode="skip")
    log.info("UPLOAD -> %s (n_2024=%d)", getattr(r, "url", r), n_2024)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"ds": make_ds, "create_ds": create_ds, "submit": submit, "status": status,
     "fetch": fetch, "upload": upload}[cmd]()
