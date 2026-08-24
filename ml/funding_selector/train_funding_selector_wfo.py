#!/usr/bin/env python3
"""
TASK-108 - WFO ROLLING cho funding SELECTOR (cả 4 horizon 4h/12h/24h/72h).

MỤC TIÊU (hướng B, user chốt): đo model selector có GENERALIZE + ỔN ĐỊNH qua các cửa sổ
trượt không — train LẠI mỗi cutoff (expanding), KHÔNG phải 1 holdout cố định như v1.
Đo cả 4 horizon để xem khung nào ổn định nhất → chốt dùng khung nào (funding fee CŨ ~ horizon 72h).

KHÁC train_funding_selector.py: cái cũ split 1 lần (train/val/test 12m cuối). Cái này LOOP cutoff:
  expanding train [đầu .. cutoff_k) → OOS [cutoff_k .. cutoff_k+3m) → trượt 3m, KHÔNG chồng lấn.
Mỗi fold × 4 horizon đo: base_rate, LIFT(top-decile), hit_top, rankIC, N. Xuất chuỗi per-fold
→ thấy LIFT/IC dao động hay ổn định qua regime.

ĐỒNG BỘ chống lệch ngầm (giống bài học gate): build_dataset DÙNG LẠI Y HỆT logic train cũ
(đọc bin, merge_asof OI by symId backward tol 2h, label exact-join symbol+ts, filter nBars>=H_STEPS,
y=(maxFav>=6%), feat = f0..f39 + 5 OI ĐÚNG thứ tự). KHÔNG scale. purge=horizon giữa train/OOS.

Env:
  TOOL1_GLOB OI_FILE LABEL_CSV MAP_CSV  (bắt buộc — giống train cũ)
  OOS_MONTHS (3)  FIRST_OOS (202301: 2 năm lịch sử tối thiểu)  LAST (202606)
  OUT_DIR (.)  SAVE_LAST_MODEL=1 (lưu model fold cuối cho mỗi H — để vòng cuối/generate dùng)
  SMOKE=1 (chỉ 1 fold đầu, in shape — kiểm luồng nhanh)
Chạy Kaggle (data đã là dataset, RAM 30GB đủ giải nén OI). 1 kernel rolling, multi sau.
"""
import os, gzip, glob, json, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wfo_sel")

H_STEPS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}   # số bước-15m mỗi horizon
HORIZONS = ["4h", "12h", "24h", "72h"]
WIN = 0.06
# [2-sided triple-barrier] SL/TP song song, param qua env. maxFav/maxAdv la RATIO;
# maxFav DUONG (dinh), maxAdv AM (day = min low/close-1) -> adv_hit khi maxAdv <= -SEL_ADV_PCT.
SEL_FAV_PCT = float(os.environ.get("SEL_FAV_PCT", "0.06"))  # TP
SEL_ADV_PCT = float(os.environ.get("SEL_ADV_PCT", "0.03"))  # SL placeholder, user chot sau
SELECTOR_GRID_MIN = int(os.environ.get("SELECTOR_GRID_MIN", "15"))
SEL_SAMPLE_MODE = os.environ.get("SEL_SAMPLE_MODE", "grid")   # "grid" (loc ts%GRID_MS==0) | "nonoverlap"
SEL_TIMEOUT_H = int(os.environ.get("SEL_TIMEOUT_H", "4"))     # horizon (h) dat luoi khi nonoverlap
# purge=horizon wall-clock DOC LAP voi luoi lay mau (H_STEPS o 15m). Neu buoc luoi doi (nonoverlap),
# purge KHONG duoc scale theo -> dung PURGE_STEP_MS=15m (khop don vi H_STEPS). Default: gia tri y het cu.
PURGE_STEP_MS = 15 * 60 * 1000
if SEL_SAMPLE_MODE == "nonoverlap":
    GRID_MS = SEL_TIMEOUT_H * 3600 * 1000   # luoi lay mau = horizon -> mau KHONG chong lap
else:
    GRID_MS = SELECTOR_GRID_MIN * 60 * 1000
MO_MS = 30 * 24 * 3600 * 1000
log.info("SAMPLE_MODE=%s SELECTOR_GRID_MIN=%d GRID_MS=%dms SEL_TIMEOUT_H=%dh (purge dung PURGE_STEP_MS=15m doc lap)",
         SEL_SAMPLE_MODE, SELECTOR_GRID_MIN, GRID_MS, SEL_TIMEOUT_H)
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES   # 45 feat — KHỚP train_meta

TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

