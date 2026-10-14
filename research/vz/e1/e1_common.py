"""VZ E1 - shared helpers: paths, cost model, event bucket, bootstrap, IO.

Docs: docs/plan/VZ_E1_TASKS.md (Rules) and docs/plan/VZ_DATA_LAKE.md.
Only the 2024 VZ datasets plus vz-metrics5m/vz-funding(2024) are read; no other year.
Cost model mirrors the EXEC bucket measure (docs/result/EXEC_RESULT.md 6(a), class
com.binance.chuyennd.tradecore.EntryCost) + 2-leg fee from ho4p1-c2 (SIM_RATE_FEE).
"""
import hashlib
import json
import logging
import os
import sys

import numpy as np

# ---------------------------------------------------------------- paths
ROOT = os.path.expanduser("~/vz_e1")
RAW = os.path.join(ROOT, "raw")
WORK = os.path.join(ROOT, "work")
OUT = os.path.join(ROOT, "out")
REPORT = os.path.join(ROOT, "reports")
LOG = os.path.join(ROOT, "logs")

# Kaggle private datasets (owner chuyendinh), READ-ONLY for E1.
DS_KLINE = "chuyendinh/vz-kline1m-2024"
DS_BASIS = "chuyendinh/vz-basis1m-2024"
DS_METRICS = "chuyendinh/vz-metrics5m"
DS_FUNDING = "chuyendinh/vz-funding"

# EXEC entry-cost buckets by event-candle bar_ret (EntryCost.bucketOf, float32).
#   NC: bar_ret > -1% ; C1: -2% < bar_ret <= -1% ; C2: -4% < bar_ret <= -2% ; C4: <= -4%
BUCKET_NAMES = ("NC", "C1", "C2", "C4")
# real bucket costs (fraction of notional) as measured 2026-10-12 (ec_S_result.json)
BUCKET_COST = (0.0007, 0.0018, 0.0019, 0.0032)
# stress bucket costs (task spec)
BUCKET_COST_STRESS = (0.0023, 0.0033, 0.0041, 0.0101)
# 2-leg fee from ho4p1-c2 prof_run.properties (SIM_RATE_FEE)
RATE_FEE = 0.000982
FEE_2LEG = 2.0 * RATE_FEE

# event definition
CRASH_BAR_RET = -0.01          # close/open-1 <= -1%
MIN_QUOTE_VOLUME = 50_000.0    # USDT per minute
MERGE_GAP_MS = 30 * 60 * 1000  # merge same-symbol events closer than 30'
HORIZONS_MIN = (15, 60, 240)

BOOT_BLOCK_DAYS = 5
BOOT_NREP = 2000
SEED = 20261014

# symbol age threshold: pre-2024 listings are indistinguishable without vz-symbols
FIRST_TS_2024_MS = 1704067200000  # 2024-01-01T00:00:00Z
LAST_TS_2024_MS = 1735689600000   # 2025-01-01T00:00:00Z


def setup_logging(name, logfile=None):
    os.makedirs(LOG, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(logging.INFO)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        root.addHandler(sh)
    if logfile:
        target = os.path.abspath(os.path.join(LOG, logfile))
        have = any(isinstance(h, logging.FileHandler)
                   and os.path.abspath(getattr(h, "baseFilename", "")) == target
                   for h in root.handlers)
        if not have:
            fh = logging.FileHandler(target)
            fh.setFormatter(fmt)
            root.addHandler(fh)
    return logging.getLogger(name)


def ensure_dirs():
    for d in (RAW, WORK, OUT, REPORT, LOG):
        os.makedirs(d, exist_ok=True)


def bucket_of(close, open_):
    """EntryCost.bucketOf in float32 (matches Java bit-for-bit on the same inputs)."""
    c = np.float32(close)
    o = np.float32(open_)
    if o == 0 or not np.isfinite(c) or not np.isfinite(o):
        return 0
    bar_ret = np.float32(np.float32(c - o) / o)
    if not (bar_ret <= np.float32(-0.01)):
        return 0
    if bar_ret > np.float32(-0.02):
        return 1
    if bar_ret > np.float32(-0.04):
        return 2
    return 3


def cost_of(bucket, stress=False):
    """Round-trip cost (fraction) = bucket entry cost + 2-leg fee."""
    base = BUCKET_COST_STRESS if stress else BUCKET_COST
    return float(base[int(bucket)] + FEE_2LEG)


def md5_file(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def utc_day(ts_ms):
    return int(ts_ms) // 86_400_000


def block_bootstrap(values, days, block=BOOT_BLOCK_DAYS, nrep=BOOT_NREP, seed=SEED):
    """Block bootstrap by UTC day (blocks of `block` consecutive days, resampled).

    values: 1-D array of per-event statistic; days: 1-D int array of UTC day index
    aligned with values. Returns dict mean/median/ci95/hit_rate over the bootstrap
    distributions of the mean (and hit-rate); n = number of observations.
    """
    values = np.asarray(values, dtype=np.float64)
    days = np.asarray(days, dtype=np.int64)
    n = int(values.size)
    if n == 0:
        return {"n": 0}
    order = np.argsort(days, kind="stable")
    values = values[order]
    days = days[order]
    uniq, starts = np.unique(days, return_index=True)
    counts = np.diff(np.append(starts, n))
    # per-day arrays
    day_vals = [values[s:s + c] for s, c in zip(starts, counts)]
    n_days = len(uniq)
    blocks = [list(range(i, min(i + block, n_days))) for i in range(0, n_days, block)]
    nb = len(blocks)
    rng = np.random.default_rng(seed)
    means = np.empty(nrep)
    meds = np.empty(nrep)
    hits = np.empty(nrep)
    for r in range(nrep):
        pick = rng.integers(0, nb, size=nb)
        pool = []
        for b in pick:
            for d in blocks[b]:
                pool.append(day_vals[d])
        cat = np.concatenate(pool) if pool else np.array([0.0])
        means[r] = cat.mean()
        meds[r] = np.median(cat)
        hits[r] = (cat > 0).mean()
    return {
        "n": n,
        "n_days": n_days,
        "n_blocks": nb,
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "hit_rate": float((values > 0).mean()),
        "boot_mean": float(means.mean()),
        "ci95_mean": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
        "ci95_median": [float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))],
        "ci95_hit": [float(np.percentile(hits, 2.5)), float(np.percentile(hits, 97.5))],
    }


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=False, default=str)
