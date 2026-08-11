#!/usr/bin/env python3
# LONG-CONF-HEADROOM — test gia thuyet "gate long qua tho bao (nhi phan)". Gate hien tai (production):
#   admit/reject theo p6 >= ~0.68 (0.15*AI_DYNAMIC_MAX=0.3212 -> symbolPred=1-p6<=0.3212 -> p6>=0.6788)
#   + size CO DINH (SIZE_MULT deu tay, xem NEXT_SESSION_TODO_20260719.md "MAX-DEPLOYMENT (long)").
# CAU HOI: trong nhom duoc admit (VA ca pho p6), p6 co du bao return/keo khong? Neu quan he monotonic
#   -> size-by-confidence (soft-gate) dang xay (lever manh hon SIZE_MULT deu tay).
# KHONG train model moi ngoai clfP6 walk-forward can co de co p6 OOS (nhu sl4h-ev2-export/ev2-export-2022) —
#   preds ev2 da xuat (ev2_preds_n6_2022.csv.gz) KHONG co san lam Kaggle input nen kernel nay TU train
#   clfP6 y het base (BASE: ev2-export-2022/run_train.py, dataset + preamble + fold + GPU/CPU fallback
#   giu 100%), roi merge them retEnd_4h + oi_z de PHAN TICH (khong dung de train).
# RETURN METRIC: retEnd_4h (close-to-close return that, EV2 chuan horizon=4h, xem
#   ExportFundingLabel.java "retEnd_H = close(t+H)/close(t)-1") tru FRICTION_PCT=0.8 (round-trip fee 0.2%
#   + slippage 0.6% = 0.8%, dung so sim ma sát production — xem NEXT_SESSION_TODO_20260719.md dong 7-8).
#   Spearman IC KHONG doi duoi phep tru hang so nay; winrate/mean deu la SAU friction (thuc te hon).
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = int(os.environ.get("N_PCT", "6"))            # target %, khop selector production (n6)
NEED_BARS_4H = 16                                    # nBars_4h >= 16 (cua so 4h tren luoi 15m)
ADMIT_P = float(os.environ.get("ADMIT_P", "0.68"))   # nguong gate production (p6>=0.6788 lam tron 0.68)
FRICTION_PCT = float(os.environ.get("FRICTION_PCT", "0.8"))  # round-trip fee+slippage (%) — xem CORE.md
N_DECILE = int(os.environ.get("N_DECILE", "10"))
SEED = int(os.environ.get("SEED", "42"))
GRID_MS = 15 * 60 * 1000
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES               # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("long-conf-headroom")


def find1(p):
    m = sorted(glob.glob(p, recursive=True))
    assert m, f"KHONG TIM THAY: {p}"
    return m[0]


TOOL1_GLOB = os.environ.get("TOOL1_GLOB", "/kaggle/input/**/ff_*.bin")
OI_FILE = os.environ.get("OI_FILE") or find1("/kaggle/input/**/oi_percoin_full.bin")
LABEL_CSV = os.environ.get("LABEL_CSV") or find1("/kaggle/input/**/funding_label.csv")
MAP_CSV = os.environ.get("MAP_CSV") or find1("/kaggle/input/**/symbol_map.csv")
OUT_DIR = os.environ.get("OUT_DIR", "/kaggle/working")
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))
OOS_MONTHS = int(os.environ.get("OOS_MONTHS", "3"))
FIRST_OOS = os.environ.get("FIRST_OOS", "202201")     # 2022 coverage (khop ev2-export-2022, nhieu sample hon)
LAST = os.environ.get("LAST", "202606")
SMOKE = os.environ.get("SMOKE", "0") == "1"
os.makedirs(OUT_DIR, exist_ok=True)


# ================= PREAMBLE LOAD (giu nguyen tu sl4h-ev2-export / ev2-export-2022) =================
def _read(path, dt, item, grid=False):
    raw = open(path, "rb").read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    assert len(raw) % item == 0, f"{path}: len {len(raw)} khong chia het {item}"
    a = np.frombuffer(raw, dtype=dt)
    if grid:
        a = a[(a["ts"] % GRID_MS) == 0]
    return a


