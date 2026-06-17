# TASK-026b Kaggle: TRAIN GATE PRODUCTION — horizon 12h (chot), nhan adaptive +-0.7 sigma.
# Khac train_gate_xgboost.py (chi chan doan 3 horizon): day la ban train ra MODEL DUNG DUOC.
# Pipeline:
#   1. Cat OOS dong lanh 12 thang cuoi (cham 1 lan, KHONG tune).
#   2. Phan truoc OOS: purged K-fold + embargo 12h (=H) -> OOF -> CV macro-F1, decile spread, rank-IC.
#   3. Train final tren TOAN BO phan-truoc-OOS -> predict OOS.
#   4. OOS metrics: rank-IC(P_up-P_down, ret_12h)+t-stat, decile spread, precision/recall+lift lop DOWN.
#   5. Beat-rule baseline: (marketBreadthStrength thap) AND (fundingRateAvg24H cao) -> block(DOWN).
#   6. PRE-REGISTERED pass-criteria: in PASS/FAIL.
#   7. Xuat ONNX + feature-list + manifest (md5 v1, commit) cho Java cam backtest.
# Tin hieu gate = P_up - P_down (KHONG hard argmax). Chay Kaggle (RUNBOOK).
import pandas as pd, numpy as np, xgboost as xgb, glob, json, hashlib, sys, subprocess
from sklearn.metrics import f1_score, precision_score, recall_score
from scipy.stats import spearmanr
from collections import Counter

# ----- config (PRE-REGISTERED) -----
HORIZON_LABEL = "ret_12h"; SHIFT_N = 48           # 12h / 15m = 48 moc
K_SIGMA = 0.7; SIGMA_WIN = 2880; SIGMA_MINP = 500 # adaptive +-0.7 sigma (rolling std 30 ngay backward)
EMBARGO_MS = 12*3600*1000                          # embargo = H = 12h
N_FOLD = 5; OOS_MONTHS = 12
PARAMS = dict(objective="multi:softprob", num_class=3, max_depth=5, eta=0.05,
              subsample=0.8, colsample_bytree=0.8, eval_metric="mlogloss", nthread=4, seed=42)
# pass thresholds
IC_MIN = 0.0; IC_T_MIN = 2.0                        # rank-IC OOS > 0 va |t| >= 2
COMMIT = sys.argv[1] if len(sys.argv) > 1 else "unknown"

# ----- load -----
print("INPUTS:", glob.glob("/kaggle/input/*"))
_c = glob.glob("/kaggle/input/**/gate_dataset_v1.csv", recursive=True)
assert _c, "khong thay gate_dataset_v1.csv"
SRC = _c[0]
md5 = hashlib.md5(open(SRC, "rb").read()).hexdigest()
print(f"SRC={SRC} md5={md5}")
df = pd.read_csv(SRC).sort_values("tEpochMs").reset_index(drop=True)
ts = df["tEpochMs"].values
dt = pd.to_datetime(ts, unit="ms")

label_cols = ["ret_4h","ret_12h","ret_24h","n_4h","n_12h","n_24h"]
drop = set(label_cols + ["tEpochMs","tDate","b6_oiPriceDiverge"])   # bo b6_oiPriceDiverge (trung |corr|=1)
feat = [c for c in df.columns if c not in drop]
print(f"n_feat={len(feat)}")
X = df[feat].astype(float).values

# ----- label adaptive +-0.7 sigma (no-leak: sigma shift theo horizon) -----
rr = df[HORIZON_LABEL].values
sigma = pd.Series(rr).rolling(SIGMA_WIN, min_periods=SIGMA_MINP).std().shift(SHIFT_N).values
y = np.where(rr >= K_SIGMA*sigma, 2, np.where(rr <= -K_SIGMA*sigma, 0, 1)).astype(float)
valid = (~np.isnan(sigma)) & (~np.isnan(rr))

# ----- OOS dong lanh 12 thang cuoi -----
cutoff = dt.max() - pd.DateOffset(months=OOS_MONTHS)
is_oos = np.asarray(dt > cutoff)   # dt la DatetimeIndex -> (dt>cutoff) da la ndarray (khong co .values)
tr_mask = valid & (~is_oos); oos_mask = valid & is_oos
print(f"OOS cutoff={cutoff} | n_train={tr_mask.sum()} n_oos={oos_mask.sum()}")

