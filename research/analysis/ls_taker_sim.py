#!/usr/bin/env python3
"""LS_TAKER_SIM — bien the PHI SIM (0,80% phang + funding, khong slip) cho 4 o CHINH (bao kem theo
pre-reg §2 "chi phi BIEN THE ... Bao kem, KHONG dung de phan quyet"). Dung nguyen ham harness.
"""
import importlib.util
import warnings
from datetime import datetime, timezone

import numpy as np

warnings.filterwarnings("ignore")
spec = importlib.util.spec_from_file_location("lst", "/home/ubuntu/src/BinanceFuturesJava/research/analysis/ls_taker.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
import json
UTC = timezone.utc


def main():
    meta = json.load(open(M.OUT + "/meta.json"))
    NH, ncol, T0, T0_MIN, H0 = meta["NH"], meta["ncol"], meta["T0"], meta["T0_MIN"], meta["H0"]
    lsg = np.load(M.OUT + "/lsg.npy", mmap_mode="r")
    lst = np.load(M.OUT + "/lst.npy", mmap_mode="r")
    tak = np.load(M.OUT + "/tak.npy", mmap_mode="r")
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

    def run(ffun, hold, fee, want=(9, 0)):
        acc = {g: [[], []] for g in list(want) + ["EW"]}
        for i in hw:
            j = i + hold
            if j >= NH:
                continue
            f = ffun(i); c = c5[i]
            u = np.isfinite(f) & np.isfinite(c) & np.isfinite(c5[j]) & (c > 0)
            if u.sum() < M.MIN_SYM:
                continue
            idx = np.flatnonzero(u)
            order = np.argsort(np.asarray(f[idx], dtype=np.float64), kind="stable")
            N = len(idx); dec = np.empty(N, dtype=np.int8)
            dec[order] = np.minimum(np.arange(N) * 10 // N, 9)
            net = (c5[j][u] / c5[i][u] - 1.0 - fee - (f5[j][u] - f5[i][u])).astype(np.float64)
            t = int(T0_MIN + i * 60)
            for g in want:
                m = dec == g
                acc[g][0].append(net[m]); acc[g][1].append(np.full(int(m.sum()), t, dtype=np.int64))
            acc["EW"][0].append(net); acc["EW"][1].append(np.full(N, t, dtype=np.int64))
        return {g: (np.concatenate(acc[g][0]), np.concatenate(acc[g][1])) for g in list(want) + ["EW"]}

    print("### BIEN THE PHI SIM (0,80%% phang + funding, KHONG slip) — W1, 24h")
    for nm, ffun, hold, want in (
            ("H1 log(lsg)", lambda i: logsafe(lsg[i]), 24, (9, 0)),
            ("H2 div", lambda i: logsafe(lst[i]) - logsafe(lsg[i]), 24, (9, 0)),
            ("H3var tak cs", lambda i: np.asarray(tak[i], dtype=np.float64), 24, (9, 0))):
        o = run(ffun, hold, M.FEE_SIM, want)
        for g in want:
            print("  %-14s %s: net=%+.4f%%" % (nm, "Q%d" % g, 100 * o[g][0].mean()))
        print("  %-14s EW: net=%+.4f%% | Q9-EW = %+.4f%%" % (nm, 100 * o["EW"][0].mean(),
              100 * (o[want[0]][0].mean() - o["EW"][0].mean())))
    # H3 MOM15 overlay
    z = np.load("/tmp/funding_factor/pools.npz")
    m_min = z["m_min"].astype(np.int64); m_valid = z["m_valid"]
    m_raw = z["m_raw"]; m_fund = z["m_fund"]
    base = m_raw[1].astype(np.float64) - m_fund[1].astype(np.float64)
    devm = (m_min >= W1_0) & (m_min < END)
    sel = devm & (((m_valid >> 1) & 1) == 1) & np.isfinite(base)
    mm = m_min[sel]; net = base[sel] - M.FEE_SIM
    ev = np.load(M.OUT + "/events_5m.npz")
    fv = ev["tak"][sel]
    ok = np.isfinite(fv)
    v = fv[ok]
    ter = np.minimum((np.argsort(np.argsort(v, kind="stable")) * 3) // len(v), 2)
    n_ = net[ok]
    print("  H3 tak(muc)   (MOM15 overlay, phí SIM): ter0=%+.4f%% ter2=%+.4f%% | ter2-ter0 = %+.4f%%" % (
        100 * n_[ter == 0].mean(), 100 * n_[ter == 2].mean(),
        100 * (n_[ter == 2].mean() - n_[ter == 0].mean())))


if __name__ == "__main__":
    main()
