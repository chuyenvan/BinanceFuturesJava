#!/usr/bin/env python3
# SL4H — chien luoc "stop-loss cung sau 4h" (long-only, BO GATE, chi dung SELECTOR).
# Label sl4h (REGRESSION score, don vi %):
#   HIT : maxFav_4h >= N_PCT/100 (nBars_4h>=16)          -> score = N_PCT            (+diem duong = target %)
#   MISS: ret4h = retEnd_4h*100                          -> score = PEN*ret4h neu ret4h<0
#                                                            score = ret4h     neu ret4h>=0
# Tai dung 100% pipeline train_funding_selector_wfo (TASK-108): ff_*.bin (40 feat) + OI (5 feat),
#   merge_asof OI backward tol 2h theo symId, walk-forward EXPANDING fold, purge=4h, leak-free.
# Edge: LIFT@32 / LIFT@64 (top-k coin theo pred MOI moc ts, %HIT thuc / base_rate) + IC(spearman pred vs score).
# TACH BIET voi CDC n=3 (task 157 dca-hard): moi thu ten sl4h_nX, id kernel chuyendinh/sl4h-train-nX.
# Kaggle: dataset tu giai nen .gz -> .bin; mount doi -> glob de quy, khong hardcode path.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO LABEL (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = int(os.environ.get("N_PCT", "9"))    # <-- target % cho folder nay (n6/n9/n15)
PEN = float(os.environ.get("PEN", "1.5"))    # he so phat nhanh am (bat doi xung, y=1.5)
NEED_BARS = 16                               # nBars_4h >= 16 (du cua so 4h tren luoi 15m)
TOPK = [32, 64]                              # LIFT@k: top-k coin theo pred moi moc ts
RANDOM_REPS = 10                             # so lan lay ngau nhien de do baseline
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sl4h")


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


def load_labels():
    """Build score sl4h(N) tu funding_label.csv: HIT->N ; MISS->PEN*ret4h(neg) hoac ret4h(>=0)."""
    cols = ["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h"]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df["nBars_4h"] >= NEED_BARS) & df["maxFav_4h"].notna() & df["retEnd_4h"].notna()].copy()
    hit = (df["maxFav_4h"].values >= N_PCT / 100.0)
    ret4h = df["retEnd_4h"].values * 100.0
    miss = np.where(ret4h < 0, PEN * ret4h, ret4h)
    df["hit"] = hit.astype(np.int8)
    df["score"] = np.where(hit, float(N_PCT), miss).astype(np.float32)
    log.info("Label sl4h_n%d: %d/%d rows hop le | base_rate(HIT)=%.4f | score mean=%.4f p10=%.3f p50=%.3f p90=%.3f",
             N_PCT, len(df), n0, float(df.hit.mean()), float(df.score.mean()),
             float(np.percentile(df.score, 10)), float(np.percentile(df.score, 50)),
             float(np.percentile(df.score, 90)))
    return df[["ts", "symbol", "hit", "score"]]


def build_dataset():
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)                                   # symId,symbol
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    lb = load_labels()
    ds = merged.merge(lb, on=["symbol", "ts"], how="inner")     # exact-join symbol+ts (GIONG train cu)
    del t, o, merged, lb
    log.info("Dataset ghep: %d rows | n_sym=%d | base_rate=%.4f", len(ds), ds.symbol.nunique(),
             float(ds.hit.mean()))
    return ds.sort_values("ts").reset_index(drop=True)


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


def evaluate(te, pred):
    """LIFT@k (top-k coin theo pred MOI moc ts) + IC spearman(pred,score). Random baseline cung ts-group."""
    import scipy.stats as st
    d = te[["ts", "hit", "score"]].copy()
    d["pred"] = np.asarray(pred, dtype=float)
    base = float(d.hit.mean())
    ic = float(st.spearmanr(d["pred"].values, d["score"].values).correlation)
    rng = np.random.default_rng(SEED)
    ev = {"N": int(len(d)), "base_rate": round(base, 4), "IC": round(ic, 4)}
    groups = [g for _, g in d.groupby("ts")]
    for k in TOPK:
        gk = [g for g in groups if len(g) >= k]
        if not gk:
            ev[f"LIFT{k}"] = None
            continue
        top_hit = np.concatenate([g.nlargest(k, "pred")["hit"].values for g in gk])
        hit_top = float(top_hit.mean())
        rnd = []
        for _ in range(RANDOM_REPS):
            rr = np.concatenate([g["hit"].values[rng.choice(len(g), k, replace=False)] for g in gk])
            rnd.append(float(rr.mean()))
        hit_rnd = float(np.mean(rnd))
        ev[f"n_ts_ge{k}"] = len(gk)
        ev[f"hit_top{k}"] = round(hit_top, 4)
        ev[f"hit_rand{k}"] = round(hit_rnd, 4)
        ev[f"LIFT{k}"] = round(hit_top / base, 3) if base > 0 else None
        ev[f"LIFT{k}_vs_rand"] = round(hit_top / hit_rnd, 3) if hit_rnd > 0 else None
    return ev


