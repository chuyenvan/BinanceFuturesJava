"""VZ E1 - T4 (H-C) analysis around funding settlement (<= 8 variants).

Events + returns come from e1_families_pass.py (e1_t4_funding_events.parquet).
Cost = NC (0.0007 + 2 leg fee) because a settlement is not a crash candle.
Variants: quintile settled rate; |rate| top 5%; sign(rate) x BTC 24h regime;
interval 4h vs 8h. Outcomes: -60'->0, 0->+60', 0->+240'.
"""
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_ledger
from e1_common import OUT, REPORT, SEED, cost_of, setup_logging, write_json
from e1_stats import day_level_boot, monotonicity, spread_ci

log = setup_logging("e1_t4", "e1_t4.log")
DATE = "2026-10-14"


def _stats(ev, lv, col, hi=None, lo=None):
    boot, lvs = day_level_boot(ev[col].to_numpy(np.float64), ev["day"].to_numpy(np.int64), lv)
    d = {"n": int((lv > 0).sum()),
         "levels": {str(x): {k: v for k, v in boot[x].items() if k != "reps_mean"}
                    for x in lvs if x > 0}}
    means = [boot[x]["mean"] for x in lvs if x > 0]
    d["monotonicity"] = monotonicity(means)
    if hi is not None and lo is not None and hi in boot and lo in boot:
        d["spread"] = spread_ci(boot, lo, hi)
    return d


def run():
    ev = pq.read_table(os.path.join(OUT, "e1_t4_funding_events.parquet")).to_pandas()
    ev["day"] = (ev.ts // 86_400_000).astype(np.int64)
    ev["net_pre"] = ev.ret_pre - cost_of(0)
    ev["net_60"] = ev.ret_60 - cost_of(0)
    ev["net_240"] = ev.ret_240 - cost_of(0)
    ev["net_stress_60"] = ev.ret_60 - cost_of(0, True)
    res = {"n": int(len(ev))}
    r = ev.rate.to_numpy(np.float64)
    ok = np.isfinite(r)
    lv1 = np.zeros(len(ev), dtype=np.int64)
    lv1[ok] = np.searchsorted(np.quantile(r[ok], [0.2, 0.4, 0.6, 0.8]), r[ok], side="right") + 1
    res["V1_rate_q5"] = _stats(ev, lv1, "net_60", 5, 1)
    ar = np.abs(r)
    thr = np.nanquantile(ar, 0.95)
    res["V2_absrate_top5"] = _stats(ev, np.where(ar >= thr, 2, 1), "net_60", 2, 1)
    sign = np.where(~ok, 0, np.where(r > 0, 1, 2))
    reg = np.where(ev.btc_ret_24h.to_numpy() > 0, 10, 20)
    lv3 = np.where((sign > 0), sign * 10 + reg // 10, 0)
    res["V3_sign_x_btcregime"] = {c: _stats(ev, lv3, c) for c in ("net_pre", "net_60", "net_240")}
    lv4 = np.where(ev.interval_h.to_numpy() <= 4, 1, 2)
    res["V4_interval"] = _stats(ev, lv4, "net_60", 2, 1)
    write_json(os.path.join(REPORT, "e1_t4.json"), res)
    rows = []
    for name in ("V1_rate_q5", "V2_absrate_top5", "V4_interval"):
        d = res[name]
        sp = d.get("spread", {})
        rows.append({"task": "T4", "family": "H-C", "variant": name, "n": d["n"],
                     "result": "net60 spread=%s CI=%s mono=%.2f" % (
                         _f(sp.get("diff_mean")), _f(sp.get("ci95")), d["monotonicity"]),
                     "date": DATE})
    for name in ("V3_sign_x_btcregime",):
        d = res[name]["net_60"]
        lvls = d["levels"]
        best = max(lvls.items(), key=lambda kv: abs(kv[1]["mean"])) if lvls else None
        rows.append({"task": "T4", "family": "H-C", "variant": name, "n": d["n"],
                     "result": "net60 levels=%s" % (
                         ",".join("%s:%.5f" % (k, v["mean"]) for k, v in lvls.items())),
                     "date": DATE})
    e1_ledger.append(rows)
    log.info("T4 n=%d", len(ev))
    return res


def _f(x):
    if x is None:
        return "n/a"
    if isinstance(x, list):
        return "[%.5f,%.5f]" % (x[0], x[1])
    return "%.5f" % x if np.isfinite(x) else "n/a"


if __name__ == "__main__":
    run()
