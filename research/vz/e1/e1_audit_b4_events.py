"""VZ AUDIT B4 - event pass: B2-outcome / B4 / B5 / C1 / C2 / C3.

Builds the E1 crash event set for each of 2022/2023/2024/2025 with the CONFIRM
engine (`e1_core.build_year_events`, prior_lookback=True, 30d lookback, release
kept on so the local month cache survives), then reports:

B4  events/year + active symbols/month + events/symbol + event concentration
B5  anomalies.csv rows per year (and rows actually skipped by the reader)
B2  1000 random events/year: close(ts+1440') read straight from the parquet
    (independent reader, no e1_core/e1_data/SymIndex) vs the runner's gross_1440
C1  2024 quintile edges applied to each year -> % events per quintile per year
C2  share of events dropped for missing close+1440' by year x quintile
C3  events-per-minute distribution per year + spread with 1 event/minute

Writes ~/vz_e1/out/audit_b4_events_<year>.parquet and
~/vz_e1/reports/audit_b4_events.json.
"""
import argparse
import csv
import json
import os
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_core
import e1_data
from e1_common import OUT, REPORT, setup_logging, write_json
from e1_stats import day_level_boot, monotonicity, spread_ci

log = setup_logging("e1_audit_b4_events", "e1_audit_b4_events.log")
HERE = os.path.dirname(os.path.abspath(__file__))
T3CFG = os.path.join(HERE, "configs", "t3_thresholds.json")
YEARS = [2022, 2023, 2024, 2025]
H1440 = 1440 * 60_000


def events_path(year):
    return os.path.join(OUT, "audit_b4_events_%d.parquet" % year)


def build_or_load(year, rebuild=False):
    p = events_path(year)
    if os.path.exists(p) and not rebuild:
        ev = pd.read_parquet(p)
        log.info("loaded %s rows=%d", p, len(ev))
        return ev
    t0 = time.time()
    ev = e1_core.build_year_events(year, lookback_days=30, prior_lookback=True,
                                   release=False, fetch=True)
    ev.to_parquet(p, index=False)
    log.info("built %s rows=%d (%.0fs)", p, len(ev), time.time() - t0)
    return ev


def edges_2024():
    cfg = json.load(open(T3CFG))
    return np.array(cfg["features"]["tss_reversal"]["edges"], dtype=np.float64)


def levels_from(vals, edges):
    lv = np.zeros(len(vals), dtype=np.int64)
    ok = np.isfinite(vals)
    lv[ok] = np.searchsorted(edges, vals[ok], side="right") + 1
    return lv


# ---------------------------------------------------------------- B2 hand read
def hand_close_lookup(month, syms):
    """(sym,ts)->close read directly from the month parquet (independent path).

    No e1_core/SymIndex/anomalies filtering: plain column read + pandas filter.
    """
    path = e1_data.month_path(month, "kline", fetch=True)
    t = pq.read_table(path, columns=["ts", "sym", "close"]).to_pandas()
    t = t[t.sym.isin(syms)]
    if t.empty:
        return {}
    return {(str(s), int(ts)): float(c)
            for s, ts, c in zip(t.sym.to_numpy(), t.ts.to_numpy(np.int64),
                                t.close.to_numpy(np.float64))}


def next_month(m):
    return "%04d-01" % (int(m[:4]) + 1) if m[5:7] == "12" else \
        "%04d-%02d" % (int(m[:4]), int(m[5:7]) + 1)


