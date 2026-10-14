"""VZ E1 - shared statistics: day-level block bootstrap for grouped effects.

Block bootstrap by UTC day (block 5 days, NREP 2000, seed 20261014) as fixed by
the task rules. Returns per-replicate group means so callers can form spreads
(top-vs-bottom) with a proper CI.
"""
import numpy as np

from e1_common import BOOT_BLOCK_DAYS, BOOT_NREP, SEED


def day_level_boot(values, days, levels, block=BOOT_BLOCK_DAYS, nrep=BOOT_NREP,
                   seed=SEED):
    """values: per-observation stat; days: per-observation UTC day; levels: int array.

    Returns {level: {n, mean, median, hit_rate, ci95_mean, ci95_hit, reps_mean, reps_hit}}
    where reps_* are the per-replicate arrays (for spreads).
    """
    values = np.asarray(values, dtype=np.float64)
    days = np.asarray(days, dtype=np.int64)
    levels = np.asarray(levels, dtype=np.int64)
    uniq_days = np.unique(days)
    day_pos = {d: i for i, d in enumerate(uniq_days)}
    dps = np.array([day_pos[d] for d in days], dtype=np.int64)
    nd = len(uniq_days)
    uniq_lv = np.unique(levels)
    nlv = len(uniq_lv)
    lv_index = {lv: i for i, lv in enumerate(uniq_lv)}
    lpos = np.array([lv_index[l] for l in levels], dtype=np.int64)

    # per (day, level) sums / counts / hits
    flat = dps * nlv + lpos
    size = nd * nlv
    sums = np.bincount(flat, weights=values, minlength=size).reshape(nd, nlv)
    cnts = np.bincount(flat, minlength=size).reshape(nd, nlv).astype(np.float64)
    hits = np.bincount(flat, weights=(values > 0).astype(np.float64),
                       minlength=size).reshape(nd, nlv)

    blocks = [np.arange(i, min(i + block, nd)) for i in range(0, nd, block)]
    nb = len(blocks)
    rng = np.random.default_rng(seed)
    reps_mean = np.empty((nrep, nlv))
    reps_hit = np.empty((nrep, nlv))
    for r in range(nrep):
        pick = rng.integers(0, nb, size=nb)
        idx = np.concatenate([blocks[b] for b in pick])
        s = sums[idx].sum(axis=0)
        c = cnts[idx].sum(axis=0)
        h = hits[idx].sum(axis=0)
        reps_mean[r] = np.where(c > 0, s / np.maximum(c, 1), np.nan)
        reps_hit[r] = np.where(c > 0, h / np.maximum(c, 1), np.nan)

    out = {}
    for lv in uniq_lv:
        j = lv_index[lv]
        sel = levels == lv
        v = values[sel]
        out[int(lv)] = {
            "n": int(sel.sum()),
            "n_days": int(len(np.unique(days[sel]))),
            "mean": float(v.mean()) if v.size else np.nan,
            "median": float(np.median(v)) if v.size else np.nan,
            "hit_rate": float((v > 0).mean()) if v.size else np.nan,
            "ci95_mean": [float(np.nanpercentile(reps_mean[:, j], 2.5)),
                          float(np.nanpercentile(reps_mean[:, j], 97.5))],
            "ci95_hit": [float(np.nanpercentile(reps_hit[:, j], 2.5)),
                         float(np.nanpercentile(reps_hit[:, j], 97.5))],
            "reps_mean": reps_mean[:, j],
        }
    return out, uniq_lv


def spread_ci(boot, lo_level, hi_level):
    """top-minus-bottom difference with CI from the joint replicates."""
    a = boot[hi_level]["reps_mean"]
    b = boot[lo_level]["reps_mean"]
    d = a - b
    finite = np.isfinite(d)
    return {
        "diff_mean": float(np.nanmean(d)),
        "ci95": [float(np.nanpercentile(d[finite], 2.5)),
                 float(np.nanpercentile(d[finite], 97.5))] if finite.any() else [np.nan, np.nan],
        "excl_zero": bool(finite.any() and (np.nanpercentile(d[finite], 2.5) > 0
                                            or np.nanpercentile(d[finite], 97.5) < 0)),
    }


def monotonicity(level_means):
    """Spearman correlation of level index vs mean (1.0 = perfectly increasing)."""
    import scipy.stats as st  # optional; fall back to a simple hand calc
    x = np.arange(len(level_means), dtype=np.float64)
    y = np.asarray(level_means, dtype=np.float64)
    ok = np.isfinite(y)
    if ok.sum() < 3:
        return np.nan
    try:
        return float(st.spearmanr(x[ok], y[ok]).correlation)
    except Exception:
        rx = np.argsort(np.argsort(x[ok])).astype(float)
        ry = np.argsort(np.argsort(y[ok])).astype(float)
        rx -= rx.mean(); ry -= ry.mean()
        return float((rx * ry).sum() / np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))


def quantile_levels(values, nq):
    """Assign 1..nq by quantile of `values` (NaN -> 0)."""
    v = np.asarray(values, dtype=np.float64)
    lv = np.zeros(len(v), dtype=np.int64)
    ok = np.isfinite(v)
    if ok.sum() == 0:
        return lv, []
    edges = np.quantile(v[ok], np.linspace(0, 1, nq + 1)[1:-1])
    lv[ok] = np.searchsorted(edges, v[ok], side="right") + 1
    return lv, edges
