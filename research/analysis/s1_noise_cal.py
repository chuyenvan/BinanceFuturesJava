# NOISE_CAL: do ty le duong-tinh-gia cua doi chung nhieu tren SELECT vs CONFIRM.
# Pre-reg: docs/prereg/PREREG_S1_NOISE_CAL.md. TAI SU DUNG nguyen ham load_D/run_variant/metric cua
# research/analysis/s1_hpo_bag_featgrp.py (import module, KHONG sua logic train/nhan/purge).
# Tai su dung baseline da co san (/home/ubuntu/s1hpo/pred_baseline18.parquet, seed 42, KEEP9,
# da PASS tu-kiem spearman=1.0 trong result.json.baseline18_selfcheck) thay vi train lai --
# tiet kiem ~11 phut, khong doi ket qua vi la CUNG mot baseline model/predictions.
import json
import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import s1_hpo_bag_featgrp as base

OUT = base.OUT
KEEP9 = base.KEEP9
CUTS18 = base.CUTS18
CUT_MS_18 = base.CUT_MS_18
TZ = base.TZ
SELECT_N = base.SELECT_N
CONFIRM_N = base.CONFIRM_N

# seed cho cot nhieu MOI (noise_0/1/2 da co san trong feat_v2_x1.parquet, seed goc 20260902,
# xem docs/prereg/PREREG_S1_NOISE_CAL.md Sec 2). Chot TRUOC khi chay, khong doi sau khi thay so.
NEW_NOISE_SEEDS = {"noise_3": 20260920, "noise_4": 20260921}


def fold_windows(cuts_ms=CUT_MS_18):
    """Y het cong thuc lo/hi trong run_variant(), dung de suy lai fold cho baseline tai su dung
    (pred_baseline18.parquet chi luu ts,sym,score, khong luu fold)."""
    ws = []
    for c in cuts_ms:
        lo = c
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        ws.append((lo, hi))
    return ws


def assign_fold(ts, windows):
    fold = np.full(len(ts), -1, dtype=np.int64)
    for i, (lo, hi) in enumerate(windows):
        m = (ts >= lo) & (ts < hi)
        fold[m] = i
    return fold


