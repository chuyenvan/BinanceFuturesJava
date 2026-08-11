#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RE-PROBE selectability on UNFILTERED universe (walk-forward toan quy) — BAN SUA OVERLAP.

Sua so voi ban goc (chuyendinh/reprobe-unfiltered-wf):
  * LO HONG GOC: top-decile chon bang argsort tren TOAN BO (symbol,ts) gop ca quy, va
    rankIC = spearmanr pooled tren toan bo row. => 1 coin giu pwin cao nhieu bar 15m lien tiep
    bi dem toi H_STEPS lan (overlap), thoi phong ca alpha lan do-on-dinh IC.
  * SUA:
    1) SELECT per-timestamp cross-section + COOLDOWN H bar/symbol => non-overlapping EVENT.
    2) rankIC = mean over ts cua spearman(pwin_ts, y_ts) (xsec IC dung nghia factor);
       GIU pooled_ic de so apples-to-apples voi con so 18/18 cu.
    3) Them WORST-decile alpha + SPREAD (top - bottom) lam falsification (diagnostic).
    4) Report EFFECTIVE N: #event sau dedup + #cross-section doc lap ~ n_ts / H_steps.
    5) Them net-alpha CRUDE = alpha - FLAT_COST (endpoint, khong path) — chi de sanity, KHONG phai verdict.
    6) CHAY CA 2 MODE trong 1 lan: 'overlap' (tai lap ban cu) va 'dedup' (ban sua) tren CUNG model
       => do THANG muc thoi phong overlap (train xgboost 1 lan/fold, eval 2 cach).

