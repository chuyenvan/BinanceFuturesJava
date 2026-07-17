#!/usr/bin/env python3
# SL4H-EV2 — kien truc 2-model + EV ranking (long-only, BO GATE, chi SELECTOR).
# Chan doan vong 1 (task sl4h-train-n{3,6,9,15}): 1-regression reward-penalty FAIL —
#   model chi hoc VE PHAT (tranh coin am) ma MU VE THUONG (chon coin pump). LIFT@32 median <1.
# CDC doc lap (task-157) xac nhan + do selector cu duoi ke toan SL-cung-4h: PnL/keo -1.30% (thua random).
# VONG 2 — tach 2 model:
#   Model A (classifier): P(HIT), HIT = maxFav_4h >= N_PCT/100 (nBars_4h>=NEED).
#   Model B (regressor) : E(ret4h) train CHI tren tap MISS (do do am/duong khi khong dat target).
#   EV = p*N_PCT + (1-p)*PEN*ret4h_pred_pct     (ret4h_pred don vi %, co the am/duong; clip 3-sigma).
# Ke toan SL-cung: moi keo HIT -> +N_PCT% ; MISS -> ret4h thuc %. So random baseline cung k.
# Tai dung 100% pipeline load data cua sl4h-train-n6 (ff_*.bin 40 feat + OI 5 feat + funding_label.csv),
#   walk-forward EXPANDING fold, purge, leak-free. Chi thay phan label/model/eval.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = int(os.environ.get("N_PCT", "15"))    # target % (n6 lam dai dien)
PEN = float(os.environ.get("PEN", "1.5"))    # he so phat nhanh am trong EV (y=1.5)
NEED_BARS_4H = 16                            # nBars_4h >= 16 (cua so 4h tren luoi 15m)
NEED_BARS_12H = 48                           # nBars_12h >= 48 (cua so 12h)
NEED_BARS_24H = 96                           # nBars_24h >= 96 (cua so 24h) — fallback bonus
TOPK = [32, 64]                              # LIFT@k / PnL@k: top-k coin theo EV moi moc ts
PSTAR_GRID = [0.3, 0.4, 0.5, 0.6, 0.7]       # quet nguong P* cho threshold-gating
MIN_TRADES_FOLD = 30                         # tieu chi PASS: >=30 keo/quy (moi fold=1 quy OOS 3m)
RANDOM_REPS = 10                             # so lan lay ngau nhien de do baseline
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sl4h-ev2")


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


def label_columns():
    """Doc header funding_label.csv, in cot (BONUS 12h/24h detect)."""
    head = pd.read_csv(LABEL_CSV, nrows=1)
    cols = list(head.columns)
    log.info("funding_label.csv columns: %s", cols)
    return cols


def build_features():
    """Merged features (ts, symId, 45 feat, symbol) — KHONG phu thuoc horizon. Dung lai cho moi H."""
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)                                   # symId,symbol
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    del t, o
    log.info("Features ghep: %d rows | n_sym=%d", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def load_labels(horizon, need_bars):
    """hit = maxFav_H >= N_PCT/100 ; ret_pct = retEnd_H*100 (return thuc, don vi %)."""
    cf, cr, cn = f"maxFav_{horizon}", f"retEnd_{horizon}", f"nBars_{horizon}"
    df = pd.read_csv(LABEL_CSV, usecols=["tEpochMs", "symbol", cf, cr, cn],
                     on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df[cn] >= need_bars) & df[cf].notna() & df[cr].notna()].copy()
    df["hit"] = (df[cf].values >= N_PCT / 100.0).astype(np.int8)
    df["ret_pct"] = (df[cr].values * 100.0).astype(np.float32)
    log.info("Label %s n%d: %d/%d rows | base_rate(HIT)=%.4f | ret_pct mean=%.3f p10=%.2f p90=%.2f",
             horizon, N_PCT, len(df), n0, float(df.hit.mean()), float(df.ret_pct.mean()),
             float(np.percentile(df.ret_pct, 10)), float(np.percentile(df.ret_pct, 90)))
    return df[["ts", "symbol", "hit", "ret_pct"]]


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


