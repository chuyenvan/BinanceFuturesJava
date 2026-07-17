#!/usr/bin/env python3
# EXIT-LAB-12H — thu nghiem CHIEN LUOC EXIT voi CUA SO QUYET DINH = 12h (vong 3b).
# BOI CANH: exit-lab-4h dung cua so quyet dinh 4h (hit do tren maxFav_4h, cat cung 4h, nuoi 12h/24h).
#   Cau hoi bien the: neu MO RONG cua so QUYET DINH sang 12h — tin hieu vao cham target trong 12h,
#   cat cung tai 12h, nuoi tiep toi 24h — thi PnL/keo co tot hon khong? (chu ky quyet dinh cham hon).
# THIET KE: tai dung 100% pipeline load/fold/purge/XGB cua exit-lab-4h. KHAC:
#   hit3=P(maxFav_12h>=3%), hit6=P(maxFav_12h>=6%) voi nBars_12h>=48 ; regLoss=E(retEnd_12h | miss3) tren MISS-3%.
# EXIT VARIANTS (vector hoa tu cot label, KHONG can model them):
#   E1 = retEnd_12h*100                                    (cat cung 12h — baseline)
#   E2 = where(hit6, +6, retEnd_12h*100)                   (TP cung +6% tren cua so 12h)
#   E3 = where(hit3, retEnd_24h*100, retEnd_12h*100)       (nuoi tho toi 24h) — can cot _24h
#   E4 = where(hit3, max(1.0, retEnd_24h*100), retEnd_12h*100)  (nuoi co san +1%) — can cot _24h
#   hit3 = maxFav_12h>=0.03 & nBars_12h>=48 ; hit6 tuong tu 0.06. Thieu cot _24h -> chi E1/E2.
# GATING GRID/fold OOS: G3=clfP3.p, G6=clfP6.p (P* in {0.5,0.6,0.7,0.8}), GEV=p6*6+(1-p6)*1.5*regLoss*100 (>0).
#   Moi (variant x gate x P*): n_keo/fold, PnL/keo mean, hit3_rate, PnL fold TE NHAT, random cung n (5 lan).
# PLACEBO: 1 lan shuffle target clfP6 per-fold -> gate p>=0.7 -> PnL/keo phai ~ random (chong overfit label).
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
NEED_BARS_12H = 48                    # nBars_12h >= 48 (cua so quyet dinh 12h tren luoi 15m)
NEED_BARS_24H = 96                    # nBars_24h >= 96 (cua so nuoi 24h)
PSTAR_GRID = [0.5, 0.6, 0.7, 0.8]     # nguong P* cho gate G3/G6
MIN_TRADES_FOLD = 30                  # o bang chi giu combo co n_med >= 30
RANDOM_REPS = 5                       # so lan lay ngau nhien de do baseline
PEN = 1.5                             # he so phat trong GEV (khop EV2)
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("exit-lab-12h")


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
FIRST_OOS = os.environ.get("FIRST_OOS", "202301")
LAST = os.environ.get("LAST", "202606")
SEED = int(os.environ.get("SEED", "42"))
SMOKE = os.environ.get("SMOKE", "0") == "1"
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))
os.makedirs(OUT_DIR, exist_ok=True)


