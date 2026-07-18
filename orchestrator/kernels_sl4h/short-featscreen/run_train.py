#!/usr/bin/env python3
# SHORT-FEATSCREEN — conditional-edge feature screen cho SHORT (BUCKET-SPLIT, KHONG retrain).
# Muc tieu: short hien dung Y HET 45 feature cua long (chua screen rieng cho dump). Gia thuyet:
#   co feature "conditioning" tach duoc dump manh/yeu (funding cao, OI spike, RSI qua mua,
#   dist-tren-SMA...) — KHAC voi feature co edge cho pump/long.
# PHUONG PHAP (leak-free, tai dung 100% pipeline load+fold cua feat-screen/short-selector):
#   1) Label HIT_short = drop>=6% trong 12h (drop=-maxAdv_12h*100, nBars_12h>=48) — GIU NGUYEN,
#      KHONG dieu kien thu tu tHitFav/tHitAdv (khac short-selector) vi o day chi can target
#      train classifier P(HIT_short), khong phai ke toan.
#   2) Train clfP(HIT_short) walk-forward (expanding, purge) tren 45 feat GIONG sl4h-ev2-n6,
#      predict ps tren OOS.
#   3) GATED = OOS co ps trong TOP theo RANK (ps short thap, KHONG dung nguong tuyet doi):
#      mac dinh GATE_MODE=rank — top GATE_TOP_PCT (=20%) MOI MOC (nhom theo ts, rank ps trong
#      cung 1 thoi diem). GATE_MODE=quantile — ps >= quantile(GATE_QUANTILE=0.8) TOAN CUC (pool
#      het OOS moi fold roi tinh 1 nguong duy nhat).
#   4) Ke toan SHORT tren GATED (SL-cung stop=20%, path-aware):
#        stopped (rise>=20 & tHitFav_12h<tHitAdv_12h) -> pnl = -20
#        elif drop>=6                                  -> pnl = +6
#        else                                           -> pnl = -retEnd_12h*100
#      net = mean(pnl) - 0.2% (phi 2 chan). KHONG funding (chi screen dieu kien, khong ke toan cuoi).
#   5) Voi MOI feature trong 45 (f0..f39 + 5 OI): chia GATED thanh N_BUCKET(=5) quantile theo
#      feature -> per-bucket n / mean pnl short / hit_rate(=P(drop>=6% trong bucket)).
#      edge_spread = pnl(bucket cao nhat) - pnl(bucket thap nhat) ; monotonic = |spearman(bucket_idx,bucket_pnl)|.
#   6) Xep 45 feature theo |edge_spread| giam dan, in top-15, marker <2KB.
# KHONG retrain selector that, KHONG deploy, KHONG dung WFO Oracle — chi screen dieu kien.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
HORIZON = os.environ.get("HORIZON", "12h")                 # dump cham hon pump -> horizon dai hon (4h)
N_PCT_DROP = int(os.environ.get("N_PCT_DROP", "6"))         # nguong HIT_short: drop >= 6%
NEED_BARS_12H = int(os.environ.get("NEED_BARS_12H", "48"))  # nBars_12h >= 48 (cua so 12h tren luoi 15m)
STOP_PCT = float(os.environ.get("STOP_PCT", "20"))          # hard-SL short (rise>=20% -> stopped)
GATE_MODE = os.environ.get("GATE_MODE", "rank")             # "rank" (top% moi moc) | "quantile" (nguong toan cuc)
GATE_TOP_PCT = float(os.environ.get("GATE_TOP_PCT", "0.20"))    # rank mode: top 20% moi moc (theo ts)
GATE_QUANTILE = float(os.environ.get("GATE_QUANTILE", "0.8"))   # quantile mode: ps >= quantile(0.8) toan cuc
N_BUCKET = int(os.environ.get("N_BUCKET", "5"))             # so bucket (quantile) moi feature
TOP_PRINT = int(os.environ.get("TOP_PRINT", "15"))
FEE_PCT = 0.2                                               # phi 2 chan 0.1%*2
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector (long va short dung chung)
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("short-featscreen")


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


def check_12h_columns(cols):
    """Bat buoc co du cot 12h — neu thieu, BAO RO va dung (khong doan/fallback am tham)."""
    need = [f"maxFav_{HORIZON}", f"maxAdv_{HORIZON}", f"tHitFav_{HORIZON}",
            f"tHitAdv_{HORIZON}", f"retEnd_{HORIZON}", f"nBars_{HORIZON}"]
    missing = [c for c in need if c not in cols]
    if missing:
        raise SystemExit(f"NO_{HORIZON.upper()} — funding_label.csv THIEU cot: {missing}. "
                          f"Kiem tra dataset chuyendinh/funding-label-full da export horizon {HORIZON} chua.")
    log.info("OK: du cot %s trong funding_label.csv", HORIZON)