def evaluate(te, p, ev):
    """EV-rank LIFT@k + PnL/keo SL-cung top-k (vs random) + AUC + quet nguong P*.
       pnl mot keo: HIT -> +N_PCT% ; MISS -> ret_pct thuc %."""
    from sklearn.metrics import roc_auc_score
    import scipy.stats as st
    d = te[["ts", "hit", "ret_pct"]].copy()
    d["p"] = np.asarray(p, dtype=float)
    d["ev"] = np.asarray(ev, dtype=float)
    d["pnl"] = np.where(d["hit"].values == 1, float(N_PCT), d["ret_pct"].values)   # ke toan SL-cung
    base = float(d.hit.mean())
    try:
        auc = float(roc_auc_score(d["hit"].values, d["p"].values)) if d.hit.nunique() > 1 else None
    except Exception:
        auc = None
    ic = float(st.spearmanr(d["ev"].values, d["ret_pct"].values).correlation)
    rng = np.random.default_rng(SEED)
    out = {"N": int(len(d)), "base_rate": round(base, 4),
           "AUC": round(auc, 4) if auc is not None else None, "IC_ev": round(ic, 4)}
    groups = [g for _, g in d.groupby("ts")]
    # ---- top-k theo EV-rank (LIFT %HIT + PnL/keo) ----
    for k in TOPK:
        gk = [g for g in groups if len(g) >= k]
        if not gk:
            out[f"LIFT{k}"] = None
            out[f"pnl_top{k}"] = None
            continue
        top = [g.nlargest(k, "ev") for g in gk]
        hit_top = float(np.concatenate([t["hit"].values for t in top]).mean())
        pnl_top = float(np.concatenate([t["pnl"].values for t in top]).mean())
        rnd_hit, rnd_pnl = [], []
        for _ in range(RANDOM_REPS):
            idx = [rng.choice(len(g), k, replace=False) for g in gk]
            rnd_hit.append(float(np.concatenate([g["hit"].values[i] for g, i in zip(gk, idx)]).mean()))
            rnd_pnl.append(float(np.concatenate([g["pnl"].values[i] for g, i in zip(gk, idx)]).mean()))
        hit_rnd = float(np.mean(rnd_hit))
        pnl_rnd = float(np.mean(rnd_pnl))
        out[f"n_ts_ge{k}"] = len(gk)
        out[f"hit_top{k}"] = round(hit_top, 4)
        out[f"hit_rand{k}"] = round(hit_rnd, 4)
        out[f"LIFT{k}"] = round(hit_top / base, 3) if base > 0 else None
        out[f"pnl_top{k}"] = round(pnl_top, 4)
        out[f"pnl_rand{k}"] = round(pnl_rnd, 4)
    # ---- quet nguong P* (threshold-gating tren p classifier, toan bo OOS fold) ----
    thr = {}
    for ps in PSTAR_GRID:
        sel = d[d["p"] >= ps]
        thr[str(ps)] = {"n_trades": int(len(sel)),
                        "pnl_per_trade": round(float(sel["pnl"].mean()), 4) if len(sel) else None,
                        "hit_rate": round(float(sel["hit"].mean()), 4) if len(sel) else None}
    out["thresh"] = thr
    return out


def fit_predict_ev(xgb, tr, te):
    """Model A (P HIT) + Model B (E ret4h tren MISS) -> EV moi sample OOS.
       EV = p*N_PCT + (1-p)*PEN*ret_pred_pct ; clip ret_pred ngoai 3-sigma (outlier)."""
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit"])
    p = clf.predict_proba(te[FEAT])[:, 1]
    tr_miss = tr[tr["hit"] == 0]
    reg = xgb.XGBRegressor(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                           subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                           objective="reg:squarederror", eval_metric="rmse",
                           n_jobs=-1, tree_method="hist", random_state=SEED)
    reg.fit(tr_miss[FEAT], tr_miss["ret_pct"])
    ret_pred = reg.predict(te[FEAT]).astype(float)
    mu, sd = float(np.mean(ret_pred)), float(np.std(ret_pred))
    if sd > 0:                                    # clip outlier >3 sigma (khong cap binh thuong)
        ret_pred = np.clip(ret_pred, mu - 3 * sd, mu + 3 * sd)
    ev = p * float(N_PCT) + (1.0 - p) * PEN * ret_pred
    return p, ev


