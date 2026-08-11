#!/usr/bin/env python3
# SHORT-CROWD-ROBUST -- DE-RISK proxy short-crowding TRUOC KHI ton slot WFO Oracle.
#   BASE: copy 100% preamble/logic short-crowding/run_train.py (label short: drop=-maxAdv_H*100,
#   HIT khi drop>=t; ke toan let-run: stopped(rise>=s & tfav<tadv)->-s, else->-retEnd_H*100;
#   gate crowding = ls_toptrader quantile CROSS-SECTIONAL cung ts). Giu y het de so KHOP voi
#   short-crowding (khong doi feature/fold/classifier/accounting).
#
# CONFIG WINNER (co dinh, KHONG sweep lai) tu short-crowding: t=9% drop, horizon=24h, stop=30%,
#   gate = ls_toptrader top-10% (q0.90) AND ps>=0.60. Ket qua goc: net_chop=+3.47/keo, tpq>=30.
#
# NGHI NGO: co the la artifact 1 nam may man keo trung binh len (bai hoc cu: proxy "trailing"
#   tung bao +14.8 lac quan gia do overfit 1 giai doan roi sup khi test rong hon). 3 KIEM TRA
#   DE-RISK truoc khi don slot WFO:
#   1) PER-YEAR: tach net/tpq/winrate theo NAM OOS (2022/2023/2024/2025) + regime bull/chop
#      (cung REGIME_CUT nhu short-crowding: bull=oos_from<2025-01-01, chop=>=2025-01-01).
#      Cau hoi: net_chop DUONG DEU cac nam hay chi 1 nam keo trung binh?
#   2) SWEEP MIN: q_crowd {0.80,0.85,0.90,0.95} x horizon {12h,24h} (t=9,s=30,p>=0.60 GIU CO
#      DINH -- chi doi q_crowd/horizon). Cau hoi: net_chop co MONOTONIC tang theo q_crowd
#      khong (dung ly thuyet: crowd cao hon => short tot hon)? Neu khong monotonic => nghi
#      ngo them noise/overfit threshold.
#   3) PLACEBO: hoan vi (shuffle) ls_toptrader CHEO-SECTIONAL -- cung 1 ts, tron ngau nhien gia
#      tri ls_toptrader giua cac symbol dang song (GIU NGUYEN phan phoi tai moi ts, chi pha moi
#      lien he thuc symbol<->crowding). Neu gate THAT: net_chop placebo phai SUP ve ~0 (gate
#      random khong con edge). Neu placebo VAN duong dang ke => gate la GIA (proxy an theo bien
#      khac tuong quan gia voi ls_toptrader, khong phai crowding that).
#
# Marker SHORT_CROWD_ROBUST_RESULT (JSON 1 dong) cho 3 kiem tra + config winner.
# KHONG deploy, KHONG dung WFO Oracle o day -- chi de-risk tren proxy label (funding_label.csv)
# TRUOC KHI quyet dinh co don slot WFO cho short-crowding hay khong. KHONG git commit.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== CONFIG WINNER (pre-register -- KHONG doi sau khi nhin so) =====
HORIZON_WINNER = "24h"                                            # horizon WINNER (per-year + placebo)
HORIZONS = ["24h", "12h"]                                         # 24h=winner, 12h them cho sweep Q2
TARGET = int(os.environ.get("TARGET", "9"))                       # t=9% drop (WINNER, co dinh)
STOP = int(os.environ.get("STOP", "30"))                          # s=30% (WINNER, co dinh)
PSTAR = float(os.environ.get("PSTAR", "0.60"))                    # p>=0.60 (WINNER, co dinh)
QCROWD_WINNER = float(os.environ.get("QCROWD_WINNER", "0.90"))    # q_crowd=0.90 (WINNER, co dinh)
QCROWD_SWEEP = [float(x) for x in os.environ.get("QCROWD_SWEEP", "0.80,0.85,0.90,0.95").split(",")]
LS_FEAT = os.environ.get("LS_FEAT", "ls_toptrader")               # feature crowding WINNER
FEE_PCT = 0.2                                                     # phi 2 chan 0.1%*2 (funding OFF)
NEED_BARS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}
REGIME_CUT = pd.Timestamp("2025-01-01")                           # BULL: oos_from<cut ; CHOP: >=cut
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat -- KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("short-crowd-robust")


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
FIRST_OOS = os.environ.get("FIRST_OOS", "202201")     # muon coverage 2022 cho per-year check (Q1)
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
    """Merged features (ts, symId, 45 feat, symbol) -- dung CHUNG cho MOI horizon."""
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
    """Cot ke toan cho horizon H: ts,symbol,rise,dropp,tfav,tadv,retpct."""
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
    log.info("Label %s: %d/%d rows | drop p50=%.2f p90=%.2f | rise p50=%.2f | base(drop>=%d)=%.4f",
             horizon, len(out), n0, float(np.percentile(dropp, 50)), float(np.percentile(dropp, 90)),
             float(np.percentile(rise, 50)), TARGET, float((dropp >= TARGET).mean()))
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