TOOL1_GLOB = os.environ["TOOL1_GLOB"]
OI_FILE = os.environ["OI_FILE"]
LABEL_CSV = os.environ["LABEL_CSV"]
MAP_CSV = os.environ["MAP_CSV"]
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))
OOS_MONTHS = int(os.environ.get("OOS_MONTHS", "3"))
FIRST_OOS = os.environ.get("FIRST_OOS", "202301")
LAST = os.environ.get("LAST", "202606")
OUT_DIR = os.environ.get("OUT_DIR", ".")
SMOKE = os.environ.get("SMOKE", "0") == "1"
SAVE_LAST_MODEL = os.environ.get("SAVE_LAST_MODEL", "0") == "1"
SEED = int(os.environ.get("SEED", "42"))
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
    parts = []
    for fp in files:
        a = _read(fp, TOOL1_DT, 170, grid=True)   # lọc 15m grid GIỐNG train cũ
        parts.append(a)
    a = np.concatenate(parts)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    log.info("Tool1 (15m grid): %d rows | %d symId | ts[%s..%s]", len(df), df.symId.nunique(),
             pd.to_datetime(df.ts.min(), unit="ms"), pd.to_datetime(df.ts.max(), unit="ms"))
    return df.sort_values("ts").reset_index(drop=True)


