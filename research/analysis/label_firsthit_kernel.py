#!/usr/bin/env python3
"""LABEL_FIRSTHIT — chuan bi dataset nhan FH + dung kernel Kaggle GPU (train FH + CTRL trong 1 kernel).
Pre-reg docs/prereg/PREREG_LABEL_FIRSTHIT.md. Usage: python3 label_firsthit_kernel.py prep | build
prep : gop labels/fh_YYYYMM.parquet -> fh_all.parquet (cham) + ds/fh_train_labels.parquet (ts < 20251001-168h, ts,symId,y)
build: kernel dir k_fh/ (trainer label_firsthit_train.py nhung base64 + assert md5, assert sha nhan FH).
"""
import base64, glob, hashlib, json, logging, os, sys
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("fhkb")
R = "/home/ubuntu/src/BinanceFuturesJava"
D = "/home/ubuntu/claude_master/1003/fh"
TZ = 7 * 3600000
CUT_MAX = int(pd.Timestamp("2025-10-01", tz="UTC").value // 10 ** 6) - TZ   # cutoff 20251001 (00:00 GMT+7)
PURGE = 672 * 900000
SLUG = "label-firsthit-g015-gpu"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def prep():
    fs = sorted(glob.glob(D + "/labels/fh_2*.parquet"))
    assert len(fs) == 60, len(fs)
    A = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    assert not A.duplicated(["ts", "symId"]).any()
    A.to_parquet(D + "/fh_all.parquet", index=False)
    yr = pd.to_datetime(A.ts, unit="ms").dt.year
    st = A.assign(yr=yr).groupby("yr").agg(n=("y", "size"), y=("y", "mean"),
                                             sl=("hit", lambda h: float(np.isin(h, [2, 3]).mean())),
                                             tie=("hit", lambda h: float((h == 3).mean())),
                                             none=("hit", lambda h: float((h == 0).mean())))
    log.info("FH all %d dong\n%s", len(A), st.to_string())
    T = A[A.ts < CUT_MAX - PURGE][["ts", "symId", "y"]].reset_index(drop=True)
    os.makedirs(D + "/ds", exist_ok=True)
    T.to_parquet(D + "/ds/fh_train_labels.parquet", index=False)
    meta = {"title": "fh-label-firsthit", "id": "chuyendinh/fh-label-firsthit", "licenses": [{"name": "CC0-1.0"}]}
    json.dump(meta, open(D + "/ds/dataset-metadata.json", "w"), indent=1)
    s = sha256(D + "/ds/fh_train_labels.parquet")
    json.dump({"sha": s, "rows": int(len(T)), "ts_max": int(T.ts.max()), "by_year": st.reset_index().to_dict("records")},
              open(D + "/fh_prep.json", "w"), indent=1, default=float)
    log.info("train labels %d dong ts_max %s sha %s", len(T), pd.to_datetime(int(T.ts.max()), unit="ms"), s)


def build():
    src = open(R + "/research/analysis/label_firsthit_train.py", "rb").read()
    md5 = hashlib.md5(src).hexdigest()
    fsha = json.load(open(D + "/fh_prep.json"))["sha"]
    tpl = open(D + "/label_firsthit_kernel_tpl.py").read()
    b64 = base64.b64encode(src).decode()
    b64 = "\n".join(b64[i:i + 100] for i in range(0, len(b64), 100))
    code = (tpl.replace("__ARMS__", repr(["FH", "CTRL"])).replace("__MD5__", md5)
            .replace("__FHSHA__", fsha).replace("__B64__", b64))
    kd = D + "/k_fh"
    os.makedirs(kd, exist_ok=True)
    open(kd + "/" + SLUG + ".py", "w").write(code)
    meta = {"id": "chuyendinh/" + SLUG, "title": SLUG, "code_file": SLUG + ".py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_tpu": False,
            "enable_internet": False, "keywords": ["gpu"],
            "dataset_sources": ["chuyendinh/funding-oi-percoin", "chuyendinh/funding-unf15-data",
                                "chuyendinh/sel1m-code", "chuyendinh/fh-label-firsthit"],
            "kernel_sources": [], "competition_sources": [], "model_sources": []}
    json.dump(meta, open(kd + "/kernel-metadata.json", "w"), indent=1)
    log.info("built %s trainer md5=%s fh sha=%s", kd, md5, fsha)


if __name__ == "__main__":
    {"prep": prep, "build": build}[sys.argv[1]]()
