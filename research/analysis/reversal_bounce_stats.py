#!/usr/bin/env python3
"""REVERSAL_BOUNCE stats — edge/null/CI(block-72h x1.21)/ICC/MOM15-overlap + GO/NO-GO.

Doc signals.csv + rd15_*.npy tu reversal_bounce.py. Pure Python. Pre-reg: PREREG_REVERSAL_BOUNCE.md.
"""
import os
import json
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

OUT = "/tmp/reversal_bounce"
PRINTDONE = "/home/ubuntu/java/devrun/C2b/storage/printDone.csv"
SEED = 20260905
NREP = 2000
BLOCK_H = 72
CI_INFLATE_LEGACY = 1.21
RNG = np.random.default_rng(SEED)

UTC = timezone.utc


def min_of(y, mo, d):
    return int(datetime(y, mo, d, tzinfo=UTC).timestamp() // 60)


DEV_START = min_of(2022, 1, 1)
DEV_END = min_of(2024, 7, 1)


def block_boot(net, blk, nrep=NREP, seed=SEED, inflate=1.0):
    df = pd.DataFrame({"b": blk, "x": net})
    g = df.groupby("b")["x"]
    s = g.sum().values
    c = g.count().values
    nblk = len(s)
    rng = np.random.default_rng(seed)
    means = np.empty(nrep)
    for r in range(nrep):
        idx = rng.integers(0, nblk, nblk)
        means[r] = s[idx].sum() / c[idx].sum()
    lo, hi = np.percentile(means, [2.5, 97.5])
    obs = net.mean()
    half = (hi - lo) / 2.0 * inflate
    return {
        "obs": obs, "lo": lo, "hi": hi, "sd": means.std(),
        "p_gt0": float((means > 0).mean()),
        "ci_lo_infl": obs - half, "ci_hi_infl": obs + half,
        "mean_boot": means.mean(),
    }


def block_perm(net, blk, nrep=NREP, seed=SEED):
    """Block-respecting sign-flip null: flip sign of net at BLOCK level, p = P(null >= obs)."""
    blk = np.asarray(blk)
    net = np.asarray(net)
    bcode, binv = np.unique(blk, return_inverse=True)
    rng = np.random.default_rng(seed)
    obs = net.mean()
    null = np.empty(nrep)
    nblk = len(bcode)
    signs = rng.choice([-1.0, 1.0], size=(nrep, nblk))
    # block sums then signed total mean (vectorized): mean of net*sign[block] = (signs @ blocksums)/N
    bsum = np.bincount(binv, weights=net)
    N = len(net)
    null = (signs @ bsum) / N
    p = float((null >= obs).mean())
    return obs, null.mean(), null.std(), p


def icc(net, group_id):
    df = pd.DataFrame({"g": group_id, "x": net})
    grp = df.groupby("g")["x"]
    k = grp.count().values
    mi = grp.mean().values
    gm = net.mean()
    a = len(k)
    ni = len(net)
    msb = (k * (mi - gm) ** 2).sum() / (a - 1) if a > 1 else float("nan")
    within = net - df["g"].map(grp.mean()).values
    msw = (within ** 2).sum() / (ni - a) if ni > a else float("nan")
    k0 = (ni - (k ** 2).sum() / ni) / (a - 1) if a > 1 else float("nan")
    denom = msb + (k0 - 1) * msw
    return (msb - msw) / denom if denom != 0 else float("nan")


def main():
    df = pd.read_csv(OUT + "/signals.csv")
    rep = []
    rep.append("=== REVERSAL-BOUNCE LONG (fixed DROP_THRESH=0.01, HOLD 24h) ===")
    rep.append("raw fires=%d distinct_syms=%d" % (len(df), df["sym"].nunique()))
    df["end_min"] = df["entry_ts"] + 1440
    df["completed"] = df["hold_min"] >= 1440
    df["edge_censored"] = (~df["completed"]) & (df["end_min"] > min_of(2026, 1, 1))
    df["short_delist"] = (~df["completed"]) & (~df["edge_censored"])
    rep.append("completed24h=%d short_delist=%d edge_censored=%d" %
               (df["completed"].sum(), df["short_delist"].sum(), df["edge_censored"].sum()))
    use = df[~df["edge_censored"]].copy()
    rep.append("USED N=%d" % len(use))

    # blocks (72h) + day (GMT+7)
    use["blk"] = use["entry_ts"] // (BLOCK_H * 60)
    use["date"] = pd.to_datetime(use["entry_ts"] + 420, unit="m").dt.strftime("%Y-%m-%d")
    use["dayid"] = pd.factorize(use["date"])[0]
    use["is_dev"] = (use["entry_ts"] >= DEV_START) & (use["entry_ts"] < DEV_END)

    def summ(sub, label):
        n = len(sub)
        if n == 0:
            return "%s: N=0" % label
        net = sub["net_ret"].values
        r = block_boot(net, sub["blk"].values, inflate=1.0)
        rl = block_boot(net, sub["blk"].values, inflate=CI_INFLATE_LEGACY)
        wr = float((net > 0).mean())
        t = net.mean() / (net.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
        return ("%s: N=%d meanNet=%.4f%% meanRaw=%.4f%% winrate=%.1f%% t(iid)=%.2f "
                "CI72h=[%.4f%%,%.4f%%] p(mean>0)=%.3f | CI72h_x1.21=[%.4f%%,%.4f%%]" %
                (label, n, net.mean() * 100, sub["raw_ret"].mean() * 100, wr * 100, t,
                 r["lo"] * 100, r["hi"] * 100, r["p_gt0"],
                 rl["ci_lo_infl"] * 100, rl["ci_hi_infl"] * 100))

    rep.append("")
    rep.append("-- HEADLINE (net after fee 0.10%% + slip 0.5x-range + funding) --")
    rep.append(summ(use, "ALL 2021-2025"))
    rep.append(summ(use[use["is_dev"]], "DEV 2022-01..2024-06"))
    rep.append("")
    rep.append("-- Decay by year --")
    for yr in sorted(use["year"].unique()):
        rep.append(summ(use[use["year"] == yr], "Y%d" % yr))
    rep.append("")
    rep.append("-- %coin+ --")
    pm = use.groupby("sym")["net_ret"].agg(["mean", "count"])
    for mt in [1, 5, 10]:
        sub = pm[pm["count"] >= mt]
        if len(sub):
            rep.append("min_trades>=%d: nsym=%d %%coin+=%.1f%%" %
                       (mt, len(sub), (sub["mean"] > 0).mean() * 100))
    rep.append("")
    rep.append("-- delisting impact --")
    comp = use[use["completed"]]; deli = use[use["short_delist"]]
    rep.append("completed: N=%d meanNet=%.4f%% | short_delist: N=%d meanNet=%.4f%% (raw=%.4f%%)" %
               (len(comp), comp["net_ret"].mean() * 100, len(deli),
                deli["net_ret"].mean() * 100 if len(deli) else float("nan"),
                deli["raw_ret"].mean() * 100 if len(deli) else float("nan")))
    rep.append("")
    rep.append("-- Null test (block permutation 72h, seed %d) --" % SEED)
    obs, nm, ns, pv = block_perm(use["net_ret"].values, use["blk"].values)
    rep.append("obs mean=%.5f%% null mean=%.5f%% sd=%.5f%% p(>=obs)=%.4f" %
               (obs * 100, nm * 100, ns * 100, pv))
    rep.append("")
    rep.append("-- ICC (net_ret clustered) --")
    rep.append("ICC(day)=%.4f  ICC(72h block)=%.4f" %
               (icc(use["net_ret"].values, use["dayid"].values),
                icc(use["net_ret"].values, use["blk"].values)))
    rep.append("")

    # ---- MOM15 overlap ----
    rep.append("-- MOM15 overlap (primary: breadth rateDown15MAvg < -0.028 from raw 1M) --")
    umin = np.load(OUT + "/rd15_min.npy")
    rd15 = np.load(OUT + "/rd15_val.npy")
    # most recent 15m-aligned mark <= t
    t = use["entry_ts"].values.astype(np.int64)
    mark = t - ((t - 14) % 15)
    idx = np.searchsorted(umin, mark, side="right") - 1
    idx = np.clip(idx, 0, len(umin) - 1)
    mrd = rd15[idx]
    mom_fire = mrd < -0.028
    rep.append("rateDown15MAvg: %d 15m-points, min=%.4f max=%.4f" % (len(umin), rd15.min(), rd15.max()))
    rep.append("fires with MOM15 firing (<-0.028) at fire mark: %d (%.2f%%) | quiet: %d (%.2f%%)" %
               (int(mom_fire.sum()), 100 * mom_fire.mean(), int((~mom_fire).sum()),
                100 * (~mom_fire).mean()))
    rep.append(summ(use[~mom_fire], "edge on MOM15-QUIET"))
    rep.append(summ(use[mom_fire], "edge on MOM15-FIRING"))
    rep.append("")
    rep.append("-- MOM15 overlap (secondary: printDone C2b DEV day-level) --")
    try:
        pdn = pd.read_csv(PRINTDONE)
        pdn["sdt"] = pd.to_datetime(pdn["start"], format="%Y%m%d %H:%M", errors="coerce")
        pdn = pdn[pdn["sdt"].notna()]
        pdn["date"] = pdn["sdt"].dt.strftime("%Y-%m-%d")
        mom_days = set(pdn["date"].unique())
        mom_symday = set((r["sym"], r["date"]) for _, r in pdn.iterrows())
        fire_days = set(use["date"].unique())
        rep.append("MOM15 C2b: N=%d distinct_days=%d" % (len(pdn), len(mom_days)))
        rep.append("reversal fire-days=%d ; overlap with MOM15-days=%d (%.1f%% of fire-days)" %
                   (len(fire_days), len(fire_days & mom_days),
                    100 * len(fire_days & mom_days) / max(1, len(fire_days))))
        on_mom = use[use["date"].isin(mom_days)]
        off_mom = use[~use["date"].isin(mom_days)]
        rep.append("fires on MOM15-days=%d (%.1f%%) ; on MOM15-QUIET days=%d (%.1f%%)" %
                   (len(on_mom), 100 * len(on_mom) / len(use), len(off_mom),
                    100 * len(off_mom) / len(use)))
        use["symdate"] = list(zip(use["sym"], use["date"]))
        cotrade = use["symdate"].isin(mom_symday).sum()
        rep.append("same sym+day as a MOM15 entry: %d (%.2f%% of fires)" %
                   (cotrade, 100 * cotrade / len(use)))
    except Exception as e:
        rep.append("printDone parse error: %r" % e)

    txt = "\n".join(rep)
    open(OUT + "/report.txt", "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
