#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHORT-PROBE: do viec SHORT cac symbol duoc selector cham diem THAP nhat (bottom-decile pwin).

CANH BAO ARCHITECTURE (doc ky truoc khi dung):
  * Short PHA bat bien long-only cua he thong. Trong crypto short co upside vo han -> BAT BUOC SL cung.
    Bo code nay la PROBE NGHIEN CUU, KHONG deploy production.
  * Label selector = P(maxFav>=6%) = "kha nang bom". pwin THAP = "it kha nang bom",
    KHONG dong nghia "kha nang dump". => tin hieu short o day la PROXY YEU (vang-upside, khong phai downside).
  * Endpoint short alpha KHONG = short monetize duoc. Cu squeeze (spike len truoc khi dump) an short truoc.
    => BAT BUOC do short MAE (=maxFav) + squeeze_frac, va SL-sim, khong chi endpoint tran.

Do (event-level, non-overlapping, khu overlap giong reprobe):
  - chon BOTTOM-decile theo pwin per-timestamp + cooldown H bar/symbol.
  - short_ret_end = -retEnd (gross endpoint, KHONG SL, KHONG funding).
  - short_excess  = -(retEnd - bench_ret)  (excess vs short trung binh universe cung ts).
  - short_MAE     = maxFav (short lun sau bao nhieu trong cua so) -> median + squeeze_frac (maxFav>=WIN).
  - short_MFE     = -maxAdv (short lai tot nhat co the).
  - short_pnl_sl  = SL-sim THO: neu maxFav>=SL_SHORT -> -SL_SHORT; nguoc lai -retEnd; roi tru FLAT_COST.
                    (proxy: gia dinh bi stop khi cham SL; KHONG biet maxFav xay ra truoc/sau retEnd -> xem CAVEAT).
  VERDICT cham tren short_pnl_sl (sau SL+cost), KHONG tren endpoint tran.

