"""X1 S1 — TRAIN + LUU MODEL fold CUOI (cutoff 20251001) + CONG doi chung.

`s1_rank.py`/`x1_s1_rank.py` train roi predict ngay trong vong lap, KHONG luu model
(`docs/experiment/L1_SHADOW_C3.md` muc 3b = blocker B1). Script nay tai lap DUNG fold cuoi cua X1
(cung ledger, cung feature, cung sieu tham so, cung purge 72h), roi:
  1. `booster.save_model(<out>/s1a2x1_cut20251001.json)`
  2. convert ONNX (`onnxmltools`) -> `<out>/s1a2x1_cut20251001.onnx`
  3. CONG: predict lai OOS 2025Q4 bang model da luu (JSON qua xgboost, va ONNX qua
     onnxruntime) roi so voi cot `score` cua `ledger/pred_s1a2x1.parquet` tren cung
     (ts,sym). Yeu cau spearman = 1.000000 va max|delta| <= 1e-6.

Chay: env X1_LNAME=cand_dev_x1 X1_FEAT=/home/ubuntu/featv2/feat_v2_x1.parquet \
      python3 -u x1_s1_save_model.py <out_dir>
"""
import logging as _logging, sys as _sys
_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
LOG = _logging.getLogger(__name__)


def _p(*a):
    LOG.info(" ".join(str(x) for x in a))


import hashlib
import json
import os
import time

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr


def log(*a):
    _p(time.strftime("%H:%M:%S"), *a)


H = 3600000
TZ = 7 * H
PURGE = 72 * H
LED = "/home/ubuntu/ledger"
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
        "ret_14d", "ls_global", "rk_oi_delta24h"]
LNAME = os.environ.get("X1_LNAME", "cand_dev_x1")
FEAT = os.environ.get("X1_FEAT", "/home/ubuntu/featv2/feat_v2_x1.parquet")
PRED = os.environ.get("X1_PRED", f"{LED}/pred_s1a2x1.parquet")
CUT_DAY = os.environ.get("X1_CUT", "20251001")
OUT = _sys.argv[1] if len(_sys.argv) > 1 else "/home/ubuntu/s1_model"
os.makedirs(OUT, exist_ok=True)
TAG = f"s1a2x1_cut{CUT_DAY}"


