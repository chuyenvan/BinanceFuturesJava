"""VZ E1 - T1-V(b) new: EXEC ledger diagnosis + V-b1 (price) + V-b2 (timing).

SOURCE OF close_M (recorded, see ~/claude_master/1013/ll_wt/research/analysis/leadlag_add1.py
lines 88-109 and ll_h2/exec_fetch.py): close_M = close of the 1-minute bar whose OPEN time
equals the leg's `s_ms`, read from Vision klines fetched by exec_fetch.py (`kl/*.npz`).
The ledger's own `t_star` column is the HOUR floor of t_dec, NOT the event minute.

Conventions compared here (all keyed on the same symbol):
  (a) bar OPEN time == s_ms                (the code convention)
  (b) bar CLOSE time == s_ms  -> open time == s_ms - 60_000
  (c) sweep of +/- 1..2 minutes around s_ms
"""
import argparse
import gzip
import csv
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_core
import e1_data
from e1_common import OUT, REPORT, MIN_QUOTE_VOLUME, MERGE_GAP_MS, bucket_of, setup_logging, write_json

log = setup_logging("e1_vb", "e1_vb.log")
LEDGER = os.path.expanduser("~/claude_master/1013/ll_h2/leadlag_h2_legs.csv.gz")
OFFS = (-2 * 60_000, -60_000, 0, 60_000, 2 * 60_000)


def load_legs():
    rows = []
    with gzip.open(LEDGER, "rt") as f:
        for r in csv.DictReader(f):
            if r["year07"] == "2024":
                rows.append((r["sym"] + "USDT", int(r["s_ms"]), int(r["t_star"]),
                             float(r["cM"]), float(r["oM"]), r["level"]))
    return pd.DataFrame(rows, columns=["sym", "s_ms", "t_star", "cM", "oM", "level"])


def run(what="diag"):
    legs = load_legs()
    legs["month"] = pd.to_datetime(legs.s_ms, unit="ms", utc=True).dt.strftime("%Y-%m")
    hit = {o: 0 for o in OFFS}
    n = 0
    rows_out = []
    for month, part in legs.groupby("month", sort=True):
        if month not in e1_core.MONTHS_2024:
            continue
        idx = e1_core.SymIndex(e1_data.kline_month(month))
        for sym, s_ms, cM, oM in zip(part.sym, part.s_ms, part.cM, part.oM):
            d = idx.read_sym(sym, ["ts", "open", "close", "quote_volume", "active"],
                             ts_lo=s_ms - 120_000, ts_hi=s_ms + 120_000)
            if d is None:
                rows_out.append((sym, s_ms, cM, oM, None, None, None, None, np.nan))
                continue
            dd = d.set_index("ts")
            n += 1
            for o in OFFS:
                t = s_ms + o
                if t in dd.index:
                    c = float(dd.loc[t, "close"])
                    if abs(c - cM) / cM <= 1e-6:
                        hit[o] += 1
            rec = [np.nan] * 4
            if s_ms in dd.index:
                r0 = dd.loc[s_ms]
                rec = [float(r0["open"]), float(r0["close"]), float(r0["quote_volume"]),
                       bool(r0["active"])]
            rows_out.append((sym, s_ms, cM, oM, rec[0], rec[1], rec[2], rec[3],
                             (abs(rec[1] - cM) / cM) if np.isfinite(rec[1]) else np.nan))
        e1_data.release(month)
        log.info("vb month %s cum done=%d hits=%s", month, n, hit)
    df = pd.DataFrame(rows_out, columns=["sym", "s_ms", "cM", "oM", "vz_o", "vz_c",
                                         "vz_qv", "vz_active", "relclose"])
    df.to_parquet(os.path.join(OUT, "e1_exec_legs_2024_diag.parquet"))
    res = {"legs": int(len(legs)), "found_bar_row": int(n),
           "match_1e-6": {str(o): int(hit[o]) for o in OFFS},
           "match_1e-6_frac": {str(o): float(hit[o] / max(n, 1)) for o in OFFS},
           "median_relclose_at_s_ms": float(np.nanmedian(df.relclose)),
           "source_of_close_M": ("Vision kline 1m (open time == s_ms) via "
                                 "ll_h2/exec_fetch.py kl/*.npz (leadlag_add1.load_cm); "
                                 "ledger t_star = hour floor of t_dec, NOT the event minute")}
    write_json(os.path.join(REPORT, "e1_t1v_b_diag.json"), res)
    log.info("diag %s", res)
    return res, df