def fit_predict(xgb, tr, te):
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit"])
    return clf.predict_proba(te[FEAT])[:, 1]


def pnl_short(df, s):
    """Ke toan SL-cung short LET-RUN (path-aware), giong het short-crowding (t chi la LABEL):
       stopped=(rise>=s)&(tfav<tadv) -> -s ; else -> -retpct (ride het horizon)."""
    rise = df["rise"].values
    tfav = df["tfav"].values
    tadv = df["tadv"].values
    retpct = df["retpct"].values
    stopped = (rise >= float(s)) & (tfav < tadv)
    return np.where(stopped, -float(s), -retpct).astype(np.float64)


def run_fold_predictions(xgb, ds, folds, need):
    """Train clfP(HIT_short_TARGET) tren tung fold IS (ts<cut-purge), predict OOS [cut,oos_end).
       Tra list DataFrame per-fold: ts,symbol,oos_from,fold,p,hit,dropp,ls_toptrader,rise,tfav,
       tadv,retpct -- du de tinh gate + pnl downstream MA KHONG train lai."""
    d = ds.copy()
    d["hit"] = (d["dropp"].values >= float(TARGET)).astype(np.int8)
    purge = need * GRID_MS
    out = []
    for fi, (cut, oos_end) in enumerate(folds):
        tr = d[d.ts < cut - purge]
        te = d[(d.ts >= cut) & (d.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("fold %d [cut=%s] thieu data (tr=%d te=%d pos=%d) - bo", fi,
                        pd.to_datetime(cut, unit="ms").date(), len(tr), len(te), int(tr["hit"].sum()))
            continue
        p = fit_predict(xgb, tr, te)
        oos_from = str(pd.to_datetime(cut, unit="ms").date())
        oos_to = str(pd.to_datetime(oos_end, unit="ms").date())
        sub = te[["ts", "symbol", "dropp", "ls_toptrader", "rise", "tfav", "tadv", "retpct"]].copy()
        sub["p"] = np.asarray(p, dtype=float)
        sub["hit"] = (sub["dropp"].values >= float(TARGET)).astype(np.int8)
        sub["oos_from"] = oos_from
        sub["fold"] = fi
        out.append(sub.reset_index(drop=True))
        log.info("fold %d [%s..%s] tr=%d te=%d pos_rate_tr=%.4f", fi, oos_from, oos_to,
                  len(tr), len(te), float(tr["hit"].mean()))
    return out


def crowd_mask(df, q, ls_feat=None, pstar=None):
    """Entry = (p>=pstar) AND (ls_feat quantile cross-sectional cung ts >= q). Giong het
       co che rank topK/quantile trong short-crowding (d.groupby('ts')[lf].rank(pct=True))."""
    lf = ls_feat if ls_feat is not None else LS_FEAT
    ps = pstar if pstar is not None else PSTAR
    pct = df.groupby("ts")[lf].rank(pct=True)
    return (df["p"].values >= ps) & (pct.values >= q)


def pooled_metrics(folds_dfs, mask_fn, s):
    """Pool trades qua nhieu fold (list DataFrame) sau mask_fn(df)->bool array.
       net = mean(pnl)-fee | tpq = trung binh so trade/fold | win = ty le pnl>0."""
    all_pnl = []
    per_fold_n = []
    for df in folds_dfs:
        m = mask_fn(df)
        n = int(np.asarray(m).sum())
        per_fold_n.append(n)
        if n:
            all_pnl.append(pnl_short(df[m], s))
    if not all_pnl:
        return {"net": None, "tpq": round(float(np.mean(per_fold_n)), 2) if per_fold_n else 0.0,
                "win": None, "n_trades": 0, "n_fold": len(folds_dfs)}
    pnl = np.concatenate(all_pnl)
    return {"net": round(float(pnl.mean()) - FEE_PCT, 4),
            "tpq": round(float(np.mean(per_fold_n)), 2),
            "win": round(float((pnl > 0).mean()), 4),
            "n_trades": int(len(pnl)), "n_fold": len(folds_dfs)}


def split_regime(folds_dfs):
    bull = [d for d in folds_dfs if pd.Timestamp(d["oos_from"].iloc[0]) < REGIME_CUT]
    chop = [d for d in folds_dfs if pd.Timestamp(d["oos_from"].iloc[0]) >= REGIME_CUT]
    return bull, chop


def split_year(folds_dfs):
    by_year = {}
    for d in folds_dfs:
        y = pd.Timestamp(d["oos_from"].iloc[0]).year
        by_year.setdefault(y, []).append(d)
    return by_year


# ===== CAU HOI 1: PER-YEAR + REGIME (CONFIG WINNER co dinh) =====
def q1_per_year_regime(folds24):
    mask_fn = lambda df: crowd_mask(df, QCROWD_WINNER)
    by_year = split_year(folds24)
    per_year = {}
    for y in sorted(by_year):
        m = pooled_metrics(by_year[y], mask_fn, STOP)
        per_year[str(y)] = {"net": m["net"], "tpq": m["tpq"], "win": m["win"],
                            "n_trades": m["n_trades"], "n_fold": m["n_fold"]}
        log.info("[Q1 PER-YEAR %d] net=%s tpq=%s win=%s n_trades=%d n_fold=%d",
                 y, m["net"], m["tpq"], m["win"], m["n_trades"], m["n_fold"])
    for y in (2022, 2023, 2024, 2025):
        if str(y) not in per_year:
            per_year[str(y)] = None
            log.warning("[Q1 PER-YEAR] THIEU nam %d trong OOS folds (khong du data hop le trong "
                        "FIRST_OOS=%s..LAST=%s hoac ngoai range dataset)", y, FIRST_OOS, LAST)
    bull, chop = split_regime(folds24)
    regime = {"bull": pooled_metrics(bull, mask_fn, STOP) if bull else None,
             "chop": pooled_metrics(chop, mask_fn, STOP) if chop else None}
    log.info("[Q1 REGIME] bull(oos_from<%s)=%s | chop(oos_from>=%s)=%s",
             REGIME_CUT.date(), regime["bull"], REGIME_CUT.date(), regime["chop"])
    return per_year, regime


# ===== CAU HOI 2: SWEEP q_crowd x horizon (t/s/p GIU CO DINH) =====
def q2_sweep(folds_by_h):
    rows = []
    for h in HORIZONS:
        folds = folds_by_h.get(h, [])
        if not folds:
            log.warning("[Q2 SWEEP] horizon %s khong co fold hop le -- bo", h)
            continue
        bull, chop = split_regime(folds)
        chop_seq = []
        for q in QCROWD_SWEEP:
            mfn = lambda df, q=q: crowd_mask(df, q)
            m_all = pooled_metrics(folds, mfn, STOP)
            m_bull = pooled_metrics(bull, mfn, STOP) if bull else {"net": None, "tpq": 0.0}
            m_chop = pooled_metrics(chop, mfn, STOP) if chop else {"net": None, "tpq": 0.0}
            row = {"h": h, "q": q, "net": m_all["net"], "net_bull": m_bull["net"],
                  "net_chop": m_chop["net"], "tpq": m_all["tpq"]}
            rows.append(row)
            chop_seq.append(m_chop["net"])
            log.info("[Q2 SWEEP h=%s q=%.2f] net=%s net_bull=%s net_chop=%s tpq=%s",
                     h, q, row["net"], row["net_bull"], row["net_chop"], row["tpq"])
        valid = [v for v in chop_seq if v is not None]
        mono = bool(all(valid[i] <= valid[i + 1] for i in range(len(valid) - 1))) if len(valid) > 1 else None
        log.info("[Q2 SWEEP h=%s] net_chop theo q=%s -> seq=%s MONOTONIC(tang dan)=%s",
                 h, QCROWD_SWEEP, chop_seq, mono)
    return rows


# ===== CAU HOI 3: PLACEBO (shuffle ls_toptrader cheo-section, cung ts) =====
def q3_placebo(folds24):
    rng = np.random.default_rng(SEED)

    def _shuf(x):
        v = x.values.copy()
        rng.shuffle(v)
        return v

    shuffled = []
    for df in folds24:
        d2 = df.copy()
        d2[f"{LS_FEAT}_shuf"] = d2.groupby("ts")[LS_FEAT].transform(_shuf)
        shuffled.append(d2)

    def mask_fn(df):
        pct = df.groupby("ts")[f"{LS_FEAT}_shuf"].rank(pct=True)
        return (df["p"].values >= PSTAR) & (pct.values >= QCROWD_WINNER)

    bull, chop = split_regime(shuffled)
    m_all = pooled_metrics(shuffled, mask_fn, STOP)
    m_bull = pooled_metrics(bull, mask_fn, STOP) if bull else {"net": None}
    m_chop = pooled_metrics(chop, mask_fn, STOP) if chop else {"net": None}
    log.info("[Q3 PLACEBO] shuffle %s cheo-section (cung ts, GIU phan phoi tai moi ts) -> "
             "net=%s net_bull=%s net_chop=%s (that WINNER net_chop~+3.47 -- neu placebo van "
             "duong dang ke => gate GIA)", LS_FEAT, m_all["net"], m_bull["net"], m_chop["net"])
    return m_chop["net"], m_all["net"]


def run():
    cols = label_columns()
    ok = True
    for h in HORIZONS:
        need_cols = [f"{p}_{h}" for p in ["maxFav", "maxAdv", "tHitFav", "tHitAdv", "retEnd", "nBars"]]
        missing = [c for c in need_cols if c not in cols]
        if missing:
            log.error("THIEU cot horizon %s trong funding_label.csv: %s", h, missing)
            ok = False
    if not ok:
        raise SystemExit("THIEU cot horizon can thiet -- kiem funding_label.csv.")

    feats = build_features()
    import xgboost as xgb

    folds_by_h = {}
    for h in HORIZONS:
        need = NEED_BARS[h]
        lb = load_horizon_labels(h, need)
        ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
        log.info("[%s] Dataset ghep: %d rows", h, len(ds))
        folds = build_folds()
        if SMOKE:
            folds = folds[:2]
            log.info("SMOKE: chi chay 2 fold")
        fold_dfs = run_fold_predictions(xgb, ds, folds, need)
        folds_by_h[h] = fold_dfs
        log.info("[%s] %d/%d fold hop le", h, len(fold_dfs), len(folds))

    folds24 = folds_by_h.get(HORIZON_WINNER, [])
    if not folds24:
        raise SystemExit(f"KHONG fold hop le cho horizon WINNER {HORIZON_WINNER} -- khong the danh gia.")

    per_year, regime = q1_per_year_regime(folds24)
    sweep_rows = q2_sweep(folds_by_h)
    placebo_net_chop, placebo_net_all = q3_placebo(folds24)

    winner_mask = lambda df: crowd_mask(df, QCROWD_WINNER)
    winner_all = pooled_metrics(folds24, winner_mask, STOP)
    bull24, chop24 = split_regime(folds24)
    winner_bull = pooled_metrics(bull24, winner_mask, STOP) if bull24 else {"net": None}
    winner_chop = pooled_metrics(chop24, winner_mask, STOP) if chop24 else {"net": None}

    result = {
        "label": "short-crowd-robust",
        "config_winner": {"t": TARGET, "h": HORIZON_WINNER, "s": STOP, "q_crowd": QCROWD_WINNER,
                          "p_star": PSTAR, "ls_feat": LS_FEAT},
        "winner_net": winner_all["net"], "winner_net_bull": winner_bull["net"],
        "winner_net_chop": winner_chop["net"], "winner_tpq": winner_all["tpq"],
        "first_oos": FIRST_OOS, "last": LAST, "oos_months": OOS_MONTHS, "seed": SEED,
        "regime_cut": str(REGIME_CUT.date()),
        "per_year": per_year, "regime": regime,
        "q_sweep": sweep_rows,
        "placebo_net_chop": placebo_net_chop, "placebo_net_all": placebo_net_all,
    }

    out_path = os.path.join(OUT_DIR, "short_crowd_robust_results.json")
    json.dump(result, open(out_path, "w"), indent=2, default=str)

    if placebo_net_chop is not None and winner_chop["net"] is not None and placebo_net_chop > 0 \
            and placebo_net_chop > 0.3 * winner_chop["net"]:
        log.warning("[Q3 PLACEBO] net_chop placebo=%s KHONG sup ve ~0 so voi WINNER net_chop=%s "
                    "-> NGHI NGO gate GIA (proxy an theo bien khac tuong quan gia voi %s).",
                    placebo_net_chop, winner_chop["net"], LS_FEAT)
    else:
        log.info("[Q3 PLACEBO] net_chop placebo=%s sup ve gan 0 so voi WINNER net_chop=%s -> "
                 "gate co ve THAT (khong phai may man).", placebo_net_chop, winner_chop["net"])

    line = json.dumps({"config_winner": result["config_winner"],
                       "winner_net_chop": winner_chop["net"],
                       "per_year": per_year, "regime": regime, "q_sweep": sweep_rows,
                       "placebo_net_chop": placebo_net_chop, "placebo_net_all": placebo_net_all},
                      separators=(",", ":"), default=str)
    if len(line) > 3000:
        line = json.dumps({"winner_net_chop": winner_chop["net"], "per_year": per_year,
                           "placebo_net_chop": placebo_net_chop}, separators=(",", ":"), default=str)
    print("SHORT_CROWD_ROBUST_RESULT " + line)
    log.info("XONG -> %s (RESULT line len=%d)", out_path, len(line))


if __name__ == "__main__":
    run()
