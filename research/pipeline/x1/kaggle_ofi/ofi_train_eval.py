# OFI Stage B -- train candidate (KEEP9 + ofi_1h + aggr_buy_ratio_1h) and noise control
# (KEEP9 + noise_ofi_check), compare vs reused Kaggle-baseline (KEEP9 only, n_jobs=1,
# edge5=15.209468%), nested SELECT(fold0-9)/CONFIRM(fold10-17), block-bootstrap CI.
# Harness ported verbatim from research/analysis/s1_hpo_bag_featgrp.py (same formulas,
# same seeds/NREP/block size) per docs/PREREG_S1_FREE_OFI.md Sec 4. Self-contained Kaggle
# CPU kernel. dataset_sources=["chuyendinh/s1-featv2-x1-20260919"],
# kernel_sources=["chuyendinh/s1-baseline18-det-n1-20260919","chuyendinh/ofi-build-feat-15sym"].
import glob
import json
import os
import subprocess
import sys
import time

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "xgboost==3.2.0"], check=True)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xgboost as xgb  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

WORK = "/kaggle/working"
os.makedirs(WORK, exist_ok=True)

H = 3600000
TZ = 7 * H
PURGE = 72 * H
KEEP9 = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
         "ret_14d", "ls_global", "rk_oi_delta24h"]
CUTS18 = ("20210701 20211001 20220101 20220401 20220701 20221001 20230101 20230401 "
          "20230701 20231001 20240101 20240401 20240701 20241001 20250101 20250401 "
          "20250701 20251001").split()
SELECT_N = 10
CONFIRM_N = 8
BLOCK_H = 72
NREP = 2000
SEED = 20260919


def cuts_to_ms(cut_days):
    return [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in cut_days]


CUT_MS_18 = cuts_to_ms(CUTS18)


def find1(pattern):
    g = glob.glob(pattern, recursive=True)
    assert g, f"not found: {pattern}"
    return g[0]


LED_PATH = find1("/kaggle/input/**/cand_dev_x1_lite.parquet")
FEAT_PATH = find1("/kaggle/input/**/feat_v2_x1_keep9.parquet")
BASELINE_PATH = find1("/kaggle/input/**/pred_baseline18_n1_kaggle.parquet")
OFI_PATH = find1("/kaggle/input/**/ofi_feat_x1.parquet")
print("LED_PATH", LED_PATH, flush=True)
print("FEAT_PATH", FEAT_PATH, flush=True)
print("BASELINE_PATH", BASELINE_PATH, flush=True)
print("OFI_PATH", OFI_PATH, flush=True)