def build_features():
    """Merged features (ts, symId, 45 feat, symbol)."""
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)                                   # symId,symbol
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    del t, o
    log.info("Features ghep: %d rows | n_sym=%d", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def load_short_labels(horizon, need_bars):
    """Label SHORT don gian cho screen: hit_short = drop>=N_PCT_DROP% (KHONG dieu kien thu tu
    tHitFav/tHitAdv — khac short-selector, vi day chi la target train classifier de xep hang ps,
    khong phai ke toan). Cot ke toan (rise, tfav, tadv, retpct) van giu de tinh pnl sau."""
    cf, ca = f"maxFav_{horizon}", f"maxAdv_{horizon}"
    tf, ta = f"tHitFav_{horizon}", f"tHitAdv_{horizon}"
    cr, cn = f"retEnd_{horizon}", f"nBars_{horizon}"
    df = pd.read_csv(LABEL_CSV, usecols=["tEpochMs", "symbol", cf, ca, tf, ta, cr, cn],
                     on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df[cn] >= need_bars) & df[cf].notna() & df[ca].notna() & df[cr].notna()].copy()
    rise = (df[cf].values * 100.0).astype(np.float32)          # do tang (bat loi short), duong
    drop = (-df[ca].values * 100.0).astype(np.float32)         # do sau giam (loi short), duong
    tfav = df[tf].values.astype(np.float32)                    # phut toi dinh
    tadv = df[ta].values.astype(np.float32)                    # phut toi day
    retpct = (df[cr].values * 100.0).astype(np.float32)         # retEnd% (close-to-close)
    hit_short = (drop >= float(N_PCT_DROP)).astype(np.int8)
    out = pd.DataFrame({"ts": df["ts"].values, "symbol": df["symbol"].values,
                        "hit_short": hit_short, "rise": rise, "drop": drop,
                        "tfav": tfav, "tadv": tadv, "retpct": retpct})
    log.info("Label SHORT %s N%d: %d/%d rows | base_rate(HIT_short)=%.4f | drop p50=%.2f p90=%.2f",
             horizon, N_PCT_DROP, len(out), n0, float(out.hit_short.mean()),
             float(np.percentile(drop, 50)), float(np.percentile(drop, 90)))
    return out


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


def fit_predict_short(xgb, tr, te):
    """clfP(HIT_short) — dung Y HET hyperparam base kernel sl4h-ev2-n6 / feat-screen."""
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit_short"])
    return clf.predict_proba(te[FEAT])[:, 1]


def pnl_short(g):
    """Ke toan SHORT SL-cung stop=20%, path-aware (vector hoa):
       stopped (rise>=STOP_PCT & tfav<tadv) -> -STOP_PCT
       elif drop>=N_PCT_DROP                -> +N_PCT_DROP
       else                                 -> -retpct
    """
    rise = g["rise"].values
    tfav = g["tfav"].values
    tadv = g["tadv"].values
    drop = g["drop"].values
    retpct = g["retpct"].values
    stopped = (rise >= STOP_PCT) & (tfav < tadv)
    hit = drop >= float(N_PCT_DROP)
    pnl = np.where(stopped, -float(STOP_PCT), np.where(hit, float(N_PCT_DROP), -retpct))
    return pnl.astype(np.float64)


