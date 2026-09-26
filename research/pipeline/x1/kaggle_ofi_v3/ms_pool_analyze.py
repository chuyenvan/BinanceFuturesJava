"""Pooled multi-seed analysis cho OFI V3 — docs/prereg/PREREG_S1_FREE_OFI_V3_MULTISEED.md muc 3.

Doc `ms_diffs_s<seed>.parquet` (output PHU cua 4 kernel) + `ofi_result_v3_ms_s<seed>.json`,
roi ap dung DUNG ham `block_ci_diff` cua `ofi_train_eval_v3.py` (block 72h, NREP 2000, bootstrap
seed 20260919) voi k=3 (inflate = 1,482304) de ra per-seed + pooled + verdict theo luat C1..C6.

KHONG tinh lai metric tu du lieu tho: moi so per-seed lay/don lai tu chinh chuoi diff ma kernel xuat ra
(co doi chieu cheo voi json cua kernel).

Dung: python ms_pool_analyze.py <dir_output> > summary.json
"""
import json
import os
import sys

import numpy as np
import pandas as pd

NREP = 2000
BLOCK_H = 72
SEED = 20260919
K = 3
SELECT_N = 10
CONFIRM_N = 8
SEEDS = [42, 43, 44, 45]
NEW = [43, 44, 45]
H = 3600000

# So da CONG BO (RESULT_S1_FREE_OFI_V3_UNIVERSE.md, commit c5c9faf) — dung cho kiem toan ven C6.
PUB_REF = dict(
    cand_edge5_mean=0.016500961035490036,
    cand_rankic_mean=0.0019546861051446362,
    baseline_fresh_edge5_all_pct=15.209467887878418,
)


def inflate(k):
    return 1.0 if k <= 1 else float(np.sqrt(2 * np.log(k)))


def block_ci_diff(diff, block_h=BLOCK_H, nrep=NREP, seed=SEED, k=1):
    """COPY NGUYEN ham cua ofi_train_eval_v3.py (khong doi mot chu)."""
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


def verdict(ci):
    if ci["contains_zero"]:
        return "NULL"
    return "THANG" if ci["mean"] > 0 else "THUA"


D = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
out = {"dir": D, "K": K, "inflate_K": inflate(K), "nrep": NREP, "bootstrap_seed": SEED,
       "block_h": BLOCK_H, "seeds": SEEDS, "new_seeds": NEW}

# ---- nap diff + json tung seed ----
diffs, js = {}, {}
for s in SEEDS:
    diffs[s] = pd.read_parquet(os.path.join(D, f"ms_diffs_s{s}.parquet"))
    js[s] = json.load(open(os.path.join(D, f"ofi_result_v3_ms_s{s}.json")))

fold = diffs[42]["fold"]
for s in SEEDS:
    assert diffs[s].columns.tolist() == diffs[42].columns.tolist(), f"cot khac nhau o seed {s}"


def key(s, prefix, kind):
    return diffs[s][f"{prefix}__{kind}"]


def split(series, lo, hi):
    ts_in = fold[(fold >= lo) & (fold <= hi)].index
    return series[series.index.isin(ts_in)]


def per_seed(variant, kind, lo, hi):
    return {s: split(key(s, variant, kind), lo, hi) for s in SEEDS}


# ---- C5 sanity: tap tick phai TRUNG KHOP giua cac seed ----
idx_eq = {}
for variant in ("candidate_vs_fresh", "noise_vs_fresh", "fresh_vs_frozen"):
    for kind in ("edge5", "rankic"):
        base = set(per_seed(variant, kind, 0, SELECT_N + CONFIRM_N - 1)[42].dropna().index)
        idx_eq[f"{variant}__{kind}"] = all(
            set(per_seed(variant, kind, 0, SELECT_N + CONFIRM_N - 1)[s].dropna().index) == base
            for s in SEEDS)
