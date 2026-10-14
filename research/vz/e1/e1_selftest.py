"""VZ E1 - causal self-test (T1-V a).

For sampled events, recompute the per-symbol feature frame twice: once with the
full window and once with every row after t_dec set to NaN. All rollings look
strictly backwards, so the feature values at t_dec must be bit-exact identical.
"""
import os

import numpy as np
import pandas as pd
import pyarrow as pa

import e1_data
from e1_common import REPORT, setup_logging, write_json
import e1_core

log = setup_logging("e1_selftest", "e1_selftest.log")

FEATURES = ["taker_sell_share", "tss_5", "tss_15", "volz60",
            "ret_pre_15", "ret_pre_60", "ret_pre_240", "prem_z7", "mark_index_gap"]


def _sym_frame(indexes, sym, m_start, m_end):
    kparts, bparts = [], []
    for key, lo, hi in (("prev", m_start - e1_core.LOOKBACK_MS, None),
                        ("cur", m_start - e1_core.LOOKBACK_MS, None),
                        ("next", m_end, m_end + e1_core.FWD_MS)):
        pair = indexes.get(key)
        if pair is None:
            continue
        kidx, bidx = pair
        d = kidx.read_sym(sym, e1_core.KLINE_COLS, ts_lo=lo, ts_hi=hi)
        if d is not None:
            kparts.append(d)
        b = bidx.read_sym(sym, e1_core.BASIS_COLS, ts_lo=lo, ts_hi=hi)
        if b is not None:
            bparts.append(b)
    if not kparts:
        return None
    kl = pd.concat(kparts, ignore_index=True)
    ba = pd.concat(bparts, ignore_index=True) if bparts else pd.DataFrame(columns=e1_core.BASIS_COLS)
    return kl.merge(ba, on=["sym", "ts"], how="left", sort=False)


def _mask_after(sub, t_dec):
    m = sub.copy()
    fut = m.ts.to_numpy(np.int64) > t_dec
    for c in m.columns:
        if c == "ts" or c == "sym":
            continue
        m[c] = m[c].astype(np.float64)
        m.loc[fut, c] = np.nan
    return m


def run_causal(months=("2024-01", "2024-04", "2024-08"), n_sample=40, seed=20261014):
    rng = np.random.default_rng(seed)
    results, total = {}, 0
    for month in months:
        m_start, m_end = e1_core.month_bounds(month)
        mi = e1_core.MONTHS_2024.index(month)
        def _pair(mm):
            return (e1_core.SymIndex(e1_data.kline_month(mm)),
                    e1_core.SymIndex(e1_data.basis_month(mm)))
        local = {"cur": _pair(month)}
        if mi > 0:
            local["prev"] = _pair(e1_core.MONTHS_2024[mi - 1])
        if mi < 11:
            local["next"] = _pair(e1_core.MONTHS_2024[mi + 1])
        cand = e1_core.candidates(local["cur"][0], m_start, m_end)
        if cand.empty:
            results[month] = {"events": 0, "checked": 0, "n_mismatch": 0, "ok": True}
            continue
        idxs = rng.choice(len(cand), size=min(n_sample, len(cand)), replace=False)
        bad, checked = [], 0
        for kk in idxs:
            sym = cand.sym.to_numpy()[kk]
            t_dec = int(cand.ts.to_numpy()[kk])
            raw = _sym_frame(local, sym, m_start, m_end)
            if raw is None:
                continue
            full = e1_core.compute_features(raw)
            masked = e1_core.compute_features(_mask_after(raw, t_dec))
            ta = full.ts.to_numpy(np.int64)
            ka = int(np.searchsorted(ta, t_dec))
            tb = masked.ts.to_numpy(np.int64)
            kb = int(np.searchsorted(tb, t_dec))
            for c in FEATURES:
                a = full[c].to_numpy()[ka]
                b = masked[c].to_numpy()[kb]
                if not (np.isnan(a) and np.isnan(b)) and not (a == b):
                    bad.append((str(sym), t_dec, c, float(a), float(b)))
            checked += 1
        results[month] = {"events": int(len(cand)), "checked": checked,
                          "n_mismatch": len(bad), "mismatches": bad[:5],
                          "ok": len(bad) == 0}
        total += checked
        log.info("causal %s events=%d checked=%d mismatch=%d", month, len(cand), checked, len(bad))
        del local
    ok = all(v["ok"] for v in results.values())
    out = {"passed": ok, "checked_total": total, "months": results, "features": FEATURES}
    write_json(os.path.join(REPORT, "e1_t1v_a_causal.json"), out)
    log.info("V-a causal PASSED=%s checked=%d", ok, total)
    return out


if __name__ == "__main__":
    run_causal()
