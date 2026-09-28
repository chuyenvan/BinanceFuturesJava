#!/usr/bin/env python3
"""ofi_ext_trades_build.py — PREREG_OFI_MONEY_REORIENT: dung file ung vien B2 `ofi_ext_trades.parquet`.

Tap cap MOI = ( U_{arm in candidate/baseline_fresh/noise} U_{seed in 43,44,45} global-top-8(arm,seed) ) \\ P32,
tren dung tap tick cua P32. global-top-8 = 8 coin co ORIENT*score LON nhat trong toan bo symbol co diem o tick do
(ORIENT=-1 <=> score THAP = TOT, dung chieu; ORIENT=+1 = chieu CU, chi de TAI LAP file cu).
Dinh dang GIONG file cu (dataset chuyendinh/ofi-money-ext-trades): cot ts, sym, score; sap (ts, sym);
score = so thu tu trong tick (0..n-1) => mr_label_build.py (sort score tang, head(KMAX)) giu NGUYEN thu tu.

  python3 ofi_ext_trades_build.py --kdirs .../kout43,.../kout44,.../kout45 --orient -1 --out ofi_ext_trades.parquet
  python3 ofi_ext_trades_build.py ... --orient 1 --compare <file cu>   # kiem tai lap
"""
import argparse, hashlib, os
import numpy as np, pandas as pd

LABEL = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
KMAP = {"candidate": "pred_ofi_candidate_v2.parquet", "baseline_fresh": "pred_baseline_fresh.parquet",
        "noise_ofi_check": "pred_ofi_noise_v2.parquet"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kdirs", required=True)
    ap.add_argument("--orient", type=int, default=-1, choices=[-1, 1])
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--out", required=True)
    ap.add_argument("--compare", default=None)
    a = ap.parse_args()
    P = pd.read_parquet(LABEL, columns=["ts", "symId"])
    ticks = np.sort(P.ts.unique())
    p32 = set(zip(P.ts.to_numpy(np.int64), P.symId.to_numpy(np.int64)))
    sel = []
    for kd in a.kdirs.split(","):
        for arm, fn in KMAP.items():
            p = pd.read_parquet(os.path.join(kd, fn), columns=["ts", "sym", "score"])
            p = p[p.ts.isin(ticks) & p.score.notna()].copy()
            p["s"] = a.orient * p.score.to_numpy(np.float64)
            p = p.sort_values(["ts", "s"], ascending=[True, False], kind="stable")
            t = p.groupby("ts", sort=True).head(a.k)[["ts", "sym"]]
            n_in = sum((x, y) in p32 for x, y in zip(t.ts.to_numpy(np.int64), t.sym.to_numpy(np.int64)))
            print("%-44s %-16s top%d=%d  trong P32=%d (%.2f%%)" % (kd, arm, a.k, len(t), n_in, 100.0 * n_in / len(t)), flush=True)
            sel.append(t)
    U = pd.concat(sel).drop_duplicates()
    m = np.array([(x, y) not in p32 for x, y in zip(U.ts.to_numpy(np.int64), U.sym.to_numpy(np.int64))])
    N = U[m].sort_values(["ts", "sym"], kind="stable").reset_index(drop=True)
    N["score"] = N.groupby("ts").cumcount().astype(np.float64)
    N = N[["ts", "sym", "score"]].astype({"ts": np.int64, "sym": np.int64})
    per = N.groupby("ts").size()
    print("HOP=%d cap | NGOAI P32 (MOI)=%d cap, %d tick (/%d), %d sym | moi/tick TB=%.2f max=%d" % (
        len(U), len(N), N.ts.nunique(), len(ticks), N.sym.nunique(),
        len(N) / len(ticks), per.max() if len(per) else 0), flush=True)
    N.to_parquet(a.out, index=False)
    print("WROTE %s sha256=%s" % (a.out, hashlib.sha256(open(a.out, "rb").read()).hexdigest()), flush=True)
    if a.compare:
        O = pd.read_parquet(a.compare)
        so = set(zip(O.ts, O.sym)); sn = set(zip(N.ts, N.sym))
        same_rows = len(O) == len(N) and (O[["ts", "sym", "score"]].reset_index(drop=True)
                                          .equals(N[["ts", "sym", "score"]].reset_index(drop=True)))
        print("COMPARE vs %s: cu=%d moi=%d | chi_cu=%d chi_moi=%d | bang_giong_het=%s" % (
            a.compare, len(so), len(sn), len(so - sn), len(sn - so), same_rows), flush=True)


if __name__ == "__main__":
    main()