CANH BAO DIEN GIAI: alpha o day van la ENDPOINT (retEnd_H), khong tru funding, khong exit policy.
Sua overlap KHONG lam alpha tu duong len — no chi tra loi "claim selectability bi thoi bao nhieu".
Monetization van la viec cua Track A-lite (first-touch + cost + funding).
"""
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reprobe")

# ============ PRE-REGISTER GATE (ghi truoc khi xem so) ============
# GIU NGUYEN nguong goc de so sanh. LUU Y: estimator IC doi tu pooled -> xsec-mean,
# nen truoc khi coi verdict la chinh thuc, Uni CAN re-affirm nguong tren estimator moi.
# Verdict chinh cham tren xsec IC + alpha mode 'dedup'.
GATE = {"ic_med_min": 0.02, "ic_posfrac_min": 0.70, "alpha_med_min": 0.0, "alpha_posfrac_min": 0.60}
# ==================================================================

SMOKE = os.environ.get("SMOKE", "0") == "1"      # full walk-forward (SMOKE=0)
DECILE = float(os.environ.get("DECILE", "0.10"))  # ty le top/bottom moi cross-section
MIN_XSEC = int(os.environ.get("MIN_XSEC", "10"))  # so coin toi thieu/ts de tinh xsec IC + select
FLAT_COST = float(os.environ.get("FLAT_COST", "0.0015"))  # ~fee+slip round-trip crude, chi de net-alpha sanity
MODES = ["overlap", "dedup"]                       # chay ca hai; verdict cham tren 'dedup'
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
OUT = "/kaggle/working/reprobe_unfiltered.json"


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
    log.info("Features: %d rows | %d symId | ts[%s..%s]", len(df), df.symId.nunique(),
             pd.to_datetime(df.ts.min(), unit="ms"), pd.to_datetime(df.ts.max(), unit="ms"))
    return df


def read_map():
    mp = pd.read_csv(find1("/kaggle/input/**/symid_map.csv"))
    cols = {c.lower(): c for c in mp.columns}
    mp = mp.rename(columns={cols.get("symid", mp.columns[0]): "symId",
                            cols.get("symbol", mp.columns[1]): "symbol"})
    return mp[["symId", "symbol"]]


def read_labels():
    path = find1("/kaggle/input/**/funding_label.csv")
    cols = ["tEpochMs", "symbol"] + [f"maxFav_{h}" for h in HORIZONS] \
        + [f"nBars_{h}" for h in HORIZONS] + [f"retEnd_{h}" for h in HORIZONS]
    df = pd.read_csv(path, usecols=lambda c: c in cols, on_bad_lines="skip")
    df = df.rename(columns={"tEpochMs": "ts"})
    df["ts"] = df["ts"].astype(np.int64)
    for h in HORIZONS:
        ok = (df[f"nBars_{h}"] >= H_STEPS[h]) & df[f"maxFav_{h}"].notna()
        df[f"y_{h}"] = np.where(ok, (df[f"maxFav_{h}"] >= WIN).astype(np.float32), np.nan)
    keep = ["ts", "symbol"] + [f"y_{h}" for h in HORIZONS] + [f"retEnd_{h}" for h in HORIZONS]
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


def _select_events(sub, h, side, dedup):
    """Chon top (side='top') / bottom (side='bot') decile PER-TIMESTAMP.
    dedup=True => cooldown H bar/symbol (non-overlapping event). dedup=False => tai lap ban cu (giu het)."""
    h_ms = H_STEPS[h] * GRID_MS
    last_sel = {}
    picked = []
    asc = (side == "bot")
    for ts, g in sub.groupby("ts", sort=True):
        if len(g) < MIN_XSEC:
            continue
        k = max(1, int(np.ceil(len(g) * DECILE)))
        gg = g.sort_values("pwin", ascending=asc).head(k)
        for idx, sym, t in zip(gg.index, gg["symId"].values, gg["ts"].values):
            if dedup:
                prev = last_sel.get(int(sym))
                if prev is not None and t < prev + h_ms:
                    continue
                last_sel[int(sym)] = int(t)
            picked.append(idx)
    return np.array(picked, dtype=np.int64)


def compute_ic(sub):
    """IC khong phu thuoc dedup (tren toan bo sub). Tra ve (pooled_ic, xsec_ic, n_ts)."""
    import scipy.stats as st
    pooled_ic, _ = st.spearmanr(sub["pwin"].values, sub["y"].values)
    xs = []
    for ts, g in sub.groupby("ts", sort=False):
        if len(g) < MIN_XSEC or g["y"].nunique() < 2:
            continue
        ic_ts, _ = st.spearmanr(g["pwin"].values, g["y"].values)
        if np.isfinite(ic_ts):
            xs.append(ic_ts)
    xsec_ic = float(np.mean(xs)) if xs else float("nan")
    return float(pooled_ic), xsec_ic, int(len(xs))


def eval_fold(sub, h, dedup, pooled_ic, xsec_ic, n_ts):
    """Metric mot fold cho mot mode dedup. IC truyen vao (dedup-independent)."""
    n_indep = max(1, n_ts // H_STEPS[h])
    base = float(sub["y"].mean())
    base_ret_by_ts = sub.groupby("ts")["ret"].mean().to_dict()
    top_idx = _select_events(sub, h, "top", dedup)
    bot_idx = _select_events(sub, h, "bot", dedup)
    if len(top_idx) < 20:
        return None
    top = sub.loc[top_idx]
    bot = sub.loc[bot_idx] if len(bot_idx) else None

    def _alpha(ev):
        r = ev["ret"].values.astype(float)
        bench = np.array([base_ret_by_ts.get(int(t), np.nan) for t in ev["ts"].values])
        return float(np.nanmean(r)), float(np.nanmean(bench)), float(np.nanmean(r - bench))

    top_ret, top_bench, top_alpha = _alpha(top)
    lift = float(top["y"].mean()) / base if base > 0 else float("nan")
    winrate = float((top["ret"] > 0).mean())
    net_alpha = top_alpha - FLAT_COST
    if bot is not None and len(bot):
        _, _, bot_alpha = _alpha(bot)
        spread = top_alpha - bot_alpha
    else:
        bot_alpha = float("nan"); spread = float("nan")

    return {"N": int(len(sub)), "base_rate": round(base, 4), "n_event_top": int(len(top_idx)),
            "n_event_bot": int(len(bot_idx)), "n_ts": n_ts, "n_indep": int(n_indep),
            "LIFT": round(lift, 3), "pooled_IC": round(pooled_ic, 4), "xsec_IC": round(xsec_ic, 4),
            "top_ret": round(top_ret, 5), "bench_ret": round(top_bench, 5), "alpha": round(top_alpha, 5),
            "net_alpha_crude": round(net_alpha, 5), "bot_alpha": round(bot_alpha, 5),
            "spread_top_bot": round(spread, 5), "winrate": round(winrate, 4)}


def summarize(r):
    ics = [x["xsec_IC"] for x in r]; als = [x["alpha"] for x in r]
    ic_med = float(np.nanmedian(ics)); ic_pf = float(np.mean([c > 0 for c in ics]))
    al_med = float(np.median(als)); al_pf = float(np.mean([a > 0 for a in als]))
    pass_sel = ic_med > GATE["ic_med_min"] and ic_pf >= GATE["ic_posfrac_min"]
    pass_al = al_med > GATE["alpha_med_min"] and al_pf >= GATE["alpha_posfrac_min"]
    verdict = "EDGE_REAL" if (pass_sel and pass_al) else ("WEAK" if (pass_sel or pass_al) else "NONE")
    return {"n_fold": len(r), "LIFT_med": round(float(np.median([x["LIFT"] for x in r])), 3),
            "xsecIC_med": round(ic_med, 4), "xsecIC_posfrac": round(ic_pf, 3),
            "pooledIC_med": round(float(np.nanmedian([x["pooled_IC"] for x in r])), 4),
            "alpha_med_pct": round(al_med*100, 4), "alpha_posfrac": round(al_pf, 3),
            "net_alpha_crude_med_pct": round(float(np.median([x["net_alpha_crude"] for x in r]))*100, 4),
            "spread_med_pct": round(float(np.nanmedian([x["spread_top_bot"] for x in r]))*100, 4),
            "winrate_med": round(float(np.median([x["winrate"] for x in r])), 4),
            "n_event_top_med": int(np.median([x["n_event_top"] for x in r])),
            "n_indep_med": int(np.median([x["n_indep"] for x in r])),
            "PASS_selectability": bool(pass_sel), "PASS_alpha": bool(pass_al), "VERDICT": verdict}


def run():
    feat = read_features()
    mp = read_map()
    lab = read_labels()
    feat = feat.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    ds = feat.merge(lab, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("MERGED: %d rows | %d symbol | DECILE=%.2f MIN_XSEC=%d", len(ds), ds.symbol.nunique(),
             DECILE, MIN_XSEC)
    if len(ds) < 10000:
        raise SystemExit("MERGE qua it -> nghi lech pha ts feature vs label. DUNG.")

    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[len(folds)//2: len(folds)//2 + 1]
        log.info("SMOKE: 1 fold %s", folds)
    results = {m: {h: [] for h in HORIZONS} for m in MODES}
    for fi, (cut, oos_end) in enumerate(folds):
        oos = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(oos) < 500:
            continue
        for h in HORIZONS:
            yc = f"y_{h}"; rc = f"retEnd_{h}"
            purge = H_STEPS[h] * GRID_MS
            tr = ds[(ds.ts < cut - purge) & ds[yc].notna()]
            te = oos[oos[yc].notna()]
            if len(tr) < 5000 or len(te) < 200 or tr[yc].sum() < 50:
                log.warning("fold %d %s thieu data tr=%d te=%d", fi, h, len(tr), len(te))
                continue
            pos = tr[yc].mean()
            clf = xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                    scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                    eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=SEED)
            clf.fit(tr[FEAT], tr[yc])
            pwin = clf.predict_proba(te[FEAT])[:, 1]
            sub = pd.DataFrame({"ts": te["ts"].values, "symId": te["symId"].values,
                                "pwin": pwin, "y": te[yc].values, "ret": te[rc].values}).dropna(subset=["y"])
            if len(sub) < 500 or sub["y"].sum() < 20:
                continue
            pooled_ic, xsec_ic, n_ts = compute_ic(sub)   # 1 lan, dung cho ca 2 mode
            for mode in MODES:
                ev = eval_fold(sub, h, mode == "dedup", pooled_ic, xsec_ic, n_ts)
                if ev:
                    ev.update({"fold": fi, "oos_from": str(pd.to_datetime(cut, unit="ms").date())})
                    results[mode][h].append(ev)
            d = results["dedup"][h][-1] if results["dedup"][h] else {}
            o = results["overlap"][h][-1] if results["overlap"][h] else {}
            log.info("fold %d %s [%s] xsecIC=%.4f pooledIC=%.4f nIndep=%d | "
                     "OVERLAP alpha=%.4f%% nEv=%d | DEDUP alpha=%.4f%% net=%.4f%% spread=%.4f%% wr=%.3f nEv=%d",
                     fi, h, str(pd.to_datetime(cut, unit="ms").date()),
                     d.get("xsec_IC", float('nan')), d.get("pooled_IC", float('nan')), d.get("n_indep", 0),
                     o.get("alpha", float('nan'))*100, o.get("n_event_top", 0),
                     d.get("alpha", float('nan'))*100, d.get("net_alpha_crude", float('nan'))*100,
                     d.get("spread_top_bot", float('nan'))*100, d.get("winrate", float('nan')),
                     d.get("n_event_top", 0))

    summary = {m: {} for m in MODES}
    for m in MODES:
        for h in HORIZONS:
            r = results[m][h]
            summary[m][h] = summarize(r) if r else {"n_fold": 0}
    for h in HORIZONS:
        for m in MODES:
            s = summary[m][h]
            if s.get("n_fold"):
                log.info("=== [%s] %s VERDICT=%s | xsecIC med=%.4f posfrac=%.2f (pooledIC med=%.4f) | "
                         "alpha med=%.4f%% posfrac=%.2f | net=%.4f%% | spread=%.4f%% | nEvTop med=%d nIndep med=%d | nfold=%d",
                         m, h, s["VERDICT"], s["xsecIC_med"], s["xsecIC_posfrac"], s["pooledIC_med"],
                         s["alpha_med_pct"], s["alpha_posfrac"], s["net_alpha_crude_med_pct"],
                         s["spread_med_pct"], s["n_event_top_med"], s["n_indep_med"], s["n_fold"])

    out = {"smoke": SMOKE, "modes": MODES, "decile": DECILE, "min_xsec": MIN_XSEC, "flat_cost": FLAT_COST,
           "universe": "unfiltered", "feat": "f0..f39 (no OI)", "first_oos": FIRST_OOS, "gate": GATE,
           "note": "alpha=ENDPOINT retEnd gross funding; net_alpha_crude tru flat cost, KHONG path. "
                   "Verdict chinh = mode 'dedup' tren xsec_IC+alpha. 'overlap'=tai lap ban cu de do muc thoi phong.",
           "summary": summary, "per_fold": results}
    json.dump(out, open(OUT, "w"), indent=2)
    log.info("XONG -> %s", OUT)
    print("REPROBE_SUMMARY_JSON=" + json.dumps(summary))


if __name__ == "__main__":
    run()
