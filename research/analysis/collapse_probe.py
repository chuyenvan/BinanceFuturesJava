"""PREREG_COLLAPSE_PROBE (commit 7e1bbf6): AUC walk-forward - feature entry-time co du doan collapse khong? Khong sim."""
import logging, numpy as np, pandas as pd, xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score
logging.basicConfig(level=logging.INFO, format="%(message)s"); L = logging.getLogger("probe")
F = "/home/ubuntu/java/devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv"
H = 3600000; TZ = "Asia/Ho_Chi_Minh"
d = pd.read_csv(F, usecols=lambda c: c and not c.startswith("Unnamed"))
d["ts"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M").dt.tz_localize(TZ); d["te"] = pd.to_datetime(d.end, format="%Y%m%d %H:%M").dt.tz_localize(TZ)
d["ts_ms"] = d.ts.astype("int64") // 10**6; d["te_ms"] = d.te.astype("int64") // 10**6
d = d.sort_values("ts_ms").reset_index(drop=True)
# F1 book-state features (tinh tren MOI lenh, moi level), truoc khi loc level
ts_arr, te_arr = d.ts_ms.values, d.te_ms.values
d["n_open_at_entry"] = [int(((ts_arr < t) & (te_arr > t)).sum()) for t in ts_arr]
d = d.sort_values(["sym", "ts_ms"]); pe = d.groupby("sym").te_ms.shift(1); gap = (d.ts_ms - pe) / H
d["is_reentry_24h"] = (gap.notna() & (gap <= 24)).astype(int); d = d.sort_values("ts_ms")
d = d[d.level == "PREDICT_SYMBOL_TRADE"].copy(); L.info("PST trades: %d", len(d))
d["hour"] = d.ts.dt.hour; d["yr"] = d.ts.dt.year
d["collapse"] = ((d.status == "STOP_LOSS_DONE") & (d.profit <= -20)).astype(int); d["sl"] = (d.status == "STOP_LOSS_DONE").astype(int)
L.info("labels: collapse=%d (%.1f%%) sl=%d (%.1f%%)", d.collapse.sum(), 100*d.collapse.mean(), d.sl.sum(), 100*d.sl.mean())
# F2 join featv2
mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); s2id = dict(zip(mp.symbol, mp.symId))
d["symId"] = (d.sym + "USDT").map(s2id); d["ts_h"] = (d.ts_ms // H) * H
Fv = pd.read_parquet("/home/ubuntu/featv2/feat_v2_x1.parquet"); f2 = [c for c in Fv.columns if c not in ("ts", "sym") and not c.startswith("noise")]
d = d.merge(Fv.rename(columns={"ts": "ts_h", "sym": "symId"}), on=["ts_h", "symId"], how="left")
L.info("join featv2: symId ok %.3f, feature row ok %.3f", d.symId.notna().mean(), d.vol_7d.notna().mean())
f1 = ["symbolPred", "pred15m", "risk4h", "dow", "up", "dow15m", "hour", "n_open_at_entry", "is_reentry_24h"]
feats = f1 + f2; X = d[feats].astype(float)
cuts = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}", tz=TZ).value // 10**6) for c in
        "20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001".split()]
