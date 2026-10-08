#!/usr/bin/env python3
"""HO1 B3 — net015 (G015x26) predict-only 2026H1 bang model_f19_4h.json (cut20251231). Pre-reg 35d03784 §3.

Duong feature = y het g015_net_train.build_matrix (OI merge_asof backward 2h, symbol_map); file Tool1 chia quy UTC nen doc
ca file quy truoc de phu cua so fold +07; OI doc theo khoi [lo-2h, hi) (RAM thap); thu tu dong sort on dinh (ts, symId).
  G-B3: model_f18_4h.json (cung kernel GPU cut20251231) predict lai OOS [20251001,20260101) +07, so
        kg015x26_cut20251231/out/predict_wf_20251001.bin theo khoa (ts,sym): spearman 1,0 / max|d| <= 1,2e-7.
  2026: model_f19_4h.json -> predict_wf_20260101.bin [20260101,20260401) va predict_wf_20260401.bin [20260401,20260701) +07.
SEAL DONG: khong in/ghi thong ke gia tri du doan 2026 — chi dem, NaN, khoang ts, sha.
"""
import glob
import hashlib
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/pipeline"))
import g015_net_train as G  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho1net")
KG = "/home/ubuntu/kg015x26_cut20251231/g015x26-cut20251231-gpu/out"
F18, F18_SHA = KG + "/model_f18_4h.json", "56dd4a14a5f8f879add9e539d13b35ca1f5392662a78204cb0d0008aee19ca20"
F19, F19_SHA = KG + "/model_f19_4h.json", "83a5333df0f7b1271f90658e81b0e37f4e2b29e681b8d7a37a0526e2b855657d"
REF25 = KG + "/predict_wf_20251001.bin"
BLACK = {"b40586a63925c602dd191130d7eab76ded4f24e98c9bde23d959c76f204b08eb"}
OUT = "/home/ubuntu/claude_master/1003/ho1/net015_2026"
SCR = "/home/ubuntu/claude_master/1003/ho1/net015_scratch"
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])


def read_oi(lo, hi, step=10_000_000):
    """Doc OI theo khoi (khong memmap ca file) -> ban ghi ts in [lo, hi)."""
    n = os.path.getsize(G.OI_FILE) // G.OI_DT.itemsize
    parts = []
    for k in range(0, n, step):
        c = np.fromfile(G.OI_FILE, dtype=G.OI_DT, count=min(step, n - k), offset=k * G.OI_DT.itemsize)
        t = c["ts"].astype(np.int64)
        parts.append(c[(t >= lo) & (t < hi)].copy())
        del c, t
    return np.concatenate(parts)


def build_rows(patterns, lo_ts, hi_ts):
    """= build_matrix (Tool1 + OI merge_asof backward tol 2h + symbol_map) cho cac dong Tool1 ts in [lo_ts, hi_ts).
    OI chi can [ts-2h, ts] => gia tri y het chunk theo nam cua pipeline goc. Thu tu ra: sort on dinh (ts, symId)."""
    smap = pd.read_csv(G.MAP_CSV)
    aa = []
    for p in patterns:
        x = G.read_tool1(p, grid_ms=G.GRID_MS)
        xt = x["ts"].astype(np.int64)
        aa.append(x[(xt >= lo_ts) & (xt < hi_ts)].copy())
        del x, xt
    a = np.concatenate(aa) if len(aa) > 1 else aa[0]
    del aa
    aoc = read_oi(lo_ts - G.OI_TOL, hi_ts)
    t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32),
                      "ridx": np.arange(len(a), dtype=np.int64)})
    o = pd.DataFrame({"ts": aoc["ts"].astype(np.int64), "symId": aoc["sym"].astype(np.int32)})
    O = np.asarray(aoc["oi"], dtype=np.float32)
    for j, nm in enumerate(G.OI_NAMES):
        o[nm] = O[:, j]
    del aoc, O
    t = t.sort_values("ts").reset_index(drop=True)
    o = o.sort_values("ts").reset_index(drop=True)
    mg = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=G.OI_TOL)
    del t, o
    mg = mg.merge(smap, on="symId", how="left").dropna(subset=["symbol"])
    mg = mg.sort_values(["ts", "symId"], kind="stable").reset_index(drop=True)
    X = np.empty((len(mg), G.NF), dtype=np.float32)
    X[:, :40] = a["f"][mg["ridx"].to_numpy()]
    X[:, 40:] = mg[G.OI_NAMES].to_numpy(np.float32)
    ts, sym = mg["ts"].to_numpy(np.int64), mg["symId"].to_numpy(np.int32)
    info = dict(patterns=patterns, lo=lo_ts, hi=hi_ts, n_tool1_in=int(len(a)), n_merged=int(len(mg)),
                n_oi_nan_rows=int(np.isnan(X[:, 40:]).all(axis=1).sum()), ts_min=int(ts.min()), ts_max=int(ts.max()))
    log.info("rows %s", info)
    del a, mg
    return X, ts, sym, info


