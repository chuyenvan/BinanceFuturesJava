"""E1 loader memory probe - build ONE month of 2024 and (optionally) write it.

The measured command is the documented one:

    systemd-run --user --scope -q -p MemoryMax=3G -p MemorySwapMax=1G \
        /usr/bin/time -v python3 e1_load_probe.py --month 2024-01

`--month 2024-01` runs the whole e1_core.build path (metrics5m + funding +
kline/basis for that month, panel + dayvol) with **no** write, so the peak RSS
reported by `/usr/bin/time -v` ("Maximum resident set size (kbytes)") is the
loader's, not the writer's. `--write` saves the month to ~/vz_e1/work (never to
~/vz_e1/out, so the canonical 2024 files are never touched).

`--compare` is a SEPARATE invocation: it reads the written probe month and the
canonical ~/vz_e1/out/e1_{events,panel}_2024.parquet rows of the same month and
prints the event-set / feature identity check. Kept out of the measured run so
the comparison's own memory does not pollute the peak.
"""
import argparse
import gc
import os

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import e1_core
from e1_common import OUT, WORK, ensure_dirs, setup_logging

log = setup_logging("e1_load_probe", "e1_load_probe.log")

# columns compared for identity; sym_age_days/age_known are deliberately EXCLUDED
# (they depend on how many months the caller scans for first_seen, not on the loader)
EVENT_COLS = ["sym", "ts", "open", "close", "high", "low", "quote_volume",
              "taker_sell_share", "tss_5", "tss_15", "volz60",
              "ret_pre_15", "ret_pre_60", "ret_pre_240", "prem_close", "prem_z7",
              "mark_index_gap", "gross_15", "gross_60", "gross_240",
              "mfe_60", "mae_60", "mfe_240", "mae_240",
              "oi", "oi_value", "doi_15", "doi_60", "funding_rate",
              "mins_to_funding", "btc_ret_15", "btc_ret_60", "bucket"]
PANEL_COLS = ["sym", "ts", "off", "ret_cum", "prem_close", "volz60", "tss", "doi_cum"]


def probe_paths(month, kind):
    return os.path.join(WORK, "probe_%s_%s.parquet" % (kind, month))


def build_month(month, write=False):
    ensure_dirs()
    ev, panel, dayvol = e1_core.build([month])
    log.info("month %s: events=%d panel=%d dayvol=%d", month, len(ev), len(panel), len(dayvol))
    print("PROBE month=%s events=%d panel=%d dayvol=%d" % (month, len(ev), len(panel), len(dayvol)))
    if write:
        for kind, df in (("events", ev), ("panel", panel), ("dayvol", dayvol)):
            p = probe_paths(month, kind)
            pq.write_table(pa.Table.from_pandas(df, preserve_index=False), p, compression="zstd")
            print("PROBE wrote %s rows=%d" % (p, len(df)))
    del ev, panel, dayvol
    gc.collect()


def _month_slice(path, month, columns):
    lo, hi = e1_core.month_bounds(month)
    t = pq.read_table(path, columns=columns,
                      filters=[("ts", ">=", lo), ("ts", "<", hi)]).to_pandas()
    return t


