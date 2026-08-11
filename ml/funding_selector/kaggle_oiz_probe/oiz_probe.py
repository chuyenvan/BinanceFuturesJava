#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OI-Z GATE PROBE (Kaggle) — screen nhanh: oi_z veto/soft co cai thien chat luong va TON frequency bao nhieu?

Day la SCREEN cross-sectional tren Kaggle (endpoint alpha + so event), KHONG phai verdict production.
Verdict that (exit machine + martingale + funding) van can Java WFO. Muc dich: xem oi_z co dang dua vao
gate khong, va dang nao (hard veto vs soft weight) truoc khi ton compute Oracle.

Modes (ap TRUOC khi chon top-decile, tren candidate cross-section moi ts):
  - off          : khong loc.
  - veto_q50/q75 : giu coin co oiZ <= quantile Q cua ts do (low OI = it crowded). Q=0.5/0.75.
  - soft_weight  : khong loc; weight event = (1 - oiZ_rank_in_ts) khi tong hop alpha (down-weight OI cao).

Cham JOINT: alpha (endpoint retEnd, dedup event) × frequency (n_event). Filter cai thien alpha nhung bop
frequency duoi san = FAIL (frequency wall). Pre-register san frequency.

oiZ nguon: oi_percoin_full.bin record 30B = (>i8 ts, >i2 symId, 5x>f4[oiDelta24h, oiZ, lsGlobal, lsToptrader, takerBuy]).
symId cua OI theo symbol_map.csv RIENG cua dataset OI -> bridge sang feature qua SYMBOL.
"""
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("oiz_probe")

# ===== PRE-REGISTER (Uni chot) =====
# oi_z DANG dua vao gate neu: 1 mode co alpha_med > off VA n_event_med >= FREQ_FLOOR (san frequency) VA posfrac>=0.6.
FREQ_FLOOR = int(os.environ.get("FREQ_FLOOR", "300"))   # min event/fold (dedup) de coi la con song frequency
GATE = {"posfrac_min": 0.60}
# ===================================

SMOKE = os.environ.get("SMOKE", "0") == "1"
DECILE = float(os.environ.get("DECILE", "0.10"))
MIN_XSEC = int(os.environ.get("MIN_XSEC", "10"))
KEEP_Q = {"veto_q50": 0.50, "veto_q75": 0.75}
MODES = ["off", "veto_q50", "veto_q75", "soft_weight"]
HORIZONS = ["4h", "12h"]
H_STEPS = {"4h": 16, "12h": 48}
WIN = 0.06
GRID_MS = 15 * 60 * 1000
FEAT = [f"f{j}" for j in range(40)]
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])   # itemsize 30
FIRST_OOS = os.environ.get("FIRST_OOS", "202201")
LAST = os.environ.get("LAST", "202607")
OOS_MONTHS = 3
SEED = 42
OUT = "/kaggle/working/oiz_probe.json"


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
        assert len(raw) % 170 == 0
        a = np.frombuffer(raw, dtype=TOOL1_DT)
        parts.append(a[(a["ts"] % GRID_MS) == 0])
    a = np.concatenate(parts)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    log.info("Features: %d rows", len(df))
    return df


def read_map(name):
    mp = pd.read_csv(find1(f"/kaggle/input/**/{name}"))
    cols = {c.lower(): c for c in mp.columns}
    mp = mp.rename(columns={cols.get("symid", mp.columns[0]): "symId",
                            cols.get("symbol", mp.columns[1]): "symbol"})
    return mp[["symId", "symbol"]]


def read_labels():
    path = find1("/kaggle/input/**/funding_label.csv")
    numc = [f"{k}_{h}" for h in HORIZONS for k in ("maxFav", "nBars", "retEnd")]
    cols = ["tEpochMs", "symbol"] + numc
    dtype = {c: np.float32 for c in numc}; dtype["symbol"] = "category"
    df = pd.read_csv(path, usecols=lambda c: c in cols, dtype=dtype, on_bad_lines="skip")
    df = df.rename(columns={"tEpochMs": "ts"}); df["ts"] = df["ts"].astype(np.int64)
    for h in HORIZONS:
        ok = (df[f"nBars_{h}"] >= H_STEPS[h]) & df[f"maxFav_{h}"].notna()
        df[f"y_{h}"] = np.where(ok, (df[f"maxFav_{h}"] >= WIN), np.nan).astype(np.float32)
    keep = ["ts", "symbol"] + [f"y_{h}" for h in HORIZONS] + [f"retEnd_{h}" for h in HORIZONS]
    log.info("Labels: %d rows", len(df))
    return df[keep]


def read_oiz():
    """Doc oi_percoin_full.bin -> DataFrame (symbol, ts, oiZ). Bridge symId->symbol qua symbol_map.csv cua OI."""
    fp = find1("/kaggle/input/**/oi_percoin_full.bin")
    raw = open(fp, "rb").read()
    if len(raw) % 30 != 0:
        raw = gzip.decompress(raw)
    assert len(raw) % 30 == 0, f"oi bin len {len(raw)} khong chia het 30"
    a = np.frombuffer(raw, dtype=OI_DT)
    a = a[(a["ts"] % GRID_MS) == 0]
    oiZ = np.asarray(a["oi"], dtype=np.float32)[:, 1]      # float #1 = oiZ
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "oiSym": a["sym"].astype(np.int32), "oiZ": oiZ})
    df = df[np.isfinite(df["oiZ"])]
    oimap = read_map("symbol_map.csv")
    id2sym = dict(zip(oimap["symId"].astype(np.int32), oimap["symbol"].astype(str)))
    df["symbol"] = df["oiSym"].map(id2sym)
    df = df.drop(columns=["oiSym"]).dropna(subset=["symbol"])
    log.info("OI-z: %d rows (finite) | %d symbol", len(df), df["symbol"].nunique())
    return df[["symbol", "ts", "oiZ"]]


def build_folds():
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01"); last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6))); cur = nxt
    return folds


def select_events(sub, h, mode):
    """Ap gate mode -> chon top-decile per-ts -> cooldown H bar. Tra ve (idx, weights)."""
    h_ms = H_STEPS[h] * GRID_MS
    last_sel = {}; picked = []; weights = []
    for ts, g in sub.groupby("ts", sort=True):
        gg = g
        if mode in KEEP_Q:
            if gg["oiZ"].notna().sum() < MIN_XSEC:
                continue
            thr = gg["oiZ"].quantile(KEEP_Q[mode])
            gg = gg[gg["oiZ"] <= thr]
        if len(gg) < MIN_XSEC:
            continue
        k = max(1, int(np.ceil(len(gg) * DECILE)))
        top = gg.sort_values("pwin", ascending=False).head(k)
        if mode == "soft_weight":
            # weight = 1 - rank_oiZ trong ts (oiZ cao -> weight thap). NaN oiZ -> weight 1 (khong phat).
            oz = top["oiZ"]
            r = oz.rank(pct=True)
            w = (1.0 - r).fillna(1.0).values
        else:
            w = np.ones(len(top))
        for idx, sym, t, wi in zip(top.index, top["symId"].values, top["ts"].values, w):
            prev = last_sel.get(int(sym))
            if prev is not None and t < prev + h_ms:
                continue
            last_sel[int(sym)] = int(t); picked.append(idx); weights.append(wi)
    return np.array(picked, dtype=np.int64), np.array(weights, dtype=float)


def wmean(x, w):
    x = np.asarray(x, float); w = np.asarray(w, float)
    m = np.isfinite(x) & np.isfinite(w)
    return float(np.sum(x[m] * w[m]) / np.sum(w[m])) if np.sum(w[m]) > 0 else float("nan")


def run():
    import gc, xgboost as xgb
    feat = read_features(); fmap = read_map("symid_map.csv"); lab = read_labels(); oi = read_oiz()
    f2 = dict(zip(fmap["symbol"].astype(str), fmap["symId"].astype(np.int32)))
    lab["symId"] = lab["symbol"].map(f2)
    oi["symId"] = oi["symbol"].map(f2)
    lab = lab.drop(columns=["symbol"]).dropna(subset=["symId"]); lab["symId"] = lab["symId"].astype(np.int32)
    oi = oi.drop(columns=["symbol"]).dropna(subset=["symId"]); oi["symId"] = oi["symId"].astype(np.int32)
    ds = feat.merge(lab, on=["symId", "ts"], how="inner")
    ds = ds.merge(oi, on=["symId", "ts"], how="left").sort_values("ts").reset_index(drop=True)  # oiZ NaN neu thieu
    del feat, lab, oi; gc.collect()
    log.info("MERGED: %d rows | oiZ non-null %.1f%%", len(ds), 100*ds["oiZ"].notna().mean())
    if len(ds) < 10000:
        raise SystemExit("MERGE qua it. DUNG.")

    folds = build_folds()
    if SMOKE:
        folds = folds[len(folds)//2: len(folds)//2 + 1]
    res = {m: {h: [] for h in HORIZONS} for m in MODES}
    for fi, (cut, oe) in enumerate(folds):
        oos = ds[(ds.ts >= cut) & (ds.ts < oe)]
        if len(oos) < 500:
            continue
        for h in HORIZONS:
            yc = f"y_{h}"; rc = f"retEnd_{h}"; purge = H_STEPS[h] * GRID_MS
            tr = ds[(ds.ts < cut - purge) & ds[yc].notna()]
            te = oos[oos[yc].notna()]
            if len(tr) < 5000 or len(te) < 200 or tr[yc].sum() < 50:
                continue
            pos = tr[yc].mean()
            clf = xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8,
                                    colsample_bytree=0.8, min_child_weight=20,
                                    scale_pos_weight=(1 - pos) / max(pos, 1e-6), eval_metric="auc",
                                    n_jobs=-1, tree_method="hist", random_state=SEED)
            clf.fit(tr[FEAT], tr[yc])
            te = te.copy(); te["pwin"] = clf.predict_proba(te[FEAT])[:, 1]
            bench = te.groupby("ts")[rc].mean().to_dict()
            sub = te[["ts", "symId", "pwin", "oiZ", rc]].rename(columns={rc: "ret"})
            for m in MODES:
                idx, w = select_events(sub[["ts", "symId", "pwin", "oiZ"]].assign(ret=sub["ret"]), h, m)
                if len(idx) < 20:
                    continue
                ev = sub.loc[idx]
                b = np.array([bench.get(int(t), np.nan) for t in ev["ts"].values])
                alpha_vec = ev["ret"].values - b
                alpha = wmean(alpha_vec, w) if m == "soft_weight" else float(np.nanmean(alpha_vec))
                res[m][h].append({"fold": fi, "alpha": round(alpha, 6), "n_event": int(len(idx)),
                                  "winrate": round(float(np.nanmean(ev["ret"].values > 0)), 4)})
        log.info("fold %d done", fi)

    summary = {}
    for m in MODES:
        summary[m] = {}
        for h in HORIZONS:
            r = res[m][h]
            if not r:
                summary[m][h] = {"n_fold": 0}; continue
            al = [x["alpha"] for x in r]; nev = [x["n_event"] for x in r]
            al_med = float(np.median(al)); al_pf = float(np.mean([a > 0 for a in al]))
            nev_med = int(np.median(nev))
            alive = nev_med >= FREQ_FLOOR
            summary[m][h] = {"n_fold": len(r), "alpha_med_pct": round(al_med*100, 4),
                             "alpha_posfrac": round(al_pf, 3), "n_event_med": nev_med,
                             "winrate_med": round(float(np.median([x["winrate"] for x in r])), 4),
                             "freq_alive": bool(alive)}
    for h in HORIZONS:
        for m in MODES:
            s = summary[m].get(h, {})
            if s.get("n_fold"):
                log.info("=== [%s] %s | alpha med=%.4f%% posfrac=%.2f | nEv med=%d freq_alive=%s | wr=%.3f",
                         m, h, s["alpha_med_pct"], s["alpha_posfrac"], s["n_event_med"], s["freq_alive"],
                         s["winrate_med"])
    out = {"smoke": SMOKE, "modes": MODES, "keep_q": KEEP_Q, "freq_floor": FREQ_FLOOR, "decile": DECILE,
           "note": "SCREEN Kaggle: alpha ENDPOINT dedup, chua cost/funding. Cham JOINT alpha x frequency. "
                   "Verdict production that = Java WFO. So off vs veto vs soft: veto tang alpha nhung tut nEv "
                   "(frequency wall); soft giu nEv. Chon mode co alpha>off MA freq_alive.",
           "summary": summary}
    json.dump(out, open(OUT, "w"), indent=2)
    log.info("XONG -> %s", OUT)
    print("OIZ_PROBE_SUMMARY_JSON=" + json.dumps(summary))


if __name__ == "__main__":
    run()