def main():
    base._p("\n########## NOISE_CAL: noise_1..noise_4 doi chung (xem PREREG_S1_NOISE_CAL.md) ##########")
    D = base.load_D()

    # doc noise_1, noise_2 co san (seed 20260902, cung rng stream voi noise_0 -- xac nhan doc
    # lap thuc nghiem trong pre-reg: corr ~ 1e-4)
    Fextra = pd.read_parquet(base.X1_FEAT, columns=["ts", "sym", "noise_1", "noise_2"])
    Fextra["noise_1"] = Fextra["noise_1"].astype(np.float32)
    Fextra["noise_2"] = Fextra["noise_2"].astype(np.float32)

    # sinh noise_3, noise_4 MOI: 1 draw uniform doc lap / dong (ts_h,sym) cua feat_v2_x1.parquet,
    # giong het cach noise_0/1/2 duoc sinh trong x1_feat_v2_build.py, CHI khac seed. KHONG ghi
    # de file feat_v2_x1.parquet goc -- chi merge tam trong bo nho script nay.
    for col, seed in NEW_NOISE_SEEDS.items():
        rng = np.random.default_rng(seed)
        Fextra[col] = rng.random(len(Fextra)).astype(np.float32)

    D = D.merge(Fextra.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    cov = {c: float(D[c].notna().mean()) for c in ["noise_1", "noise_2", "noise_3", "noise_4"]}
    base._p("noise_1..4 merged, coverage (ty le notna sau merge ts_h,sym) =", cov)

    # baseline: TAI SU DUNG pred_baseline18.parquet (seed 42, KEEP9, da PASS self-check trong
    # result.json). Ghep lai g1lite tu D (cung ts,sym), suy lai fold tu 18 cua so cutoff.
    baseline = pd.read_parquet(f"{OUT}/pred_baseline18.parquet")
    # pred_baseline18.parquet da duoc main() cua s1_hpo_bag_featgrp.py ghi de bang
    # baseline.to_parquet(...) SAU KHI tinh xong (khong phai ban rut gon ts,sym,score cua
    # run_variant(save=True) noi bo) -- xac nhan thuc nghiem: file co du ts,sym,g1lite,yr,
    # score,fold. Vi vay dung truc tiep, KHONG can suy lai fold/g1lite (sua loi so voi thiet ke
    # ban dau trong PREREG_S1_NOISE_CAL.md Sec 2 -- gia tri ket qua khong doi vi day la CUNG
    # mot du lieu, chi khac cach lay).
    assert {"ts", "sym", "g1lite", "fold", "score"}.issubset(baseline.columns), (
        f"pred_baseline18.parquet thieu cot: {list(baseline.columns)}")
    base._p("baseline (tai su dung pred_baseline18.parquet) ticks/fold:\n",
            baseline.groupby("fold").ts.nunique().to_string())

    RL = pd.read_parquet(base.PATH_LABELS, columns=["ts", "sym", "g1_replay"])
    REPLAY_MAX_TS = int(RL.ts.max())

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
    base_e = base.edge5_series(baseline)
    base_ic_lite = base.rankic_series(baseline, "g1lite")
    base_ic_replay = base.rankic_series(base_r, "g1_replay")

    def metrics_for(P, tag):
        Pr, rate_info = with_replay(P)
        e = base.edge5_series(P)
        ic_lite = base.rankic_series(P, "g1lite")
        ic_replay = base.rankic_series(Pr, "g1_replay")
        n_bad = int((~np.isfinite(P.score)).sum())
        sanity = dict(n_oos=len(P), replay_join_rate_overall=rate_info["rate_overall"],
                      replay_join_rate_covered=rate_info["rate_covered"],
                      replay_n_covered=rate_info["n_covered"], n_bad_score=n_bad,
                      ticks=int(P.ts.nunique()))
        base.log(tag, "sanity", sanity)
        assert n_bad == 0, f"{tag}: score co NaN/Inf"
        assert rate_info["n_covered"] == 0 or rate_info["rate_covered"] >= 0.95, (
            f"{tag}: g1_replay join rate TRONG pham vi coverage "
            f"{rate_info['rate_covered']:.4f} < 0.95")
        return dict(edge5=e, ic_lite=ic_lite, ic_replay=ic_replay, sanity=sanity)

    base_m = metrics_for(baseline, "baseline_reused")
    base._p("baseline_reused ticks =", base_m["sanity"]["ticks"],
            "(doi chieu voi result.json baseline_sanity.ticks=18283)")

    def eval_candidate(name, P, k=3):
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
        conf_iclite = split(d_iclite, SELECT_N, SELECT_N + CONFIRM_N - 1)
        conf_icreplay = split(d_icreplay, SELECT_N, SELECT_N + CONFIRM_N - 1)

        ci_conf_e = base.block_ci_diff(conf_e, k=k)
        ci_conf_iclite = base.block_ci_diff(conf_iclite, k=k)
        ci_conf_icreplay = base.block_ci_diff(conf_icreplay, k=k)
        ci_sel_e = base.block_ci_diff(sel_e, k=k)
        sd_sel = base.sd_boot(sel_e)

        return dict(name=name, k=k,
                    select_mean_edge5=float(sel_e.mean()) if len(sel_e) else float("nan"),
                    select_sd_boot_edge5=sd_sel,
                    select_threshold=base.inflate(k) * sd_sel if sd_sel == sd_sel else float("nan"),
                    select_exceeds_threshold=(bool(abs(sel_e.mean()) >= base.inflate(k) * sd_sel)
                                               if sd_sel == sd_sel else None),
                    select_ci_edge5=ci_sel_e,
                    confirm_edge5_ci=ci_conf_e,
                    confirm_iclite_ci=ci_conf_iclite,
                    confirm_icreplay_ci=ci_conf_icreplay,
                    confirm_verdict_edge5=base.verdict(ci_conf_e["mean"], ci_conf_e),
                    sanity=cand_m["sanity"])

    results = {}
    for col in ["noise_1", "noise_2", "noise_3", "noise_4"]:
        FE = KEEP9 + [col]
        P = base.run_variant(D, f"noisecal_{col}", FE, [dict(random_state=42)], cuts_days=CUTS18)
        results[col] = eval_candidate(f"NOISECAL_{col}", P, k=3)
        base._p(col, "select_mean_edge5=", results[col]["select_mean_edge5"],
                "select_exceeds_threshold=", results[col]["select_exceeds_threshold"],
                "confirm_verdict=", results[col]["confirm_verdict_edge5"],
                "confirm_contains_zero=", results[col]["confirm_edge5_ci"]["contains_zero"])

    with open(f"{OUT}/result.json") as f:
        prev = json.load(f)
    noise0 = prev["P3"]["noise_control"]

    select_exceed = {"noise_0": bool(noise0["select_exceeds_threshold"])}
    confirm_exceed = {"noise_0": bool(not noise0["confirm_edge5_ci"]["contains_zero"])}
    for col in ["noise_1", "noise_2", "noise_3", "noise_4"]:
        select_exceed[col] = bool(results[col]["select_exceeds_threshold"])
        confirm_exceed[col] = bool(not results[col]["confirm_edge5_ci"]["contains_zero"])

    n_select_exceed = sum(select_exceed.values())
    n_confirm_exceed = sum(confirm_exceed.values())

    if n_confirm_exceed >= 2:
        branch = "c"
    elif n_select_exceed <= 2:
        branch = "a"
    else:
        branch = "b"

    out = dict(noise0=noise0, results=results, select_exceed=select_exceed,
               confirm_exceed=confirm_exceed, n_select_exceed=n_select_exceed,
               n_confirm_exceed=n_confirm_exceed, branch=branch,
               noise_seeds=dict(noise_0=20260902, noise_1=20260902, noise_2=20260902,
                                 **NEW_NOISE_SEEDS),
               noise_coverage_after_merge=cov)
    with open(f"{OUT}/noisecal.json", "w") as f:
        json.dump(out, f, indent=2, default=str)
    base._p("=== NOISE_CAL DONE, branch =", branch,
            "select_exceed =", n_select_exceed, "/5",
            "confirm_exceed =", n_confirm_exceed, "/5 ===")
    base._p("select_exceed detail:", select_exceed)
    base._p("confirm_exceed detail:", confirm_exceed)


if __name__ == "__main__":
    main()
