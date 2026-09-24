"""PREREG_PUMPDUMP_DETECT (commit f22bae0): do 4 detector pump->dump (close-based) tren TOAN BO lenh T170.

MO TA (descriptive) — KHONG chay sim, KHONG sua .java, KHONG push.
Dung DUNG theo docs/prereg/PREREG_PUMPDUMP_DETECT.md:
  - Nhom: SUP = profit <= -20 (n=49), DOI_CHUNG = con lai (n=1040).
  - 6 feature close-based (4 detector): ret_24h, ret_72h (D1); ext_ma7, ext_ma30 (D2);
    ddmag_72h (D3); accel_24h (D4).
  - Moi feature bao cao (a) decile SUP rate + Spearman + monotone; (b) mean diff SUP-DC + bootstrap
    block-72h x1.21 (2000 rep, seed 20260905); (c) danh doi what-if p75/p90/p95 (KHONG re-run);
    (d) so NaN.
  - Tieu chi DANG_THEO (chot truoc): (a) monotone VA (b) CI hieu mean khong chua 0 VA
    (c) PnL rong >= 0 o it nhat 1 nguong. Khong dat => NULL + DUNG.
"""
import json
import logging
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
LOGFILE = os.path.join(OUT_DIR, "pumpdump_detect.log")
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler(LOGFILE, "w"), logging.StreamHandler()])
L = logging.getLogger("pumpdump")

TZ = "Asia/Ho_Chi_Minh"
H_MS = 3600 * 1000
DAY_MS = 24 * H_MS

CSV = "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv"
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
MAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"

SEED = 20260905
NREP = 2000
CI_INFLATE = 1.21
BLOCK_H = 72

# ---------------- load trades ----------------
d = pd.read_csv(CSV)
d = d.loc[:, ~d.columns.str.startswith("Unnamed")].copy()
for c in ("profit", "pnl", "margin", "entry", "symbolPred"):
    d[c] = pd.to_numeric(d[c], errors="coerce")
d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M").dt.tz_localize(TZ)
d["ts_ms"] = d["ts"].astype("int64") // 10**6

mp = pd.read_csv(MAP)
s2id = dict(zip(mp.symbol, mp.symId))
d["symId"] = (d["sym"] + "USDT").map(s2id).astype(float)
assert d["symId"].notna().all(), "co symbol khong map duoc"
d["symId"] = d["symId"].astype(int)

d["sup"] = (d["profit"] <= -20).astype(int)
d["win"] = (d["pnl"] > 0).astype(int)
n_total = len(d)
n_sup = int(d["sup"].sum())
L.info("n_total=%d  n_SUP=%d  n_DOI_CHUNG=%d", n_total, n_sup, n_total - n_sup)

# ---------------- load CLOSES_1H, per-sym sorted ----------------
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
C = np.fromfile(CLOSES, dtype=DT)
cts = C["ts"].astype(np.int64)
csym = C["sym"].astype(np.int64)
cc = C["c"].astype(np.float64)
o = np.lexsort((cts, csym))
cts, csym, cc = cts[o], csym[o], cc[o]
uniq, start = np.unique(csym, return_index=True)
end = np.append(start[1:], len(csym))
SIDX = {int(s): (cts[a:b], cc[a:b]) for s, a, b in zip(uniq, start, end)}
FIRST_TS = {int(s): int(cts[a]) for s, a in zip(uniq, start)}
L.info("CLOSES_1H loaded: %d records, %d symbols", len(C), len(uniq))


def close_at(sid, t_ms):
    a = SIDX.get(sid)
    if a is None:
        return np.nan
    ts, c = a
    i = int(np.searchsorted(ts, t_ms, side="right")) - 1
    return c[i] if i >= 0 else np.nan


def closes_before(sid, t_ms, k):
    """Return the last k closes (as array, oldest->newest) at or before t_ms."""
    a = SIDX.get(sid)
    if a is None:
        return np.array([])
    ts, c = a
    hi = int(np.searchsorted(ts, t_ms, side="right"))
    lo = max(0, hi - k)
    return c[lo:hi]


def close_and_max(sid, t_lo, t_hi):
    a = SIDX.get(sid)
    if a is None:
        return np.nan, np.nan
    ts, c = a
    lo = int(np.searchsorted(ts, t_lo, side="left"))
    hi = int(np.searchsorted(ts, t_hi, side="right"))
    seg = c[lo:hi]
    if len(seg) == 0:
        return np.nan, np.nan
    return seg[-1], seg.max()