out["C5_tick_index_identical_across_seeds"] = idx_eq
out["C5_all_pass"] = bool(all(idx_eq.values()))

# ---- C6 kiem toan ven moi truong: seed 42 tai lap so da cong bo ----
s42 = js[42]
c42 = s42["candidate_vs_fresh"]["confirm_edge5_ci"]["mean"]
i42 = s42["candidate_vs_fresh"]["confirm_rankic_ci"]["mean"]
b42 = s42["baseline_fresh_edge5_all_pct"]
fvf42 = key(42, "fresh_vs_frozen", "edge5").abs().max()
out["C6_repro_seed42"] = dict(
    cand_edge5_mean=c42, pub=PUB_REF["cand_edge5_mean"], abs_diff=abs(c42 - PUB_REF["cand_edge5_mean"]),
    cand_rankic_mean=i42, pub_rankic=PUB_REF["cand_rankic_mean"],
    abs_diff_rankic=abs(i42 - PUB_REF["cand_rankic_mean"]),
    baseline_fresh_edge5_all_pct=b42, pub_baseline=PUB_REF["baseline_fresh_edge5_all_pct"],
    abs_diff_baseline=abs(b42 - PUB_REF["baseline_fresh_edge5_all_pct"]),
    fresh_vs_frozen_max_abs=fvf42,
)
out["C6_pass"] = bool(
    abs(c42 - PUB_REF["cand_edge5_mean"]) <= 1e-9
    and abs(i42 - PUB_REF["cand_rankic_mean"]) <= 1e-9
    and abs(b42 - PUB_REF["baseline_fresh_edge5_all_pct"]) <= 1e-9
    and fvf42 == 0.0)

# ---- per-seed: CONFIRM + SELECT ----
rows = []
for s in SEEDS:
    row = {"seed": s}
    for variant, label in (("candidate_vs_fresh", "cand"), ("noise_vs_fresh", "noise")):
        for kind in ("edge5", "rankic"):
            conf = block_ci_diff(per_seed(variant, kind, SELECT_N, SELECT_N + CONFIRM_N - 1)[s], k=K)
            sel = block_ci_diff(per_seed(variant, kind, 0, SELECT_N - 1)[s], k=K)
            row[f"{label}_{kind}_confirm"] = conf
            row[f"{label}_{kind}_select"] = sel
            row[f"{label}_{kind}_confirm_verdict"] = verdict(conf)
    fvf = block_ci_diff(per_seed("fresh_vs_frozen", "edge5", SELECT_N, SELECT_N + CONFIRM_N - 1)[s], k=1)
    fvf_ic = block_ci_diff(per_seed("fresh_vs_frozen", "rankic", SELECT_N, SELECT_N + CONFIRM_N - 1)[s], k=1)
    row["fresh_vs_frozen_edge5_confirm"] = fvf
    row["fresh_vs_frozen_rankic_confirm"] = fvf_ic
    # doi chieu cheo: mean tinh lai tu diff PHAI khop json cua kernel
    row["xcheck_cand_edge5_json"] = js[s]["candidate_vs_fresh"]["confirm_edge5_ci"]["mean"]
    row["xcheck_cand_edge5_recomputed"] = row["cand_edge5_confirm"]["mean"]
    row["xcheck_ok"] = bool(abs(row["xcheck_cand_edge5_json"] - row["xcheck_cand_edge5_recomputed"]) <= 1e-12)
    row["xcheck_cand_rankic_json"] = js[s]["candidate_vs_fresh"]["confirm_rankic_ci"]["mean"]
    row["xcheck_cand_rankic_recomputed"] = row["cand_rankic_confirm"]["mean"]
    row["xcheck_rankic_ok"] = bool(
        abs(row["xcheck_cand_rankic_json"] - row["xcheck_cand_rankic_recomputed"]) <= 1e-12)
    row["json_final_verdict"] = js[s]["final_verdict"]
    row["json_n_oos"] = js[s]["candidate_vs_fresh"]["n_oos"]
    row["json_n_ticks"] = js[s]["candidate_vs_fresh"]["n_ticks"]
    row["json_noise_vs_fresh_confirm_exceeds"] = js[s]["noise_vs_fresh_confirm_exceeds"]
    row["ofi_coverage_frac"] = js[s]["ofi_coverage_frac"]
    rows.append(row)
