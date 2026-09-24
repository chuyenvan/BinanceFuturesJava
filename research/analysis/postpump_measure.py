"""PREREG_POSTPUMP_MEASURE (commit f8ebac7): do tin hieu "post-pump" tren TOAN BO lenh T170.

MO TA (descriptive) — KHONG chay sim, KHONG sua .java, KHONG push.
Thuc hien DUNG theo docs/prereg/PREREG_POSTPUMP_MEASURE.md:
  - Nhom: SUP = profit <= -20 (n=49), DOI_CHUNG = con lai (n=1040).
  - Feature chinh mom30d (causal, 30d return cua chinh coin tai entry).
  - Feature phu: vol30d, drawdown30d, symbolPred, tuoi niem yet.
  - Kiem dinh (a) so sanh mom30d + bootstrap block-72h x1.21; (b) decile momentum;
    (c) theo nam; (d) bang danh doi what-if (KHONG re-run).
  - Tieu chi ket luan chot truoc: DANG THEO neu (a) CI hieu mean mom30d khong chua 0
    VA (b) ti le SUP don dieu tang theo bucket. Neu khong => NULL + DUNG.
"""
import json
import logging
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT_DIR, exist_ok=True)
LOGFILE = os.path.join(OUT_DIR, "postpump_measure.log")
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler(LOGFILE, "w"), logging.StreamHandler()])
L = logging.getLogger("postpump")

TZ = "Asia/Ho_Chi_Minh"
H_MS = 3600 * 1000
DAY_MS = 24 * H_MS
LOOKBACK_MS = 30 * DAY_MS

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


def close_and_max(sid, t_lo, t_hi):
    """Tra ve (close tai t_hi, max close trong [t_lo, t_hi], closes trong window)."""
    a = SIDX.get(sid)
    if a is None:
        return np.nan, np.nan, np.array([])
    ts, c = a
    lo = int(np.searchsorted(ts, t_lo, side="left"))
    hi = int(np.searchsorted(ts, t_hi, side="right"))
    seg = c[lo:hi]
    if len(seg) == 0:
        return np.nan, np.nan, np.array([])
    return seg[-1], seg.max(), seg


def compute_features(row):
    sid = int(row["symId"])
    t = int(row["ts_ms"])
    c_entry = close_at(sid, t)
    c_30 = close_at(sid, t - LOOKBACK_MS)
    mom = (c_entry / c_30 - 1.0) * 100.0 if (np.isfinite(c_30) and c_30 > 0) else np.nan

    ce, mx, seg = close_and_max(sid, t - LOOKBACK_MS, t)
    dd = (ce / mx - 1.0) * 100.0 if (np.isfinite(mx) and mx > 0) else np.nan
    if len(seg) >= 3:
        rets = seg[1:] / seg[:-1] - 1.0
        vol = float(np.std(rets)) * 100.0
    else:
        vol = np.nan

    ft = FIRST_TS.get(sid)
    age = (t - ft) / DAY_MS if ft is not None else np.nan
    return mom, vol, dd, age


moms, vols, dds, ages = [], [], [], []
for _, r in d.iterrows():
    mom, vol, dd, age = compute_features(r)
    moms.append(mom)
    vols.append(vol)
    dds.append(dd)
    ages.append(age)

d["mom30d"] = moms
d["vol30d"] = vols
d["drawdown30d"] = dds
d["age_days"] = ages

n_nan_mom = int(d["mom30d"].isna().sum())
L.info("n_NAN mom30d=%d (coin niem yet < 30d truoc entry)", n_nan_mom)

# ---------------- (a) so sanh mom30d ----------------
sup = d[d["sup"] == 1]
dc = d[d["sup"] == 0]
v_sup = d.loc[d["sup"] == 1, "mom30d"].dropna().values
v_dc = d.loc[d["sup"] == 0, "mom30d"].dropna().values

res = {
    "n_total": n_total, "n_sup": n_sup, "n_doi_chung": n_total - n_sup,
    "n_nan_mom": n_nan_mom,
}

res["a"] = {
    "sup_mean": float(np.mean(v_sup)), "sup_median": float(np.median(v_sup)),
    "sup_n": int(len(v_sup)),
    "dc_mean": float(np.mean(v_dc)), "dc_median": float(np.median(v_dc)),
    "dc_n": int(len(v_dc)),
    "diff_mean": float(np.mean(v_sup) - np.mean(v_dc)),
    "diff_median": float(np.median(v_sup) - np.median(v_dc)),
}
L.info("(a) mom30d: SUP mean=%.2f med=%.2f (n=%d) | DC mean=%.2f med=%.2f (n=%d) | diff mean=%.2f med=%.2f",
       res["a"]["sup_mean"], res["a"]["sup_median"], len(v_sup),
       res["a"]["dc_mean"], res["a"]["dc_median"], len(v_dc),
       res["a"]["diff_mean"], res["a"]["diff_median"])

