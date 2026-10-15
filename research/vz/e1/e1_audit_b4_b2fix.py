"""VZ AUDIT B4 - B2 fix: 1000 random events/year, close(ts+1440') read by hand.

The first B2 checker (e1_audit_b4_events.b2_outcome_check) reported false
mismatches for two reasons: it cached the "next month" frame by month only (so a
second symbol of the same month reused a frame loaded for another symbol), and it
read the calendar next month even when ts+1440' stays inside the event's own
month. Here each sampled event is looked up in its own month first, then in the
following month, and an event whose ts+1440' leaves the year is required to be
NaN in the runner (pre-reg: never read the next year).

Writes ~/vz_e1/reports/audit_b4_b2.json. Read-only (parquet reads only).
"""
import json
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_data
from e1_common import OUT, REPORT, setup_logging, write_json

log = setup_logging("e1_audit_b4_b2", "e1_audit_b4_b2.log")
H1440 = 1440 * 60_000
YEARS = [2022, 2023, 2024, 2025]
N = 1000
SEED = 20261015


def next_month(m):
    y, mm = int(m[:4]), int(m[5:7])
    return "%04d-%02d" % ((y + 1, 1) if mm == 12 else (y, mm + 1))


def month_symbols(month, syms, cache):
    """{sym: (ts, close)} for one month, one parquet read for all needed symbols."""
    need = sorted(set(syms) - set(cache.get(month, {})))
    if need:
        path = e1_data.month_path(month, "kline", fetch=True)
        t = pq.read_table(path, columns=["ts", "sym", "close"]).to_pandas()
        # `sym` arrives dictionary-encoded (pandas categorical): groupby(observed=False)
        # would emit an EMPTY group per unused category, so force observed=True.
        t["sym"] = t["sym"].astype(str)
        t = t[t.sym.isin(set(need))]
        d = cache.setdefault(month, {})
        for s, g in t.groupby("sym", sort=False, observed=True):
            d[str(s)] = (g.ts.to_numpy(np.int64), g.close.to_numpy(np.float64))
    return cache.get(month, {})


def check_year(year, cache):
    ev = pd.read_parquet(os.path.join(OUT, "audit_b4_events_%d.parquet" % year))
    rng = np.random.default_rng(SEED + year)
    idx = rng.choice(len(ev), size=min(N, len(ev)), replace=False)
    samp = ev.iloc[idx]
    months = sorted(set(samp.month.astype(str)))
    for m in months:
        s_m = set(samp[samp.month.astype(str) == m].sym.astype(str))
        month_symbols(m, s_m, cache)
        nm = next_month(m)
        if int(nm[:4]) == year:  # only the intra-year following month is in scope
            s_nm = set(samp[samp.month.astype(str) == m].sym.astype(str))
            month_symbols(nm, s_nm, cache)
    diffs, no24, cross_year, checked = [], 0, 0, 0
    for r in samp.itertuples(index=False):
        s, ts, m = str(r.sym), int(r.ts), str(r.month)
        checked += 1
        tsa, ca = month_symbols(m, [s], cache)[s]
        j0 = int(np.searchsorted(tsa, ts))
        c0 = ca[j0] if j0 < len(tsa) and tsa[j0] == ts else np.nan
        t1 = ts + H1440
        rec = None
        tsa, ca = month_symbols(m, [s], cache)[s]
        j1 = int(np.searchsorted(tsa, t1))
        if j1 < len(tsa) and tsa[j1] == t1:
            rec = ca[j1]
        else:
            m1 = next_month(m)
            if int(m1[:4]) != year:
                cross_year += 1
                if np.isfinite(r.gross_1440):
                    raise SystemExit("B2 FAIL: runner read the next year %s %d" % (s, ts))
                continue
            tsb, cb = month_symbols(m1, [s], cache)[s]
            j1 = int(np.searchsorted(tsb, t1))
            if j1 < len(tsb) and tsb[j1] == t1:
                rec = cb[j1]
        if rec is None or not (np.isfinite(c0) and c0 > 0 and rec > 0):
            if np.isfinite(r.gross_1440):
                raise SystemExit("B2 FAIL: runner finite, hand read missing %s %d" % (s, ts))
            no24 += 1
            continue
        g = float(np.log(rec / c0))
        if not np.isfinite(r.gross_1440):
            raise SystemExit("B2 FAIL: runner NaN, hand read finite %s %d" % (s, ts))
        diffs.append(abs(g - float(r.gross_1440)))
    d = np.array(diffs) if diffs else np.array([0.0])
    return {"year": year, "n_checked": checked, "n_compared": int(d.size),
            "n_no_24h_both": no24, "n_cross_year_runner_nan_ok": cross_year,
            "max_abs_diff_gross_1440": float(d.max()), "n_diff_gt_1e-12": int((d > 1e-12).sum()),
            "pass": bool(d.max() == 0.0)}


def main():
    cache = {}
    res = {str(y): check_year(y, cache) for y in YEARS}
    res["seed"] = SEED
    res["pass_all"] = bool(all(v["pass"] for k, v in res.items() if k.isdigit()))
    write_json(os.path.join(REPORT, "audit_b4_b2.json"), res)
    log.info("B2 maxdiff=%s pass_all=%s",
             {k: v["max_abs_diff_gross_1440"] for k, v in res.items() if k.isdigit()},
             res["pass_all"])
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
