"""Buoc 0 (V4) — xac dinh KHUNG NGAY cua doan underwater dai nhat cho tung config.

Cau hoi: 4 config co co che KHAC HAN nhau (#52 chia margin deu; GS100/120/140 noi gate + DCA)
deu ra UW 221-223 ngay o 2025 — co phai CUNG MOT khung ngay (su kien he thong) hay chi la
trung so ngau nhien cua tung co che?

Dung lai c3_rates.equity(tag) (equity ngay = b + unP tu sim.out) — khong chay lai sim.
Usage: python3 uw_window.py TAG [TAG ...]
"""
import sys
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C


def longest_uw(s):
    """Tra ve (n_ngay, ngay_dinh_truoc_DD, ngay_bat_dau_uw, ngay_hoi_ve_dinh)."""
    cm = s.cummax()
    uw = s < cm
    best = (0, None, None, None)
    grp = (~uw).cumsum()
    for _, seg in s[uw].groupby(grp[uw]):
        n = len(seg)
        if n > best[0]:
            start = seg.index[0]
            prev = s.index[s.index < start]
            peak = prev[-1] if len(prev) else start
            after = s.index[s.index > seg.index[-1]]
            rec = after[0] if len(after) else None
            best = (n, peak, start, rec)
    return best


print("%-14s %6s %12s %12s %12s %10s" % ("tag", "UW", "peak(truoc)", "uw_start", "hoi_ve_dinh", "equity_dinh"))
for t in sys.argv[1:]:
    try:
        s = C.equity(t)
    except Exception as e:
        print("%-14s LOI %s" % (t, e))
        continue
    n, peak, st, rec = longest_uw(s)
    ep = float(s.loc[peak]) if peak is not None else float("nan")
    print("%-14s %6d %12s %12s %12s %10.0f" % (
        t, n,
        peak.date() if peak is not None else "-",
        st.date() if st is not None else "-",
        rec.date() if rec is not None else "CHUA HOI",
        ep))
