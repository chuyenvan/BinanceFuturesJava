#!/usr/bin/env python3
# EV2-FRONTIER — sinh DATA THO cho "frontier" (duong danh doi tan-suat <-> bien-net) cua selector EV2.
# MUC DICH: tra loi nhi phan "edge co du khong". Quet day nguong P* de xem tich
#   (tan_suat x bien-net-sau-phi) co cho nao vuot target khong hay tut deu ~ 0.
# BASE: sl4h-ev2-n6/run_train.py — tai dung 100% preamble load (ff+oi+label), walk-forward EXPANDING fold,
#   train clfP6 = P(maxFav_H>=0.06). BO regressor/EV; CHI dung classifier p6 + ke toan SL-cung.
# Ke toan SL-cung moi keo: HIT(maxFav_H>=0.06) -> +N_PCT% ; MISS -> retEnd_H*100 (%).
# net = gross - FEE_PCT (FEE_PCT %/keo round-trip). Tach REGIME theo ngay OOS fold:
#   BULL = oos_from < 2025-01-01 ; CHOP = oos_from >= 2025-01-01.
# LEAK-FREE: chi dung OOS moi fold, gop moi fold; KHONG tron IS.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = int(os.environ.get("N_PCT", "6"))     # target % (n6)
NEED_BARS_4H = 16                             # nBars_4h >= 16 (cua so 4h tren luoi 15m)
NEED_BARS_12H = 48                            # nBars_12h >= 48 (cua so 12h)
FEE_PCT = float(os.environ.get("FEE_PCT", "0.2"))   # %/keo round-trip (chi phi tru vao gross)
PSTAR_GRID = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
REGIME_SPLIT = pd.Timestamp("2025-01-01")     # BULL: oos_from < moc ; CHOP: >=
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ev2-frontier")


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


# ================= CLASSIFIER clfP6 (giu nguyen hyperparam tu base) =================
def fit_predict_clf(xgb, tr, te):
    """Model A (P HIT) — clfP6 target maxFav_H>=0.06 ; predict p6 OOS. KHONG dung regressor/EV."""
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit"])
    return clf.predict_proba(te[FEAT])[:, 1]


def collect_oos(xgb, feats, horizon, need_bars, folds):
    """Gop OOS moi fold (leak-free): cot p6, pnl (SL-cung), hit, oos_from, fold, regime.
       pnl/keo: HIT -> +N_PCT% ; MISS -> ret_pct thuc %."""
    lb = load_labels(horizon, need_bars)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("[%s] Dataset ghep: %d rows | base_rate=%.4f", horizon, len(ds), float(ds.hit.mean()))
    rows = []
    fold_meta = []       # (fold_idx, oos_from_ts, regime)
    purge = need_bars * GRID_MS
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("[%s] fold %d thieu data (tr=%d te=%d hit=%d) - bo", horizon, fi,
                        len(tr), len(te), int(tr["hit"].sum()))
            continue
        p6 = fit_predict_clf(xgb, tr, te)
        oos_from = pd.to_datetime(cut, unit="ms")
        regime = "bull" if oos_from < REGIME_SPLIT else "chop"
        pnl = np.where(te["hit"].values == 1, float(N_PCT), te["ret_pct"].values.astype(float))
        sub = pd.DataFrame({"p6": np.asarray(p6, dtype=float),
                            "pnl": pnl.astype(float),
                            "hit": te["hit"].values.astype(int),
                            "fold": fi,
                            "regime": regime})
        rows.append(sub)
        fold_meta.append((fi, str(oos_from.date()), regime))
        log.info("[%s] fold %d [%s] regime=%s n_oos=%d base=%.4f p6[med=%.3f p90=%.3f]",
                 horizon, fi, str(oos_from.date()), regime, len(sub), float(te["hit"].mean()),
                 float(np.median(p6)), float(np.percentile(p6, 90)))
    if not rows:
        return None, []
    return pd.concat(rows, ignore_index=True), fold_meta


def _stats(gated, n_quarters):
    """Do (n_trades, trades_per_quarter, gross, net, hit_rate) tren tap gated cho so quy cho truoc."""
    n = int(len(gated))
    if n == 0 or n_quarters == 0:
        return {"n_trades": n, "trades_per_quarter": 0.0, "gross": None, "net": None, "hit_rate": None}
    gross = float(gated["pnl"].mean())
    return {"n_trades": n,
            "trades_per_quarter": round(n / n_quarters, 3),
            "gross": round(gross, 4),
            "net": round(gross - FEE_PCT, 4),
            "hit_rate": round(float(gated["hit"].mean()), 4)}


