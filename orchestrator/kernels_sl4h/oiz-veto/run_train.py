#!/usr/bin/env python3
# OIZ-VETO — test entry-veto theo feature conditioning (oi_z/f22/f14/f8/oi_delta24h) tren tap GATED
#   cua selector EV2 (clfP6). BOI CANH: feat-screen tim ra oi_z co edge_spread -3.24% monotonic=1.0
#   (oi_z THAP -> pnl +2.43 ; oi_z CAO -> -0.81) va f22/f14/f8/oi_delta24h cung dan dat manh, nhung
#   classifier UNDER-DUNG (toi uu P(HIT), khong toi uu PnL). GIA THUYET: veto entry oi_z cao (bo qua)
#   se nang edge net cua selector, danh doi tan suat.
# BASE: sl4h-ev2-n6/run_train.py — tai dung 100% preamble load (ff+oi+label), walk-forward EXPANDING
#   fold, purge, train clfP6 = P(maxFav_4h>=0.06). Ke toan SL-cung: HIT6 -> +6 ; MISS -> retEnd_4h*100.
# PHUONG PHAP (leak-free): moi fold train tren IS, predict p6 tren OOS; GATED = OOS rows p6>=GATE_P.
#   Gop GATED moi fold (chi OOS, KHONG tron IS). Vi edge_spread AM (gia tri feature THAP = tot), veto
#   giu entry feature <= quantile Q cua chinh feature do TRONG TAP GATED (Q in {0.3,0.5,0.7,0.9}).
#   Regime bull/chop tach theo ngay OOS fold (REGIME_SPLIT, dung chung voi ev2-frontier).
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = int(os.environ.get("N_PCT", "6"))    # target % (n6 lam dai dien)
NEED_BARS_4H = 16                            # nBars_4h >= 16 (cua so 4h tren luoi 15m)
GATE_P = float(os.environ.get("GATE_P", "0.7"))     # nguong p6 vao tap GATED (dung nhu feat-screen)
FEE_PCT = float(os.environ.get("FEE_PCT", "0.2"))   # %/keo round-trip (net = gross - FEE_PCT)
Q_GRID = [0.3, 0.5, 0.7, 0.9]                 # giu % "tot nhat" (feature THAP = tot, edge_spread AM)
VETO_FEATS = ["oi_z", "f22", "f14", "f8", "oi_delta24h"]
DOUBLE_Q = 0.7                                # veto kep: oi_z<=Q AND f22<=Q
REGIME_SPLIT = pd.Timestamp("2025-01-01")     # BULL: oos_from < moc ; CHOP: >= (dung chung ev2-frontier)
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("oiz-veto")


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


# ================= PREAMBLE LOAD (giu nguyen tu base sl4h-ev2-n6) =================
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
    head = pd.read_csv(LABEL_CSV, nrows=1)
    cols = list(head.columns)
    log.info("funding_label.csv columns: %s", cols)
    return cols


def build_features():
    """Merged features (ts, symId, 45 feat, symbol). KHONG phu thuoc horizon."""
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
    log.info("Label %s n%d: %d/%d rows | base_rate(HIT)=%.4f | ret_pct mean=%.3f",
             horizon, N_PCT, len(df), n0, float(df.hit.mean()), float(df.ret_pct.mean()))
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


# ================= CLASSIFIER clfP6 (giu nguyen hyperparam tu base) =================
def fit_predict_p6(xgb, tr, te):
    """clfP6 = P(HIT+6%/4h) — dung Y HET hyperparam base kernel sl4h-ev2-n6."""
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit"])
    return clf.predict_proba(te[FEAT])[:, 1]


