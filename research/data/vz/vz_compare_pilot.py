"""1a - byte-exact comparison of the new-encoding build vs pilot v1.

Compares common columns (ts, sym, every shared value column) as raw bit
patterns (int64 view for floats). Only allowed differences:
  kline1m : v2 adds `active`
  basis1m : v2 drops `prem_open`, adds `active`

Usage: vz_compare_pilot.py <v1_dir> <v2_dir> [ym]
"""
import json
import os
import sys

import numpy as np
import pyarrow.parquet as pq

KLINE_COLS = ["ts", "open", "high", "low", "close", "volume", "quote_volume",
              "n_trades", "taker_buy_base", "taker_buy_quote"]
BASIS_COLS = ["ts", "prem_high", "prem_low", "prem_close", "mark_close", "index_close"]


def bits_equal(a, b):
    if a.dtype.kind == "f":
        return np.array_equal(a.view(np.int64), b.view(np.int64))
    if a.dtype.kind in "iu" and a.dtype.itemsize == b.dtype.itemsize:
        return np.array_equal(a, b)
    return np.array_equal(a.astype(str), b.astype(str))


def compare(ds, cols, v1p, v2p):
    f1 = pq.ParquetFile(v1p)
    f2 = pq.ParquetFile(v2p)
    if f1.num_row_groups != f2.num_row_groups:
        return {"status": "FAIL", "reason": "row group count differs",
                "v1_rg": f1.num_row_groups, "v2_rg": f2.num_row_groups}
    bad = []
    bad_sym = 0
    total_rows = 0
    for i in range(f1.num_row_groups):
        t1 = f1.read_row_group(i, columns=cols + ["sym"]).to_pandas()
        t2 = f2.read_row_group(i, columns=cols + ["sym"]).to_pandas()
        s1 = str(t1["sym"].iloc[0]) if len(t1) else ""
        s2 = str(t2["sym"].iloc[0]) if len(t2) else ""
        if s1 != s2 or len(t1) != len(t2):
            bad_sym += 1
            bad.append({"rg": i, "sym_v1": s1, "sym_v2": s2,
                        "rows_v1": len(t1), "rows_v2": len(t2)})
            continue
        total_rows += len(t1)
        for c in cols:
            if not bits_equal(t1[c].to_numpy(), t2[c].to_numpy()):
                bad.append({"rg": i, "sym": s1, "col": c})
                if len(bad) > 50:
                    break
        if len(bad) > 50:
            break
    return {"status": "PASS" if not bad else "FAIL",
            "rows_compared": total_rows, "row_groups": f1.num_row_groups,
            "sym_mismatch": bad_sym, "mismatches": bad}


def main():
    v1_dir, v2_dir = sys.argv[1], sys.argv[2]
    ym = sys.argv[3] if len(sys.argv) > 3 else "2024-08"
    year = ym[:4]
    out = {"ym": ym, "datasets": {}}
    for ds, cols in [("kline1m", KLINE_COLS), ("basis1m", BASIS_COLS)]:
        v1p = os.path.join(v1_dir, "%s-%s.parquet" % (ds, ym))
        v2p = os.path.join(v2_dir, ds, year, ym + ".parquet")
        out["datasets"][ds] = compare(ds, cols, v1p, v2p)
        out["datasets"][ds]["v1_bytes"] = os.path.getsize(v1p)
        out["datasets"][ds]["v2_bytes"] = os.path.getsize(v2p)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
