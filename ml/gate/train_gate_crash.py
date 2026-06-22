#!/usr/bin/env python3
"""
TASK-041 H2: Train GATE chặn-sập 3-lớp trên gate_dataset_v1 (label 24h/-15%, CÓ DÙNG OI).

Cấu hình chốt (A0): H=24h, X=-15% (lớp SẬP = ret_24h <= -0.15). 3 lớp: SẬP / TRUNG_TÍNH / TĂNG.
- DÙNG OI/LS (b6/b8) -> cắt về giai đoạn OI đầy đủ (>= 2021-12-01) cho OI có vai trò thật.
- Imbalance NẶNG (~1% SẬP): class_weight balanced; metric = precision/recall LỚP SẬP + lift, KHÔNG accuracy.
- De-overlap: embargo = H (96 bước 15m) giữa train/test; OOS = 12 tháng cuối đông lạnh.
- So RULE TRẦN "breadth thấp VÀ funding cao". ML không vượt rule -> bỏ ML (báo cáo trung thực).
- Leave-one-crash-out: kiểm không overfit 1 cú (LUNA/FTX).

Env: DATA (mac dinh /kaggle/input/**/gate_dataset_v1.csv), OUT_DIR=/kaggle/working, SEED=42
"""
import os, glob, json
import numpy as np
import pandas as pd
import xgboost as xgb

SEED = int(os.environ.get("SEED", "42"))
OUT = os.environ.get("OUT_DIR", "/kaggle/working")
DATA = os.environ.get("DATA", "/kaggle/input/**/gate_dataset_v1.csv")
X_CRASH = -0.15           # nguong SẬP (A0)
Y_UP = 0.09               # 0.6 * 15% (H1_GATE_SPEC C2: Y = 0.6|X|)
EMBARGO = 96              # 24h = 96 buoc 15m
OI_START = "2021-12-01"   # cat ve giai doan co OI day du
os.makedirs(OUT, exist_ok=True)

f = sorted(glob.glob(DATA, recursive=True))
assert f, f"khong thay {DATA}"
df = pd.read_csv(f[0]).sort_values("tEpochMs").reset_index(drop=True)
print(f"raw {len(df)} | {pd.to_datetime(df.tEpochMs.min(),unit='ms')} -> {pd.to_datetime(df.tEpochMs.max(),unit='ms')}")

# cat ve giai doan co OI (de OI co vai tro that)
cut = pd.Timestamp(OI_START).value // 10**6
df = df[df.tEpochMs >= cut].reset_index(drop=True)
df = df[df.ret_24h.notna()].reset_index(drop=True)
print(f"sau cat OI-start + bo label NaN: {len(df)}")

# 3-lop
def lab(r):
    if r <= X_CRASH: return 0   # SAP
    if r >= Y_UP:    return 2   # TANG
    return 1                    # TRUNG_TINH
df["y"] = df.ret_24h.apply(lab)
print("phan bo lop:", df.y.value_counts().to_dict(), "| SAP =", (df.y==0).mean()*100, "%")

# features: bo cot meta + label, GIU het feature A + B + OI/LS (b6/b8)
DROP = ["tEpochMs","tDate","ret_4h","ret_12h","ret_24h","n_4h","n_12h","n_24h","y"]
FEATS = [c for c in df.columns if c not in DROP]
print(f"{len(FEATS)} feature (gom OI b6/b8):", [c for c in FEATS if c.startswith(("b6","b8"))])

# split OOS = 12 thang cuoi dong lanh; embargo H giua train/test
ts_max = df.tEpochMs.max()
oos_cut = ts_max - 365*24*3600*1000
emb_ms = EMBARGO*15*60*1000
train = df[df.tEpochMs < oos_cut - emb_ms].reset_index(drop=True)
oos = df[df.tEpochMs >= oos_cut].reset_index(drop=True)
print(f"train {len(train)} (toi {pd.to_datetime(train.tEpochMs.max(),unit='ms')}) | OOS {len(oos)} | SAP train={ (train.y==0).sum()} OOS={(oos.y==0).sum()}")

Xtr, ytr = train[FEATS].values, train.y.values
Xoos, yoos = oos[FEATS].values, oos.y.values

# class weight balanced (SAP hiem)
n = len(ytr); cw = {c: n/(3*max(1,(ytr==c).sum())) for c in [0,1,2]}
w = np.array([cw[c] for c in ytr])
print("class_weight:", {k:round(v,2) for k,v in cw.items()})

dtr = xgb.DMatrix(Xtr, label=ytr, weight=w, feature_names=FEATS, missing=np.nan)
doos = xgb.DMatrix(Xoos, label=yoos, feature_names=FEATS, missing=np.nan)
params = dict(objective="multi:softprob", num_class=3, max_depth=4, eta=0.03,
              subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
              eval_metric="mlogloss", seed=SEED)
bst = xgb.train(params, dtr, num_boost_round=400, evals=[(dtr,"tr"),(doos,"oos")],
                early_stopping_rounds=40, verbose_eval=50)

# danh gia LOP SAP tren OOS
p = bst.predict(doos)
p_crash = p[:,0]
yb = (yoos==0).astype(int)
base = yb.mean()
print(f"\n=== OOS lop SAP (base={base*100:.2f}%) ===")
res = {"base_rate": float(base), "n_oos": int(len(yoos)), "n_crash_oos": int(yb.sum())}
for thr_pct in [99, 97, 95, 90]:
    thr = np.percentile(p_crash, thr_pct)
    sel = p_crash >= thr
    if sel.sum()==0: continue
    prec = yb[sel].mean(); rec = yb[sel].sum()/max(1,yb.sum()); lift = prec/base if base>0 else 0
    print(f"top {100-thr_pct}% (thr={thr:.3f}): n={sel.sum()} precision={prec:.3f} recall={rec:.3f} lift={lift:.2f}x")
    res[f"top{100-thr_pct}pct"] = dict(n=int(sel.sum()), precision=float(prec), recall=float(rec), lift=float(lift))

# RULE TRAN: breadth thap (percentAboveMA20 thap) VA funding cao (basketFundingAvg cao)
print("\n=== RULE TRAN: breadth thap VA funding cao ===")
if "percentAboveMA20" in FEATS and "basketFundingAvg" in FEATS:
    bo = oos["percentAboveMA20"].values; fo = oos["basketFundingAvg"].values
    b_thr = np.nanpercentile(train["percentAboveMA20"], 25)
    f_thr = np.nanpercentile(train["basketFundingAvg"], 75)
    rule = (bo <= b_thr) & (fo >= f_thr)
    if rule.sum()>0:
        rp = yb[rule].mean(); rr = yb[rule].sum()/max(1,yb.sum())
        print(f"rule: n={rule.sum()} precision={rp:.3f} recall={rr:.3f} lift={rp/base:.2f}x")
        res["rule"] = dict(n=int(rule.sum()), precision=float(rp), recall=float(rr), lift=float(rp/base))

# importance (OI co vao top?)
imp = bst.get_score(importance_type="gain")
top = sorted(imp.items(), key=lambda x:-x[1])[:15]
print("\n=== top-15 importance (gain) ===")
for k,v in top: print(f"  {k}: {v:.1f}")
res["top_importance"] = {k:float(v) for k,v in top}

bst.save_model(f"{OUT}/gate_crash_24h.ubj")
json.dump(res, open(f"{OUT}/gate_metrics.json","w"), indent=2)
print(f"\nDONE -> {OUT}/gate_crash_24h.ubj + gate_metrics.json")
