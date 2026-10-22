#!/usr/bin/env python3
"""TSX_V2_SIM - co ngay cho 4 bien the (PREREG_TSX_V2_SIM). DUNG cong thuc tsx/tsx_flags.py (DEV) va
tsx/ho/tsx_ho.py flags() (HO 2026, noi index.npz + ew_2026.npz); chi doi (thr, lookback). Tu kiem: (-0.30, 30) phai
trung flags.json / ho_flags.json (chuoi khoang + sha). Out: ~/claude_master/tsx2sim/flags_variants.json
"""
import hashlib
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx2flags")
OUT = "/home/ubuntu/claude_master/tsx2sim"
TSX = "/home/ubuntu/claude_master/tsx"
# ten -> (SIM_LOSER_TS_EXT_HOURS, thr, lookback); tong giu toi da = 168 + ext
ARMS = {"X14": (336, -0.30, 30), "V336": (168, -0.30, 30), "V420": (252, -0.30, 30),
        "VT25": (336, -0.25, 30), "VL45": (336, -0.30, 45)}


def ranges_of(days):
    rng, st, pv = [], None, None
    for d in days:
        if st is None:
            st = pv = d
        elif d == pv + pd.Timedelta(days=1):
            pv = d
        else:
            rng.append((st, pv))
            st = pv = d
    if st is not None:
        rng.append((st, pv))
    return rng


def rstr(rng):
    return ",".join("%s-%s" % (a.strftime("%Y%m%d"), b.strftime("%Y%m%d")) for a, b in rng)


def eod_dev():
    z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
    ts = pd.to_datetime(z["ew_ts"].astype(np.int64), unit="ms")
    L = pd.Series(np.cumsum(z["ew_r"].astype(np.float64)), index=ts)
    return L.groupby(L.index.floor("D")).last()


def eod_ho():
    a = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
    b = np.load(TSX + "/ho/ew_out/ew_2026.npz")
    ta, ra, tb, rb = a["ew_ts"].astype(np.int64), a["ew_r"], b["ew_ts"].astype(np.int64), b["ew_r"]
    lo = int(pd.Timestamp("2025-10-01").value // 10**6)
    hi = int(pd.Timestamp("2026-01-01").value // 10**6)
    ma, mb = (ta >= lo) & (ta < hi), (tb >= lo) & (tb < hi)
    assert np.array_equal(ta[ma], tb[mb]) and float(np.max(np.abs(ra[ma] - rb[mb]))) <= 1e-9, "V1 FAIL"
    ts = np.concatenate([ta[ta < hi], tb[tb >= hi]])
    r = np.concatenate([ra[ta < hi], rb[tb >= hi]])
    L = pd.Series(np.cumsum(r.astype(np.float64)), index=pd.to_datetime(ts, unit="ms"))
    return L.groupby(L.index.floor("D")).last()


def days_of(eod, thr, lb, lo, hi):
    dd = np.exp(eod - eod.rolling(lb + 1, min_periods=1).max()) - 1
    fd = sorted(dd[dd <= thr].index + pd.Timedelta(days=1))
    return [d for d in fd if pd.Timestamp(lo) <= d <= pd.Timestamp(hi)]


def pack(days):
    s = rstr(ranges_of(days))
    by = pd.Series(1, index=pd.DatetimeIndex(days)).groupby(lambda x: x.year).sum().to_dict() if days else {}
    return dict(n_days=len(days), n_ranges=len(ranges_of(days)), ranges=s, sha256=hashlib.sha256(s.encode()).hexdigest(),
                by_year={int(k): int(v) for k, v in by.items()})


def main():
    os.makedirs(OUT, exist_ok=True)
    ed, eh = eod_dev(), eod_ho()
    out = {}
    for arm, (h, thr, lb) in ARMS.items():
        dev = pack(days_of(ed, thr, lb, "2021-07-01", "2025-12-31"))
        ho = pack(days_of(eh, thr, lb, "2026-01-01", "2026-09-30"))
        out[arm] = dict(ext_hours=h, total_hours=168 + h, thr=thr, lookback=lb, dev=dev, ho=ho)
        log.info("%s ext=%d tong=%d thr=%.2f L=%d | DEV %d ngay %d khoang sha %s %s | HO %d ngay %d khoang sha %s %s",
                 arm, h, 168 + h, thr, lb, dev["n_days"], dev["n_ranges"], dev["sha256"][:8], dev["by_year"],
                 ho["n_days"], ho["n_ranges"], ho["sha256"][:8], ho["ranges"])
    pre, hof = json.load(open(TSX + "/flags.json")), json.load(open(TSX + "/ho/ho_flags.json"))
    chk = dict(dev_base=out["X14"]["dev"]["ranges"] == pre["ranges"] and out["X14"]["dev"]["sha256"] == pre["sha256"],
               ho_base=out["X14"]["ho"]["ranges"] == hof["ranges"] and out["X14"]["ho"]["sha256"] == hof["sha256"],
               v336_same=out["V336"]["dev"]["ranges"] == pre["ranges"] and out["V336"]["ho"]["ranges"] == hof["ranges"],
               v420_same=out["V420"]["dev"]["ranges"] == pre["ranges"] and out["V420"]["ho"]["ranges"] == hof["ranges"],
               vt25_phaseB=out["VT25"]["dev"]["n_days"] == 406, vl45_phaseB=out["VL45"]["dev"]["n_days"] == 445)
    log.info("KIEM %s", chk)
    assert all(chk.values()), chk
    json.dump(dict(arms=out, checks=chk), open(OUT + "/flags_variants.json", "w"), indent=1)
    log.info("WROTE %s/flags_variants.json", OUT)


if __name__ == "__main__":
    main()