def b2_outcome_check(ev, year, n=1000, seed=20261015):
    rng = np.random.default_rng(seed + year)
    idx = rng.choice(len(ev), size=min(n, len(ev)), replace=False)
    samp = ev.iloc[idx].copy()
    samp["m"] = samp.month.astype(str)
    hit = miss = 0
    diffs = []
    bad = []
    # one month at a time (keeps RSS low: at most 2 month files in memory)
    for m, grp in samp.groupby("m", sort=True):
        syms = set(grp.sym.astype(str))
        cm = hand_close_lookup(m, syms)
        cn = {}
        t1s = {}
        for r in grp.itertuples(index=False):
            s = str(r.sym)
            t1 = int(r.ts) + H1440
            if (s, int(r.ts)) in cm and (s, t1) not in cm:
                t1s[s] = t1
        if t1s:
            cn = hand_close_lookup(next_month(m), set(t1s))
        for r in grp.itertuples(index=False):
            s = str(r.sym)
            c0 = cm.get((s, int(r.ts)))
            t1 = int(r.ts) + H1440
            rec = cm.get((s, t1)) or cn.get((s, t1))
            if c0 is None:
                miss += 1
                continue
            if rec is None or c0 <= 0 or rec <= 0:
                # the runner should also have gross_1440 = NaN here
                if np.isfinite(r.gross_1440):
                    bad.append((s, int(r.ts), r.gross_1440, "runner finite, hand read misses ts+1440"))
                miss += 1
                continue
            g_hand = float(np.log(rec / c0))
            if not np.isfinite(r.gross_1440):
                bad.append((s, int(r.ts), None, "runner NaN, hand read finite %.8f" % g_hand))
                miss += 1
                continue
            diffs.append(abs(g_hand - r.gross_1440))
            hit += 1
        del cm, cn, t1s
    d = np.array(diffs) if diffs else np.array([0.0])
    return {"year": year, "n_sampled": int(len(samp)), "n_compared": hit,
            "n_skipped": miss, "max_abs_diff_gross_1440": float(d.max()),
            "n_mismatch": len(bad), "mismatch_examples": bad[:5],
            "pass": bool(len(bad) == 0 and d.max() == 0.0)}


# ---------------------------------------------------------------- B4 / B5
def b5_anomalies(year):
    rows = 0
    per_month = {}
    for m in ["%04d-%02d" % (year, i) for i in range(1, 13)]:
        try:
            bad = e1_data.anomalies(m, "kline")
        except Exception as e:  # noqa: BLE001
            log.warning("anomalies lookup %s failed: %s", m, e)
            bad = set()
        per_month[m] = len(bad)
        rows += len(bad)
    return {"year": year, "anomaly_rows_in_dataset": rows, "per_month": per_month}


def b4_explain(ev, year, data_months):
    ex = ev[ev.month.astype(str).str.startswith(str(year))]
    per_sym = ex.groupby("sym").size().sort_values(ascending=False)
    tot = int(len(ex))
    top20 = float(per_sym.head(20).sum() / tot) if tot else float("nan")
    dm = [d for d in data_months if d["month"].startswith(str(year))]
    syms = [d["n_syms"] for d in dm]
    return {"year": year, "n_events": tot,
            "n_syms_month_min": int(min(syms)) if syms else None,
            "n_syms_month_max": int(max(syms)) if syms else None,
            "n_syms_month_mean": float(np.mean(syms)) if syms else None,
            "events_per_symbol": float(tot / np.mean(syms)) if syms else None,
            "n_distinct_event_symbols": int(ex.sym.nunique()),
            "top20_symbol_event_share": top20,
            "top10_event_symbols": {str(k): int(v) for k, v in per_sym.head(10).items()}}


# ---------------------------------------------------------------- C
def c1_quintiles_by_year(evs, edges):
    out = {}
    for y, ev in evs.items():
        v = ev.tss_reversal.to_numpy(np.float64)
        lv = levels_from(v, edges)
        ok = lv > 0
        n = int(ok.sum())
        frac = {str(q): float((lv[ok] == q).mean()) for q in range(1, 6)}
        out[str(y)] = {"n_with_feature": n, "n_events": int(len(ev)), "pct_per_quintile": frac}
    return out