def run():
    ds = build_dataset()
    if len(ds) == 0:
        raise SystemExit("Dataset rong sau merge - kiem alignment ts/symbol.")
    import xgboost as xgb
    folds = build_folds()
    log.info("SL4H n%d: %d fold expanding OOS=%dm | PEN=%.2f", N_PCT, len(folds), OOS_MONTHS, PEN)
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chi chay fold 0")

    per_fold = []
    purge = NEED_BARS * GRID_MS
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d) - bo", fi, len(tr), len(te))
            continue
        reg = xgb.XGBRegressor(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                               subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                               objective="reg:squarederror", eval_metric="rmse",
                               n_jobs=-1, tree_method="hist", random_state=SEED)
        reg.fit(tr[FEAT], tr["score"])
        pred = reg.predict(te[FEAT])
        ev = evaluate(te, pred)
        ev.update({"fold": fi, "n_train": int(len(tr)),
                   "oos_from": str(pd.to_datetime(cut, unit="ms").date()),
                   "oos_to": str(pd.to_datetime(oos_end, unit="ms").date())})
        per_fold.append(ev)
        log.info("fold %d [%s..%s] base=%.4f IC=%.4f LIFT32=%s LIFT64=%s (top32 hit=%s vs rand=%s)",
                 fi, ev["oos_from"], ev["oos_to"], ev["base_rate"], ev["IC"],
                 ev.get("LIFT32"), ev.get("LIFT64"), ev.get("hit_top32"), ev.get("hit_rand32"))

    def agg(key):
        vals = [f[key] for f in per_fold if f.get(key) is not None]
        return {"median": round(float(np.median(vals)), 4), "min": round(float(np.min(vals)), 4),
                "max": round(float(np.max(vals)), 4), "std": round(float(np.std(vals)), 4),
                "n": len(vals)} if vals else {"n": 0}

    summary = {"n_pct": N_PCT, "pen": PEN, "n_fold": len(per_fold),
               "LIFT32": agg("LIFT32"), "LIFT64": agg("LIFT64"), "IC": agg("IC"),
               "base_rate_median": round(float(np.median([f["base_rate"] for f in per_fold])), 4)
               if per_fold else None,
               "pct_fold_LIFT32_gt1": round(float(np.mean([f.get("LIFT32", 0) > 1
                    for f in per_fold if f.get("LIFT32") is not None])), 3) if per_fold else None,
               "pct_fold_IC_gt0": round(float(np.mean([f["IC"] > 0 for f in per_fold])), 3)
               if per_fold else None}

    out = {"label": "sl4h", "n_pct": N_PCT, "pen": PEN, "eval": "top-k per-ts LIFT + spearman IC",
           "first_oos": FIRST_OOS, "last": LAST, "oos_months": OOS_MONTHS, "seed": SEED,
           "summary": summary, "per_fold": per_fold}
    json.dump(out, open(os.path.join(OUT_DIR, f"sl4h_n{N_PCT}_results.json"), "w"), indent=2)
    # dong grep-able cuoi cung
    print("SL4H_RESULT " + json.dumps({"n_pct": N_PCT, "pen": PEN, "n_fold": summary["n_fold"],
          "LIFT32_med": summary["LIFT32"].get("median"), "LIFT64_med": summary["LIFT64"].get("median"),
          "IC_med": summary["IC"].get("median"), "base_rate_med": summary["base_rate_median"],
          "pct_fold_LIFT32_gt1": summary["pct_fold_LIFT32_gt1"],
          "pct_fold_IC_gt0": summary["pct_fold_IC_gt0"]}))
    log.info("XONG -> %s/sl4h_n%d_results.json", OUT_DIR, N_PCT)


if __name__ == "__main__":
    run()
