"""A1 perp discount — cham T1..T4 theo PREREG_VZ_A1_PERP_DISCOUNT (c4de0684). Python logging, khong print.
Usage: a1_test.py <a1_feat.csv> <out.json> [seed_tag]
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("a1t")
FEAT, OUT = sys.argv[1], sys.argv[2]
TAG = sys.argv[3] if len(sys.argv) > 3 else "a1"
PD = os.path.expanduser(f"~/kaggle_sim/out/gqsf-{TAG}/storage/printDone.csv")
NREP, SEED, BLOCK = 2000, 20261016, 5

d = pd.read_csv(PD, index_col=False)
d = d[d.level != "DCA_LEVEL1"].copy()
d["t0"] = (pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)).astype("int64") // 10**6
d["n"] = d.groupby("t0").sym.transform("size")
d["year"] = pd.to_datetime(d.t0, unit="ms").dt.year
d = d[(d.n >= 6) & d.year.isin([2022, 2024])].copy()
d["ret"] = d.pnl / d.margin
F = pd.read_csv(FEAT)
m = d.merge(F[["sym", "t0", "F1", "F2", "v2", "v3_corr", "max_ts_used", "lag-2", "lag-1", "lag0", "lag1", "lag2"]], on=["sym", "t0"], how="left")
log.info("[%s] chan %d, dot %d; merge feature %d", TAG, len(m), m.t0.nunique(), m.F1.notna().sum() + 0)

# ---- kiem du lieu
chk = {}
chk["V1_causal"] = bool((m.max_ts_used.dropna() <= m.t0[m.max_ts_used.notna()]).all())
chk["V2_price_frac"] = float(m.v2.mean())
chk["V3_corr_med_info"] = float(m.v3_corr.median())
lags = {k: float(F[k].median()) for k in ["lag-2", "lag-1", "lag0", "lag1", "lag2"]}
chk["V3_lags"] = lags
chk["V3_lag_ok"] = bool(lags["lag0"] == max(lags.values()) and lags["lag0"] > 0.3)
chk["V4_cov_both"] = float((m.F1.notna() & m.F2.notna()).mean())
chk["pass"] = chk["V1_causal"] and chk["V2_price_frac"] >= 0.95 and chk["V3_lag_ok"] and chk["V4_cov_both"] >= 0.90
miss = m[m.F1.isna() | m.F2.isna()].sym.value_counts().head(15).to_dict()
log.info("kiem: %s ; thieu feature theo sym: %s", chk, miss)
if not chk["pass"]:
    log.error("KIEM DU LIEU FAIL -> KHONG tinh outcome")
    json.dump({"check": chk, "missing": miss}, open(OUT, "w"), indent=1)
    sys.exit(2)

# ---- dot
m["day"] = pd.to_datetime(m.t0, unit="ms").dt.floor("D")
B = m.groupby("t0").agg(pnl=("pnl", "sum"), margin=("margin", "sum"), F1=("F1", "median"), F2=("F2", "median"),
                        day=("day", "first"), year=("year", "first"), n=("sym", "size")).reset_index()
B["ret"] = B.pnl / B.margin


def ic_burst(Bs, f):
    s = Bs[[f, "ret"]].dropna()
    return spearmanr(s[f], s.ret).correlation if len(s) >= 8 else np.nan


def ic_within(ms, f):
    v = []
    for _, g in ms.groupby("t0"):
        g = g[[f, "ret"]].dropna()
        if len(g) >= 6 and g[f].nunique() > 1:
            v.append(spearmanr(g[f], g.ret).correlation)
    return float(np.nanmean(v)) if v else np.nan, len(v)


days = np.array(sorted(B.day.unique()))
rng = np.random.default_rng(SEED)


def boot(stat_fn):
    nb = int(np.ceil(len(days) / BLOCK)); out = []
    for _ in range(NREP):
        starts = rng.integers(0, len(days), nb)
        pick = np.concatenate([days[(s + np.arange(BLOCK)) % len(days)] for s in starts])[:len(days)]
        idx = pd.Series(pick).value_counts()
        out.append(stat_fn(idx))
    return np.array(out)


def resample_frame(df, idx):
    parts = [df[df.day == dday].assign(_rep=k) for dday, cnt in idx.items() for k in range(cnt)]
    return pd.concat(parts, ignore_index=True)


res = {"check": chk, "tag": TAG, "n_legs": int(len(m)), "n_bursts": int(len(B))}
tests = [("T1", "burst", "F1"), ("T2", "burst", "F2"), ("T3", "within", "F1"), ("T4", "within", "F2")]
for name, kind, f in tests:
    if kind == "burst":
        est = ic_burst(B, f)
        def fn(idx, f=f):
            r = resample_frame(B, idx); return ic_burst(r, f)
        by_year = {int(y): ic_burst(B[B.year == y], f) for y in (2022, 2024)}
        med = B[f].median()
        spread = float(B[B[f] <= med].ret.mean() - B[B[f] > med].ret.mean())
        nunit = int(B[f].notna().sum())
    else:
        est, nunit = ic_within(m, f)
        def fn(idx, f=f):
            r = resample_frame(m, idx)
            r["t0"] = r.t0.astype(str) + "_" + r._rep.astype(str)
            return ic_within(r, f)[0]
        by_year = {int(y): ic_within(m[m.year == y], f)[0] for y in (2022, 2024)}
        sp = []
        for _, g in m.groupby("t0"):
            g = g[[f, "ret"]].dropna()
            if len(g) >= 6:
                mm = g[f].median(); sp.append(g[g[f] <= mm].ret.mean() - g[g[f] > mm].ret.mean())
        spread = float(np.nanmean(sp))
    bs = boot(fn)
    ci95 = np.nanquantile(bs, [0.025, 0.975]).tolist()
    cib = np.nanquantile(bs, [0.00625, 0.99375]).tolist()
    cand = bool(cib[1] < 0 and all(v < 0 for v in by_year.values()))
    weak = bool(ci95[1] < 0)
    res[name] = {"feat": f, "kind": kind, "est": float(est), "ci95": ci95, "ci_bonf": cib, "by_year": by_year,
                 "spread_low_minus_high": spread, "n_unit": nunit, "candidate": cand, "weak": weak}
    log.info("%s %s %-6s IC %+.3f CI95 [%+.3f;%+.3f] Bonf [%+.3f;%+.3f] nam %s spread(thap-cao) %+.4f n %d -> %s",
             name, f, kind, est, *ci95, *cib, {k: round(v, 3) for k, v in by_year.items()}, spread, nunit,
             "UNG VIEN" if cand else ("yeu" if weak else "-"))
w = B.nsmallest(10, "ret")
B["rk1"] = B.F1.rank(pct=True); B["rk2"] = B.F2.rank(pct=True)
res["worst10"] = B.loc[w.index, ["t0", "n", "ret", "F1", "F2", "rk1", "rk2"]].assign(
    t=lambda x: pd.to_datetime(x.t0, unit="ms").astype(str)).drop(columns="t0").round(5).to_dict("records")
log.info("10 dot te nhat:\n%s", pd.DataFrame(res["worst10"]).to_string(index=False))
json.dump(res, open(OUT, "w"), indent=1, default=float)
log.info("ghi %s", OUT)
