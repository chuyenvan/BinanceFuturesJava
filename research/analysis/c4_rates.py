"""C4 — cham diem cac arm "thang GIA TRI" so voi PARITY (docs/PREREG_C4.md muc 3-4).

Dung lai may bootstrap khoi-72h x1.21 cua research/analysis/c3_rates.py (khong viet lai).
Them: do ADMISSION (trung khoa (sym,start) voi parity, phan phoi symbolPred), bang rate
theo NAM + CI theo nam, rang buoc cung theo nam.

Usage: python3 c4_rates.py C4_parity C4_regen [C4_maxfav]
"""
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

KEYS = C.KEYS
QUAL = ("win", "tsloss", "mp_sm", "mp_sl", "margin")   # 5 rate CHAT LUONG cua pre-reg
LBL = {"n": "n", "win": "win%", "tsloss": "TSloss%", "mp_sm": "mP|SM",
       "mp_sl": "mP|SL", "meanP": "meanP", "margin": "mMargin"}
HARD_DD, HARD_Q = 15.0, -5.0


def ci_pair_df(da, db):
    """Paired block-72h bootstrap CI cua hieu (A - B) tren hai bang trade DA LOC."""
    if len(da) == 0 or len(db) == 0:
        return {k: (float("nan"),) * 3 + (False,) for k in KEYS}
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}
    gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(C.SEED)
    obs = {k: C.rates(da)[k] - C.rates(db)[k] for k in KEYS}
    draws = {k: [] for k in KEYS}
    for _ in range(C.NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        la = [ga[b] for b in pick if b in ga]
        lb = [gb[b] for b in pick if b in gb]
        ra = C.rates(pd.concat(la) if la else da.iloc[:0])
        rb = C.rates(pd.concat(lb) if lb else db.iloc[:0])
        for k in KEYS:
            draws[k].append(ra[k] - rb[k])
    out = {}
    for k in KEYS:
        arr = np.asarray(draws[k], dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            out[k] = (obs[k], float("nan"), float("nan"), False)
            continue
        lo, hi = np.percentile(arr, [2.5, 97.5])
        c = (lo + hi) / 2.0
        lo, hi = c - (c - lo) * C.CI_INFLATE, c + (hi - c) * C.CI_INFLATE
        out[k] = (obs[k], lo, hi, not (lo <= 0.0 <= hi))
    return out


def rate_table(tags, dd, title, sub=None):
    log.info("")
    log.info("### %s", title)
    log.info("| arm | n | win%% | TSloss%% | mP\\|SM | mP\\|SL | meanP | mMargin |")
    log.info("|---|---:|---:|---:|---:|---:|---:|---:|")
    for t in tags:
        d = dd[t] if sub is None else sub(dd[t])
        r = C.rates(d)
        log.info("| %s | %d | %.2f | %.2f | %.3f | %.3f | %.3f | %.0f |", t, int(r["n"]),
                 r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"], r["meanP"], r["margin"])


def ci_table(arms, parity, dd, title, sub=None):
    log.info("")
    log.info("### %s  (hieu ARM - %s, CI khoi-72h x%.2f)", title, parity, C.CI_INFLATE)
    log.info("| arm | do | hieu | CI lo | CI hi | NGOAI CI |")
    log.info("|---|---|---:|---:|---:|:---:|")
    for t in arms:
        da = dd[t] if sub is None else sub(dd[t])
        db = dd[parity] if sub is None else sub(dd[parity])
        r = ci_pair_df(da, db)
        nq = 0
        for k in KEYS:
            o, lo, hi, out = r[k]
            log.info("| %s | %s | %+.4f | %+.4f | %+.4f | %s |", t, LBL[k], o, lo, hi,
                     "**CO**" if out else "-")
            if out and k in QUAL:
                nq += 1
        log.info("| %s | **so rate CHAT LUONG ngoai CI** | **%d/5** | | | |", t, nq)


def admission(arms, parity, dd):
    log.info("")
    log.info("### ADMISSION (bao rieng - co hoc, KHONG dem vao quy tac quyet dinh)")
    log.info("| arm | n | trung khoa (sym,start) voi parity | %% cua arm | %% cua parity | "
             "symbolPred p10/p50/p90 | %%STRONG (<=0.29) |")
    log.info("|---|---:|---:|---:|---:|---|---:|")
    kp = set(zip(dd[parity].sym, dd[parity].start))
    for t in [parity] + list(arms):
        d = dd[t]
        ka = set(zip(d.sym, d.start))
        inter = len(ka & kp)
        sp = d.symbolPred.dropna()
        q = np.percentile(sp, [10, 50, 90]) if len(sp) else [float("nan")] * 3
        lead = d[d.leg == 0]
        st = 100.0 * (lead.symbolPred.fillna(1.0) <= C.WEAK_THR).mean()
        log.info("| %s | %d | %d | %.2f | %.2f | %.4f / %.4f / %.4f | %.1f |", t, len(d),
                 inter, 100.0 * inter / max(len(ka), 1), 100.0 * inter / max(len(kp), 1),
                 q[0], q[1], q[2], st)


def hard(tags):
    log.info("")
    log.info("### RANG BUOC CUNG theo nam (maxDD <= 15%%/nam, khong nam am, khong quy < -5%%)")
    log.info("| arm | nam | maxDD%% | UW (ngay) | ret_nam%% | quy_min%% | PASS |")
    log.info("|---|---|---:|---:|---:|---:|:---:|")
    for t in tags:
        s = C.equity(t)
        for y, sy in s.groupby(s.index.year):
            dd = (sy / sy.cummax() - 1) * 100
            uw = int((sy < sy.cummax()).sum())
            ret = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
            qe = sy.resample("QE").last()
            q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
            qr = (qe.values / q0.values - 1) * 100
            ok = (dd.min() >= -HARD_DD) and (ret > 0) and (qr.min() >= HARD_Q)
            log.info("| %s | %d | %.2f | %d | %+.2f | %+.2f | %s |", t, y, dd.min(), uw,
                     ret, qr.min(), "PASS" if ok else "**FAIL**")


def equity_table(tags):
    log.info("")
    log.info("### EQUITY / CAGR - **KHONG phai tieu chi** (AGENT_RUNBOOK muc 0.3)")
    log.info("| arm | equity cuoi | CAGR%% | maxDD%% (48t) | UW (48t) |")
    log.info("|---|---:|---:|---:|---:|")
    for t in tags:
        s = C.equity(t)
        yrs = (s.index[-1] - s.index[0]).days / 365.25
        log.info("| %s | %d | %.2f | %.2f | %d |", t, int(s.iloc[-1]),
                 ((s.iloc[-1] / s.iloc[0]) ** (1 / yrs) - 1) * 100,
                 float((s / s.cummax() - 1).min() * 100), int((s < s.cummax()).sum()))


def main(argv):
    """--cut YYYYMMDD: chi giu lenh co `end` < moc do (phep cat cua X1_EXTEND muc 3;
    da xac nhan 'chay 48 thang roi cat' == 'chay 30 thang')."""
    cut = None
    if "--cut" in argv:
        i = argv.index("--cut")
        cut = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    parity, arms = argv[0], argv[1:]
    tags = [parity] + arms
    dd = {t: C.trades(t) for t in tags}
    if cut:
        lim = pd.Timestamp(cut)
        for t in tags:
            e = pd.to_datetime(dd[t]["end"], format="%Y%m%d %H:%M", errors="coerce")
            dd[t] = dd[t][e < lim]
            log.info("CAT end < %s: %s -> %d lenh", cut, t, len(dd[t]))
    for t in tags:
        log.info("%s: %d lenh, %s .. %s", t, len(dd[t]), dd[t].ts.min(), dd[t].ts.max())
    rate_table(tags, dd, "BANG CHINH - 48 thang")
    ci_table(arms, parity, dd, "CI - 48 thang")
    for y in (2022, 2023, 2024, 2025) if not cut else (2022, 2023, 2024):
        rate_table(tags, dd, "Nam %d" % y, sub=lambda d, y=y: d[d.ts.dt.year == y])
        ci_table(arms, parity, dd, "CI nam %d" % y, sub=lambda d, y=y: d[d.ts.dt.year == y])
    admission(arms, parity, dd)
    if not cut:
        hard(tags)
        equity_table(tags)
    else:
        log.info("")
        log.info("(bo bang rang buoc cung / equity: chuoi equity cua arm cat khong so duoc"
                 " truc tiep voi arm chay du 48 thang)")
        hard(arms)
        equity_table(arms)


if __name__ == "__main__":
    main(sys.argv[1:])
