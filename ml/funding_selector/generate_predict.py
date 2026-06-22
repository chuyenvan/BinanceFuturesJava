#!/usr/bin/env python3
"""
TASK-039c - Generate funding predict SET (per-thang).

Dung 4 model XGBClassifier (.ubj tu 039a) predict P(cham +6%) cho 4 horizon, cho MOI diem
Tool1 (mac dinh MOI PHUT cua tap da filter; GRID=1 de ep ve 15m) intersect OI (merge_asof
backward) tren toan lich su. KHONG merge label, KHONG filter nBars -> phu moi entry kha di.

Output: predict_YYYYMM.bin, record 26B big-endian ">q h 4f"
        = (ts:int64, symId:int16, p4h, p12h, p24h, p72h: float32).  P(win) in [0,1] (NaN neu feat thieu).

Env:
  TOOL1_GLOB  OI_FILE  MODEL_DIR   (bat buoc)
  OUT_DIR (mac dinh .)   OI_TOL_MS (2h)   RESUME=1 (skip thang da co -> checkpoint/retry)

Convention KHOA: model_<H>.ubj la XGBClassifier objective binary:logistic. Load bang Booster
(khong can sklearn) -> Booster.predict(DMatrix) = sigmoid(margin) = P(class=1) = P(win),
TUONG DUONG XGBClassifier.predict_proba[:,1] cho binary:logistic. DMatrix giu feature_names=FEAT.
"""
import os, gzip, glob, json, re, logging
import numpy as np
import pandas as pd
import xgboost as xgb

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fgen")

GRID_MS = 15 * 60 * 1000
HORIZONS = ["4h", "12h", "24h", "72h"]
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES            # 45 feat - phai khop train_meta.feat

TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B
OUT_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4", 4)])      # 26B
assert OUT_DT.itemsize == 26, f"OUT_DT itemsize {OUT_DT.itemsize} != 26 (numpy padding?)"

TOOL1_GLOB = os.environ.get("TOOL1_GLOB", "/kaggle/input/**/ff_*.bin")
OI_FILE = os.environ.get("OI_FILE", "/kaggle/input/**/oi_percoin_full.bin")
MODEL_DIR = os.environ.get("MODEL_DIR", "/kaggle/input")
OUT_DIR = os.environ.get("OUT_DIR", "/kaggle/working")
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))
RESUME = os.environ.get("RESUME", "1") == "1"
# GRID=1 ép predict về lưới 15m (bản v1 cũ). GRID=0 (mặc định MỚI) giữ MỖI PHÚT của tập đã
# filter — Tool1 vốn export per-phút cho coin lọt EntrySignalFilter; không grid = dày 15x.
GRID = os.environ.get("GRID", "0") == "1"
os.makedirs(OUT_DIR, exist_ok=True)


def _read(path, dt, item, grid=False):
    raw = open(path, "rb").read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    assert len(raw) % item == 0, f"{path}: len {len(raw)} khong chia het {item}"
    a = np.frombuffer(raw, dtype=dt)
    if grid:
        a = a[(a["ts"] % GRID_MS) == 0]
    return a


def load_oi():
    files = sorted(glob.glob(OI_FILE, recursive=True)) if any(c in OI_FILE for c in "*?[") else [OI_FILE]
    assert files, f"OI khong thay: {OI_FILE}"
    a = _read(files[0], OI_DT, 30)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    O = np.asarray(a["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        df[nm] = O[:, j]
    df = df.sort_values("ts").reset_index(drop=True)
    log.info("OI: %d rows | %d symId", len(df), df.symId.nunique())
    return df


def _find(pat):
    f = sorted(glob.glob(pat, recursive=True))
    return f[0] if f else None


def load_models():
    ms = {}
    for H in HORIZONS:
        p = _find(os.path.join(MODEL_DIR, f"**/model_{H}.ubj")) or _find(os.path.join(MODEL_DIR, f"model_{H}.ubj"))
        assert p, f"thieu model {H} trong {MODEL_DIR}"
        b = xgb.Booster()
        b.load_model(p)
        if b.feature_names is not None:
            assert b.feature_names == FEAT, f"feat mismatch {H}: model={b.feature_names[:3]} vs {FEAT[:3]}"
        ms[H] = b
        mp = _find(os.path.join(MODEL_DIR, f"**/train_meta_{H}.json")) or _find(os.path.join(MODEL_DIR, f"train_meta_{H}.json"))
        if mp:
            feat = json.load(open(mp))["feat"]
            assert feat == FEAT, f"feat mismatch train_meta {H}"
    log.info("loaded 4 booster | feat khop train_meta (%d feat)", len(FEAT))
    return ms


def month_of(path):
    m = re.search(r"(\d{6})", os.path.basename(path))
    return m.group(1) if m else os.path.basename(path)


def main():
    oi = load_oi()
    models = load_models()
    files = sorted(glob.glob(TOOL1_GLOB, recursive=True))
    assert files, f"Tool1 khong thay: {TOOL1_GLOB}"
    log.info("%d file Tool1 can predict", len(files))

    index = {}
    for fp in files:
        ym = month_of(fp)
        outp = os.path.join(OUT_DIR, f"predict_{ym}.bin")
        if RESUME and os.path.exists(outp):
            rows = os.path.getsize(outp) // OUT_DT.itemsize
            index[ym] = {"rows": int(rows), "resumed": True}
            log.info("skip %s (da co, %d dong)", ym, rows)
            continue

        a = _read(fp, TOOL1_DT, 170, grid=GRID)
        t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
        F = np.asarray(a["f"], dtype=np.float32)
        for j in range(40):
            t[f"f{j}"] = F[:, j]
        t = t.sort_values("ts").reset_index(drop=True)

        merged = pd.merge_asof(t, oi, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
        X = merged[FEAT]
        dm = xgb.DMatrix(X, feature_names=FEAT, missing=np.nan)
        P = np.column_stack([models[H].predict(dm) for H in HORIZONS]).astype(np.float32)
        assert np.nanmin(P) >= -1e-6 and np.nanmax(P) <= 1 + 1e-6, f"{ym}: p ngoai [0,1]"

        out = np.empty(len(merged), dtype=OUT_DT)
        out["ts"] = merged["ts"].values
        out["sym"] = merged["symId"].values.astype(np.int16)
        out["p"] = P
        out.tofile(outp)

        ts0, ts1 = int(merged.ts.min()), int(merged.ts.max())
        oi_cov = float(merged["oi_z"].notna().mean())
        index[ym] = {"rows": int(len(merged)), "ts_min": ts0, "ts_max": ts1, "oi_cov": round(oi_cov, 4)}
        log.info("predict_%s ghi %d dong | OI-cov %.1f%% | ts[%s .. %s]",
                 ym, len(merged), oi_cov * 100,
                 pd.to_datetime(ts0, unit="ms"), pd.to_datetime(ts1, unit="ms"))

    json.dump(index, open(os.path.join(OUT_DIR, "predict_index.json"), "w"), indent=2)
    total = sum(v["rows"] for v in index.values())
    log.info("XONG %d thang | tong %d dong -> %s", len(index), total, OUT_DIR)


if __name__ == "__main__":
    main()
