#!/usr/bin/env python3
"""TSX_V3 - danh sach ngay co cho V0..V4 (PREREG_TSX_V3). CUNG cong thuc tsx/tsx_flags.py (DEV, edge_attr/index.npz) va
tsx/ho/tsx_ho.py flags() (HO 2026, noi index.npz + ew_2026.npz), nhu research/tsx_v2_sim/flags.py (bfa59d4a).
  ON_{thr,L}(D) <=> exp(EOD(D-1) - max EOD(D-1-L..D-1)) - 1 <= thr.
  V2 = B3b (PREREG_TSX_V2 §2): ON_V2(D) = ON_base(D) and reb(D) < 0.20, reb(D) = exp(EOD(D-1) - min_{d in [F_D-1, D-1]} EOD(d)) - 1,
       F_D = ngay dau cua chuoi ngay ON_base lien tiep chua D. Ban "tat vinh vien toi het chuoi" tinh kem de kiem trung.
Tu kiem: V0 = flags.json / ho_flags.json; V1/V3/V4 = tsx2sim/flags_variants.json (V420/VT25/VL45) byte-identical;
V2 DEV so ngay = phaseB K6 B3b_r0.20 (210); V2 la tap con V0. Out: ~/claude_master/tsx_v3/flags_v3.json
"""
import hashlib
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx3flags")
OUT = "/home/ubuntu/claude_master/tsx_v3"
TSX = "/home/ubuntu/claude_master/tsx"
REPO = "/home/ubuntu/claude_master/vz_e1_wt"
ONE = pd.Timedelta(days=1)


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
    assert np.array_equal(ta[ma], tb[mb]) and float(np.max(np.abs(ra[ma] - rb[mb]))) <= 1e-9, "noi EW FAIL"
    ts = np.concatenate([ta[ta < hi], tb[tb >= hi]])
    r = np.concatenate([ra[ta < hi], rb[tb >= hi]])
    L = pd.Series(np.cumsum(r.astype(np.float64)), index=pd.to_datetime(ts, unit="ms"))
    return L.groupby(L.index.floor("D")).last()


def days_of(eod, thr, lb, lo, hi):
    dd = np.exp(eod - eod.rolling(lb + 1, min_periods=1).max()) - 1
    fd = sorted(dd[dd <= thr].index + ONE)
    return [d for d in fd if pd.Timestamp(lo) <= d <= pd.Timestamp(hi)]


def b3_days(eod, base_days, r):
    """= research/tsx_v2/phase_b.py b3_days (B3, theo ngay)."""
    bs = set(base_days)
    out = []
    for D in base_days:
        F = D
        while F - ONE in bs:
            F -= ONE
        seg = eod[(eod.index >= F - ONE) & (eod.index <= D - ONE)]
        reb = np.exp(eod.get(D - ONE) - seg.min()) - 1
        if reb < r:
            out.append(D)
    return out


def b3_perm_days(eod, base_days, r):
    """ban 'tat tu ngay sau EOD hoi >= r toi het chuoi ON_base' (chi de kiem trung voi B3)."""
    bs = set(base_days)
    out, off_chain = [], None
    for D in base_days:
        F = D
        while F - ONE in bs:
            F -= ONE
        if off_chain == F:
            continue
        seg = eod[(eod.index >= F - ONE) & (eod.index <= D - ONE)]
        if np.exp(eod.get(D - ONE) - seg.min()) - 1 >= r:
            off_chain = F
            continue
        out.append(D)
    return out


def pack(days):
    s = rstr(ranges_of(days))
    by = pd.Series(1, index=pd.DatetimeIndex(days)).groupby(lambda x: x.year).sum().to_dict() if days else {}
    return dict(n_days=len(days), n_ranges=len(ranges_of(days)), ranges=s, sha256=hashlib.sha256(s.encode()).hexdigest(),
                by_year={int(k): int(v) for k, v in by.items()})


