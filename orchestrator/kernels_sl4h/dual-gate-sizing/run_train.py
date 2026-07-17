#!/usr/bin/env python3
# DUAL-GATE-SIZING — n=6, 4h. GATE KEP (p6 + regLoss) + SIZING theo EV (vong 3b).
# BOI CANH: sl4h-ev2 (n6) gate 1 chieu p6>=0.7 -> +1.74%/keo. Cau hoi: (1) them dieu kien regLoss_pred
#   khong qua am (>= L*) co CAT bot keo xau -> nang PnL/keo? (2) thay vi equal-size, PHAN BO VON theo EV
#   (size ti le EV, clip 0.5..2.0) co nang TONG PnL/quy tren cung tap p>=0.7 khong?
# THIET KE: tai dung pipeline load/fold/purge/XGB cua sl4h-ev2. clfP6=P(maxFav_4h>=6% & nBars_4h>=16);
#   regLoss=E(retEnd_4h | miss6) train tren MISS-6%. EV = p6*6 + (1-p6)*1.5*regLoss*100.
# GATE KEP grid P* x L*: p6>=P* AND regLoss_pred*100 >= L* (L* in {-1,-2,-3, None-khong-loc}).
#   Moi (P*,L*): n_keo/fold, PnL/keo, hit6_rate, worst-fold. Ke toan SL-cung: HIT->+6 ; MISS->retEnd_4h%.
# SIZING (tren tap p6>=0.7): size = clip(EV, 0.5, 2.0) chuan hoa mean=1 trong fold -> so equal-size.
#   Moi fold (=1 quy): TONG PnL/quy equal = sum(pnl) ; EV-weighted = sum(size*pnl). Median qua fold ca 2.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = 6
NEED_BARS_4H = 16                            # nBars_4h >= 16 (cua so 4h)
PSTAR_GRID = [0.5, 0.6, 0.7, 0.8]            # nguong p6 cho gate chieu 1
LSTAR_GRID = [-1.0, -2.0, -3.0, None]        # nguong regLoss_pred (%) cho gate chieu 2; None=khong loc
SIZE_PSTAR = 0.7                             # tap co dinh cho phan sizing (p6>=0.7)
SIZE_CLIP = (0.5, 2.0)                       # clip size theo EV
MIN_TRADES_FOLD = 30                         # tieu chi: >=30 keo/quy
PEN = 1.5                                    # he so phat trong EV (khop EV2)
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dual-gate")


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


def build_folds():
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def _med(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.median(vals)), 4) if vals else None


def load_labels():
    df = pd.read_csv(LABEL_CSV, usecols=["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h"],
                     on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df["nBars_4h"] >= NEED_BARS_4H) & df["maxFav_4h"].notna() & df["retEnd_4h"].notna()].copy()
    df["hit6"] = ((df["maxFav_4h"].values >= 0.06) & (df["nBars_4h"].values >= NEED_BARS_4H)).astype(np.int8)
    df["ret_pct"] = (df["retEnd_4h"].values * 100.0).astype(np.float32)
    df["r4"] = df["retEnd_4h"].astype(np.float32)
    log.info("Label n6: %d/%d rows | hit6=%.4f | ret_pct mean=%.3f",
             len(df), n0, float(df.hit6.mean()), float(df.ret_pct.mean()))
    return df[["ts", "symbol", "hit6", "ret_pct", "r4"]]


def fit_predict(xgb, tr, te):
    """clfP6 -> p6, auc ; regLoss=E(retEnd_4h | miss6) tren MISS-6% -> regpred (frac).
       EV = p6*6 + (1-p6)*PEN*regpred*100 (don vi %)."""
    from sklearn.metrics import roc_auc_score
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit6"])
    p6 = clf.predict_proba(te[FEAT])[:, 1]
    try:
        auc = float(roc_auc_score(te["hit6"].values, p6)) if te["hit6"].nunique() > 1 else None
    except Exception:
        auc = None
    m = tr[tr["hit6"] == 0]
    if len(m) < 200:
        regpred = np.zeros(len(te))
    else:
        reg = xgb.XGBRegressor(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                               subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                               objective="reg:squarederror", eval_metric="rmse",
                               n_jobs=-1, tree_method="hist", random_state=SEED)
        reg.fit(m[FEAT], m["r4"])
        regpred = reg.predict(te[FEAT]).astype(float)
        mu, sd = float(np.mean(regpred)), float(np.std(regpred))
        if sd > 0:
            regpred = np.clip(regpred, mu - 3 * sd, mu + 3 * sd)
    ev = p6 * 6.0 + (1.0 - p6) * PEN * regpred * 100.0
    return p6, regpred, ev, auc