def compare_month(month):
    """Compare the written probe month against the canonical 2024 files."""
    evp = pd.read_parquet(probe_paths(month, "events"))
    out_months = sorted(set(evp.month.astype(str)))
    can = _month_slice(os.path.join(OUT, "e1_events_2024.parquet"), month, EVENT_COLS)
    probe = evp[EVENT_COLS].copy()
    out = {"month": month, "probe_months": out_months,
           "n_probe": int(len(probe)), "n_canon": int(len(can))}
    k = ["sym", "ts"]
    a = probe.sort_values(k, kind="stable").reset_index(drop=True)
    b = can.sort_values(k, kind="stable").reset_index(drop=True)
    a["sym"] = a.sym.astype(str)
    b["sym"] = b.sym.astype(str)
    m = a.merge(b, on=k, how="outer", suffixes=("_new", "_canon"), indicator=True)
    out["event_set_identical"] = bool((m._merge == "both").all())
    out["missing_new"] = int((m._merge == "right_only").sum())
    out["missing_canon"] = int((m._merge == "left_only").sum())
    both = m[m._merge == "both"]
    worst = {}
    for c in EVENT_COLS:
        if c in k:
            continue
        x = both[c + "_new"].to_numpy(np.float64)
        y = both[c + "_canon"].to_numpy(np.float64)
        fin = np.isfinite(x) & np.isfinite(y)
        d = float(np.max(np.abs(x[fin] - y[fin]))) if fin.any() else 0.0
        nan_mis = int((np.isfinite(x) != np.isfinite(y)).sum())
        if d > 0 or nan_mis:
            worst[c] = {"max_abs_diff": d, "nan_mismatch": nan_mis}
    out["event_col_diffs"] = worst

    pan = pd.read_parquet(probe_paths(month, "panel"))
    cap = _month_slice(os.path.join(OUT, "e1_panel_2024.parquet"), month, PANEL_COLS)
    pa_ = pan[PANEL_COLS].sort_values(["sym", "ts", "off"], kind="stable").reset_index(drop=True)
    cb = cap.sort_values(["sym", "ts", "off"], kind="stable").reset_index(drop=True)
    pa_["sym"] = pa_.sym.astype(str)
    cb["sym"] = cb.sym.astype(str)
    out["n_panel_probe"] = int(len(pa_))
    out["n_panel_canon"] = int(len(cb))
    if len(pa_) == len(cb):
        pdiff = {}
        for c in PANEL_COLS:
            if c in ("sym", "ts", "off"):
                continue
            x = pa_[c].to_numpy(np.float64)
            y = cb[c].to_numpy(np.float64)
            fin = np.isfinite(x) & np.isfinite(y)
            d = float(np.max(np.abs(x[fin] - y[fin]))) if fin.any() else 0.0
            nan_mis = int((np.isfinite(x) != np.isfinite(y)).sum())
            if d > 0 or nan_mis:
                pdiff[c] = {"max_abs_diff": d, "nan_mismatch": nan_mis}
        out["panel_keys_identical"] = bool(
            (pa_[["sym", "ts", "off"]].values == cb[["sym", "ts", "off"]].values).all())
        out["panel_col_diffs"] = pdiff
    else:
        out["panel_keys_identical"] = False
        out["panel_col_diffs"] = "row count differs"

    # dayvol: full symbol x day grid (missing combos = 0.0), compared to canonical
    lo, hi = e1_core.month_bounds(month)
    can_dv = pd.read_parquet(os.path.join(OUT, "e1_dayvol_2024.parquet"))
    can_dv = can_dv[(can_dv.day >= lo // 86_400_000) & (can_dv.day < hi // 86_400_000)]
    dv = pd.read_parquet(probe_paths(month, "dayvol")).sort_values(["sym", "day"]).reset_index(drop=True)
    can_dv = can_dv.sort_values(["sym", "day"]).reset_index(drop=True)
    dv["sym"] = dv.sym.astype(str)
    can_dv["sym"] = can_dv.sym.astype(str)
    out["n_dayvol_probe"] = int(len(dv))
    out["n_dayvol_canon"] = int(len(can_dv))
    if len(dv) == len(can_dv):
        keys_same = bool((dv[["sym", "day"]].values == can_dv[["sym", "day"]].values).all())
        x = dv.quote_volume.to_numpy(np.float64)
        y = can_dv.quote_volume.to_numpy(np.float64)
        out["dayvol_keys_identical"] = keys_same
        out["dayvol_max_abs_diff"] = float(np.max(np.abs(x - y))) if len(x) else 0.0
    else:
        out["dayvol_keys_identical"] = False
        out["dayvol_max_abs_diff"] = None
    out["pass"] = bool(out["event_set_identical"] and not out["event_col_diffs"]
                       and out.get("panel_keys_identical", False)
                       and not out.get("panel_col_diffs")
                       and out["dayvol_keys_identical"]
                       and (out["dayvol_max_abs_diff"] or 0.0) == 0.0)
    print("COMPARE " + str(out))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default="2024-01")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--compare", action="store_true",
                    help="compare written probe month vs canonical 2024 files (no build)")
    args = ap.parse_args()
    if args.compare:
        compare_month(args.month)
    else:
        build_month(args.month, write=args.write)


if __name__ == "__main__":
    main()