def eval_horizon(xgb, feats, horizon, need_bars, folds):
    lb = load_labels(horizon, need_bars)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("[%s] Dataset ghep: %d rows | base_rate=%.4f", horizon, len(ds), float(ds.hit.mean()))
    per_fold = []
    purge = need_bars * GRID_MS
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("[%s] fold %d thieu data (tr=%d te=%d hit=%d) - bo", horizon, fi,
                        len(tr), len(te), int(tr["hit"].sum()))
            continue
        p, ev = fit_predict_ev(xgb, tr, te)
        r = evaluate(te, p, ev)
        r.update({"fold": fi, "n_train": int(len(tr)),
                  "oos_from": str(pd.to_datetime(cut, unit="ms").date()),
                  "oos_to": str(pd.to_datetime(oos_end, unit="ms").date())})
        per_fold.append(r)
        log.info("[%s] fold %d [%s..%s] base=%.4f AUC=%s LIFT32=%s pnl_top32=%s (rand=%s) IC_ev=%.3f",
                 horizon, fi, r["oos_from"], r["oos_to"], r["base_rate"], r["AUC"],
                 r.get("LIFT32"), r.get("pnl_top32"), r.get("pnl_rand32"), r["IC_ev"])
    return per_fold


def _med(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.median(vals)), 4) if vals else None


def summarize(per_fold):
    """Tong hop qua fold + chon best_threshold (max pnl/keo trong so P* co >=MIN_TRADES_FOLD keo/quy)."""
    if not per_fold:
        return None
    S = {"n_fold": len(per_fold),
         "auc_med": _med([f["AUC"] for f in per_fold]),
         "base_rate_med": _med([f["base_rate"] for f in per_fold]),
         "IC_ev_med": _med([f["IC_ev"] for f in per_fold]),
         "LIFT32_ev_med": _med([f.get("LIFT32") for f in per_fold]),
         "LIFT64_ev_med": _med([f.get("LIFT64") for f in per_fold]),
         "pnl_top32_med": _med([f.get("pnl_top32") for f in per_fold]),
         "pnl_rand32_med": _med([f.get("pnl_rand32") for f in per_fold]),
         "pnl_top64_med": _med([f.get("pnl_top64") for f in per_fold]),
         "pnl_rand64_med": _med([f.get("pnl_rand64") for f in per_fold])}
    # threshold aggregate
    thr_agg = {}
    for ps in PSTAR_GRID:
        k = str(ps)
        thr_agg[k] = {"n_trades_med": _med([f["thresh"][k]["n_trades"] for f in per_fold]),
                      "pnl_per_trade_med": _med([f["thresh"][k]["pnl_per_trade"] for f in per_fold]),
                      "hit_rate_med": _med([f["thresh"][k]["hit_rate"] for f in per_fold])}
    S["thresh_agg"] = thr_agg
    # chon best: uu tien P* co n_trades_med>=MIN va pnl>0, max pnl; fallback max pnl bat ky
    cand = [(ps, thr_agg[str(ps)]) for ps in PSTAR_GRID
            if thr_agg[str(ps)]["pnl_per_trade_med"] is not None]
    ok = [(ps, a) for ps, a in cand if (a["n_trades_med"] or 0) >= MIN_TRADES_FOLD]
    pool = ok if ok else cand
    best = max(pool, key=lambda x: x[1]["pnl_per_trade_med"]) if pool else None
    S["best_threshold"] = ({"pstar": best[0], "n_trades_per_fold_med": best[1]["n_trades_med"],
                            "pnl_per_trade_med": best[1]["pnl_per_trade_med"],
                            "hit_rate": best[1]["hit_rate_med"]} if best else None)
    return S