def m1(): return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))
def m2(): return xgb.XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=20, random_state=42, n_jobs=4, verbosity=0)
def wf(y, make, cols, seed_shuffle=None):
    pred = pd.Series(np.nan, index=d.index); rng = np.random.default_rng(seed_shuffle) if seed_shuffle is not None else None
    for i, c in enumerate(cuts):
        hi = int((pd.Timestamp(c, unit="ms", tz="UTC") + pd.DateOffset(months=3)).value // 10**6)
        tr = d.index[d.te_ms < c - 72 * H]; te = d.index[(d.ts_ms >= c) & (d.ts_ms < hi)]
        if len(tr) < 150 or len(te) == 0 or y[tr].sum() < 10: continue
        ytr = y[tr].values.copy()
        if rng is not None: rng.shuffle(ytr)
        m = make(); m.fit(X.loc[tr, cols], ytr); pred[te] = m.predict_proba(X.loc[te, cols])[:, 1]
    return pred
def auc(y, p):
    ok = p.notna(); return roc_auc_score(y[ok], p[ok]) if ok.sum() > 20 and y[ok].nunique() == 2 else np.nan
def report(name, y, p):
    yrs = {yy: auc(y[d.yr == yy], p[d.yr == yy]) for yy in (2022, 2023, 2024, 2025)}
    L.info("%-28s AUC all=%.3f | %s | n_oos=%d", name, auc(y, p), " ".join(f"{k}={v:.3f}" for k, v in yrs.items()), p.notna().sum()); return auc(y, p), yrs
L.info("\n== PRIMARY look: M2 xgb, label collapse ==")
p_primary = wf(d.collapse, m2, feats); a_all, a_yr = report("M2 collapse (PRIMARY)", d.collapse, p_primary)
L.info("== 3 look mo ta ==")
report("M1 logreg collapse", d.collapse, wf(d.collapse, m1, feats))
report("M2 xgb sl", d.sl, wf(d.sl, m2, feats)); report("M1 logreg sl", d.sl, wf(d.sl, m1, feats))
L.info("== kiem soat H0: xao nhan train x10 (M2, collapse) ==")
nulls = [auc(d.collapse, wf(d.collapse, m2, feats, seed_shuffle=s)) for s in range(10)]
L.info("null AUC: mean=%.3f sd=%.3f min=%.3f max=%.3f", np.nanmean(nulls), np.nanstd(nulls), np.nanmin(nulls), np.nanmax(nulls))
L.info("== AUC tung fold (PRIMARY) ==")
for i, c in enumerate(cuts):
    hi = int((pd.Timestamp(c, unit="ms", tz="UTC") + pd.DateOffset(months=3)).value // 10**6); te = (d.ts_ms >= c) & (d.ts_ms < hi)
    L.info("fold %2d %s n=%3d pos=%2d AUC=%.3f", i, pd.Timestamp(c, unit="ms", tz="UTC").strftime("%Y-%m"), te.sum(), d.collapse[te].sum(), auc(d.collapse[te], p_primary[te]))
L.info("\n== QUYET DINH (PREREG muc 5): all>=0.65 va 2023/2024/2025 >=0.60 ==")
ok = a_all >= 0.65 and all(a_yr[y] >= 0.60 for y in (2023, 2024, 2025))
L.info("PRIMARY all=%.3f 2023=%.3f 2024=%.3f 2025=%.3f => %s", a_all, a_yr[2023], a_yr[2024], a_yr[2025], "DANG PRE-REG FILTER" if ok else "DONG: khong co tin hieu")
L.info("\n== MO TA (khong quyet dinh) ==")
mfull = m2(); tr = d.index[d.te_ms < cuts[-1] - 72 * H]; mfull.fit(X.loc[tr], d.collapse[tr])
imp = pd.Series(mfull.feature_importances_, index=feats).sort_values(ascending=False); L.info("importance top-10 (M2 fit toi cut cuoi):\n%s", imp.head(10).round(4).to_string())
for f in ("n_open_at_entry", "symbolPred", "vol_7d", "age_days", "dd_7d"):
    a = roc_auc_score(d.collapse[X[f].notna()], X[f][X[f].notna()]); L.info("AUC don-feature %-16s = %.3f (huong %s)", f, max(a, 1 - a), "+" if a >= .5 else "-")
ok_ = p_primary.notna(); dd = d[ok_].copy(); dd["p"] = p_primary[ok_]
dd["drop"] = dd.groupby(dd.ts.dt.to_period("Q")).p.transform(lambda s: s >= s.quantile(0.9))
dr = dd[dd["drop"]]; L.info("counterfactual bo top-10%%/quy (n=%d): pnl SL tranh duoc=%.0f, pnl SM mat=%.0f, net=%.0f (CHAN TREN, khong re-sim sizing)",
    len(dr), -dr.pnl[dr.sl == 1].sum(), dr.pnl[dr.sl == 0].sum(), -dr.pnl.sum())
L.info("thanh phan lenh bi bo: SL=%d (%.1f%% vs base %.1f%%), collapse=%d", (dr.sl == 1).sum(), 100*(dr.sl == 1).mean(), 100*dd.sl.mean(), dr.collapse.sum())
