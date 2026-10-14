"""VZ E1 - T3 (H-B, conditional regression, <= 8 variants).

Thresholds (quantile edges) are frozen into configs/t3_thresholds.json BEFORE any
outcome is computed (`--freeze`), then `--run` uses only the frozen file. The
ledger gets one row per variant actually evaluated.

Measure: net return spread 60'/240' between the extreme groups + monotonicity
across groups (net = after EXEC bucket cost + 2-leg fee).
"""
import argparse
import json
import os

import numpy as np
import pyarrow.parquet as pq

from e1_common import OUT, REPORT, setup_logging, write_json
from e1_stats import day_level_boot, monotonicity, spread_ci
import e1_ledger

log = setup_logging("e1_t3", "e1_t3.log")
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "configs", "t3_thresholds.json")
DATE = "2026-10-14"
EVENTS = os.path.join(OUT, "e1_events_2024.parquet")

# (name, feature expression, n_quantiles, hi_level, lo_level)
VARIANTS = [
    ("V1_tss_event_q5", "taker_sell_share", 5, 5, 1),
    ("V2_tss_reversal_q5", "tss_reversal", 5, 5, 1),
    ("V3_doi15_q5", "doi_15", 5, 5, 1),
    ("V4_doi60_q5", "doi_60", 5, 5, 1),
    ("V5_premz7_q5", "prem_z7", 5, 5, 1),
    ("V6_funding_q5", "funding_rate", 5, 5, 1),
    ("V7_combo_tsshigh_doi15low_t3", "combo7", 3, 31, 13),
    ("V8_combo_premlow_doi15low_t3", "combo8", 3, 11, 33),
]
VAR_BY_NAME = {v[0]: v for v in VARIANTS}


def load_events(path=EVENTS):
    ev = pq.read_table(path).to_pandas()
    ev["tss_reversal"] = ev.taker_sell_share - ev.tss_5
    return ev


def freeze(ev=None):
    ev = load_events() if ev is None else ev
    cfg = {"date": DATE, "features": {}}
    for name, feat, nq, hi, lo in VARIANTS:
        if feat in ("combo7", "combo8"):
            continue
        v = ev[feat].to_numpy(np.float64)
        ok = np.isfinite(v)
        cfg["features"][feat] = {
            "nq": nq,
            "edges": np.quantile(v[ok], np.linspace(0, 1, nq + 1)[1:-1]).tolist(),
            "n_used": int(ok.sum()), "n_nan": int((~ok).sum())}
    for base in ("doi_15", "taker_sell_share", "prem_z7"):
        v = ev[base].to_numpy(np.float64)
        ok = np.isfinite(v)
        cfg["features"].setdefault(base, {})["tercile_edges"] = \
            np.quantile(v[ok], [1 / 3, 2 / 3]).tolist()
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=1)
    log.info("frozen T3 thresholds -> %s", CONFIG)
    return cfg


def levels_for(cfg, feat, nq, ev):
    if feat == "combo7":
        return _combo(cfg, "taker_sell_share", "doi_15", ev)
    if feat == "combo8":
        return _combo(cfg, "prem_z7", "doi_15", ev)
    edges = np.array(cfg["features"][feat]["edges"], dtype=np.float64)
    v = ev[feat].to_numpy(np.float64)
    lv = np.zeros(len(v), dtype=np.int64)
    ok = np.isfinite(v)
    lv[ok] = np.searchsorted(edges, v[ok], side="right") + 1
    return lv


def _combo(cfg, a, b, ev):
    ea = np.array(cfg["features"][a]["tercile_edges"], dtype=np.float64)
    eb = np.array(cfg["features"][b]["tercile_edges"], dtype=np.float64)
    va = ev[a].to_numpy(np.float64)
    vb = ev[b].to_numpy(np.float64)
    ok = np.isfinite(va) & np.isfinite(vb)
    la = np.searchsorted(ea, va, side="right") + 1
    lb = np.searchsorted(eb, vb, side="right") + 1
    lv = np.zeros(len(ev), dtype=np.int64)
    lv[ok] = la[ok] * 10 + lb[ok]
    return lv


def evaluate_variant(name, cfg, ev):
    _, feat, nq, hi_lv, lo_lv = VAR_BY_NAME[name]
    lv = levels_for(cfg, feat, nq, ev)
    out = {"variant": name, "feature": feat, "n": int((lv > 0).sum()),
           "levels_present": sorted(int(x) for x in np.unique(lv) if x > 0)}
    for col in ("net_60", "net_240", "net_stress_60", "net_stress_240"):
        boot, lvs = day_level_boot(ev[col].to_numpy(np.float64),
                                   ev["day"].to_numpy(np.int64), lv)
        levels = [int(x) for x in lvs if x > 0]
        out[col] = {str(x): {k: v for k, v in boot[x].items() if k != "reps_mean"}
                    for x in levels}
        out[col + "_monotonicity"] = monotonicity([boot[x]["mean"] for x in levels])
        if hi_lv in boot and lo_lv in boot:
            out[col + "_spread_extreme"] = spread_ci(boot, lo_lv, hi_lv)
    return out


def run(only=None):
    if not os.path.exists(CONFIG):
        raise SystemExit("T3 thresholds not frozen; run --freeze first (and commit it)")
    cfg = json.load(open(CONFIG))
    ev = load_events()
    results = []
    for name, feat, nq, hi, lo in VARIANTS:
        if only and name != only:
            continue
        out = evaluate_variant(name, cfg, ev)
        results.append(out)
        log.info("T3 %s n=%d mono60=%.2f spread60=%.5f", name, out["n"],
                 out["net_60_monotonicity"],
                 out.get("net_60_spread_extreme", {}).get("diff_mean", float("nan")))
    write_json(os.path.join(REPORT, "e1_t3.json"), {"config": cfg, "variants": results})
    if not only:
        rows = []
        for r in results:
            sp = r.get("net_60_spread_extreme", {})
            rows.append({"task": "T3", "family": "H-B", "variant": r["variant"], "n": r["n"],
                         "result": "spread60=%s CI=%s mono60=%.2f" % (
                             _f(sp.get("diff_mean")), _f(sp.get("ci95")),
                             r["net_60_monotonicity"]),
                         "date": DATE})
        e1_ledger.append(rows)
        log.info("T3 ledger rows appended: %d", len(rows))
    return results


def _f(x):
    if x is None:
        return "n/a"
    if isinstance(x, list):
        return "[%.5f,%.5f]" % (x[0], x[1])
    return "%.5f" % x if np.isfinite(x) else "n/a"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.freeze:
        freeze()
    if a.run:
        run()
    if not (a.freeze or a.run):
        print("use --freeze or --run")


if __name__ == "__main__":
    main()
