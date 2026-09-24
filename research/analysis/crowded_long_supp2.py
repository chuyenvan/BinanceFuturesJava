#!/usr/bin/env python3
"""CROWDED_LONG_SUPP2 — (S4) dia phuong hoa DUOI: duoi co TAP TRUNG vao cua so ON khong?

Cau hoi (2) cua nhien vu chi co cua neu cua so ON chua TY LE KHONG CAN XUNG cua duoi.
Do: ty le ON trong 5%/1% cua so xau nhat (EW 24h/1h, MOM15 24h/4h) so voi tan suat ON nen;
bang 10 cua so drop24 te nhat cua KEEPLEG0 (ngay + trang thai ON);
trang thai ON quanh cu giam lon nhat cua mau (2025-10-10).

Post-hoc, khong doi tieu chi phan quyet. Thuan Python. Khong Java/sim. Khong push.
"""
import json
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import crowded_long as CL  # noqa: E402

PAN = "/tmp/crowded"
SERIES = "/home/ubuntu/intradaydd/series.npz"
UTC = timezone.utc
REP = []


def say(s=""):
    REP.append(s); print(s, flush=True)


def onshare(v, st, q):
    """ty le ON trong q% cua so xau nhat cua v + lift"""
    k = max(1, int(round(q / 100.0 * len(v))))
    o = np.argsort(v)[:k]
    return float((st[o] == 1).mean()), float(np.nanmean(st)), k


