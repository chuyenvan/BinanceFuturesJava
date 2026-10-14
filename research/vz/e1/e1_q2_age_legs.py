"""VZ E1 - Q2: symbol-age filter on the system's EXEC legs (2024, <= 4 variants).

Data: `e1_t9_legs_2024.parquet` (6 709 legs). The legs file has no age column, so age
at entry is taken from E1: for matched legs (rep_ts>0) the event's exact `sym_age_days`;
for unmatched legs a proxy (s_ms - first 2024 event of that symbol)/day, with the same
`age_known` rule (symbol listed inside 2024). Groups: 0-7 / 8-30 / 31-90 / >90 days / unknown.

Variants (descriptive, no GO):
 1. net hold-to-exit by age group
 2. net 240' by age group
 3. drop legs with age <= 30d: sum/net per leg of dropped vs kept + share of total
 4. same with <= 7d
"""
import json
import os

import numpy as np
import pandas as pd

import e1_ledger
from e1_common import OUT, REPORT, SEED, setup_logging, write_json
from e1_stats import day_level_boot

log = setup_logging("e1_q2_age_legs", "e1_q2_age_legs.log")
LEGS = os.path.join(OUT, "e1_t9_legs_2024.parquet")
EVENTS = os.path.join(OUT, "e1_events_2024.parquet")
DATE = "2026-10-14"
DAY = 86_400_000


def age_of_legs(lg, ev):
    ev = ev[["sym", "ts", "sym_age_days", "age_known"]].copy()
    ev["ts"] = ev.ts.astype(np.int64)
    lg = lg.copy()
    lg["s_ms"] = lg.s_ms.astype(np.int64)
    fm = ev.loc[ev.groupby("sym")["ts"].idxmin(), ["sym", "ts", "age_known"]]
    fm = fm.rename(columns={"ts": "t0", "age_known": "known_sym"})
    lg = lg.merge(fm, on="sym", how="left")
    m = lg.rep_ts.to_numpy(np.int64) > 0
    age = np.full(len(lg), np.nan)
    known = np.zeros(len(lg), dtype=bool)
    # exact for matched legs (event at rep_ts)
    mm = lg.loc[m, ["sym", "rep_ts"]].rename(columns={"rep_ts": "ts"}).merge(
        ev, on=["sym", "ts"], how="left")
    age_exact = mm.sym_age_days.to_numpy(np.float64)
    known_exact = mm.age_known.to_numpy(bool)
    idx = np.where(m)[0]
    age[idx] = age_exact
    known[idx] = known_exact
    # proxy for unmatched legs
    um = ~m
    t0 = lg.t0.to_numpy(np.float64)
    age[um] = (lg.s_ms.to_numpy(np.float64)[um] - t0[um]) / DAY
    known[um] = lg.known_sym.to_numpy(bool)[um]
    lg["age_days"] = age
    lg["age_known"] = known
    lg["age_src"] = np.where(m, "exact_event", "proxy_first_event")
    return lg


def age_group(a, known):
    if not known or not np.isfinite(a):
        return "unknown"
    if a <= 7:
        return "0-7"
    if a <= 30:
        return "8-30"
    if a <= 90:
        return "31-90"
    return ">90"


def block(lg, col, groups):
    out = {}
    for g in groups:
        s = lg[lg.age_grp == g]
        v = s[col].to_numpy(np.float64)
        ok = np.isfinite(v)
        v = v[ok]
        days = s.day.to_numpy(np.int64)[ok]
        if v.size == 0:
            out[g] = {"n": 0}
            continue
        boot, _ = day_level_boot(v, days, np.ones(v.size, dtype=np.int64), seed=SEED)
        b = boot[1]
        out[g] = {"n": int(v.size), "mean": float(v.mean()), "median": float(np.median(v)),
                  "hit_rate": float((v > 0).mean()),
                  "ci95_mean": [float(b["ci95_mean"][0]), float(b["ci95_mean"][1])]}
    return out


