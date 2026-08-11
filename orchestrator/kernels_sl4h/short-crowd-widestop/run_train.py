#!/usr/bin/env python3
# SHORT-CROWD-WIDESTOP — test nghi van "stop 30% qua nho cho short crowding".
#   COPY 100% preamble/fold/classifier/label/accounting/gate tu
#   orchestrator/kernels_sl4h/short-crowding/run_train.py (GIU NGUYEN de so khop).
#
# NEN: short-crowding da tim duoc best_chop = t=9, horizon=24h, stop=30, crowding
#   q0.90 (ls_toptrader), base p>=0.60 -> net_chop = +3.47 (tpq>=30). Combo nay
#   CO DINH lam winner trong kernel nay (KHONG sweep lai t / quantile / base-selection).
#
# CAU HOI: stop 30% co qua nho khong? Coin bi crowding co the pump THEM (nhieu) truoc
#   khi bleed that su (short-crowding la cuoc CUOI theo dao chieu long-crowded — co the
#   mat thoi gian de "vo lo" long truoc khi dao chieu). Stop rong hon (40/50/60/70) co
#   giu duoc keo qua khoi bi cat som de bat duoc pha bleed dai han khong, hay chi la
#   om lo lon hon (vi "cham day het horizon" van co the -retEnd rat am)?
#
# GIOI HAN QUAN TRONG — chay 1x: short 1x, gia +100% (rise>=100) = LIQUIDATION thuc te
#   (mat toan bo margin, khong con gi de "ride het horizon"). Voi stop trong grid nay
#   (<=70%, deu <100%) thi VE NGUYEN TAC stop luon cat truoc muc chay N?U dieu kien
#   stop kich hoat dung luc. Nhung ke toan LET-RUN dung dieu kien path-aware
#   (rise>=s & tfav<tadv) — CO THE co keo KHONG bi flag "stopped" theo dieu kien nay ma
#   van co rise>100 sau do (vi thu tu tfav/tadv khac timing don gian "gia cham s truoc").
#   => nhung keo nay dang duoc ke toan bang -retEnd_H*100 (coi nhu "song" den het horizon)
#   trong khi thuc te 1x da CHAY giua duong -> DANH GIA THAP hon muc lo thuc te.
#   Kernel nay BAT BUOC in ra: %keo bi stopped vs let-run, va trong let-run bao nhieu %
#   co rise>100 (dang le da chay) de CANH BAO rieng, KHONG am tham bo qua.
#
# HORIZON sweep: 24h (winner cu) + 72h (hold dai hon — gan gia thuyet "bleed can thoi
#   gian" hon, van trong gioi han cot label co san toi 72h trong funding_label.csv).
#
# STOP sweep: {30,40,50,60,70} — 30 la baseline da biet (winner cu short-crowding),
#   sweep them 40-70 de xem net_chop tang/giam theo do rong stop, tim sweet spot (neu co).
#
# KHONG deploy, KHONG dung WFO Oracle — van la screen dieu kien tren proxy label
#   (funding_label.csv), giong het short-crowding.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
# Winner CO DINH tu short-crowding (t=9, p>=0.60, q0.90 ls_toptrader) — KHONG sweep lai
# trong kernel nay (chi sweep stop x horizon, xem duoi).
TARGET_T = int(os.environ.get("TARGET_T", "9"))
PSTAR = float(os.environ.get("PSTAR", "0.60"))
QCROWD = float(os.environ.get("QCROWD", "0.90"))
LS_FEAT = os.environ.get("LS_FEAT", "ls_toptrader")

# Sweep DUY NHAT trong kernel nay: stop x horizon.
STOP_GRID = [int(x) for x in os.environ.get("STOP_GRID", "30,40,50,60,70").split(",") if x]
HORIZONS = [h for h in os.environ.get("HORIZONS", "24h,72h").split(",") if h]

FEE_PCT = 0.2                                    # phi 2 chan 0.1%*2 (funding OFF) — giong short-crowding
CHOP_TPQ_MIN = 30.0                              # nguong tpq cho best_chop (giong short-crowding)
NEED_BARS = {"24h": 96, "72h": 288}
REGIME_CUT = pd.Timestamp("2025-01-01")          # BULL: oos_from<cut ; CHOP: >=cut
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("short-crowd-widestop")


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
    """Merged features (ts, symId, 45 feat, symbol) — dung CHUNG cho MOI horizon (khong doi theo H)."""
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)                                   # symId,symbol
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    del t, o
    missing_ls = [c for c in ("ls_toptrader", "ls_global") if c not in merged.columns]
    assert not missing_ls, f"THIEU cot crowding trong OI feature: {missing_ls}"
    log.info("Features ghep: %d rows | n_sym=%d | cot crowding OK: ls_toptrader,ls_global",
             len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def load_horizon_labels(horizon, need_bars):
    """Cot ke toan cho horizon H (khong phu thuoc target): ts,symbol,rise,dropp,tfav,tadv,retpct."""
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
    log.info("Label %s: %d/%d rows | drop p50=%.2f p90=%.2f | rise p50=%.2f p90=%.2f p99=%.2f | "
             "base(drop>=%d)=%.4f | %%rise>100(1x-chay)=%.4f", horizon, len(out), n0,
             float(np.percentile(dropp, 50)), float(np.percentile(dropp, 90)),
             float(np.percentile(rise, 50)), float(np.percentile(rise, 90)), float(np.percentile(rise, 99)),
             TARGET_T, float((dropp >= TARGET_T).mean()), float((rise > 100).mean()))
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


def pnl_stats(dd, s):
    """Ke toan SL-cung short LET-RUN (path-aware), GIU NGUYEN cong thuc short-crowding
       (t chi la LABEL, KHONG anh huong ke toan nay): stopped=(rise>=s)&(tfav<tadv) -> -s ;
       else -> -retpct (ride het horizon). Tra THEM stopped-mask + rise de tinh %stopped
       va %rise>100 trong let-run (canh bao chay 1x khi stop rong)."""
    rise = dd["rise"].values
    tfav = dd["tfav"].values
    tadv = dd["tadv"].values
    retpct = dd["retpct"].values
    stopped = (rise >= float(s)) & (tfav < tadv)
    pnl = np.where(stopped, -float(s), -retpct)
    return pnl.astype(np.float64), stopped, rise


def fit_predict(xgb, tr, te):
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit"])
    return clf.predict_proba(te[FEAT])[:, 1]


def _metrics_ext(sel, s):
    """net/win_rate GIONG short-crowding (_metrics) + BO SUNG pct_stopped va
       pct_rise_gt100_letrun (canh bao chay 1x khi stop rong)."""
    n = int(len(sel))
    if not n:
        return {"trades": 0, "net": None, "win_rate": None, "pct_stopped": None,
                "pct_rise_gt100_letrun": None}
    pnl, stopped, rise = pnl_stats(sel, s)
    letrun = ~stopped
    n_letrun = int(letrun.sum())
    pct_rise_gt100 = float((rise[letrun] > 100.0).mean()) if n_letrun > 0 else None
    return {"trades": n,
            "net": round(float(pnl.mean()) - FEE_PCT, 4),
            "win_rate": round(float((pnl > 0).mean()), 4),
            "pct_stopped": round(float(stopped.mean()), 4),
            "pct_rise_gt100_letrun": round(pct_rise_gt100, 4) if pct_rise_gt100 is not None else None}


def eval_fold(te, p, oos_from):
    """Per-fold cho winner CO DINH (t=9, p>=0.60, q0.90 ls_toptrader) — CHI sweep stop.
       CROWDING GATE GIONG HET short-crowding: entry = (ps>=PSTAR) AND (ls_feat>=quantile
       QCROWD, quantile tinh CROSS-SECTIONAL cung ts qua d.groupby('ts')[lf].rank(pct=True)
       — giong het co che rank topK/quantile da co trong short-crowding, KHONG look-ahead
       theo thoi gian)."""
    d = te.copy()
    d["p"] = np.asarray(p, dtype=float)
    d["hit"] = (d["dropp"].values >= float(TARGET_T)).astype(np.int8)
    base = float(d["hit"].mean())
    d["pct_ls"] = d.groupby("ts")[LS_FEAT].rank(pct=True)
    sel_mask = (d["p"].values >= PSTAR) & (d["pct_ls"].values >= QCROWD)
    sub = d[sel_mask]
    r = {"oos_from": oos_from, "N": int(len(d)), "N_sel": int(len(sub)), "base_rate": round(base, 4),
         "by_s": {}}
    for s in STOP_GRID:
        r["by_s"][str(s)] = _metrics_ext(sub, s)
    return r


def eval_target(xgb, ds, folds, need):
    d = ds.copy()
    d["hit"] = (d["dropp"].values >= float(TARGET_T)).astype(np.int8)
    per_fold = []
    purge = need * GRID_MS
    for fi, (cut, oos_end) in enumerate(folds):
        tr = d[d.ts < cut - purge]
        te = d[(d.ts >= cut) & (d.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("[t%d] fold %d thieu data (tr=%d te=%d pos=%d) - bo", TARGET_T, fi,
                        len(tr), len(te), int(tr["hit"].sum()))
            continue
        p = fit_predict(xgb, tr, te)
        oos_from = str(pd.to_datetime(cut, unit="ms").date())
        r = eval_fold(te, p, oos_from)
        r["fold"] = fi
        r["oos_to"] = str(pd.to_datetime(oos_end, unit="ms").date())
        per_fold.append(r)
        d0 = r["by_s"].get(str(STOP_GRID[0]))
        log.info("[t%d] fold %d [%s..%s] base=%.4f N_sel=%d | s%d: tpq=%s net=%s stopped=%s rise100(letrun)=%s",
                 TARGET_T, fi, oos_from, r["oos_to"], r["base_rate"], r["N_sel"], STOP_GRID[0],
                 d0 and d0["trades"], d0 and d0["net"], d0 and d0["pct_stopped"],
                 d0 and d0["pct_rise_gt100_letrun"])
    return per_fold


def aggregate(per_fold):
    """Aggregate median qua fold + TACH REGIME cho net (giong short-crowding).
       pct_stopped/pct_rise_gt100 aggregate median qua TAT CA fold (khong tach regime —
       day la thong ke ve du lieu/path, khong phai hieu suat theo regime)."""
    bull = [f for f in per_fold if pd.Timestamp(f["oos_from"]) < REGIME_CUT]
    chop = [f for f in per_fold if pd.Timestamp(f["oos_from"]) >= REGIME_CUT]
    agg = {"n_fold": len(per_fold), "n_bull": len(bull), "n_chop": len(chop), "by_s": {}}
    for s in STOP_GRID:
        ss = str(s)

        def g(folds, field):
            vals = [f["by_s"][ss][field] for f in folds if f["by_s"][ss][field] is not None]
            return round(float(np.median(vals)), 4) if vals else None

        agg["by_s"][ss] = {
            "tpq": g(per_fold, "trades"),
            "net": g(per_fold, "net"),
            "net_bull": g(bull, "net") if bull else None,
            "net_chop": g(chop, "net") if chop else None,
            "win": g(per_fold, "win_rate"),
            "pct_stopped": g(per_fold, "pct_stopped"),
            "pct_rise_gt100": g(per_fold, "pct_rise_gt100_letrun"),
        }
    return agg


def print_table(horizon, agg):
    print(f"\n===== SHORT-CROWD-WIDESTOP [{horizon}] t={TARGET_T}% p*>={PSTAR} q>={QCROWD} "
          f"({LS_FEAT}) | folds={agg['n_fold']} (bull={agg['n_bull']} chop={agg['n_chop']}) =====")
    for s in STOP_GRID:
        m = agg["by_s"][str(s)]
        pct_letrun = round(1.0 - m["pct_stopped"], 4) if m.get("pct_stopped") is not None else None
        print("  stop=%3d%% | tpq=%-6s net=%-8s net_bull=%-8s net_chop=%-8s win=%-7s "
              "pct_stopped=%-7s pct_letrun=%-7s pct_rise_gt100(let-run)=%-7s" %
              (s, m.get("tpq"), m.get("net"), m.get("net_bull"), m.get("net_chop"),
               m.get("win"), m.get("pct_stopped"), pct_letrun, m.get("pct_rise_gt100")))


def run_horizon(xgb, feats, horizon):
    need = NEED_BARS[horizon]
    lb = load_horizon_labels(horizon, need)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("[%s] Dataset ghep: %d rows", horizon, len(ds))

    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold")
    log.info("SHORT-CROWD-WIDESTOP %s | %d fold OOS=%dm | winner CO DINH t=%d p*=%.2f q=%.2f ls=%s | "
             "STOP sweep=%s | FUNDING=OFF", horizon, len(folds), OOS_MONTHS, TARGET_T, PSTAR, QCROWD,
             LS_FEAT, STOP_GRID)

    pf = eval_target(xgb, ds, folds, need)
    if not pf:
        log.warning("[%s] khong fold hop le — bo horizon.", horizon)
        return None
    agg = aggregate(pf)
    print_table(horizon, agg)
    return agg


def run():
    cols = label_columns()
    valid_horizons = []
    for h in HORIZONS:
        need_cols = [f"{p}_{h}" for p in ["maxFav", "maxAdv", "tHitFav", "tHitAdv", "retEnd", "nBars"]]
        missing = [c for c in need_cols if c not in cols]
        if missing:
            log.error("NO_%s — thieu cot horizon: %s (bo horizon nay)", h.upper(), missing)
        else:
            valid_horizons.append(h)
    assert valid_horizons, f"KHONG horizon nao hop le trong {HORIZONS} — kiem funding_label.csv."

    feats = build_features()
    import xgboost as xgb

    grid = []
    agg_by_h = {}
    for h in valid_horizons:
        agg = run_horizon(xgb, feats, h)
        if agg is None:
            continue
        agg_by_h[h] = agg
        for s in STOP_GRID:
            m = agg["by_s"][str(s)]
            grid.append({"s": s, "h": h, "net": m.get("net"), "net_bull": m.get("net_bull"),
                         "net_chop": m.get("net_chop"), "tpq": m.get("tpq"), "win": m.get("win"),
                         "pct_stopped": m.get("pct_stopped"), "pct_rise_gt100": m.get("pct_rise_gt100")})

    if not grid:
        raise SystemExit("Khong combo nao hop le — kiem du lieu horizon/fold.")

    # ----- CANH BAO CHAY 1x: bat ky combo nao co pct_rise_gt100 (trong let-run) > 0 -----
    burn_warn = [g for g in grid if g.get("pct_rise_gt100") is not None and g["pct_rise_gt100"] > 0]
    if burn_warn:
        for g in sorted(burn_warn, key=lambda x: -x["pct_rise_gt100"]):
            log.warning("[CHAY-1x WARNING] h=%s stop=%d%%: %.2f%% keo LET-RUN co rise>100%% "
                        "(dang le da CHAY neu that su dung don bay 1x — ke toan hien tai (-retEnd) "
                        "dang DANH GIA THAP hon muc lo thuc te cho cac keo nay).",
                        g["h"], g["s"], g["pct_rise_gt100"] * 100.0)
    else:
        log.info("Khong combo nao co keo let-run voi rise>100%% trong pham vi da test — "
                 "an toan voi ke toan hien tai (trong pham vi stop/horizon da sweep).")

    # ----- KET LUAN: net_chop tang/giam theo do rong stop, sweet spot moi horizon -----
    for h in valid_horizons:
        row = sorted([g for g in grid if g["h"] == h], key=lambda g: g["s"])
        log.info("[KET LUAN %s] stop=%s -> net_chop=%s", h, [g["s"] for g in row],
                 [g["net_chop"] for g in row])
        valid_nc = [(g["s"], g["net_chop"]) for g in row if g["net_chop"] is not None]
        if valid_nc:
            best_s, best_nc = max(valid_nc, key=lambda x: x[1])
            worst_s, worst_nc = min(valid_nc, key=lambda x: x[1])
            trend = "TANG" if valid_nc[-1][1] > valid_nc[0][1] else ("GIAM" if valid_nc[-1][1] < valid_nc[0][1] else "PHANG")
            log.info("[KET LUAN %s] stop %d%%->%d%%: net_chop %s (%.4f -> %.4f) | sweet spot (max) = "
                     "stop %d%% (net_chop=%.4f) | worst = stop %d%% (net_chop=%.4f)",
                     h, valid_nc[0][0], valid_nc[-1][0], trend, valid_nc[0][1], valid_nc[-1][1],
                     best_s, best_nc, worst_s, worst_nc)

    # ----- best_chop toan cuc (rang buoc tpq>=CHOP_TPQ_MIN, giong short-crowding) -----
    eligible = [g for g in grid if g.get("net_chop") is not None and g.get("tpq") is not None
                and g["tpq"] >= CHOP_TPQ_MIN]
    best_chop = max(eligible, key=lambda g: g["net_chop"]) if eligible else None
    if best_chop:
        log.info("BEST-CHOP (tpq>=%.0f) -> %s", CHOP_TPQ_MIN, best_chop)
    else:
        log.warning("KHONG combo nao dat tpq>=%.0f voi net_chop hop le.", CHOP_TPQ_MIN)

    out_path = os.path.join(OUT_DIR, "short_crowd_widestop_results.json")
    json.dump({"label": "short-crowd-widestop",
               "winner_fixed": {"t": TARGET_T, "pstar": PSTAR, "qcrowd": QCROWD, "ls_feat": LS_FEAT},
               "stop_grid": STOP_GRID, "horizons": valid_horizons, "chop_tpq_min": CHOP_TPQ_MIN,
               "grid": grid, "best_chop": best_chop, "by_horizon_aggregate": agg_by_h},
              open(out_path, "w"), indent=2, default=str)

    line = json.dumps({"grid": grid, "best_chop": best_chop}, separators=(",", ":"))
    if len(line) > 4000:
        line = json.dumps({"best_chop": best_chop, "grid_n": len(grid)}, separators=(",", ":"))
    print("SHORT_CROWD_WIDESTOP_RESULT " + line)
    log.info("XONG -> %s (RESULT line len=%d)", out_path, len(line))


if __name__ == "__main__":
    run()