def build_frame():
    """Tai lap DUNG cach `x1_s1_rank.py` dung `D` (chi doc cot can -> tiet kiem RAM;
    cac cot khac KHONG vao model nen gia tri KEEP khong doi)."""
    D = pd.read_parquet(f"{LED}/{LNAME}.parquet", columns=["ts", "sym", "g1lite"])
    D = D[D.g1lite.notna()].copy()
    log("pool", D.shape)
    D["med"] = D.groupby("ts").g1lite.transform("median")
    D["rel"] = D.g1lite - D.med
    D["rk"] = D.groupby("ts").rel.rank(pct=True, method="first")
    D["rel5"] = np.minimum((D.rk * 5).astype(int), 4)
    D["ts_h"] = (D.ts // H) * H
    F = pd.read_parquet(FEAT, columns=["ts", "sym"] + KEEP)
    D = D.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    log("join feat: co vol_7d", D.vol_7d.notna().mean().round(3))
    return D


def main():
    D = build_frame()
    c = int(pd.Timestamp(f"{CUT_DAY[:4]}-{CUT_DAY[4:6]}-{CUT_DAY[6:]}").value // 1e6) - TZ
    hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
    tr = D[D.ts < c - PURGE].sort_values("ts")
    oos = D[(D.ts >= c) & (D.ts < hi)].sort_values("ts")
    assert tr.ts.max() < c, "LEAK"
    log(f"fold cutoff {CUT_DAY}: train {len(tr)} (den {pd.to_datetime(tr.ts.max(), unit='ms')}) "
        f"oos {len(oos)} ticks {oos.ts.nunique()}")
    m = xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4, learning_rate=0.05,
                      subsample=0.8, colsample_bytree=0.8, min_child_weight=50, n_jobs=4,
                      tree_method="hist", random_state=42, lambdarank_pair_method="topk",
                      lambdarank_num_pair_per_sample=8)
    jpath = f"{OUT}/{TAG}.json"
    if os.environ.get("X1_REUSE_JSON") == "1" and os.path.exists(jpath):
        m.load_model(jpath)
        log("REUSE model da luu", jpath, os.path.getsize(jpath), "B")
    else:
        t0 = time.time()
        m.fit(tr[KEEP], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
        log(f"fit xong {time.time() - t0:.0f}s")
        m.get_booster().save_model(jpath)
        log("saved", jpath, os.path.getsize(jpath), "B")

    p_mem = m.predict(oos[KEEP])
    ref = pd.read_parquet(PRED)
    ref = ref[(ref.ts >= c) & (ref.ts < hi)][["ts", "sym", "score"]]
    O = oos[["ts", "sym"]].copy()
    O["score_mem"] = -p_mem

    # --- JSON reload
    b2 = xgb.Booster()
    b2.load_model(jpath)
    dm = xgb.DMatrix(oos[KEEP].to_numpy(dtype=np.float32), feature_names=list(KEEP))
    O["score_json"] = -b2.predict(dm)

    # --- ONNX
    onnx_ok, opath = False, f"{OUT}/{TAG}.onnx"
    try:
        # onnxmltools 1.16 KHONG co converter san cho XGBRanker ("No proper operator name
        # found for XGBRanker") -> dang ky no dung converter/shape-calculator cua XGBRegressor:
        # ca hai deu la ensemble hoi quy tra 1 so thuc, chi khac ham muc tieu luc TRAIN.
        from onnxmltools.convert.xgboost.operator_converters.XGBoost import convert_xgboost as _conv
        from skl2onnx import convert_sklearn, update_registered_converter
        from skl2onnx.common.data_types import FloatTensorType
        from skl2onnx.common.shape_calculator import calculate_linear_regressor_output_shapes
        update_registered_converter(xgb.XGBRanker, "XGBoostXGBRanker",
                                    calculate_linear_regressor_output_shapes, _conv)
        # onnxmltools doi ten feature theo mau 'f%d'; model train tu DataFrame nen dang giu ten
        # that. Doi ten TRONG BO NHO (sau khi da predict xong p_mem) — file JSON tren dia GIU
        # NGUYEN ten that; input ONNX la VI TRI theo S1FeatureLive.FEATURE_ORDER.
        m.get_booster().feature_names = [f"f{i}" for i in range(len(KEEP))]
        onx = convert_sklearn(m, initial_types=[("input", FloatTensorType([None, len(KEEP)]))],
                              target_opset={"": 15, "ai.onnx.ml": 2})
        with open(opath, "wb") as f:
            f.write(onx.SerializeToString())
        onnx_ok = True
        log("saved", opath, os.path.getsize(opath), "B")
    except Exception as e:
        _p("ONNX convert FAIL:", type(e).__name__, str(e)[:300])
    if onnx_ok:
        import onnxruntime as ort
        s = ort.InferenceSession(opath, providers=["CPUExecutionProvider"])
        xx = oos[KEEP].to_numpy(dtype=np.float32)
        outs = []
        for i in range(0, len(xx), 200000):
            outs.append(np.asarray(s.run(None, {"input": xx[i:i + 200000]})[0]).ravel())
        O["score_onnx"] = -np.concatenate(outs)

    M = ref.merge(O, on=["ts", "sym"], how="inner")
    _p(f"\nghep cap voi {PRED}: {len(M)}/{len(ref)} dong ref")
    rows = []
    for col in [c2 for c2 in ("score_mem", "score_json", "score_onnx") if c2 in M.columns]:
        a = M.score.to_numpy(np.float64)
        b = M[col].to_numpy(np.float64)
        ok = ~(np.isnan(a) | np.isnan(b))
        sp = spearmanr(a[ok], b[ok]).correlation
        d = np.abs(a[ok] - b[ok])
        rows.append((col, int(ok.sum()), sp, float(d.max()), float(np.median(d))))
    T = pd.DataFrame(rows, columns=["nguon", "n", "spearman", "max_abs_d", "med_abs_d"])
    _p(T.to_string(index=False, float_format=lambda x: f"{x:.9g}"))
    passed = bool((T.spearman >= 1.0 - 1e-9).all() and (T.max_abs_d <= 1e-6).all())
    _p(f"CONG MODEL (spearman = 1.000000 & max|d| <= 1e-6): {'PASS' if passed else 'FAIL'}")

    # CONG CHUC NANG: selector chi dung THU HANG (top-K). Do ty le tick ma tap top-8 GIONG HET
    # tap top-8 cua `pred_s1a2x1.parquet`. Day moi la thu quyet dinh lenh vao, khong phai |delta|.
    topk = {}
    for col in [c2 for c2 in ("score_json", "score_onnx") if c2 in M.columns]:
        same = 0
        tot = 0
        for _, g in M.groupby("ts"):
            if len(g) < 8:
                continue
            tot += 1
            a = set(g.nsmallest(8, "score").sym)
            b = set(g.nsmallest(8, col).sym)
            if a == b:
                same += 1
        topk[col] = (same, tot, 100.0 * same / max(tot, 1))
        _p(f"top-8 trung tuyet doi ({col}): {same}/{tot} tick = {100.0 * same / max(tot, 1):.4f}%")
    passed_topk = all(v[0] == v[1] for v in topk.values())
    _p(f"CONG TOP-K (tap top-8 trung 100% tick): {'PASS' if passed_topk else 'FAIL'}")

    man = {
        "tag": TAG, "cutoff": CUT_DAY, "train_rows": int(len(tr)),
        "train_ts_max": int(tr.ts.max()), "purge_ms": PURGE,
        "oos_rows": int(len(oos)), "features": KEEP,
        "ledger": f"{LED}/{LNAME}.parquet", "feat": FEAT, "ref_pred": PRED,
        "xgboost": xgb.__version__,
        "sha256_json": hashlib.sha256(open(jpath, "rb").read()).hexdigest(),
        "sha256_onnx": hashlib.sha256(open(opath, "rb").read()).hexdigest() if onnx_ok else None,
        "gate": T.to_dict("records"), "gate_pass": passed,
        "topk8": topk, "topk8_pass": passed_topk,
    }
    json.dump(man, open(f"{OUT}/{TAG}.manifest.json", "w"), indent=1)
    _p("manifest ->", f"{OUT}/{TAG}.manifest.json")
    _sys.exit(0 if (passed and passed_topk) else 3)


if __name__ == "__main__":
    main()
