#!/usr/bin/env python3
# EXIT-LAB-4H — thu nghiem CHIEN LUOC EXIT (vong 3), long-only, ke toan "as-traded".
# BOI CANH: EV2 2-model (sl4h-ev2-n6) PASS — clfP(HIT6%,4h) AUC 0.743, gate P>=0.7 -> +1.74%/keo
#   duoi ke toan SL-CUNG-4h (HIT->+6% ; MISS->retEnd_4h). Cau hoi tiep: neu "NUOI" lenh da cham
#   lai thay vi chot TP cung, con lenh khong cham thi cat cung 4h — PnL/keo co vuot +1.74 khong?
# THIET KE: tai dung 100% pipeline load/fold/purge/XGB cua sl4h-ev2-n6. Train 1 lan/fold dung chung:
#   clfP3=P(maxFav_4h>=3%), clfP6=P(>=6%), clfP9=P(>=9%) ; regLoss=E(retEnd_4h | maxFav_4h<3%) tren MISS-3%.
# EXIT VARIANTS (vector hoa tu cot label, KHONG can model them):
#   E1 = retEnd_4h*100                                   (dong cung 4h — baseline)
#   E2 = where(hit6, +6, retEnd_4h*100)                  (TP cung +6% — chinh la EV2)
#   E3 = where(hit3, retEnd_12h*100, retEnd_4h*100)      (nuoi tho 12h)
#   E4 = where(hit3, max(1.0, retEnd_12h*100), retEnd_4h*100)  (nuoi co san +1% — proxy trailing arm SL)
#   E5 = where(hit3, retEnd_24h*100, retEnd_4h*100)      (nuoi 24h — neu cot _24h co)
#   hit3 = maxFav_4h>=0.03 & nBars_4h>=16 ; hit6 tuong tu 0.06.
# GATING GRID/fold OOS: G3=clfP3.p, G6=clfP6.p (P* in {0.5,0.6,0.7,0.8}), GEV=p6*6+(1-p6)*1.5*regLoss*100 (>0).
#   Moi (variant x gate x P*): n_keo/fold, PnL/keo mean, hit3_rate, PnL fold TE NHAT, so random cung n (5 lan).
# PLACEBO: 1 lan shuffle target clfP6 per-fold -> gate P>=0.7 -> PnL/keo phai ~ random (chong overfit label).
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
NEED_BARS_4H = 16                     # nBars_4h >= 16 (cua so 4h tren luoi 15m)
NEED_BARS_12H = 48                    # nBars_12h >= 48 (cua so 12h)
NEED_BARS_24H = 96                    # nBars_24h >= 96 (cua so 24h)
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
log = logging.getLogger("exit-lab")


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
    """In df.columns cua funding_label.csv; tra lai bo cot horizon co san + list variant chay duoc."""
    head = pd.read_csv(LABEL_CSV, nrows=1)
    cols = list(head.columns)
    print("EXITLAB_COLUMNS " + json.dumps(cols))
    log.info("funding_label.csv columns: %s", cols)
    has = {c: (c in cols) for c in ["maxFav_4h", "retEnd_4h", "nBars_4h",
                                     "retEnd_12h", "nBars_12h", "retEnd_24h", "nBars_24h",
                                     "retEnd_72h", "nBars_72h"]}
    for c in ["maxFav_4h", "retEnd_4h", "nBars_4h"]:
        assert has[c], f"THIEU cot bat buoc {c}"
    have12 = has["retEnd_12h"] and has["nBars_12h"]
    have24 = has["retEnd_24h"] and has["nBars_24h"]
    if not have12:
        for c in ["retEnd_12h", "nBars_12h"]:
            if not has[c]:
                print(f"EXITLAB_NO_{c}")
    if not have24:
        for c in ["retEnd_24h", "nBars_24h"]:
            if not has[c]:
                print(f"EXITLAB_NO_{c}")
    # variant kha dung: E1,E2 luon; E3,E4 can 12h; E5 can 24h
    variants = ["E1", "E2"]
    if have12:
        variants += ["E3", "E4"]
    if have24:
        variants += ["E5"]
    log.info("EXIT variants kha dung: %s (have12=%s have24=%s)", variants, have12, have24)
    return cols, have12, have24, variants