# block bootstrap for MEAN diff (primary)
valid = d[d["mom30d"].notna()].copy().reset_index(drop=True)
t0 = int(valid["ts_ms"].min())
valid["blk"] = ((valid["ts_ms"] - t0) // (BLOCK_H * H_MS)).astype(int)
blk_list = np.sort(valid["blk"].unique())
blk_to_idx = {b: np.array(g.index) for b, g in valid.groupby("blk")}
mom_arr = valid["mom30d"].values
sup_arr = valid["sup"].values

rng = np.random.default_rng(SEED)
diffs = np.full(NREP, np.nan)
for r in range(NREP):
    pick = rng.integers(0, len(blk_list), size=len(blk_list))
    idx = np.concatenate([blk_to_idx[blk_list[p]] for p in pick])
    m = mom_arr[idx]
    s = sup_arr[idx]
    a = m[s == 1]
    b = m[s == 0]
    if len(a) > 0 and len(b) > 0:
        diffs[r] = a.mean() - b.mean()

diffs = diffs[np.isfinite(diffs)]
lo, hi = np.percentile(diffs, [2.5, 97.5])
c = (lo + hi) / 2.0
lo_i = c - (c - lo) * CI_INFLATE
hi_i = c + (hi - c) * CI_INFLATE
res["a"]["ci95_mean_raw"] = [float(lo), float(hi)]
res["a"]["ci95_mean_inflated"] = [float(lo_i), float(hi_i)]
res["a"]["bootstrap_sd"] = float(np.std(diffs, ddof=1))
res["a"]["n_rep_valid"] = int(len(diffs))
res["a"]["excludes_zero"] = bool(lo_i * hi_i > 0)
L.info("(a) bootstrap mean diff: CI raw [%.2f, %.2f] -> inflated x%.2f [%.2f, %.2f] | excludes0=%s | sd=%.3f n_rep=%d",
       lo, hi, CI_INFLATE, lo_i, hi_i, res["a"]["excludes_zero"], res["a"]["bootstrap_sd"], len(diffs))

# ---------------- (b) decile momentum ----------------
valid = d[d["mom30d"].notna()].copy().reset_index(drop=True)
valid["decile"] = pd.qcut(valid["mom30d"].rank(method="first"), 10, labels=False).astype(int)
dec_rows = []
for k in range(10):
    g = valid[valid["decile"] == k]
    nsup = int(g["sup"].sum())
    dec_rows.append({
        "decile": k + 1,
        "mom_lo": float(g["mom30d"].min()), "mom_hi": float(g["mom30d"].max()),
        "n": int(len(g)), "n_sup": nsup,
        "sup_rate_pct": 100.0 * nsup / len(g) if len(g) else np.nan,
        "mean_pnl_usdt": float(g["pnl"].mean()) if len(g) else np.nan,
        "mean_profit_pct": float(g["profit"].mean()) if len(g) else np.nan,
        "total_pnl_usdt": float(g["pnl"].sum()) if len(g) else np.nan,
    })
dec = pd.DataFrame(dec_rows)
rho = spearmanr(dec["decile"].values, dec["sup_rate_pct"].values).correlation
monotone = bool((rho >= 0.7) and (dec.loc[dec.decile == 10, "sup_rate_pct"].iloc[0]
                                  > dec.loc[dec.decile == 1, "sup_rate_pct"].iloc[0]))
res["b"] = {"spearman_rho": float(rho), "monotone": monotone,
            "d10_sup_rate": float(dec.loc[dec.decile == 10, "sup_rate_pct"].iloc[0]),
            "d1_sup_rate": float(dec.loc[dec.decile == 1, "sup_rate_pct"].iloc[0])}
res["b"]["deciles"] = dec_rows
L.info("(b) decile momentum: Spearman rho=%.3f (nguong >=0.7), D1=%.1f%% D10=%.1f%% => monotone=%s",
       rho, res["b"]["d1_sup_rate"], res["b"]["d10_sup_rate"], monotone)
for _, row in dec.iterrows():
    L.info("  decile %2d  mom[%6.1f,%6.1f]  n=%4d  nSUP=%2d  sup%%=%5.1f  meanPnL=%+8.1f  totPnL=%+9.1f",
           row["decile"], row["mom_lo"], row["mom_hi"], row["n"], row["n_sup"],
           row["sup_rate_pct"], row["mean_pnl_usdt"], row["total_pnl_usdt"])

# ---------------- (c) theo nam ----------------
valid["year"] = valid["ts"].dt.year
year_rows = []
for y, g in valid.groupby("year"):
    gs = g[g["sup"] == 1]
    gd = g[g["sup"] == 0]
    year_rows.append({
        "year": int(y), "n": int(len(g)), "n_sup": int(g["sup"].sum()),
        "sup_rate_pct": 100.0 * g["sup"].mean(),
        "mean_mom_sup": float(gs["mom30d"].mean()) if len(gs) else np.nan,
        "mean_mom_dc": float(gd["mom30d"].mean()) if len(gd) else np.nan,
    })
res["c"] = year_rows
L.info("(c) theo nam:")
for row in year_rows:
    L.info("  %d: n=%d nSUP=%d sup%%=%.1f mean_mom SUP=%.1f DC=%.1f",
           row["year"], row["n"], row["n_sup"], row["sup_rate_pct"],
           row["mean_mom_sup"], row["mean_mom_dc"])

# ---------------- (d) danh doi what-if ----------------
mom_valid = valid["mom30d"].values
thresholds = {}
for q in ("p75", "p90", "p95"):
    thresholds[q] = float(np.percentile(mom_valid, int(q[1:])))
tradeoff = []
for q, thr in thresholds.items():
    rm = valid[valid["mom30d"] > thr]
    rm_sup = rm[rm["sup"] == 1]
    rm_win = rm[rm["pnl"] > 0]
    rm_other = rm[(rm["profit"] < 0) & (rm["profit"] > -20)]
    usd_lo_tranh = float(-rm_sup["pnl"].sum())
    usd_lai_mat = float(rm_win["pnl"].sum())
    net = float(-rm["pnl"].sum())
    tradeoff.append({
        "threshold": q, "thr_value": thr,
        "n_removed": int(len(rm)),
        "n_sup_removed": int(len(rm_sup)), "usd_lo_tranh": usd_lo_tranh,
        "n_win_removed": int(len(rm_win)), "usd_lai_mat": usd_lai_mat,
        "n_otherloss_removed": int(len(rm_other)),
        "pnl_rong_thay_doi": net,
    })
res["d"] = tradeoff
res["d_thresholds"] = thresholds
L.info("(d) danh doi what-if (KHONG re-run):")
for row in tradeoff:
    L.info("  %s (mom>%.2f): removed=%d SUP=%d(lo tranh %+.0f USD) win=%d(lai mat %+.0f USD) otherloss=%d => PnL rong %+.0f USD",
           row["threshold"], row["thr_value"], row["n_removed"],
           row["n_sup_removed"], row["usd_lo_tranh"],
           row["n_win_removed"], row["usd_lai_mat"],
           row["n_otherloss_removed"], row["pnl_rong_thay_doi"])

# ---------------- feature phu (descriptive) ----------------
def desc(col):
    vs = d.loc[d["sup"] == 1, col].dropna()
    vd = d.loc[d["sup"] == 0, col].dropna()
    return {"sup_mean": float(vs.mean()), "sup_median": float(vs.median()), "sup_n": int(len(vs)),
            "dc_mean": float(vd.mean()), "dc_median": float(vd.median()), "dc_n": int(len(vd))}

res["secondary"] = {c: desc(c) for c in ("vol30d", "drawdown30d", "symbolPred", "age_days")}
L.info("feature phu (SUP vs DC, mean/median):")
for c, v in res["secondary"].items():
    L.info("  %-12s SUP mean=%.3f med=%.3f | DC mean=%.3f med=%.3f",
           c, v["sup_mean"], v["sup_median"], v["dc_mean"], v["dc_median"])

# ---------------- ket luan ----------------
excl0 = res["a"]["excludes_zero"]
concl = "DANG_THEO" if (excl0 and monotone) else "NULL"
res["conclusion"] = concl
res["criteria"] = {"a_excludes_zero": excl0, "b_monotone": monotone}
L.info("\nKET LUAN: (a) CI hieu mean mom30d excludes0=%s | (b) monotone=%s => %s",
       excl0, monotone, concl)

# ---------------- write outputs ----------------
json_path = os.path.join(OUT_DIR, "postpump_measure.json")
with open(json_path, "w") as fh:
    json.dump(res, fh, indent=2, default=float)

dec.to_csv(os.path.join(OUT_DIR, "postpump_measure_deciles.csv"), index=False)
pd.DataFrame(tradeoff).to_csv(os.path.join(OUT_DIR, "postpump_measure_tradeoff.csv"), index=False)
pd.DataFrame(year_rows).to_csv(os.path.join(OUT_DIR, "postpump_measure_yearly.csv"), index=False)

L.info("\nDONE_POSTPUMP  json=%s", json_path)
