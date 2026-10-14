"""VZ E1 - Q1 fee fix: recompute every net table (T3-T9) with the corrected fee model.

Q1: `SIM_RATE_FEE` (0.000982) is the ROUND-TRIP (2-leg) fee and the sim subtracts it
ONCE (OrderTargetInfoTest.calTp lines 282-283/285-286; Configs.java:103/185;
docs/result/RESULT_AUDIT_PNL.md:126). E1 used to add `2 * 0.000982` => double count.
`e1_common.cost_of` now adds the round-trip fee once.

Because the corrected cost is a UNIFORM shift (+RATE_FEE) of every net value, the
group SPREADS must be identical to the old ones (<= 1e-9); levels' mean/median/CI/hit
move by construction. This script:
  1. backs up reports + the net-bearing parquets,
  2. recomputes net_*/net_stress_* from gross_* + bucket with the fixed `cost_of`,
  3. re-runs the T3/T4/T5/T6/T9 report writers (ledger appends suppressed),
  4. asserts every spread/diff_mean matches the old value (<= 1e-9) and reports the
     shift, the scenarios table, and the used-fee constant.

Writes  reports/fee_recompute.json  (machine-checkable proof).
"""
import glob
import json
import os
import shutil

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import e1_ledger
import e1_t3
import e1_t4
import e1_t5
import e1_t6
import e1_t9
from e1_common import (FEE_ROUNDTRIP, OUT, RATE_FEE, REPORT, bucket_of, cost_of,
                       setup_logging, write_json)

log = setup_logging("e1_recompute_costs", "e1_recompute_costs.log")
BACK_OUT = os.path.join(OUT, "backup_pre_fee_fix")
BACK_REP = os.path.join(REPORT, "pre_fee_fix")
EVENTS = os.path.join(OUT, "e1_events_2024.parquet")
LEGS = os.path.join(OUT, "e1_t9_legs_2024.parquet")
NET1440 = os.path.join(OUT, "e1_t9_events_net1440.parquet")


def _recompute_frame(df, spec):
    """spec: list of (gross_col, net_col, stress). Returns max |new-old-RATE_FEE| over finite."""
    worst = 0.0
    for gross_col, net_col, stress in spec:
        if gross_col not in df.columns:
            raise SystemExit("recompute: missing %s" % gross_col)
        g = df[gross_col].to_numpy(np.float64)
        old = df[net_col].to_numpy(np.float64)
        new = g - np.array([cost_of(b, stress) for b in df.bucket], dtype=np.float64)
        fin = np.isfinite(old) & np.isfinite(new)
        if fin.any():
            worst = max(worst, float(np.max(np.abs((new - old)[fin] - RATE_FEE))))
        df[net_col] = new
    return worst


def recompute_parquets():
    os.makedirs(BACK_OUT, exist_ok=True)
    os.makedirs(BACK_REP, exist_ok=True)
    for p in (EVENTS, LEGS, NET1440) + tuple(glob.glob(os.path.join(REPORT, "*.json"))):
        d = BACK_OUT if p.endswith(".parquet") else BACK_REP
        dst = os.path.join(d, os.path.basename(p))
        if not os.path.exists(dst):
            shutil.copy2(p, dst)
    shift = {}
    # events: net_15/60/240 + stress
    ev = pd.read_parquet(EVENTS)
    spec = []
    for h in (15, 60, 240):
        spec += [("gross_%d" % h, "net_%d" % h, False),
                 ("gross_%d" % h, "net_stress_%d" % h, True)]
    shift["events"] = _recompute_frame(ev, spec)
    pq.write_table(pa.Table.from_pandas(ev, preserve_index=False), EVENTS, compression="zstd")
    # t9 legs: 60/240/exit
    lg = pd.read_parquet(LEGS)
    spec = []
    for tag in ("60", "240", "exit"):
        spec += [("gross_%s" % tag, "net_%s" % tag, False),
                 ("gross_%s" % tag, "net_stress_%s" % tag, True)]
    shift["legs"] = _recompute_frame(lg, spec)
    lg.to_parquet(LEGS, index=False)
    # t9 1440
    nr = pd.read_parquet(NET1440)
    shift["net1440"] = _recompute_frame(nr, [("gross_1440", "net_1440", False),
                                             ("gross_1440", "net_stress_1440", True)])
    nr.to_parquet(NET1440, index=False)
    log.info("recompute shifts (max |Δnet - RATE_FEE|) %s", shift)
    return shift


