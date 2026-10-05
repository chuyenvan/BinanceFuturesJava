#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPLOY242 readiness (BAC 1, 0-sim, OFFLINE, CHI DOC) — lineage model gate p15 + phan bo live vs DEV + gate buffer.

Buoc (moi so in ra deu do lai duoc; 2026 CHI dung so sanh phan bo LIVE, KHONG cham sim/chon tham so):
  A. Retrain dung recipe ml/gate/train_gate_fold.py (XGB d4/n150/lr0.05/sub0.8/col0.8/mcw10/seed42/n_jobs4,
     purge 15') tren store ~/claudedata/gate_dataset_full.csv.gz:
       - fold_18 (CUTOFF=20251001) -> doi chieu pred.bin 2025Q4 (kiem moi truong tai lap = RESULT_PREDBIN_REPRO)
       - fold_final (CUTOFF=20260101, train <= 2025-12-31 23:45) -> export ONNX (onnxmltools.convert_xgboost)
         -> parity Python(model.predict) vs onnxruntime tren >=20k vector (store + feat_dump live + devexport)
  B. Lineage .onnx dang chay tren 242 (keo ve READ-ONLY): md5/sha256, chu ky I/O, so cay/do sau, corr vs pred.bin.
  C. Phan bo p15 (%): pred.bin 2025 / 2025Q4 | live p15_out (feat_dump 242) | ONNX242(feat_dump) | NEW(feat_dump)
     | NEW(devexport 2026-07-01..09-28, replay offline) | ONNX242(devexport).
  D. Gate buffer run/gate_ratio_live.bin (GRR1/snappy): n, khoang ts, phan vi r; uoc factor*gs = p15_old/r de
     tinh r_new = p15_new/(factor*gs) va so pass FALLBACK (thr = 0.008*factor*gs) neu doi model.
Output: <OUT>/lineage.json, <OUT>/model/Model_Regressor_Return15M.onnx (+ manifest.json).
"""
import glob
import hashlib
import json
import logging
import os
import struct
import sys
import time
import zlib

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("deploy242_lineage")

HOME = os.path.expanduser("~")
OUT = os.environ.get("OUT", HOME + "/claude_master/1002/deploy242")
STORE = os.environ.get("STORE", HOME + "/claudedata/gate_dataset_full.csv.gz")
PREDBIN = os.environ.get("PREDBIN", HOME + "/wfo_ds_x1_2021/pred.bin")
LIVE_ONNX = os.environ.get("LIVE_ONNX", OUT + "/live242/gate242.onnx")
FEAT_DUMP_DIR = os.environ.get("FEAT_DUMP_DIR", OUT + "/live242/fd/feat_dump")
DEVEXPORT = os.environ.get("DEVEXPORT", HOME + "/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz")
GATE_BUF = os.environ.get("GATE_BUF", OUT + "/live242/gate_ratio_live.bin")
WFO_MODELS = HOME + "/claudedata/wfo_models"
PURGE_MS = 15 * 60 * 1000

# Thu tu V3FULL — COPY tu ml/gate/train_gate_fold.py (= OnnxInferenceManager.extractFeaturesV3Full). Nguon su that.
V3FULL = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
    "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength", "btcDominance",
    "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]
assert len(V3FULL) == 33
XGB_PARAMS = dict(objective="reg:squarederror", max_depth=4, n_estimators=150, learning_rate=0.05,
                  subsample=0.8, colsample_bytree=0.8, min_child_weight=10, random_state=42, n_jobs=4)
QS = [50, 90, 99, 99.9]
THR_TAIL = 0.02947   # nguong "duoi" dung trong RESULT_GATE_ROOTCAUSE (frac >= 2,947%)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cut_ms(yyyymmdd):
    """GIONG train_gate_fold.py: pd.Timestamp(naive).value//1e6 (= 00:00 UTC)."""
    return pd.Timestamp("%s-%s-%s" % (yyyymmdd[:4], yyyymmdd[4:6], yyyymmdd[6:])).value // 10 ** 6


def dist(x, name):
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return {"name": name, "n": 0}
    d = {"name": name, "n": int(len(x))}
    for q in QS:
        d["p%s" % q] = round(float(np.percentile(x, q)) * 100, 4)
    d["max"] = round(float(x.max()) * 100, 4)
    d["frac_ge_2947"] = float((x >= THR_TAIL).mean())
    d["n_ge_2947"] = int((x >= THR_TAIL).sum())
    LOG.info("[DIST] %-34s n=%8d p50=%.3f p90=%.3f p99=%.3f p99.9=%.3f max=%.3f (%%) n>=2.947%%=%d",
             name, d["n"], d["p50"], d["p90"], d["p99"], d["p99.9"], d["max"], d["n_ge_2947"])
    return d


def corr(a, b):
    from scipy.stats import spearmanr
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    m = np.isfinite(a) & np.isfinite(b)
    return {"n": int(m.sum()), "pearson": float(np.corrcoef(a[m], b[m])[0, 1]),
            "spearman": float(spearmanr(a[m], b[m]).correlation), "max_abs_diff": float(np.max(np.abs(a[m] - b[m])))}


def load_predbin(path):
    raw = open(path, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + n * 16], dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")]))
    return pd.DataFrame({"ts": a["ts"].astype(np.int64), "p15_dev": a["p15"].astype(np.float32)})


def read_gz_partial(path):
    """Doc gz ke ca file thieu trailer (writer cu / file dang ghi). Bo dong cuoi chua tron."""
    raw = open(path, "rb").read()
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        txt = d.decompress(raw)
    except zlib.error:
        txt = b""
    txt = txt.decode("utf-8", "replace")
    if not txt.endswith("\n"):
        txt = txt[:txt.rfind("\n") + 1]
    return txt


def load_feat_dump(dirpath):
    import io
    frames = []
    files = sorted(glob.glob(os.path.join(dirpath, "feat_dump_*.csv.gz")))
    for f in files:
        txt = read_gz_partial(f)
        if txt.count("\n") < 2:
            continue
        try:
            frames.append(pd.read_csv(io.StringIO(txt)))
        except Exception as e:   # file hong -> bo, ghi log
            LOG.warning("bo %s: %s", f, e)
    df = pd.concat(frames, ignore_index=True)
    df = df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    LOG.info("[FEAT_DUMP] %d file, %d dong (dedup ts) %s .. %s", len(files), len(df),
             pd.to_datetime(df.ts.min(), unit="ms"), pd.to_datetime(df.ts.max(), unit="ms"))
    return df, len(files)


def onnx_info(path):
    import onnx
    m = onnx.load(path)
    info = {"md5": md5(path), "sha256": sha256(path), "bytes": os.path.getsize(path),
            "producer": "%s %s" % (m.producer_name, m.producer_version), "ir_version": m.ir_version,
            "opset": [(o.domain, o.version) for o in m.opset_import],
            "inputs": [(i.name, [d.dim_value or d.dim_param for d in i.type.tensor_type.shape.dim]) for i in m.graph.input],
            "outputs": [(o.name, [d.dim_value or d.dim_param for d in o.type.tensor_type.shape.dim]) for o in m.graph.output],
            "metadata": {p.key: p.value for p in m.metadata_props}, "doc_string": m.doc_string[:200]}
    for node in m.graph.node:
        if node.op_type.startswith("TreeEnsemble"):
            at = {a.name: a for a in node.attribute}
            tids = list(at["nodes_treeids"].ints) if "nodes_treeids" in at else []
            modes = [s.decode() for s in at["nodes_modes"].strings] if "nodes_modes" in at else []
            info["tree_op"] = node.op_type
            info["n_trees"] = (max(tids) + 1) if tids else None
            info["n_nodes"] = len(tids)
            info["n_leaves"] = sum(1 for s in modes if s == "LEAF")
            info["base_values"] = list(at["base_values"].floats) if "base_values" in at else None
            info["post_transform"] = at["post_transform"].s.decode() if "post_transform" in at else None
            feats = list(at["nodes_featureids"].ints) if "nodes_featureids" in at else []
            used = sorted(set(f for f, mo in zip(feats, modes) if mo != "LEAF"))
            info["n_features_used"] = len(used)
    return info


def ort_predict(path, X):
    import onnxruntime as ort
    s = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    name = s.get_inputs()[0].name     # GIONG Java: session.getInputNames().iterator().next()
    out = s.run(None, {name: np.ascontiguousarray(X, dtype=np.float32)})[0]
    return np.asarray(out, dtype=np.float64).reshape(-1)


def load_gate_buffer(path):
    """GateRatioPersist: chunk = [MAGIC 'GRR1' i4][LEN i4][CRC32 i4][snappy(raw)], raw = n x [ts i8][r f4] big-endian."""
    import snappy
    raw = open(path, "rb").read()
    off, ts_l, r_l, nchunk = 0, [], [], 0
    while off + 12 <= len(raw):
        magic, ln, crc = struct.unpack(">iiI", raw[off:off + 12])
        off += 12
        if magic != 0x47525231:
            raise ValueError("magic sai tai %d" % (off - 12))
        if off + ln > len(raw):
            break
        comp = raw[off:off + ln]
        off += ln
        if (zlib.crc32(comp) & 0xffffffff) != crc:
            raise ValueError("CRC lech chunk %d" % nchunk)
        u = snappy.uncompress(comp)
        k = len(u) // 12
        a = np.frombuffer(u[:k * 12], dtype=np.dtype([("ts", ">i8"), ("r", ">f4")]))
        ts_l.append(a["ts"].astype(np.int64))
        r_l.append(a["r"].astype(np.float64))
        nchunk += 1
    return np.concatenate(ts_l), np.concatenate(r_l), nchunk


def train_fold(store, cutoff):
    from xgboost import XGBRegressor
    cut = cut_ms(cutoff)
    tr = store[store.timestamp < cut - PURGE_MS]
    assert tr.timestamp.max() < cut - PURGE_MS
    t0 = time.time()
    m = XGBRegressor(**XGB_PARAMS)
    m.fit(tr[V3FULL].values.astype(np.float32), tr["label_oldbasket"].values.astype(np.float32))
    LOG.info("[TRAIN] cutoff=%s train_rows=%d ts_max=%s (%.0fs)", cutoff, len(tr),
             pd.to_datetime(tr.timestamp.max(), unit="ms"), time.time() - t0)
    return m, {"cutoff": cutoff, "cut_ms": int(cut), "train_rows": int(len(tr)),
               "train_ts_min": str(pd.to_datetime(tr.timestamp.min(), unit="ms")),
               "train_ts_max": str(pd.to_datetime(tr.timestamp.max(), unit="ms"))}


def export_onnx(model, path):
    from onnxmltools.convert import convert_xgboost
    from skl2onnx.common.data_types import FloatTensorType
    onx = convert_xgboost(model, initial_types=[("float_input", FloatTensorType([None, 33]))])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(onx.SerializeToString())
    return path


def main():
    res = {"generated": time.strftime("%Y-%m-%d %H:%M:%S %z"), "inputs": {}}
    # ---------------- inputs
    LOG.info("doc store %s", STORE)
    store = pd.read_csv(STORE, usecols=["timestamp"] + V3FULL + ["label_oldbasket"])
    store = store.dropna(subset=["label_oldbasket"])
    store[V3FULL] = store[V3FULL].astype(np.float32)
    res["inputs"]["store"] = {"path": STORE, "sha256": sha256(STORE), "rows": int(len(store)),
                              "ts_min": str(pd.to_datetime(store.timestamp.min(), unit="ms")),
                              "ts_max": str(pd.to_datetime(store.timestamp.max(), unit="ms"))}
    LOG.info("[STORE] %s", res["inputs"]["store"])
    pb = load_predbin(PREDBIN)
    res["inputs"]["predbin"] = {"path": PREDBIN, "md5": md5(PREDBIN), "rows": int(len(pb))}
    fd, nfd = load_feat_dump(FEAT_DUMP_DIR)
    res["inputs"]["feat_dump"] = {"dir": FEAT_DUMP_DIR, "files": nfd, "rows": int(len(fd)),
                                  "ts_min": str(pd.to_datetime(fd.ts.min(), unit="ms")),
                                  "ts_max": str(pd.to_datetime(fd.ts.max(), unit="ms"))}
    dx = pd.read_csv(DEVEXPORT, usecols=["ts"] + V3FULL).drop_duplicates("ts").sort_values("ts")
    res["inputs"]["devexport"] = {"path": DEVEXPORT, "rows": int(len(dx)),
                                  "ts_min": str(pd.to_datetime(dx.ts.min(), unit="ms")),
                                  "ts_max": str(pd.to_datetime(dx.ts.max(), unit="ms"))}
    LOG.info("[DEVEXPORT] %s", res["inputs"]["devexport"])

    # ---------------- A1. fold_18 retrain vs pred.bin 2025Q4 (kiem moi truong)
    q4a, q4b = cut_ms("20251001"), cut_ms("20260101")
    m18, meta18 = train_fold(store, "20251001")
    oos = store[(store.timestamp >= q4a) & (store.timestamp < q4b)]
    j = oos[["timestamp"]].copy()
    j["p_retrain18"] = m18.predict(oos[V3FULL].values.astype(np.float32))
    j = j.merge(pb.rename(columns={"ts": "timestamp"}), on="timestamp", how="inner")
    res["A1_fold18_vs_predbin_2025Q4"] = {"meta": meta18, "corr": corr(j.p_retrain18, j.p15_dev),
                                         "dist_retrain": dist(j.p_retrain18, "retrain18@2025Q4"),
                                         "dist_predbin": dist(j.p15_dev, "pred.bin@2025Q4")}
    LOG.info("[A1] %s", res["A1_fold18_vs_predbin_2025Q4"]["corr"])

    # ---------------- A2. fold_final (train <= 2025-12-31) -> ONNX -> parity Python vs ORT
    mF, metaF = train_fold(store, "20260101")
    onnx_new = export_onnx(mF, os.path.join(OUT, "model", "Model_Regressor_Return15M.onnx"))
    rng = np.random.default_rng(20261002)
    Xs = store[V3FULL].values[rng.choice(len(store), 20000, replace=False)]
    Xpar = np.vstack([Xs, fd[V3FULL].values.astype(np.float32), dx[V3FULL].values.astype(np.float32)[::10]])
    p_py = mF.predict(Xpar).astype(np.float64)
    p_ort = ort_predict(onnx_new, Xpar)
    dpar = np.abs(p_py - p_ort)
    res["A2_final_export"] = {"meta": metaF, "xgb_params": XGB_PARAMS, "onnx": onnx_info(onnx_new),
                              "parity_py_vs_ort": {"n": int(len(Xpar)), "max_abs": float(dpar.max()),
                                                   "p99_abs": float(np.percentile(dpar, 99)),
                                                   "pass_1e6": bool(dpar.max() <= 1e-6)}}
    import xgboost, onnxruntime, onnxmltools
    res["A2_final_export"]["versions"] = {"xgboost": xgboost.__version__, "onnxruntime": onnxruntime.__version__,
                                          "onnxmltools": onnxmltools.__version__}
    LOG.info("[A2] parity py vs ORT: %s", res["A2_final_export"]["parity_py_vs_ort"])
    with open(os.path.join(OUT, "model", "manifest.json"), "w") as fh:
        json.dump({"what": "gate p15 DEV-generation final fold (recipe train_gate_fold.py)", "store": res["inputs"]["store"],
                   "train": metaF, "xgb_params": XGB_PARAMS, "features_v3full_order": V3FULL,
                   "label": "label_oldbasket", "purge_ms": PURGE_MS, "onnx_sha256": sha256(onnx_new),
                   "versions": res["A2_final_export"]["versions"],
                   "status": "CANDIDATE — CHUA deploy; can owner duyet o bac 2a"}, fh, indent=1)

    # ---------------- B. lineage ONNX 242
    live_info = onnx_info(LIVE_ONNX)
    wfo_md5 = {os.path.basename(os.path.dirname(p)): md5(p)
               for p in sorted(glob.glob(WFO_MODELS + "/fold_*/Model_Regressor_Return15M.onnx"))}
    live_info["same_md5_as_wfo_models"] = [k for k, v in wfo_md5.items() if v == live_info["md5"]]
    oq = oos[V3FULL].values.astype(np.float32)
    p_live_q4 = ort_predict(LIVE_ONNX, oq)
    p_new_q4 = ort_predict(onnx_new, oq)
    jj = oos[["timestamp"]].copy()
    jj["live"], jj["new"], jj["r18"] = p_live_q4, p_new_q4, m18.predict(oq)
    jj = jj.merge(pb.rename(columns={"ts": "timestamp"}), on="timestamp", how="inner")
    res["B_lineage_live_onnx"] = {"live": live_info, "new": res["A2_final_export"]["onnx"],
                                  "corr_live_vs_predbin_2025Q4": corr(jj.live, jj.p15_dev),
                                  "corr_live_vs_retrain18_2025Q4": corr(jj.live, jj.r18),
                                  "corr_new_vs_predbin_2025Q4": corr(jj.new, jj.p15_dev),
                                  "dist_live_on_store_2025Q4": dist(jj.live, "ONNX242@store2025Q4"),
                                  "dist_new_on_store_2025Q4": dist(jj.new, "NEW(insample)@store2025Q4")}
    LOG.info("[B] live onnx = %s ; corr live vs pred.bin Q4 %s", live_info["same_md5_as_wfo_models"],
             res["B_lineage_live_onnx"]["corr_live_vs_predbin_2025Q4"])

    # ---------------- C. phan bo p15 (%)
    pbd = pb.copy()
    pbd["dt"] = pd.to_datetime(pbd.ts, unit="ms")
    Xfd = fd[V3FULL].values.astype(np.float32)
    p_live_fd = ort_predict(LIVE_ONNX, Xfd)
    p_new_fd = ort_predict(onnx_new, Xfd)
    Xdx = dx[V3FULL].values.astype(np.float32)
    p_live_dx = ort_predict(LIVE_ONNX, Xdx)
    p_new_dx = ort_predict(onnx_new, Xdx)
    res["C_dist"] = {
        "predbin_2025": dist(pbd.p15_dev[(pbd.ts >= cut_ms("20250101")) & (pbd.ts < q4b)], "pred.bin DEV 2025"),
        "predbin_2025Q4": dist(pbd.p15_dev[(pbd.ts >= q4a) & (pbd.ts < q4b)], "pred.bin DEV 2025Q4"),
        "predbin_all": dist(pbd.p15_dev, "pred.bin DEV 2021-04..2025-12"),
        "live_p15_out_featdump": dist(fd.p15_out, "LIVE p15_out (feat_dump 242)"),
        "onnx242_on_featdump": dist(p_live_fd, "ONNX242(feat_dump)"),
        "new_on_featdump": dist(p_new_fd, "NEW(feat_dump LIVE)"),
        "onnx242_on_devexport": dist(p_live_dx, "ONNX242(devexport 07-09/2026)"),
        "new_on_devexport": dist(p_new_dx, "NEW(devexport 07-09/2026)"),
    }
    res["C_check_dump_consistency"] = corr(p_live_fd, fd.p15_out.values)
    res["C_corr_new_vs_live_featdump"] = corr(p_new_fd, p_live_fd)
    res["C_corr_new_vs_live_devexport"] = corr(p_new_dx, p_live_dx)
    LOG.info("[C] ONNX242(feat_dump) vs p15_out: %s", res["C_check_dump_consistency"])

    # ---------------- D. gate buffer
    bts, br, nch = load_gate_buffer(GATE_BUF)
    pct = 0.999950829
    D = {"file": GATE_BUF, "sha256": sha256(GATE_BUF), "chunks": nch, "n": int(len(br)),
         "ts_unique": int(len(np.unique(bts))),
         "ts_min": str(pd.to_datetime(bts.min(), unit="ms")), "ts_max": str(pd.to_datetime(bts.max(), unit="ms")),
         "span_days": float((bts.max() - bts.min()) / 86400000.0),
         "r_p50": float(np.percentile(br, 50)), "r_p99": float(np.percentile(br, 99)),
         "r_q_pct_all": float(np.quantile(br, pct)), "r_max": float(br.max())}
    # factor*gs = p15_old / r ; p15_old lay tu feat_dump p15_out cung phut (ts tick selector = phut)
    bdf = pd.DataFrame({"ts": bts, "r": br})
    m = bdf.merge(pd.DataFrame({"ts": fd.ts.values, "p15_old": fd.p15_out.values, "p15_new": p_new_fd}), on="ts")
    m = m[(m.r > 0) & (m.p15_old > 0)]
    if len(m):
        fgs = m.p15_old / m.r
        m["r_new"] = m.p15_new / fgs
        thr_fb = 0.008 * fgs            # nguong FALLBACK (warm-up) = MIN_MOMENTUM_15M * factor * gs
        D.update({"matched_records": int(len(m)), "matched_ts": int(m.ts.nunique()),
                  "factor_gs_p50": float(np.median(fgs)), "thr_fallback_p50": float(np.median(thr_fb)),
                  "thr_fallback_min": float(thr_fb.min()),
                  "fallback_pass_old": int((m.p15_old >= thr_fb).sum()),
                  "fallback_pass_new": int((m.p15_new >= thr_fb).sum()),
                  "r_new_p50": float(np.median(m.r_new)), "r_new_max": float(m.r_new.max()),
                  "r_old_max_matched": float(m.r.max())})
    res["D_gate_buffer"] = D
    LOG.info("[D] %s", D)
    with open(os.path.join(OUT, "lineage.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=str)
    LOG.info("ghi %s", os.path.join(OUT, "lineage.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