out["per_seed"] = rows

# ---- pooled: trung binh THEO TICK tren 3 seed MOI, roi CUNG block_ci_diff voi k=3 ----
pooled = {}
for variant, label in (("candidate_vs_fresh", "cand"), ("noise_vs_fresh", "noise")):
    for kind in ("edge5", "rankic"):
        st = per_seed(variant, kind, SELECT_N, SELECT_N + CONFIRM_N - 1)
        p = pd.concat([st[s].rename(s) for s in NEW], axis=1).mean(axis=1)
        pooled[f"{label}_{kind}_confirm"] = block_ci_diff(p, k=K)
        pooled[f"{label}_{kind}_confirm_verdict"] = verdict(pooled[f"{label}_{kind}_confirm"])
        st = per_seed(variant, kind, 0, SELECT_N - 1)
        p = pd.concat([st[s].rename(s) for s in NEW], axis=1).mean(axis=1)
        pooled[f"{label}_{kind}_select"] = block_ci_diff(p, k=K)
out["pooled_new_seeds"] = pooled

# ---- C1..C4 verdict ----
noise_ok = all(r["noise_edge5_confirm"]["contains_zero"] for r in rows)
c2 = pooled["cand_edge5_confirm"]
n_pos = sum(1 for r in rows if r["seed"] in NEW and r["cand_edge5_confirm"]["mean"] > 0)
n_ci = sum(1 for r in rows if r["seed"] in NEW and not r["cand_edge5_confirm"]["contains_zero"])
n_ci_ic = sum(1 for r in rows if r["seed"] in NEW and not r["cand_rankic_confirm"]["contains_zero"])
c1 = noise_ok
c2_ok = (c2["mean"] > 0) and (not c2["contains_zero"])
c3_ok = (n_pos >= 2) and (n_ci >= 2)
c3_ic_ok = n_ci_ic >= 2
if not c1:
    v = "FAIL — HARNESS_NGHI_NGO"
elif c2_ok and c3_ok and out["C5_all_pass"] and out["C6_pass"]:
    v = "PASS (multi-seed xac nhan) — CHI LA UNG VIEN, khong tich hop/deploy"
elif (not c2_ok) or (n_ci < 2):
    v = "FAIL — dong truc OFI"
else:
    v = "FAIL — khac (xem chi tiet)"
out["criteria"] = dict(
    C1_noise_null_all_seeds=bool(c1),
    C2_pooled_ok=bool(c2_ok), C2_mean=c2["mean"], C2_ci=[c2["lo"], c2["hi"]],
    C3_n_new_seed_positive=int(n_pos), C3_n_new_seed_ci_excl0=int(n_ci),
    C3_rankic_n_new_seed_ci_excl0=int(n_ci_ic),
    C3_ok=bool(c3_ok), C3_rankic_ok=bool(c3_ic_ok),
    C4_rankic_pooled_ok=bool(pooled["cand_rankic_confirm"]["mean"] > 0
                            and not pooled["cand_rankic_confirm"]["contains_zero"]),
    C5_all_pass=out["C5_all_pass"], C6_pass=out["C6_pass"],
)
out["VERDICT"] = v
out["noise_seed_noise_floor_note"] = (
    "fresh_vs_frozen != 0 o seed 43/44/45 la DUONG NHIEN (khac model seed) — bao nhu NEN NHIEU SEED, "
    "khong phai tieu chi pass/fail; chi seed 42 phai = 0 tuyet doi (C6).")
print(json.dumps(out, indent=2, default=str))
