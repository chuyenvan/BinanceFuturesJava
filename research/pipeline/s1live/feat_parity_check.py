"""CONG KHOP FEATURE S1 — so 7 feature GIA tinh boi Java S1FeatureLive tu nguon LIVE
(Aerospike 242 kline_1m_opt gop 1m -> 1h) voi `featv2/feat_v2_x1.parquet` (nguon offline
CLOSES_1H.bin = kline 1h Vision). In spearman + max|delta| tung feature cho TUNG quy uoc gop.

Dung: python3 feat_parity_check.py <csv_prev> <csv_open> <ts_from> <ts_to>
"""
import logging as _logging, sys as _sys
_logging.basicConfig(level=_logging.INFO, format="%(message)s", stream=_sys.stdout)
LOG = _logging.getLogger(__name__)


def _p(*a):
    LOG.info(" ".join(str(x) for x in a))


import numpy as np
import pandas as pd
from scipy.stats import spearmanr

FE = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d"]
FEAT = "/home/ubuntu/featv2/feat_v2_x1.parquet"


def load_ref(t0, t1):
    F = pd.read_parquet(FEAT, columns=["ts", "sym"] + FE)
    F = F[(F.ts >= t0) & (F.ts < t1)].copy()
    return F


def compare(tag, csv, F):
    L = pd.read_csv(csv)
    _p(f"\n===== quy uoc gop 1m->1h: {tag} =====")
    _p(f"live rows={len(L)} syms={L.sym.nunique()} ticks={L.ts.nunique()}")
    _p(f"ref  rows={len(F)} syms={F.sym.nunique()} ticks={F.ts.nunique()}")
    M = F.merge(L, on=["ts", "sym"], how="inner", suffixes=("_ref", "_live"))
    _p(f"ghep cap duoc: {len(M)} dong "
       f"({100.0 * len(M) / max(len(F), 1):.2f}% cua ref, {100.0 * len(M) / max(len(L), 1):.2f}% cua live)")
    rows = []
    for f in FE:
        a = M[f + "_ref"].to_numpy(dtype=np.float64)
        b = M[f + "_live"].to_numpy(dtype=np.float64)
        ok = ~(np.isnan(a) | np.isnan(b))
        n = int(ok.sum())
        if n < 100:
            rows.append((f, n, np.nan, np.nan, np.nan))
            continue
        sp = spearmanr(a[ok], b[ok]).correlation
        d = np.abs(a[ok] - b[ok])
        rows.append((f, n, sp, float(d.max()), float(np.median(d))))
    D = pd.DataFrame(rows, columns=["feature", "n_pair", "spearman", "max_abs_d", "med_abs_d"])
    _p(D.to_string(index=False, float_format=lambda x: f"{x:.9g}"))
    bad = D[(D.spearman < 0.999) | D.spearman.isna()]
    _p(f"CONG (spearman >= 0.999 cho 7 feature gia): {'PASS' if bad.empty else 'FAIL'}"
       + ("" if bad.empty else " -- feature truot: " + ",".join(bad.feature)))
    return D, bad.empty


if __name__ == "__main__":
    csv_prev, csv_open = _sys.argv[1], _sys.argv[2]
    t0, t1 = int(_sys.argv[3]), int(_sys.argv[4])
    F = load_ref(t0, t1)
    r = {}
    for tag, c in (("prev", csv_prev), ("open", csv_open)):
        r[tag] = compare(tag, c, F)[1]
    _p("\n== TONG KET ==")
    for k, v in r.items():
        _p(f"  {k}: {'PASS' if v else 'FAIL'}")
