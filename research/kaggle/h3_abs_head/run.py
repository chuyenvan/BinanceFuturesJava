"""H3 — DAU TU TIN TUYET DOI (Kaggle GPU). Xem PREREG_H3.md. CHI DUNG DU LIEU DEV.
A3a = 9 feat V3 + p15 (doc lap) | A3b = A3a + p_g015 (xep chong len G015).
Nhan y = 1[g1lite > 0.05]. WFO 10 cutoff, purge 72h. Doi chung shuffle-label doc lap tung tick.
Xuat: pred_h3a.parquet, pred_h3b.parquet, h3_metrics.json"""
import os, glob, json, time, sys
import numpy as np, pandas as pd, xgboost as xgb
from scipy.stats import spearmanr

SMOKE = False   # ban smoke doi dong nay thanh True: chi 2 fold + 20% dong, de kiem duong ong

def log(*a): print(time.strftime("%H:%M:%S"), *a, flush=True)

H = 3600000; TZ = 7 * H; PURGE = 72 * H
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
        "ret_14d", "ls_global", "rk_oi_delta24h"]

def find(name):
    hits = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    if not hits:
        raise SystemExit(f"KHONG tim thay {name} trong /kaggle/input")
    log("dung", hits[0])
    return hits[0]

# ---------- nap du lieu ----------
C = pd.read_parquet(find("cand_dev3.parquet"), columns=["ts", "sym", "p15", "p_g015", "g1lite"])
C = C[C.g1lite.notna() & C.p_g015.notna()]
for c in ("p15", "p_g015", "g1lite"):
    C[c] = C[c].astype("float32")
C["ts"] = C.ts.astype("int64"); C["sym"] = C.sym.astype("int32")
log("ledger v3", C.shape, "ticks", C.ts.nunique())

F = pd.read_parquet(find("feat_v2.parquet"), columns=["ts", "sym"] + KEEP)
for c in KEEP:
    F[c] = F[c].astype("float32")
F = F.rename(columns={"ts": "ts_h"})
C["ts_h"] = (C.ts // H) * H
C = C.merge(F, on=["ts_h", "sym"], how="left")
del F
log("sau join feat", C.shape, "co vol_7d", float(C.vol_7d.notna().mean()))

C["y"] = (C.g1lite > 0.05).astype("int8")
C["yr"] = pd.to_datetime(C.ts, unit="ms").dt.year
log("base rate P(g1lite>5%) =", round(float(C.y.mean()), 4))

CUTD = ["20220101", "20220401", "20220701", "20221001", "20230101",
        "20230401", "20230701", "20231001", "20240101", "20240401"]
CUT = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in CUTD]
if SMOKE:
    keep_idx = [0, 9]
    CUTD = [CUTD[i] for i in keep_idx]; CUT = [CUT[i] for i in keep_idx]
    C = C.sample(frac=0.2, random_state=0).sort_values("ts").reset_index(drop=True)
    log("SMOKE: 2 fold, rows", len(C))

# ---------- cong thuc gate THUC TE (khong duoc doi) ----------
def gate_admit(score, p15):
    mult = np.clip(score / 0.15 * 1.2876, 0.26787, 2.14135)
    return p15 >= (0.008 * mult)

def brier(p, y):
    return float(np.mean((p - y) ** 2))

def reliability(p, y, nb=20):
    q = pd.qcut(pd.Series(p), nb, labels=False, duplicates="drop")
    d = pd.DataFrame({"p": p, "y": y, "b": q}).groupby("b").agg(p=("p", "mean"), o=("y", "mean"), n=("y", "size"))
    return float((d.p - d.o).abs().max()), d

def params():
    base = dict(objective="binary:logistic", eval_metric="logloss",
                n_estimators=400, max_depth=5, learning_rate=0.05,
                min_child_weight=100, subsample=0.8, colsample_bytree=0.8,
                random_state=42, n_jobs=4)
    v = tuple(int(x) for x in xgb.__version__.split(".")[:2])
    if v >= (2, 0):
        base.update(device="cuda", tree_method="hist")
    else:
        base.update(tree_method="gpu_hist")
    return base
