#!/usr/bin/env python3
# SHORT-GRID — grid tim LABEL SHORT tot nhat cho MOT horizon H (chia 4 kernel chay SONG SONG).
#   Grid: TARGET t in {3,6,9,15}% x STOP s in {8,15,20,30}% x selection (P* {0.30..0.70} HOAC topK/moc).
#   Phase-1 PROXY: label tu cot SAN CO trong funding_label.csv (KHONG re-export Java — de dank validate winner sau).
#
# TAI DUNG 100% pipeline load cua short-selector / sl4h-ev2-n6 (ff_*.bin 40 feat + OI 5 feat + funding_label.csv),
#   walk-forward EXPANDING fold, purge theo nBars, leak-free. Chi thay LABEL(theo t) + KE TOAN(theo s) + SWEEP.
#
# LABEL SHORT (path-thô tu cot san co ; tHit* la PHUT ; retEnd rong=gap -> bo):
#   drop = -maxAdv_H*100  (do SAU giam, DUONG — short LOI khi gia giam)
#   rise =  maxFav_H*100  (do TANG, BAT LOI cho short — cham dinh = hard-SL)
#   HIT_short_t = (drop >= t) & (nBars_H du)          <- target train classifier P(HIT_short_t), 1 clf / target.
#
# KE TOAN SL-CUNG short LET-RUN (moi (t, s)) — path-aware STOP, KHONG funding (funding OFF theo Uni chot):
#   let-dump-run: KHONG chot co dinh — ride toi horizon hoac stop (bo nhanh chot +t cu, cap winner sai thiet ke Uni).
#   t CHI con vai tro LABEL train classifier P(drop>=t) — KHONG con vai tro chot trong ke toan.
#   stopped = (rise >= s) & (tHitFav_H < tHitAdv_H)   (cham dinh +s TRUOC khi cham day -> stopped)
#     stopped              -> pnl = -s
#   else                   -> pnl = -retEnd_H*100     (ride het horizon: gia giam=retEnd<0=>+; gia tang=>-)
#   net = mean(pnl) - 0.2% (phi 2 chan). *** KHONG tru funding (OFF) ***
#
# SELECTION (chong DOI LENH vi ps short thap): DUNG CA HAI —
#   (a) threshold P* in {0.30..0.70}: chon row co p >= ps.
#   (b) rank topK/moc in {1,3,5,10}: moi moc ts chon top-K coin theo p (khong bao gio doi lenh).
#
# METRIC do moi (t, s, selection): net PnL | winrate(win_rate=%pnl>0, hit_rate=%drop>=t) | tpq(tan suat=trades/quy)
#   | AUC(theo target) | tach REGIME bull(oos_from<2025-01-01)/chop(>=). CHON theo net+winrate+tan suat (KHONG chi AUC).
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
HORIZON = os.environ.get("HORIZON", "24h")            # kernel nay = 24h (override qua env HORIZON)
TARGET_GRID = [int(x) for x in os.environ.get("TARGET_GRID", "3,6,9,15").split(",")]   # target chot loi short %
STOP_GRID = [int(x) for x in os.environ.get("STOP_GRID", "8,15,20,30").split(",")]     # hard-SL RONG sweep %
PSTAR_GRID = [round(0.30 + 0.05 * i, 2) for i in range(9)]   # 0.30..0.70 step .05 (ps short thap)
TOPK_GRID = [int(x) for x in os.environ.get("TOPK_GRID", "1,3,5,10").split(",")]       # top-K coin / moc ts
FEE_PCT = 0.2                                         # phi 2 chan 0.1%*2 (funding OFF)
MIN_TPQ = 2.0                                         # nguong tpq (median trades/quy) de diem vao dong RESULT
NEED_BARS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}    # nBars_H du (luoi 15m): H/15m
REGIME_CUT = pd.Timestamp("2025-01-01")              # BULL: oos_from < cut ; CHOP: >= cut
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("short-grid")


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
    """Merged features (ts, symId, 45 feat, symbol)."""
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)                                   # symId,symbol
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    del t, o
    log.info("Features ghep: %d rows | n_sym=%d", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def load_horizon_labels(horizon, need_bars):
    """Cot ke toan cho horizon H (KHONG phu thuoc target): ts,symbol,rise,dropp,tfav,tadv,retpct."""
    cf, ca = f"maxFav_{horizon}", f"maxAdv_{horizon}"
    tf, ta = f"tHitFav_{horizon}", f"tHitAdv_{horizon}"
    cr, cn = f"retEnd_{horizon}", f"nBars_{horizon}"
    df = pd.read_csv(LABEL_CSV, usecols=["tEpochMs", "symbol", cf, ca, tf, ta, cr, cn],
                     on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df[cn] >= need_bars) & df[cf].notna() & df[ca].notna() & df[cr].notna()].copy()
    rise = (df[cf].values * 100.0).astype(np.float32)          # do tang (bat loi short), duong
    dropp = (-df[ca].values * 100.0).astype(np.float32)        # do sau giam (loi short), duong
    tfav = df[tf].values.astype(np.float32)                    # phut toi dinh
    tadv = df[ta].values.astype(np.float32)                    # phut toi day
    retpct = (df[cr].values * 100.0).astype(np.float32)        # retEnd% (close-to-close)
    out = pd.DataFrame({"ts": df["ts"].values, "symbol": df["symbol"].values,
                        "rise": rise, "dropp": dropp, "tfav": tfav, "tadv": tadv, "retpct": retpct})
    log.info("Label %s: %d/%d rows | drop p50=%.2f p90=%.2f | rise p50=%.2f | base(drop>=t): %s",
             horizon, len(out), n0, float(np.percentile(dropp, 50)), float(np.percentile(dropp, 90)),
             float(np.percentile(rise, 50)),
             {t: round(float((dropp >= t).mean()), 4) for t in TARGET_GRID})
    return out