def collect_gated(xgb, feats, folds):
    """Moi fold: train clfP6 tren IS -> predict p6 tren OOS -> GATED = p6>=GATE_P (leak-free: chi OOS).
       Giu them cot VETO_FEATS + fold + regime de sweep veto sau. pnl = HIT?+N_PCT:ret_pct (SL-cung)."""
    lb = load_labels("4h", NEED_BARS_4H)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | base_rate=%.4f", len(ds), float(ds.hit.mean()))
    purge = NEED_BARS_4H * GRID_MS
    keep = VETO_FEATS + ["hit", "ret_pct"]
    gated_parts = []
    fold_meta = []       # (fold_idx, oos_from_str, regime)
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d hit=%d) - bo", fi,
                        len(tr), len(te), int(tr["hit"].sum()))
            continue
        p6 = fit_predict_p6(xgb, tr, te)
        oos_from = pd.to_datetime(cut, unit="ms")
        regime = "bull" if oos_from < REGIME_SPLIT else "chop"
        te = te.copy()
        te["p6"] = p6
        g = te[te["p6"] >= GATE_P][keep].copy()
        g["pnl"] = np.where(g["hit"].values == 1, float(N_PCT), g["ret_pct"].values)
        g["fold"] = fi
        g["regime"] = regime
        gated_parts.append(g)
        fold_meta.append((fi, str(oos_from.date()), regime))
        log.info("fold %d [%s] regime=%s: OOS=%d gated=%d (p6>=%.2f) gated_pnl_mean=%.4f gated_hit=%.4f",
                 fi, str(oos_from.date()), regime, len(te), len(g), GATE_P,
                 float(g["pnl"].mean()) if len(g) else float("nan"),
                 float(g["hit"].mean()) if len(g) else float("nan"))
    if not gated_parts:
        raise SystemExit("Khong fold nao hop le — kiem alignment ts/symbol.")
    gated = pd.concat(gated_parts, ignore_index=True)
    log.info("GATED gop toan bo fold: %d keo | pnl_mean=%.4f | hit=%.4f",
             len(gated), float(gated["pnl"].mean()), float(gated["hit"].mean()))
    return gated, fold_meta


def _stats(sub, n_quarters):
    """(n_trades, trades_per_quarter, gross, net, hit_rate) tren tap con cho so quy cho truoc."""
    n = int(len(sub))
    if n == 0 or n_quarters == 0:
        return {"n_trades": n, "trades_per_quarter": 0.0, "gross": None, "net": None, "hit_rate": None}
    gross = float(sub["pnl"].mean())
    return {"n_trades": n,
            "trades_per_quarter": round(n / n_quarters, 3),
            "gross": round(gross, 4),
            "net": round(gross - FEE_PCT, 4),
            "hit_rate": round(float(sub["hit"].mean()), 4)}


def veto_point(gated, mask, n_quarters_all, n_bull, n_chop):
    """Ap mask (bool array) len GATED -> stats pooled + bull + chop."""
    sub = gated[mask]
    s_all = _stats(sub, n_quarters_all)
    s_bull = _stats(sub[sub["regime"] == "bull"], n_bull)
    s_chop = _stats(sub[sub["regime"] == "chop"], n_chop)
    return {"n_trades": s_all["n_trades"], "trades_per_quarter": s_all["trades_per_quarter"],
            "net": s_all["net"], "hit_rate": s_all["hit_rate"],
            "net_bull": s_bull["net"], "net_chop": s_chop["net"]}


