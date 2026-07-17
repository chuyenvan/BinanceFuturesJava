#!/usr/bin/env python3
# SL4H-TRAIL-COND — trailing DIEU KIEN theo conviction model entry (P9), so voi E4 co dinh.
# Y tuong (Bac 1, KHONG train model exit moi): dung P(HIT9%) lam tin hieu conviction tai entry de
#   chon HORIZON nuoi: P9 cao -> nuoi 24h ; P9 giua -> nuoi 12h (E4) ; P9 thap -> dong cung 4h (E1).
# Baseline = E4 co dinh (nuoi 12h san +1% cho moi keo hit3). Ke toan: keo hit3 nuoi theo horizon,
#   san +1% (proxy trailing arm SL); thieu cua so -> fallback dong cung 4h. Gate = P6>=0.7.
# Reuse 100% preamble load cua sl4h-ev2-n6.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

N_PCT = int(os.environ.get("N_PCT", "6"))
NEED_4H, NEED_12H, NEED_24H = 16, 48, 96
PSTAR = float(os.environ.get("PSTAR", "0.7"))
FLOOR = float(os.environ.get("FLOOR", "1.0"))          # san +1% khi nuoi (proxy trailing arm)
MIN_TRADES_FOLD = 30
SEED = int(os.environ.get("SEED", "42"))
GRID_MS = 15 * 60 * 1000
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sl4h-trail-cond")


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
SMOKE = os.environ.get("SMOKE", "0") == "1"
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


def load_labels():
    cols = ["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h",
            "retEnd_12h", "nBars_12h", "retEnd_24h", "nBars_24h"]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    df = df[(df["nBars_4h"] >= NEED_4H) & df["maxFav_4h"].notna() & df["retEnd_4h"].notna()].copy()
    mf = df["maxFav_4h"].values
    df["hit3"] = (mf >= 0.03).astype(np.int8)
    df["hit6"] = (mf >= N_PCT / 100.0).astype(np.int8)
    df["hit9"] = (mf >= 0.09).astype(np.int8)
    df["r4"] = (df["retEnd_4h"].values * 100.0).astype(np.float32)
    df["r12"] = (df["retEnd_12h"].values * 100.0).astype(np.float32)
    df["r24"] = (df["retEnd_24h"].values * 100.0).astype(np.float32)
    df["ok12"] = (df["nBars_12h"].fillna(0).values >= NEED_12H).astype(np.int8)
    df["ok24"] = (df["nBars_24h"].fillna(0).values >= NEED_24H).astype(np.int8)
    log.info("Label n%d: %d rows | hit3=%.3f hit6=%.3f hit9=%.3f",
             N_PCT, len(df), float(df.hit3.mean()), float(df.hit6.mean()), float(df.hit9.mean()))
    keep = ["ts", "symbol", "hit3", "hit6", "hit9", "r4", "r12", "r24", "ok12", "ok24"]
    return df[keep]


def build_folds():
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def exit_e1(s):
    return s["r4"].values.astype(float)


def exit_nuoi(s, horizon):
    """hit3 -> nuoi toi horizon voi san FLOOR (fallback dong 4h neu thieu cua so); else dong 4h."""
    r4 = s["r4"].values.astype(float)
    if horizon == 12:
        rr, ok = s["r12"].values.astype(float), s["ok12"].values
    else:
        rr, ok = s["r24"].values.astype(float), s["ok24"].values
    nuoi = np.where(ok == 1, np.maximum(FLOOR, rr), r4)
    return np.where(s["hit3"].values == 1, nuoi, r4)