def load_tool1():
    files = sorted(glob.glob(TOOL1_GLOB, recursive=True))
    assert files, f"Tool1 khong thay: {TOOL1_GLOB}"
    parts = [_read(fp, TOOL1_DT, 170, grid=True) for fp in files]
    a = np.concatenate(parts)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    log.info("Tool1 (15m grid): %d rows | %d symId", len(df), df.symId.nunique())
    return df.sort_values("ts").reset_index(drop=True)


def load_oi():
    a = _read(OI_FILE, OI_DT, 30)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    O = np.asarray(a["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        df[nm] = O[:, j]
    log.info("OI: %d rows | %d symId", len(df), df.symId.nunique())
    return df.sort_values("ts").reset_index(drop=True)


def build_features():
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    del t, o
    log.info("Features ghep: %d rows | n_sym=%d", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def load_labels():
    """hit6 = maxFav_4h>=N_PCT% & nBars_4h>=16 (target train clfP6, KHONG doi).
       ret_net = retEnd_4h*100 - FRICTION_PCT (% that sau fee+slippage, DUNG DE PHAN TICH, khong train)."""
    cols = ["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h"]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df["nBars_4h"] >= NEED_BARS_4H) & df["maxFav_4h"].notna() & df["retEnd_4h"].notna()].copy()
    df["hit6"] = (df["maxFav_4h"].values >= N_PCT / 100.0).astype(np.int8)
    df["ret_net"] = (df["retEnd_4h"].values * 100.0 - FRICTION_PCT).astype(np.float32)
    log.info("Label n%d (4h): %d/%d rows | hit6_rate=%.4f | ret_net mean=%.3f",
              N_PCT, len(df), n0, float(df.hit6.mean()), float(df.ret_net.mean()))
    return df[["ts", "symbol", "hit6", "ret_net"]]


def build_folds():
    """expanding: OOS_k=[cutoff_k, cutoff_k+OOS_MONTHS), train = tat ca ts < cutoff_k - purge."""
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


# ================= CLASSIFIER clfP6 walk-forward (GPU cuda + CPU fallback, tu ev2-export-2022) =====
def _mk_gpu(xgb):
    return xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                             objective="binary:logistic", eval_metric="logloss",
                             n_jobs=-1, tree_method="hist", device="cuda", random_state=SEED)


def _mk_cpu(xgb):
    return xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                             objective="binary:logistic", eval_metric="logloss",
                             n_jobs=-1, tree_method="hist", random_state=SEED)


def mk_classifier(xgb):
    """GPU truoc (device=cuda); fallback CPU (tree_method=hist) neu GPU thieu / xgboost cu khong ho tro
    device= — de kernel khong chet khi GPU khong san sang (y het ev2-export-2022)."""
    try:
        return _mk_gpu(xgb)
    except TypeError as e:
        log.warning("device=cuda khong duoc ho tro (%s) - fallback CPU tree_method=hist", e)
        return _mk_cpu(xgb)


def fit_predict_p6(xgb, tr, te):
    """clfP6 = P(HIT+N_PCT%/4h) OOS, leak-free (train IS < cutoff-purge, predict OOS)."""
    try:
        clf = mk_classifier(xgb)
        clf.fit(tr[FEAT], tr["hit6"])
        return clf.predict_proba(te[FEAT])[:, 1]
    except Exception as e:
        log.warning("GPU fit loi (%s) - fallback CPU tree_method=hist", e)
        clf = _mk_cpu(xgb)
        clf.fit(tr[FEAT], tr["hit6"])
        return clf.predict_proba(te[FEAT])[:, 1]