def _read(path, dt, item, grid=False):
    raw = open(path, "rb").read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    assert len(raw) % item == 0, f"{path}: len {len(raw)} khong chia het {item}"
    a = np.frombuffer(raw, dtype=dt)
    if grid:
        a = a[(a["ts"] % GRID_MS) == 0]      # loc 15m grid GIONG train selector
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
    log.info("Tool1 (15m grid): %d rows | %d symId | ts[%s..%s]", len(df), df.symId.nunique(),
             pd.to_datetime(df.ts.min(), unit="ms"), pd.to_datetime(df.ts.max(), unit="ms"))
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
    """Merged features (ts, symId, 45 feat, symbol) — KHONG phu thuoc horizon. Dung 1 lan."""
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)                                   # symId,symbol
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    del t, o
    log.info("Features ghep: %d rows | n_sym=%d", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def build_folds():
    """expanding: OOS_k = [cutoff_k, cutoff_k+OOS_MONTHS), truot = OOS_MONTHS (khong chong lan)."""
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def detect_columns():
    """In df.columns cua funding_label.csv; cua so QUYET DINH 12h bat buoc, nuoi 24h tuy chon."""
    head = pd.read_csv(LABEL_CSV, nrows=1)
    cols = list(head.columns)
    print("EXITLAB12H_COLUMNS " + json.dumps(cols))
    log.info("funding_label.csv columns: %s", cols)
    has = {c: (c in cols) for c in ["maxFav_12h", "retEnd_12h", "nBars_12h",
                                     "retEnd_24h", "nBars_24h"]}
    for c in ["maxFav_12h", "retEnd_12h", "nBars_12h"]:
        assert has[c], f"THIEU cot bat buoc cua so 12h {c}"
    have24 = has["retEnd_24h"] and has["nBars_24h"]
    if not have24:
        for c in ["retEnd_24h", "nBars_24h"]:
            if not has[c]:
                print(f"EXITLAB12H_NO_{c}")
    variants = ["E1", "E2"]
    if have24:
        variants += ["E3", "E4"]
    log.info("EXIT variants kha dung: %s (have24=%s)", variants, have24)
    return cols, have24, variants


def load_labels(have24):
    """Cua so QUYET DINH 12h: hit tren maxFav_12h, cat cung retEnd_12h. Nuoi 24h tuy chon."""
    want = ["tEpochMs", "symbol", "maxFav_12h", "retEnd_12h", "nBars_12h"]
    if have24:
        want += ["retEnd_24h", "nBars_24h"]
    df = pd.read_csv(LABEL_CSV, usecols=want, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df["nBars_12h"] >= NEED_BARS_12H) & df["maxFav_12h"].notna()
            & df["retEnd_12h"].notna()].copy()
    df["hit3"] = ((df["maxFav_12h"].values >= 0.03) & (df["nBars_12h"].values >= NEED_BARS_12H)).astype(np.int8)
    df["hit6"] = ((df["maxFav_12h"].values >= 0.06) & (df["nBars_12h"].values >= NEED_BARS_12H)).astype(np.int8)
    df["hit9"] = ((df["maxFav_12h"].values >= 0.09) & (df["nBars_12h"].values >= NEED_BARS_12H)).astype(np.int8)
    df["r12"] = df["retEnd_12h"].astype(np.float32)                 # phan so (retEnd_12h) — cat cung
    if not have24:
        df["retEnd_24h"] = np.nan; df["nBars_24h"] = 0
    log.info("Label 12h: %d/%d rows | hit3=%.4f hit6=%.4f hit9=%.4f | r12%% mean=%.3f",
             len(df), n0, float(df.hit3.mean()), float(df.hit6.mean()), float(df.hit9.mean()),
             float(df.r12.mean() * 100))
    keep = ["ts", "symbol", "hit3", "hit6", "hit9", "r12", "retEnd_24h", "nBars_24h"]
    return df[keep]


def compute_pnl(d, variant):
    """PnL/keo (%) cho tung variant. Cat cung 12h (r12); nuoi toi 24h neu du cua so, thieu -> fallback 12h."""
    r12p = d["r12"].values.astype(float) * 100.0
    hit3 = d["hit3"].values == 1
    hit6 = d["hit6"].values == 1
    if variant == "E1":
        return r12p
    if variant == "E2":
        return np.where(hit6, 6.0, r12p)
    if variant in ("E3", "E4"):
        r24 = d["retEnd_24h"].values.astype(float) * 100.0
        ok24 = (d["nBars_24h"].values >= NEED_BARS_24H) & np.isfinite(r24)
        nurt = np.where(ok24, r24, r12p)                      # thieu cua so 24h -> cat cung 12h
        if variant == "E4":
            nurt = np.where(ok24, np.maximum(1.0, r24), r12p)  # san +1% (proxy trailing arm SL)
        return np.where(hit3, nurt, r12p)
    raise ValueError(variant)


def safe_fit_clf(xgb, tr, te, ycol):
    """Fit XGBClassifier -> (p_oos, auc_oos). Neu 1 lop thieu (<20 mau) -> p=base const, auc=None."""
    from sklearn.metrics import roc_auc_score
    y = tr[ycol].values
    if y.sum() < 20 or (y == 0).sum() < 20:
        return np.full(len(te), float(y.mean())), None
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], y)
    p = clf.predict_proba(te[FEAT])[:, 1]
    try:
        auc = float(roc_auc_score(te[ycol].values, p)) if te[ycol].nunique() > 1 else None
    except Exception:
        auc = None
    return p, auc