def build_folds():
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def pnl_short(dd, s, t):
    """Ke toan SL-cung short LET-RUN (path-aware), vector hoa, cho (stop s; t chi con la LABEL, KHONG dung de chot):
       let-dump-run: khong chot co dinh o +t — ride toi horizon hoac stop.
       stopped=(rise>=s)&(tfav<tadv) -> -s ; else -> -retpct (ride het horizon)."""
    rise = dd["rise"].values
    tfav = dd["tfav"].values
    tadv = dd["tadv"].values
    retpct = dd["retpct"].values
    stopped = (rise >= float(s)) & (tfav < tadv)
    pnl = np.where(stopped, -float(s), -retpct)
    return pnl.astype(np.float64)


def fit_predict(xgb, tr, te):
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit"])
    return clf.predict_proba(te[FEAT])[:, 1]


def _metrics(sel, pnl_col, hit_col):
    n = int(len(sel))
    if not n:
        return {"trades": 0, "net": None, "win_rate": None, "hit_rate": None}
    pnl = sel[pnl_col].values
    return {"trades": n,
            "net": round(float(pnl.mean()) - FEE_PCT, 4),
            "win_rate": round(float((pnl > 0).mean()), 4),
            "hit_rate": round(float(sel[hit_col].mean()), 4)}


def eval_fold(te, p, target, oos_from):
    """Per-fold cho MOT target: auc + per selection(P*/topK) per stop -> trades/net/win_rate/hit_rate."""
    from sklearn.metrics import roc_auc_score
    d = te.copy()
    d["p"] = np.asarray(p, dtype=float)
    d["hit"] = (d["dropp"].values >= float(target)).astype(np.int8)
    base = float(d["hit"].mean())
    try:
        auc = float(roc_auc_score(d["hit"].values, d["p"].values)) if d["hit"].nunique() > 1 else None
    except Exception:
        auc = None
    d["rankd"] = d.groupby("ts")["p"].rank(method="first", ascending=False)   # topK/moc
    r = {"oos_from": oos_from, "N": int(len(d)), "base_rate": round(base, 4),
         "AUC": round(auc, 4) if auc is not None else None, "sel": {}}
    # pre-tinh pnl theo tung stop (khong doi theo selection)
    pnl_by_s = {}
    for s in STOP_GRID:
        d[f"pnl_{s}"] = pnl_short(d, s, target)
        pnl_by_s[s] = f"pnl_{s}"
    def _run(mask, key):
        sub = d[mask]
        r["sel"][key] = {str(s): _metrics(sub, pnl_by_s[s], "hit") for s in STOP_GRID}
    for ps in PSTAR_GRID:
        _run(d["p"].values >= ps, f"p{ps:.2f}")
    for k in TOPK_GRID:
        _run(d["rankd"].values <= k, f"top{k}")
    return r


def _med(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.median(vals)), 4) if vals else None


