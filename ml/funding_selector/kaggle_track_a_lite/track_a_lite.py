#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRACK A-lite — proxy first-touch net-EV: cu bom (maxFav) co monetize duoc bang exit thuc + cost khong?

Thay endpoint co dinh (retEnd) bang EXIT first-touch tu cot barrier co san:
  maxFav_H, maxAdv_H, tHitFav_H (phut), tHitAdv_H (phut), retEnd_H, nBars_H  (ExportFundingLabel).
Chi mo phong lop FIRST-TOUCH (TP/SL/time) — KHONG phai trailing (trailing can path 1m = Track A).

Chuoi:
  1) train selector (giong reprobe) -> pwin.
  2) top-decile per-ts + cooldown H (event-level, khong overlap).
  3) moi event: first-touch voi T = dung horizon h (tranh van de extreme-sau-T):
       hit_fav = maxFav>=TP & tHitFav<=T ; hit_adv = maxAdv<=-SL & tHitAdv<=T
       ca hai -> tHit nho hon thang truoc ; chi fav -> +TP ; chi adv -> -SL ; khong -> retEnd
     gross -> net = gross - FLAT_COST.  (FUNDING CHUA tru: dataset khong co funding -> flag; can merge funding_data.)
  4) verdict per policy tren net-EV OOS + posfrac quy.  P0 endpoint = sanity (phai ~ reprobe alpha ~0).

CAVEAT: maxFav/maxAdv la extreme ca cua so (khong path-ordered); tHit cho biet thoi diem cham extreme
  nhung SL-first-touch van xap xi (khong biet duong di truoc do co cham TP/SL khac). Path dung 100% = Track A (1m).