def feat_for(row):
    sid = int(row["symId"])
    t = int(row["ts_ms"])
    ce = close_at(sid, t)

    c24 = close_at(sid, t - 24 * H_MS)
    ret24 = (ce / c24 - 1.0) * 100.0 if (np.isfinite(c24) and c24 > 0 and np.isfinite(ce) and ce > 0) else np.nan

    c72 = close_at(sid, t - 72 * H_MS)
    ret72 = (ce / c72 - 1.0) * 100.0 if (np.isfinite(c72) and c72 > 0 and np.isfinite(ce) and ce > 0) else np.nan

    # MA_k = mean of last k hourly closes at t (need exactly k)
    seg7 = closes_before(sid, t, 7)
    ma7 = float(np.mean(seg7)) if len(seg7) == 7 else np.nan
    ext_ma7 = (ce / ma7 - 1.0) * 100.0 if (np.isfinite(ma7) and ma7 > 0 and np.isfinite(ce) and ce > 0) else np.nan

    seg30 = closes_before(sid, t, 30)
    ma30 = float(np.mean(seg30)) if len(seg30) == 30 else np.nan
    ext_ma30 = (ce / ma30 - 1.0) * 100.0 if (np.isfinite(ma30) and ma30 > 0 and np.isfinite(ce) and ce > 0) else np.nan

    _, mx72 = close_and_max(sid, t - 72 * H_MS, t)
    ddmag72 = (1.0 - ce / mx72) * 100.0 if (np.isfinite(mx72) and mx72 > 0 and np.isfinite(ce) and ce > 0) else np.nan

    c48 = close_at(sid, t - 48 * H_MS)
    if (np.isfinite(c24) and c24 > 0 and np.isfinite(c48) and c48 > 0 and np.isfinite(ce) and ce > 0):
        accel = ((ce / c24 - 1.0) - (c24 / c48 - 1.0)) * 100.0
    else:
        accel = np.nan

    return dict(ret_24h=ret24, ret_72h=ret72, ext_ma7=ext_ma7, ext_ma30=ext_ma30,
                ddmag_72h=ddmag72, accel_24h=accel)


FEATURES = ["ret_24h", "ret_72h", "ext_ma7", "ext_ma30", "ddmag_72h", "accel_24h"]

feats = {f: [] for f in FEATURES}
for _, r in d.iterrows():
    fv = feat_for(r)
    for f in FEATURES:
        feats[f].append(fv[f])
for f in FEATURES:
    d[f] = feats[f]

res = {"n_total": n_total, "n_sup": n_sup, "n_doi_chung": n_total - n_sup}
res["features"] = {}

