#!/usr/bin/env python3
"""So 2 output harness (out_*.csv.gz gate 33 / fund_*.csv.gz Tool1 45) — bit-level (chuoi in Java) + dung sai 1e-6*(1+|b|).
argv: ref.csv.gz new.csv.gz kind(gate|fund) out.json [--first ms] [--last ms] [--minutes-excl file]
Cot phu thuoc funding (PREREG_PARITY_V11_WINDOW §3) bao cao RIENG (khong tinh vao 'nonfund')."""
import argparse
import json
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("cmp_runs")
FUND_GATE = ["fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend"]
FUND_T1 = ["f%d" % i for i in list(range(17, 26)) + [32]]
OI_T1 = ["f%d" % i for i in range(40, 45)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref")
    ap.add_argument("new")
    ap.add_argument("kind", choices=["gate", "fund"])
    ap.add_argument("out")
    ap.add_argument("--first", type=int, default=None)
    ap.add_argument("--last", type=int, default=None)
    a = ap.parse_args()
    A = pd.read_csv(a.ref, dtype=str, keep_default_na=False)
    B = pd.read_csv(a.new, dtype=str, keep_default_na=False)
    key = ["min"] if a.kind == "gate" else ["min", "symbol"]
    for D in (A, B):
        D["_m"] = D["min"].astype(np.int64)
    if a.first is not None:
        A = A[A._m >= a.first]
        B = B[B._m >= a.first]
    if a.last is not None:
        A = A[A._m <= a.last]
        B = B[B._m <= a.last]
    if A.duplicated(key).any() or B.duplicated(key).any():
        log.error("khoa trung trong output (%s)", key)
    J = A.merge(B, on=key, how="outer", suffixes=("_a", "_b"), indicator=True)
    only_a = int((J._merge == "left_only").sum())
    only_b = int((J._merge == "right_only").sum())
    J = J[J._merge == "both"]
    cols = [c for c in A.columns if c not in key and c not in ("_m",)]
    excl = FUND_GATE if a.kind == "gate" else FUND_T1 + OI_T1
    res = {"ref": a.ref, "new": a.new, "kind": a.kind, "rows_ref": int(len(A)), "rows_new": int(len(B)), "rows_both": int(len(J)),
           "only_ref": only_a, "only_new": only_b, "cols": {}}
    bit_nonfund = np.ones(len(J), bool)
    tol_nonfund = np.ones(len(J), bool)
    for c in cols:
        x, y = J[c + "_a"].values, J[c + "_b"].values
        bit = x == y
        try:
            xf = pd.to_numeric(J[c + "_a"], errors="coerce").values
            yf = pd.to_numeric(J[c + "_b"], errors="coerce").values
            tol = bit | (np.abs(xf - yf) <= 1e-6 * (1 + np.abs(yf))) | (np.isnan(xf) & np.isnan(yf))
        except Exception:  # noqa: BLE001
            tol = bit
        res["cols"][c] = {"bit": float(bit.mean()) if len(bit) else None, "tol": float(tol.mean()) if len(tol) else None,
                          "n_bit_diff": int((~bit).sum()), "funding_dep": c in excl}
        if c not in excl:
            bit_nonfund &= bit
            tol_nonfund &= tol
    res["rows_bit_nonfund"] = float(bit_nonfund.mean()) if len(J) else None
    res["rows_tol_nonfund"] = float(tol_nonfund.mean()) if len(J) else None
    mins = J["min"].values
    bad = sorted(set(mins[~bit_nonfund].tolist()))
    res["minutes"] = int(len(set(mins.tolist())))
    res["minutes_bit_nonfund_all"] = int(res["minutes"] - len(bad))
    res["bad_minutes_nonfund"] = bad[:50]
    res["n_bad_minutes_nonfund"] = len(bad)
    res["cols_diff_nonfund"] = {c: v["n_bit_diff"] for c, v in res["cols"].items() if v["n_bit_diff"] and not v["funding_dep"]}
    res["cols_diff_fund"] = {c: v["n_bit_diff"] for c, v in res["cols"].items() if v["n_bit_diff"] and v["funding_dep"]}
    json.dump(res, open(a.out, "w"), indent=1)
    log.info("%s %s rows ref=%d new=%d both=%d only_ref=%d only_new=%d | nonfund bit=%.6f tol=%.6f bad_min=%d | diff_nonfund=%s | diff_fund=%s",
             a.kind, a.new, len(A), len(B), len(J), only_a, only_b, res["rows_bit_nonfund"] or -1, res["rows_tol_nonfund"] or -1,
             len(bad), res["cols_diff_nonfund"], res["cols_diff_fund"])


if __name__ == "__main__":
    main()