def load_oi():
    files = sorted(glob.glob(OI_FILE, recursive=True)) if any(c in OI_FILE for c in "*?[") else [OI_FILE]
    a = _read(files[0], OI_DT, 30)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    O = np.asarray(a["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        df[nm] = O[:, j]
    log.info("OI: %d rows | %d symId", len(df), df.symId.nunique())
    return df.sort_values("ts").reset_index(drop=True)


def load_labels():
    """[2-SIDED triple-barrier] y_<H> theo SL vs TP song song (thay label 1-chieu maxFav>=6%).
    fav_hit = maxFav_H >= SEL_FAV_PCT (TP);  adv_hit = maxAdv_H <= -SEL_ADV_PCT (SL, maxAdv la ratio AM).
    y=1 (win): fav_hit & (not adv_hit OR tHitFav < tHitAdv)   -> cham TP truoc.
    y=0 (lose): adv_hit & (not fav_hit OR tHitAdv <= tHitFav) -> cham SL truoc (tie -> SL).
    y=0 (timeout): khong cham barrier nao trong H.
    Chi tinh tren nBars_H du + maxFav/maxAdv notna. tHit* cung don vi (phut)."""
    cols = (["tEpochMs", "symbol"]
            + [f"maxFav_{H}" for H in HORIZONS] + [f"maxAdv_{H}" for H in HORIZONS]
            + [f"tHitFav_{H}" for H in HORIZONS] + [f"tHitAdv_{H}" for H in HORIZONS]
            + [f"nBars_{H}" for H in HORIZONS])
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip")
    df = df.rename(columns={"tEpochMs": "ts"})
    for H in HORIZONS:
        need = H_STEPS[H]
        valid = (df[f"nBars_{H}"] >= need) & df[f"maxFav_{H}"].notna() & df[f"maxAdv_{H}"].notna()
        fav_hit = df[f"maxFav_{H}"] >= SEL_FAV_PCT
        adv_hit = df[f"maxAdv_{H}"] <= -SEL_ADV_PCT
        fav_first = df[f"tHitFav_{H}"] < df[f"tHitAdv_{H}"]
        win = fav_hit & (~adv_hit | fav_first)
        lose = adv_hit & (~fav_hit | ~fav_first)
        timeout = (~fav_hit) & (~adv_hit)
        df[f"y_{H}"] = np.where(valid, win.astype(np.float32), np.nan)
        v = int(valid.sum())
        if v > 0:
            log.info("Label %s [2sided fav=%.3f adv=%.3f]: valid=%d base_new(y=1)=%.4f "
                     "(old_1sided=%.4f) | win=%.4f lose=%.4f timeout=%.4f", H, SEL_FAV_PCT, SEL_ADV_PCT,
                     v, float(np.nanmean(df.loc[valid, f"y_{H}"])), float((fav_hit & valid).sum()) / v,
                     float((win & valid).sum()) / v, float((lose & valid).sum()) / v,
                     float((timeout & valid).sum()) / v)
        else:
            log.warning("Label %s: 0 dong hop le", H)
    keep = ["ts", "symbol"] + [f"y_{H}" for H in HORIZONS]
    return df[keep]


def build_dataset(t, o, lb, mp):
    """Ghép Tool1+OI+label GIỐNG HỆT train cũ. Trả ds có cột y_<H> cho cả 4 horizon."""
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    ds = merged.merge(lb, on=["symbol", "ts"], how="inner")
    log.info("Dataset ghép: %d rows | n_sym=%d | base_rate per-H: %s", len(ds), ds.symbol.nunique(),
             {H: round(float(ds[f"y_{H}"].mean()), 4) for H in HORIZONS})
    return ds.sort_values("ts").reset_index(drop=True)


def evaluate(score, y):
    import scipy.stats as st
    m = ~np.isnan(y)
    y = np.asarray(y)[m]; score = np.asarray(score, dtype=float)[m]
    if len(y) < 200 or y.sum() < 10:
        return None
    base = y.mean(); n = len(y); k = max(100, n // 10)
    idx = np.argsort(-score)[:k]
    hit = y[idx].mean()
    lift = hit / base if base > 0 else float("nan")
    ic, _ = st.spearmanr(score, y)
    return {"N": int(n), "base_rate": round(float(base), 4), "N_top": int(k),
            "hit_top": round(float(hit), 4), "LIFT": round(float(lift), 3),
            "rankIC": round(float(ic), 4)}


def build_folds():
    """expanding: OOS_k = [cutoff_k, cutoff_k+OOS_MONTHS), trượt = OOS_MONTHS (không chồng lấn)."""
    def ym2ms(ym):
        return pd.Timestamp(f"{ym[:4]}-{ym[4:]}-01").value // 10**6
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def run():
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)   # symId,symbol
    lb = load_labels()
    ds = build_dataset(t, o, lb, mp)
    del t, o, lb
    if len(ds) == 0:
        raise SystemExit("Dataset rỗng sau merge — kiểm alignment ts/symbol.")

    import xgboost as xgb
    folds = build_folds()
    log.info("WFO selector: %d fold expanding OOS=%dm, %d horizon", len(folds), OOS_MONTHS, len(HORIZONS))
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chỉ chạy fold 0")

    results = {H: [] for H in HORIZONS}
    last_models = {}
    for fi, (cut, oos_end) in enumerate(folds):
        purge = {H: H_STEPS[H] * PURGE_STEP_MS for H in HORIZONS}   # wall-clock horizon, doc lap luoi lay mau
        oos = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(oos) < 500:
            log.warning("fold %d OOS quá ít (%d) — bỏ", fi, len(oos))
            continue
        for H in HORIZONS:
            ycol = f"y_{H}"
            tr = ds[ds.ts < cut - purge[H]]
            tr = tr[tr[ycol].notna()]
            te = oos[oos[ycol].notna()]
            if len(tr) < 5000 or len(te) < 200 or tr[ycol].sum() < 50:
                log.warning("fold %d H=%s thiếu data (tr=%d te=%d) — bỏ", fi, H, len(tr), len(te))
                continue
            pos = tr[ycol].mean()
            clf = xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                    scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                    eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=SEED)
            clf.fit(tr[FEAT], tr[ycol])
            pwin = clf.predict_proba(te[FEAT])[:, 1]
            ev = evaluate(pwin, te[ycol].values)
            if ev:
                ev["fold"] = fi
                ev["oos_from"] = str(pd.to_datetime(cut, unit="ms").date())
                ev["oos_to"] = str(pd.to_datetime(oos_end, unit="ms").date())
                ev["n_train"] = int(len(tr))
                results[H].append(ev)
                log.info("fold %d H=%s [%s..%s] LIFT=%.3f rankIC=%.4f base=%.3f N=%d ntr=%d",
                         fi, H, ev["oos_from"], ev["oos_to"], ev["LIFT"], ev["rankIC"],
                         ev["base_rate"], ev["N"], len(tr))
            if SAVE_LAST_MODEL:
                last_models[H] = clf   # giữ model fold cuối mỗi H

    # tổng hợp ổn định per-horizon
    summary = {}
    for H in HORIZONS:
        r = results[H]
        if not r:
            summary[H] = {"n_fold": 0}
            continue
        lifts = [x["LIFT"] for x in r]
        ics = [x["rankIC"] for x in r]
        summary[H] = {
            "n_fold": len(r),
            "LIFT_median": round(float(np.median(lifts)), 3),
            "LIFT_min": round(float(np.min(lifts)), 3),
            "LIFT_max": round(float(np.max(lifts)), 3),
            "LIFT_std": round(float(np.std(lifts)), 3),
            "pct_fold_LIFT_gt_1": round(float(np.mean([l > 1.0 for l in lifts])), 3),
            "rankIC_median": round(float(np.median(ics)), 4),
            "rankIC_min": round(float(np.min(ics)), 4),
            "rankIC_std": round(float(np.std(ics)), 4),
            "pct_fold_IC_gt_0": round(float(np.mean([c > 0 for c in ics])), 3),
        }
        log.info("=== H=%s ỔN ĐỊNH: %d fold | LIFT med=%.3f [%.3f,%.3f] std=%.3f | rankIC med=%.4f std=%.4f | %%fold IC>0=%.2f",
                 H, summary[H]["n_fold"], summary[H]["LIFT_median"], summary[H]["LIFT_min"],
                 summary[H]["LIFT_max"], summary[H]["LIFT_std"], summary[H]["rankIC_median"],
                 summary[H]["rankIC_std"], summary[H]["pct_fold_IC_gt_0"])

    out = {"oos_months": OOS_MONTHS, "first_oos": FIRST_OOS, "last": LAST, "seed": SEED,
           "n_folds_built": len(folds), "summary": summary, "per_fold": results}
    json.dump(out, open(os.path.join(OUT_DIR, "wfo_selector_results.json"), "w"), indent=2)
    log.info("XONG -> %s/wfo_selector_results.json", OUT_DIR)

    if SAVE_LAST_MODEL:
        for H, clf in last_models.items():
            clf.save_model(os.path.join(OUT_DIR, f"model_wfo_last_{H}.ubj"))
        log.info("đã lưu %d model fold cuối", len(last_models))


if __name__ == "__main__":
    run()
