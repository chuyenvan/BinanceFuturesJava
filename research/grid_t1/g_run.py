#!/usr/bin/env python3
"""GRID_T1 runner: real + control simulations for G-RANGE / G-DYN.

Writes ~/claude_master/grid_t1_wk/sim_<period>.npz with daily equity per asset/variant/seed.
"""
import json
import os
import sys
import time
import zlib
import numpy as np
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g_sim  # noqa: E402

WK = os.path.expanduser("~/claude_master/grid_t1_wk")
CACHE = os.path.join(WK, "cache")
FUND = os.path.join(WK, "fund")
TS0 = 1638316800000
MIN = 60000
DAY = 1440
PERIODS = {"E": ("2022-01-01", "2024-01-01"), "C": ("2024-01-01", "2026-01-01")}
NSEED = 60


def midx(datestr):
    return int((np.datetime64(datestr, "ms").astype("int64") - TS0) // MIN)


def load_asset(sym, i_hist, i_end):
    z = np.load(os.path.join(CACHE, sym + ".npz"))
    first, last = int(z["first"]), int(z["last"])
    o = z["o"][i_hist:i_end].astype(np.float64)
    h = z["h"][i_hist:i_end].astype(np.float64)
    l = z["l"][i_hist:i_end].astype(np.float64)
    c = z["c"][i_hist:i_end].astype(np.float64)
    f = os.path.join(FUND, sym + ".npz")
    if os.path.exists(f):
        fz = np.load(f)
        fts, frat = fz["ts"], fz["rate"]
    else:
        fts, frat = np.zeros(0, np.int64), np.zeros(0, np.float64)
    return o, h, l, c, first, last, fts, frat


def work(task):
    per, sym, i_start, i_end = task
    i_hist = max(1, i_start - 20160)
    i_hist = (i_hist // 60) * 60
    o, h, l, c, first, last, fts, frat = load_asset(sym, i_hist, i_end)
    n_avail = i_end - i_hist
    # asset window: truncate to full days
    lo = max(i_start, ((first + 59) // 60) * 60)
    lo = ((lo + DAY - 1) // DAY) * DAY
    hi = min(i_end, ((last + 1) // DAY) * DAY)
    ndays = max(0, (i_end - i_start) // DAY)
    out = {"sym": sym, "period": per, "ndays": ndays,
           "ret": {}, "ctrl": {}, "stats": {}}
    if hi <= lo:
        for k in ("range_maker", "range_taker", "range_gross", "dyn_g", "dyn_a", "dyn_g_taker"):
            out["ret"][k] = np.full(ndays, np.nan)
        out["ctrl"]["range_maker"] = np.full((NSEED, ndays), np.nan)
        out["ctrl"]["dyn_g"] = np.full((NSEED, ndays), np.nan)
        return out
    ratios = g_sim.ratios(o, h, l, c)
    base = TS0 + i_hist * MIN
    d0 = (lo - i_start) // DAY
    nd_asset = (hi - lo) // DAY

    def equity(mode, variant=0, boot=False, fee=2e-4, ftaker=5e-4, use_fund=True, seed=0):
        ts, eq, st = g_sim.run(o, h, l, c, base, 0, lo - i_hist, hi - i_hist,
                               mode, variant, boot, fee, ftaker, 1.0,
                               fts if use_fund else None, frat if use_fund else None,
                               seed, ratios)
        e = np.ones(nd_asset + 1)
        m = min(nd_asset, len(eq))
        e[1:1 + m] = eq[:m]
        if m < nd_asset:
            e[1 + m:] = e[m]
        r = e[1:] / e[:-1] - 1.0
        return r, st

    for key, kw in (
        ("range_maker", dict(mode=0)),
        ("range_taker", dict(mode=0, fee=5e-4, ftaker=5e-4)),
        ("range_gross", dict(mode=0, fee=0.0, ftaker=0.0, use_fund=False)),
        ("dyn_g", dict(mode=1, variant=0)),
        ("dyn_a", dict(mode=1, variant=1)),
        ("dyn_g_taker", dict(mode=1, variant=0, fee=5e-4, ftaker=5e-4)),
    ):
        r, st = equity(**kw)
        full = np.full(ndays, np.nan)
        full[d0:d0 + len(r)] = r
        out["ret"][key] = full
        out["stats"][key] = st.tolist()

    for key, kw in (("range_maker", dict(mode=0)), ("dyn_g", dict(mode=1, variant=0))):
        arr = np.full((NSEED, ndays), np.nan)
        for s in range(NSEED):
            r, st = equity(boot=True, seed=s * 7919 + (1 if per == "C" else 0) * 104729 + zlib.crc32(sym.encode()) % 100003, **kw)
            arr[s, d0:d0 + len(r)] = r
        out["ctrl"][key] = arr
    return out


def main():
    u = json.load(open(os.path.join(WK, "universe.json")))
    for per, (a, b) in PERIODS.items():
        i0, i1 = midx(a), midx(b)
        syms = ["BTCUSDT", "ETHUSDT"] + u[per]["union"]
        tasks = [(per, s, i0, i1) for s in syms]
        t0 = time.time()
        res = []
        with Pool(3) as p:
            for k, r in enumerate(p.imap_unordered(work, tasks, chunksize=1)):
                res.append(r)
                print(per, k + 1, len(tasks), r["sym"], f"{time.time()-t0:.0f}s", flush=True)
        keys = list(res[0]["ret"].keys())
        np.savez(os.path.join(WK, "sim_" + per + ".npz"),
                 syms=np.array([r["sym"] for r in res], dtype=object),
                 ndays=np.int64(res[0]["ndays"]),
                 **{k: np.vstack([r["ret"][k] for r in res]) for k in keys},
                 **{"ctrl_" + k: np.stack([r["ctrl"][k] for r in res]) for k in res[0]["ctrl"]},
                 stats=json.dumps({r["sym"]: r["stats"] for r in res}))
        print("saved", per, flush=True)


if __name__ == "__main__":
    main()
