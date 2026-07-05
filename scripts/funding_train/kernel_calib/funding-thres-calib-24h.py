#!/usr/bin/env python3
"""
TASK-130c THRESHOLD CALIBRATION (Kaggle GPU) — đóng sổ tầng-1.
Mục tiêu: model mới dùng được theo semantics production (score=1−P(win@24h) ≤ maxThres → CHỌN)
và so hit_SEL táo-với-táo với production (hit_SEL 65.8%, maxThres 0.3212, đo per-fold TASK-128).
Pre-register:
- Train lại 3 seeds (42/43/44) với BEST PARAMS Optuna (hardcode từ metrics_24h_tuned.json commit 214216b)
  → deterministic tái lập models của kernel optuna. Ensemble P_win = mean.
- Quét ngưỡng maxThres trên VAL: bảng (thres → coverage%, hit_SEL, lift). Chọn 2 ứng viên TRÊN VAL:
  (a) SAME-COVERAGE: thres cho coverage VAL ≈ 35% (coverage production trên kỳ TEST, từ bảng TASK-128:
      2025Q4 39.6%, 2026Q1 30.2%); (b) MAX-HIT: thres max hit_SEL với coverage ≥ 10%.
- Áp 2 ứng viên lên TEST ĐÚNG 1 LẦN → bảng cuối. TEST không tham gia chọn ngưỡng.
"""
import os, glob, json, sys, traceback
import numpy as np

WORK = "/kaggle/working"
BEST = dict(max_depth=9, learning_rate=0.011522932326335892, subsample=0.6082711795022981,
            colsample_bytree=0.5023215589753468, min_child_weight=25.670064144686005,
            reg_alpha=0.0001276332154676552, reg_lambda=9.855514275376441)

def find1(pat):
    m = sorted(glob.glob(pat, recursive=True))
    assert m, "KHONG tim thay: " + pat
    return m[0]

def scan(scores, y, thresholds):
    # score = 1 - P(win); CHON khi score <= thres
    rows = []
    base = y.mean()
    for t in thresholds:
        sel = scores <= t
        cov = sel.mean()
        if sel.sum() < 200:
            rows.append((round(t,4), round(cov*100,2), None, None)); continue
        hit = y[sel].mean()
        rows.append((round(t,4), round(cov*100,2), round(hit,4), round(hit/base,3)))
    return rows, base

def main():
    ff_all = sorted(glob.glob("/kaggle/input/**/ff_*.bin", recursive=True))
    os.environ.update({
        "TOOL1_GLOB": os.path.dirname(ff_all[0]) + "/ff_*.bin",
        "OI_FILE": find1("/kaggle/input/**/oi_percoin_full.bin"),
        "LABEL_CSV": find1("/kaggle/input/**/funding_label.csv"),
        "MAP_CSV": find1("/kaggle/input/**/symbol_map.csv"),
        "OUT_DIR": WORK, "HORIZON": "24h", "TEST_MONTHS": "6", "VAL_MONTHS": "6",
    })
    train_py = find1("/kaggle/input/**/train_funding_selector.py")
    mod = {"__name__": "m", "__file__": train_py}
    exec(compile(open(train_py).read(), train_py, "exec"), mod)
    ds, feat = mod["build_dataset"]()
    tr, va, te = mod["time_split"](ds)
    assert tr.ts.max() < va.ts.min() and va.ts.max() < te.ts.min(), "LEAK split"
    import xgboost as xgb
    pos = tr.y.mean(); spw = (1-pos)/max(pos,1e-6)
    pv, pt = [], []
    for seed in (42,43,44):
        clf = xgb.XGBClassifier(tree_method="hist", device="cuda", eval_metric="auc", n_jobs=-1,
                                random_state=seed, scale_pos_weight=spw, n_estimators=2000,
                                early_stopping_rounds=50, **BEST)
        clf.fit(tr[feat], tr.y, eval_set=[(va[feat], va.y)], verbose=False)
        pv.append(clf.predict_proba(va[feat])[:,1]); pt.append(clf.predict_proba(te[feat])[:,1])
    sva = 1.0 - np.mean(pv, axis=0)   # score VAL
    ste = 1.0 - np.mean(pt, axis=0)   # score TEST
    yva, yte = va.y.values, te.y.values

    ths = np.round(np.arange(0.10, 0.66, 0.02), 4)
    rows_val, base_val = scan(sva, yva, ths)
    print("=== BANG QUET NGUONG (VAL, base=%.4f) ===" % base_val, flush=True)
    print("thres  cov%%  hit_SEL  lift", flush=True)
    for r in rows_val: print("  ".join(str(x) for x in r), flush=True)

    # chon 2 ung vien TREN VAL
    target_cov = 0.35
    cand_a = min((r for r in rows_val if r[2] is not None), key=lambda r: abs(r[1]/100 - target_cov))
    cand_b = max((r for r in rows_val if r[2] is not None and r[1] >= 10.0), key=lambda r: r[2])
    picks = {"same_coverage_35pct": cand_a[0], "max_hit_cov_ge10": cand_b[0], "production_thres": 0.3212}
    print("UNG VIEN (chon tren VAL):", picks, flush=True)

    out = {"picks_on_val": picks, "val_base": round(float(base_val),4), "scan_val": rows_val,
           "test_base": round(float(yte.mean()),4), "test_apply": {}}
    print("=== AP TEST (1 lan) base=%.4f ===" % yte.mean(), flush=True)
    for name, t in picks.items():
        sel = ste <= t
        cov = sel.mean(); hit = yte[sel].mean() if sel.sum() >= 200 else None
        out["test_apply"][name] = {"thres": t, "coverage_pct": round(cov*100,2),
                                    "hit_SEL": (round(float(hit),4) if hit is not None else None),
                                    "nSEL": int(sel.sum())}
        print(f"  {name}: thres={t} cov={cov*100:.2f}% hit_SEL={hit} nSEL={sel.sum()}", flush=True)
    out["baseline_production_TASK128"] = {"hit_SEL": 0.658, "maxThres": 0.3212,
        "note": "per-fold toan ky; per-quarter ky TEST: 2025Q4 hit .6644 cov 39.6%, 2026Q1 hit .6502 cov 30.2%"}
    json.dump(out, open(f"{WORK}/thres_calib_24h.json","w"), indent=2)
    print("CALIB_DONE", flush=True)

if __name__ == "__main__":
    try: main(); sys.exit(0)
    except Exception: traceback.print_exc(); sys.exit(1)
