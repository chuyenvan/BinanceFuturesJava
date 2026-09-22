#!/usr/bin/env python3
"""BIGUP_MEDIUPDOWN stats — edge/null/CI(block-72h x1.21)/ICC/MOM15-overlap + GO/NO-GO theo level.

Doc /tmp/bigup_mediumdown/{signals.csv, bu_arrays.npz}. Thuan Python. Pre-reg: docs/PREREG_BIGUP_MEDIUPDOWN.md.
"""
import os
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

OUT = "/tmp/bigup_mediumdown"
PRINTDONE = "/home/ubuntu/java/devrun/C2b/storage/printDone.csv"
SEED = 20260905
NREP = 2000
BLOCK_H = 72
CI_INFLATE = 1.21
BASE = int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp() // 60)
DEV_START = int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp() // 60)
DEV_END = int(datetime(2024, 7, 1, tzinfo=timezone.utc).timestamp() // 60)
SAMPLE_END = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() // 60)
MOM15_THR = -0.028
LEVELS = ["BIG_UP", "MEDIUM_UP", "MEDIUM_DOWN", "BIG_DOWN_OLD"]


def block_boot(net, blk, inflate=1.0):
    g = pd.DataFrame({"b": blk, "x": net}).groupby("b")["x"]
    s = g.sum().values
    c = g.count().values
    nb = len(s)
    rng = np.random.default_rng(SEED)
    means = np.empty(NREP)
    for r in range(NREP):
        idx = rng.integers(0, nb, nb)
        means[r] = s[idx].sum() / c[idx].sum()
    lo, hi = np.percentile(means, [2.5, 97.5])
    obs = net.mean()
    half = (hi - lo) / 2.0 * inflate
    return {"obs": obs, "lo": lo, "hi": hi, "p_gt0": float((means > 0).mean()),
            "ci_lo": obs - half, "ci_hi": obs + half}


def block_perm(net, blk):
    bc, bi = np.unique(blk, return_inverse=True)
    rng = np.random.default_rng(SEED)
    signs = rng.choice([-1.0, 1.0], size=(NREP, len(bc)))
    bs = np.bincount(bi, weights=net)
    null = (signs @ bs) / len(net)
    return float(net.mean()), float(null.mean()), float(null.std()), float((null >= net.mean()).mean())


def icc(net, gid):
    df = pd.DataFrame({"g": gid, "x": net})
    grp = df.groupby("g")["x"]
    k = grp.count().values
    mi = grp.mean().values
    gm = net.mean()
    a = len(k)
    ni = len(net)
    if a < 2 or ni <= a:
        return float("nan")
    msb = (k * (mi - gm) ** 2).sum() / (a - 1)
    within = net - df["g"].map(grp.mean()).values
    msw = (within ** 2).sum() / (ni - a)
    k0 = (ni - (k ** 2).sum() / ni) / (a - 1)
    den = msb + (k0 - 1) * msw
    return (msb - msw) / den if den != 0 else float("nan")


def summarise(sub, label):
    n = len(sub)
    if n == 0:
        return "%s: N=0" % label
    net = sub["net"].values
    r = block_boot(net, sub["blk"].values, inflate=1.0)
    rl = block_boot(net, sub["blk"].values, inflate=CI_INFLATE)
    t = net.mean() / (net.std(ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    return ("%s: N=%d meanNet=%.4f%% meanRaw=%.4f%% win=%.1f%% t=%.2f CI72h=[%.4f%%,%.4f%%] "
            "p(>0)=%.3f CI72h_x1.21=[%.4f%%,%.4f%%]" % (
                label, n, net.mean() * 100, sub["raw"].mean() * 100, (net > 0).mean() * 100, t,
                r["lo"] * 100, r["hi"] * 100, r["p_gt0"], rl["ci_lo"] * 100, rl["ci_hi"] * 100))


def main():
    df = pd.read_csv(OUT + "/signals.csv")
    df = df.rename(columns={"net_ret": "net", "raw_ret": "raw"})
    arr = np.load(OUT + "/bu_arrays.npz")
    rd15 = arr["rd15"]
    rep = []
    rep.append("=== BIG_UP / MEDIUM_UP / MEDIUM_DOWN (code cu 157cf4d) + BIG_DOWN_OLD (reference) ===")
    rep.append("fires(raw)=%d syms=%d  by-level=%s" % (
        len(df), df["sym"].nunique(), dict(df["level_name"].value_counts())))

    df["end_min"] = df["entry_ts"] + 1440
    df["completed"] = df["hold"] >= 1440
    df["edge_censored"] = (~df["completed"]) & (df["end_min"] > SAMPLE_END - 1)
    df["short_delist"] = (~df["completed"]) & (~df["edge_censored"])
    rep.append("completed=%d short_delist=%d edge_censored=%d" %
               (df["completed"].sum(), df["short_delist"].sum(), df["edge_censored"].sum()))
    use = df[~df["edge_censored"]].copy()
    use["blk"] = use["entry_ts"] // (BLOCK_H * 60)
    use["date"] = pd.to_datetime(use["entry_ts"] + 420, unit="m").dt.strftime("%Y-%m-%d")
    use["dayid"] = pd.factorize(use["date"])[0]
    use["is_dev"] = (use["entry_ts"] >= DEV_START) & (use["entry_ts"] < DEV_END)
    # MOM15 fire at nearest 15m-aligned mark <= entry minute (primary)
    t = use["entry_ts"].values.astype(np.int64)
    mark = t - ((t - 14) % 15)
    idx = np.clip(mark - BASE, 0, len(rd15) - 1)
    mrd = rd15[idx]
    use["mom15"] = np.isfinite(mrd) & (mrd < MOM15_THR)

    # printDone day-level (secondary)
    pdn = None
    try:
        pdn = pd.read_csv(PRINTDONE)
        pdn["sdt"] = pd.to_datetime(pdn["start"], format="%Y%m%d %H:%M", errors="coerce")
        pdn = pdn[pdn["sdt"].notna()]
        pdn["date"] = pdn["sdt"].dt.strftime("%Y-%m-%d")
    except Exception as e:
        rep.append("printDone parse error: %r" % e)

    for lv in LEVELS:
        sub = use[use["level_name"] == lv].copy()
        rep.append("")
        rep.append("########## %s ##########" % lv)
        rep.append(summarise(sub, "ALL 2021-2025"))
        rep.append(summarise(sub[sub["is_dev"]], "DEV 2022-01..2024-06"))
        rep.append(summarise(sub[~sub["is_dev"]], "NON-DEV (2021 + 2024-07..2025-12)"))
        if len(sub) == 0:
            continue
        rep.append("-- by year --")
        for yr in sorted(sub["year"].unique()):
            rep.append("  " + summarise(sub[sub["year"] == yr], "Y%d" % yr))
        rep.append("-- %%coin+ --")
        pm = sub.groupby("sym")["net"].agg(["mean", "count"])
        for mt in (1, 5, 10):
            s2 = pm[pm["count"] >= mt]
            if len(s2):
                rep.append("  min_trades>=%d: nsym=%d %%coin+=%.1f%%" % (mt, len(s2), (s2["mean"] > 0).mean() * 100))
        rep.append("-- delist --")
        comp = sub[sub["completed"]]
        dl = sub[sub["short_delist"]]
        rep.append("  completed N=%d meanNet=%.4f%% | short_delist N=%d meanNet=%.4f%%" % (
            len(comp), comp["net"].mean() * 100 if len(comp) else float("nan"),
            len(dl), dl["net"].mean() * 100 if len(dl) else float("nan")))
        rep.append("-- null (block sign-flip 72h) --")
        o, nm, ns, pv = block_perm(sub["net"].values, sub["blk"].values)
        rep.append("  obs=%.5f%% nullMean=%.5f%% sd=%.5f%% p(>=obs)=%.4f" % (o * 100, nm * 100, ns * 100, pv))
        rep.append("-- ICC --")
        rep.append("  ICC(day)=%.4f ICC(72h)=%.4f" % (icc(sub["net"].values, sub["dayid"].values),
                                                      icc(sub["net"].values, sub["blk"].values)))
        rep.append("-- MOM15 overlap (primary: rd15<-0.028 at nearest 15m mark) --")
        mf = sub["mom15"].values
        rep.append("  MOM15-firing at fire mark: %d (%.2f%%) | quiet: %d (%.2f%%)" % (
            int(mf.sum()), 100 * mf.mean(), int((~mf).sum()), 100 * (~mf).mean()))
        rep.append("  " + summarise(sub[~mf], "edge MOM15-QUIET"))
        rep.append("  " + summarise(sub[mf], "edge MOM15-FIRING"))
        rep.append("-- onset subset (descriptive) --")
        srt = sub.sort_values(["sym", "entry_ts"])
        gap = srt.groupby("sym")["entry_ts"].diff().fillna(10 ** 9)
        onset = (gap > 1440).values
        rep.append("  " + summarise(srt[onset], "ONSET (first fire per sym after >=HOLD gap)"))
        if pdn is not None:
            rep.append("-- MOM15 overlap (secondary: printDone C2b day-level) --")
            mdays = set(pdn["date"].unique())
            msd = set(zip(pdn["sym"], pdn["date"]))
            fd = set(sub["date"].unique())
            on = sub[sub["date"].isin(mdays)]
            rep.append("  fire-days=%d overlap MOM15-days=%d (%.1f%%)" % (
                len(fd), len(fd & mdays), 100 * len(fd & mdays) / max(1, len(fd))))
            rep.append("  fires on MOM15-days=%d (%.1f%%) | same sym+day=%d (%.2f%%)" % (
                len(on), 100 * len(on) / len(sub),
                int(pd.Series(list(zip(sub["sym"], sub["date"]))).isin(msd).sum()),
                100 * pd.Series(list(zip(sub["sym"], sub["date"]))).isin(msd).mean()))

    txt = "\n".join(rep)
    open(OUT + "/report.txt", "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
