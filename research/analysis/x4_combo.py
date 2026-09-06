"""X4 run 11 - kiem to hop X4_COMBO (G=0.12, W=0.05, H=0.20) so voi PARITY.

PREREG_X4 muc 6.4: neu X4_COMBO xau hon tong hop cac truc rieng le o mean(profit|SM)
NGOAI CI thi GIU BASE. Ngoai ra in du bang de bao cao.
"""
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C
import x4_rates as X

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

T = "X4_COMBO"
X.THR[T] = 0.20
X.CFG[T] = (0.12, 0.05, 0.5)


def main():
    tags = [X.PARITY, "X4_G12", "X4_W05", "X4_H20", T]
    dd = {t: X.trades4(t) for t in tags}
    r = {t: X.rates4(dd[t]) for t in tags}

    log.info("=== RUN 11: X4_COMBO vs cac truc rieng le ===")
    log.info("%-10s %6s %7s %7s %9s %9s %9s %9s %9s", "tag", "n", "win%", "TSl%",
             "mean|SM", "med|SM", "p90|SM", "meanP", "sumPnl|SM")
    for t in tags:
        log.info("%-10s %6.0f %7.2f %7.2f %9.3f %9.3f %9.3f %9.3f %9.0f", t, r[t]["n"],
                 r[t]["win"], r[t]["tsloss"], r[t]["mp_sm"], r[t]["medsm"], r[t]["p90sm"],
                 r[t]["meanP"], r[t]["sumpnl_sm"])
    base = r[X.PARITY]["mp_sm"]
    add = sum(r[t]["mp_sm"] - base for t in ("X4_G12", "X4_W05", "X4_H20"))
    log.info("")
    log.info("Tong hop tuyen tinh 3 truc: base %.3f + (%.3f) = %.3f | COMBO thuc te %.3f | lech %.3f",
             base, add, base + add, r[T]["mp_sm"], r[T]["mp_sm"] - (base + add))

    log.info("")
    log.info("=== C4: n STOP_LOSS_DONE + ghep (sym,start) voi PARITY ===")
    pk = dd[X.PARITY][dd[X.PARITY].leg == 0].drop_duplicates(
        subset=["sym", "start"]).set_index(["sym", "start"])["status"]
    d = dd[T][dd[T].leg == 0].drop_duplicates(subset=["sym", "start"]).set_index(
        ["sym", "start"])["status"]
    common = d.index.intersection(pk.index)
    a, b = d.loc[common], pk.loc[common]
    log.info("n_SL COMBO=%d parity=%d | ghep %.1f%% | SM->SL=%d SL->SM=%d",
             r[T]["n_sl"], r[X.PARITY]["n_sl"], 100.0 * len(common) / len(d),
             int(((b == "STOP_MARKET_DONE") & (a == "STOP_LOSS_DONE")).sum()),
             int(((b == "STOP_LOSS_DONE") & (a == "STOP_MARKET_DONE")).sum()))

    log.info("")
    log.info("=== NHANH TRAILING (thr 0.20, capS 0.12, capW 0.05) ===")
    dl = dd[T][dd[T].leg == 0]
    st = dl[dl.symbolPred.notna() & (dl.symbolPred <= 0.20)]
    wk = dl[dl.symbolPred.isna() | (dl.symbolPred > 0.20)]
    f = lambda g: g.loc[g.status == "STOP_MARKET_DONE", "profit"]
    log.info("nSTRONG=%d nWEAK=%d STRONG%%=%.1f | mSM_STRONG=%.3f mSM_WEAK=%.3f",
             len(st), len(wk), 100.0 * len(st) / len(dl), f(st).mean(), f(wk).mean())

    log.info("")
    ci = X.ci_pair(dd[T], dd[X.PARITY])
    log.info("--- CI khoi-72h x1.21 : %s - %s [TOAN CUA SO] ---", T, X.PARITY)
    log.info("%-9s %10s %11s %11s %8s", "rate", "hieu", "lo", "hi", "ngoaiCI")
    nout = 0
    for k in X.KEYS4:
        o, lo, hi, o2 = ci[k]
        nout += int(o2 and k in X.QUALITY)
        log.info("%-9s %10.3f %11.3f %11.3f %8s", X.LBL[k], o, lo, hi, "YES" if o2 else "-")
    log.info("  => rate CHAT LUONG ngoai CI: %d", nout)

    log.info("")
    log.info("=== RANG BUOC CUNG THEO NAM ===")
    s = C.equity(T)
    ok = True
    for y, sy in s.groupby(s.index.year):
        ddv = (sy / sy.cummax() - 1) * 100
        uw = sy < sy.cummax()
        uwmax = int(uw.groupby((~uw).cumsum()).sum().max())
        qe = sy.resample("QE").last()
        q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
        qr = (qe.values / q0.values - 1) * 100
        ry = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
        good = (ddv.min() >= -15) and (ry >= 0) and (qr.min() >= -5)
        ok &= good
        log.info("%d maxDD=%.2f UW=%d ret=%.2f qmin=%.2f %s", y, ddv.min(), uwmax, ry,
                 qr.min(), "PASS" if good else "**FAIL**")
    years = (s.index[-1] - s.index[0]).days / 365.25
    log.info("PASS R1-R3: %s | equity=%.0f CAGR=%.2f%% (KHONG phai tieu chi)", ok, s.iloc[-1],
             ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100)


if __name__ == "__main__":
    main()