def collect_spreads(obj, path=""):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = "%s.%s" % (path, k)
            if k in ("diff_mean", "spread") and isinstance(v, (int, float)):
                out[p] = float(v)
            elif k.endswith("_spread_extreme") and isinstance(v, dict):
                for kk, vv in v.items():
                    if kk in ("diff_mean",) and isinstance(vv, (int, float)):
                        out[p + "." + kk] = float(vv)
            out.update(collect_spreads(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(collect_spreads(v, "%s[%d]" % (path, i)))
    return out


def main():
    log.info("Q1 fee fix: RATE_FEE=%s FEE_ROUNDTRIP=%s (was 2*RATE_FEE=%s)",
             RATE_FEE, FEE_ROUNDTRIP, 2 * RATE_FEE)
    e1_ledger.append = lambda rows, path=None: log.info(
        "ledger append suppressed (%d rows)", len(rows))
    shift = recompute_parquets()

    log.info("re-running T3/T4/T5/T6/T9 report writers")
    e1_t3.run()
    e1_t4.run()
    e1_t5.run()
    e1_t6.run()
    e1_t9.stats()

    # verify spreads invariant vs the backed-up (pre-fix) reports
    checks = {}
    worst = 0.0
    for name in ("e1_t3", "e1_t4", "e1_t5", "e1_t6", "e1_t9"):
        old = json.load(open(os.path.join(BACK_REP, "%s.json" % name)))
        new = json.load(open(os.path.join(REPORT, "%s.json" % name)))
        so, sn = collect_spreads(old), collect_spreads(new)
        if set(so) != set(sn):
            raise SystemExit("DUNG: spread key set changed for %s" % name)
        d = max((abs(so[k] - sn[k]) for k in so), default=0.0)
        checks[name] = {"n_spreads": len(so), "max_abs_diff": d}
        worst = max(worst, d)
    if worst > 1e-9:
        raise SystemExit("DUNG/BAO: spread khong trung ban cu (max=%.3e > 1e-9)" % worst)

    # fee scenario table: mean net of 2024 crash events at 60'/240'/24h
    ev = pd.read_parquet(EVENTS, columns=["sym", "ts", "bucket", "gross_60", "gross_240"])
    nr = pd.read_parquet(NET1440, columns=["sym", "ts", "gross_1440"])
    ev = ev.merge(nr, on=["sym", "ts"], how="left")
    cb = np.array([cost_of(b) for b in ev.bucket], dtype=np.float64)
    scen = {"sim_SIM_RATE_FEE": FEE_ROUNDTRIP, "taker_taker": 0.0010, "taker_taker_BNB": 0.0009,
            "maker_in_taker_out": 0.0007, "maker_in_taker_out_BNB": 0.00063,
            "old_double_2x0.000982": 2 * RATE_FEE}
    scen_tab = {}
    for tag, fee in scen.items():
        row = {}
        for h, col in ((60, "gross_60"), (240, "gross_240"), (1440, "gross_1440")):
            g = ev[col].to_numpy(np.float64)
            net = g - (cb - FEE_ROUNDTRIP) - fee   # bucket entry cost (real) + scenario fee
            fin = np.isfinite(net)
            row["net_%d_mean" % h] = float(net[fin].mean()) if fin.any() else None
            row["n_%d" % h] = int(fin.sum())
        scen_tab[tag] = row

    res = {"RATE_FEE": RATE_FEE, "FEE_ROUNDTRIP": FEE_ROUNDTRIP,
           "old_fee_2leg": 2 * RATE_FEE, "shift_max_dev": shift,
           "spread_checks": checks, "spread_max_abs_diff": worst,
           "fee_scenarios": scen_tab,
           "conclusion": "fee was double-counted (2x0.000982); now added once"}
    write_json(os.path.join(REPORT, "fee_recompute.json"), res)
    e1_ledger.append = e1_ledger.__dict__.get("_orig_append")
    log.info("fee_recompute.json written; worst spread diff=%.3e", worst)
    return res


if __name__ == "__main__":
    print(json.dumps(main(), indent=1, default=str))