def collect_oos(xgb, feats, folds):
    """Moi fold: train clfP6 tren IS -> predict p6 tren OOS. Gop TOAN BO OOS (khong chi GATED) de
    phan tich full-spectrum + admit-subset. Cot giu: p6, hit6, ret_net, oi_z, fold."""
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | hit6_rate=%.4f", len(ds), float(ds.hit6.mean()))
    purge = NEED_BARS_4H * GRID_MS
    keep = ["hit6", "ret_net", "oi_z"]
    parts = []
    auc_hist = []
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit6"].sum() < 50 or (tr["hit6"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d hit6=%d) - bo", fi,
                        len(tr), len(te), int(tr["hit6"].sum()))
            continue
        p6 = fit_predict_p6(xgb, tr, te)
        te = te.copy()
        te["p6"] = p6
        out = te[["p6"] + keep].copy()
        out["fold"] = fi
        parts.append(out)
        try:
            from sklearn.metrics import roc_auc_score
            auc = float(roc_auc_score(te["hit6"].values, p6)) if te["hit6"].nunique() > 1 else None
        except Exception:
            auc = None
        if auc is not None:
            auc_hist.append(auc)
        n_admit = int((p6 >= ADMIT_P).sum())
        log.info("fold %d [%s..%s] OOS=%d | AUC=%s | admit(p6>=%.2f)=%d (%.2f%%)",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()), len(out),
                 round(auc, 4) if auc is not None else None, ADMIT_P, n_admit,
                 100.0 * n_admit / len(out) if len(out) else 0.0)
    if not parts:
        raise SystemExit("Khong fold nao hop le — kiem alignment ts/symbol.")
    pooled = pd.concat(parts, ignore_index=True)
    log.info("Pooled OOS toan bo fold: %d keo | AUC median=%s",
              len(pooled), round(float(np.median(auc_hist)), 4) if auc_hist else None)
    return pooled, auc_hist


# ================= DECILE + IC =================
def decile_table(df, label, n_dec=N_DECILE):
    """Chia p6 thanh n_dec nhom (qcut, duplicates='drop'). In n/mean/median/winrate moi decile.
    winrate = ty le ret_net > 0 (thuc su co lai SAU friction) ; hit6_rate them tham khao."""
    d = df.copy()
    try:
        d["decile"], bins = pd.qcut(d["p6"], n_dec, labels=False, retbins=True, duplicates="drop")
    except ValueError as e:
        log.warning("%s: qcut loi (%s) - qua it gia tri p6 phan biet", label, e)
        return [], []
    rows = []
    print("\n===== DECILE p6 — %s (n_dec=%d) =====" % (label, d["decile"].nunique()))
    print("decile  p6_range           n        mean_ret  median_ret  winrate  hit6_rate")
    for dec in sorted(d["decile"].dropna().unique()):
        sub = d[d["decile"] == dec]
        lo, hi = float(bins[int(dec)]), float(bins[int(dec) + 1])
        row = {"decile": int(dec), "p6_lo": round(lo, 4), "p6_hi": round(hi, 4),
               "n": int(len(sub)), "mean_ret": round(float(sub["ret_net"].mean()), 4),
               "median_ret": round(float(sub["ret_net"].median()), 4),
               "winrate": round(float((sub["ret_net"] > 0).mean()), 4),
               "hit6_rate": round(float(sub["hit6"].mean()), 4)}
        rows.append(row)
        print("%-7d [%.4f,%.4f] %-8d %-9s %-11s %-8s %s" % (
            row["decile"], row["p6_lo"], row["p6_hi"], row["n"], row["mean_ret"],
            row["median_ret"], row["winrate"], row["hit6_rate"]))
    mono_ret = [r["mean_ret"] for r in rows]
    is_mono = all(mono_ret[i] <= mono_ret[i + 1] for i in range(len(mono_ret) - 1)) if len(mono_ret) > 1 else None
    print("monotonic(mean_ret tang deu theo decile) = %s" % is_mono)
    return rows, is_mono


def spearman_ic(x, y):
    from scipy.stats import spearmanr
    if len(x) < 30 or np.std(x) == 0 or np.std(y) == 0:
        return None, None
    rho, p = spearmanr(x, y)
    return (None if np.isnan(rho) else round(float(rho), 5)), (None if np.isnan(p) else float(p))