def sweep_horizon(horizon, pooled, fold_meta):
    """Sweep P* grid. Voi moi P*: pooled + regime bull/chop + rough return proxy (SERIAL upper-bound)."""
    n_folds_total = len({m[0] for m in fold_meta})
    n_bull = len({m[0] for m in fold_meta if m[2] == "bull"})
    n_chop = len({m[0] for m in fold_meta if m[2] == "chop"})
    log.info("[%s] SWEEP: n_folds=%d (bull=%d chop=%d) FEE_PCT=%.3f", horizon, n_folds_total,
             n_bull, n_chop, FEE_PCT)
    bull = pooled[pooled["regime"] == "bull"]
    chop = pooled[pooled["regime"] == "chop"]
    points = []
    for ps in PSTAR_GRID:
        g_all = pooled[pooled["p6"] >= ps]
        g_bull = bull[bull["p6"] >= ps]
        g_chop = chop[chop["p6"] >= ps]
        s_all = _stats(g_all, n_folds_total)
        # net_total_pct: SERIAL upper-bound (KHONG phai return that) — tong net/keo tren toan tap gated / so quy.
        net_total_pct = (round(float((g_all["pnl"] - FEE_PCT).sum()) / n_folds_total, 3)
                         if n_folds_total and len(g_all) else 0.0)
        pt = {"horizon": horizon, "pstar": ps,
              "n_trades": s_all["n_trades"],
              "trades_per_quarter": s_all["trades_per_quarter"],
              "gross": s_all["gross"], "net": s_all["net"], "hit_rate": s_all["hit_rate"],
              "regime_pooled": s_all,
              "regime_bull": _stats(g_bull, n_bull),
              "regime_chop": _stats(g_chop, n_chop),
              "net_total_pct": net_total_pct}
        points.append(pt)
        log.info("[%s] P*>=%.2f : n=%d tpq=%.2f gross=%s net=%s hit=%s | bull_net=%s chop_net=%s",
                 horizon, ps, s_all["n_trades"], s_all["trades_per_quarter"], s_all["gross"],
                 s_all["net"], s_all["hit_rate"], pt["regime_bull"]["net"], pt["regime_chop"]["net"])
    return points


def compact_row(pt):
    return {"pstar": pt["pstar"], "tpq": pt["trades_per_quarter"], "net": pt["net"],
            "net_bull": pt["regime_bull"]["net"], "net_chop": pt["regime_chop"]["net"]}


def run():
    cols = label_columns()
    has12 = all(c in cols for c in ["maxFav_12h", "retEnd_12h", "nBars_12h"])
    horizons = [("4h", NEED_BARS_4H)]
    if has12:
        horizons.append(("12h", NEED_BARS_12H))
    else:
        log.info("NO_12H — khong co cot 12h, chi chay horizon 4h.")

    feats = build_features()
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold dau")
    log.info("EV2-FRONTIER n%d: %d fold expanding OOS=%dm | FEE_PCT=%.3f | horizons=%s",
             N_PCT, len(folds), OOS_MONTHS, FEE_PCT, [h for h, _ in horizons])

    all_points = []
    compact = {}
    for horizon, need in horizons:
        pooled, fold_meta = collect_oos(xgb, feats, horizon, need, folds)
        if pooled is None:
            log.warning("[%s] khong fold hop le — bo horizon.", horizon)
            continue
        points = sweep_horizon(horizon, pooled, fold_meta)
        all_points.extend(points)
        # ~5 diem dai dien: 0.4/0.5/0.6/0.7/0.8
        reps = [pt for pt in points if abs(pt["pstar"] - round(pt["pstar"], 1)) < 1e-9
                and pt["pstar"] in (0.4, 0.5, 0.6, 0.7, 0.8)]
        compact[horizon] = [compact_row(pt) for pt in reps]

    if not all_points:
        raise SystemExit("Khong horizon nao hop le — kiem alignment ts/symbol.")

    out = {"label": "ev2-frontier", "n_pct": N_PCT, "fee_pct": FEE_PCT,
           "pstar_grid": PSTAR_GRID, "regime_split": str(REGIME_SPLIT.date()),
           "first_oos": FIRST_OOS, "last": LAST, "oos_months": OOS_MONTHS, "seed": SEED,
           "note_net_total_pct": "SERIAL upper-bound (trade noi tiep full-von) — KHONG phai return that",
           "points": all_points}
    json.dump(out, open(os.path.join(OUT_DIR, "ev2_frontier_results.json"), "w"), indent=2)
    log.info("XONG -> %s/ev2_frontier_results.json", OUT_DIR)

    # dong cuoi <2KB de doc shape nhanh
    print("FRONTIER_RESULT " + json.dumps({"n_pct": N_PCT, "fee_pct": FEE_PCT, "byH": compact},
                                          separators=(",", ":")))


if __name__ == "__main__":
    run()
