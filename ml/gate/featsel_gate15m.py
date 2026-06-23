#!/usr/bin/env python3
"""
TASK-043 Bước C — Feature selection LẶP VÒNG tìm bộ feature tốt nhất cho gate 15m.

CHỈ dùng feature ĐÃ XUẤT trong CSV (không thêm feature ngoài) — cắt tỉa.
Nhãn = label_oldbasket (thắng bước B: IC 0.469 vs selector 0.459).
Đo = purged time-series CV 5-fold, embargo 1 mốc. Metric chính = IC mean (Spearman), phụ = lift top-10%@+1%.

Chiến lược (chạy tuần tự trên Oracle - dataset nhỏ, mỗi train ~vài giây):
  1. BASELINE: tất cả feature.
  2. DROP-WEAK: bỏ feature |IC đơn biến| < ngưỡng (quét nhiều ngưỡng).
  3. BACKWARD: lần lượt bỏ từng feature, giữ bỏ nếu IC CV không giảm (greedy elimination).
  4. FORWARD: bắt đầu từ top-k feature mạnh, thêm dần.
  5. TOP-K: chỉ giữ k feature |IC| cao nhất (quét k).
In bảng so sánh + lưu bộ feature tốt nhất ra JSON.

Env: DATA, OUT (json), QUICK (1=chỉ baseline+drop-weak+topk, bỏ backward chậm)
"""
import os, glob, json, itertools
import numpy as np, pandas as pd, xgboost as xgb
from scipy.stats import spearmanr

DATA = os.environ.get("DATA", os.path.expanduser("~/claudedata/gate15m_v2_full.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/claudedata/gate15m_v2_featsel.json"))
LABEL = os.environ.get("LABEL", "label_oldbasket")
QUICK = os.environ.get("QUICK", "0") == "1"
FOLDS, EMBARGO = 5, 1

df = pd.read_csv(sorted(glob.glob(DATA))[0]).sort_values("timestamp").reset_index(drop=True)
DROP = ["timestamp","volatilityRegime","label_oldbasket","label_selector","nBasketOld","nBasketSel"]
ALL_FEATS = [c for c in df.columns if c not in DROP and df[c].dtype != object]
y_full = df[LABEL].values
N = len(df); sz = N // FOLDS
print(f"rows={N} | {len(ALL_FEATS)} feature | label={LABEL}")

PARAMS = dict(objective="reg:squarederror", max_depth=4, eta=0.05, subsample=0.8,
              colsample_bytree=0.8, min_child_weight=10, eval_metric="rmse", seed=42)
NROUND = 150

# precompute fold indices (cùng split cho mọi cấu hình -> so công bằng)
FOLDS_IDX = []
for k in range(FOLDS):
    lo, hi = k*sz, (N if k==FOLDS-1 else (k+1)*sz)
    te = np.arange(lo, hi)
    mask = np.ones(N, bool); mask[max(0,lo-EMBARGO):min(N,hi+EMBARGO)] = False
    FOLDS_IDX.append((np.where(mask)[0], te))

def eval_feats(feats):
    """purged CV -> (ic_mean, lift_mean). Cache theo frozenset."""
    Xall = df[feats].values
    ics, lifts = [], []
    for tr, te in FOLDS_IDX:
        if len(te) < 50: continue
        dtr = xgb.DMatrix(Xall[tr], label=y_full[tr], missing=np.nan)
        dte = xgb.DMatrix(Xall[te], label=y_full[te], missing=np.nan)
        bst = xgb.train(PARAMS, dtr, num_boost_round=NROUND, verbose_eval=False)
        pred = bst.predict(dte)
        ic = spearmanr(pred, y_full[te]).correlation
        thr = np.percentile(pred, 90); sel = pred >= thr
        base = (y_full[te] > 0.01).mean()
        lift = ((y_full[te][sel] > 0.01).mean()/base) if base > 0 else 0
        ics.append(ic); lifts.append(lift)
    return float(np.mean(ics)), float(np.mean(lifts))

# univariate IC để xếp hạng
uic = []
for c in ALL_FEATS:
    v = spearmanr(df[c].values, y_full).correlation
    uic.append((c, 0 if np.isnan(v) else abs(v)))
uic.sort(key=lambda x:-x[1])
ranked = [c for c,_ in uic]

results = {}
def record(name, feats):
    ic, lift = eval_feats(feats)
    results[name] = dict(ic=round(ic,4), lift=round(lift,3), nfeat=len(feats), feats=feats)
    print(f"[{name:22}] nfeat={len(feats):2} IC={ic:.4f} lift={lift:.2f}x")
    return ic

# 1. BASELINE
base_ic = record("BASELINE_all", ALL_FEATS)

# 2. DROP-WEAK theo nguong |IC| don bien
for thr in [0.01, 0.02, 0.05, 0.10]:
    keep = [c for c,v in uic if v >= thr]
    if len(keep) >= 3 and len(keep) < len(ALL_FEATS):
        record(f"DROPWEAK_ic>={thr}", keep)

# 3. TOP-K feature manh nhat
for k in [5, 8, 10, 12, 15, 20]:
    if k < len(ranked):
        record(f"TOPK_{k}", ranked[:k])

# 4. BACKWARD greedy elimination (bo neu IC khong giam qua eps) — chi khi !QUICK
if not QUICK:
    cur = list(ALL_FEATS); cur_ic,_ = eval_feats(cur)
    improved = True; rounds = 0
    while improved and len(cur) > 3 and rounds < 25:
        improved = False; rounds += 1
        worst_drop, worst_ic = None, cur_ic
        for f in list(cur):
            trial = [x for x in cur if x != f]
            ic,_ = eval_feats(trial)
            if ic >= worst_ic - 1e-4:   # bo f neu IC khong giam (>= cur - eps)
                if ic >= worst_ic: worst_ic, worst_drop = ic, f
        if worst_drop is not None:
            cur.remove(worst_drop); cur_ic = worst_ic; improved = True
    record("BACKWARD_greedy", cur)

# chon best theo IC (tie-break lift cao, nfeat it)
best = max(results.items(), key=lambda kv: (kv[1]["ic"], kv[1]["lift"], -kv[1]["nfeat"]))
print(f"\n=== BEST: {best[0]} | IC={best[1]['ic']} lift={best[1]['lift']} nfeat={best[1]['nfeat']} ===")
print(f"    feats: {best[1]['feats']}")
print(f"    vs BASELINE IC={results['BASELINE_all']['ic']} (Δ={best[1]['ic']-results['BASELINE_all']['ic']:+.4f})")
out = dict(label=LABEL, baseline_ic=results["BASELINE_all"]["ic"],
           best_config=best[0], best=best[1], all_results=results,
           univariate_ic=[(c,round(v,4)) for c,v in uic])
json.dump(out, open(OUT,"w"), indent=2)
print(f"saved -> {OUT}")