def load_labels(have12, have24):
    """Doc cot label can thiet, filter cua so 4h day du, tra cac cot tho (phan so) + nhan HIT."""
    want = ["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h"]
    if have12:
        want += ["retEnd_12h", "nBars_12h"]
    if have24:
        want += ["retEnd_24h", "nBars_24h"]
    df = pd.read_csv(LABEL_CSV, usecols=want, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df["nBars_4h"] >= NEED_BARS_4H) & df["maxFav_4h"].notna()
            & df["retEnd_4h"].notna()].copy()
    df["hit3"] = ((df["maxFav_4h"].values >= 0.03) & (df["nBars_4h"].values >= NEED_BARS_4H)).astype(np.int8)
    df["hit6"] = ((df["maxFav_4h"].values >= 0.06) & (df["nBars_4h"].values >= NEED_BARS_4H)).astype(np.int8)
    df["hit9"] = ((df["maxFav_4h"].values >= 0.09) & (df["nBars_4h"].values >= NEED_BARS_4H)).astype(np.int8)
    df["r4"] = df["retEnd_4h"].astype(np.float32)                    # phan so (retEnd_4h)
    if not have12:
        df["retEnd_12h"] = np.nan; df["nBars_12h"] = 0
    if not have24:
        df["retEnd_24h"] = np.nan; df["nBars_24h"] = 0
    log.info("Label: %d/%d rows | hit3=%.4f hit6=%.4f hit9=%.4f | r4%% mean=%.3f",
             len(df), n0, float(df.hit3.mean()), float(df.hit6.mean()), float(df.hit9.mean()),
             float(df.r4.mean() * 100))
    keep = ["ts", "symbol", "hit3", "hit6", "hit9", "r4",
            "retEnd_12h", "nBars_12h", "retEnd_24h", "nBars_24h"]
    return df[keep]


def compute_pnl(d, variant):
    """PnL/keo (don vi %) cho tung variant, vector hoa. Cot d: r4 (frac), hit3/hit6,
       retEnd_12h/nBars_12h, retEnd_24h/nBars_24h. Row nuoi khong du cua so -> fallback 4h."""
    r4p = d["r4"].values.astype(float) * 100.0
    hit3 = d["hit3"].values == 1
    hit6 = d["hit6"].values == 1
    if variant == "E1":
        return r4p
    if variant == "E2":
        return np.where(hit6, 6.0, r4p)
    if variant in ("E3", "E4"):
        r12 = d["retEnd_12h"].values.astype(float) * 100.0
        ok12 = (d["nBars_12h"].values >= NEED_BARS_12H) & np.isfinite(r12)
        nurt = np.where(ok12, r12, r4p)                       # thieu cua so 12h -> dong cung 4h
        if variant == "E4":
            nurt = np.where(ok12, np.maximum(1.0, r12), r4p)  # san +1% (proxy trailing arm SL)
        return np.where(hit3, nurt, r4p)
    if variant == "E5":
        r24 = d["retEnd_24h"].values.astype(float) * 100.0
        ok24 = (d["nBars_24h"].values >= NEED_BARS_24H) & np.isfinite(r24)
        nurt = np.where(ok24, r24, r4p)
        return np.where(hit3, nurt, r4p)
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
    """regLoss = E(retEnd_4h frac | maxFav_4h<3%) — train CHI tren tap MISS-3% (hit3==0)."""
    m = tr[tr["hit3"] == 0]
    if len(m) < 200:
        return np.zeros(len(te))
    reg = xgb.XGBRegressor(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                           subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                           objective="reg:squarederror", eval_metric="rmse",
                           n_jobs=-1, tree_method="hist", random_state=SEED)
    reg.fit(m[FEAT], m["r4"])
    pred = reg.predict(te[FEAT]).astype(float)
    mu, sd = float(np.mean(pred)), float(np.std(pred))
    if sd > 0:
        pred = np.clip(pred, mu - 3 * sd, mu + 3 * sd)
    return pred


