#!/usr/bin/env python3
"""HO1 B2 — gate p15 8 seed cut 2026-01-01 (+07) cho holdout 2026H1. Pre-reg docs/prereg/PREREG_HOLDOUT2026H1.md (35d03784).

Recipe = train_gate_fold.py / GA.retrain (XGBRegressor d4/n150/lr.05/sub.8/col.8/mcw10/n_jobs4, V3FULL, label_oldbasket),
chi doi random_state. Mep train CHAT: ts < SEAL - 15' (SEAL = 2026-01-01 00:00 +07). Doan 2026: loader CHI timestamp + 33 feat.
pred.bin moi = ban ghi DEV (ts < SEAL, NGUYEN byte pred DEV seed do) + ban ghi 2026H1 (ts store, p15 moi, risk 0f = fallback
WFOGateRunner). SEAL DONG: KHONG in/ghi thong ke gia tri p15 2026 — chi dem, NaN, md5.
Usage: python3 ho1_gate_build.py [--seeds 42,7,...]
"""
import argparse
import hashlib
import json
import logging
import os
import struct
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import gate_ablation_driver as GA  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho1gate")

D = "/home/ubuntu/claude_master/1003/ho1/gate"
TZ = "Asia/Ho_Chi_Minh"
SEAL = pd.Timestamp("2026-01-01", tz=TZ).value // 10**6
END = pd.Timestamp("2026-07-01", tz=TZ).value // 10**6
PURGE_MS = 15 * 60_000
TR_CUT = SEAL - PURGE_MS
Q4 = pd.Timestamp("2025-10-01", tz=TZ).value // 10**6
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
GSB = "/home/ubuntu/claude_master/1004/gsb"
DEV_PRED = {42: ("/home/ubuntu/wfo_ds_x1_2021/pred.bin", "5dd6bb4c3f98d89d58770005c0001526"),
            7: ("/home/ubuntu/claude_master/1004/gabl/pred_SEED7/pred.bin", "b737fb6d64d198c14654ea9c92510b36")}
for _s in [13, 21, 99, 123, 777, 2024]:
    DEV_PRED[_s] = (GSB + "/pred_S%d/pred.bin" % _s, json.load(open(GSB + "/pred_S%d/meta.json" % _s))["md5"])
REF_ONNX = "/home/ubuntu/claude_master/1002/deploy242/model/Model_Regressor_Return15M.onnx"
REF_SHA = "d37969eefa93bf93865cd3de78618a4a5b899b6c22e5a06529e30c0c8aeab915"
BLACK_SHA = {"d19fc8cddd9fb11778653e4b108bb52da92ea168117efac4a407c18c0f260474",
             "9ba5b0b87b6609e0af232a7eb8f56476af1ef268bb12ff2ea978e3bfb3ae1ca9",
             "4cc62c14f95fc74aa9f2cd7c2794a30291b0fdabf0dfceec81ae1edda162fdae"}
REC = np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def md5b(b):
    return hashlib.md5(b).hexdigest()


def year7(ts):
    return pd.to_datetime(ts, unit="ms", utc=True).tz_convert(TZ).year


def load_dev():
    """Store < SEAL: 33 feat + label_oldbasket (y het GA.load_store)."""
    assert GA.md5f(GA.STORE) == GA.STORE_MD5, "store md5"
    df = GA.load_store(GA.V3FULL + ["label_oldbasket"])
    assert df["timestamp"].max() < SEAL
    return df


