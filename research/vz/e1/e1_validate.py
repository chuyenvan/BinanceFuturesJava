"""VZ E1 - T1-V validation harness (b, c, d).

V-b  reproduce the EXEC legs ledger over 2024: VZ kline close at the leg minute
     must equal the ledger close_M (|d|/close <= 1e-6) in >= 99.5% of joined
     legs; also report the share of 2024 EXEC legs that fall on an E1 crash event.
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
    md5, legs = load_ledger_2024()
    log.info("ledger md5=%s legs2024=%d", md5, len(legs))
    key = {}
    for s, t in zip(legs.sym, legs.ts):
        key[(s, t)] = np.nan
    matched = 0
    close_delta = []
    for month in e1_core.MONTHS_2024:
        f = e1_data.kline_month(month)
        t = pq.read_table(f, columns=["ts", "sym", "close"]).to_pandas()
        t = t[t.sym.isin(set(legs.sym.unique()))]
        for s, ts, c in zip(t.sym.to_numpy(), t.ts.to_numpy(np.int64), t.close.to_numpy()):
            k = (s, int(ts))
            if k in key:
                key[k] = c
        del t
        e1_data.release(month)
        log.info("vb month %s scanned", month)
    legs["vz_close"] = [key.get((s, int(t)), np.nan)
                        for s, t in zip(legs.sym, legs.ts)]
    joined = legs[np.isfinite(legs.vz_close.to_numpy())]
    if len(joined):
        rel = (np.abs(joined.vz_close - joined.cM) / joined.cM).to_numpy()
        close_delta = rel
        frac_ok = float((rel <= 1e-6).mean())
    else:
        frac_ok = 0.0
    # share of 2024 legs on an E1 crash event
    evp = os.path.join(OUT, "e1_events_2024.parquet")
    on_event = 0
    if os.path.exists(evp):
        ev = pq.read_table(evp, columns=["sym", "ts"]).to_pandas()
        evset = set(zip(ev.sym.to_numpy(), ev.ts.to_numpy(np.int64)))
        on_event = int(sum(1 for s, t in zip(legs.sym, legs.ts) if (s, int(t)) in evset))
    out = {
        "ledger_md5": md5, "ledger_md5_prefix_ok": md5.startswith(LEDGER_MD5_PREFIX),
        "legs_2024": int(len(legs)),
        "joined": int(len(joined)),
        "joined_frac": float(len(joined) / len(legs)),
        "close_match_1e-6_frac": frac_ok,
        "close_match_1e-6_pass": bool(frac_ok >= 0.995),
        "legs_on_e1_crash_event": on_event,
        "legs_on_e1_crash_event_frac": float(on_event / len(legs)),
        "joined_missing": int(len(legs) - len(joined)),
    }
    write_json(os.path.join(REPORT, "e1_t1v_b_repro.json"), out)
    log.info("V-b %s", out)
    return out


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
