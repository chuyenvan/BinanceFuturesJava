#!/usr/bin/env python3
"""
LEAK-FREE funding-selector predictions (walk-forward per-fold) -> predict_wf_*.bin (26B >q h 4f).

Thay vi 1 model train<=2024-12 predict ca history (in-sample, ro ri), sinh prediction WALK-FORWARD:
moi block OOS 3 thang [C, C+3m) du doan boi model chi train < C - purge. Ghep -> chuoi leak-free.
Lua chon (Uni duyet 2026-07-02): expanding train, purge=72h, ca 4 horizon, params=ban single,
cutoff theo GMT+7 (khop WFO). Fold 1 phu them vung 2021 (IS-only). RUNBOOK buoc 2.

Env: TOOL1_GLOB OI_FILE LABEL_CSV MAP_CSV OUT_DIR [CUTOFFS OOS_MONTHS TZ_OFFSET_MS PURGE_STEPS
     SMOKE_FOLDS NEST SEED OI_TOL_MS]
"""
import os, gzip, glob, logging, struct
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fwf")

H_LIST = ["4h", "12h", "24h", "72h"]
H_STEPS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}
WIN = 0.06
GRID_MS = 15 * 60 * 1000

TOOL1_GLOB = os.environ["TOOL1_GLOB"]
OI_FILE = os.environ["OI_FILE"]
LABEL_CSV = os.environ["LABEL_CSV"]
MAP_CSV = os.environ["MAP_CSV"]
OUT_DIR = os.environ.get("OUT_DIR", ".")
os.makedirs(OUT_DIR, exist_ok=True)
OOS_MONTHS = int(os.environ.get("OOS_MONTHS", "3"))
TZ_OFFSET_MS = int(os.environ.get("TZ_OFFSET_MS", str(7 * 3600 * 1000)))
PURGE_MS = int(os.environ.get("PURGE_STEPS", "288")) * GRID_MS
SMOKE_FOLDS = int(os.environ.get("SMOKE_FOLDS", "0"))
NEST = int(os.environ.get("NEST", "400"))
SEED = int(os.environ.get("SEED", "42"))
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))

TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES


def read_bin(path_or_glob, dt, item, grid_filter=False):
    is_glob = any(c in path_or_glob for c in "*?[")
    files = sorted(glob.glob(path_or_glob, recursive=True)) if is_glob else [path_or_glob]
    assert files, f"khong tim thay file: {path_or_glob}"
    parts = []
    for fp in files:
        raw = open(fp, "rb").read()
        if fp.endswith(".gz"):
            raw = gzip.decompress(raw)
        assert len(raw) % item == 0, f"{fp}: {len(raw)} khong chia het {item}"
        a = np.frombuffer(raw, dtype=dt)
        if grid_filter:
            a = a[(a["ts"] % GRID_MS) == 0]
        parts.append(a)
    return np.concatenate(parts) if len(parts) > 1 else parts[0]