def aggregate(per_fold):
    """Aggregate median qua fold + TACH REGIME. tpq = median trades/fold (1 fold=1 quy)."""
    bull = [f for f in per_fold if pd.Timestamp(f["oos_from"]) < REGIME_CUT]
    chop = [f for f in per_fold if pd.Timestamp(f["oos_from"]) >= REGIME_CUT]
    sel_keys = list(per_fold[0]["sel"].keys())
    agg = {"n_fold": len(per_fold), "n_bull": len(bull), "n_chop": len(chop),
           "auc_med": _med([f["AUC"] for f in per_fold]),
           "base_rate_med": _med([f["base_rate"] for f in per_fold]), "sel": {}}
    for sk in sel_keys:
        agg["sel"][sk] = {}
        for s in STOP_GRID:
            ss = str(s)
            def g(folds, field):
                return _med([f["sel"][sk][ss][field] for f in folds])
            agg["sel"][sk][ss] = {
                "tpq": g(per_fold, "trades"),
                "net": g(per_fold, "net"),
                "net_bull": g(bull, "net") if bull else None,
                "net_chop": g(chop, "net") if chop else None,
                "win_rate": g(per_fold, "win_rate"),
                "hit_rate": g(per_fold, "hit_rate")}
    return agg


def best_point(target, agg):
    """Diem tot nhat cua target theo NET (rang buoc tpq>=MIN_TPQ de tranh doi lenh degenerate)."""
    best = None
    for sk, byS in agg["sel"].items():
        for s, m in byS.items():
            if m["net"] is None or m["tpq"] is None or m["tpq"] < MIN_TPQ:
                continue
            if best is None or m["net"] > best["net"]:
                best = {"t": target, "sel": sk, "s": int(s), "net": m["net"], "tpq": m["tpq"],
                        "win": m["win_rate"], "hit": m["hit_rate"],
                        "nb": m["net_bull"], "nc": m["net_chop"], "auc": agg["auc_med"]}
    if best is None:      # noi long: bo rang buoc tpq neu grid qua thua lenh
        for sk, byS in agg["sel"].items():
            for s, m in byS.items():
                if m["net"] is None:
                    continue
                if best is None or m["net"] > best["net"]:
                    best = {"t": target, "sel": sk, "s": int(s), "net": m["net"], "tpq": m["tpq"],
                            "win": m["win_rate"], "hit": m["hit_rate"],
                            "nb": m["net_bull"], "nc": m["net_chop"], "auc": agg["auc_med"]}
    return best


