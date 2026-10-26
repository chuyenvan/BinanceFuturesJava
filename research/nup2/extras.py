#!/usr/bin/env python3
"""NUP2 extras: N_eff, entry/DCA split, validation counts tu printDone + log.
Usage: python3 extras.py <tag> [<tag> ...]  -> nup2_wk/extras.csv
Doc lap voi pipeline quarterly: chi pandas/numpy + CSV.
"""
import csv
import json
import os
import re
import sys

import numpy as np
import pandas as pd

KS = "/home/ubuntu/kaggle_sim/out/"
OUT = "/home/ubuntu/claude_master/nup2_wk/extras.csv"
YEARS = [2022, 2023, 2024, 2025]


def load(tag):
    d = pd.read_csv(KS + tag + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "pnl", "margin"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "quantity", "entry"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["ts"] = pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d["end"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["notional"] = d["quantity"] * d["entry"]
    return d


def cluster_frame(d):
    c = d.groupby(["sym", "te"], sort=False).agg(t0=("ts", "min"), pnl=("pnl", "sum"),
                                                  notional=("notional", "sum"), n=("sym", "size")).reset_index()
    return c.sort_values("t0")


def neff(c):
    t = c["t0"].sort_values().reset_index(drop=True)
    if not len(t):
        return {}
    grp = (t.diff() > pd.Timedelta(hours=6)).cumsum()
    g = pd.DataFrame({"t": t, "g": grp})
    out = {}
    for y in YEARS:
        gy = g[(g.t >= pd.Timestamp("%d-01-01" % y)) & (g.t < pd.Timestamp("%d-01-01" % (y + 1)))]
        out["neff_%d" % y] = int(gy.g.nunique())
        out["days_%d" % y] = int(gy.t.dt.date.nunique())
    out["neff"] = int(g.g.nunique())
    out["days_new"] = int(sum(out["days_%d" % y] for y in YEARS))
    return out


def daily(d, a="2022-01-01", b="2026-01-01"):
    z = d[(d.te >= pd.Timestamp(a)) & (d.te < pd.Timestamp(b))]
    return z.groupby(z.te.dt.date)["pnl"].sum()


def main(tags):
    rows = []
    for t in tags:
        d = load(t)
        c = cluster_frame(d)
        r = dict(tag=t, n_cl=len(c), n_leg=len(d))
        r.update(neff(c))
        # entry vs DCA
        d["is_entry"] = d["ts"].eq(d.groupby(["sym", "te"])["ts"].transform("min"))
        m = (d.te >= pd.Timestamp("2022-01-01")) & (d.te < pd.Timestamp("2026-01-01"))
        e = d[m]
        r["pnl_entry"] = float(e.loc[e.is_entry, "pnl"].sum())
        r["pnl_dca"] = float(e.loc[~e.is_entry, "pnl"].sum())
        r["n_entry_leg"] = int(e.is_entry.sum())
        r["n_dca_leg"] = int((~e.is_entry).sum())
        r["leg_per_cl_med"] = float(c.n.median())
        r["dca_per_cl_med"] = float((c.n - 1).median())
        r["cluster_notional_max"] = float(c.notional.max())
        r["cluster_notional_med"] = float(c.notional.median())
        leg0 = d[d.is_entry]
        r["leg0_notional_med"] = float(leg0.notional.median())
        dl = daily(d)
        r["pnl_days"] = float(dl.sum())
        r["top10_share"] = float(dl.nlargest(10).sum() / dl.sum()) if dl.sum() else np.nan
        # corr PnL ngay voi B0 cung seed
        seed = t.rsplit("-", 1)[-1]
        b0t = "tsx-x14-" + seed
        if os.path.exists(KS + b0t + "/storage/printDone.csv"):
            db = daily(load(b0t))
            j = pd.concat([dl.rename("a"), db.rename("b")], axis=1).fillna(0.0)
            r["corr_b0"] = float(j.a.corr(j.b)) if len(j) > 2 else np.nan
        else:
            r["corr_b0"] = np.nan
        # log counts
        lp = KS + t + "/logs/full.log"
        if not os.path.exists(lp):
            lp = KS + t + "/logs/sim.out"
        txt = open(lp, errors="ignore").read() if os.path.exists(lp) else ""
        mm = re.findall(r"skipFull=(\d+)", txt)
        r["skip_full"] = int(mm[-1]) if mm else np.nan
        gg = re.findall(r"GATE-RATIO on pct=\S+ days=\S+ seen=(\d+) pass=(\d+)", txt)
        r["gate_seen"] = int(gg[-1][0]) if gg else np.nan
        r["gate_pass"] = int(gg[-1][1]) if gg else np.nan
        # tier2
        f2 = KS + t + "/storage/tier2.csv"
        if os.path.exists(f2):
            t2 = pd.read_csv(f2, dtype=str)
            r["n_tier2"] = len(t2)
            key = set(zip(t2.sym.astype(str).str.strip().str.replace(r"USDT$", "", regex=True),
                       t2.start.astype(str).str.strip()))
            dk = d.assign(k=list(zip(d.sym, d.start.astype(str).str.strip())))
            r["pnl_tier2"] = float(dk[dk.k.isin(key)].pnl.sum())
        else:
            r["n_tier2"] = 0
            r["pnl_tier2"] = np.nan
        rows.append(r)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print("wrote", OUT, len(rows))


if __name__ == "__main__":
    main(sys.argv[1:])