def build_features():
    a = read_bin(TOOL1_GLOB, TOOL1_DT, 170, grid_filter=True)
    t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        t[f"f{j}"] = F[:, j]
    t = t.sort_values("ts").reset_index(drop=True)
    log.info("Tool1: %d rows | %d symId | ts[%s..%s]", len(t), t.symId.nunique(),
             pd.to_datetime(t.ts.min(), unit="ms"), pd.to_datetime(t.ts.max(), unit="ms"))
    ao = read_bin(OI_FILE, OI_DT, 30, grid_filter=True)  # OI 5m cadence -> loc 15m grid (lossless cho merge tai moc 15m, cat 113M->38M chong OOM)
    o = pd.DataFrame({"ts": ao["ts"].astype(np.int64), "symId": ao["sym"].astype(np.int32)})
    O = np.asarray(ao["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        o[nm] = O[:, j]
    o = o.sort_values("ts").reset_index(drop=True)
    m = pd.read_csv(MAP_CSV)
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(m, on="symId", how="left").dropna(subset=["symbol"])
    log.info("Features: %d rows | %d symbol", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def load_labels():
    cols = ["tEpochMs", "symbol"] + [f"maxFav_{h}" for h in H_LIST] + [f"nBars_{h}" for h in H_LIST]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip")
    out = {}
    for h in H_LIST:
        need = H_STEPS[h]
        d = df[["tEpochMs", "symbol", f"maxFav_{h}", f"nBars_{h}"]].rename(
            columns={"tEpochMs": "ts", f"maxFav_{h}": "maxFav", f"nBars_{h}": "nBars"})
        d = d[(d["nBars"] >= need) & d["maxFav"].notna()].copy()
        d["y"] = (d["maxFav"] >= WIN).astype(np.int8)
        out[h] = d[["ts", "symbol", "y"]]
        log.info("Label %s: %d rows | base=%.4f", h, len(d), d["y"].mean())
    return out


def gen_cutoffs(ts_min, ts_max):
    env = os.environ.get("CUTOFFS", "").strip()
    if env:
        cs = []
        for x in env.split(","):
            x = x.strip()
            dt = pd.Timestamp(f"{x[0:4]}-{x[4:6]}-{x[6:8]}", tz="UTC")
            cs.append(int(dt.value // 1_000_000) - TZ_OFFSET_MS)
        return sorted(cs)
    start = pd.Timestamp(pd.to_datetime(ts_min + TZ_OFFSET_MS, unit="ms").strftime("%Y-%m-01"), tz="UTC")
    c = start + pd.DateOffset(months=12)
    cs = []
    while True:
        c_ms = int(c.value // 1_000_000) - TZ_OFFSET_MS
        oos_end = int((c + pd.DateOffset(months=OOS_MONTHS)).value // 1_000_000) - TZ_OFFSET_MS
        if oos_end > ts_max:
            break
        cs.append(c_ms)
        c = c + pd.DateOffset(months=OOS_MONTHS)
    return cs


def train_predict_fold(feat_df, labels, cutoff_ms, block_lo, block_hi, fidx):
    import xgboost as xgb
    oos = feat_df[(feat_df.ts >= block_lo) & (feat_df.ts < block_hi)]
    if len(oos) == 0:
        log.warning("fold %d: OOS block rong", fidx)
        return None
    key = oos[["ts", "symId"]].reset_index(drop=True)
    preds = {h: np.full(len(oos), np.nan, dtype=np.float32) for h in H_LIST}
    tr_cut = cutoff_ms - PURGE_MS
    tr_feat = feat_df[feat_df.ts < tr_cut]
    for h in H_LIST:
        tr = tr_feat.merge(labels[h], on=["symbol", "ts"], how="inner")
        if len(tr) < 5000 or tr.y.nunique() < 2:
            log.warning("fold %d %s: train it (%d) -> bo", fidx, h, len(tr))
            continue
        assert tr.ts.max() < cutoff_ms, f"LEAK fold {fidx} {h}"
        pos = tr.y.mean()
        clf = xgb.XGBClassifier(n_estimators=NEST, max_depth=5, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=SEED)
        clf.fit(tr[FEAT], tr.y, verbose=False)
        preds[h] = clf.predict_proba(oos[FEAT])[:, 1].astype(np.float32)
        log.info("fold %d %s: train %d (ts_max=%s<cutoff) pos=%.4f pred %d", fidx, h, len(tr),
                 pd.to_datetime(tr.ts.max(), unit="ms"), pos, len(oos))
    return key, preds


def write_bin(path, key, preds):
    ts = key["ts"].values
    sid = key["symId"].values
    p = [preds[h] for h in H_LIST]
    with open(path, "wb") as fo:
        for i in range(len(key)):
            fo.write(struct.pack(">qh4f", int(ts[i]), int(sid[i]),
                                 float(p[0][i]), float(p[1][i]), float(p[2][i]), float(p[3][i])))
    log.info("ghi %s: %d rec = %d bytes", path, len(key), len(key) * 26)


def main():
    feat_df = build_features()
    labels = load_labels()
    ts_min, ts_max = int(feat_df.ts.min()), int(feat_df.ts.max())
    cutoffs = gen_cutoffs(ts_min, ts_max)
    log.info("CUTOFFS (%d): %s", len(cutoffs),
             [str(pd.to_datetime(c + TZ_OFFSET_MS, unit="ms").date()) for c in cutoffs])
    if SMOKE_FOLDS > 0:
        cutoffs = cutoffs[:SMOKE_FOLDS]
        log.info("SMOKE: %d fold dau", SMOKE_FOLDS)
    for i, c in enumerate(cutoffs):
        block_lo = ts_min if i == 0 else c
        cdt = pd.to_datetime(c + TZ_OFFSET_MS, unit="ms").normalize()
        block_hi = int((cdt + pd.DateOffset(months=OOS_MONTHS)).value // 1_000_000) - TZ_OFFSET_MS
        r = train_predict_fold(feat_df, labels, c, block_lo, block_hi, i)
        if r is None:
            continue
        key, preds = r
        cdate = pd.to_datetime(c + TZ_OFFSET_MS, unit="ms").strftime("%Y%m%d")
        write_bin(os.path.join(OUT_DIR, f"predict_wf_{cdate}.bin"), key, preds)
    log.info("DONE -> %s", OUT_DIR)


if __name__ == "__main__":
    main()