# ---------------- per-feature: (a) decile, (b) CI, (c) tradeoff, (d) NaN ----------------
for f in FEATURES:
    L.info("\n===== FEATURE %s =====", f)
    n_nan = int(d[f].isna().sum())
    L.info("(d) NaN/khong do duoc = %d / %d (%.1f%%)", n_nan, n_total, 100.0 * n_nan / n_total)
    feat_res = {"n_nan": n_nan}

    valid = d[d[f].notna()].copy().reset_index(drop=True)
    n_valid = len(valid)

    # (a) decile
    valid["decile"] = pd.qcut(valid[f].rank(method="first"), 10, labels=False).astype(int)
    dec_rows = []
    for k in range(10):
        g = valid[valid["decile"] == k]
        nsup = int(g["sup"].sum())
        dec_rows.append({
            "decile": k + 1,
            "feat_lo": float(g[f].min()), "feat_hi": float(g[f].max()),
            "n": int(len(g)), "n_sup": nsup,
            "sup_rate_pct": 100.0 * nsup / len(g) if len(g) else np.nan,
            "mean_pnl_usdt": float(g["pnl"].mean()) if len(g) else np.nan,
            "total_pnl_usdt": float(g["pnl"].sum()) if len(g) else np.nan,
        })
    dec = pd.DataFrame(dec_rows)
    rho = spearmanr(dec["decile"].values, dec["sup_rate_pct"].values).correlation
    d10 = dec.loc[dec.decile == 10, "sup_rate_pct"].iloc[0]
    d1 = dec.loc[dec.decile == 1, "sup_rate_pct"].iloc[0]
    monotone = bool((rho >= 0.7) and (d10 > d1))
    feat_res["a"] = {"spearman_rho": float(rho), "monotone": monotone,
                     "d10_sup_rate": float(d10), "d1_sup_rate": float(d1), "deciles": dec_rows}
    L.info("(a) decile: rho=%.3f (nguong >=0.7) D1=%.1f%% D10=%.1f%% => monotone=%s",
           rho, d1, d10, monotone)

    # (b) mean diff + bootstrap block-72h
    v_sup = valid.loc[valid["sup"] == 1, f].values
    v_dc = valid.loc[valid["sup"] == 0, f].values
    diff_mean = float(np.mean(v_sup) - np.mean(v_dc)) if (len(v_sup) and len(v_dc)) else np.nan
    feat_res["b"] = {"sup_mean": float(np.mean(v_sup)) if len(v_sup) else np.nan,
                     "sup_median": float(np.median(v_sup)) if len(v_sup) else np.nan,
                     "sup_n": int(len(v_sup)),
                     "dc_mean": float(np.mean(v_dc)) if len(v_dc) else np.nan,
                     "dc_median": float(np.median(v_dc)) if len(v_dc) else np.nan,
                     "dc_n": int(len(v_dc)),
                     "diff_mean": diff_mean}

    t0 = int(valid["ts_ms"].min())
    valid["blk"] = ((valid["ts_ms"] - t0) // (BLOCK_H * H_MS)).astype(int)
    blk_list = np.sort(valid["blk"].unique())
    blk_to_idx = {b: np.array(g.index) for b, g in valid.groupby("blk")}
    feat_arr = valid[f].values
    sup_arr = valid["sup"].values

    rng = np.random.default_rng(SEED)
    diffs = np.full(NREP, np.nan)
    for rep in range(NREP):
        pick = rng.integers(0, len(blk_list), size=len(blk_list))
        idx = np.concatenate([blk_to_idx[blk_list[p]] for p in pick])
        m = feat_arr[idx]; s = sup_arr[idx]
        a = m[s == 1]; b = m[s == 0]
        if len(a) > 0 and len(b) > 0:
            diffs[rep] = a.mean() - b.mean()
    diffs = diffs[np.isfinite(diffs)]
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    ctr = (lo + hi) / 2.0
    lo_i = ctr - (ctr - lo) * CI_INFLATE
    hi_i = ctr + (hi - ctr) * CI_INFLATE
    excludes0 = bool(lo_i * hi_i > 0)
    feat_res["b"]["ci95_mean_raw"] = [float(lo), float(hi)]
    feat_res["b"]["ci95_mean_inflated"] = [float(lo_i), float(hi_i)]
    feat_res["b"]["bootstrap_sd"] = float(np.std(diffs, ddof=1))
    feat_res["b"]["n_rep_valid"] = int(len(diffs))
    feat_res["b"]["excludes_zero"] = excludes0
    L.info("(b) mean diff=%.3f | SUP mean=%.2f med=%.2f (n=%d) | DC mean=%.2f med=%.2f (n=%d) | CI infl [%.3f, %.3f] excl0=%s sd=%.3f",
           diff_mean, np.mean(v_sup), np.median(v_sup), len(v_sup),
           np.mean(v_dc), np.median(v_dc), len(v_dc), lo_i, hi_i, excludes0, feat_res["b"]["bootstrap_sd"])

    # (c) tradeoff what-if
    feat_valid = valid[f].values
    tradeoff = []
    any_net_ge0 = False
    for q in ("p75", "p90", "p95"):
        thr = float(np.percentile(feat_valid, int(q[1:])))
        rm = valid[valid[f] > thr]
        rm_sup = rm[rm["sup"] == 1]
        rm_win = rm[rm["pnl"] > 0]
        rm_other = rm[(rm["profit"] < 0) & (rm["profit"] > -20)]
        usd_lo_tranh = float(-rm_sup["pnl"].sum())
        usd_lai_mat = float(rm_win["pnl"].sum())
        net = float(-rm["pnl"].sum())
        if net >= 0:
            any_net_ge0 = True
        tradeoff.append({
            "threshold": q, "thr_value": thr, "n_removed": int(len(rm)),
            "n_sup_removed": int(len(rm_sup)), "usd_lo_tranh": usd_lo_tranh,
            "n_win_removed": int(len(rm_win)), "usd_lai_mat": usd_lai_mat,
            "n_otherloss_removed": int(len(rm_other)), "pnl_rong_thay_doi": net,
        })
    feat_res["c"] = tradeoff
    feat_res["c_any_net_ge0"] = bool(any_net_ge0)
    L.info("(c) danh doi what-if (KHONG re-run), any net>=0 = %s:", any_net_ge0)
    for row in tradeoff:
        L.info("  %s (feat>%.3f): removed=%d SUP=%d(lo tranh %+.0f) win=%d(lai mat %+.0f) other=%d => PnL rong %+.0f",
               row["threshold"], row["thr_value"], row["n_removed"], row["n_sup_removed"],
               row["usd_lo_tranh"], row["n_win_removed"], row["usd_lai_mat"],
               row["n_otherloss_removed"], row["pnl_rong_thay_doi"])

    # conclusion per pre-registered criteria
    concl = "DANG_THEO" if (monotone and excludes0 and any_net_ge0) else "NULL"
    feat_res["conclusion"] = concl
    feat_res["criteria"] = {"a_monotone": monotone, "b_excludes_zero": excludes0,
                            "c_any_net_ge0": any_net_ge0}
    L.info("=> KET LUAN %s: monotone=%s excl0=%s net_ge0=%s => %s",
           f, monotone, excludes0, any_net_ge0, concl)

    res["features"][f] = feat_res

# ---------------- write outputs ----------------
json_path = os.path.join(OUT_DIR, "pumpdump_detect.json")
with open(json_path, "w") as fh:
    json.dump(res, fh, indent=2, default=float)
L.info("\nDONE_PUMPDUMP  json=%s", json_path)
