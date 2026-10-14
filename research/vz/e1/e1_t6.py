"""VZ E1 - T6 (H-E, symbol age, <= 8 variants).

(a) crash events by symbol age (0-7 / 8-30 / 31-90 / >90 days) - only events
    whose age is exact (symbol first seen inside 2024); pre-2024 listings are
    reported as a separate `age_unknown` group (vz-symbols is not uploaded yet).
(b) unconditional drift over the first 30 days after a 2024 listing
    (1/3/7/30 days).
(c) the last ~30 days before removal, approximated by the last month-on-month
    close snapshot - descriptive, survivorship caveat stated.
"""
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_ledger
from e1_common import OUT, REPORT, SEED, setup_logging, write_json
from e1_stats import day_level_boot

log = setup_logging("e1_t6", "e1_t6.log")
DATE = "2026-10-14"
YEAR_END = 1735689600000


def _boot(vals, days):
    vals = np.asarray(vals, dtype=np.float64)
    days = np.asarray(days, dtype=np.int64)
    if len(vals) == 0:
        return {"n": 0}
    boot, _ = day_level_boot(vals, days, np.ones(len(vals), dtype=np.int64), seed=SEED)
    b = boot[1]
    return {"n": int(b["n"]), "mean": b["mean"], "median": b["median"],
            "hit_rate": b["hit_rate"], "ci95_mean": b["ci95_mean"]}


def run():
    ev = pq.read_table(os.path.join(OUT, "e1_events_2024.parquet"),
                       columns=["sym", "ts", "day", "sym_age_days", "age_known",
                                "net_60", "net_240", "bucket"]).to_pandas()
    res = {}

    # (a) crash by age
    a = {"buckets": {}}
    exact = ev[ev.age_known]
    edges = [0, 7, 30, 90, 1e9]
    names = ["0-7d", "8-30d", "31-90d", ">90d"]
    lv = np.zeros(len(ev), dtype=np.int64)
    bucket_names = []
    for i in range(4):
        m = (exact.sym_age_days > edges[i]) & (exact.sym_age_days <= edges[i + 1])
        a["buckets"][names[i]] = {
            "n": int(m.sum()),
            "net_60": _boot(exact.loc[m, "net_60"].to_numpy(), exact.loc[m, "day"].to_numpy()),
            "net_240": _boot(exact.loc[m, "net_240"].to_numpy(), exact.loc[m, "day"].to_numpy()),
            "bucket_dist": exact.loc[m, "bucket"].value_counts().to_dict(),
        }
    a["age_unknown"] = {
        "n": int((~ev.age_known).sum()),
        "note": "sym first ts = 2024-01-01 (listed on/before 2024) - age not exact",
        "net_60": _boot(ev.loc[~ev.age_known, "net_60"].to_numpy(),
                        ev.loc[~ev.age_known, "day"].to_numpy()),
    }
    res["a_crash_by_age"] = a

    # (b) listing drift
    dpath = os.path.join(OUT, "e1_listing_drift.parquet")
    b = {}
    if os.path.exists(dpath):
        dr = pq.read_table(dpath).to_pandas()
        dr["day0"] = (dr.t0 // 86_400_000).astype(np.int64)
        b["n_symbols"] = int(dr.sym.nunique())
        for h in sorted(dr.h_days.unique()):
            s = dr[dr.h_days == h]
            b["%dd" % int(h)] = _boot(s.ret.to_numpy(), s.day0.to_numpy())
        res["b_listing_drift"] = b

    # (c) pre-delisting, month snapshots
    spath = os.path.join(OUT, "e1_month_snap.parquet")
    c = {}
    if os.path.exists(spath):
        snap = pq.read_table(spath).to_pandas().sort_values(["sym", "month"])
        rows = []
        for sym, g in snap.groupby("sym", sort=False):
            last = g.iloc[-1]
            if last.last_ts < YEAR_END - 86_400_000:      # removed during 2024
                if len(g) >= 2 and g.iloc[-2].close_last > 0:
                    r = last.close_last / g.iloc[-2].close_last - 1.0
                    rows.append((sym, last.month, r))
        c["n_removed"] = len(rows)
        if rows:
            df = pd.DataFrame(rows, columns=["sym", "last_month", "ret_30d"])
            c["ret_30d_mean"] = float(df.ret_30d.mean())
            c["ret_30d_median"] = float(df.ret_30d.median())
            c["ret_30d_frac_neg"] = float((df.ret_30d < 0).mean())
            c["note"] = "approx: last month-on-month close snapshot; survivorship caveat"
        res["c_predelist"] = c

    write_json(os.path.join(REPORT, "e1_t6.json"), res)
    rows = []
    for name in names:
        bb = a["buckets"][name]
        rows.append({"task": "T6", "family": "H-E", "variant": "age_%s" % name, "n": bb["n"],
                     "result": "net60 mean=%.5f CI=%s" % (bb["net_60"].get("mean", float("nan")),
                                                          bb["net_60"].get("ci95_mean", "n/a"))
                     if bb["n"] else "no events", "date": DATE})
    rows.append({"task": "T6", "family": "H-E", "variant": "age_unknown", "n": a["age_unknown"]["n"],
                 "result": "net60 mean=%.5f" % a["age_unknown"]["net_60"].get("mean", float("nan"))
                 if a["age_unknown"]["n"] else "no events", "date": DATE})
    for h in ("1d", "3d", "7d", "30d"):
        if h in b:
            rows.append({"task": "T6", "family": "H-E", "variant": "listing_drift_%s" % h,
                         "n": b[h]["n"], "result": "mean=%.5f CI=%s" % (b[h]["mean"], b[h]["ci95_mean"]),
                         "date": DATE})
    if c.get("n_removed"):
        rows.append({"task": "T6", "family": "H-E", "variant": "predelist_30d",
                     "n": c["n_removed"], "result": "median=%.5f" % c["ret_30d_median"],
                     "date": DATE})
    e1_ledger.append(rows)
    log.info("T6 done rows=%d", len(rows))
    return res


if __name__ == "__main__":
    run()
