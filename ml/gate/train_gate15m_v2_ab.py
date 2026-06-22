#!/usr/bin/env python3
"""
TASK-043 Bước B — Đo IC nhanh: model 15m dự báo nhãn nào tốt hơn (oldbasket vs selector).

Pre-register (KHÓA trước khi nhìn kết quả, từ report 043):
  PASS giả thuyết "đổi tập selector tốt hơn" KHI: IC de-overlap nhãn-selector >= IC nhãn-oldbasket
  RÕ RỆT (chênh >= +0.03 tuyệt đối) HOẶC lift top-decile +1% cao hơn rõ. Không hơn -> giả thuyết SAI.

Train XGBoost regression NHỎ (depth 4, ít cây - right-size cho WFO sau), purged time-series CV
(embargo 15m = 1 mốc, vì de-overlap đã 15m nên embargo nhẹ; OOS theo fold thời gian).
So 2 nhãn trên CÙNG feature + CÙNG split -> chênh lệch IC là do NHÃN, không do gì khác.

Env: DATA (mac dinh ~/claudedata/gate15m_v2_full.csv), OUT (mac dinh ~/claudedata/gate15m_v2_ic.json)
"""
import os, glob, json
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

DATA = os.environ.get("DATA", os.path.expanduser("~/claudedata/gate15m_v2_full.csv"))
OUT = os.environ.get("OUT", os.path.expanduser("~/claudedata/gate15m_v2_ic.json"))
FOLDS = 5
EMBARGO = 1  # mốc (de-overlap đã 15m)

df = pd.read_csv(sorted(glob.glob(DATA))[0]).sort_values("timestamp").reset_index(drop=True)
print(f"rows={len(df)} | {pd.to_datetime(df.timestamp.min(),unit='ms')} -> {pd.to_datetime(df.timestamp.max(),unit='ms')}")

# feature = tat ca tru meta/label. volatilityRegime la string -> bo (hoac one-hot; bo cho gon)
DROP = ["timestamp","volatilityRegime","label_oldbasket","label_selector","nBasketOld","nBasketSel"]
FEATS = [c for c in df.columns if c not in DROP and df[c].dtype != object]
print(f"{len(FEATS)} feature")

PARAMS = dict(objective="reg:squarederror", max_depth=4, eta=0.05, subsample=0.8,
              colsample_bytree=0.8, min_child_weight=10, eval_metric="rmse", seed=42)

def cv_ic(label_col):
    """purged time-series CV, tra (IC trung binh, lift top-decile +1% trung binh, list IC moi fold)."""
    y = df[label_col].values
    X = df[FEATS].values
    N = len(df); sz = N // FOLDS
    ics, lifts = [], []
    for k in range(FOLDS):
        lo, hi = k*sz, (N if k==FOLDS-1 else (k+1)*sz)
        te = np.arange(lo, hi)
        mask = np.ones(N, bool); mask[max(0,lo-EMBARGO):min(N,hi+EMBARGO)] = False
        tr = np.where(mask)[0]
        if len(te) < 50: continue
        dtr = xgb.DMatrix(X[tr], label=y[tr], feature_names=FEATS, missing=np.nan)
        dte = xgb.DMatrix(X[te], label=y[te], feature_names=FEATS, missing=np.nan)
        bst = xgb.train(PARAMS, dtr, num_boost_round=150, verbose_eval=False)
        pred = bst.predict(dte)
        ic = spearmanr(pred, y[te]).correlation
        # lift top-decile: trong 10% pred cao nhat, ty le realized > 1% vs base
        thr = np.percentile(pred, 90); sel = pred >= thr
        base = (y[te] > 0.01).mean()
        lift = ((y[te][sel] > 0.01).mean() / base) if base > 0 else 0
        ics.append(ic); lifts.append(lift)
    return float(np.mean(ics)), float(np.mean(lifts)), [round(x,4) for x in ics]

res = {}
for lab in ["label_oldbasket","label_selector"]:
    ic, lift, fold_ics = cv_ic(lab)
    res[lab] = dict(ic_mean=ic, lift_top10_1pct=lift, fold_ics=fold_ics)
    print(f"\n{lab}: IC_mean={ic:.4f} | lift_top10%@+1%={lift:.2f}x | folds={fold_ics}")

d_ic = res["label_selector"]["ic_mean"] - res["label_oldbasket"]["ic_mean"]
d_lift = res["label_selector"]["lift_top10_1pct"] - res["label_oldbasket"]["lift_top10_1pct"]
verdict = "PASS (selector tot hon ro ret)" if (d_ic >= 0.03 or d_lift >= 0.3) else \
          ("YEU (selector hon chut)" if d_ic > 0 else "FAIL (selector KHONG hon)")
res["delta_ic_selector_minus_old"] = round(d_ic,4)
res["delta_lift"] = round(d_lift,4)
res["verdict"] = verdict
print(f"\n=== VERDICT: ΔIC={d_ic:+.4f} ΔLift={d_lift:+.2f} -> {verdict} ===")
print("Pre-register: PASS khi ΔIC>=+0.03 HOAC ΔLift>=+0.3")
json.dump(res, open(OUT,"w"), indent=2)
print(f"saved -> {OUT}")
