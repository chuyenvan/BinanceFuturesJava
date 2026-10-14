"""VZ E1 - T2 (H-A, descriptive profile, 0 hypothesis tests).

Profile around the crash minute (-60'..+240', step 5') of taker_sell_share,
volume z, prem z, cumulative dOI and cumulative price, split by EXEC bucket
(C1/C2/C4) and by whether BTC crashed too (BTC ret 15' <= -1%).
No thresholds are chosen here and no outcome is tested.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from e1_common import OUT, REPORT, setup_logging, write_json

log = setup_logging("e1_t2", "e1_t2.log")

METRICS = ["tss", "volz60", "prem_close", "doi_cum", "ret_cum"]
BUCKETS = {1: "C1", 2: "C2", 3: "C4"}


def profile(df, group_col, group_val, metric):
    sub = df[df[group_col] == group_val]
    g = sub.groupby("off")[metric]
    out = {}
    for off, s in g:
        v = s.to_numpy(dtype=np.float64)
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        out[int(off)] = {"n": int(v.size), "median": float(np.median(v)),
                         "q25": float(np.percentile(v, 25)),
                         "q75": float(np.percentile(v, 75)),
                         "mean": float(v.mean())}
    return out


def run():
    ev = pq.read_table(os.path.join(OUT, "e1_events_2024.parquet"),
                       columns=["sym", "ts", "bucket", "btc_ret_15"]).to_pandas()
    panel = pq.read_table(os.path.join(OUT, "e1_panel_2024.parquet")).to_pandas()
    ev["btc_crash"] = (ev.btc_ret_15 <= -0.01).fillna(False)
    df = panel.merge(ev[["sym", "ts", "bucket", "btc_crash"]], on=["sym", "ts"], how="left")
    res = {"overall": {}, "by_bucket": {}, "by_btc_crash": {}, "n_events": int(len(ev))}
    for m in METRICS:
        res["overall"][m] = profile(df.assign(g=1), "g", 1, m)
        for b, name in BUCKETS.items():
            res["by_bucket"].setdefault(name, {})[m] = profile(df, "bucket", b, m)
        for flag, name in ((True, "btc_crash"), (False, "btc_no_crash")):
            res["by_btc_crash"].setdefault(name, {})[m] = profile(df, "btc_crash", flag, m)
    write_json(os.path.join(REPORT, "e1_t2_profile.json"), res)

    lines = ["# VZ E1 - T2 (H-A) profile quanh phut sap (median, -60'..+240')",
             "", "n events = %d" % len(ev), ""]
    for m in METRICS:
        lines.append("## %s" % m)
        lines.append("")
        lines.append("| off | overall | C1 | C2 | C4 | BTC crash | BTC no-crash |")
        lines.append("|---|---|---|---|---|---|---|")
        for off in range(-60, 241, 5):
            row = [str(off)]
            for src, key in (("overall", None), ("by_bucket", "C1"), ("by_bucket", "C2"),
                             ("by_bucket", "C4"), ("by_btc_crash", "btc_crash"),
                             ("by_btc_crash", "btc_no_crash")):
                if src == "overall":
                    d = res["overall"][m].get(str(off)) or res["overall"][m].get(off)
                else:
                    d = res[src][key][m].get(str(off)) or res[src][key][m].get(off)
                row.append("%.4g" % d["median"] if d else "-")
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    with open(os.path.join(REPORT, "e1_t2_profile.md"), "w") as f:
        f.write("\n".join(lines))
    log.info("T2 done events=%d groups written", len(ev))
    return res


if __name__ == "__main__":
    run()