def print_table(horizon, per_fold, S):
    print(f"\n===== PER-FOLD [{horizon}] n{N_PCT} =====")
    print("fold  oos_from   oos_to     base   AUC    LIFT32 LIFT64 pnlT32 pnlR32 pnlT64 pnlR64 IC_ev")
    for f in per_fold:
        print("%4d  %-10s %-10s %.3f  %-6s %-6s %-6s %-6s %-6s %-6s %-6s %+.3f" % (
            f["fold"], f["oos_from"], f["oos_to"], f["base_rate"], f["AUC"],
            f.get("LIFT32"), f.get("LIFT64"), f.get("pnl_top32"), f.get("pnl_rand32"),
            f.get("pnl_top64"), f.get("pnl_rand64"), f["IC_ev"]))
    print(f"--- threshold sweep P* [{horizon}] (median qua fold: n_trades/quy | pnl/keo | %HIT) ---")
    for ps in PSTAR_GRID:
        a = S["thresh_agg"][str(ps)]
        print("  P*>=%.1f : n=%s  pnl/keo=%s  hit=%s" % (
            ps, a["n_trades_med"], a["pnl_per_trade_med"], a["hit_rate_med"]))


def run():
    cols = label_columns()
    has12 = all(c in cols for c in ["maxFav_12h", "retEnd_12h", "nBars_12h"])
    has24 = all(c in cols for c in ["maxFav_24h", "retEnd_24h", "nBars_24h"])
    if has12:
        h2, need2 = "12h", NEED_BARS_12H
    elif has24:
        h2, need2 = "24h", NEED_BARS_24H
    else:
        h2, need2 = None, None
        log.info("NO_12H — khong co cot 12h/24h, chi chay horizon 4h.")

    feats = build_features()
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chi chay fold 0")
    log.info("SL4H-EV2 n%d: %d fold expanding OOS=%dm | PEN=%.2f | h2=%s", N_PCT, len(folds),
             OOS_MONTHS, PEN, h2)

    pf4 = eval_horizon(xgb, feats, "4h", NEED_BARS_4H, folds)
    if not pf4:
        raise SystemExit("Khong fold nao hop le cho 4h — kiem alignment ts/symbol.")
    S4 = summarize(pf4)
    print_table("4h", pf4, S4)

    h12_out = None
    if h2:
        pf12 = eval_horizon(xgb, feats, h2, need2, folds)
        if pf12:
            S12 = summarize(pf12)
            print_table(h2, pf12, S12)
            h12_out = {"horizon": h2, "auc_med": S12["auc_med"],
                       "LIFT32_ev_med": S12["LIFT32_ev_med"], "LIFT64_ev_med": S12["LIFT64_ev_med"],
                       "pnl_per_trade_top32_med": S12["pnl_top32_med"],
                       "pnl_random_med": S12["pnl_rand32_med"],
                       "best_threshold": S12["best_threshold"]}
        else:
            log.warning("[%s] khong fold hop le — bo horizon phu.", h2)


    out = {"label": "sl4h-ev2", "arch": "2-model (clf HIT + reg ret-on-MISS) + EV rank",
           "n_pct": N_PCT, "pen": PEN, "first_oos": FIRST_OOS, "last": LAST,
           "oos_months": OOS_MONTHS, "seed": SEED, "h2": h2,
           "summary_4h": S4, "per_fold_4h": pf4}
    json.dump(out, open(os.path.join(OUT_DIR, f"sl4h_ev2_n{N_PCT}_results.json"), "w"), indent=2)

    result = {"n_pct": N_PCT,
              "auc_med": S4["auc_med"],
              "LIFT32_ev_med": S4["LIFT32_ev_med"], "LIFT64_ev_med": S4["LIFT64_ev_med"],
              "pnl_per_trade_top32_med": S4["pnl_top32_med"], "pnl_random_med": S4["pnl_rand32_med"],
              "best_threshold": S4["best_threshold"],
              "h12": h12_out}
    print("SL4H_EV2_RESULT " + json.dumps(result))
    log.info("XONG -> %s/sl4h_ev2_n%d_results.json", OUT_DIR, N_PCT)


if __name__ == "__main__":
    run()