def run():
    label_columns()
    feats = build_features()
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold dau")
    log.info("OIZ-VETO n%d: %d fold expanding OOS=%dm | GATE_P=%.2f | FEE_PCT=%.3f | Q_GRID=%s",
             N_PCT, len(folds), OOS_MONTHS, GATE_P, FEE_PCT, Q_GRID)

    gated, fold_meta = collect_gated(xgb, feats, folds)
    n_quarters_all = len({m[0] for m in fold_meta})
    n_bull = len({m[0] for m in fold_meta if m[2] == "bull"})
    n_chop = len({m[0] for m in fold_meta if m[2] == "chop"})
    log.info("n_quarters: pooled=%d bull=%d chop=%d", n_quarters_all, n_bull, n_chop)

    # ---- baseline: KHONG veto, chi gate p6>=GATE_P ----
    base_mask = np.ones(len(gated), dtype=bool)
    baseline = veto_point(gated, base_mask, n_quarters_all, n_bull, n_chop)
    print("\n===== OIZ-VETO baseline (GATED p6>=%.2f, KHONG veto) =====" % GATE_P)
    print("n=%d tpq=%.2f net=%s hit=%s net_bull=%s net_chop=%s" % (
        baseline["n_trades"], baseline["trades_per_quarter"], baseline["net"],
        baseline["hit_rate"], baseline["net_bull"], baseline["net_chop"]))

    # ---- veto don: giu feature <= quantile Q cua CHINH feature trong GATED (edge_spread AM: thap=tot) ----
    veto_single = {}
    print("\n===== VETO DON theo feature (giu <=quantile Q, feature THAP = tot) =====")
    print("feat        Q     n_giu   tpq     net      net_bull net_chop hit")
    for feat in VETO_FEATS:
        veto_single[feat] = {}
        col = gated[feat]
        for q in Q_GRID:
            thr = float(col.quantile(q))
            mask = (col <= thr).values     # NaN -> False (loai NaN khoi tap giu, dung leak-free)
            pt = veto_point(gated, mask, n_quarters_all, n_bull, n_chop)
            pt["quantile_thr"] = round(thr, 4)
            veto_single[feat][str(q)] = pt
            print("%-11s %.1f   %-7d %-7s %-8s %-8s %-8s %s" % (
                feat, q, pt["n_trades"], pt["trades_per_quarter"], pt["net"],
                pt["net_bull"], pt["net_chop"], pt["hit_rate"]))

    # ---- veto kep: oi_z<=Q AND f22<=Q, Q=DOUBLE_Q ----
    thr_oiz = float(gated["oi_z"].quantile(DOUBLE_Q))
    thr_f22 = float(gated["f22"].quantile(DOUBLE_Q))
    mask_double = ((gated["oi_z"] <= thr_oiz) & (gated["f22"] <= thr_f22)).values
    double_pt = veto_point(gated, mask_double, n_quarters_all, n_bull, n_chop)
    double_pt["quantile_thr_oi_z"] = round(thr_oiz, 4)
    double_pt["quantile_thr_f22"] = round(thr_f22, 4)
    print("\n===== VETO KEP oi_z<=Q AND f22<=Q (Q=%.1f) =====" % DOUBLE_Q)
    print("n_giu=%d tpq=%.2f net=%s net_bull=%s net_chop=%s hit=%s" % (
        double_pt["n_trades"], double_pt["trades_per_quarter"], double_pt["net"],
        double_pt["net_bull"], double_pt["net_chop"], double_pt["hit_rate"]))

    # ---- so sanh: net sau veto vs baseline (delta) ----
    print("\n===== SO SANH net (veto - baseline=%.4f) =====" % baseline["net"])
    for feat in VETO_FEATS:
        for q in Q_GRID:
            pt = veto_single[feat][str(q)]
            delta = round(pt["net"] - baseline["net"], 4) if pt["net"] is not None else None
            print("  %-11s Q=%.1f: net=%s delta=%s tpq=%s (baseline_tpq=%.2f)" % (
                feat, q, pt["net"], delta, pt["trades_per_quarter"], baseline["trades_per_quarter"]))

    full = {"label": "oiz-veto", "n_pct": N_PCT, "gate_p": GATE_P, "fee_pct": FEE_PCT,
            "q_grid": Q_GRID, "veto_feats": VETO_FEATS, "double_q": DOUBLE_Q,
            "regime_split": str(REGIME_SPLIT.date()),
            "first_oos": FIRST_OOS, "last": LAST, "oos_months": OOS_MONTHS, "seed": SEED,
            "n_gated": int(len(gated)), "n_quarters_pooled": n_quarters_all,
            "n_quarters_bull": n_bull, "n_quarters_chop": n_chop,
            "baseline": baseline, "veto_single": veto_single, "veto_double": double_pt}
    json.dump(full, open(os.path.join(OUT_DIR, "oiz_veto_results.json"), "w"), indent=2)

    # marker gon <2KB: baseline_net + per-feature per-Q {tpq,net,nb,nc,hr}
    def _compact(pt):
        return {"tpq": pt["trades_per_quarter"], "net": pt["net"],
                "nb": pt["net_bull"], "nc": pt["net_chop"], "hr": pt["hit_rate"]}

    marker = {"n_gated": int(len(gated)), "gate_p": GATE_P, "fee_pct": FEE_PCT,
              "baseline_net": baseline["net"], "baseline_tpq": baseline["trades_per_quarter"],
              "by_feat": {feat: {str(q): _compact(veto_single[feat][str(q)]) for q in Q_GRID}
                          for feat in VETO_FEATS},
              "double_0.7": _compact(double_pt)}
    line = "OIZVETO_RESULT " + json.dumps(marker, separators=(",", ":"))
    if len(line) >= 2000:
        log.warning("Marker qua 2KB (%d chars) — cat bot decimal.", len(line))
    print(line)
    log.info("XONG -> %s/oiz_veto_results.json", OUT_DIR)


if __name__ == "__main__":
    run()