def collect_gated(xgb, feats, folds):
    """Moi fold: train clfP(HIT_short) tren IS -> predict ps tren OOS. Gop het OOS (leak-free,
    chi predict, chua gate) roi GATE mot lan theo GATE_MODE (rank moi moc | quantile toan cuc)."""
    lb = load_short_labels(HORIZON, NEED_BARS_12H)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | base_rate(HIT_short)=%.4f", len(ds), float(ds.hit_short.mean()))
    purge = NEED_BARS_12H * GRID_MS
    keep = FEAT + ["ts", "hit_short", "rise", "drop", "tfav", "tadv", "retpct"]
    te_parts = []
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit_short"].sum() < 50 or (tr["hit_short"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d hit=%d) - bo", fi,
                        len(tr), len(te), int(tr["hit_short"].sum()))
            continue
        ps = fit_predict_short(xgb, tr, te)
        te = te[keep].copy()
        te["ps"] = ps
        te_parts.append(te)
        log.info("fold %d [%s..%s]: OOS=%d ps_mean=%.4f base(hit_short)=%.4f",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()), len(te),
                 float(te["ps"].mean()), float(te["hit_short"].mean()))
    if not te_parts:
        raise SystemExit("Khong fold nao hop le — kiem alignment ts/symbol.")
    allte = pd.concat(te_parts, ignore_index=True)

    if GATE_MODE == "rank":
        allte["rank_pct"] = allte.groupby("ts")["ps"].rank(pct=True, method="average")
        gated = allte[allte["rank_pct"] >= (1.0 - GATE_TOP_PCT)].copy()
        log.info("GATE_MODE=rank: top %.0f%% ps moi moc (nhom theo ts)", GATE_TOP_PCT * 100)
    elif GATE_MODE == "quantile":
        thr = float(allte["ps"].quantile(GATE_QUANTILE))
        gated = allte[allte["ps"] >= thr].copy()
        log.info("GATE_MODE=quantile: nguong ps>=%.4f (quantile toan cuc=%.2f)", thr, GATE_QUANTILE)
    else:
        raise SystemExit(f"GATE_MODE khong hop le: {GATE_MODE} (chi 'rank' hoac 'quantile')")

    gated["pnl"] = pnl_short(gated)
    gated["hit"] = gated["hit_short"]           # dung ten "hit" chung cho screen_feature (giong feat-screen)
    log.info("GATED gop toan bo fold: %d/%d keo | pnl_mean=%.4f | net=%.4f | hit_rate=%.4f",
             len(gated), len(allte), float(gated["pnl"].mean()),
             float(gated["pnl"].mean()) - FEE_PCT, float(gated["hit"].mean()))
    return gated


def screen_feature(gated, feat):
    """Chia GATED thanh N_BUCKET quantile theo `feat` (bo NaN). Tra per-bucket n/pnl/hit_rate +
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
    cols = label_columns()
    check_12h_columns(cols)
    feats = build_features()
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold dau")
    log.info("SHORT-FEATSCREEN [%s] N%d(drop) STOP=%.0f%%: %d fold expanding OOS=%dm | "
             "GATE_MODE=%s GATE_TOP_PCT=%.2f GATE_QUANTILE=%.2f | N_BUCKET=%d",
             HORIZON, N_PCT_DROP, STOP_PCT, len(folds), OOS_MONTHS, GATE_MODE,
             GATE_TOP_PCT, GATE_QUANTILE, N_BUCKET)

    gated = collect_gated(xgb, feats, folds)

    rows = [r for r in (screen_feature(gated, f) for f in FEAT) if r is not None]
    # xep theo |edge_spread| giam dan
    rows.sort(key=lambda r: abs(r["edge_spread"]), reverse=True)

    print(f"\n===== SHORT-FEATSCREEN conditional-edge [{HORIZON}] (GATED %s, N=%d keo, %d bucket) ====="
          % (GATE_MODE, len(gated), N_BUCKET))
    print("rank feat         edge_spread monotonic  bucket_pnls                         n_total")
    for i, r in enumerate(rows[:TOP_PRINT]):
        print("%3d  %-11s %+8.4f   %6.3f    %-34s %d" % (
            i + 1, r["feat"], r["edge_spread"], r["monotonic"],
            str(r["bucket_pnls"]), r["n_total"]))

    # file day du
    full = {"label": "short-featscreen", "horizon": HORIZON, "n_pct_drop": N_PCT_DROP,
            "stop_pct": STOP_PCT, "gate_mode": GATE_MODE, "gate_top_pct": GATE_TOP_PCT,
            "gate_quantile": GATE_QUANTILE, "n_bucket": N_BUCKET,
            "first_oos": FIRST_OOS, "last": LAST, "oos_months": OOS_MONTHS, "seed": SEED,
            "n_gated": int(len(gated)),
            "gated_pnl_mean": round(float(gated["pnl"].mean()), 4),
            "gated_net": round(float(gated["pnl"].mean()) - FEE_PCT, 4),
            "gated_hit_rate": round(float(gated["hit"].mean()), 4),
            "ranked": rows}
    json.dump(full, open(os.path.join(OUT_DIR, "short_featscreen_results.json"), "w"), indent=2)

    # marker gon <2KB: top-15 {feat, edge_spread, monotonic, bucket_pnls}
    top = [{"feat": r["feat"], "edge_spread": r["edge_spread"], "monotonic": r["monotonic"],
            "bucket_pnls": r["bucket_pnls"]} for r in rows[:15]]
    marker = {"horizon": HORIZON, "n_gated": int(len(gated)),
              "gated_pnl_mean": round(float(gated["pnl"].mean()), 4),
              "gate_mode": GATE_MODE, "n_bucket": N_BUCKET, "top15": top}
    print("SHORT_FEATSCREEN_RESULT " + json.dumps(marker, separators=(",", ":")))
    log.info("XONG -> %s/short_featscreen_results.json", OUT_DIR)


if __name__ == "__main__":
    run()