def c2_missing_by_year_quintile(evs, edges):
    out = {}
    for y, ev in evs.items():
        v = ev.tss_reversal.to_numpy(np.float64)
        lv = levels_from(v, edges)
        fin = np.isfinite(ev.net_1440.to_numpy(np.float64))
        ok = lv > 0
        rec = {}
        for q in range(1, 6):
            sel = ok & (lv == q)
            n = int(sel.sum())
            drop = int((sel & ~fin).sum())
            rec[str(q)] = {"n": n, "n_missing_24h": drop,
                           "frac_missing": float(drop / n) if n else None}
        sel_all = ok
        rec["all"] = {"n": int(sel_all.sum()),
                      "n_missing_24h": int((sel_all & ~fin).sum()),
                      "frac_missing": float((sel_all & ~fin).sum() / sel_all.sum())
                      if sel_all.sum() else None}
        rec["n_events_no_level"] = int((~ok).sum())
        out[str(y)] = rec
    return out


def c3_minute_clusters(evs, edges):
    out = {}
    for y, ev in evs.items():
        cnt = ev.groupby("ts").size()
        hist = cnt.value_counts().sort_index()
        # 1 event per minute: keep the first row of each minute (ts order stable)
        ded = ev.sort_values(["ts", "sym"], kind="stable").drop_duplicates("ts", keep="first")
        lv = levels_from(ded.tss_reversal.to_numpy(np.float64), edges)
        s = ded[np.isfinite(ded.net_1440.to_numpy(np.float64))].copy()
        lv2 = levels_from(s.tss_reversal.to_numpy(np.float64), edges)
        boot, lvs = day_level_boot(s.net_1440.to_numpy(np.float64),
                                   s.day.to_numpy(np.int64), lv2)
        levels = [int(x) for x in lvs if x > 0]
        spread = (spread_ci(boot, 1, 5)["diff_mean"] if (1 in boot and 5 in boot)
                  else float("nan"))
        mono = monotonicity([boot[x]["mean"] for x in levels]) if levels else float("nan")
        out[str(y)] = {"n_events": int(len(ev)), "n_minutes_with_event": int(len(cnt)),
                       "max_events_one_minute": int(cnt.max()),
                       "hist_events_per_minute": {str(int(k)): int(v)
                                                  for k, v in hist.head(10).items()},
                       "n_minutes_gt1": int((cnt > 1).sum()),
                       "n_events_if_1_per_minute": int(len(ded)),
                       "n_finite_net1440_if_1_per_minute": int(len(s)),
                       "spread_net_1440_if_1_per_minute": float(spread),
                       "mono_net_1440_if_1_per_minute": float(mono)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default=",".join(str(y) for y in YEARS))
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--with-b2", action="store_true")
    a = ap.parse_args()
    years = [int(x) for x in a.years.split(",") if x.strip()]
    edges = edges_2024()
    evs = {}
    for y in years:
        evs[y] = build_or_load(y, rebuild=a.rebuild)
    data_months = []
    p = os.path.join(REPORT, "audit_b4_data.json")
    if os.path.exists(p):
        data_months = json.load(open(p)).get("months", [])
    res = {"edges_2024_tss_reversal": edges.tolist(),
           "per_year_counts": {str(y): {"n_events_all": int(len(evs[y])),
                                        "n_with_24h": int(np.isfinite(
                                            evs[y].net_1440.to_numpy(np.float64)).sum())}
                               for y in years},
           "b4": {str(y): b4_explain(evs[y], y, data_months) for y in years},
           "b5_anomalies": {str(y): b5_anomalies(y) for y in years},
           "c1_quintiles_by_year": c1_quintiles_by_year(evs, edges),
           "c2_missing_1440_by_year_quintile": c2_missing_by_year_quintile(evs, edges),
           "c3_minute_clusters": c3_minute_clusters(evs, edges)}
    if a.with_b2:
        res["b2_outcome_check"] = {str(y): b2_outcome_check(evs[y], y) for y in years}
    write_json(os.path.join(REPORT, "audit_b4_events.json"), res)
    log.info("audit events report written")
    print(json.dumps(res["per_year_counts"], indent=1))
    return res


if __name__ == "__main__":
    main()