"""
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("track_a_lite")

# ===== PRE-REGISTER (Uni chot truoc khi nhin so) =====
# GO neu >=1 policy co net_EV_med > 0 VA posfrac quy >= 0.60 VA reproduce duoc P0~reprobe (sanity).
GATE = {"netEV_med_min": 0.0, "posfrac_min": 0.60}
# =====================================================

SMOKE = os.environ.get("SMOKE", "0") == "1"
DECILE = float(os.environ.get("DECILE", "0.10"))
MIN_XSEC = int(os.environ.get("MIN_XSEC", "10"))
FLAT_COST = float(os.environ.get("FLAT_COST", "0.0015"))   # fee+slip round-trip crude (funding CHUA co)
HORIZONS = ["4h", "12h"]
H_STEPS = {"4h": 16, "12h": 48}
H_MIN = {"4h": 4*60, "12h": 12*60}       # horizon tinh bang phut (khop don vi tHit)
# Grid TP/SL (T = dung horizon). Pre-register.
TP_GRID = [0.04, 0.06]
SL_GRID = [0.02, 0.03, 0.04]
WIN = 0.06
GRID_MS = 15 * 60 * 1000
FEAT = [f"f{j}" for j in range(40)]
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
FIRST_OOS = os.environ.get("FIRST_OOS", "202201")
LAST = os.environ.get("LAST", "202607")
OOS_MONTHS = 3
SEED = 42
OUT = "/kaggle/working/track_a_lite.json"


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
    need = ["maxFav", "maxAdv", "tHitFav", "tHitAdv", "retEnd", "nBars"]
    numc = [f"{k}_{h}" for h in HORIZONS for k in need]
    cols = ["tEpochMs", "symbol"] + numc
    dtype = {c: np.float32 for c in numc}          # float32 giam ~1/2 RAM
    dtype["symbol"] = "category"                     # tranh 47M chuoi object
    df = pd.read_csv(path, usecols=lambda c: c in cols, dtype=dtype, on_bad_lines="skip")
    df = df.rename(columns={"tEpochMs": "ts"})
    df["ts"] = df["ts"].astype(np.int64)
    for h in HORIZONS:
        ok = (df[f"nBars_{h}"] >= H_STEPS[h]) & df[f"maxFav_{h}"].notna()
        df[f"y_{h}"] = np.where(ok, (df[f"maxFav_{h}"] >= WIN), np.nan).astype(np.float32)
    keep = ["ts", "symbol"] + [f"y_{h}" for h in HORIZONS] + numc
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


def _select_top(sub, h):
    """top-decile per-ts + cooldown H bar/symbol (event-level, non-overlapping)."""
    h_ms = H_STEPS[h] * GRID_MS
    last_sel = {}
    picked = []
    for ts, g in sub.groupby("ts", sort=True):
        if len(g) < MIN_XSEC:
            continue
        k = max(1, int(np.ceil(len(g) * DECILE)))
        gg = g.sort_values("pwin", ascending=False).head(k)
        for idx, sym, t in zip(gg.index, gg["symId"].values, gg["ts"].values):
            prev = last_sel.get(int(sym))
            if prev is not None and t < prev + h_ms:
                continue
            last_sel[int(sym)] = int(t)
            picked.append(idx)
    return np.array(picked, dtype=np.int64)


def first_touch_gross(maxFav, maxAdv, tHitFav, tHitAdv, retEnd, T_min, TP, SL):
    """Vectorized first-touch gross return. T = horizon (phut). retEnd la fallback (khong barrier nao cham)."""
    hit_fav = (maxFav >= TP) & (tHitFav <= T_min)
    hit_adv = (maxAdv <= -SL) & (tHitAdv <= T_min)
    both = hit_fav & hit_adv
    fav_first = tHitFav < tHitAdv
    gross = np.where(np.isnan(retEnd), 0.0, retEnd)           # fallback endpoint
    gross = np.where(hit_adv & ~hit_fav, -SL, gross)
    gross = np.where(hit_fav & ~hit_adv, TP, gross)
    gross = np.where(both, np.where(fav_first, TP, -SL), gross)
    reason = np.where(both, np.where(fav_first, "tp", "sl"),
              np.where(hit_fav, "tp", np.where(hit_adv, "sl", "end")))
    return gross.astype(float), reason


def eval_policies(ev, h):
    """ev: DataFrame events (1 fold). Tra ve list metric per policy."""
    T_min = H_MIN[h]
    mF = ev[f"maxFav_{h}"].values.astype(float)
    mA = ev[f"maxAdv_{h}"].values.astype(float)
    tF = ev[f"tHitFav_{h}"].values.astype(float)
    tA = ev[f"tHitAdv_{h}"].values.astype(float)
    rE = ev[f"retEnd_{h}"].values.astype(float)
    out = []
    # P0 endpoint (sanity)
    net0 = np.where(np.isnan(rE), np.nan, rE) - FLAT_COST
    out.append({"policy": "P0_endpoint", "net_ev": round(float(np.nanmedian(net0)), 5),
                "winrate": round(float(np.nanmean(net0 > 0)), 4), "tp_frac": None, "sl_frac": None,
                "n": int(np.sum(~np.isnan(net0)))})
    # first-touch grid
    for TP in TP_GRID:
        for SL in SL_GRID:
            gross, reason = first_touch_gross(mF, mA, tF, tA, rE, T_min, TP, SL)
            net = gross - FLAT_COST
            out.append({"policy": f"TP{int(TP*100)}_SL{int(SL*100)}_T{h}",
                        "net_ev": round(float(np.median(net)), 5),
                        "net_ev_mean": round(float(np.mean(net)), 5),
                        "winrate": round(float(np.mean(net > 0)), 4),
                        "tp_frac": round(float(np.mean(reason == "tp")), 4),
                        "sl_frac": round(float(np.mean(reason == "sl")), 4),
                        "end_frac": round(float(np.mean(reason == "end")), 4),
                        "n": int(len(net))})
    return out


def run():
    import gc
    feat = read_features(); mp = read_map(); lab = read_labels()
    # merge tren symId (int) thay vi symbol (chuoi) -> nhe RAM. Map symbol->symId qua category .map (khong materialize chuoi).
    sym2id = dict(zip(mp["symbol"].astype(str), mp["symId"].astype(np.int32)))
    lab["symId"] = lab["symbol"].map(sym2id)
    lab = lab.drop(columns=["symbol"]).dropna(subset=["symId"])
    lab["symId"] = lab["symId"].astype(np.int32)
    ds = feat.merge(lab, on=["symId", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    del feat, lab; gc.collect()
    log.info("MERGED: %d rows | %d symId", len(ds), ds.symId.nunique())
    if len(ds) < 10000:
        raise SystemExit("MERGE qua it -> nghi lech pha ts. DUNG.")

    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[len(folds)//2: len(folds)//2 + 1]
    per_fold = {h: [] for h in HORIZONS}
    for fi, (cut, oos_end) in enumerate(folds):
        oos = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(oos) < 500:
            continue
        for h in HORIZONS:
            yc = f"y_{h}"; purge = H_STEPS[h] * GRID_MS
            tr = ds[(ds.ts < cut - purge) & ds[yc].notna()]
            te = oos[oos[yc].notna()]
            if len(tr) < 5000 or len(te) < 200 or tr[yc].sum() < 50:
                continue
            pos = tr[yc].mean()
            clf = xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                    scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                    eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=SEED)
            clf.fit(tr[FEAT], tr[yc])
            te = te.copy()
            te["pwin"] = clf.predict_proba(te[FEAT])[:, 1]
            idx = _select_top(te[["ts", "symId", "pwin"]], h)
            if len(idx) < 20:
                continue
            ev = te.loc[idx]
            res = eval_policies(ev, h)
            for r in res:
                r["fold"] = fi; r["oos_from"] = str(pd.to_datetime(cut, unit="ms").date()); r["n_event"] = len(idx)
            per_fold[h].append(res)
            p1 = next((x for x in res if x["policy"] == f"TP6_SL3_T{h}"), {})
            p0 = res[0]
            log.info("fold %d %s nEv=%d | P0_end net=%.4f%% | TP6_SL3 net=%.4f%% wr=%.3f tp=%.2f sl=%.2f",
                     fi, h, len(idx), p0["net_ev"]*100, p1.get("net_ev", float('nan'))*100,
                     p1.get("winrate", float('nan')), p1.get("tp_frac", 0), p1.get("sl_frac", 0))

    # summarize per (h, policy) across folds
    summary = {}
    for h in HORIZONS:
        if not per_fold[h]:
            summary[h] = {}; continue
        pols = [x["policy"] for x in per_fold[h][0]]
        summary[h] = {}
        for p in pols:
            series = [next(x for x in fold if x["policy"] == p) for fold in per_fold[h]]
            nev = [s["net_ev"] for s in series]
            netmed = float(np.median(nev)); posfrac = float(np.mean([v > 0 for v in nev]))
            go = netmed > GATE["netEV_med_min"] and posfrac >= GATE["posfrac_min"]
            summary[h][p] = {"net_ev_med_pct": round(netmed*100, 4), "posfrac": round(posfrac, 3),
                             "winrate_med": round(float(np.median([s["winrate"] for s in series])), 4),
                             "tp_frac_med": (round(float(np.median([s["tp_frac"] for s in series])), 4)
                                             if series[0]["tp_frac"] is not None else None),
                             "sl_frac_med": (round(float(np.median([s["sl_frac"] for s in series])), 4)
                                             if series[0].get("sl_frac") is not None else None),
                             "n_fold": len(series), "VERDICT": "GO" if go else "NO"}
    # log best policy per horizon
    for h in HORIZONS:
        if summary.get(h):
            best = max(summary[h].items(), key=lambda kv: kv[1]["net_ev_med_pct"])
            log.info("=== %s BEST policy=%s net_ev_med=%.4f%% posfrac=%.2f verdict=%s | P0_end=%.4f%%",
                     h, best[0], best[1]["net_ev_med_pct"], best[1]["posfrac"], best[1]["VERDICT"],
                     summary[h].get("P0_endpoint", {}).get("net_ev_med_pct", float('nan')))

    out = {"smoke": SMOKE, "decile": DECILE, "flat_cost": FLAT_COST, "tp_grid": TP_GRID, "sl_grid": SL_GRID,
           "gate": GATE, "universe": "unfiltered", "feat": "f0..f39 (no OI)",
           "note": "first-touch tu barrier col (T=horizon). tHit=phut. FUNDING CHUA tru (flag). "
                   "P0_endpoint = sanity ~ reprobe alpha. Trailing/path 1m = Track A (khong o day). "
                   "GO can >=1 policy net_ev_med>0 & posfrac>=0.6 & P0 reproduce reprobe.",
           "summary": summary}
    json.dump(out, open(OUT, "w"), indent=2)
    log.info("XONG -> %s", OUT)
    print("TRACK_A_LITE_SUMMARY_JSON=" + json.dumps(summary))


if __name__ == "__main__":
    run()