def main():
    os.makedirs(OUT, exist_ok=True)
    ed, eh = eod_dev(), eod_ho()
    D0, D1, H0, H1 = "2021-07-01", "2025-12-31", "2026-01-01", "2026-09-30"
    base_d, base_h = days_of(ed, -0.30, 30, D0, D1), days_of(eh, -0.30, 30, H0, H1)
    v2_d, v2_h = b3_days(ed, base_d, 0.20), b3_days(eh, base_h, 0.20)
    v2p_d, v2p_h = b3_perm_days(ed, base_d, 0.20), b3_perm_days(eh, base_h, 0.20)
    arms = {"V0": (336, "X14", base_d, base_h), "V1": (252, "V420", base_d, base_h), "V2": (336, "B3b_r0.20", v2_d, v2_h),
            "V3": (336, "VT25", days_of(ed, -0.25, 30, D0, D1), days_of(eh, -0.25, 30, H0, H1)),
            "V4": (336, "VL45", days_of(ed, -0.30, 45, D0, D1), days_of(eh, -0.30, 45, H0, H1))}
    out = {}
    for a, (h, src, dd_, hh_) in arms.items():
        out[a] = dict(ext_hours=h, total_hours=168 + h, same_as=src, dev=pack(dd_), ho=pack(hh_))
        out[a]["dev"]["symdiff_vs_V0"] = len(set(dd_) ^ set(base_d))
        out[a]["ho"]["symdiff_vs_V0"] = len(set(hh_) ^ set(base_h))
        log.info("%s ext=%d tong=%dh (=%s) | DEV %d ngay %d khoang sha %s symdiff %d %s | HO %d ngay sha %s symdiff %d %s", a, h, 168 + h,
                 src, out[a]["dev"]["n_days"], out[a]["dev"]["n_ranges"], out[a]["dev"]["sha256"][:8], out[a]["dev"]["symdiff_vs_V0"],
                 out[a]["dev"]["by_year"], out[a]["ho"]["n_days"], out[a]["ho"]["sha256"][:8], out[a]["ho"]["symdiff_vs_V0"],
                 out[a]["ho"]["ranges"])
    out["V2"]["dev"]["removed_vs_V0"] = [d.strftime("%Y-%m-%d") for d in sorted(set(base_d) - set(v2_d))]
    out["V2"]["ho"]["removed_vs_V0"] = [d.strftime("%Y-%m-%d") for d in sorted(set(base_h) - set(v2_h))]
    log.info("V2 bo ngay DEV %s | HO %s", out["V2"]["dev"]["removed_vs_V0"], out["V2"]["ho"]["removed_vs_V0"])
    pre, hof = json.load(open(TSX + "/flags.json")), json.load(open(TSX + "/ho/ho_flags.json"))
    t2 = json.load(open("/home/ubuntu/claude_master/tsx2sim/flags_variants.json"))["arms"]
    K6 = json.load(open(REPO + "/docs/result/tsx_v2/phaseB.json"))["checks"]["K6_on_days"]
    chk = dict(v0_dev=out["V0"]["dev"]["ranges"] == pre["ranges"] and out["V0"]["dev"]["sha256"] == pre["sha256"],
               v0_dev_sha_c79ef302=out["V0"]["dev"]["sha256"].startswith("c79ef302"),
               v0_ho=out["V0"]["ho"]["ranges"] == hof["ranges"] and out["V0"]["ho"]["sha256"] == hof["sha256"])
    for a, (h, src, _, _) in arms.items():
        if src in t2:
            chk[a + "_eq_tsx2_" + src] = (out[a]["dev"]["ranges"] == t2[src]["dev"]["ranges"] and out[a]["ho"]["ranges"] == t2[src]["ho"]["ranges"]
                                         and h == t2[src]["ext_hours"])
    chk["v2_dev_n_eq_K6"] = out["V2"]["dev"]["n_days"] == K6["B3b_r0.20"]
    chk["v2_subset_v0"] = set(v2_d) <= set(base_d) and set(v2_h) <= set(base_h)
    chk["v2_perm_identical_dev"] = v2p_d == v2_d
    chk["v2_perm_identical_ho"] = v2p_h == v2_h
    log.info("KIEM %s", chk)
    hard = [k for k in chk if not k.startswith("v2_perm")]
    assert all(chk[k] for k in hard), chk
    json.dump(dict(arms=out, checks=chk), open(OUT + "/flags_v3.json", "w"), indent=1)
    log.info("WROTE %s/flags_v3.json sha256 %s", OUT, hashlib.sha256(open(OUT + "/flags_v3.json", "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