def predict(model_path, sha, X):
    import xgboost as xgb
    assert G.sha256(model_path) == sha and sha not in BLACK
    clf = xgb.XGBClassifier()
    clf.load_model(model_path)
    return clf.predict_proba(X)[:, 1].astype(np.float32)


def gate_b3():
    from scipy.stats import spearmanr
    lo, hi = G.ms("20251001"), G.ms("20260101")
    X, ts, sym, info = build_rows([os.path.join(G.T1_DIR, "features_20250701*"), os.path.join(G.T1_DIR, "features_20251001*")], lo, hi)
    m = (ts >= lo) & (ts < hi)
    p = predict(F18, F18_SHA, X[m])
    k = ts[m] * 10000 + sym[m]
    r = np.fromfile(REF25, dtype=DT)
    kr = r["ts"].astype(np.int64) * 10000 + r["sym"].astype(np.int64)
    assert len(np.unique(k)) == len(k) and len(np.unique(kr)) == len(kr)
    o, orr = np.argsort(k), np.argsort(kr)
    same = len(k) == len(kr) and np.array_equal(k[o], kr[orr])
    g = dict(chunk=info, n_new=int(len(k)), n_ref=int(len(kr)), keys_equal=bool(same))
    if same:
        a, b = p[o].astype(np.float64), r["p0"].astype(np.float64)[orr]
        g.update(spearman=float(spearmanr(a, b).correlation), max_abs=float(np.abs(a - b).max()),
                 nan_new=int(np.isnan(a).sum()))
        g["pass"] = bool(g["spearman"] >= 0.99999 and g["max_abs"] <= 1.2e-7)
    else:
        g["pass"] = False
    log.info("G-B3: %s", g)
    return g


def run_2026():
    X, ts, sym, info = build_rows([os.path.join(G.T1_DIR, "features_20251001*"), os.path.join(G.T1_DIR, "features_2026*")],
                                   G.ms("20260101"), G.ms("20260701"))
    outs = {}
    for c0, c1 in (("20260101", "20260401"), ("20260401", "20260701")):
        lo, hi = G.ms(c0), G.ms(c1)
        m = (ts >= lo) & (ts < hi)
        p = predict(F19, F19_SHA, X[m])
        path = os.path.join(OUT, "predict_wf_%s.bin" % c0)
        G.write_bin(path, ts[m], sym[m], p)
        tq = ts[m]
        outs[c0] = dict(path=path, n=int(m.sum()), nan=int(np.isnan(p).sum()), ts_min=int(tq.min()), ts_max=int(tq.max()),
                        span_days=int((tq.max() - tq.min()) // 86400000), lo=lo, hi=hi, sha256=G.sha256(path),
                        bytes=os.path.getsize(path))
        assert outs[c0]["sha256"] not in BLACK and outs[c0]["span_days"] <= 100 and lo <= tq.min() and tq.max() < hi
        log.info("2026 %s: %s", c0, {k: v for k, v in outs[c0].items()})
    return dict(chunk=info, files=outs)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(SCR, exist_ok=True)
    import tool1_col
    t1 = {os.path.basename(f): tool1_col.meta(f) for f in sorted(glob.glob(os.path.join(G.T1_DIR, "features_202[56]*")))}
    log.info("Tool1 meta: %s", t1)
    res = dict(prereg="35d03784", tool1_meta=t1, model_f19_sha256=F19_SHA, model_f18_sha256=F18_SHA)
    res["G_B3"] = gate_b3()
    json.dump(res, open(OUT + "/manifest_net015_2026.json", "w"), indent=1, default=str)
    if not res["G_B3"]["pass"]:
        log.error("G-B3 FAIL -> DUNG, khong predict 2026")
        sys.exit(2)
    res["pred_2026"] = run_2026()
    json.dump(res, open(OUT + "/manifest_net015_2026.json", "w"), indent=1, default=str)
    log.info("XONG B3")


if __name__ == "__main__":
    main()