ytr_all = y[tr_mask].astype(int); Xtr_all = X[tr_mask]; tstr = ts[tr_mask]; rtr = rr[tr_mask]
yoos = y[oos_mask].astype(int);   Xoos = X[oos_mask];   roos = rr[oos_mask]; doos = dt[oos_mask]
print(f"dist train(DOWN,FLAT,UP)={(np.bincount(ytr_all,minlength=3)/len(ytr_all)).round(3).tolist()}")
print(f"dist oos  (DOWN,FLAT,UP)={(np.bincount(yoos,minlength=3)/len(yoos)).round(3).tolist()}")

def sw(yy):
    c = Counter(yy); n = len(yy); k = len(c); w = {cl: n/(k*v) for cl, v in c.items()}
    return np.array([w[v] for v in yy])

def purged_folds(tss, n):
    idx = np.arange(len(tss)); b = np.linspace(0, len(tss), n+1).astype(int)
    for kk in range(1, n):
        va_s, va_e = b[kk], b[kk+1]; t0 = tss[va_s]
        tr = idx[:va_s]; tr = tr[tss[tr] < t0 - EMBARGO_MS]
        yield tr, idx[va_s:va_e]

# ----- (2) CV tren phan-truoc-OOS -----
f1s = []; best_iters = []; oof_va = []; oof_p = []
for fold, (tr, va) in enumerate(purged_folds(tstr, N_FOLD)):
    if len(tr) < 2000 or len(va) < 500: continue
    dtr = xgb.DMatrix(Xtr_all[tr], label=ytr_all[tr], weight=sw(ytr_all[tr]), missing=np.nan)
    dva = xgb.DMatrix(Xtr_all[va], label=ytr_all[va], missing=np.nan)
    bst = xgb.train(PARAMS, dtr, num_boost_round=400, evals=[(dva,"va")],
                    early_stopping_rounds=30, verbose_eval=False)
    best_iters.append(bst.best_iteration + 1)
    proba = bst.predict(dva); f1s.append(f1_score(ytr_all[va], proba.argmax(1), average="macro"))
    oof_va.append(va); oof_p.append(proba)
cv_f1 = float(np.mean(f1s)); n_est = int(np.median(best_iters))
print(f"\n[CV] macro-F1={cv_f1:.4f} (std {np.std(f1s):.4f}) | n_est(median best)={n_est}")
vaC = np.concatenate(oof_va); PC = np.concatenate(oof_p, axis=0)
cv_sig = PC[:,2] - PC[:,0]; cv_ret = rtr[vaC]
cv_spread = float(pd.qcut(pd.Series(cv_sig).rank(method="first"), 10, labels=False)
                  .to_frame("dec").assign(r=cv_ret).groupby("dec")["r"].mean().pipe(lambda g: g.loc[9]-g.loc[0]))
print(f"[CV] decile spread (P_up-P_down) dec9-dec0 = {cv_spread:.4f}")

# ----- (3) train final tren toan bo phan-truoc-OOS (XGBClassifier de export ONNX) -----
from xgboost import XGBClassifier
clf = XGBClassifier(n_estimators=n_est, max_depth=5, learning_rate=0.05, subsample=0.8,
                    colsample_bytree=0.8, objective="multi:softprob", num_class=3,
                    tree_method="hist", missing=np.nan, n_jobs=4, random_state=42)
clf.fit(Xtr_all, ytr_all, sample_weight=sw(ytr_all))

# ----- (4) OOS metrics -----
Poos = clf.predict_proba(Xoos); sig = Poos[:,2] - Poos[:,0]; pred = Poos.argmax(1)
# rank-IC theo ngay -> t-stat tren chuoi IC ngay
icd = pd.DataFrame({"d": doos.values.astype("datetime64[D]"), "s": sig, "r": roos}) \
        .groupby("d").apply(lambda g: spearmanr(g["s"], g["r"]).correlation if len(g) > 10 else np.nan).dropna()
ic_mean = float(icd.mean()); ic_t = float(ic_mean / (icd.std()/np.sqrt(len(icd)))) if icd.std() > 0 else 0.0
go = pd.qcut(pd.Series(sig).rank(method="first"), 10, labels=False)
oos_spread = float(pd.DataFrame({"dec": go, "r": roos}).groupby("dec")["r"].mean().pipe(lambda g: g.loc[9]-g.loc[0]))
down_base = float((yoos == 0).mean())
prec_d = float(precision_score(yoos, pred, labels=[0], average="micro", zero_division=0))
rec_d  = float(recall_score(yoos, pred, labels=[0], average="micro", zero_division=0))
lift_d = float(prec_d / down_base) if down_base > 0 else 0.0
print(f"\n[OOS] rank-IC(day)={ic_mean:.4f} t={ic_t:.2f} (n_day={len(icd)})")
print(f"[OOS] decile spread={oos_spread:.4f} | DOWN base={down_base:.4f} prec={prec_d:.4f} rec={rec_d:.4f} lift={lift_d:.2f}")

