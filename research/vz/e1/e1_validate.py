"""VZ E1 - T1-V validation harness (b, c, d).

V-b  MASTER 2026-10-14 (supersedes the first V-b): the ledger's close_M is the
     Vision 1m bar whose OPEN time equals the leg's `s_ms` (ll_h2/exec_fetch.py
     kl + leadlag_add1.load_cm); the ledger's own `t_star` column is the HOUR
     floor of t_dec, not the event minute. V-b1 = price match >= 99.5% under that
     single written convention; V-b2 = >= 95% of EXEC legs whose VZ same-minute
     bar has bar_ret <= -1% must coincide with an E1 crash event. Implemented in
     e1_vb.py (run_vb here delegates to it).
V-c  run the core build twice and compare the output md5 (determinism).
V-d  crash events per month 2024 + bucket distribution (crash is always >= C1).
"""
import argparse
import gzip
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_core
import e1_data
from e1_common import LOG, OUT, REPORT, md5_file, setup_logging, write_json

log = setup_logging("e1_validate", "e1_validate.log")

LEDGER = os.path.expanduser("~/claude_master/1013/ll_h2/leadlag_h2_legs.csv.gz")
LEDGER_MD5_PREFIX = "e3a63b58"


def load_ledger_2024():
    md5 = md5_file(LEDGER)
    rows = []
    with gzip.open(LEDGER, "rt") as f:
        import csv
        for r in csv.DictReader(f):
            if r["year07"] == "2024":
                rows.append((r["sym"] + "USDT", int(r["t_star"]), float(r["cM"]),
                             float(r["br"]), r["level"]))
    df = pd.DataFrame(rows, columns=["sym", "ts", "cM", "br", "level"])
    return md5, df


def run_vb():
    """Delegate to e1_vb (MASTER 2026-10-14: V-b1 price + V-b2 timing)."""
    import e1_vb
    _, df = e1_vb.run()
    return e1_vb.run_b1b2(df)


def run_vc():
    md5s = []
    for i in range(2):
        r = subprocess.run([sys.executable, "e1_core.py", "--out-suffix", "_vc%d" % i],
                           cwd=os.path.dirname(os.path.abspath(__file__)),
                           capture_output=True, text=True)
        if r.returncode != 0:
            log.error("vc run %d failed: %s", i, r.stderr[-800:])
            return {"pass": False, "error": r.stderr[-800:]}
        md5s.append((md5_file(os.path.join(OUT, "e1_events_2024_vc%d.parquet" % i)),
                     md5_file(os.path.join(OUT, "e1_panel_2024_vc%d.parquet" % i))))
    ok = md5s[0] == md5s[1]
    out = {"pass": ok, "run0": md5s[0], "run1": md5s[1]}
    write_json(os.path.join(REPORT, "e1_t1v_c_determinism.json"), out)
    log.info("V-c %s", out)
    return out


def run_vd():
    ev = pq.read_table(os.path.join(OUT, "e1_events_2024.parquet"),
                       columns=["sym", "ts", "month", "bucket"]).to_pandas()
    per_month = ev.groupby("month").size().to_dict()
    buckets = ev.groupby("bucket").size().to_dict()
    names = {0: "NC", 1: "C1", 2: "C2", 3: "C4"}
    out = {"events_total": int(len(ev)),
           "per_month": {k: int(v) for k, v in per_month.items()},
           "bucket": {names[k]: int(v) for k, v in buckets.items()},
           "crash_always_ge_C1": int(buckets.get(0, 0)) == 0}
    write_json(os.path.join(REPORT, "e1_t1v_d_counts.json"), out)
    log.info("V-d %s", out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default="bd", help="subset of b,c,d")
    args = ap.parse_args()
    res = {}
    if "b" in args.what:
        res["b"] = run_vb()
    if "c" in args.what:
        res["c"] = run_vc()
    if "d" in args.what:
        res["d"] = run_vd()
    print(res)


if __name__ == "__main__":
    main()
