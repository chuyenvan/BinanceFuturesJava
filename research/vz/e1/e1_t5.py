"""VZ E1 - T5 (H-D, extreme basis, <= 8 variants).

Events: |prem z7| > 3, merged 60'/symbol. Outcomes: dprem 15'/60', price
60'/240' net of the event-candle EXEC bucket cost (mostly NC). Splits: sign,
daily-liquidity tercile, same/other crash candle.
"""
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_ledger
from e1_common import OUT, REPORT, SEED, bucket_of, cost_of, setup_logging, write_json
from e1_stats import day_level_boot

log = setup_logging("e1_t5", "e1_t5.log")
DATE = "2026-10-14"


def run():
    ev = pq.read_table(os.path.join(OUT, "e1_t5_basis_events.parquet")).to_pandas()
    dv = pq.read_table(os.path.join(OUT, "e1_dayvol_2024.parquet")).to_pandas()
    ev["day"] = (ev.ts // 86_400_000).astype(np.int64)
    ev = ev.merge(dv, on=["sym", "day"], how="left")
    # bucket from the event candle bar_ret (NC unless the candle crashed)
    br = ev.bar_ret.to_numpy(np.float64)
    ev["bucket"] = [bucket_of(np.float32(1 + b), np.float32(1)) if np.isfinite(b) else 0 for b in br]
    for c, cost in (("ret_60", "net_60"), ("ret_240", "net_240")):
        ev[cost] = ev[c] - [cost_of(b) for b in ev.bucket]
        ev["net_stress_" + c.split("_")[1]] = ev[c] - [cost_of(b, True) for b in ev.bucket]
    q = ev.quote_volume.to_numpy(np.float64)
    ok = np.isfinite(q)
    edges = np.quantile(q[ok], [1 / 3, 2 / 3]) if ok.any() else [np.nan, np.nan]
    liq = np.where(~ok, 0, np.searchsorted(edges, q, side="right") + 1)
    ev["liq"] = liq
    ev["crash"] = (ev.bar_ret <= -0.01).fillna(False)

    def one(mask, name, col):
        v = ev.loc[mask, col].to_numpy(np.float64)
        d = ev.loc[mask, "day"].to_numpy(np.int64)
        if len(v) == 0:
            return {"n": 0}
        boot, lvs = day_level_boot(v, d, np.ones(len(v), dtype=np.int64), seed=SEED)
        b = boot[1]
        return {"n": int(b["n"]), "mean": b["mean"], "median": b["median"],
                "hit_rate": b["hit_rate"], "ci95_mean": b["ci95_mean"]}

    variants = {
        "V1_absz_gt3": ev.index >= 0,
        "V2_z_neg": ev.prem_z7 < -3,
        "V3_z_pos": ev.prem_z7 > 3,
        "V4_liq_low": ev.liq == 1,
        "V5_liq_mid": ev.liq == 2,
        "V6_liq_high": ev.liq == 3,
        "V7_on_crash": ev.crash,
        "V8_off_crash": ~ev.crash,
    }
    res = {"n": int(len(ev)), "liq_edges": [float(x) for x in edges]}
    for name, mask in variants.items():
        res[name] = {c: one(mask, name, c) for c in ("net_60", "net_240",
                                                     "net_stress_60", "net_stress_240",
                                                     "dprem_15", "dprem_60")}
    write_json(os.path.join(REPORT, "e1_t5.json"), res)
    rows = []
    for name in variants:
        r = res[name]["net_60"]
        rows.append({"task": "T5", "family": "H-D", "variant": name, "n": r.get("n", 0),
                     "result": "net60 mean=%.5f CI=%s hit=%.3f" % (
                         r.get("mean", float("nan")),
                         r.get("ci95_mean", "n/a"), r.get("hit_rate", float("nan")))
                     if r.get("n") else "no events",
                     "date": DATE})
    e1_ledger.append(rows)
    log.info("T5 done n=%d", len(ev))
    return res


if __name__ == "__main__":
    run()