def eval_dualgate(te, p6, regloss_pct):
    """Grid P* x L*: p6>=P* AND regloss_pct>=L* (L*=None -> khong loc chieu 2).
       Tra dict[(P*,L*)] = {n, pnl, hit6}. Ke toan SL-cung: HIT->+6 ; MISS->ret_pct."""
    hit6 = te["hit6"].values
    pnl = np.where(hit6 == 1, float(N_PCT), te["ret_pct"].values)
    res = {}
    for ps in PSTAR_GRID:
        for ls in LSTAR_GRID:
            mask = p6 >= ps
            if ls is not None:
                mask = mask & (regloss_pct >= ls)
            idx = np.where(mask)[0]
            n = int(len(idx))
            res[(ps, ls)] = {"n": n,
                             "pnl": round(float(pnl[idx].mean()), 4) if n else None,
                             "hit6": round(float(hit6[idx].mean()), 4) if n else None}
    return res


def eval_sizing(te, p6, ev):
    """Tren tap p6>=SIZE_PSTAR: TONG PnL/quy equal-size vs EV-weighted.
       size = clip(EV, 0.5,2.0) chuan hoa mean=1 trong fold. equal=sum(pnl); wt=sum(size*pnl)."""
    hit6 = te["hit6"].values
    pnl = np.where(hit6 == 1, float(N_PCT), te["ret_pct"].values)
    idx = np.where(p6 >= SIZE_PSTAR)[0]
    if len(idx) == 0:
        return {"n": 0, "equal_total": None, "ev_total": None, "equal_per_trade": None,
                "ev_per_trade": None}
    pv = pnl[idx]
    ev_sel = ev[idx]
    size = np.clip(ev_sel, SIZE_CLIP[0], SIZE_CLIP[1])
    msz = float(size.mean())
    size = size / msz if msz > 0 else np.ones_like(size)      # chuan hoa mean=1
    equal_total = float(pv.sum())
    ev_total = float((size * pv).sum())
    return {"n": int(len(idx)), "equal_total": round(equal_total, 4), "ev_total": round(ev_total, 4),
            "equal_per_trade": round(float(pv.mean()), 4),
            "ev_per_trade": round(float((size * pv).sum() / size.sum()), 4)}


def run():
    feats = build_features()
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | hit6=%.4f", len(ds), float(ds.hit6.mean()))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chi chay fold 0")
    log.info("DUAL-GATE-SIZING n6: %d fold expanding OOS=%dm", len(folds), OOS_MONTHS)

    purge = NEED_BARS_4H * GRID_MS
    auc_hist = []
    grid_hist = {(ps, ls): {"n": [], "pnl": [], "hit6": []} for ps in PSTAR_GRID for ls in LSTAR_GRID}
    sz_hist = {"n": [], "equal_total": [], "ev_total": [], "equal_pt": [], "ev_pt": []}

    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit6"].sum() < 50 or (tr["hit6"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d hit6=%d) - bo", fi, len(tr), len(te),
                        int(tr["hit6"].sum()))
            continue
        p6, regpred, ev, auc = fit_predict(xgb, tr, te)
        regloss_pct = regpred * 100.0
        if auc is not None:
            auc_hist.append(auc)
        gr = eval_dualgate(te, p6, regloss_pct)
        for key, r in gr.items():
            h = grid_hist[key]
            h["n"].append(r["n"]); h["pnl"].append(r["pnl"]); h["hit6"].append(r["hit6"])
        sz = eval_sizing(te, p6, ev)
        sz_hist["n"].append(sz["n"]); sz_hist["equal_total"].append(sz["equal_total"])
        sz_hist["ev_total"].append(sz["ev_total"]); sz_hist["equal_pt"].append(sz["equal_per_trade"])
        sz_hist["ev_pt"].append(sz["ev_per_trade"])
        log.info("fold %d [%s..%s] AUC=%s | size n=%s eqTot=%s evTot=%s",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()),
                 round(auc, 4) if auc else None, sz["n"], sz["equal_total"], sz["ev_total"])

    if not auc_hist:
        raise SystemExit("Khong fold nao hop le — kiem alignment ts/symbol.")
    finalize(auc_hist, grid_hist, sz_hist)


