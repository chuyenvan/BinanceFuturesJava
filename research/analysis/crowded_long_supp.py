#!/usr/bin/env python3
"""CROWDED_LONG_SUPP — bo tro SAU khi do (post-hoc): QC gia chet + robust winsor + bang cua so te nhat.

Vi sao ton tai: metric da dang ky o PREREG §4 "maxDD cua chuoi luu ke 24h-step" tra ve -100,00%
=> SUY BIEN, khong dung duoc. Nguyen nhan phai do lai (khong suy dien) va phai co phien ban thay the
co ghi nhan. Script nay (a) chan doan nguyen nhan, (b) do lai voi EW WINSOR (clip cross-section),
(c) in bang 10 cua so drop24 te nhat voi ngay + trang thai ON.

KHONG doi tieu chi phan quyet nao cua pre-reg. Thuan Python. Khong Java/sim. Khong push.
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
OUT = "/tmp/crowded"
UTC = timezone.utc
REP = []


def say(s=""):
    REP.append(s); print(s, flush=True)


def main():
    meta = json.load(open(PAN + "/meta.json"))
    NH, ncol, T0_MIN, H0 = meta["NH"], meta["ncol"], meta["T0_MIN"], meta["H0"]
    syms = meta["syms"]
    lsg = np.load(PAN + "/lsg.npy", mmap_mode="r")
    c5 = np.load(PAN + "/c5.npy", mmap_mode="r")
    rg = np.load(PAN + "/rg.npy", mmap_mode="r")
    f5 = np.load(PAN + "/f5.npy", mmap_mode="r")
    W1_0 = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp()) // 60
    END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp()) // 60
    CL.OOS0 = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp()) // 60
    OOS0 = CL.OOS0

    # ---- x_t + ON (giong crowded_long.py) ----
    allh = np.arange(H0, NH, dtype=np.int64)
    x = np.full(NH, np.nan); n_u = np.zeros(NH, dtype=np.int32)
    for i in allh:
        v = np.asarray(lsg[i], dtype=np.float64); c = np.asarray(c5[i], dtype=np.float64)
        u = np.isfinite(v) & (v > 0) & np.isfinite(c) & (c > 0)
        n_u[i] = int(u.sum())
        if n_u[i] >= CL.MIN_SYM:
            x[i] = np.median(np.log(np.maximum(v[u], 1e-12)))
    s_x = pd.Series(x)
    ON = {}
    for N in CL.NDAYS:
        win = N * 24
        q = s_x.rolling(win, min_periods=1).quantile(0.80).shift(1).values
        cnt = s_x.rolling(win, min_periods=1).count().shift(1).values
        ON[N] = np.where((cnt >= 0.9 * win) & np.isfinite(q) & np.isfinite(x), x > q, np.nan)
    hw = allh[(T0_MIN + allh * 60 >= W1_0) & (T0_MIN + allh * 60 < END)]

    say("### S1. QC metric da dang ky: vi sao maxDD(path) = -100,00%")
    say("Chuan doan: kem net 1h cua tung symbol, dem so o co net < -50% / < -90%.")
    ext = {}
    for H in (1, 24):
        cnt50 = 0; cnt90 = 0; ntot = 0
        worst = []
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
            idxs = np.flatnonzero(u)
            ntot += len(nt)
            cnt50 += int((nt < -0.5).sum()); cnt90 += int((nt < -0.9).sum())
            k = int(np.argmin(nt))
            worst.append((float(nt[k]), syms[idxs[k]], int(T0_MIN + i * 60), float(ci[k]), float(cj[k])))
        worst.sort()
        ext[H] = dict(ntot=ntot, n_lt50=cnt50, n_lt90=cnt90)
        say("  H=%2dh: %d o symbol-gio | net < -50%%: %d (%.4f%%) | net < -90%%: %d (%.5f%%)" % (
            H, ntot, cnt50, 100 * cnt50 / ntot, cnt90, 100 * cnt90 / ntot))
        say("     5 o xau nhat:")
        for w in worst[:5]:
            say("       %8.2f%%  %-12s %s  c5: %.10f -> %.10f" % (
                100 * w[0], w[1], datetime.fromtimestamp(w[2] * 60, UTC).strftime("%Y-%m-%d %H:%M"), w[3], w[4]))
    say("  => 1 o -99,9%% dong gop ~1/n vao EW; chuoi luu ke (1+r) -> 0 => maxDD(path) = -100%%. SUY BIEN.")
    say("  => Phien ban thay the (post-hoc, ghi nhan): EW WINSOR clip cross-section tai [p1,p99] cua chinh gio do.")

    # ---- S2: EW winsor ----
    say("")
    say("### S2. EW WINSOR (clip cross-section [p1,p99] moi gio) — ON vs OFF")
    EWw = {}
    for H in (1, 4, 24):
        n_ = np.full(NH, np.nan); ts_ = np.zeros(NH, dtype=np.int64); nw = np.full(NH, np.nan)
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
            lo, hi = np.percentile(nt, [1, 99])
            nw[i] = nt.clip(lo, hi).mean()
            n_[i] = nt.mean(); ts_[i] = T0_MIN + i * 60
        m = np.isfinite(n_)
        EWw[H] = (n_[m], ts_[m], nw[m])
        say("  H=%2dh: EW raw TB = %+.4f%% | EW winsor TB = %+.4f%%" % (H, 100 * n_[m].mean(), 100 * nw[m].mean()))
    T_RES = {}
    for H in (1, 24):
        _, ts_, w_ = EWw[H]
        idx = ((ts_ - T0_MIN) // 60).astype(np.int64)
        for N in CL.NDAYS:
            st = ON[N][idx]
            m1 = st == 1; m0 = st == 0
            a = w_[m1]; b = w_[m0]
            t1 = CL.tails(a); t0 = CL.tails(b)
            c = CL.contrast(a, ts_[m1], b, ts_[m0], "EWwins H%dh N%dd ON-OFF" % (H, N), k=CL.KFAM)
            say("  H=%2dh N=%2dd: ON n=%5d mean=%+.4f%% CVaR5=%+.4f%% p01=%+.4f%% | OFF mean=%+.4f%% CVaR5=%+.4f%% p01=%+.4f%%" % (
                H, N, len(a), 100 * t1["mean"], 100 * t1["cvar5"], 100 * t1["p01"],
                100 * t0["mean"], 100 * t0["cvar5"], 100 * t0["p01"]))
            CL.row_contrast(c)
            # kinh te luat tren winsor
            keep = np.isfinite(st)
            ww = w_[keep]; tt = ts_[keep]; s2 = st[keep]
            rn = 0.5 * ww * (s2 == 1) + ww * (s2 == 0)
            say("      rule(0,5): mean=%+.4f%% (D=%+.4f%%) CVaR5=%+.4f%% (D=%+.4f%%) maxDD(path)=%+.2f%% (baseline %+.2f%%)" % (
                100 * rn.mean(), 100 * (rn.mean() - ww.mean()),
                100 * CL.tails(rn)["cvar5"], 100 * (CL.tails(rn)["cvar5"] - CL.tails(ww)["cvar5"]),
                100 * CL.path_maxdd(rn, tt), 100 * CL.path_maxdd(ww, tt)))
            T_RES["wins_H%dh_N%d" % (H, N)] = dict(c=c, rule_mean=float(rn.mean()), base_mean=float(ww.mean()),
                                                   maxdd_rule=float(CL.path_maxdd(rn, tt)),
                                                   maxdd_base=float(CL.path_maxdd(ww, tt)))
    # ON-OFF tren EW winsor cho Q9-style khong can; dong them: contrast MDE cho MOM15
    say("")
    say("### S3. MDE cua TUONG PHAN (proxy) — de doi chieu voi hieu ung MOM15 24h")
    z = np.load(CL.POOLS)
    m_min = z["m_min"].astype(np.int64); m_valid = z["m_valid"]; m_raw = z["m_raw"]
    m_slip = z["m_slip"]; m_fund = z["m_fund"]
    devm = (m_min >= int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) // 60) & (m_min < END)
    base24 = m_raw[1].astype(np.float64) - m_slip.astype(np.float64) - m_fund[1].astype(np.float64)
    devm &= (((m_valid >> 1) & 1) == 1) & np.isfinite(base24)
    hm = (m_min // 60) * 60
    hi = ((hm - T0_MIN) // 60).astype(np.int64)
    okh = (hi >= 0) & (hi < NH)
    inw1 = (m_min >= W1_0) & (m_min < END)
    for N in CL.NDAYS:
        onv = np.full(len(m_min), np.nan); onv[okh] = ON[N][hi[okh]]
        net = base24 - CL.FEE_RT
        sel = devm & np.isfinite(onv) & inw1
        a = net[sel & (onv == 1)]; b = net[sel & (onv == 0)]
        ta = m_min[sel & (onv == 1)]; tb = m_min[sel & (onv == 0)]
        c = CL.contrast(a, ta, b, tb, "MOM15 H24 N%dd ON-OFF" % N, k=CL.KFAM)
        CL.row_contrast(c)
        say("      (doi chieu: MDE_adj nhanh ON = %+.4f%%; CI72h_x1.21 cua tuong phan = [%+.4f%%, %+.4f%%])" % (
            100 * CL.mde_half(a, ta // (CL.BLOCK_H * 60))[0] * np.sqrt(CL.KFAM), 100 * c["ci_lo"], 100 * c["ci_hi"]))
        T_RES["mom_contrast_N%d" % N] = c
    json.dump(T_RES, open(OUT + "/supp_crowded.json", "w"), indent=1)
    open(OUT + "/report_crowded_supp.txt", "w").write("\n".join(REP) + "\n")


if __name__ == "__main__":
    main()