# ----- (5) beat-rule baseline: breadth thap AND funding cao -> block(DOWN) -----
bi = feat.index("marketBreadthStrength"); fi = feat.index("fundingRateAvg24H")
br_lo = np.nanpercentile(Xtr_all[:, bi], 30); fu_hi = np.nanpercentile(Xtr_all[:, fi], 70)
rule_block = (Xoos[:, bi] < br_lo) & (Xoos[:, fi] > fu_hi)
rule_pred = np.where(rule_block, 0, 1)
rule_prec = float(precision_score(yoos, rule_pred, labels=[0], average="micro", zero_division=0))
rule_rec  = float(recall_score(yoos, rule_pred, labels=[0], average="micro", zero_division=0))
print(f"[RULE] block precision(DOWN)={rule_prec:.4f} recall={rule_rec:.4f} lift={rule_prec/down_base if down_base>0 else 0:.2f}")
# model rank cung muc recall voi rule: lay top-k sig theo so luong rule_block -> precision
k = int(rule_block.sum())
beat = False
if k > 0:
    topk = np.argsort(-sig)[:k]; model_prec_at_k = float((yoos[topk] == 0).mean())
    beat = model_prec_at_k > rule_prec
    print(f"[BEAT] model precision@k(={k}, rank by -sig=P_down up)={model_prec_at_k:.4f} vs rule {rule_prec:.4f} -> {'BEAT' if beat else 'KHONG BEAT'}")

# ----- (6) PRE-REGISTERED pass-criteria -----
c_ic   = (ic_mean > IC_MIN) and (abs(ic_t) >= IC_T_MIN)
c_sign = (np.sign(oos_spread) == np.sign(cv_spread)) and (cv_spread != 0)
c_beat = beat
print("\n===== PRE-REGISTERED PASS (ML tang 1) =====")
print(f"  [{'PASS' if c_ic else 'FAIL'}] rank-IC OOS>0 & |t|>=2 : IC={ic_mean:.4f} t={ic_t:.2f}")
print(f"  [{'PASS' if c_sign else 'FAIL'}] decile spread giu dau CV: CV={cv_spread:.4f} OOS={oos_spread:.4f}")
print(f"  [{'PASS' if c_beat else 'FAIL'}] model BEAT rule baseline (precision@k lop DOWN)")
print(f"  => ML-GATE {'PASS' if (c_ic and c_sign and c_beat) else 'FAIL'} (tang 2 = backtest, lam o buoc sau)")

# ----- (7) export ONNX + manifest -----
try:
    subprocess.run([sys.executable,"-m","pip","install","-q","onnxmltools","skl2onnx","onnx"], check=False)
    from onnxmltools.convert import convert_xgboost
    from onnxmltools.convert.common.data_types import FloatTensorType
    onx = convert_xgboost(clf, initial_types=[("input", FloatTensorType([None, len(feat)]))])
    open("/kaggle/working/gate_model_12h.onnx","wb").write(onx.SerializeToString())
    print("ONNX saved: gate_model_12h.onnx")
except Exception as e:
    print("ONNX export FAIL (lam o buoc tich hop):", repr(e))
clf.get_booster().save_model("/kaggle/working/gate_model_12h.json")
json.dump({"features": feat, "order": "khop Java side; index 0..%d" % (len(feat)-1)},
          open("/kaggle/working/gate_features.json","w"), ensure_ascii=False, indent=2)
json.dump({"task":"026b","horizon":HORIZON_LABEL,"k_sigma":K_SIGMA,"embargo_h":12,
           "src_md5":md5,"commit":COMMIT,"n_feat":len(feat),"n_est":n_est,
           "cv_macro_f1":cv_f1,"cv_spread":cv_spread,"oos_ic":ic_mean,"oos_ic_t":ic_t,
           "oos_spread":oos_spread,"down_base":down_base,"oos_cutoff":str(cutoff),
           "pass_ic":bool(c_ic),"pass_sign":bool(c_sign),"pass_beat":bool(c_beat)},
          open("/kaggle/working/gate_manifest.json","w"), ensure_ascii=False, indent=2)
print("manifest saved: gate_manifest.json")