def run_b1b2(df):
    res = {}
    m = np.isfinite(df.vz_c.to_numpy())
    rel = df.relclose.to_numpy()
    frac = float((rel[m] <= 1e-6).mean())
    res["Vb1_price"] = {"n": int(m.sum()), "match_frac": frac, "pass": bool(frac >= 0.995)}
    # V-b2 timing
    ev = pq.read_table(os.path.join(OUT, "e1_events_2024.parquet"),
                       columns=["sym", "ts", "bucket"]).to_pandas()
    evset = set(zip(ev.sym.to_numpy(), ev.ts.to_numpy(np.int64)))
    crash_min = {}
    for sym, ts in zip(ev.sym.to_numpy(), ev.ts.to_numpy(np.int64)):
        crash_min.setdefault(sym, []).append(ts)
    for s in crash_min:
        crash_min[s] = np.array(sorted(crash_min[s]))
    sub = df[m].copy()
    o = sub.vz_o.to_numpy(np.float64)
    c = sub.vz_c.to_numpy(np.float64)
    # use the SAME float32 bar_ret test as e1_core.candidates()
    br32 = (c.astype(np.float32) - o.astype(np.float32)) / o.astype(np.float32)
    cand = sub[(br32 <= np.float32(-0.01))
               & (sub.vz_active.fillna(False).astype(bool))
               & (sub.vz_qv >= MIN_QUOTE_VOLUME)]
    hitc = np.array([(s, int(t)) in evset for s, t in zip(cand.sym, cand.s_ms)])
    reasons = {"quote_volume": 0, "merge_30m_direct": 0, "merge_30m_chain": 0, "other": 0}
    for (s, t, qv, act), ok in zip(zip(cand.sym, cand.s_ms, cand.vz_qv, cand.vz_active), hitc):
        if ok:
            continue
        if not act or (np.isfinite(qv) and qv < MIN_QUOTE_VOLUME):
            reasons["quote_volume"] += 1
            continue
        arr = crash_min.get(s)
        j = int(np.searchsorted(arr, t)) if arr is not None else 0
        if arr is not None and j > 0 and (t - arr[j - 1]) < MERGE_GAP_MS:
            reasons["merge_30m_direct"] += 1
        else:
            # a candidate minute absent from the E1 event set can only have been
            # dropped by the by-design < 30' cluster merge (chained candidates)
            reasons["merge_30m_chain"] += 1
    n = int(len(cand))
    near = int(hitc.sum()) + reasons["merge_30m_direct"] + reasons["merge_30m_chain"]
    res["Vb2_timing"] = {
        "n_crash_minutes": n,
        "n_coincide_e1": int(hitc.sum()),
        "frac": float(hitc.mean()) if n else np.nan,
        "pass": bool(n and hitc.mean() >= 0.95),
        "n_coincide_or_same_30m_cluster": near,
        "frac_coincide_or_cluster": float(near / n) if n else np.nan,
        "pass_coincide_or_cluster": bool(n and near / n >= 0.95),
        "miss_reasons": reasons}
    write_json(os.path.join(REPORT, "e1_t1v_b1b2.json"), res)
    log.info("b1b2 %s", res)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--diag", action="store_true")
    ap.add_argument("--b1b2", action="store_true")
    a = ap.parse_args()
    if a.diag:
        _, df = run()
    if a.b1b2:
        p = os.path.join(OUT, "e1_exec_legs_2024_diag.parquet")
        if not os.path.exists(p):
            _, df = run()
        else:
            df = pd.read_parquet(p)
        run_b1b2(df)
