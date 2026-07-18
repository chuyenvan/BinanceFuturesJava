#!/usr/bin/env python3
# FEAT-SCREEN — conditional-edge feature screen (BUCKET-SPLIT, KHONG retrain).
# Muc tieu: entry selector EV2 (clfP6 P(HIT+6%/4h)) chi co edge mong (+0.72/keo gross -> breakeven
#   capital-constrained). Gia thuyet: co feature "conditioning" (vd regime dai han) tach duoc
#   entry tot/xau. Screen RE: voi moi feature, chia tap GATED (OOS rows p6>=0.7) theo decile/quantile
#   cua feature -> do PnL/keo tung bucket. Neu edge tach ro giua bucket -> feature mang thong tin
#   conditioning -> dang dung (entry-veto hoac them vao model).
# PHUONG PHAP (leak-free): CHI dung OOS rows; bucket theo gia tri feature TAI ENTRY (<=t, khong leak).
#   edge_spread = pnl(bucket cao nhat) - pnl(bucket thap nhat) ; monotonic = |spearman(bucket_idx, bucket_pnl)|.
# Tai dung 100% pipeline load + fold + train clfP6 tu sl4h-ev2-n6 (proven). Chi thay phan eval.
# Ke toan SL-cung 4h: HIT6 -> +6 ; MISS -> retEnd_4h*100 (giong base kernel).
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = int(os.environ.get("N_PCT", "6"))    # target % (n6 lam dai dien)
NEED_BARS_4H = 16                            # nBars_4h >= 16 (cua so 4h tren luoi 15m)
GATE_P = float(os.environ.get("GATE_P", "0.7"))   # nguong p6 de vao tap GATED (giong PSTAR cao)
N_BUCKET = int(os.environ.get("N_BUCKET", "5"))   # so bucket (quantile) moi feature
TOP_PRINT = int(os.environ.get("TOP_PRINT", "15"))
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("feat-screen")


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


def fit_predict_p6(xgb, tr, te):
    """clfP6 = P(HIT+6%/4h) — dung Y HET hyperparam base kernel sl4h-ev2-n6."""
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit"])
    return clf.predict_proba(te[FEAT])[:, 1]


def collect_gated(xgb, feats, folds):
    """Moi fold: train clfP6 tren IS -> predict p6 tren OOS -> lay GATED (p6>=GATE_P).
       Gop GATED moi fold (leak-free: chi OOS). pnl = HIT ? +N_PCT : ret_pct (SL-cung)."""
    lb = load_labels("4h", NEED_BARS_4H)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | base_rate=%.4f", len(ds), float(ds.hit.mean()))
    purge = NEED_BARS_4H * GRID_MS
    keep = FEAT + ["hit", "ret_pct"]
    gated_parts = []
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d hit=%d) - bo", fi,
                        len(tr), len(te), int(tr["hit"].sum()))
            continue
        p6 = fit_predict_p6(xgb, tr, te)
        te = te.copy()
        te["p6"] = p6
        g = te[te["p6"] >= GATE_P][keep].copy()
        g["pnl"] = np.where(g["hit"].values == 1, float(N_PCT), g["ret_pct"].values)
        gated_parts.append(g)
        log.info("fold %d [%s..%s]: OOS=%d gated=%d (p6>=%.2f) gated_pnl_mean=%.4f gated_hit=%.4f",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()), len(te), len(g), GATE_P,
                 float(g["pnl"].mean()) if len(g) else float("nan"),
                 float(g["hit"].mean()) if len(g) else float("nan"))
    if not gated_parts:
        raise SystemExit("Khong fold nao hop le — kiem alignment ts/symbol.")
    gated = pd.concat(gated_parts, ignore_index=True)
    log.info("GATED gop toan bo fold: %d keo | pnl_mean=%.4f | hit=%.4f",
             len(gated), float(gated["pnl"].mean()), float(gated["hit"].mean()))
    return gated