def run():
    feats = build_features()
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows", len(ds))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
    purge = NEED_4H * GRID_MS

    variants = ["E1", "E4_fixed", "E5_fixed", "COND"]
    hist = {v: {"pnl": [], "n": []} for v in variants}
    tier_hist = {"hi": [], "mid": [], "lo": []}
    auc6_hist, auc9_hist = [], []

    def fit(xgb, tr, te, y):
        from sklearn.metrics import roc_auc_score
        c = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                              subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                              objective="binary:logistic", eval_metric="logloss",
                              n_jobs=-1, tree_method="hist", random_state=SEED)
        c.fit(tr[FEAT], tr[y])
        p = c.predict_proba(te[FEAT])[:, 1]
        try:
            a = float(roc_auc_score(te[y], p)) if te[y].nunique() > 1 else None
        except Exception:
            a = None
        return p, a

    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit6"].sum() < 50 or (tr["hit6"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d) - bo", fi, len(tr), len(te))
            continue
        p6, a6 = fit(xgb, tr, te, "hit6")
        p9, a9 = fit(xgb, tr, te, "hit9")
        if a6 is not None:
            auc6_hist.append(a6)
        if a9 is not None:
            auc9_hist.append(a9)
        mask = p6 >= PSTAR
        sel = te[mask].copy()
        p9_sel = p9[mask]
        if len(sel) < 5:
            continue
        # baselines
        e1 = exit_e1(sel)
        e4 = exit_nuoi(sel, 12)
        e5 = exit_nuoi(sel, 24)
        # COND: tercile P9 trong gated set -> hi nuoi24, mid nuoi12, lo dong4
        lo_q, hi_q = np.quantile(p9_sel, [0.33, 0.67])
        tier_hi = p9_sel >= hi_q
        tier_lo = p9_sel < lo_q
        cond = np.where(tier_hi, e5, np.where(tier_lo, e1, e4))
        pnls = {"E1": e1, "E4_fixed": e4, "E5_fixed": e5, "COND": cond}
        for v in variants:
            hist[v]["pnl"].append(float(pnls[v].mean()))
            hist[v]["n"].append(int(len(sel)))
        tier_hist["hi"].append(float(e5[tier_hi].mean()) if tier_hi.any() else None)
        tier_hist["mid"].append(float(e4[(~tier_hi) & (~tier_lo)].mean())
                                if ((~tier_hi) & (~tier_lo)).any() else None)
        tier_hist["lo"].append(float(e1[tier_lo].mean()) if tier_lo.any() else None)
        log.info("fold %d [%s] n_gate=%d AUC6=%s AUC9=%s | E1=%.3f E4=%.3f E5=%.3f COND=%.3f",
                 fi, str(pd.to_datetime(cut, unit="ms").date()), len(sel),
                 round(a6, 3) if a6 else None, round(a9, 3) if a9 else None,
                 hist["E1"]["pnl"][-1], hist["E4_fixed"]["pnl"][-1],
                 hist["E5_fixed"]["pnl"][-1], hist["COND"]["pnl"][-1])

    def med(v):
        v = [x for x in v if x is not None]
        return round(float(np.median(v)), 4) if v else None

    def worst(v):
        v = [x for x in v if x is not None]
        return round(float(np.min(v)), 4) if v else None

    summary = {v: {"pnl_med": med(hist[v]["pnl"]), "worst_fold": worst(hist[v]["pnl"]),
                   "n_med": med(hist[v]["n"])} for v in variants}
    result = {"n_pct": N_PCT, "pstar": PSTAR, "floor": FLOOR,
              "auc6_med": med(auc6_hist), "auc9_med": med(auc9_hist),
              "variants": summary,
              "cond_tiers": {"hi_nuoi24": med(tier_hist["hi"]), "mid_nuoi12": med(tier_hist["mid"]),
                             "lo_dong4": med(tier_hist["lo"])}}
    json.dump(result, open(os.path.join(OUT_DIR, "sl4h_trail_cond_results.json"), "w"), indent=2)
    print("\n===== TRAIL-COND n%d gate>=%.1f floor=%.1f =====" % (N_PCT, PSTAR, FLOOR))
    print("AUC6=%s AUC9=%s" % (result["auc6_med"], result["auc9_med"]))
    for v in variants:
        s = summary[v]
        print("  %-9s pnl/keo=%s worst_fold=%s n=%s" % (v, s["pnl_med"], s["worst_fold"], s["n_med"]))
    print("  tiers:", result["cond_tiers"])
    print("TRAILCOND_RESULT " + json.dumps(result))


if __name__ == "__main__":
    run()