def fit_regloss(xgb, tr, te):
    """regLoss = E(retEnd_12h frac | maxFav_12h<3%) — train CHI tren tap MISS-3% (hit3==0)."""
    m = tr[tr["hit3"] == 0]
    if len(m) < 200:
        return np.zeros(len(te))
    reg = xgb.XGBRegressor(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                           subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                           objective="reg:squarederror", eval_metric="rmse",
                           n_jobs=-1, tree_method="hist", random_state=SEED)
    reg.fit(m[FEAT], m["r12"])
    pred = reg.predict(te[FEAT]).astype(float)
    mu, sd = float(np.mean(pred)), float(np.std(pred))
    if sd > 0:
        pred = np.clip(pred, mu - 3 * sd, mu + 3 * sd)
    return pred


def gate_specs():
    specs = [("G3", ps) for ps in PSTAR_GRID] + [("G6", ps) for ps in PSTAR_GRID]
    specs += [("GEV", 0.0)]
    return specs


def gate_mask(gate, ps, p3, p6, gev):
    if gate == "G3":
        return p3 >= ps
    if gate == "G6":
        return p6 >= ps
    return gev > 0.0                     # GEV


def _med(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.median(vals)), 4) if vals else None


def eval_fold(te, p3, p6, gev, variants, rng):
    """Voi moi (variant x gate x P*): n_keo, PnL/keo mean, hit3_rate, PnL random cung n (RANDOM_REPS lan)."""
    hit3 = te["hit3"].values
    pnl_by_var = {v: compute_pnl(te, v) for v in variants}
    res = {}
    for gate, ps in gate_specs():
        mask = gate_mask(gate, ps, p3, p6, gev)
        idx_sel = np.where(mask)[0]
        n = int(len(idx_sel))
        for v in variants:
            pv = pnl_by_var[v]
            if n == 0:
                res[(v, gate, ps)] = {"n": 0, "pnl": None, "hit3": None, "rnd": None}
                continue
            pnl = float(pv[idx_sel].mean())
            h3 = float(hit3[idx_sel].mean())
            rnd = float(np.mean([pv[rng.choice(len(pv), n, replace=False)].mean()
                                 for _ in range(RANDOM_REPS)]))
            res[(v, gate, ps)] = {"n": n, "pnl": round(pnl, 4), "hit3": round(h3, 4),
                                  "rnd": round(rnd, 4)}
    return res


def run():
    cols, have24, variants = detect_columns()
    feats = build_features()
    lb = load_labels(have24)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | hit3=%.4f hit6=%.4f", len(ds),
             float(ds.hit3.mean()), float(ds.hit6.mean()))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chi chay fold 0")
    log.info("EXIT-LAB-12H %d fold expanding OOS=%dm | variants=%s", len(folds), OOS_MONTHS, variants)

    purge = NEED_BARS_12H * GRID_MS                   # purge = cua so quyet dinh 12h
    auc_hist = {"p3": [], "p6": [], "p9": []}
    combo_hist = {}
    plac_pnl, plac_rnd = [], []
    rng = np.random.default_rng(SEED)

    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit3"].sum() < 50 or (tr["hit3"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d hit3=%d) - bo", fi, len(tr), len(te),
                        int(tr["hit3"].sum()))
            continue
        p3, a3 = safe_fit_clf(xgb, tr, te, "hit3")
        p6, a6 = safe_fit_clf(xgb, tr, te, "hit6")
        p9, a9 = safe_fit_clf(xgb, tr, te, "hit9")
        regpred = fit_regloss(xgb, tr, te)
        gev = p6 * 6.0 + (1.0 - p6) * PEN * regpred * 100.0
        for k, a in zip(("p3", "p6", "p9"), (a3, a6, a9)):
            if a is not None:
                auc_hist[k].append(a)
        log.info("fold %d [%s..%s] AUC p3=%s p6=%s p9=%s | te=%d",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()),
                 round(a3, 4) if a3 else None, round(a6, 4) if a6 else None,
                 round(a9, 4) if a9 else None, len(te))
        fr = eval_fold(te, p3, p6, gev, variants, rng)
        for key, r in fr.items():
            h = combo_hist.setdefault(key, {"pnl": [], "n": [], "hit3": [], "rnd": []})
            h["pnl"].append(r["pnl"]); h["n"].append(r["n"])
            h["hit3"].append(r["hit3"]); h["rnd"].append(r["rnd"])
        # ---- PLACEBO: shuffle nhan hit6 trong TRAIN, gate p6>=0.7, PnL theo E1 ----
        trp = tr.copy()
        trp["hit6"] = rng.permutation(trp["hit6"].values)
        pp6, _ = safe_fit_clf(xgb, trp, te, "hit6")
        selp = np.where(pp6 >= 0.7)[0]
        if len(selp) > 0:
            e1 = compute_pnl(te, "E1")
            plac_pnl.append(float(e1[selp].mean()))
            plac_rnd.append(float(np.mean([e1[rng.choice(len(e1), len(selp), replace=False)].mean()
                                           for _ in range(RANDOM_REPS)])))

    if not combo_hist:
        raise SystemExit("Khong fold nao hop le — kiem alignment ts/symbol.")
    finalize(cols, variants, auc_hist, combo_hist, plac_pnl, plac_rnd)