def screen_feature(gated, feat):
    """Chia GATED thanh N_BUCKET quantile theo `feat` (bo NaN). Tra per-bucket n/pnl/hit6 +
       edge_spread (bucket cao - bucket thap) + monotonic |spearman(bucket_idx, bucket_pnl)|."""
    import scipy.stats as st
    d = gated[[feat, "pnl", "hit"]].dropna(subset=[feat])
    if len(d) < N_BUCKET * 5:
        return None
    try:
        cats = pd.qcut(d[feat], N_BUCKET, labels=False, duplicates="drop")
    except (ValueError, IndexError):
        return None
    d = d.assign(b=cats.values)
    nb = int(d["b"].nunique())
    if nb < 2:
        return None
    grp = d.groupby("b")
    idx = sorted(d["b"].unique())
    bucket_pnl = [round(float(grp.get_group(b)["pnl"].mean()), 4) for b in idx]
    bucket_hit = [round(float(grp.get_group(b)["hit"].mean()), 4) for b in idx]
    bucket_n = [int(len(grp.get_group(b))) for b in idx]
    edge_spread = round(bucket_pnl[-1] - bucket_pnl[0], 4)          # cao nhat - thap nhat
    sp = st.spearmanr(idx, bucket_pnl).correlation
    monotonic = round(abs(float(sp)), 4) if sp is not None and not np.isnan(sp) else 0.0
    return {"feat": feat, "n_buckets": nb, "edge_spread": edge_spread, "monotonic": monotonic,
            "bucket_pnls": bucket_pnl, "bucket_hits": bucket_hit, "bucket_n": bucket_n,
            "n_total": int(len(d))}


def run():
    label_columns()
    feats = build_features()
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold dau")
    log.info("FEAT-SCREEN n%d: %d fold expanding OOS=%dm | GATE_P=%.2f | N_BUCKET=%d",
             N_PCT, len(folds), OOS_MONTHS, GATE_P, N_BUCKET)

    gated = collect_gated(xgb, feats, folds)

    rows = [r for r in (screen_feature(gated, f) for f in FEAT) if r is not None]
    # xep theo |edge_spread| giam dan
    rows.sort(key=lambda r: abs(r["edge_spread"]), reverse=True)

    print(f"\n===== FEAT-SCREEN conditional-edge (GATED p6>=%.2f, N=%d keo, %d bucket) =====" % (
        GATE_P, len(gated), N_BUCKET))
    print("rank feat         edge_spread monotonic  bucket_pnls                         n_total")
    for i, r in enumerate(rows[:TOP_PRINT]):
        print("%3d  %-11s %+8.4f   %6.3f    %-34s %d" % (
            i + 1, r["feat"], r["edge_spread"], r["monotonic"],
            str(r["bucket_pnls"]), r["n_total"]))

    # file day du
    full = {"label": "feat-screen", "gate_p": GATE_P, "n_bucket": N_BUCKET,
            "n_pct": N_PCT, "first_oos": FIRST_OOS, "last": LAST, "oos_months": OOS_MONTHS,
            "seed": SEED, "n_gated": int(len(gated)),
            "gated_pnl_mean": round(float(gated["pnl"].mean()), 4),
            "gated_hit_rate": round(float(gated["hit"].mean()), 4),
            "ranked": rows}
    json.dump(full, open(os.path.join(OUT_DIR, "feat_screen_results.json"), "w"), indent=2)

    # marker gon <2KB: top-15 {feat, edge_spread, monotonic, bucket_pnls}
    top = [{"feat": r["feat"], "edge_spread": r["edge_spread"], "monotonic": r["monotonic"],
            "bucket_pnls": r["bucket_pnls"]} for r in rows[:15]]
    marker = {"n_gated": int(len(gated)),
              "gated_pnl_mean": round(float(gated["pnl"].mean()), 4),
              "gate_p": GATE_P, "n_bucket": N_BUCKET, "top15": top}
    print("FEATSCREEN_RESULT " + json.dumps(marker, separators=(",", ":")))
    log.info("XONG -> %s/feat_screen_results.json", OUT_DIR)


if __name__ == "__main__":
    run()
