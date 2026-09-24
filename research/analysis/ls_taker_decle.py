#!/usr/bin/env python3
"""LS_TAKER_DECLE — thang decile DAY DU 0..9 cho o CHINH cua H1 (log(ls_global), W1, 24h).

Pre-reg docs/prereg/PREREG_LS_TAKER.md §1.H1 ghi ro: "Do net trung binh TUNG decile + chenh Q_d - EW".
Script nay bo sung dung phan da dang ky do (khong phai post-hoc). Dung nguyen ham harness cua
research/analysis/ls_taker.py.
"""
import math
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import importlib.util
spec = importlib.util.spec_from_file_location("lst", "/home/ubuntu/src/BinanceFuturesJava/research/analysis/ls_taker.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

from datetime import datetime, timezone
UTC = timezone.utc


def main():
    meta = __import__("json").load(open(M.OUT + "/meta.json"))
    NH, ncol, T0, T0_MIN, H0 = meta["NH"], meta["ncol"], meta["T0"], meta["T0_MIN"], meta["H0"]
    lsg = np.load(M.OUT + "/lsg.npy", mmap_mode="r")
    c5 = np.load(M.OUT + "/c5.npy", mmap_mode="r")
    rg = np.load(M.OUT + "/rg.npy", mmap_mode="r")
    f5 = np.load(M.OUT + "/f5.npy", mmap_mode="r")
    M.OOS0 = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp()) // 60
    W1_0 = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp()) // 60
    END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()) // 60
    h_all = np.arange(H0, NH, dtype=np.int64)
    tm = T0_MIN + h_all * 60
    hw = h_all[(tm >= W1_0) & (tm < END)]

    def logsafe(x):
        x = np.asarray(x, dtype=np.float64)
        return np.where(x > 0, np.log(np.maximum(x, 1e-12)), np.nan)

    def net_of(i, j, u):
        return (c5[j][u] / c5[i][u] - 1.0 - M.FEE_RT - 0.5 * rg[i][u] / c5[i][u]
                - (f5[j][u] - f5[i][u])).astype(np.float64)

    acc = {g: [[], []] for g in list(range(10)) + ["EW"]}
    hold = 24
    for i in hw:
        j = i + hold
        if j >= NH:
            continue
        f = logsafe(lsg[i]); c = c5[i]
        u = np.isfinite(f) & np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
        if u.sum() < M.MIN_SYM:
            continue
        idx = np.flatnonzero(u)
        order = np.argsort(np.asarray(f[idx], dtype=np.float64), kind="stable")
        N = len(idx)
        dec = np.empty(N, dtype=np.int8)
        dec[order] = np.minimum(np.arange(N) * 10 // N, 9)
        net = net_of(i, j, u)
        tsm = int(T0_MIN + i * 60)
        for g in range(10):
            m = dec == g
            acc[g][0].append(net[m]); acc[g][1].append(np.full(int(m.sum()), tsm, dtype=np.int64))
        acc["EW"][0].append(net); acc["EW"][1].append(np.full(N, tsm, dtype=np.int64))
    R = []
    ew = None
    for g in list(range(10)) + ["EW"]:
        d = M.full(np.concatenate(acc[g][0]), np.concatenate(acc[g][1]), "H1 24h %s" % ("EW" if g == "EW" else "Q%d" % g), k=1)
        if g == "EW":
            ew = d
        R.append((g, d))
        print(M.line(d), flush=True)
    print()
    print("chenh vs EW (pp/lenh) @24h, W1:")
    print("  " + "  ".join("Q%d=%+.4f" % (g, 100 * (d["mean"] - ew["mean"])) for g, d in R if g != "EW"))
    print("  net>0 ? " + "  ".join("Q%d:%s" % (g, "CO" if d["mean"] > 0 else "khong") for g, d in R if g != "EW"))
    print("  EW net = %+.4f%%" % (100 * ew["mean"]))
    print("  so decile net>0 = %d/10" % sum(1 for g, d in R if g != "EW" and d["mean"] > 0))
    print("  decile co CI72h_x1.21 ngoai 0 (duong) = %s" % (
        [g for g, d in R if g != "EW" and d["ci_lo"] > 0] or "KHONG CO"))
    open("/tmp/ls_study/decle_h1.txt", "w").write("\n".join(M.line(d) for g, d in R) + "\n")


if __name__ == "__main__":
    main()