def main():
    meta = json.load(open(PAN + "/meta.json"))
    NH, T0_MIN, H0 = meta["NH"], meta["T0_MIN"], meta["H0"]
    syms = meta["syms"]
    lsg = np.load(PAN + "/lsg.npy", mmap_mode="r")
    c5 = np.load(PAN + "/c5.npy", mmap_mode="r")
    rg = np.load(PAN + "/rg.npy", mmap_mode="r")
    f5 = np.load(PAN + "/f5.npy", mmap_mode="r")
    W1_0 = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp()) // 60
    END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()) // 60
    CL.OOS0 = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp()) // 60

    allh = np.arange(H0, NH, dtype=np.int64)
    x = np.full(NH, np.nan)
    for i in allh:
        v = np.asarray(lsg[i], dtype=np.float64); c = np.asarray(c5[i], dtype=np.float64)
        u = np.isfinite(v) & (v > 0) & np.isfinite(c) & (c > 0)
        if u.sum() >= CL.MIN_SYM:
            x[i] = np.median(np.log(np.maximum(v[u], 1e-12)))
    s_x = pd.Series(x)
    ON = {}
    for N in CL.NDAYS:
        win = N * 24
        q = s_x.rolling(win, min_periods=1).quantile(0.80).shift(1).values
        cnt = s_x.rolling(win, min_periods=1).count().shift(1).values
        ON[N] = np.where((cnt >= 0.9 * win) & np.isfinite(q) & np.isfinite(x), x > q, np.nan)
    hw = allh[(T0_MIN + allh * 60 >= W1_0) & (T0_MIN + allh * 60 < END)]

    # EW series
    EW = {}
    for H in (1, 24):
        n_ = np.full(NH, np.nan); ts_ = np.zeros(NH, dtype=np.int64)
        for i in hw:
            j = i + H
            if j >= NH:
                continue
            ci = np.asarray(c5[i], dtype=np.float64); cj = np.asarray(c5[j], dtype=np.float64)
            lv = np.asarray(lsg[i], dtype=np.float64)
            u = np.isfinite(ci) & (ci > 0) & np.isfinite(cj) & np.isfinite(lv) & (lv > 0)
            if u.sum() < CL.MIN_SYM:
                continue
            nt = (cj[u] / ci[u] - 1.0 - CL.FEE_RT - 0.5 * np.asarray(rg[i], dtype=np.float64)[u] / ci[u]
                  - (np.asarray(f5[j], dtype=np.float64)[u] - np.asarray(f5[i], dtype=np.float64)[u]))
            n_[i] = nt.mean(); ts_[i] = T0_MIN + i * 60
        m = np.isfinite(n_)
        EW[H] = (n_[m], ts_[m])

    say("### S4. DUOI CO TAP TRUNG VAO CUA SO ON KHONG? (ty le ON trong nhom xau nhat, so tan suat ON nen)")
    say("%-22s %8s %10s %10s %10s %8s" % ("series", "n", "ON nen", "ON trong5%", "ON trong1%", "lift5%"))
    T = {}
    for H in (1, 24):
        n_, ts_ = EW[H]
        idx = ((ts_ - T0_MIN) // 60).astype(np.int64)
        for N in CL.NDAYS:
            st = ON[N][idx]
            keep = np.isfinite(st)
            v = n_[keep]; s = st[keep].astype(int)
            s5, base, k5 = onshare(v, s, 5.0)
            s1, _, k1 = onshare(v, s, 1.0)
            say("  EW%2dh N=%2dd%s %8d %9.1f%% %9.1f%% %9.1f%% %7.2fx" % (
                H, N, " (1%)" if False else "    ", len(v), 100 * base, 100 * s5, 100 * s1, s5 / base))
            T["EW%d_N%d" % (H, N)] = dict(n=len(v), base=base, on5=s5, on1=s1, lift5=s5 / base)
    # MOM15
    z = np.load(CL.POOLS)
    m_min = z["m_min"].astype(np.int64); m_valid = z["m_valid"]; m_raw = z["m_raw"]
    m_slip = z["m_slip"]; m_fund = z["m_fund"]
    devm = (m_min >= int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) // 60) & (m_min < END)
    hmm = (m_min // 60) * 60
    hi = ((hmm - T0_MIN) // 60).astype(np.int64)
    okh = (hi >= 0) & (hi < NH)
    inw1 = (m_min >= W1_0) & (m_min < END)
    for J, H in ((1, 24), (0, 4)):
        base_v = m_raw[J].astype(np.float64) - m_slip.astype(np.float64) - m_fund[J].astype(np.float64)
        dd = devm & (((m_valid >> 1) & 1) == 1) & np.isfinite(base_v)
        net = base_v - CL.FEE_RT
        for N in CL.NDAYS:
            onv = np.full(len(m_min), np.nan); onv[okh] = ON[N][hi[okh]]
            sel = dd & np.isfinite(onv) & inw1
            v = net[sel]; s = (onv[sel] == 1).astype(int)
            s5, base, _ = onshare(v, s, 5.0)
            s1, _, _ = onshare(v, s, 1.0)
            say("  MOM15 %2dh N=%2dd     %8d %9.1f%% %9.1f%% %9.1f%% %7.2fx" % (
                H, N, len(v), 100 * base, 100 * s5, 100 * s1, s5 / base))
            T["MOM%d_N%d" % (H, N)] = dict(n=len(v), base=base, on5=s5, on1=s1, lift5=s5 / base)

    # ---- bang 10 cua so drop24 te nhat (KEEPLEG0) ----
    say("")
    say("### S5. 10 cua so drop24 TE NHAT cua KEEPLEG0 (mark=close) + trang thai ON")
    zz = np.load(SERIES)
    L = len(zz["c_KEEPLEG0"])
    E = zz["c_KEEPLEG0"]
    hwL = hw[((T0_MIN + hw * 60) - int(pd.Timestamp("2021-07-01").timestamp()) // 60 + 24 * 60) <= L - 1]
    M0 = int(pd.Timestamp("2021-07-01").timestamp()) // 60
    hiL = ((T0_MIN + hwL * 60) - M0).astype(np.int64)
    rmin = pd.Series(E[::-1]).rolling(1440, min_periods=1).min().values
    drop = rmin[::-1][1:][hiL] / E[hiL] - 1.0
    o10 = np.argsort(drop)[:10]
    say("%-3s %-16s %10s %10s %10s" % ("#", "gio bat dau (UTC)", "drop24%", "ON N=30", "ON N=90"))
    for r, q in enumerate(o10):
        tmin = int((T0_MIN + hwL[q] * 60))
        hh = int((tmin - T0_MIN) // 60)
        say("%-3d %-16s %9.3f%% %10s %10s" % (
            r + 1, datetime.fromtimestamp(tmin * 60, UTC).strftime("%Y-%m-%d %H:%M"), 100 * drop[q],
            int(ON[30][hh]) if np.isfinite(ON[30][hh]) else "n/a",
            int(ON[90][hh]) if np.isfinite(ON[90][hh]) else "n/a"))
    # ---- trang thai ON quanh 2025-10-10 ----
    say("")
    say("### S6. Trang thai ON quanh cu giam lon nhat cua mau (2025-10-10 21:20Z)")
    for w0, w1, tag in (("2025-09-25", "2025-10-11", "dinh->day cua cu giam toan ky"),):
        a = int(pd.Timestamp(w0).timestamp()) // 60; b = int(pd.Timestamp(w1).timestamp()) // 60
        m = (T0_MIN + hw * 60 >= a) & (T0_MIN + hw * 60 <= b)
        for N in CL.NDAYS:
            say("  N=%2dd: %% gio ON trong [%s..%s] = %.1f%% (n=%d) | %% gio ON ca W1 = %.1f%%" % (
                N, w0, w1, 100 * np.nanmean(ON[N][hw][m]), int(m.sum()), 100 * np.nanmean(ON[N][hw])))
    say("")
    say("### S8. Jaccard dung nghia (ON vs vol-ter2 / BTC-24h-am / BTC<MA30)")
    lr = np.full(NH, np.nan)
    for i in allh:
        if i < 1:
            continue
        c0 = np.asarray(c5[i - 1], dtype=np.float64); c1 = np.asarray(c5[i], dtype=np.float64)
        u = np.isfinite(c0) & (c0 > 0) & np.isfinite(c1) & (c1 > 0)
        if u.sum() >= CL.MIN_SYM:
            r_ = np.log(c1[u] / c0[u]); lr[i] = r_.std(ddof=1)
    lw = lr[hw]; okv = np.isfinite(lw)
    vt = np.full(NH, -1, dtype=np.int8)
    vt[hw[okv]] = np.minimum((np.argsort(np.argsort(lw[okv], kind="stable")) * 3) // int(okv.sum()), 2)
    btcc = np.asarray(c5[:, meta["btc_col"]], dtype=np.float64)
    ma = pd.Series(btcc).rolling(30 * 24, min_periods=30 * 24).mean().values
    btcma = btcc / ma - 1.0
    btc24 = np.full(NH, np.nan); btc24[24:] = btcc[24:] / btcc[:-24] - 1.0
    for N in CL.NDAYS:
        o = (ON[N][hw] == 1)
        for tag, s in (("vol-ter2", vt[hw] == 2), ("BTC24h<0", btc24[hw] < 0), ("BTC<MA30", btcma[hw] < 0)):
            inter = float((o & s).sum()); uni = float((o | s).sum())
            say("  N=%2dd %-9s Jaccard=%.3f | |ON n vol|=%.2f" % (N, tag, inter / uni, inter / max(1.0, o.sum())))
    say("")
    say("### S7. Do dai doan ON (tan suat can thiep)")
    for N in CL.NDAYS:
        o = ON[N][hw]; bb = (o == 1).astype(np.int8)
        d = np.diff(np.concatenate([[0], bb, [0]]))
        st = np.flatnonzero(d == 1); en = np.flatnonzero(d == -1); runs = en - st
        say("  N=%dd: %d doan ON | <=2h: %.0f%% | <=6h: %.0f%% | <=24h: %.0f%% | trung vi %.1fh | dai nhat %dh (%.0f ngay)" % (
            N, len(runs), 100 * (runs <= 2).mean(), 100 * (runs <= 6).mean(), 100 * (runs <= 24).mean(),
            np.median(runs), runs.max(), runs.max() / 24.0))
    json.dump(T, open(PAN + "/supp2_crowded.json", "w"), indent=1)
    open(PAN + "/report_crowded_supp2.txt", "w").write("\n".join(REP) + "\n")
    say("")
    json.dump(T, open(PAN + "/supp2_crowded.json", "w"), indent=1)
    open(PAN + "/report_crowded_supp2.txt", "w").write("\n".join(REP) + "\n")


if __name__ == "__main__":
    main()
