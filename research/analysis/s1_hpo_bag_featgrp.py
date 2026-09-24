# S1_HPO_BAG_FEATGRP — 3 pre-reg doc lap (HPO / bagging / feature-group) tren S1, OFFLINE.
# Pre-reg: docs/prereg/PREREG_S1_HPO_BAG_FEATGRP.md. Copy khoi load-data/nhan/purge/run cua
# research/pipeline/x1/x1_s1_rank.py (KHONG doi logic nhan/purge), tham so hoa KEEP/hyperparam/
# seed/bagging. OFFLINE thuan: khong sim, khong bins, khong GPU. n_jobs=4 moi run.
#
# LUAT LOG CUA REPO: dung module `logging`, KHONG dung ham in san co.
import logging as _logging
import sys as _sys
_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
LOG = _logging.getLogger("s1hbf")


def _p(*a):
    LOG.info(" ".join(str(x) for x in a))


import argparse
import gc
import hashlib
import json
import os
import resource
import time


def rss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr


def log(*a):
    _p(time.strftime("%H:%M:%S"), *a)


# ---------- hang so / duong dan (chinh xac nhu x1_s1_rank.py) ----------
H = 3600000
TZ = 7 * H
PURGE = 72 * H
LED = "/home/ubuntu/ledger"
OUT = "/home/ubuntu/s1hpo"
X1_LNAME = "cand_dev_x1"
X1_FEAT = "/home/ubuntu/featv2/feat_v2_x1.parquet"
PATH_LABELS = f"{LED}/path_labels.parquet"

KEEP9 = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
         "ret_14d", "ls_global", "rk_oi_delta24h"]

CUTS18 = ("20210701 20211001 20220101 20220401 20220701 20221001 20230101 20230401 "
          "20230701 20231001 20240101 20240401 20240701 20241001 20250101 20250401 "
          "20250701 20251001").split()
CUTS16 = CUTS18[2:]
CUTS_Y21 = CUTS18[:2]

SELECT_N = 10   # fold idx 0..9  = 2021Q3..2023Q4
CONFIRM_N = 8   # fold idx 10..17 = 2024Q1..2025Q4

BLOCK_H = 72
NREP = 2000
SEED = 20260919

FEATGRP = {
    "G1": ["rs_btc_3d", "rs_btc_7d", "rs_mkt_3d", "rs_mkt_7d", "rk_rs_btc_7d"],
    "G2": ["fund_last", "fund_sum_3d", "fund_sum_7d", "fund_trend", "fund_z_30d", "rk_fund_sum_3d"],
    "G3": ["dd_30d", "pos_30d", "vol_30d", "ret_7d", "rk_ret_7d"],
    "NOISE": ["noise_0"],
}

ALL_FEATS_NEEDED = sorted(set(KEEP9) | set(FEATGRP["G1"]) | set(FEATGRP["G2"])
                           | set(FEATGRP["G3"]) | set(FEATGRP["NOISE"]))

HPO = {
    "H1": dict(max_depth=3),
    "H2": dict(max_depth=6),
    "H3": dict(n_estimators=150),
    "H4": dict(n_estimators=600),
    "H5": dict(min_child_weight=200),
    "H6": dict(lambdarank_num_pair_per_sample=16),
}


def cuts_to_ms(cut_days):
    return [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in cut_days]


CUT_MS_18 = cuts_to_ms(CUTS18)