def finalize(cols, variants, auc_hist, combo_hist, plac_pnl, plac_rnd):
    auc = {k: _med(v) for k, v in auc_hist.items()}
    rows = []
    for (v, gate, ps), h in combo_hist.items():
        pnl_med = _med(h["pnl"])
        n_med = _med(h["n"])
        worst = None
        pv = [x for x in h["pnl"] if x is not None]
        if pv:
            worst = round(float(np.min(pv)), 4)
        rows.append({"variant": v, "gate": gate, "pstar": ps,
                     "pnl_med": pnl_med, "n_med": n_med,
                     "hit3": _med(h["hit3"]), "rnd_med": _med(h["rnd"]), "worst": worst})
    print("\n===== EXIT-LAB-12H per-variant (median qua fold) =====")
    print("var gate  P*   n_med   pnl/keo  rand   hit3    worst")
    for v in variants:
        for r in sorted([x for x in rows if x["variant"] == v],
                        key=lambda z: (z["gate"], z["pstar"])):
            print("%-3s %-4s %.1f  %-7s %-8s %-6s %-6s %-7s" % (
                r["variant"], r["gate"], r["pstar"], r["n_med"], r["pnl_med"],
                r["rnd_med"], r["hit3"], r["worst"]))
    ok = [r for r in rows if (r["n_med"] or 0) >= MIN_TRADES_FOLD and r["pnl_med"] is not None]
    best = max(ok, key=lambda z: z["pnl_med"]) if ok else None
    if best:
        print("BEST %s %s P*=%.1f pnl/keo=%s n=%s hit3=%s worst=%s (EV2/4h chuan +1.74)" % (
            best["variant"], best["gate"], best["pstar"], best["pnl_med"],
            best["n_med"], best["hit3"], best["worst"]))
    plac = {"pnl": _med(plac_pnl), "random": _med(plac_rnd)}
    print("PLACEBO_RESULT " + json.dumps(plac))

    tab_full = sorted([r for r in rows if (r["n_med"] or 0) >= MIN_TRADES_FOLD
                       and r["pnl_med"] is not None],
                      key=lambda z: z["pnl_med"], reverse=True)
    table = [{"variant": r["variant"], "gate": r["gate"], "pstar": r["pstar"],
              "pnl_med": r["pnl_med"], "n_med": r["n_med"], "worst": r["worst"]}
             for r in tab_full]
    result = {"window": "12h", "columns_found": cols, "auc": auc,
              "best": ({"variant": best["variant"], "gate": best["gate"], "pstar": best["pstar"],
                        "pnl_per_trade_med": best["pnl_med"],
                        "n_trades_per_fold_med": best["n_med"], "hit_rate": best["hit3"],
                        "worst_fold_pnl": best["worst"]} if best else None),
              "table": table, "placebo": plac}
    while len(json.dumps(result)) >= 2000 and result["table"]:
        result["table"].pop()
    json.dump({"window": "12h", "variants": variants, "auc": auc, "rows": rows, "placebo": plac},
              open(os.path.join(OUT_DIR, "exit_lab_12h_results.json"), "w"), indent=2)
    print("EXITLAB12H_RESULT " + json.dumps(result))
    log.info("XONG -> %s/exit_lab_12h_results.json", OUT_DIR)


if __name__ == "__main__":
    run()