def drop_variant(lg, thr, col="net_exit"):
    drop = (lg.age_days <= thr) & lg.age_known & np.isfinite(lg.age_days)
    keep = ~drop
    tot = float(np.nansum(lg[col].to_numpy(np.float64)))
    tot_d = float(np.nansum(lg.loc[drop, col].to_numpy(np.float64)))
    tot_k = float(np.nansum(lg.loc[keep, col].to_numpy(np.float64)))
    return {"threshold_days": thr, "legs_dropped": int(drop.sum()), "legs_kept": int(keep.sum()),
            "sum_net_dropped": tot_d, "sum_net_kept": tot_k, "sum_net_all": tot,
            "mean_net_dropped": tot_d / max(int(drop.sum()), 1),
            "mean_net_kept": tot_k / max(int(keep.sum()), 1),
            "share_sum_from_dropped": (tot_d / tot) if tot else None}


def run():
    lg = pd.read_parquet(LEGS)
    ev = pd.read_parquet(EVENTS, columns=["sym", "ts", "sym_age_days", "age_known", "day"])
    lg = age_of_legs(lg, ev)
    lg["age_grp"] = [age_group(a, k) for a, k in zip(lg.age_days, lg.age_known)]
    groups = ["0-7", "8-30", "31-90", ">90", "unknown"]
    res = {"n_legs": int(len(lg)),
           "n_age_exact": int((lg.age_src == "exact_event").sum()),
           "n_age_proxy": int((lg.age_src == "proxy_first_event").sum()),
           "n_age_known": int(lg.age_known.sum()),
           "groups": {g: int((lg.age_grp == g).sum()) for g in groups},
           "variant1_net_exit_by_age": block(lg, "net_exit", groups),
           "variant2_net_240_by_age": block(lg, "net_240", groups),
           "variant3_drop_le30_netexit": drop_variant(lg, 30),
           "variant4_drop_le7_netexit": drop_variant(lg, 7)}
    sub = lg[lg.age_known & (lg.age_days <= 30) & np.isfinite(lg.age_days)]
    res["share_sum_from_le30"] = res["variant3_drop_le30_netexit"]["share_sum_from_dropped"]
    res["n_le30_legs"] = int(len(sub))
    write_json(os.path.join(REPORT, "e1_q2_age_legs.json"), res)
    rows = [
        {"task": "Q2", "family": "H-E", "variant": "net_exit_by_age",
         "n": len(lg), "result": "means=%s" % {g: round(v.get("mean", float("nan")), 5)
                                               for g, v in res["variant1_net_exit_by_age"].items()
                                               if v.get("n")}, "date": DATE},
        {"task": "Q2", "family": "H-E", "variant": "net_240_by_age",
         "n": len(lg), "result": "means=%s" % {g: round(v.get("mean", float("nan")), 5)
                                               for g, v in res["variant2_net_240_by_age"].items()
                                               if v.get("n")}, "date": DATE},
        {"task": "Q2", "family": "H-E", "variant": "drop_le30_netexit",
         "n": res["variant3_drop_le30_netexit"]["legs_dropped"],
         "result": "shareSum=%.4f mean_dropped=%.5f mean_kept=%.5f" % (
             res["variant3_drop_le30_netexit"]["share_sum_from_dropped"] or float("nan"),
             res["variant3_drop_le30_netexit"]["mean_net_dropped"],
             res["variant3_drop_le30_netexit"]["mean_net_kept"]), "date": DATE},
        {"task": "Q2", "family": "H-E", "variant": "drop_le7_netexit",
         "n": res["variant4_drop_le7_netexit"]["legs_dropped"],
         "result": "shareSum=%.4f mean_dropped=%.5f mean_kept=%.5f" % (
             res["variant4_drop_le7_netexit"]["share_sum_from_dropped"] or float("nan"),
             res["variant4_drop_le7_netexit"]["mean_net_dropped"],
             res["variant4_drop_le7_netexit"]["mean_net_kept"]), "date": DATE},
    ]
    e1_ledger.append(rows)
    log.info("Q2 done n=%d groups=%s", len(lg), res["groups"])
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
