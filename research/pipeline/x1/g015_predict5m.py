#!/usr/bin/env python3
"""g015_predict5m.py -- PREDICT-ONLY net015 tren luoi 5 PHUT, dung MODEL da train
o luoi 15 PHUT (khong train lai). Theo chi dao: train 15m khong anh huong nhieu,
predict/trade can luoi 5m cho chuan.

Model: /home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json (18 model goc da
train+validate luoi 15m, 2026-08-14, xem docs/G3_X26_RECOVERY.md). KHONG train lai.
Feature: /home/ubuntu/ds_feat5m (Tool1 5-phut, T1C2, 22 quy, local Oracle).
OI: khong phu thuoc grid, dung chung claudedata/oi/*.

Toi uu quan trong: CHI doc DUNG 1 file quy (quarter) khop [cutoff, cutoff+3thang)
thay vi ca nam (ten file da quy-aligned: features_<cut>_to_<cut+3m>.t1c.gz) --
giu peak RAM ~ tuong duong ban 15m full-year da chung minh an toan tren Oracle 23GB,
thay vi ca nam 5-phut (~3x dong) co the OOM.

CHAY 1 fold:
  python3 g015_predict5m.py --cutoff 20250101 --fold-idx 12 --out-dir /duong/dan
CHAY tat ca 16 fold (khop X1_CUTS):
  python3 g015_predict5m.py --fold-idx all --out-dir /duong/dan
"""
import argparse, glob, json, logging, os, struct, sys, time
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("g015pred5m")
sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
from tool1_col import read_tool1

GRID_MIN = 5
GRID_MS = GRID_MIN * 60_000
TZ = 7 * 3_600_000
OI_TOL = 2 * 3_600_000
OOS_MONTHS = 3
NF = 45
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])

T1_DIR = os.environ.get("T1_DIR_5M", "/home/ubuntu/ds_feat5m")
OI_FILE = os.environ.get("OI_FILE", "/home/ubuntu/claudedata/oi/oi_percoin_full.bin")
MAP_CSV = os.environ.get("MAP_CSV", "/home/ubuntu/claudedata/oi/symbol_map.csv")
MODEL_DIR = os.environ.get("MODEL_DIR", "/home/ubuntu/claudedata/predwf_G015")

CUT_DATES = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401",
             "20230701", "20231001", "20240101", "20240401", "20240701", "20241001",
             "20250101", "20250401", "20250701", "20251001"]  # 16 cutoff, khop X1_CUTS


def ms(datestr):
    d = pd.Timestamp("%s-%s-%s" % (datestr[:4], datestr[4:6], datestr[6:8]), tz="UTC")
    return int(d.value // 10 ** 6) - TZ


def predict_fold(cutoff, fold_idx, out_dir):
    t0 = time.time()
    c = ms(cutoff)
    cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
    lo_b = c
    hi_dt = cdt + pd.DateOffset(months=OOS_MONTHS)
    hi_b = int(hi_dt.value // 10 ** 6) - TZ
    nextq = hi_dt.strftime("%Y%m%d")
    log.info("fold %d cutoff=%s block=[%s .. %s) file~=features_%s_to_%s.*",
             fold_idx, cutoff, pd.to_datetime(lo_b, unit="ms"), pd.to_datetime(hi_b, unit="ms"),
             cutoff, nextq)

    pat = os.path.join(T1_DIR, "features_%s_to_%s.*" % (cutoff, nextq))
    files = sorted(glob.glob(pat))
    assert len(files) == 1, "ky vong dung 1 file quy, thay %d: %s" % (len(files), pat)
    a = read_tool1(files[0], grid_ms=GRID_MS)
    F = a["f"]
    log.info("read_tool1 %s: %d dong", os.path.basename(files[0]), len(a))
    ao = np.memmap(OI_FILE, dtype=OI_DT, mode="r")
    smap = pd.read_csv(MAP_CSV)
    aots = np.asarray(ao["ts"])
    msk = (aots >= lo_b - OI_TOL) & (aots < hi_b)
    del aots
    aoc = np.array(ao[msk]); del msk, ao
    t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32),
                       "ridx": np.arange(len(a), dtype=np.int64)})
    o = pd.DataFrame({"ts": aoc["ts"].astype(np.int64), "symId": aoc["sym"].astype(np.int32)})
    O = np.asarray(aoc["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        o[nm] = O[:, j]
    del aoc, O
    t = t.sort_values("ts").reset_index(drop=True)
    o = o.sort_values("ts").reset_index(drop=True)
    mg = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL)
    del t, o
    mg = mg.merge(smap, on="symId", how="left").dropna(subset=["symbol"])
    mg = mg.sort_values("ts").reset_index(drop=True)
    tsv = mg["ts"].to_numpy()
    sub = mg[(tsv >= lo_b) & (tsv < hi_b)]
    n = len(sub)
    X = np.empty((n, NF), dtype=np.float32)
    X[:, :40] = F[sub["ridx"].to_numpy()]
    X[:, 40:] = sub[OI_NAMES].to_numpy(np.float32)
    ts_oos = sub["ts"].to_numpy(np.int64)
    sid_oos = sub["symId"].to_numpy(np.int32)
    del a, F, mg, sub

    import xgboost as xgb
    clf = xgb.XGBClassifier()
    clf.load_model(os.path.join(MODEL_DIR, "model_f%d_4h.json" % fold_idx))
    p0 = clf.predict_proba(X)[:, 1].astype(np.float32)
    del X, clf
    log.info("fold %d %s: OOS rows=%d pred mean=%.6f std=%.6f", fold_idx, cutoff, n,
             float(p0.mean()), float(p0.std()))

    os.makedirs(out_dir, exist_ok=True)
    outp = os.path.join(out_dir, "predict_wf_%s.bin" % cutoff)
    nan = float("nan")
    with open(outp, "wb") as fo:
        buf = bytearray()
        for i in range(len(ts_oos)):
            buf += struct.pack(">qh4f", int(ts_oos[i]), int(sid_oos[i]), float(p0[i]), nan, nan, nan)
        fo.write(buf)
        fo.flush()
        os.fsync(fo.fileno())
    log.info("ghi %s: %d rec = %d bytes | %.1fs", outp, len(ts_oos), len(ts_oos) * 26,
             time.time() - t0)
    return {"cutoff": cutoff, "fold_idx": fold_idx, "n_oos": int(n),
            "p_mean": float(p0.mean()), "p_std": float(p0.std())}


def main():
    ap = argparse.ArgumentParser(description="net015 predict-only tren luoi 5 phut, model 15 phut")
    ap.add_argument("--cutoff", default=None, help="1 cutoff YYYYMMDD (bo qua neu --fold-idx=all)")
    ap.add_argument("--fold-idx", default="all", help="chi so model_f<i>_4h.json, hoac 'all'")
    ap.add_argument("--out-dir", default="/home/ubuntu/predwf_G015x26_5m")
    a = ap.parse_args()
    results = []
    if a.fold_idx == "all":
        for i, cutoff in enumerate(CUT_DATES):
            results.append(predict_fold(cutoff, i, a.out_dir))
    else:
        assert a.cutoff, "--cutoff bat buoc khi --fold-idx != all"
        results.append(predict_fold(a.cutoff, int(a.fold_idx), a.out_dir))
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "predict5m_summary.json"), "w") as fo:
        json.dump(results, fo, indent=1)
    log.info("DONE %d fold -> %s", len(results), a.out_dir)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise
