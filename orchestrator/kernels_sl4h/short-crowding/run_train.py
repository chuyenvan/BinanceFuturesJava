#!/usr/bin/env python3
# SHORT-CROWDING — test "cua cuoi" cua short: short CO DIEU KIEN crowding (khong short naive).
#   TAI DUNG 100% preamble/fold/classifier cua orchestrator/kernels_sl4h/short-grid-12h/run_train.py
#   (v2 let-run: HIT_short=drop>=t label train clfP; ke toan stopped(rise>=s & tfav<tadv)->-s
#   else->-retEnd_H*100; sweep; regime split bull(oos_from<2025-01-01)/chop(>=2025-01-01)).
#
# GIA THUYET (tu short-featscreen): short naive thua CHOP (da do o short-grid-12h/24h — net_chop
#   am o hau het combo). featscreen cho thay ls_toptrader (ty le long/short cua top-trader tren
#   OI) condition short-edge MANH: ls cao = long dong (crowded) => khi dao chieu, thanh ly long
#   nhoi nhau => dump manh hon. => short CHI khi crowding cao (ls_toptrader/ls_global >= quantile
#   Q_crowd) moi co the DUONG CA CHOP (edge uncorrelated voi bias-long thuong truc cua thi truong,
#   khac voi short naive an theo momentum/dao chieu chung).
#
# CROWDING GATE (diem MOI so voi short-grid) — entry = base-selection (topK/threshold theo ps
#   classifier) AND (ls_feat >= quantile Q_crowd). Quantile Q_crowd tinh CROSS-SECTIONAL tai
#   CUNG mot ts (rank giua cac coin dang song o CUNG moc thoi gian) — giong het co che rank topK
#   da co san trong short-grid (d.groupby("ts")[...].rank(...)), KHONG dung phan phoi tuong lai
#   => KHONG look-ahead theo thoi gian. Sweep Q_crowd in {0.5,0.7,0.8,0.9} (giu 50/30/20/10%
#   crowded nhat). Thu CA ls_toptrader VA ls_global (2/5 OI feature co san trong preamble, ten
#   cot XAC NHAN khop OI_NAMES cua short-grid-12h/short-featscreen).
#
# LABEL: HIT_short_t = (drop>=t), t in {6 (chinh), 9}. drop=-maxAdv_H*100 (do sau giam, duong).
# KE TOAN let-run (path-aware, KHONG chot co dinh o +t):
#   stopped = (rise>=s) & (tHitFav_H < tHitAdv_H) -> pnl=-s
#   else                                           -> pnl=-retEnd_H*100 (ride het horizon)
#   net = mean(pnl) - 0.2% (fee 2 chan 0.1%*2). Funding OFF (giong short-grid).
# Stop s in {20, 30}. Horizon chinh = 12h (env HORIZON), in them 24h (re du: cung feats, chi
#   doi label/merge — khong train lai tren tool1/OI).
#
# CAU HOI CHINH: co combo (horizon, t, s, Q_crowd, ls_feat, selection) nao net_chop DUONG voi
#   tpq>=30 khong? Neu CO => short-hedge THAT (duong CA khi thi truong di ngang/chop, khong chi
#   an theo xu huong bull). Neu KHONG => crowding-gate KHONG du de bien short thanh hedge o CHOP.
#
# KHONG deploy, KHONG dung WFO Oracle, chi la screen dieu kien tren proxy label (funding_label.csv).
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
HORIZON = os.environ.get("HORIZON", "12h")                      # horizon CHINH
EXTRA_HORIZONS = [h for h in os.environ.get("EXTRA_HORIZONS", "24h").split(",") if h and h != HORIZON]
HORIZONS = [HORIZON] + EXTRA_HORIZONS                            # 12h chinh + 24h (in them, re du dung feats)
TARGET_GRID = [int(x) for x in os.environ.get("TARGET_GRID", "6,9").split(",")]     # t=6 chinh, thu them t=9
STOP_GRID = [int(x) for x in os.environ.get("STOP_GRID", "20,30").split(",")]       # hard-SL let-run
PSTAR_GRID = [float(x) for x in os.environ.get("PSTAR_GRID", "0.50,0.60").split(",")]  # ps threshold (bo sung topK)
TOPK_GRID = [int(x) for x in os.environ.get("TOPK_GRID", "3,5,10").split(",")]      # ps top theo rank / moc ts
QCROWD_GRID = [float(x) for x in os.environ.get("QCROWD_GRID", "0.5,0.7,0.8,0.9").split(",")]  # crowding gate
LS_FEATS = [x for x in os.environ.get("LS_FEATS", "ls_toptrader,ls_global").split(",") if x]
FEE_PCT = 0.2                                                    # phi 2 chan 0.1%*2 (funding OFF)
MIN_TPQ = 2.0                                                    # nguong tpq cho "best theo net tong"
CHOP_TPQ_MIN = 30.0                                              # nguong tpq RIENG cho cau hoi chinh (best-chop)
NEED_BARS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}
REGIME_CUT = pd.Timestamp("2025-01-01")                          # BULL: oos_from<cut ; CHOP: >=cut
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("short-crowding")


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
    """Ke toan SL-cung short LET-RUN (path-aware), giong het short-grid-12h (t chi la LABEL):
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
    """Per-fold cho MOT target: auc + per (base-selection x ls_feat x Q_crowd) per stop.
       CROWDING GATE: entry = base_mask (ps>=P* HOAC top-K theo rank) AND (ls_feat >= quantile
       Q_crowd, quantile tinh CROSS-SECTIONAL cung ts qua d.groupby('ts')[lf].rank(pct=True) —
       giong het co che rank topK da co, KHONG look-ahead theo thoi gian)."""
    from sklearn.metrics import roc_auc_score
    d = te.copy()
    d["p"] = np.asarray(p, dtype=float)
    d["hit"] = (d["dropp"].values >= float(target)).astype(np.int8)
    base = float(d["hit"].mean())
    try:
        auc = float(roc_auc_score(d["hit"].values, d["p"].values)) if d["hit"].nunique() > 1 else None
    except Exception:
        auc = None
    d["rankp"] = d.groupby("ts")["p"].rank(method="first", ascending=False)     # topK theo p (rank)
    for lf in LS_FEATS:
        d[f"pct_{lf}"] = d.groupby("ts")[lf].rank(pct=True)                     # quantile cross-sectional cung ts

    r = {"oos_from": oos_from, "N": int(len(d)), "base_rate": round(base, 4),
         "AUC": round(auc, 4) if auc is not None else None, "sel": {}}

    pnl_by_s = {}
    for s in STOP_GRID:
        d[f"pnl_{s}"] = pnl_short(d, s, target)
        pnl_by_s[s] = f"pnl_{s}"

    def _run(mask, key):
        sub = d[mask]
        r["sel"][key] = {str(s): _metrics(sub, pnl_by_s[s], "hit") for s in STOP_GRID}

    base_masks = {}
    for ps in PSTAR_GRID:
        base_masks[f"p{ps:.2f}"] = d["p"].values >= ps
    for k in TOPK_GRID:
        base_masks[f"top{k}"] = d["rankp"].values <= k

    for bname, bmask in base_masks.items():
        for lf in LS_FEATS:
            for q in QCROWD_GRID:
                crowd_mask = d[f"pct_{lf}"].values >= q
                key = f"{bname}_q{q:.2f}_{lf}"
                _run(bmask & crowd_mask, key)
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


def _pack(target, sk, s, m, agg):
    return {"t": target, "sel": sk, "s": int(s), "net": m.get("net"), "tpq": m.get("tpq"),
            "win": m.get("win_rate"), "hit": m.get("hit_rate"), "nb": m.get("net_bull"),
            "nc": m.get("net_chop"), "auc": agg["auc_med"]}


def _valid_num(x):
    """True neu x la so thuc hop le (khong None, khong NaN) — dung de guard truoc khi so sanh."""
    if x is None:
        return False
    try:
        return not np.isnan(x)
    except TypeError:
        return True  # so nguyen/khac khong ap dung isnan van coi la hop le


def best_overall(target, agg):
    """Diem tot nhat theo NET TONG (rang buoc tpq>=MIN_TPQ de tranh doi lenh degenerate).
       Guard: bo qua combo co net None/NaN (vd regime/fold rong khong sinh du lieu)."""
    best, best_val = None, None
    for sk, byS in agg["sel"].items():
        for s, m in byS.items():
            net = m.get("net")
            tpq = m.get("tpq")
            if not _valid_num(net) or not _valid_num(tpq) or tpq < MIN_TPQ:
                continue
            if best is None or net > best_val:
                best = _pack(target, sk, s, m, agg)
                best_val = net
    return best


def best_chop(target, agg):
    """CAU HOI CHINH: diem tot nhat theo NET_CHOP (rang buoc tpq>=CHOP_TPQ_MIN=30 — du thanh khoan
       de goi la short-hedge THAT, khong phai vai trade may man).
       Guard: bo qua combo co net_chop None/NaN (combo khong co chop-trade / regime chop rong).
       LUU Y: so sanh dung best_val rieng (KHONG doc best["net_chop"]) vi _pack() luu gia tri nay
       duoi ten "nc" — day chinh la nguyen nhan KeyError cu (best["net_chop"] khong ton tai sau
       khi best da duoc _pack())."""
    best, best_val = None, None
    for sk, byS in agg["sel"].items():
        for s, m in byS.items():
            nc = m.get("net_chop")
            tpq = m.get("tpq")
            if not _valid_num(nc) or not _valid_num(tpq) or tpq < CHOP_TPQ_MIN:
                continue
            if best is None or nc > best_val:
                best = _pack(target, sk, s, m, agg)
                best_val = nc
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
        d15 = r["sel"].get("top5_q0.80_ls_toptrader", {}).get(str(STOP_GRID[0]))
        log.info("[%s t%d] fold %d [%s..%s] base=%.4f AUC=%s | top5_q0.80_ls_toptrader s%d: tpq=%s net=%s hit=%s",
                 HORIZON, target, fi, oos_from, r["oos_to"], r["base_rate"], r["AUC"], STOP_GRID[0],
                 d15 and d15["trades"], d15 and d15["net"], d15 and d15["hit_rate"])
    return per_fold


def print_table(horizon, target, agg):
    print(f"\n===== SHORT-CROWDING [{horizon}] t={target}% | folds={agg['n_fold']} "
          f"(bull={agg['n_bull']} chop={agg['n_chop']}) auc_med={agg['auc_med']} base={agg['base_rate_med']} =====")
    for sk in agg["sel"]:
        cells = []
        for s in STOP_GRID:
            m = agg["sel"][sk][str(s)]
            cells.append("s%d:net=%s nc=%s win=%s hit=%s tpq=%s" %
                         (s, m.get("net"), m.get("net_chop"), m.get("win_rate"), m.get("hit_rate"),
                          m.get("tpq")))
        print("  %-32s | %s" % (sk, "  ".join(cells)))


def run_horizon(xgb, feats, horizon):
    need = NEED_BARS[horizon]
    lb = load_horizon_labels(horizon, need)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("[%s] Dataset ghep: %d rows", horizon, len(ds))

    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold")
    log.info("SHORT-CROWDING %s | %d fold OOS=%dm | TARGET=%s STOP=%s | P*=%s topK=%s | "
             "Q_crowd=%s ls_feats=%s | FUNDING=OFF", horizon, len(folds), OOS_MONTHS, TARGET_GRID,
             STOP_GRID, PSTAR_GRID, TOPK_GRID, QCROWD_GRID, LS_FEATS)

    full = {"label": "short-crowding", "horizon": horizon, "target_grid": TARGET_GRID,
            "stop_grid": STOP_GRID, "pstar_grid": PSTAR_GRID, "topk_grid": TOPK_GRID,
            "qcrowd_grid": QCROWD_GRID, "ls_feats": LS_FEATS,
            "fee_pct": FEE_PCT, "funding": "OFF", "acct": "let-run",
            "first_oos": FIRST_OOS, "last": LAST, "oos_months": OOS_MONTHS, "seed": SEED,
            "regime_cut": str(REGIME_CUT.date()), "chop_tpq_min": CHOP_TPQ_MIN,
            "metric_note": "crowding gate: entry=(ps>=P* HOAC top-K theo rank) AND (ls_feat>=quantile "
                           "Q_crowd, cross-sectional cung ts). ke toan LET-RUN giong short-grid: "
                           "stopped(rise>=s & tfav<tadv)->-s, else->-retEnd*100; net=mean(pnl)-0.2%% "
                           "(funding OFF). best_overall = tpq>=2 (net max); best_chop = tpq>=30 (net_chop max) "
                           "— cau hoi chinh: co combo nao net_chop DUONG voi tpq>=30 (short-hedge that).",
            "targets": {}}
    best_overall_pts, best_chop_pts = [], []
    for t in TARGET_GRID:
        pf = eval_target(xgb, ds, t, folds, need)
        if not pf:
            log.warning("[%s t%d] khong fold hop le — bo target.", horizon, t)
            full["targets"][str(t)] = {"skipped": "no_valid_fold"}
            continue
        agg = aggregate(pf)
        print_table(horizon, t, agg)
        pf_slim = [{"fold": f["fold"], "oos_from": f["oos_from"], "oos_to": f["oos_to"],
                    "N": f["N"], "base_rate": f["base_rate"], "AUC": f["AUC"]} for f in pf]
        full["targets"][str(t)] = {"aggregate": agg, "per_fold": pf_slim}
        bo = best_overall(t, agg)
        bc = best_chop(t, agg)
        if bo:
            best_overall_pts.append(bo)
        if bc:
            best_chop_pts.append(bc)
    return full, best_overall_pts, best_chop_pts


def run():
    cols = label_columns()
    for h in HORIZONS:
        need_cols = [f"{p}_{h}" for p in ["maxFav", "maxAdv", "tHitFav", "tHitAdv", "retEnd", "nBars"]]
        missing = [c for c in need_cols if c not in cols]
        if missing:
            log.error("NO_%s — thieu cot horizon: %s (bo horizon nay)", h.upper(), missing)
            if h == HORIZON:
                raise SystemExit(f"NO_{HORIZON}")

    feats = build_features()
    import xgboost as xgb

    results = {}
    global_overall, global_chop = [], []
    for h in HORIZONS:
        need_cols = [f"{p}_{h}" for p in ["maxFav", "maxAdv", "tHitFav", "tHitAdv", "retEnd", "nBars"]]
        if any(c not in cols for c in need_cols):
            continue
        full, bo_pts, bc_pts = run_horizon(xgb, feats, h)
        results[h] = full
        for pt in bo_pts:
            pt["h"] = h
        for pt in bc_pts:
            pt["h"] = h
        global_overall += bo_pts
        global_chop += bc_pts

    if not results:
        raise SystemExit("Khong horizon nao hop le — kiem cot funding_label.csv.")

    out_path = os.path.join(OUT_DIR, "short_crowding_results.json")
    json.dump({"label": "short-crowding", "horizons": list(results.keys()),
               "qcrowd_grid": QCROWD_GRID, "ls_feats": LS_FEATS, "chop_tpq_min": CHOP_TPQ_MIN,
               "results": results}, open(out_path, "w"), indent=2)

    top_overall = max(global_overall, key=lambda b: b["net"]) if global_overall else None
    top_chop = max(global_chop, key=lambda b: b["nc"]) if global_chop else None

    if top_chop and top_chop.get("nc") is not None and top_chop["nc"] > 0:
        log.info("BEST-CHOP COMBO (net_chop DUONG, tpq>=%.0f) -> %s", CHOP_TPQ_MIN, top_chop)
    elif top_chop:
        log.warning("Co combo tpq>=%.0f nhung KHONG combo nao net_chop DUONG (best nc=%s) -> "
                    "no positive-chop combo -> cau hoi chinh: KHONG tim thay short-hedge that o CHOP.",
                    CHOP_TPQ_MIN, top_chop.get("nc"))
    else:
        log.warning("KHONG combo nao dat tpq>=%.0f voi net_chop hop le (None/NaN het) -> "
                    "no positive-chop combo -> cau hoi chinh: KHONG tim thay short-hedge that o CHOP "
                    "voi crowding-gate nay.", CHOP_TPQ_MIN)

    line = json.dumps({"qcrowd_grid": QCROWD_GRID, "ls_feats": LS_FEATS, "stop_grid": STOP_GRID,
                       "target_grid": TARGET_GRID, "chop_tpq_min": CHOP_TPQ_MIN,
                       "best_net": top_overall, "best_chop": top_chop}, separators=(",", ":"))
    if len(line) > 2000:
        line = json.dumps({"best_net": top_overall, "best_chop": top_chop}, separators=(",", ":"))
    print("SHORT_CROWDING_RESULT " + line)
    log.info("XONG -> %s (RESULT line len=%d)", out_path, len(line))


if __name__ == "__main__":
    run()