def gate_specs():
    """Danh sach (gate, pstar) — G3/G6 quet P*, GEV 1 nguong (>0)."""
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
    """Voi moi (variant x gate x P*): n_keo, PnL/keo mean, hit3_rate, PnL random cung n (RANDOM_REPS lan).
       Tra dict[(variant,gate,ps)] = {n, pnl, hit3, rnd}."""
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
    cols, have12, have24, variants = detect_columns()
    feats = build_features()
    lb = load_labels(have12, have24)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | hit3=%.4f hit6=%.4f", len(ds),
             float(ds.hit3.mean()), float(ds.hit6.mean()))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chi chay fold 0")
    log.info("EXIT-LAB %d fold expanding OOS=%dm | variants=%s", len(folds), OOS_MONTHS, variants)

    purge = NEED_BARS_4H * GRID_MS
    auc_hist = {"p3": [], "p6": [], "p9": []}
    # combo_hist[(v,gate,ps)] = {"pnl":[...folds], "n":[...], "hit3":[...], "rnd":[...]}
    combo_hist = {}
    plac_pnl, plac_rnd = [], []                       # PLACEBO: shuffle hit6 -> gate p>=0.7
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
        # FIX 2026-07-17: shuffle-label clf hiem dat p>=0.7 -> selp rong -> placebo null.
        # top-N_real (N_real=so keo gate THAT p6>=0.7 fold nay) -> cung so keo, so fair.
        n_real = int((p6 >= 0.7).sum())
        selp = np.argsort(-pp6)[:n_real] if n_real > 0 else np.where(pp6 >= 0.7)[0]
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
    # tong hop moi combo qua fold
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
    # ---- in bang thuong (theo variant) ----
    print("\n===== EXIT-LAB per-variant (median qua fold) =====")
    print("var gate  P*   n_med   pnl/keo  rand   hit3    worst")
    for v in variants:
        for r in sorted([x for x in rows if x["variant"] == v],
                        key=lambda z: (z["gate"], z["pstar"])):
            print("%-3s %-4s %.1f  %-7s %-8s %-6s %-6s %-7s" % (
                r["variant"], r["gate"], r["pstar"], r["n_med"], r["pnl_med"],
                r["rnd_med"], r["hit3"], r["worst"]))
    # ---- chon best: n_med>=MIN, max pnl_med ----
    ok = [r for r in rows if (r["n_med"] or 0) >= MIN_TRADES_FOLD and r["pnl_med"] is not None]
    best = max(ok, key=lambda z: z["pnl_med"]) if ok else None
    if best:
        print("BEST %s %s P*=%.1f pnl/keo=%s n=%s hit3=%s worst=%s (EV2 chuan +1.74)" % (
            best["variant"], best["gate"], best["pstar"], best["pnl_med"],
            best["n_med"], best["hit3"], best["worst"]))
    # ---- PLACEBO ----
    plac = {"pnl": _med(plac_pnl), "random": _med(plac_rnd)}
    print("PLACEBO_RESULT " + json.dumps(plac))

    # ---- JSON <2KB: table chi giu n_med>=30, sort pnl_med desc, cat bot cho <2KB ----
    tab_full = sorted([r for r in rows if (r["n_med"] or 0) >= MIN_TRADES_FOLD
                       and r["pnl_med"] is not None],
                      key=lambda z: z["pnl_med"], reverse=True)
    table = [{"variant": r["variant"], "gate": r["gate"], "pstar": r["pstar"],
              "pnl_med": r["pnl_med"], "n_med": r["n_med"], "worst": r["worst"]}
             for r in tab_full]
    result = {"columns_found": cols, "auc": auc,
              "best": ({"variant": best["variant"], "gate": best["gate"], "pstar": best["pstar"],
                        "pnl_per_trade_med": best["pnl_med"],
                        "n_trades_per_fold_med": best["n_med"], "hit_rate": best["hit3"],
                        "worst_fold_pnl": best["worst"]} if best else None),
              "table": table, "placebo": plac}
    while len(json.dumps(result)) >= 2000 and result["table"]:
        result["table"].pop()                          # cat o xau nhat (cuoi) cho <2KB
    json.dump({"variants": variants, "auc": auc, "rows": rows, "placebo": plac},
              open(os.path.join(OUT_DIR, "exit_lab_4h_results.json"), "w"), indent=2)
    print("EXITLAB_RESULT " + json.dumps(result))
    log.info("XONG -> %s/exit_lab_4h_results.json", OUT_DIR)


if __name__ == "__main__":
    run()