def load_2026():
    """Store 2026H1: CHI timestamp + 33 cot V3FULL (khong doc cot nhan)."""
    use = ["timestamp"] + GA.V3FULL
    assert not any(c.startswith("label") for c in use)
    df = pd.read_csv(GA.STORE, usecols=use, dtype={c: np.float32 for c in GA.V3FULL})
    df["timestamp"] = df["timestamp"].astype(np.int64)
    df = df[(df["timestamp"] >= SEAL) & (df["timestamp"] < END)].sort_values("timestamp").reset_index(drop=True)
    assert df["timestamp"].is_unique
    nan = {c: int(df[c].isna().sum()) for c in GA.V3FULL if df[c].isna().any()}
    info = dict(n=int(len(df)), ts_first=str(pd.to_datetime(df.timestamp.iloc[0], unit="ms", utc=True).tz_convert(TZ)),
                ts_last=str(pd.to_datetime(df.timestamp.iloc[-1], unit="ms", utc=True).tz_convert(TZ)),
                n_minutes_window=int((END - SEAL) // 60_000), nan_by_feat=nan)
    log.info("STORE 2026H1 (chi feat): %s", info)
    return df, info


def ref_q4(Xq4):
    import onnxruntime as ort
    assert sha256f(REF_ONNX) == REF_SHA
    s = ort.InferenceSession(REF_ONNX, providers=["CPUExecutionProvider"])
    return s.run(None, {s.get_inputs()[0].name: Xq4})[0].reshape(-1).astype(np.float32)


def train(seed, dev):
    from xgboost import XGBRegressor
    sts = dev["timestamp"].to_numpy()
    y = dev["label_oldbasket"].to_numpy(np.float32)
    m = (sts < TR_CUT) & np.isfinite(y)
    tmax = int(sts[m].max())
    assert tmax < TR_CUT <= SEAL, "train ts vuot mep"
    yrs = np.unique(year7(sts[m]))
    assert set(int(v) for v in yrs) <= {2021, 2022, 2023, 2024, 2025}, ("nam nhan train", yrs)
    model = XGBRegressor(objective="reg:squarederror", max_depth=4, n_estimators=150, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8, min_child_weight=10, random_state=seed, n_jobs=4)
    model.fit(dev[GA.V3FULL].to_numpy(np.float32)[m], y[m])
    os.makedirs(D, exist_ok=True)
    mp = D + "/gate_s%d_cut20260101p15.json" % seed
    model.save_model(mp)
    sha = sha256f(mp)
    assert sha not in BLACK_SHA
    meta = dict(seed=seed, n_train=int(m.sum()), train_ts_min=str(pd.to_datetime(int(sts[m].min()), unit="ms", utc=True).tz_convert(TZ)),
                train_ts_max=str(pd.to_datetime(tmax, unit="ms", utc=True).tz_convert(TZ)), train_ts_max_ms=tmax,
                tr_cut_ms=TR_CUT, label_years=[int(v) for v in yrs], model=mp, model_sha256=sha)
    log.info("TRAIN seed %d: %s", seed, meta)
    return model, meta


def build_pred(seed, p26, ts26, ts_ref):
    src, want = DEV_PRED[seed]
    raw = open(src, "rb").read()
    assert md5b(raw) == want, ("md5 pred DEV", seed)
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + n * 16], dtype=REC)
    assert 4 + 16 * n == len(raw)
    ts = a["ts"].astype(np.int64)
    n_dev = int(np.searchsorted(ts, SEAL))
    assert (ts[:n_dev] < SEAL).all() and (ts[n_dev:] >= SEAL).all()
    if ts_ref is not None:
        assert np.array_equal(ts[:n_dev], ts_ref), "ts DEV khac giua cac seed"
    dev_bytes = raw[4:4 + 16 * n_dev]
    b = np.zeros(len(ts26), dtype=REC)
    b["ts"] = ts26
    b["p15"] = p26.astype(">f4")
    b["risk"] = np.float32(0.0)
    assert ts26[0] > ts[n_dev - 1] and (np.diff(ts26) > 0).all()
    out_dir = D + "/pred_s%d" % seed
    os.makedirs(out_dir, exist_ok=True)
    p = out_dir + "/pred.bin"
    with open(p, "wb") as f:
        f.write(struct.pack(">i", n_dev + len(ts26)))
        f.write(dev_bytes)
        f.write(b.tobytes())
    chk = open(p, "rb").read()
    assert md5b(chk[4:4 + 16 * n_dev]) == md5b(dev_bytes)
    meta = dict(seed=seed, src_dev=src, src_dev_md5=want, n_src=n, n_src_ge_seal_dropped=n - n_dev, n_dev=n_dev,
                md5_dev_records=md5b(dev_bytes), n_2026=int(len(ts26)), n_total=n_dev + int(len(ts26)),
                nan_p15_2026=int((~np.isfinite(p26)).sum()), md5=md5b(chk), bytes=len(chk), path=p)
    log.info("PRED seed %d: %s", seed, {k: v for k, v in meta.items() if k != "path"})
    return meta, ts[:n_dev]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default=",".join(str(s) for s in SEEDS))
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]
    dev = load_dev()
    d26, info26 = load_2026()
    X26 = d26[GA.V3FULL].to_numpy(np.float32)
    ts26 = d26["timestamp"].to_numpy(np.int64)
    out = dict(prereg="35d03784", seal_ms=SEAL, tr_cut_ms=TR_CUT, store=GA.STORE, store_md5=GA.STORE_MD5,
               store_2026=info26, seeds={})
    ts_ref = None
    for s in seeds:
        model, mmeta = train(s, dev)
        if s == 42:
            from scipy.stats import pearsonr, spearmanr
            q = (dev["timestamp"].to_numpy() >= Q4)
            Xq = dev[GA.V3FULL].to_numpy(np.float32)[q]
            mine, ref = model.predict(Xq).astype(np.float32), ref_q4(Xq)
            g = dict(n=int(q.sum()), pearson=float(pearsonr(mine, ref)[0]), spearman=float(spearmanr(mine, ref).correlation))
            g["pass"] = bool(g["pearson"] >= 0.99 and g["spearman"] >= 0.99)
            out["G_B2a"] = g
            log.info("G-B2a seed42 vs d37969ee tren 2025Q4: %s", g)
            assert g["pass"], "G-B2a FAIL -> DUNG"
        p26 = model.predict(X26).astype(np.float32)
        assert np.isfinite(p26).all(), "p15 2026 co NaN"
        pmeta, ts_ref = build_pred(s, p26, ts26, ts_ref)
        out["seeds"][str(s)] = dict(train=mmeta, pred=pmeta)
        json.dump(out, open(D + "/manifest_gate.json", "w"), indent=1)
    log.info("XONG B2: %d seed", len(out["seeds"]))


if __name__ == "__main__":
    main()