CAVEAT: maxFav/maxAdv la max/min ca cua so, khong phai path tuan tu (giong Track A-lite). SL-sim co the
lac quan/bi quan hon path that. Path dung 100% can replay 1m (buoc Java sau neu probe nay dang di tiep).
Funding cho SHORT dao dau (short thuong NHAN funding khi contango) -> net short co the tot hon gross-flat_cost
o truc funding; CHUA model o day, ghi ro.
"""
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("short_probe")

# ===== PRE-REGISTER GATE (ghi truoc khi xem so) — Uni re-affirm truoc khi coi la chinh thuc =====
# SHORT_VIABLE neu: median short_pnl_sl (sau SL+cost) > 0 VA >=60% fold duong.
# CANH BAO rieng: squeeze_frac cao (>0.30) => rui ro squeeze lon du verdict PASS -> can Uni can nhac.
GATE = {"pnl_sl_med_min": 0.0, "pnl_sl_posfrac_min": 0.60, "squeeze_warn": 0.30}
# ==============================================================================================

SMOKE = os.environ.get("SMOKE", "0") == "1"
DECILE = float(os.environ.get("DECILE", "0.10"))
MIN_XSEC = int(os.environ.get("MIN_XSEC", "10"))
FLAT_COST = float(os.environ.get("FLAT_COST", "0.0015"))
SL_SHORT = float(os.environ.get("SL_SHORT", "0.06"))   # SL cung cho short (doi xung nhan 6%)
HORIZONS = ["4h", "12h"]
H_STEPS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}
WIN = 0.06
GRID_MS = 15 * 60 * 1000
FEAT = [f"f{j}" for j in range(40)]
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
FIRST_OOS = os.environ.get("FIRST_OOS", "202201")
LAST = os.environ.get("LAST", "202607")
OOS_MONTHS = 3
SEED = 42
OUT = "/kaggle/working/short_probe.json"


def find1(pat):
    m = sorted(glob.glob(pat, recursive=True))
    assert m, f"KHONG TIM THAY: {pat}"
    return m[0]


def read_features():
    files = sorted(glob.glob("/kaggle/input/**/features_*.bin", recursive=True))
    assert files, "khong thay features_*.bin"
    parts = []
    for fp in files:
        raw = open(fp, "rb").read()
        if fp.endswith(".gz"):
            raw = gzip.decompress(raw)
        assert len(raw) % 170 == 0, f"{fp}: len {len(raw)} khong chia het 170"
        a = np.frombuffer(raw, dtype=TOOL1_DT)
        a = a[(a["ts"] % GRID_MS) == 0]
        parts.append(a)
    a = np.concatenate(parts)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    log.info("Features: %d rows | %d symId", len(df), df.symId.nunique())
    return df


def read_map():
    mp = pd.read_csv(find1("/kaggle/input/**/symid_map.csv"))
    cols = {c.lower(): c for c in mp.columns}
    mp = mp.rename(columns={cols.get("symid", mp.columns[0]): "symId",
                            cols.get("symbol", mp.columns[1]): "symbol"})
    return mp[["symId", "symbol"]]


def read_labels():
    path = find1("/kaggle/input/**/funding_label.csv")
    need = ["maxFav", "maxAdv", "nBars", "retEnd"]
    cols = ["tEpochMs", "symbol"] + [f"{k}_{h}" for h in HORIZONS for k in need]
    df = pd.read_csv(path, usecols=lambda c: c in cols, on_bad_lines="skip")
    df = df.rename(columns={"tEpochMs": "ts"})
    df["ts"] = df["ts"].astype(np.int64)
    for h in HORIZONS:
        ok = (df[f"nBars_{h}"] >= H_STEPS[h]) & df[f"maxFav_{h}"].notna()
        df[f"y_{h}"] = np.where(ok, (df[f"maxFav_{h}"] >= WIN).astype(np.float32), np.nan)
    keep = ["ts", "symbol"] + [f"y_{h}" for h in HORIZONS] \
        + [f"{k}_{h}" for h in HORIZONS for k in ("maxFav", "maxAdv", "retEnd")]
    log.info("Labels: %d rows", len(df))
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


def _select_bottom(sub, h):
    """Chon BOTTOM-decile theo pwin per-ts + cooldown H bar/symbol (event-level, non-overlapping)."""
    h_ms = H_STEPS[h] * GRID_MS
    last_sel = {}
    picked = []
    for ts, g in sub.groupby("ts", sort=True):
        if len(g) < MIN_XSEC:
            continue
        k = max(1, int(np.ceil(len(g) * DECILE)))
        gg = g.sort_values("pwin", ascending=True).head(k)   # THAP nhat
        for idx, sym, t in zip(gg.index, gg["symId"].values, gg["ts"].values):
            prev = last_sel.get(int(sym))
            if prev is not None and t < prev + h_ms:
                continue
            last_sel[int(sym)] = int(t)
            picked.append(idx)
    return np.array(picked, dtype=np.int64)


def eval_short_fold(sub, h):
    """sub: [ts, symId, pwin, y, maxFav, maxAdv, retEnd]. Metric SHORT bottom-decile mot fold."""
    idx = _select_bottom(sub, h)
    if len(idx) < 20:
        return None
    ev = sub.loc[idx]
    ts = ev["ts"].values
    retEnd = ev["retEnd"].values.astype(float)
    maxFav = ev["maxFav"].values.astype(float)      # short MAE (lun sau)
    maxAdv = ev["maxAdv"].values.astype(float)       # short MFE = -maxAdv
    bench_ret = sub.groupby("ts")["retEnd"].mean().to_dict()
    bench = np.array([bench_ret.get(int(t), np.nan) for t in ts])

    short_ret_end = -retEnd
    short_excess = -(retEnd - bench)
    # SL-sim THO: bi stop -SL neu maxFav >= SL_SHORT, nguoc lai giu toi endpoint (-retEnd)
    stopped = maxFav >= SL_SHORT
    short_pnl_sl = np.where(stopped, -SL_SHORT, -retEnd) - FLAT_COST
    squeeze_frac = float(np.mean(maxFav >= WIN))

    return {"n_event": int(len(idx)),
            "short_ret_end_med": round(float(np.nanmedian(short_ret_end)), 5),
            "short_excess_med": round(float(np.nanmedian(short_excess)), 5),
            "short_pnl_sl_med": round(float(np.nanmedian(short_pnl_sl)), 5),
            "short_pnl_sl_mean": round(float(np.nanmean(short_pnl_sl)), 5),
            "short_MAE_med": round(float(np.nanmedian(maxFav)), 5),
            "short_MFE_med": round(float(np.nanmedian(-maxAdv)), 5),
            "squeeze_frac": round(squeeze_frac, 4),
            "stop_frac": round(float(np.mean(stopped)), 4),
            "winrate_short": round(float(np.mean(short_ret_end > 0)), 4)}


def summarize(r):
    pnl = [x["short_pnl_sl_med"] for x in r]
    pnl_med = float(np.median(pnl)); pnl_pf = float(np.mean([p > 0 for p in pnl]))
    sq_med = float(np.median([x["squeeze_frac"] for x in r]))
    viable = pnl_med > GATE["pnl_sl_med_min"] and pnl_pf >= GATE["pnl_sl_posfrac_min"]
    verdict = "SHORT_VIABLE" if viable else "SHORT_NOT_VIABLE"
    warn = "SQUEEZE_RISK_HIGH" if sq_med > GATE["squeeze_warn"] else "ok"
    return {"n_fold": len(r),
            "short_pnl_sl_med_pct": round(pnl_med*100, 4), "short_pnl_sl_posfrac": round(pnl_pf, 3),
            "short_excess_med_pct": round(float(np.median([x["short_excess_med"] for x in r]))*100, 4),
            "short_ret_end_med_pct": round(float(np.median([x["short_ret_end_med"] for x in r]))*100, 4),
            "squeeze_frac_med": round(sq_med, 4),
            "stop_frac_med": round(float(np.median([x["stop_frac"] for x in r])), 4),
            "short_MAE_med_pct": round(float(np.median([x["short_MAE_med"] for x in r]))*100, 4),
            "winrate_short_med": round(float(np.median([x["winrate_short"] for x in r])), 4),
            "VERDICT": verdict, "WARN": warn}


def run():
    feat = read_features()
    mp = read_map()
    lab = read_labels()
    feat = feat.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    ds = feat.merge(lab, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("MERGED: %d rows | %d symbol | SL_SHORT=%.3f FLAT_COST=%.4f", len(ds), ds.symbol.nunique(),
             SL_SHORT, FLAT_COST)
    if len(ds) < 10000:
        raise SystemExit("MERGE qua it -> nghi lech pha ts feature vs label. DUNG.")

    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[len(folds)//2: len(folds)//2 + 1]
    results = {h: [] for h in HORIZONS}
    for fi, (cut, oos_end) in enumerate(folds):
        oos = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(oos) < 500:
            continue
        for h in HORIZONS:
            yc = f"y_{h}"
            purge = H_STEPS[h] * GRID_MS
            tr = ds[(ds.ts < cut - purge) & ds[yc].notna()]
            te = oos[oos[yc].notna()]
            if len(tr) < 5000 or len(te) < 200 or tr[yc].sum() < 50:
                log.warning("fold %d %s thieu data", fi, h)
                continue
            pos = tr[yc].mean()
            clf = xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                    scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                    eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=SEED)
            clf.fit(tr[FEAT], tr[yc])
            pwin = clf.predict_proba(te[FEAT])[:, 1]
            sub = pd.DataFrame({"ts": te["ts"].values, "symId": te["symId"].values, "pwin": pwin,
                                "y": te[yc].values, "maxFav": te[f"maxFav_{h}"].values,
                                "maxAdv": te[f"maxAdv_{h}"].values, "retEnd": te[f"retEnd_{h}"].values})
            ev = eval_short_fold(sub, h)
            if ev:
                ev.update({"fold": fi, "oos_from": str(pd.to_datetime(cut, unit="ms").date())})
                results[h].append(ev)
                log.info("fold %d %s [%s] SHORT pnl_sl=%.4f%% excess=%.4f%% retEnd=%.4f%% "
                         "MAE=%.4f%% squeeze=%.3f stop=%.3f wr=%.3f nEv=%d",
                         fi, h, ev["oos_from"], ev["short_pnl_sl_med"]*100, ev["short_excess_med"]*100,
                         ev["short_ret_end_med"]*100, ev["short_MAE_med"]*100, ev["squeeze_frac"],
                         ev["stop_frac"], ev["winrate_short"], ev["n_event"])

    summary = {}
    for h in HORIZONS:
        r = results[h]
        summary[h] = summarize(r) if r else {"n_fold": 0}
        if r:
            s = summary[h]
            log.info("=== SHORT %s VERDICT=%s WARN=%s | pnl_sl med=%.4f%% posfrac=%.2f | excess=%.4f%% | "
                     "squeeze med=%.3f | MAE med=%.4f%% | wr=%.3f | nfold=%d",
                     h, s["VERDICT"], s["WARN"], s["short_pnl_sl_med_pct"], s["short_pnl_sl_posfrac"],
                     s["short_excess_med_pct"], s["squeeze_frac_med"], s["short_MAE_med_pct"],
                     s["winrate_short_med"], s["n_fold"])

    out = {"smoke": SMOKE, "decile": DECILE, "min_xsec": MIN_XSEC, "flat_cost": FLAT_COST,
           "sl_short": SL_SHORT, "universe": "unfiltered", "feat": "f0..f39 (no OI)", "gate": GATE,
           "note": "SHORT bottom-decile pwin. Verdict tren short_pnl_sl (SL-sim tho + flat cost). "
                   "endpoint tran KHONG dung ket luan. Funding short (dao dau) CHUA model. "
                   "SL-sim proxy maxFav (khong biet truoc/sau retEnd) -> xem CAVEAT trong docstring.",
           "summary": summary, "per_fold": results}
    json.dump(out, open(OUT, "w"), indent=2)
    log.info("XONG -> %s", OUT)
    print("SHORT_PROBE_SUMMARY_JSON=" + json.dumps(summary))


if __name__ == "__main__":
    run()