def eval_target(xgb, ds, target, folds, need):
    d = ds.copy()
    d["hit"] = (d["dropp"].values >= float(target)).astype(np.int8)
    per_fold = []
    purge = need * GRID_MS
    for fi, (cut, oos_end) in enumerate(folds):
        tr = d[d.ts < cut - purge]
        te = d[(d.ts >= cut) & (d.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("[%s t%d] fold %d thieu data (tr=%d te=%d pos=%d) - bo", HORIZON, target, fi,
                        len(tr), len(te), int(tr["hit"].sum()))
            continue
        p = fit_predict(xgb, tr, te)
        oos_from = str(pd.to_datetime(cut, unit="ms").date())
        r = eval_fold(te, p, target, oos_from)
        r["fold"] = fi
        r["oos_to"] = str(pd.to_datetime(oos_end, unit="ms").date())
        per_fold.append(r)
        d15 = r["sel"].get("p0.60", {}).get("15")
        log.info("[%s t%d] fold %d [%s..%s] base=%.4f AUC=%s | p.60 s15: tpq=%s net=%s hit=%s",
                 HORIZON, target, fi, oos_from, r["oos_to"], r["base_rate"], r["AUC"],
                 d15 and d15["trades"], d15 and d15["net"], d15 and d15["hit_rate"])
    return per_fold


def print_table(target, agg):
    print(f"\n===== SHORT-GRID [{HORIZON}] t={target}% | folds={agg['n_fold']} "
          f"(bull={agg['n_bull']} chop={agg['n_chop']}) auc_med={agg['auc_med']} base={agg['base_rate_med']} =====")
    for sk in agg["sel"]:
        cells = []
        for s in STOP_GRID:
            m = agg["sel"][sk][str(s)]
            cells.append("s%d:net=%s win=%s hit=%s tpq=%s" % (s, m["net"], m["win_rate"], m["hit_rate"], m["tpq"]))
        print("  %-7s | %s" % (sk, "  ".join(cells)))


def run():
    cols = label_columns()
    need_cols = [f"{p}_{HORIZON}" for p in ["maxFav", "maxAdv", "tHitFav", "tHitAdv", "retEnd", "nBars"]]
    missing = [c for c in need_cols if c not in cols]
    if missing:
        print(f"NO_{HORIZON.upper()} — thieu cot: {missing}")
        log.error("NO_%s — thieu cot horizon: %s", HORIZON.upper(), missing)
        raise SystemExit(f"NO_{HORIZON.upper()}")
    need = NEED_BARS[HORIZON]

    feats = build_features()
    lb = load_horizon_labels(HORIZON, need)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("[%s] Dataset ghep: %d rows", HORIZON, len(ds))
    del feats

    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold")
    log.info("SHORT-GRID %s | %d fold OOS=%dm | TARGET=%s STOP=%s | P*=%s topK=%s | FUNDING=OFF",
             HORIZON, len(folds), OOS_MONTHS, TARGET_GRID, STOP_GRID, PSTAR_GRID, TOPK_GRID)

    full = {"label": "short-grid", "horizon": HORIZON, "target_grid": TARGET_GRID,
            "stop_grid": STOP_GRID, "pstar_grid": PSTAR_GRID, "topk_grid": TOPK_GRID,
            "fee_pct": FEE_PCT, "funding": "OFF", "acct": "let-run",
            "first_oos": FIRST_OOS, "last": LAST,
            "oos_months": OOS_MONTHS, "seed": SEED, "regime_cut": str(REGIME_CUT.date()),
            "metric_note": "chon theo NET PnL + winrate + tpq (KHONG chi AUC). "
                           "win_rate=%(pnl>0); hit_rate=%(drop>=t, t la LABEL train, KHONG dung de chot); "
                           "tpq=median trades/quy; net=mean(pnl)-0.2%% (funding OFF); "
                           "ke toan LET-RUN (let-dump-run, khong chot co dinh +t): "
                           "stopped(rise>=s & tfav<tadv)->-s, else->-retEnd*100 (ride het horizon).",
            "targets": {}}
    best_pts = []
    for t in TARGET_GRID:
        pf = eval_target(xgb, ds, t, folds, need)
        if not pf:
            log.warning("[%s t%d] khong fold hop le — bo target.", HORIZON, t)
            full["targets"][str(t)] = {"skipped": "no_valid_fold"}
            continue
        agg = aggregate(pf)
        print_table(t, agg)
        # per_fold gon (khong luu full grid moi fold — grid day du o aggregate)
        pf_slim = [{"fold": f["fold"], "oos_from": f["oos_from"], "oos_to": f["oos_to"],
                    "N": f["N"], "base_rate": f["base_rate"], "AUC": f["AUC"]} for f in pf]
        full["targets"][str(t)] = {"aggregate": agg, "per_fold": pf_slim}
        bp = best_point(t, agg)
        if bp:
            best_pts.append(bp)

    if not any("aggregate" in v for v in full["targets"].values()):
        raise SystemExit(f"[{HORIZON}] Khong target nao co fold hop le — kiem alignment ts/symbol.")

    out_path = os.path.join(OUT_DIR, f"short_grid_{HORIZON}_results.json")
    json.dump(full, open(out_path, "w"), indent=2)

    # Dong RESULT <2KB: diem tot nhat MOI target theo net (kem winrate/tpq/regime/auc).
    line = json.dumps({"h": HORIZON, "fee": FEE_PCT, "funding": "OFF", "acct": "let-run",
                       "sel_space": {"pstar": [PSTAR_GRID[0], PSTAR_GRID[-1]], "topk": TOPK_GRID},
                       "best_per_target": best_pts}, separators=(",", ":"))
    if len(line) > 2000:      # cat gon neu qua 2KB (giu net/win/tpq)
        slim = [{"t": b["t"], "sel": b["sel"], "s": b["s"], "net": b["net"], "win": b["win"],
                 "hit": b["hit"], "tpq": b["tpq"], "nb": b["nb"], "nc": b["nc"]} for b in best_pts]
        line = json.dumps({"h": HORIZON, "acct": "let-run", "best_per_target": slim}, separators=(",", ":"))
    print(f"SHORTGRID_{HORIZON.upper()}_RESULT " + line)
    log.info("XONG -> %s (RESULT line len=%d)", out_path, len(line))


if __name__ == "__main__":
    run()