t0 = time.time()
D = pd.read_parquet(LED_PATH, columns=["ts", "sym", "g1lite"])
D = D[D.g1lite.notna()].copy()
print("pool", D.shape, flush=True)
D["med"] = D.groupby("ts").g1lite.transform("median")
D["rel"] = D.g1lite - D.med
D["rk"] = D.groupby("ts").rel.rank(pct=True, method="first")
D["rel5"] = np.minimum((D.rk * 5).astype(int), 4)
D["ts_h"] = (D.ts // H) * H

F = pd.read_parquet(FEAT_PATH, columns=["ts", "sym"] + KEEP9)
for c in KEEP9:
    if F[c].dtype == np.float64:
        F[c] = F[c].astype(np.float32)
D = D.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
del F
print("join KEEP9: co vol_7d", D.vol_7d.notna().mean().round(3), flush=True)

OFI = pd.read_parquet(OFI_PATH, columns=["ts", "sym", "ofi_1h", "aggr_buy_ratio_1h"])
D = D.merge(OFI.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
ofi_cov = D.ofi_1h.notna().mean()
print("join OFI: coverage(ofi_1h notna)=", round(ofi_cov, 5),
      "n_rows_with_ofi=", int(D.ofi_1h.notna().sum()), flush=True)

# noise control: cung PHAN BO missingness voi ofi_1h (chi khac nhau o cho co OFI that,
# thay bang uniform(0,1) doc lap, seed=20260920 -- dung PREREG Sec 4).
rng = np.random.default_rng(20260920)
noise_vals = rng.random(len(D), dtype=np.float32)
D["noise_ofi_check"] = np.where(D.ofi_1h.notna(), noise_vals, np.nan)
print("noise_ofi_check coverage matches ofi_1h:",
      bool((D.noise_ofi_check.notna() == D.ofi_1h.notna()).all()), flush=True)

D["yr"] = pd.to_datetime(D.ts, unit="ms").dt.year


def make_model(random_state=42):
    return xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4,
                          learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                          min_child_weight=50, n_jobs=1, tree_method="hist",
                          random_state=random_state, lambdarank_pair_method="topk",
                          lambdarank_num_pair_per_sample=8)


def run_variant(name, FE):
    preds = []
    for i, c in enumerate(CUT_MS_18):
        lo = c
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = D[D.ts < c - PURGE].sort_values("ts")
        oos = D[(D.ts >= lo) & (D.ts < hi)].sort_values("ts")
        if len(tr) < 5000 or len(oos) == 0:
            print(name, "fold", i, "skip", flush=True)
            continue
        assert tr.ts.max() < c, "LEAK"
        qid = pd.factorize(tr.ts, sort=True)[0]
        m = make_model(random_state=42)
        m.fit(tr[FE], tr.rel5, qid=qid)
        p = m.predict(oos[FE])
        sc = -p
        o = oos[["ts", "sym", "g1lite", "yr"]].assign(score=sc, fold=i)
        e = _edge5_fold(o)
        print(f"{name} fold {i} {CUTS18[i]}: train {len(tr)} oos {len(oos)} "
              f"ticks {oos.ts.nunique()} edge5 {100*e:+.3f}%", flush=True)
        preds.append(o)
    P = pd.concat(preds, ignore_index=True)
    P.to_parquet(f"{WORK}/pred_{name}.parquet")
    return P


def _edge5_fold(o):
    rk = o.groupby("ts").score.rank(method="first")
    top5 = o[rk <= 5]
    e = (top5.groupby("ts").g1lite.mean() - o.groupby("ts").g1lite.mean())
    return e.mean()


def edge5_series(P):
    rk = P.groupby("ts").score.rank(method="first")
    top5 = P[rk <= 5]
    e = top5.groupby("ts").g1lite.mean() - P.groupby("ts").g1lite.mean()
    return e


def rankic_series(P, outcome_col="g1lite", min_n=10):
    d = P[["ts", "score", outcome_col]].dropna()
    out = {}
    for ts, g in d.groupby("ts"):
        if len(g) < min_n:
            continue
        c = spearmanr(-g["score"], g[outcome_col]).correlation
        if c == c:
            out[ts] = c
    return pd.Series(out)


def inflate(k):
    return 1.0 if k <= 1 else float(np.sqrt(2 * np.log(k)))


def block_ci_diff(diff, block_h=BLOCK_H, nrep=NREP, seed=SEED, k=1):
    s = diff.dropna()
    if len(s) == 0:
        return dict(mean=float("nan"), lo=float("nan"), hi=float("nan"), n_ticks=0,
                    n_blocks=0, contains_zero=True, k=k, inflate=inflate(k))
    blk = (s.index // (block_h * H)).astype(np.int64)
    gb = s.groupby(blk).mean()
    cnt = s.groupby(blk).size()
    nb = len(gb)
    rng2 = np.random.default_rng(seed)
    obs = float(s.mean())
    bv = gb.to_numpy()
    cv = cnt.to_numpy().astype(np.float64)
    draws = np.empty(nrep)
    for i in range(nrep):
        pick = rng2.integers(0, nb, size=nb)
        draws[i] = np.sum(bv[pick] * cv[pick]) / np.sum(cv[pick])
    lo_raw, hi_raw = np.percentile(draws, [2.5, 97.5])
    f = inflate(k)
    c = (lo_raw + hi_raw) / 2.0
    hw = (hi_raw - lo_raw) / 2.0
    lo = c - hw * f
    hi = c + hw * f
    return dict(mean=obs, lo=float(lo), hi=float(hi), lo_raw=float(lo_raw), hi_raw=float(hi_raw),
                n_ticks=int(len(s)), n_blocks=int(nb), contains_zero=bool(lo <= 0.0 <= hi),
                k=k, inflate=f)


def sd_boot(diff, block_h=BLOCK_H, nrep=NREP, seed=SEED):
    s = diff.dropna()
    if len(s) == 0:
        return float("nan")
    blk = (s.index // (block_h * H)).astype(np.int64)
    gb = s.groupby(blk).mean()
    cnt = s.groupby(blk).size()
    nb = len(gb)
    rng2 = np.random.default_rng(seed)
    bv = gb.to_numpy()
    cv = cnt.to_numpy().astype(np.float64)
    draws = np.empty(nrep)
    for i in range(nrep):
        pick = rng2.integers(0, nb, size=nb)
        draws[i] = np.sum(bv[pick] * cv[pick]) / np.sum(cv[pick])
    return float(np.std(draws))


def verdict(ci):
    if ci["contains_zero"]:
        return "NULL"
    return "THANG" if ci["mean"] > 0 else "THUA"


print("load+merge done", round(time.time() - t0, 1), "sec", flush=True)

print("\n########## BASELINE (reused, not retrained) ##########", flush=True)
BASE = pd.read_parquet(BASELINE_PATH)  # ts,sym,score,fold
BASE = BASE.merge(D[["ts", "sym", "g1lite", "yr"]], on=["ts", "sym"], how="left")
assert BASE.g1lite.notna().all(), "baseline join g1lite co NaN -- ts/sym khong khop D"
base_e = edge5_series(BASE)
base_ic = rankic_series(BASE)
print("baseline edge5 all", f"{100*base_e.mean():+.4f}%", "n_ticks", len(base_e), flush=True)

print("\n########## CANDIDATE (KEEP9 + ofi_1h + aggr_buy_ratio_1h, k=2) ##########", flush=True)
FE_cand = KEEP9 + ["ofi_1h", "aggr_buy_ratio_1h"]
P_cand = run_variant("ofi_candidate", FE_cand)

print("\n########## NOISE CONTROL (KEEP9 + noise_ofi_check, k=2) ##########", flush=True)
FE_noise = KEEP9 + ["noise_ofi_check"]
P_noise = run_variant("ofi_noise", FE_noise)


def eval_candidate(name, P, k):
    n_bad = int((~np.isfinite(P.score)).sum())
    assert n_bad == 0, f"{name}: score co NaN/Inf"
    assert set(P.ts.unique()) == set(BASE.ts.unique()), f"{name}: tick set lech baseline"
    cand_e = edge5_series(P)
    cand_ic = rankic_series(P)
    d_e = cand_e - base_e
    d_ic = cand_ic - base_ic

    fold_of_ts = P.drop_duplicates("ts").set_index("ts")["fold"]

    def split(series, lo, hi):
        ts_in = fold_of_ts[(fold_of_ts >= lo) & (fold_of_ts <= hi)].index
        return series[series.index.isin(ts_in)]

    sel_e = split(d_e, 0, SELECT_N - 1)
    conf_e = split(d_e, SELECT_N, SELECT_N + CONFIRM_N - 1)
    sel_ic = split(d_ic, 0, SELECT_N - 1)
    conf_ic = split(d_ic, SELECT_N, SELECT_N + CONFIRM_N - 1)

    sd_sel = sd_boot(sel_e)
    ci_conf_e = block_ci_diff(conf_e, k=k)
    ci_conf_ic = block_ci_diff(conf_ic, k=k)
    return dict(
        name=name, k=k, n_oos=len(P), n_ticks=int(P.ts.nunique()),
        select_mean_edge5=float(sel_e.mean()) if len(sel_e) else float("nan"),
        select_sd_boot_edge5=sd_sel,
        select_threshold=inflate(k) * sd_sel if sd_sel == sd_sel else float("nan"),
        select_exceeds_threshold=(bool(abs(sel_e.mean()) >= inflate(k) * sd_sel)
                                   if sd_sel == sd_sel else None),
        select_n_ticks=int(len(sel_e)),
        confirm_edge5_ci=ci_conf_e,
        confirm_rankic_ci=ci_conf_ic,
        confirm_verdict_edge5=verdict(ci_conf_e),
        confirm_verdict_rankic=verdict(ci_conf_ic),
        confirm_n_ticks=int(len(conf_e)),
    )


res_cand = eval_candidate("ofi_candidate", P_cand, k=2)
res_noise = eval_candidate("ofi_noise", P_noise, k=2)

print("\n=== CANDIDATE result ===", flush=True)
print(json.dumps(res_cand, indent=2, default=str), flush=True)
print("\n=== NOISE result ===", flush=True)
print(json.dumps(res_noise, indent=2, default=str), flush=True)

# luat quyet dinh Sec 4.1 cua PREREG_S1_FREE_OFI.md
noise_confirm_exceed = not res_noise["confirm_edge5_ci"]["contains_zero"]
if noise_confirm_exceed:
    final_verdict = "HARNESS_NGHI_NGO -- noise vuot nguong tren CONFIRM, KHONG cong bo THANG/NULL/THUA cho candidate"
else:
    final_verdict = res_cand["confirm_verdict_edge5"]

result = dict(
    baseline_edge5_all_pct=float(100 * base_e.mean()),
    baseline_n_ticks=int(len(base_e)),
    ofi_coverage_frac=float(ofi_cov),
    candidate=res_cand,
    noise=res_noise,
    noise_select_exceeds=res_noise["select_exceeds_threshold"],
    noise_confirm_exceeds=noise_confirm_exceed,
    final_verdict=final_verdict,
)
with open(f"{WORK}/ofi_result.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
print("\n=== FINAL ===", flush=True)
print(json.dumps(result, indent=2, default=str), flush=True)
print("DONE", flush=True)
sys.exit(0)