log("xgboost", xgb.__version__, "->", {k: v for k, v in params().items() if k in ("device", "tree_method")})

def run(name, FE, shuffle=False):
    preds = []
    for i, c in enumerate(CUT):
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = C[C.ts < c - PURGE]
        oos = C[(C.ts >= c) & (C.ts < hi)]
        if len(tr) < 50000 or len(oos) == 0:
            log(name, "fold", i, "skip"); continue
        assert tr.ts.max() < c, "LEAK"
        ytr = tr.y.values
        if shuffle:
            # permutation DOC LAP tung tick (loi cu: transform(sample) cho cung hoan vi voi group cung size)
            rng = np.random.default_rng(1000 + i)
            ytr = ytr.copy()
            idx = np.argsort(tr.ts.values, kind="stable")
            starts = np.flatnonzero(np.r_[True, np.diff(tr.ts.values[idx]) != 0])
            bounds = np.r_[starts, len(idx)]
            for a, b in zip(bounds[:-1], bounds[1:]):
                sl = idx[a:b]
                ytr[sl] = ytr[rng.permutation(sl)]
        m = xgb.XGBClassifier(**params())
        m.fit(tr[FE], ytr, verbose=False)
        p = m.predict_proba(oos[FE])[:, 1].astype("float32")
        preds.append(oos[["ts", "sym", "g1lite", "p15", "p_g015", "y", "yr"]].assign(p_abs=p))
        log(f"{name} fold {i} {CUTD[i]}: tr {len(tr)} oos {len(oos)} "
            f"rho {spearmanr(p, oos.g1lite).correlation:+.4f}")
    P = pd.concat(preds, ignore_index=True)
    return P, m

def score_card(name, P):
    rho = float(spearmanr(P.p_abs, P.g1lite).correlation)
    rho_y = {int(y): float(spearmanr(g.p_abs, g.g1lite).correlation) for y, g in P.groupby("yr")}
    br = brier(P.p_abs.values, P.y.values)
    br_g = brier(P.p_g015.values, P.y.values)  # p_g015 la P(win) truc tiep
    mx, tab = reliability(P.p_abs.values, P.y.values)
    # gate offline: score = 1 - p_abs (thap = tu tin), cung cong thuc
    adm_new = gate_admit(1 - P.p_abs.values, P.p15.values)
    adm_g = gate_admit(1 - P.p_g015.values, P.p15.values)
    out = dict(name=name, n=int(len(P)), rho=rho, rho_by_year=rho_y,
               brier_new=br, brier_g015=br_g,
               calib_max_gap=mx,
               admit_pct_new=float(100 * adm_new.mean()),
               admit_g1lite_new=float(P.g1lite.values[adm_new].mean()) if adm_new.any() else None,
               admit_pct_g015=float(100 * adm_g.mean()),
               admit_g1lite_g015=float(P.g1lite.values[adm_g].mean()) if adm_g.any() else None,
               pool_g1lite=float(P.g1lite.mean()))
    print("\n===== " + name + " =====")
    for k, v in out.items():
        print(f"  {k} = {v}")
    print("  reliability (pred TB vs quan sat):")
    print(tab.round(4).to_string())
    return out

RES = {}
for nm, FE in [("A3a", KEEP + ["p15"]), ("A3b", KEEP + ["p15", "p_g015"])]:
    P, m = run(nm, FE)
    P[["ts", "sym", "p_abs"]].to_parquet(f"/kaggle/working/pred_h3{nm[-1].lower()}.parquet", index=False)
    RES[nm] = score_card(nm, P)
    RES[nm]["importance"] = {f: float(v) for f, v in zip(FE, m.feature_importances_)}
    del P

Psh, _ = run("SHUFFLE", KEEP + ["p15"], shuffle=True)
RES["SHUFFLE"] = score_card("SHUFFLE(doi chung)", Psh)

json.dump(RES, open("/kaggle/working/h3_metrics.json", "w"), indent=2)
log("DONE")