def load_D():
    """Copy nguyen khoi load-data/nhan cua x1_s1_rank.py (bo phan chan doan rank-IC 37 feat,
    khong lien quan nhan/purge, chi de in thong tin). Logic nhan/purge giu Y NGUYEN.
    Toi uu BO NHO (khong doi ket qua): chi doc cot ts/sym/g1lite tu ledger (9 cot con lai
    khong dung o day) va chi 26 cot feature thuc su can (KEEP9+G1+G2+G3+noise_0, thay vi 40
    cot), downcast float64->float32 -- Oracle chi co 23G RAM, ban day du 40 cot da OOM-kill."""
    D = pd.read_parquet(f"{LED}/{X1_LNAME}.parquet", columns=["ts", "sym", "g1lite"])
    D = D[D.g1lite.notna()].copy()
    log("pool", D.shape)
    D["med"] = D.groupby("ts").g1lite.transform("median")
    D["rel"] = D.g1lite - D.med
    D["rk"] = D.groupby("ts").rel.rank(pct=True, method="first")
    D["rel5"] = np.minimum((D.rk * 5).astype(int), 4)
    D["ts_h"] = (D.ts // H) * H
    F = pd.read_parquet(X1_FEAT, columns=["ts", "sym"] + ALL_FEATS_NEEDED)
    for c in ALL_FEATS_NEEDED:
        if F[c].dtype == np.float64:
            F[c] = F[c].astype(np.float32)
    D = D.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    del F
    gc.collect()
    log("join feat: co vol_7d", D.vol_7d.notna().mean().round(3))
    D["yr"] = pd.to_datetime(D.ts, unit="ms").dt.year
    log("load_D done, peak RSS MB =", round(rss_mb(), 1))
    return D


def make_model(random_state=42, max_depth=4, n_estimators=300, min_child_weight=50,
               lambdarank_num_pair_per_sample=8):
    return xgb.XGBRanker(objective="rank:ndcg", n_estimators=n_estimators, max_depth=max_depth,
                          learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                          min_child_weight=min_child_weight, n_jobs=4, tree_method="hist",
                          random_state=random_state, lambdarank_pair_method="topk",
                          lambdarank_num_pair_per_sample=lambdarank_num_pair_per_sample)


def run_variant(D, name, FE, model_kwargs_list, cuts_days=CUTS18, cuts_ms=None, save=True):
    """Y het vong lap fold cua x1_s1_rank.py::run(), them: (a) FE/hyperparam tham so hoa,
    (b) bagging (>1 model) -> trung binh HANG trong tick, KHONG trung binh score tho."""
    if cuts_ms is None:
        cuts_ms = cuts_to_ms(cuts_days)
    preds = []
    for i, c in enumerate(cuts_ms):
        lo = c
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = D[D.ts < c - PURGE].sort_values("ts")
        oos = D[(D.ts >= lo) & (D.ts < hi)].sort_values("ts")
        if len(tr) < 5000 or len(oos) == 0:
            log(name, "fold", i, "skip")
            continue
        assert tr.ts.max() < c, "LEAK"
        qid = pd.factorize(tr.ts, sort=True)[0]
        rank_sum = np.zeros(len(oos))
        last_imp = None
        for kw in model_kwargs_list:
            m = make_model(**kw)
            m.fit(tr[FE], tr.rel5, qid=qid)
            p = m.predict(oos[FE])
            sc = -p
            rk = pd.Series(sc, index=oos.index).groupby(oos["ts"]).rank(method="first")
            rank_sum += rk.to_numpy()
            last_imp = pd.Series(m.feature_importances_, index=FE)
        final_score = rank_sum / len(model_kwargs_list)
        o = oos[["ts", "sym", "g1lite", "yr"]].assign(score=final_score, fold=i)
        o["rk"] = o.groupby("ts").score.rank(method="first")
        e = (o[o.rk <= 5].groupby("ts").g1lite.mean() - o.groupby("ts").g1lite.mean())
        log(f"{name} fold {i} {cuts_days[i]}: train {len(tr)} oos {len(oos)} "
            f"ticks {oos.ts.nunique()} edge5 {100 * e.mean():+.2f}%")
        preds.append(o.drop(columns=["rk"]))
    P = pd.concat(preds, ignore_index=True)
    E = edge5_series(P)
    yr = pd.to_datetime(E.index, unit="ms").year
    _p(f"=== {name}: edge5 g1lite OOS all {100 * E.mean():+.3f}% ticks {len(E)} ===")
    if last_imp is not None:
        _p(name, "feature_importance(last fold):\n", last_imp.sort_values(ascending=False).round(3).to_string())
    if save:
        P[["ts", "sym", "score"]].to_parquet(f"{OUT}/pred_{name}.parquet")
    log(name, "peak RSS MB =", round(rss_mb(), 1))
    return P


# ---------------- metrics ----------------

def edge5_series(P):
    """P: dataframe voi cot ts,sym,g1lite,score,fold. Tra ve Series edge5 index=ts."""
    rk = P.groupby("ts").score.rank(method="first")
    top5 = P[rk <= 5]
    e = top5.groupby("ts").g1lite.mean() - P.groupby("ts").g1lite.mean()
    return e


def rankic_series(P, outcome_col, min_n=10):
    """P phai co cot 'score' va outcome_col. Tra ve Series rank-IC index=ts (score thap=tot,
    dung -score de IC>0 = S1 lam dung viec)."""
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
    """Paired block-bootstrap cua trung binh Delta (Series index=ts, don vi ms).
    inflate(k) ap quanh tam (dung quy uoc AUDIT_CI_INFLATE_STANDARDIZATION.md muc 1.1)."""
    s = diff.dropna()
    if len(s) == 0:
        return dict(mean=float("nan"), lo=float("nan"), hi=float("nan"), n_ticks=0,
                    n_blocks=0, contains_zero=True, k=k, inflate=inflate(k))
    blk = (s.index // (block_h * H)).astype(np.int64)
    gb = s.groupby(blk).mean()
    cnt = s.groupby(blk).size()
    nb = len(gb)
    rng = np.random.default_rng(seed)
    obs = float(s.mean())
    bv = gb.to_numpy()
    cv = cnt.to_numpy().astype(np.float64)
    draws = np.empty(nrep)
    for i in range(nrep):
        pick = rng.integers(0, nb, size=nb)
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
    """sd cua phan phoi bootstrap trung binh Delta (dung cho nguong T2 kieu PREREG_FS)."""
    s = diff.dropna()
    if len(s) == 0:
        return float("nan")
    blk = (s.index // (block_h * H)).astype(np.int64)
    gb = s.groupby(blk).mean()
    cnt = s.groupby(blk).size()
    nb = len(gb)
    rng = np.random.default_rng(seed)
    bv = gb.to_numpy()
    cv = cnt.to_numpy().astype(np.float64)
    draws = np.empty(nrep)
    for i in range(nrep):
        pick = rng.integers(0, nb, size=nb)
        draws[i] = np.sum(bv[pick] * cv[pick]) / np.sum(cv[pick])
    return float(np.std(draws))


def verdict(mean, ci):
    if ci["contains_zero"]:
        return "NULL"
    return "THANG" if mean > 0 else "THUA"


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------- cong reproduction ----------------

def gate_reproduction(D):
    _p("\n########## CONG REPRODUCTION ##########")
    t0 = time.time()
    P16 = run_variant(D, "repro16", KEEP9, [dict(random_state=42)], cuts_days=CUTS16, save=False)
    t16 = time.time() - t0
    t0 = time.time()
    Py21 = run_variant(D, "repro_y21", KEEP9, [dict(random_state=42)], cuts_days=CUTS_Y21, save=False)
    ty21 = time.time() - t0

    old16 = pd.read_parquet(f"{LED}/pred_s1a2x1.parquet")
    oldy21 = pd.read_parquet(f"{LED}/pred_s1a2x1_y21.parquet")

    def cmp(new, old, tag):
        m = new.merge(old, on=["ts", "sym"], suffixes=("_new", "_old"), how="inner")
        n_new, n_old, n_join = len(new), len(old), len(m)
        sp = spearmanr(m.score_new, m.score_old).correlation if n_join > 1 else float("nan")
        maxd = float((m.score_new - m.score_old).abs().max()) if n_join else float("nan")
        e_new = edge5_series(new)
        # CHAN DOAN (Buoc 1 MASTER): score cua script nay la HANG trong tick (xem run_variant),
        # trong khi score cu (pred_s1a2x1*.parquet) la -p LIEN TUC toan cuc -- 2 dai luong khac
        # thang do nen spearman GLOBAL co the thap ngay ca khi model tai lap y het. Do THEM
        # spearman TRONG TICK (bat bien voi phep bien doi hang don dieu) va ty le hang trung
        # khop tuyet doi de phan biet "gate sai dinh nghia" voi "model thuc su khac".
        m["rk_new"] = m.groupby("ts").score_new.rank(method="first")
        m["rk_old"] = m.groupby("ts").score_old.rank(method="first")
        def _sp1(g):
            if len(g) < 3:
                return np.nan
            return spearmanr(g.score_new, g.score_old).correlation
        intick = m.groupby("ts").apply(_sp1)
        intick = intick.dropna()
        rank_match = float((m.rk_new == m.rk_old).mean()) if len(m) else float("nan")
        intick_median = float(intick.median()) if len(intick) else float("nan")
        intick_min = float(intick.min()) if len(intick) else float("nan")
        intick_frac_ge_0999 = float((intick >= 0.999).mean()) if len(intick) else float("nan")
        _p(f"[{tag}] n_new={n_new} n_old={n_old} n_join={n_join} spearman={sp:.9f} "
           f"max|d|={maxd:.3e} edge5_new={100*e_new.mean():+.3f}% | "
           f"intick_spearman median={intick_median:.6f} min={intick_min:.6f} "
           f"frac>=0.999={intick_frac_ge_0999:.4f} n_ticks={len(intick)} "
           f"rank_exact_match_frac={rank_match:.6f}")
        return dict(n_new=n_new, n_old=n_old, n_join=n_join, spearman=sp, maxd=maxd,
                    edge5=100 * e_new.mean(), intick_spearman_median=intick_median,
                    intick_spearman_min=intick_min, intick_frac_ge_0999=intick_frac_ge_0999,
                    rank_exact_match_frac=rank_match)

    r16 = cmp(P16, old16, "repro16 vs pred_s1a2x1")
    ry21 = cmp(Py21, oldy21, "repro_y21 vs pred_s1a2x1_y21")

    # DINH CHINH GATE (Buoc 1 MASTER, truoc khi xem ket qua P1-P3): score cua script nay la
    # HANG trong tick (xem run_variant docstring), khong phai -p LIEN TUC toan cuc nhu file cu
    # (pred_s1a2x1*.parquet) -- spearman GLOBAL giua 2 dai luong khac thang do KHONG =1.0 ngay
    # ca khi model tai lap tuyet doi. Da xac nhan thuc nghiem (xem gate2.log):
    #   16-fold: rank_exact_match_frac=1.000000, intick_spearman median=1.000000 min=0.552560
    #            frac(>=0.999)=0.9995 tren 17349 tick.
    #   y21    : rank_exact_match_frac=1.000000, intick_spearman median=0.999998 min=0.999608
    #            frac(>=0.999)=1.0000 tren 934 tick.
    # rank_exact_match_frac=1.0 (moi dong, ca 2 cua so) la bang chung manh nhat: rank(method=
    # "first") trong tick cua score moi TRUNG TUYET DOI voi rank cua score cu -- model tai lap
    # y het, KHONG phai model khac. Cac tick co intick spearman thap (vd min=0.5526) la ARTIFACT
    # cua spearmanr tu tinh tie-break rieng (khac "first") tren nhom cuc nho co gia tri trung
    # nhau -- KHONG mau thuan voi rank_exact_match_frac=1.0. Vi vay dung rank_exact_match_frac
    # (bat bien voi tie-break, khong bi nhieu boi nhom nho) lam tieu chi chinh thay cho
    # "spearman trong tick min>=0.999" (de bi artifact o nhom nho), giu them edge5 khop moc va
    # so dong khop lam 2 tieu chi con lai dung nhu Sec.1 pre-reg goc.
    EDGE5_REF16 = 15.41
    EDGE5_REFY21 = 7.545
    ok = (r16["n_new"] == r16["n_old"] == r16["n_join"] and r16["rank_exact_match_frac"] >= 0.999999
          and abs(r16["edge5"] - EDGE5_REF16) <= 0.05
          and ry21["n_new"] == ry21["n_old"] == ry21["n_join"] and ry21["rank_exact_match_frac"] >= 0.999999
          and abs(ry21["edge5"] - EDGE5_REFY21) <= 0.05)
    md5s = dict(pred_s1a2x1=md5_of(f"{LED}/pred_s1a2x1.parquet"),
                pred_s1a2x1_y21=md5_of(f"{LED}/pred_s1a2x1_y21.parquet"),
                sha256_pred_s1a2x1=sha256_of(f"{LED}/pred_s1a2x1.parquet"),
                sha256_pred_s1a2x1_y21=sha256_of(f"{LED}/pred_s1a2x1_y21.parquet"))
    out = dict(pass_=ok, repro16=r16, repro_y21=ry21, t16_sec=t16, ty21_sec=ty21,
               t18_extrapolated_sec=t16 + ty21, md5=md5s)
    _p("REPRODUCTION GATE:", "PASS" if ok else "FAIL")
    return out, P16, Py21


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["gate", "full"])
    args = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    t_start = time.time()
    D = load_D()

    gate_out, P16, Py21 = gate_reproduction(D)
    with open(f"{OUT}/gate_result.json", "w") as f:
        json.dump(gate_out, f, indent=2, default=str)
    if not gate_out["pass_"]:
        _p("REPRODUCTION GATE FAILED -- DUNG, khong chay tiep pre-reg nao.")
        _sys.exit(1)

    if args.mode == "gate":
        _p("mode=gate xong, thoat (khong chay pre-reg).")
        return

    # Baseline dung CHUNG cho P1/P2/P3: MOT lan train rieng tren du 18 fold (fold index 0..17
    # dung thu tu CUTS18 = SELECT 0-9 / CONFIRM 10-17). Khong tai su dung truc tiep P16/Py21 cua
    # gate vi hai lan goi do co fold-index rieng (0..15 va 0..1) can phai doi lai truoc khi ghep;
    # train lai 1 lan 18-fold don gian hon va tu no la mot phep kiem tra doc lap them.
    _p("\n########## BASELINE 18-fold (dung cho P1/P2/P3) ##########")
    baseline = run_variant(D, "baseline18", KEEP9, [dict(random_state=42)], cuts_days=CUTS18)
    baseline_fold_check = baseline.groupby("fold").ts.nunique()
    _p("baseline 18-fold ticks per fold:\n", baseline_fold_check.to_string())

    # Kiem tu-nhat-quan: baseline18 phai trung tuyet doi voi ghep P16 (fold+2) + Py21 (fold+0)
    # cua cong reproduction (da PASS spearman=1.0 vs artifact cu o gate_reproduction).
    p16_shift = P16.assign(fold=P16.fold + len(CUTS_Y21))
    y21_shift = Py21.assign(fold=Py21.fold)
    concat_check = pd.concat([y21_shift, p16_shift], ignore_index=True)
    mchk = baseline.merge(concat_check, on=["ts", "sym"], suffixes=("_b18", "_split"), how="inner")
    sp_chk = spearmanr(mchk.score_b18, mchk.score_split).correlation if len(mchk) > 1 else float("nan")
    ok_chk = (len(mchk) == len(baseline) == len(concat_check)) and abs(sp_chk - 1.0) < 1e-6
    _p(f"[baseline18 self-check] n_b18={len(baseline)} n_split={len(concat_check)} "
       f"n_join={len(mchk)} spearman={sp_chk:.9f} OK={ok_chk}")
    if not ok_chk:
        _p("*** BASELINE18 SELF-CHECK FAILED -- DUNG. ***")
        _sys.exit(1)
    baseline.to_parquet(f"{OUT}/pred_baseline18.parquet")

    RL = pd.read_parquet(PATH_LABELS, columns=["ts", "sym", "g1_replay"])
    # CHAN DOAN (phat hien khi chay full, TRUOC khi xem bat ky Delta P1-P3 nao): join rate
    # g1_replay tong the chi ~13.25% tren baseline 18-fold, TUONG PHAN voi gia dinh >=95% cua
    # Sec 2.5. Da xac nhan thuc nghiem tren pred_baseline18.parquet: fold 0-11 (cutoff <=
    # 20240401) co rate ~99.9-100%, fold 12-17 (cutoff >= 20240701) co rate = 0.000000 TUYET
    # DOI, khop chinh xac voi ts max cua path_labels.parquet (2024-06-30 16:45, dung bien
    # OOS-end cua fold 11). Day la GIOI HAN CO SAN cua file nhan phu path_labels.parquet (chua
    # duoc tinh cho nua sau 2024 tro di), KHONG phai loi join key/harness -- va KHONG duoc sinh
    # lai/mo rong file nay trong vong nay (pham vi cam Sec 6: "khong sinh bins/dataset moi").
    # Sua: ap nguong >=95% cua Sec 2.5 CHI trong pham vi coverage thuc te (ts <= REPLAY_MAX_TS)
    # thay vi tren toan bo 18 fold; metric CHINH edge5 (tren g1lite) khong bi anh huong vi
    # g1lite luon co du 18 fold. He qua: Delta rank-IC tren g1_replay o cua so CONFIRM (fold
    # 10-17) chi con du lieu that o fold 10-11 (2024 Q1-Q2) -- ghi ro trong RESULT, day la gioi
    # han BAO CAO cua mot metric PHU (Sec 2.4: rank-IC "bao cao song song, khong phai luat
    # quyet dinh"), khong lam sai lech phan quyet THANG/NULL/THUA (luon theo edge5).
    REPLAY_MAX_TS = int(RL.ts.max())
    _p(f"path_labels (g1_replay) coverage: ts <= {pd.Timestamp(REPLAY_MAX_TS, unit='ms')} -- "
       f"cutoff 20240701 tro di (fold 12-17) KHONG co g1_replay (gioi han von co cua file nhan).")

    def with_replay(P):
        m = P.merge(RL, on=["ts", "sym"], how="left")
        covered = m.ts <= REPLAY_MAX_TS
        n_covered = int(covered.sum())
        rate_overall = float(m.g1_replay.notna().mean())
        rate_covered = (float(m.loc[covered, "g1_replay"].notna().mean())
                        if n_covered else float("nan"))
        return m, dict(rate_overall=rate_overall, rate_covered=rate_covered,
                       n_covered=n_covered, n_total=len(m))

    base_r, base_rate_info = with_replay(baseline)
    _p(f"baseline g1_replay join rate: overall={base_rate_info['rate_overall']:.4f} "
       f"covered(ts<=REPLAY_MAX_TS, n={base_rate_info['n_covered']})="
       f"{base_rate_info['rate_covered']:.4f}")

    base_e = edge5_series(baseline)
    base_ic_lite = rankic_series(baseline, "g1lite")
    base_ic_replay = rankic_series(base_r, "g1_replay")

    def metrics_for(P, tag):
        Pr, rate_info = with_replay(P)
        e = edge5_series(P)
        ic_lite = rankic_series(P, "g1lite")
        ic_replay = rankic_series(Pr, "g1_replay")
        n_bad = int((~np.isfinite(P.score)).sum())
        sanity = dict(n_oos=len(P), replay_join_rate_overall=rate_info["rate_overall"],
                      replay_join_rate_covered=rate_info["rate_covered"],
                      replay_n_covered=rate_info["n_covered"], n_bad_score=n_bad,
                      ticks=int(P.ts.nunique()))
        log(tag, "sanity", sanity)
        assert n_bad == 0, f"{tag}: score co NaN/Inf"
        assert rate_info["n_covered"] == 0 or rate_info["rate_covered"] >= 0.95, (
            f"{tag}: g1_replay join rate TRONG pham vi coverage "
            f"{rate_info['rate_covered']:.4f} < 0.95")
        return dict(edge5=e, ic_lite=ic_lite, ic_replay=ic_replay, sanity=sanity)

    base_m = metrics_for(baseline, "baseline")

    def eval_candidate(name, P, k, window_select=True):
        cand_m = metrics_for(P, name)
        assert set(P.ts.unique()) == set(baseline.ts.unique()), f"{name}: tick set lech baseline"
        d_e = cand_m["edge5"] - base_m["edge5"]
        d_iclite = cand_m["ic_lite"] - base_m["ic_lite"]
        d_icreplay = cand_m["ic_replay"] - base_m["ic_replay"]

        def split(series, fold_lo, fold_hi):
            fold_of_ts = P.drop_duplicates("ts").set_index("ts")["fold"]
            ts_in = fold_of_ts[(fold_of_ts >= fold_lo) & (fold_of_ts <= fold_hi)].index
            return series[series.index.isin(ts_in)]

        sel_e = split(d_e, 0, SELECT_N - 1)
        conf_e = split(d_e, SELECT_N, SELECT_N + CONFIRM_N - 1)
        sel_iclite = split(d_iclite, 0, SELECT_N - 1)
        conf_iclite = split(d_iclite, SELECT_N, SELECT_N + CONFIRM_N - 1)
        sel_icreplay = split(d_icreplay, 0, SELECT_N - 1)
        conf_icreplay = split(d_icreplay, SELECT_N, SELECT_N + CONFIRM_N - 1)

        ci_conf_e = block_ci_diff(conf_e, k=k)
        ci_conf_iclite = block_ci_diff(conf_iclite, k=k)
        ci_conf_icreplay = block_ci_diff(conf_icreplay, k=k)
        sd_sel = sd_boot(sel_e)

        return dict(name=name, k=k,
                    select_mean_edge5=float(sel_e.mean()) if len(sel_e) else float("nan"),
                    select_sd_boot_edge5=sd_sel,
                    select_threshold=inflate(k) * sd_sel if sd_sel == sd_sel else float("nan"),
                    select_exceeds_threshold=bool(abs(sel_e.mean()) >= inflate(k) * sd_sel) if sd_sel == sd_sel else None,
                    confirm_edge5_ci=ci_conf_e,
                    confirm_iclite_ci=ci_conf_iclite,
                    confirm_icreplay_ci=ci_conf_icreplay,
                    confirm_verdict_edge5=verdict(ci_conf_e["mean"], ci_conf_e),
                    sanity=cand_m["sanity"])

    result = dict(gate=gate_out, baseline18_selfcheck=dict(n_b18=len(baseline),
                  n_split=len(concat_check), n_join=len(mchk), spearman=sp_chk, ok=ok_chk),
                  baseline_sanity=base_m["sanity"])

    # ---------------- P1: S1_HPO (k=6) ----------------
    _p("\n########## P1 S1_HPO (k=6) ##########")
    p1_results = {}
    for hid, kw in HPO.items():
        mk = dict(random_state=42)
        mk.update(kw)
        P = run_variant(D, f"p1_{hid}", KEEP9, [mk])
        p1_results[hid] = eval_candidate(f"P1_{hid}", P, k=6)
    nominee1 = max(p1_results, key=lambda h: p1_results[h]["select_mean_edge5"])
    _p("P1 de cu (SELECT tot nhat):", nominee1, p1_results[nominee1]["select_mean_edge5"])
    result["P1"] = dict(candidates=p1_results, nominee=nominee1,
                         verdict=p1_results[nominee1]["confirm_verdict_edge5"])

    # ---------------- P2: S1_BAG (k=1) ----------------
    _p("\n########## P2 S1_BAG (k=1) ##########")
    seeds = [42, 1, 2, 3, 4]
    P_bag = run_variant(D, "p2_bag5", KEEP9, [dict(random_state=s) for s in seeds])
    p2_res = eval_candidate("P2_BAG5", P_bag, k=1)
    result["P2"] = dict(candidate=p2_res, verdict=p2_res["confirm_verdict_edge5"])

    # ---------------- P3: S1_FEATGRP (k=3) + doi chung nhieu ----------------
    _p("\n########## P3 S1_FEATGRP (k=3) ##########")
    p3_results = {}
    for gid in ["G1", "G2", "G3"]:
        FE = KEEP9 + FEATGRP[gid]
        P = run_variant(D, f"p3_{gid}", FE, [dict(random_state=42)])
        p3_results[gid] = eval_candidate(f"P3_{gid}", P, k=3)
    nominee3 = max(p3_results, key=lambda g: p3_results[g]["select_mean_edge5"])
    _p("P3 de cu (SELECT tot nhat):", nominee3, p3_results[nominee3]["select_mean_edge5"])

    # doi chung nhieu
    FE_noise = KEEP9 + FEATGRP["NOISE"]
    P_noise = run_variant(D, "p3_noise", FE_noise, [dict(random_state=42)])
    noise_res = eval_candidate("P3_NOISE", P_noise, k=3)
    noise_flag = noise_res["select_exceeds_threshold"]
    _p("P3 NOISE select_exceeds_threshold =", noise_flag)

    result["P3"] = dict(candidates=p3_results, nominee=nominee3,
                         verdict=p3_results[nominee3]["confirm_verdict_edge5"],
                         noise_control=noise_res, harness_error=bool(noise_flag))

    result["elapsed_sec_total"] = time.time() - t_start
    with open(f"{OUT}/result.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    _p("\n=== DONE, wrote", f"{OUT}/result.json", "elapsed", result["elapsed_sec_total"], "sec ===")

    if noise_flag:
        _p("*** HARNESS ERROR: doi chung nhieu (noise_0) VUOT nguong o SELECT. "
           "KHONG bao cao ket qua P1/P2/P3 nao khac cho den khi dieu tra. ***")


if __name__ == "__main__":
    main()
