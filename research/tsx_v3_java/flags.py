#!/usr/bin/env python3
"""TSX_V3_JAVA - danh sach ngay co cho X14 / T25 / L45 / C420 (PREREG_TSX_V3_JAVA).
CUNG bieu thuc voi ~/claude_master/tsx/tsx_flags.py (DEV: edge_attr/index.npz) va tsx/ho/tsx_ho.py flags() (HO 2026: noi index.npz
+ ew_2026.npz), chi doi tham so (thr, lookback):  ON(D+1) <=> exp(EOD(D) - max EOD(D-L..D)) - 1 <= thr.
  X14  = (-0.30, 30), EXT 336    C420 = (-0.30, 30), EXT 252 (tong giu 420h)
  T25  = (-0.25, 30), EXT 336    L45  = (-0.30, 45), EXT 336
Tu kiem (assert): X14 DEV = tsx/flags.json (214 ngay, sha c79ef302), X14 HO = tsx/ho/ho_flags.json;
T25/L45/C420 = tsx2sim/flags_variants.json (VT25/VL45/V420, chuoi run da chay) va tsx_v3/flags_v3.json (V3/V4/V1).
Out: ~/claude_master/tsx_v3_java/flags.json
"""
import hashlib
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx3j_flags")
OUT = "/home/ubuntu/claude_master/tsx_v3_java"
TSX = "/home/ubuntu/claude_master/tsx"
ONE = pd.Timedelta(days=1)
ARMS = {"X14": (-0.30, 30, 336, "X14", "V0"), "T25": (-0.25, 30, 336, "VT25", "V3"),
        "L45": (-0.30, 45, 336, "VL45", "V4"), "C420": (-0.30, 30, 252, "V420", "V1")}


def ranges_of(days):
    rng, st, pv = [], None, None
    for d in days:
        if st is None:
            st = pv = d
        elif d == pv + ONE:
            pv = d
        else:
            rng.append((st, pv))
            st = pv = d
    if st is not None:
        rng.append((st, pv))
    return rng


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
    assert np.array_equal(ta[ma], tb[mb]) and float(np.max(np.abs(ra[ma] - rb[mb]))) <= 1e-9, "noi EW FAIL"
    ts = np.concatenate([ta[ta < hi], tb[tb >= hi]])
    r = np.concatenate([ra[ta < hi], rb[tb >= hi]])
    L = pd.Series(np.cumsum(r.astype(np.float64)), index=pd.to_datetime(ts, unit="ms"))
    return L.groupby(L.index.floor("D")).last()


def days_of(eod, thr, lb, lo, hi):
    mx = eod.rolling(lb + 1, min_periods=1).max()
    dd = np.exp(eod - mx) - 1
    fd = sorted(dd[dd <= thr].index + ONE)
    return [d for d in fd if pd.Timestamp(lo) <= d <= pd.Timestamp(hi)]


def pack(days):
    rng = ranges_of(days)
    s = ",".join("%s-%s" % (a.strftime("%Y%m%d"), b.strftime("%Y%m%d")) for a, b in rng)
    by = pd.Series(1, index=pd.DatetimeIndex(days)).groupby(lambda x: x.year).sum().to_dict() if days else {}
    return dict(n_days=len(days), n_ranges=len(rng), ranges=s, sha256=hashlib.sha256(s.encode()).hexdigest(),
                by_year={int(k): int(v) for k, v in by.items()})


def main():
    os.makedirs(OUT, exist_ok=True)
    ed, eh = eod_dev(), eod_ho()
    out, SD, SH = {}, {}, {}
    for a, (thr, lb, ext, _, _) in ARMS.items():
        dd_ = days_of(ed, thr, lb, "2021-07-01", "2025-12-31")
        hh_ = days_of(eh, thr, lb, "2026-01-01", "2026-09-30")
        out[a] = dict(thr=thr, lookback=lb, ext_hours=ext, total_hours=168 + ext, dev=pack(dd_), ho=pack(hh_))
        SD[a], SH[a] = set(dd_), set(hh_)
    for a in ARMS:
        out[a]["dev"]["only_vs_X14"] = len(SD[a] - SD["X14"])
        out[a]["dev"]["missing_vs_X14"] = len(SD["X14"] - SD[a])
        out[a]["ho"]["only_vs_X14"] = len(SH[a] - SH["X14"])
        out[a]["ho"]["missing_vs_X14"] = len(SH["X14"] - SH[a])
        log.info("%-4s thr %.2f L %d EXT %d (tong %dh) | DEV %d ngay %d khoang sha %s theo nam %s (+%d/-%d vs X14) | HO %d ngay sha %s (+%d/-%d)",
                 a, out[a]["thr"], out[a]["lookback"], out[a]["ext_hours"], out[a]["total_hours"], out[a]["dev"]["n_days"],
                 out[a]["dev"]["n_ranges"], out[a]["dev"]["sha256"][:8], out[a]["dev"]["by_year"], out[a]["dev"]["only_vs_X14"],
                 out[a]["dev"]["missing_vs_X14"], out[a]["ho"]["n_days"], out[a]["ho"]["sha256"][:8], out[a]["ho"]["only_vs_X14"],
                 out[a]["ho"]["missing_vs_X14"])
    pre, hof = json.load(open(TSX + "/flags.json")), json.load(open(TSX + "/ho/ho_flags.json"))
    t2 = json.load(open("/home/ubuntu/claude_master/tsx2sim/flags_variants.json"))["arms"]
    t3 = json.load(open("/home/ubuntu/claude_master/tsx_v3/flags_v3.json"))["arms"]
    chk = dict(x14_dev_eq_flags_json=out["X14"]["dev"]["ranges"] == pre["ranges"] and out["X14"]["dev"]["sha256"] == pre["sha256"],
               x14_dev_214_c79ef302=out["X14"]["dev"]["n_days"] == 214 and out["X14"]["dev"]["sha256"].startswith("c79ef302"),
               x14_ho_eq_ho_flags=out["X14"]["ho"]["ranges"] == hof["ranges"] and out["X14"]["ho"]["sha256"] == hof["sha256"])
    for a, (_, _, ext, k2, k3) in ARMS.items():
        chk[a + "_eq_tsx2sim_" + k2] = bool(out[a]["dev"]["ranges"] == t2[k2]["dev"]["ranges"] and out[a]["ho"]["ranges"] == t2[k2]["ho"]["ranges"]
                                            and ext == t2[k2]["ext_hours"])
        chk[a + "_eq_tsx3_" + k3] = bool(out[a]["dev"]["ranges"] == t3[k3]["dev"]["ranges"] and out[a]["ho"]["ranges"] == t3[k3]["ho"]["ranges"]
                                         and ext == t3[k3]["ext_hours"])
    log.info("KIEM %s", chk)
    assert all(chk.values()), chk
    json.dump(dict(arms=out, checks=chk), open(OUT + "/flags.json", "w"), indent=1)
    log.info("WROTE %s/flags.json sha256 %s", OUT, hashlib.sha256(open(OUT + "/flags.json", "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
