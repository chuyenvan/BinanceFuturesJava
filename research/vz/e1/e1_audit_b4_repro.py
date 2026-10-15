"""VZ AUDIT B4 - A pass: 2024 reproduction (runner engine vs T9 exploration).

Compares three ways of producing the SAME 2024 B4 h24 statistic:

  EXPLORATION  e1_events_2024.parquet (tss_reversal = taker_sell_share - tss_5,
               built by e1_core.build: January has NO previous month) + the T9
               net_1440 (e1_t9_events_net1440.parquet, computed in e1_t9.measure)
               -> the published T9 B4 h24 spread, mono, n.
  CONFIRM      e1_core.build_year_events(2024, prior_lookback=True)  [what
               e1_confirm.run_confirmation does; January sees 2023-12]
  CONFIRM-NOPR e1_core.build_year_events(2024, prior_lookback=False) [January
               inside the year, i.e. the exploration's January convention]

For all three: frozen 2024 tss_reversal edges, day-level block bootstrap
(e1_stats), spread q5-q1, monotonicity -> exactly e1_confirm.col_block.

Also reports the event-level differences vs the exploration artefacts, naming the
rows whose tss_reversal differs (the January-1 lookback boundary).

Writes ~/vz_e1/out/audit_b4_events_2024.parquet (prior_lookback=True) and
~/vz_e1/out/audit_b4_events_2024_noprior.parquet, plus
~/vz_e1/reports/audit_b4_repro.json. Read-only otherwise.
"""
import json
import os

import numpy as np
import pandas as pd

import e1_confirm
import e1_core
from e1_common import OUT, REPORT, setup_logging, write_json
from e1_stats import day_level_boot, monotonicity, spread_ci

log = setup_logging("e1_audit_b4_repro", "e1_audit_b4_repro.log")
CANON = os.path.join(OUT, "e1_events_2024.parquet")
T9NET = os.path.join(OUT, "e1_t9_events_net1440.parquet")
SAVE = os.path.join(OUT, "audit_b4_events_2024.parquet")
SAVE_NP = os.path.join(OUT, "audit_b4_events_2024_noprior.parquet")
PREREG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
                      "docs", "prereg", "PREREG_VZ_B4.md")
T9_SPREAD = -0.013059224306063   # exact, re-read from reports/e1_t9.json B4_tssrev_h24 net_1440
T9_MONO = -1.0
T9_N = 65886


def b4_stats(ev, cfg):
    """e1_confirm.col_block for net_1440 / net_stress_1440 of V2_tss_reversal_q5."""
    _, feat, nq, hi_lv, lo_lv = e1_confirm.e1_t3.VAR_BY_NAME[e1_confirm.B4_VARIANT]
    lv = e1_confirm.e1_t3.levels_for(cfg, feat, nq, ev)
    out = {"n_events": int(len(ev)), "n_level_assigned": int((lv > 0).sum())}
    for col in ("net_1440", "net_stress_1440"):
        boot, lvs = day_level_boot(ev[col].to_numpy(np.float64),
                                   ev["day"].to_numpy(np.int64), lv)
        levels = [int(x) for x in lvs if x > 0]
        sp = spread_ci(boot, lo_lv, hi_lv)
        out[col] = {"n_finite": int(np.isfinite(ev[col].to_numpy(np.float64)).sum()),
                    "monotonicity": float(monotonicity([boot[x]["mean"] for x in levels])),
                    "levels": {str(x): {"n": int(boot[x]["n"]), "mean": float(boot[x]["mean"])}
                               for x in levels},
                    "spread_extreme": {"diff_mean": float(sp["diff_mean"]),
                                       "ci95": [float(sp["ci95"][0]), float(sp["ci95"][1])]}}
    return out


def load_canon():
    ev = pd.read_parquet(CANON)
    ev["tss_reversal"] = ev.taker_sell_share - ev.tss_5
    return ev


def exploration_stats(cfg):
    """T9 published B4 h24: canon features + T9 net_1440 (join like e1_t9.stats)."""
    ev = load_canon()
    nr = pd.read_parquet(T9NET)[["sym", "ts", "net_1440", "net_stress_1440"]]
    ev = ev.merge(nr, on=["sym", "ts"], how="left")
    return b4_stats(ev, cfg)


def build_2024(prior_lookback, save=None):
    if save and os.path.exists(save):
        ev = pd.read_parquet(save)
        log.info("loaded %s rows=%d", save, len(ev))
        return ev
    ev = e1_core.build_year_events(2024, lookback_days=30, prior_lookback=prior_lookback,
                                   release=False, fetch=True)
    log.info("2024 events prior_lookback=%s rows=%d", prior_lookback, len(ev))
    if save:
        ev.to_parquet(save, index=False)
    return ev