def run():
    feats = build_features()
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold dau")
    log.info("LONG-CONF-HEADROOM n%d 4h: %d fold expanding OOS=%dm | ADMIT_P=%.2f | FRICTION_PCT=%.2f",
             N_PCT, len(folds), OOS_MONTHS, ADMIT_P, FRICTION_PCT)

    pooled, auc_hist = collect_oos(xgb, feats, folds)
    admit = pooled[pooled["p6"] >= ADMIT_P].copy()
    log.info("ADMIT (p6>=%.2f): %d/%d keo (%.2f%%) | ret_net mean=%.4f | hit6_rate=%.4f",
              ADMIT_P, len(admit), len(pooled), 100.0 * len(admit) / len(pooled),
              float(admit["ret_net"].mean()) if len(admit) else float("nan"),
              float(admit["hit6"].mean()) if len(admit) else float("nan"))

    # ---- 1) decile p6 toan pho ----
    rows_full, mono_full = decile_table(pooled, "TOAN PHO (n=%d)" % len(pooled))

    # ---- 2) decile p6 CHI trong vung admit (p6>=ADMIT_P) — headroom check ----
    rows_admit, mono_admit = decile_table(admit, "ADMIT p6>=%.2f (n=%d)" % (ADMIT_P, len(admit)))

    # ---- 3) IC Spearman: toan pho, chi admit, + oi_z (them info ngoai p6?) ----
    ic_full, p_full = spearman_ic(pooled["p6"].values, pooled["ret_net"].values)
    ic_admit, p_admit = spearman_ic(admit["p6"].values, admit["ret_net"].values) if len(admit) >= 30 else (None, None)
    ic_oiz_full, p_oiz_full = spearman_ic(pooled["oi_z"].values, pooled["ret_net"].values)
    ic_oiz_admit, p_oiz_admit = spearman_ic(admit["oi_z"].values, admit["ret_net"].values) if len(admit) >= 30 else (None, None)
    print("\n===== SPEARMAN IC (corr voi ret_net, %s) =====" % ("retEnd_4h*100 - %.2f" % FRICTION_PCT))
    print("ic_full(p6, toan pho)   = %s (p=%s) n=%d" % (ic_full, p_full, len(pooled)))
    print("ic_admit(p6, admit)     = %s (p=%s) n=%d" % (ic_admit, p_admit, len(admit)))
    print("ic_oiz_full(oi_z, toan pho) = %s (p=%s)" % (ic_oiz_full, p_oiz_full))
    print("ic_oiz_admit(oi_z, admit)   = %s (p=%s) -- oi_z veto co them info ngoai p6 khong, trong tap da GATED"
          % (ic_oiz_admit, p_oiz_admit))

    n_quarters = pooled["fold"].nunique()
    full = {"label": "long-conf-headroom", "n_pct": N_PCT, "admit_p": ADMIT_P,
            "friction_pct": FRICTION_PCT, "return_metric_used": "retEnd_4h_pct_minus_friction_%.2f" % FRICTION_PCT,
            "first_oos": FIRST_OOS, "last": LAST, "oos_months": OOS_MONTHS, "seed": SEED,
            "n_pooled": int(len(pooled)), "n_admit": int(len(admit)), "n_quarters": int(n_quarters),
            "auc_median": round(float(np.median(auc_hist)), 4) if auc_hist else None,
            "decile_full": rows_full, "decile_admit": rows_admit,
            "monotonic_full": mono_full, "monotonic_admit": mono_admit,
            "ic_full": ic_full, "ic_full_p": p_full, "ic_admit": ic_admit, "ic_admit_p": p_admit,
            "ic_oiz_full": ic_oiz_full, "ic_oiz_admit": ic_oiz_admit}
    json.dump(full, open(os.path.join(OUT_DIR, "long_conf_headroom_results.json"), "w"), indent=2)

    marker = {"decile_returns": [r["mean_ret"] for r in rows_full],
              "winrate_by_decile": [r["winrate"] for r in rows_full],
              "decile_returns_admit": [r["mean_ret"] for r in rows_admit],
              "winrate_by_decile_admit": [r["winrate"] for r in rows_admit],
              "ic_full": ic_full, "ic_admit": ic_admit,
              "ic_oiz": ic_oiz_admit, "ic_oiz_full": ic_oiz_full,
              "return_metric_used": "retEnd_4h_pct_minus_friction_%.2f" % FRICTION_PCT,
              "n_pooled": int(len(pooled)), "n_admit": int(len(admit)), "admit_p": ADMIT_P}
    line = "LONG_CONF_HEADROOM_RESULT " + json.dumps(marker, separators=(",", ":"))
    if len(line) >= 2000:
        log.warning("Marker qua 2KB (%d chars) — cat bot decimal.", len(line))
    print(line)
    log.info("XONG -> %s/long_conf_headroom_results.json", OUT_DIR)


if __name__ == "__main__":
    run()