def _lslab(ls):
    return "none" if ls is None else str(int(ls))


def finalize(auc_hist, grid_hist, sz_hist):
    auc = _med(auc_hist)
    rows = []
    for (ps, ls), h in grid_hist.items():
        pv = [x for x in h["pnl"] if x is not None]
        worst = round(float(np.min(pv)), 4) if pv else None
        rows.append({"pstar": ps, "lstar": ls, "n_med": _med(h["n"]), "pnl_med": _med(h["pnl"]),
                     "hit6_med": _med(h["hit6"]), "worst": worst})
    print("\n===== DUAL-GATE grid P* x L* (median qua fold) — n6 4h =====")
    print("P*   L*    n_med   pnl/keo  hit6    worst")
    for r in sorted(rows, key=lambda z: (z["pstar"], -9 if z["lstar"] is None else z["lstar"])):
        print("%.1f  %-4s  %-7s %-8s %-6s %-7s" % (
            r["pstar"], _lslab(r["lstar"]), r["n_med"], r["pnl_med"], r["hit6_med"], r["worst"]))
    ok = [r for r in rows if (r["n_med"] or 0) >= MIN_TRADES_FOLD and r["pnl_med"] is not None]
    best = max(ok, key=lambda z: z["pnl_med"]) if ok else None
    if best:
        print("BEST_GATE P*=%.1f L*=%s pnl/keo=%s n=%s hit6=%s worst=%s (EV2 chuan +1.74)" % (
            best["pstar"], _lslab(best["lstar"]), best["pnl_med"], best["n_med"],
            best["hit6_med"], best["worst"]))
    sizing = {"n_med": _med(sz_hist["n"]),
              "equal_total_med": _med(sz_hist["equal_total"]),
              "ev_weighted_total_med": _med(sz_hist["ev_total"]),
              "equal_per_trade_med": _med(sz_hist["equal_pt"]),
              "ev_weighted_per_trade_med": _med(sz_hist["ev_pt"])}
    print("SIZING (p6>=%.1f, median/quy) equal_total=%s ev_total=%s | equal_pt=%s ev_pt=%s" % (
        SIZE_PSTAR, sizing["equal_total_med"], sizing["ev_weighted_total_med"],
        sizing["equal_per_trade_med"], sizing["ev_weighted_per_trade_med"]))

    tab_full = sorted([r for r in rows if (r["n_med"] or 0) >= MIN_TRADES_FOLD
                       and r["pnl_med"] is not None], key=lambda z: z["pnl_med"], reverse=True)
    table = [{"pstar": r["pstar"], "lstar": _lslab(r["lstar"]), "pnl_med": r["pnl_med"],
              "n_med": r["n_med"], "worst": r["worst"]} for r in tab_full]
    result = {"n_pct": N_PCT, "auc": auc,
              "best_gate": ({"pstar": best["pstar"], "lstar": _lslab(best["lstar"]),
                             "pnl_per_trade_med": best["pnl_med"], "n_trades_per_fold_med": best["n_med"],
                             "hit_rate": best["hit6_med"], "worst_fold_pnl": best["worst"]}
                            if best else None),
              "sizing": sizing, "table": table}
    while len(json.dumps(result)) >= 2000 and result["table"]:
        result["table"].pop()
    json.dump({"n_pct": N_PCT, "auc": auc, "rows": [{**r, "lstar": _lslab(r["lstar"])} for r in rows],
               "sizing": sizing}, open(os.path.join(OUT_DIR, "dual_gate_sizing_results.json"), "w"),
              indent=2)
    print("DUALGATE_RESULT " + json.dumps(result))
    log.info("XONG -> %s/dual_gate_sizing_results.json", OUT_DIR)


if __name__ == "__main__":
    run()
