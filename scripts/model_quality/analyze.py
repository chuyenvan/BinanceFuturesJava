#!/usr/bin/env python3
"""
TASK-128 — tong hop market_realized.csv + funding_realized.csv (do Task128ModelQuality sinh) ->
IC / decile-lift / hit-rate theo QUY. Thuan tieu thu CSV Java (khong sinh/bien doi feature).

Chay: python analyze.py <t128_out_dir>   (dir chua 2 CSV). In bang + ghi *_quarterly.csv.

Metric (khop DINH NGHIA PRE-REGISTERED docs/reports/model_quality_wfo_20260704.md):
- Market predReturn15M: Spearman IC vs real15 (de-overlap 15m); decile-lift +1/2/3/6%.
- Market predRisk4H  : Spearman IC vs realDD4H (de-overlap 4h). Ca hai am -> IC duong = dung chieu.
- Funding: rank-IC(pwin=1-score, maxFav24) + hit-rate SELECTED(score<=maxThres) vs REJECTED vs UNIVERSE
           (chi tick complete=1). maxThres default = 0.15*2.14135 = 0.3212 (GENE HPO — 1 operating point).
"""
import sys, os
import numpy as np
import pandas as pd

MAXTHRES = 0.15 * 2.14135   # PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX (Configs default)
GMT7_MS = 7 * 3600 * 1000

def quarter(ts_ms):
    d = pd.to_datetime(ts_ms + GMT7_MS, unit="ms")   # GMT+7
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"

def spearman(a, b):
    if len(a) < 10: return np.nan, 0
    ra = pd.Series(a).rank().values
    rb = pd.Series(b).rank().values
    if np.std(ra) == 0 or np.std(rb) == 0: return np.nan, len(a)
    return float(np.corrcoef(ra, rb)[0, 1]), len(a)

def deoverlap(df, horizon_ms):
    df = df.sort_values("ts")
    keep, last = [], -10**18
    for ts in df["ts"].values:
        if ts - last >= horizon_ms:
            keep.append(ts); last = ts
    return df[df["ts"].isin(set(keep))]

def market(path):
    df = pd.read_csv(path)
    df["q"] = df["ts"].map(quarter)
    print("\n==== MARKET (pred.bin = ai_pred_market_full_basket_v2, KHONG leak-free) ====")
    rows = []
    for q in sorted(df["q"].unique()) + ["ALL"]:
        d = df if q == "ALL" else df[df["q"] == q]
        d15 = deoverlap(d.dropna(subset=["pred15", "real15"]), 15 * 60000)
        ic15, n15 = spearman(d15["pred15"].values, d15["real15"].values)
        dR = deoverlap(d.dropna(subset=["predRisk4H", "realDD4H"]), 4 * 3600000)
        icR, nR = spearman(dR["predRisk4H"].values, dR["realDD4H"].values)
        # decile-lift +1/2/3/6% tren d15
        lifts = {}
        if n15 >= 50:
            v = d15.sort_values("pred15", ascending=False)
            topk = max(30, int(len(v) * 0.10))
            for thr in (0.01, 0.02, 0.03, 0.06):
                base = (d15["real15"] >= thr).mean()
                top = (v.head(topk)["real15"] >= thr).mean()
                lifts[thr] = round(top / base, 2) if base > 0 else np.nan
        rows.append([q, n15, round(ic15, 4), nR, round(icR, 4),
                     lifts.get(0.01), lifts.get(0.02), lifts.get(0.03), lifts.get(0.06)])
    m = pd.DataFrame(rows, columns=["quarter", "n15", "IC_ret15", "nDD", "IC_risk4H",
                                    "lift+1%", "lift+2%", "lift+3%", "lift+6%"])
    print(m.to_string(index=False))
    return m

def funding(path):
    df = pd.read_csv(path)
    df["q"] = df["ts"].map(quarter)
    c = df[df["complete"] == 1].copy()
    print(f"\n==== FUNDING (leak-free per-fold, score=1-P(win@24h); maxThres={MAXTHRES:.4f}) ====")
    print(f"  rows total={len(df)} complete(nBars>=96)={len(c)} ({100*len(c)/max(1,len(df)):.1f}%)")
    rows = []
    for q in sorted(c["q"].unique()) + ["ALL"]:
        d = c if q == "ALL" else c[c["q"] == q]
        if len(d) < 10:
            rows.append([q, len(d)] + [np.nan]*7); continue
        ic, n = spearman(d["pwin"].values, d["maxFav24"].values)   # pwin=1-score vs realized maxFav
        sel = d[d["score"] <= MAXTHRES]
        rej = d[d["score"] > MAXTHRES]
        hr_sel = sel["win"].mean() if len(sel) else np.nan
        hr_rej = rej["win"].mean() if len(rej) else np.nan
        hr_uni = d["win"].mean()
        mf_sel = sel["maxFav24"].mean() if len(sel) else np.nan
        mf_uni = d["maxFav24"].mean()
        rows.append([q, len(d), round(ic, 4), round(hr_sel, 4), round(hr_uni, 4),
                     round(hr_rej, 4), round(mf_sel, 4), round(mf_uni, 4), len(sel)])
    f = pd.DataFrame(rows, columns=["quarter", "n", "rankIC", "hit_SEL", "hit_UNI",
                                    "hit_REJ", "mf_SEL", "mf_UNI", "nSEL"])
    print(f.to_string(index=False))
    return f

def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "t128_out"
    mp = os.path.join(outdir, "market_realized.csv")
    fp = os.path.join(outdir, "funding_realized.csv")
    if os.path.exists(mp):
        market(mp).to_csv(os.path.join(outdir, "market_quarterly.csv"), index=False)
    if os.path.exists(fp):
        funding(fp).to_csv(os.path.join(outdir, "funding_quarterly.csv"), index=False)

if __name__ == "__main__":
    main()
