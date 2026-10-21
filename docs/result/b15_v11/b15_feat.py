#!/usr/bin/env python3
"""B15_V11 (PREREG 6cf67a58 §4): dac trung impact moi leg (L24, sig_d, nbar) tai phut vao M, DUNG leg_features cua
edge_attr_build.py (EDGE_ATTR 4852f57e). Cache theo (vs, M) -> feat_cache.parquet. Kline 2026: tai tu Kaggle
chuyendinh/vz-kline1m-2026 vao kl26/ (xoa sau khi xong).
Usage: python3 b15_feat.py TAG [TAG ...]
"""
import glob
import logging
import os
import sys
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/edge_attr")
import edge_attr_build as EB  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("b15f")
W = "/home/ubuntu/claude_master/b15"
KL = W + "/kl26"
CACHE = W + "/feat_cache.parquet"
H7 = pd.Timedelta(hours=7)
_kp0 = EB.kp
_api = []


def kp(ym):
    if ym < "2026-01":
        return _kp0(ym)
    p = KL + "/kline1m-%s.parquet" % ym
    if not os.path.exists(p):
        if not _api:
            from kaggle.api.kaggle_api_extended import KaggleApi
            a = KaggleApi()
            a.authenticate()
            _api.append(a)
        os.makedirs(KL, exist_ok=True)
        _api[0].dataset_download_file("chuyendinh/vz-kline1m-2026", "kline1m-%s.parquet" % ym, path=KL, quiet=True)
        for z in glob.glob(KL + "/*.zip"):
            with zipfile.ZipFile(z) as f:
                f.extractall(KL)
            os.remove(z)
    log.info("kp %s exists=%s", ym, os.path.exists(p))
    return p if os.path.exists(p) else None


EB.kp = kp


def pairs_of(tag):
    d = pd.read_csv("/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv" % tag, index_col=False, usecols=["sym", "start"])
    t0 = pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    return pd.DataFrame({"vs": d["sym"].astype(str).str.strip() + "USDT",
                         "M": ((t0 - H7).astype("int64") // 10 ** 6).astype(np.int64)})


def load_cache():
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    e = pd.read_parquet("/home/ubuntu/claude_master/edge_attr/legs.parquet", columns=["vs", "M", "L24", "sig_d", "nbar"])
    e = e[np.isfinite(e["L24"]) & np.isfinite(e["nbar"])].drop_duplicates(["vs", "M"])
    log.info("seed cache tu EDGE_ATTR legs.parquet: %d cap", len(e))
    return e.reset_index(drop=True)


def main(tags):
    c = load_cache()
    need = pd.concat([pairs_of(t) for t in tags]).drop_duplicates()
    have = set(zip(c["vs"], c["M"]))
    miss = need[[(v, m) not in have for v, m in zip(need["vs"], need["M"])]].copy()
    log.info("tags=%d pairs=%d cache=%d can tinh=%d", len(tags), len(need), len(c), len(miss))
    if len(miss):
        miss["ym"] = pd.to_datetime(miss["M"], unit="ms").dt.strftime("%Y-%m")
        miss = EB.leg_features(miss.reset_index(drop=True))
        bad = [ym for ym in miss["ym"].unique() if kp(ym) is None]
        if bad:
            log.error("THIEU kline thang %s -> khong cache cac leg do", bad)
        miss = miss[~miss["ym"].isin(bad)].copy()
        miss.loc[~np.isfinite(miss["nbar"]), "nbar"] = 0.0   # thang co file nhung symbol vang
        add = miss[["vs", "M", "L24", "sig_d", "nbar"]]
        c = pd.concat([c, add], ignore_index=True).drop_duplicates(["vs", "M"], keep="last")
        c.to_parquet(CACHE, index=False)
    log.info("FEAT_DONE cache=%d", len(c))


if __name__ == "__main__":
    main(sys.argv[1:])