def compare_event_level(new, tag):
    canon = load_canon()
    t9 = pd.read_parquet(T9NET)[["sym", "ts", "net_1440", "net_stress_1440"]]
    mn = new[["sym", "ts", "bucket", "tss_reversal", "net_60", "net_240"]].copy()
    mc = canon[["sym", "ts", "bucket", "tss_reversal", "net_60", "net_240"]].copy()
    m = mn.merge(mc, on=["sym", "ts"], how="outer", suffixes=("_new", "_canon"),
                 indicator=True)
    out = {"tag": tag, "n_new": int(len(new)), "n_canon": int(len(canon)),
           "event_set_identical": bool((m._merge == "both").all()),
           "n_only_new": int((m._merge == "left_only").sum()),
           "n_only_canon": int((m._merge == "right_only").sum())}
    both = m[m._merge == "both"]
    out["bucket_mismatch"] = int((both.bucket_new != both.bucket_canon).sum())
    for col in ("tss_reversal", "net_60", "net_240"):
        a = both[col + "_new"].to_numpy(np.float64)
        b = both[col + "_canon"].to_numpy(np.float64)
        fin = np.isfinite(a) & np.isfinite(b)
        out[col + "_max_abs_diff"] = float(np.max(np.abs(a[fin] - b[fin]))) if fin.any() else None
        out[col + "_nan_new_only"] = int((~np.isfinite(a) & np.isfinite(b)).sum())
        out[col + "_nan_canon_only"] = int((np.isfinite(a) & ~np.isfinite(b)).sum())
    mm = new.merge(t9, on=["sym", "ts"], how="inner", suffixes=("", "_t9"))
    a = mm.net_1440.to_numpy(np.float64)
    b = mm.net_1440_t9.to_numpy(np.float64)
    fin = np.isfinite(a) & np.isfinite(b)
    out["net1440_n_compared"] = int(fin.sum())
    out["net1440_max_abs_diff"] = float(np.max(np.abs(a[fin] - b[fin]))) if fin.any() else None
    out["net1440_nan_mismatch"] = int((np.isfinite(a) != np.isfinite(b)).sum())
    return out


def differing_rows(new, tag):
    canon = load_canon()
    mn = new[["sym", "ts", "tss_reversal", "net_1440"]].copy()
    mc = canon[["sym", "ts", "tss_reversal"]].copy()
    m = mn.merge(mc, on=["sym", "ts"], how="inner", suffixes=("_new", "_canon"))
    a = m.tss_reversal_new.to_numpy(np.float64)
    b = m.tss_reversal_canon.to_numpy(np.float64)
    diff = ~((np.isnan(a) & np.isnan(b)) | (np.abs(a - b) <= 1e-12))
    rows = m[diff]
    return {"tag": tag, "n_tss_reversal_diff_rows": int(diff.sum()),
            "rows": [(str(r.sym), int(r.ts),
                      None if not np.isfinite(r.tss_reversal_new) else float(r.tss_reversal_new),
                      None if not np.isfinite(r.tss_reversal_canon) else float(r.tss_reversal_canon))
                     for r in rows.head(20).itertuples(index=False)]}


def main():
    pre = e1_confirm.yaml_block(PREREG)
    cfg = e1_confirm.build_cfg(pre)
    res = {"prereg_yaml": pre, "edges": cfg["features"]["tss_reversal"]["edges"],
           "t9_reference": {"spread_net_1440": T9_SPREAD, "mono": T9_MONO, "n_finite": T9_N}}
    res["exploration_rebuilt"] = exploration_stats(cfg)
    write_json(os.path.join(REPORT, "audit_b4_repro.json"), res)
    ev_prior = build_2024(True, save=SAVE)
    res["confirm_prior_lookback_true"] = b4_stats(ev_prior, cfg)
    res["event_level_vs_canon_prior_true"] = compare_event_level(ev_prior, "prior_true")
    res["differing_rows_prior_true"] = differing_rows(ev_prior, "prior_true")
    write_json(os.path.join(REPORT, "audit_b4_repro.json"), res)
    ev_np = build_2024(False, save=SAVE_NP)
    res["confirm_prior_lookback_false"] = b4_stats(ev_np, cfg)
    res["event_level_vs_canon_prior_false"] = compare_event_level(ev_np, "prior_false")
    write_json(os.path.join(REPORT, "audit_b4_repro.json"), res)
    e = res["exploration_rebuilt"]["net_1440"]["spread_extreme"]["diff_mean"]
    p = res["confirm_prior_lookback_true"]["net_1440"]["spread_extreme"]["diff_mean"]
    p0 = res["confirm_prior_lookback_false"]["net_1440"]["spread_extreme"]["diff_mean"]
    res["verdict"] = {
        "exploration_rebuilt_eq_t9_1e-9": bool(abs(e - T9_SPREAD) <= 1e-9),
        "prior_true_eq_t9_1e-9": bool(abs(p - T9_SPREAD) <= 1e-9),
        "prior_false_eq_t9_1e-9": bool(abs(p0 - T9_SPREAD) <= 1e-9),
        "prior_true_spread": p, "prior_false_spread": p0,
        "delta_prior_true_vs_t9": p - T9_SPREAD,
        "n_finite_prior_true": res["confirm_prior_lookback_true"]["net_1440"]["n_finite"],
        "n_finite_prior_false": res["confirm_prior_lookback_false"]["net_1440"]["n_finite"],
    }
    write_json(os.path.join(REPORT, "audit_b4_repro.json"), res)
    log.info("A pass done: %s", res["verdict"])
    return res


if __name__ == "__main__":
    main()
