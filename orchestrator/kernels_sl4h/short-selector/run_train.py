#!/usr/bin/env python3
# SHORT-SELECTOR — kiem tra EDGE cua selector BAN KHONG (short) tren regime chop/bear.
# Gia thuyet: chien luoc hien LONG-ONLY, edge regime-gated (BULL duong, CHOP breakeven).
#   Them SHORT de lap regime CHOP/BEAR + tang tan suat. SHORT KHONG doi xung long:
#   lo VO HAN khi gia tang -> BAT BUOC hard-SL cung X%, CAM martingale/DCA, va FUNDING
#   (short TRA funding khi funding duong = da so bull) la chi phi THAT phai tru.
#
# TAI DUNG 100% pipeline load cua sl4h-ev2-n6 (ff_*.bin 40 feat + OI 5 feat + funding_label.csv),
#   walk-forward EXPANDING fold, purge, leak-free. Chi thay phan LABEL + KE TOAN + EVAL cho short.
#
# LABEL SHORT (tu cot SAN CO trong funding_label.csv: maxFav_H, maxAdv_H, tHitFav_H, tHitAdv_H,
#             retEnd_H, nBars_H ; luu y tHit* la PHUT, retEnd co the rong=gap):
#   drop = -maxAdv_H*100  (do SAU giam, DUONG — short LOI khi gia giam)
#   rise =  maxFav_H*100  (do TANG, BAT LOI cho short — cham day la hard-SL)
#   N_PCT=6 CHI con dung lam NGUONG LABEL train classifier HIT_short (xem duoi) — KHONG con la
#     target chot loi trong ke toan (da bo, xem ly do duoi).
#   HIT_short (path-aware, GIU NGUYEN — target train classifier, KHONG doi):
#       (maxAdv_H <= -N/100) AND (tHitAdv_H < tHitFav_H OR tHitFav_H <= 0)   [nBars du]
#     -> KHONG phu thuoc SL => classifier target HIT_short train MOT LAN, ke toan quet SL sau.
#   *** KE TOAN SHORT MOI (2026-07-18) — SUA vi ke toan cu SL CHAT {5,8,10} + chot co dinh +6%
#       la risk-reward NGUOC (SL 30 ma chot 6 thi can win-rate 83% moi hoa von). Thay bang
#       hard-SL RONG + LET-RUN toi het horizon (KHONG target co dinh): ***
#     Voi moi horizon H va moi muc hard-SL S (sweep X_SL_GRID = {8,15,20,30}):
#     * neu rise_H (=maxFav_H*100) >= S  -> stopped: pnl = -S   (check TRUOC TIEN, hard-SL cung
#                                             chan squeeze; khong con phu thuoc thu tu tHitFav/tHitAdv
#                                             vi KHONG con nhanh chot-loi-som canh tranh voi SL)
#     * else                            -> pnl = -retEnd_H*100 (let-dump-run: gia giam toi het
#                                             cua so H -> duong cho short; KHONG chot loi som)
#     * net = pnl - 0.2% (phi) - FUNDING_BPS
#   ⚠️ FUNDING la XAP XI: funding_rate KHONG co trong label -> dung env FUNDING_BPS_PER_TRADE
#      (default 0.3 = 0.3%/keo, xap xi short TRA funding qua vai ky 8h). Funding THAT do o Java WFO
#      sau (APPLY_FUNDING_FEE=true — BAT BUOC cho short).
#
# Gia thuyet can kiem: short net_CHOP > net_BULL (NGUOC long) — dung => short lap dung regime long chet.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = int(os.environ.get("N_PCT", "6"))          # nguong label HIT_short (train classifier), KHONG con la target chot loi
X_SL_GRID = [int(x) for x in os.environ.get("X_SL_GRID", "8,15,20,30").split(",")]  # hard-SL RONG sweep (let-run, khong target co dinh)
X_SL_DEFAULT = int(os.environ.get("X_SL", "15"))   # SL dai dien cho log per-fold (khong dung cho dong RESULT — dong RESULT quet het grid)
P_REPR = [0.5, 0.6, 0.7]                            # P* dai dien cho dong SHORT_SELECTOR_RESULT compact
FUNDING_BPS = float(os.environ.get("FUNDING_BPS_PER_TRADE", "0.3"))  # xap xi short tra funding
FEE_PCT = 0.2                                       # phi 2 chan 0.1%*2
NEED_BARS = {"4h": 16, "12h": 48, "24h": 96}        # nBars_H du (luoi 15m)
PSTAR_GRID = [round(0.30 + 0.05 * i, 2) for i in range(13)]  # 0.30..0.90 step .05
REGIME_CUT = pd.Timestamp("2025-01-01")             # BULL: oos_from < cut ; CHOP: >= cut
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("short-selector")


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
    """Merged features (ts, symId, 45 feat, symbol). Dung lai cho moi horizon."""
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)                                   # symId,symbol
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    del t, o
    log.info("Features ghep: %d rows | n_sym=%d", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def load_short_labels(horizon, need_bars):
    """Label SHORT tu cot san co. Tra ve ts,symbol,hit_short + cot ke toan (rise,retpct,thit*)."""
    cf, ca = f"maxFav_{horizon}", f"maxAdv_{horizon}"
    tf, ta = f"tHitFav_{horizon}", f"tHitAdv_{horizon}"
    cr, cn = f"retEnd_{horizon}", f"nBars_{horizon}"
    df = pd.read_csv(LABEL_CSV, usecols=["tEpochMs", "symbol", cf, ca, tf, ta, cr, cn],
                     on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    # nBars du + maxFav/maxAdv/retEnd co mat (retEnd rong = gap -> bo, GIONG base kernel loc cr notna)
    df = df[(df[cn] >= need_bars) & df[cf].notna() & df[ca].notna() & df[cr].notna()].copy()
    rise = (df[cf].values * 100.0).astype(np.float32)           # do tang (bat loi short), duong
    drop = (-df[ca].values * 100.0).astype(np.float32)          # do sau giam (loi short), duong
    tfav = df[tf].values.astype(np.float32)                     # phut toi dinh
    tadv = df[ta].values.astype(np.float32)                     # phut toi day
    retpct = (df[cr].values * 100.0).astype(np.float32)         # retEnd% (close-to-close)
    # HIT_short: cham -N% TRUOC khi cham +X_SL (path-aware) — KHONG phu thuoc X_SL
    hit_short = ((drop >= float(N_PCT)) & ((tadv < tfav) | (tfav <= 0))).astype(np.int8)
    out = pd.DataFrame({"ts": df["ts"].values, "symbol": df["symbol"].values,
                        "hit_short": hit_short, "rise": rise, "tfav": tfav,
                        "tadv": tadv, "retpct": retpct})
    log.info("Label SHORT %s N%d: %d/%d rows | base_rate(HIT_short)=%.4f | drop p50=%.2f p90=%.2f | rise p50=%.2f",
             horizon, N_PCT, len(out), n0, float(out.hit_short.mean()),
             float(np.percentile(drop, 50)), float(np.percentile(drop, 90)),
             float(np.percentile(rise, 50)))
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


def pnl_gross_short(te, s_sl):
    """Ke toan SHORT moi (let-dump-run, KHONG target co dinh), vector hoa:
    * rise_H (=maxFav_H*100) >= S -> stopped: pnl = -S (hard-SL cung, check TRUOC)
    * else                        -> pnl = -retEnd_H*100 (de dump chay toi het horizon)
    Khong con phu thuoc tHitFav/tHitAdv/hit_short — khong con nhanh chot-loi-som canh tranh SL.
    """
    rise = te["rise"].values
    retpct = te["retpct"].values
    stopped = rise >= float(s_sl)
    pnl = np.where(stopped, -float(s_sl), -retpct)
    return pnl.astype(np.float64)


def fit_predict(xgb, tr, te):
    """Model DUY NHAT: classifier P(HIT_short). Short khong dung EV-regressor (chi gating threshold)."""
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit_short"])
    return clf.predict_proba(te[FEAT])[:, 1]


def eval_fold(te, p, oos_from):
    """Tra ve dict per-fold: auc, base, N, va per (X_SL, P*) -> trades, gross, net, hit_rate."""
    from sklearn.metrics import roc_auc_score
    d = te.copy()
    d["p"] = np.asarray(p, dtype=float)
    base = float(d.hit_short.mean())
    try:
        auc = float(roc_auc_score(d.hit_short.values, d.p.values)) if d.hit_short.nunique() > 1 else None
    except Exception:
        auc = None
    r = {"oos_from": oos_from, "N": int(len(d)), "base_rate": round(base, 4),
         "AUC": round(auc, 4) if auc is not None else None, "xsl": {}}
    for x_sl in X_SL_GRID:
        d["pnl"] = pnl_gross_short(d, x_sl)
        thr = {}
        for ps in PSTAR_GRID:
            sel = d[d.p >= ps]
            n = int(len(sel))
            thr[str(ps)] = {
                "trades": n,
                "gross": round(float(sel.pnl.mean()), 4) if n else None,
                "net": round(float(sel.pnl.mean()) - FEE_PCT - FUNDING_BPS, 4) if n else None,
                "hit_rate": round(float(sel.hit_short.mean()), 4) if n else None}
        r["xsl"][str(x_sl)] = thr
    return r


def _med(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.median(vals)), 4) if vals else None


def aggregate(per_fold):
    """Aggregate qua fold + TACH REGIME BULL vs CHOP. trades_per_quarter = median (1 fold=1 quy)."""
    bull = [f for f in per_fold if pd.Timestamp(f["oos_from"]) < REGIME_CUT]
    chop = [f for f in per_fold if pd.Timestamp(f["oos_from"]) >= REGIME_CUT]
    agg = {"n_fold": len(per_fold), "n_bull": len(bull), "n_chop": len(chop),
           "auc_med": _med([f["AUC"] for f in per_fold]),
           "base_rate_med": _med([f["base_rate"] for f in per_fold]), "xsl": {}}
    for x_sl in X_SL_GRID:
        xk = str(x_sl)
        pgrid = {}
        for ps in PSTAR_GRID:
            pk = str(ps)
            def g(folds, field):
                return _med([f["xsl"][xk][pk][field] for f in folds])
            pgrid[pk] = {
                "tpq": g(per_fold, "trades"),
                "gross": g(per_fold, "gross"),
                "net": g(per_fold, "net"),
                "net_bull": g(bull, "net") if bull else None,
                "net_chop": g(chop, "net") if chop else None,
                "hit_rate": g(per_fold, "hit_rate")}
        agg["xsl"][xk] = pgrid
    return agg


def print_table(horizon, agg):
    print(f"\n===== SHORT [{horizon}] N{N_PCT} | folds={agg['n_fold']} (bull={agg['n_bull']} chop={agg['n_chop']}) auc_med={agg['auc_med']} base={agg['base_rate_med']} =====")
    for x_sl in X_SL_GRID:
        print(f"--- X_SL={x_sl}%  (median qua fold: tpq | net | net_BULL | net_CHOP | %HIT) ---")
        for ps in PSTAR_GRID:
            a = agg["xsl"][str(x_sl)][str(ps)]
            print("  P*>=%.2f : tpq=%s net=%s  bull=%s chop=%s  hit=%s" % (
                ps, a["tpq"], a["net"], a["net_bull"], a["net_chop"], a["hit_rate"]))


def eval_horizon(xgb, feats, horizon, folds):
    need = NEED_BARS[horizon]
    lb = load_short_labels(horizon, need)
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("[%s] Dataset ghep: %d rows | base_rate=%.4f", horizon, len(ds), float(ds.hit_short.mean()))
    per_fold = []
    purge = need * GRID_MS
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit_short"].sum() < 50 or (tr["hit_short"] == 0).sum() < 50:
            log.warning("[%s] fold %d thieu data (tr=%d te=%d hit=%d) - bo", horizon, fi,
                        len(tr), len(te), int(tr["hit_short"].sum()))
            continue
        p = fit_predict(xgb, tr, te)
        oos_from = str(pd.to_datetime(cut, unit="ms").date())
        r = eval_fold(te, p, oos_from)
        r["fold"] = fi
        r["oos_to"] = str(pd.to_datetime(oos_end, unit="ms").date())
        per_fold.append(r)
        d8 = r["xsl"][str(X_SL_DEFAULT)]["0.6"]
        log.info("[%s] fold %d [%s..%s] base=%.4f AUC=%s | X%d P*.6: tpq=%s net=%s hit=%s",
                 horizon, fi, oos_from, r["oos_to"], r["base_rate"], r["AUC"],
                 X_SL_DEFAULT, d8["trades"], d8["net"], d8["hit_rate"])
    return per_fold


def compact_points(horizon, agg, x_sl_list=None, p_list=None):
    """Diem dai dien (H, S, P*) cho dong SHORT_SELECTOR_RESULT. Mac dinh quet CA X_SL_GRID x
    P_REPR {0.5,0.6,0.7} — day du hon compact cu (chi 1 X_SL). auc/base ghi 1 lan/horizon
    (khong lap lai theo S/P* vi khong doi theo 2 truc do) de tiet kiem cho gioi han <2KB."""
    x_sl_list = x_sl_list if x_sl_list is not None else X_SL_GRID
    p_list = p_list if p_list is not None else P_REPR
    pts = []
    for x_sl in x_sl_list:
        for ps in p_list:
            a = agg["xsl"][str(x_sl)][str(ps)]
            pts.append({"h": horizon, "s": x_sl, "p": ps, "tpq": a["tpq"], "net": a["net"],
                        "nb": a["net_bull"], "nc": a["net_chop"], "hr": a["hit_rate"]})
    return pts


def run():
    cols = label_columns()
    horizons = ["4h"]
    if all(c in cols for c in ["maxFav_12h", "maxAdv_12h", "tHitFav_12h", "tHitAdv_12h", "retEnd_12h", "nBars_12h"]):
        horizons.append("12h")
    else:
        log.info("NO_12H — thieu cot 12h.")
    if all(c in cols for c in ["maxFav_24h", "maxAdv_24h", "tHitFav_24h", "tHitAdv_24h", "retEnd_24h", "nBars_24h"]):
        horizons.append("24h")
    else:
        log.info("NO_24H — thieu cot 24h.")

    feats = build_features()
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:2]
        log.info("SMOKE: chi chay 2 fold")
    log.info("SHORT-SELECTOR N%d | %d fold OOS=%dm | X_SL_GRID=%s | FUNDING_BPS=%.2f | horizons=%s",
             N_PCT, len(folds), OOS_MONTHS, X_SL_GRID, FUNDING_BPS, horizons)

    full = {"label": "short-selector", "n_pct": N_PCT, "x_sl_grid": X_SL_GRID,
            "funding_bps": FUNDING_BPS, "fee_pct": FEE_PCT, "first_oos": FIRST_OOS, "last": LAST,
            "oos_months": OOS_MONTHS, "seed": SEED, "regime_cut": str(REGIME_CUT.date()),
            "note": "ke toan let-dump-run (khong target co dinh): rise_H>=S -> -S (stopped),"
                    " else -> -retEnd_H*100. funding la XAP XI (FUNDING_BPS/keo);"
                    " funding THAT do o Java WFO APPLY_FUNDING_FEE=true",
            "horizons": {}}
    aucs = {}
    compact_by_h = {}
    for h in horizons:
        pf = eval_horizon(xgb, feats, h, folds)
        if not pf:
            log.warning("[%s] khong fold hop le — bo horizon.", h)
            continue
        agg = aggregate(pf)
        print_table(h, agg)
        full["horizons"][h] = {"aggregate": agg, "per_fold": pf}
        aucs[h] = agg["auc_med"]
        compact_by_h[h] = compact_points(h, agg)          # H x X_SL_GRID x P_REPR — day du

    if not full["horizons"]:
        raise SystemExit("Khong horizon nao co fold hop le — kiem alignment ts/symbol.")

    json.dump(full, open(os.path.join(OUT_DIR, "short_selector_results.json"), "w"), indent=2)

    # Dong SHORT_SELECTOR_RESULT phai <2KB — chon diem dai dien, KHONG in het grid (full grid
    # da nam day du trong short_selector_results.json). Giam dan chi tiet (tier) toi khi vua khit.
    hz = list(compact_by_h.keys())

    def _line(pts, p_set):
        pts_f = [p for p in pts if p["p"] in p_set]
        return json.dumps({"n_pct": N_PCT, "sl_grid": X_SL_GRID, "funding_bps": FUNDING_BPS,
                           "auc": aucs, "pts": pts_f}, separators=(",", ":"))

    all_pts = [p for h in hz for p in compact_by_h[h]]
    tiers = [
        set(P_REPR),                      # tier0: full H x S x {0.5,0.6,0.7}
        {0.6},                            # tier1: chi P*=0.6, van du 4 S x N horizon
    ]
    line = None
    for p_set in tiers:
        cand = _line(all_pts, p_set)
        if len(cand) <= 2000:
            line = cand
            break
    if line is None:
        # tier2: S hep nhat (SL rong nhat vs chat nhat) tai P*=0.6 — vua canh tranh vua gon
        narrow_pts = [p for p in all_pts if p["p"] == 0.6 and p["s"] in (min(X_SL_GRID), max(X_SL_GRID))]
        line = _line(narrow_pts, {0.6})
        if len(line) > 2000:
            # tier3: cuoi cung — cat bot theo so luong, dam bao TUYET DOI <2KB
            line = json.dumps({"n_pct": N_PCT, "sl_grid": X_SL_GRID, "auc": aucs,
                               "pts": narrow_pts[:len(hz)]}, separators=(",", ":"))
    print("SHORT_SELECTOR_RESULT " + line)
    log.info("XONG -> %s/short_selector_results.json (RESULT line len=%d)", OUT_DIR, len(line))


if __name__ == "__main__":
    run()
