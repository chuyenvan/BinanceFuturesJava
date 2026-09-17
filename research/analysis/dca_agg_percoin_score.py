"""DCA-AGG-PERCOIN (docs/PREREG_DCA_AGG_PERCOIN.md) — cham diem muc 4.

PRIMARY = khong rate nao XAU ngoai CI (5 rate chat luong TOAN BO leg: win/tsloss/mp_sm/mp_sl/meanP).
CI bootstrap block-72h x(1.21 * B4), B4 = sqrt(2 ln 3) = 1.4823 (k=3 variants), 2000 rep, seed 20260905.
CO CHE: max margin 1 coin <= 15% equity (cluster peak); tong margin DCA-grid <= 30% equity (sweep).
CHAN: maxDD nam <=30%, UW <=200 ngay, quy >= -15%, khong nam am; tap trung 1 coin <= 15% (abs).

Usage: python3 dca_agg_percoin_score.py PARITY LOOSE_AGG30 LOOSE_AGG30_PC15 LOOSE_PC15
"""
import sys
import re
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

B = C.B
BLOCK_H = C.BLOCK_H          # 72
NREP = C.NREP                # 2000
# [CHUAN HOA 2026-09-17] docs/AUDIT_CI_INFLATE_STANDARDIZATION.md muc 6 loi (3):
#   ban cu: CI_TOTAL = C.CI_INFLATE(1.21) * sqrt(2 ln 3)(1.4823) = 1.7936 - NHAN CHONG.
#   1.21 khong phai "he so nen": no la mot he so multiplicity lich su (ung k=2.079).
#   He so DUNG cho k=3 ung vien = sqrt(2 ln 3) = 1.482304, ap MOT lan.
K_VARIANTS = 3
CI_TOTAL = C.inflate(K_VARIANTS)
SEED = C.SEED
PERCOIN_CAP = 15.0           # % equity
AGG_CAP = 30.0               # % equity

RATES = [("win", lambda d: 100.0 * (d.profit > 0).mean(), "up"),
         ("tsloss", lambda d: 100.0 * (d.status == "STOP_LOSS_DONE").mean(), "down"),
         ("mp_sm", lambda d: d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean(), "up"),
         ("mp_sl", lambda d: d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean(), "up"),
         ("meanP", lambda d: d.profit.mean(), "up")]


def ci_diff(da, db, fn):
    if len(da) == 0 or len(db) == 0:
        return float("nan"), float("nan"), float("nan"), False
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}
    gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(SEED)
    obs = fn(da) - fn(db)
    draws = []
    for _ in range(NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        sa = pd.concat([ga[b] for b in pick if b in ga]) if any(b in ga for b in pick) else da.iloc[:0]
        sb = pd.concat([gb[b] for b in pick if b in gb]) if any(b in gb for b in pick) else db.iloc[:0]
        draws.append(fn(sa) - fn(sb))
    arr = np.asarray(draws, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return obs, float("nan"), float("nan"), False
    lo, hi = np.percentile(arr, [2.5, 97.5])
    c = (lo + hi) / 2.0
    lo, hi = c - (c - lo) * CI_TOTAL, c + (hi - c) * CI_TOTAL
    return obs, lo, hi, not (lo <= 0.0 <= hi)


def read_done(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["sym"].notna()].copy()
    d["start"] = d["start"].astype(str); d["end"] = d["end"].astype(str)
    for c in ("margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def yearly_hard(tag):
    s = C.equity(tag)
    out = {}
    for y, sy in s.groupby(s.index.year):
        dd = (sy / sy.cummax() - 1) * 100
        uw = sy < sy.cummax()
        uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
        ry = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
        out[y] = dict(dd=float(dd.min()), uw=uwmax, ret=float(ry))
    return out


def worst_quarter(tag):
    s = C.equity(tag)
    qe = s.resample("QE").last()
    q0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), qe]).iloc[:-1]
    qr = (qe.values / q0.values - 1) * 100
    return float(qr.min()) if len(qr) else float("nan")


def conc_max(tag):
    """Max % equity vao 1 coin = max over (sym, cluster) cua sum margin / equity(start day)."""
    d = read_done(tag)
    eq = C.equity(tag)
    d["day"] = d["start"].str.slice(0, 8)
    d["eq"] = d["day"].map(eq)
    cm = d.groupby(["sym", "end"]).agg(tot=("margin", "sum"), eq0=("eq", "first")).reset_index()
    cm = cm.dropna(subset=["eq0"])
    cm["tot_pct"] = cm["tot"] / cm["eq0"] * 100
    return float(cm.tot_pct.max()) if len(cm) else float("nan")


def agg_dca_sweep(tag):
    """Peak tong margin cac leg DCA_LEVEL1 DANG MO (toan so) / equity(start day), do bang sweep."""
    d = read_done(tag)
    dca = d[d["level"] == "DCA_LEVEL1"].copy()
    if len(dca) == 0:
        return 0.0, 0.0
    eq = C.equity(tag)
    def eq_at(ts):
        # equity(day) gan nhat <= ts (forward-fill theo ngay)
        day = ts.normalize()
        e = eq.asof(day) if hasattr(eq, "asof") else None
        return e
    # dat asof theo chi so ngay
    eq2 = eq.copy(); eq2 = eq2.sort_index()
    events = []
    for _, r in dca.iterrows():
        s = pd.to_datetime(r["start"], format="%Y%m%d %H:%M", errors="coerce")
        e = pd.to_datetime(r["end"], format="%Y%m%d %H:%M", errors="coerce")
        if pd.isna(s) or pd.isna(e):
            continue
        events.append((s, float(r["margin"])))
        events.append((e, -float(r["margin"])))
    if not events:
        return 0.0, 0.0
    # sort theo time; tai cung 1 phut, CLOSE (-) truoc OPEN (+) de khong dem leg sap dong
    events.sort(key=lambda x: (x[0], x[1]))
    running = 0.0
    peak_ratio = 0.0
    peak_abs = 0.0
    for t, dm in events:
        running += dm
        peak_abs = max(peak_abs, running)
        if running > 0:
            ev = eq2.asof(t)
            if ev is not None and not pd.isna(ev) and ev > 0:
                peak_ratio = max(peak_ratio, running / ev * 100)
    return peak_ratio, peak_abs


def log_summary(tag):
    """Doc [CONC-PC] SUMMARY blocked=... va [CONC-PC] MODE tu sim.out."""
    blocked = None
    mode = None
    nskip = 0
    try:
        with open(f"{B}/{tag}/logs/sim.out", errors="ignore") as fh:
            for line in fh:
                if "[CONC-PC] MODE" in line:
                    m = re.search(r"pct=([\d.]+)", line)
                    if m: mode = m.group(1)
                if "[CONC-PC] SKIP" in line:
                    nskip += 1
                if "[CONC-PC] SUMMARY" in line:
                    m = re.search(r"blocked=(\d+)", line)
                    if m: blocked = int(m.group(1))
    except FileNotFoundError:
        pass
    return dict(mode=mode, blocked=blocked, skip_logged=nskip)


def dca_leg_count(tag):
    d = read_done(tag)
    n_dca = int((d["level"] == "DCA_LEVEL1").sum())
    return n_dca, len(d)


def main():
    tags = sys.argv[1:]
    parity = tags[0]
    variants = tags[1:]

    print("=== CI multiplicity: k=%d => sqrt(2 ln k) = %.6f (%d rep seed %d) ===" % (
        K_VARIANTS, CI_TOTAL, NREP, SEED))
    print("=== [CHUAN HOA 2026-09-17] ban cu dung 1.7936 = 1.21 x 1.4823 (nhan chong) ===")
    print("CO CHE: per-coin <= %.0f%% equity | aggregate DCA-grid <= %.0f%% equity" % (
        PERCOIN_CAP, AGG_CAP))
    print("PRIMARY = khong rate nao XAU ngoai CI (XAU = ngoai CI + nguoc huong tot)\n")

    allr = {t: C.trades(t) for t in tags}
    for t in tags:
        d = allr[t]
        print("  %-24s n=%d win=%.2f tsloss=%.2f mp_sm=%.3f mp_sl=%.3f meanP=%.3f" % (
            t, len(d),
            100.0 * (d.profit > 0).mean(),
            100.0 * (d.status == "STOP_LOSS_DONE").mean(),
            d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean(),
            d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean(),
            d.profit.mean()))

    for v in variants:
        dv, dp = allr[v], allr[parity]
        print("\n--- %s vs %s (TOAN BO leg, n=%d vs %d) ---" % (v, parity, len(dv), len(dp)))
        n_bad = 0
        for name, fn, direction in RATES:
            obs, lo, hi, out = ci_diff(dv, dp, fn)
            good = (direction == "up" and obs > 0) or (direction == "down" and obs < 0)
            bad = out and not good
            n_bad += int(bad)
            flag = "XAU" if bad else ("ngoaaiCI" if out else "-")
            print("    %-8s hieu=%9.3f  CI=[%9.3f, %9.3f]  ngoaiCI=%s  dir=%s  %s" % (
                name, obs, lo, hi, "YES" if out else "-", direction, flag))
        print("  >>> PRIMARY: so rate XAU ngoai CI = %d (can =0 de PASS)" % n_bad)

    print("\n=== CHAN (hard) ===")
    for t in tags:
        hv = yearly_hard(t)
        qmin = worst_quarter(t)
        ddmax = min(r["dd"] for r in hv.values())
        uwmax = max(r["uw"] for r in hv.values())
        neg = [str(y) for y, r in hv.items() if r["ret"] < 0]
        bad = []
        if ddmax < -30: bad.append("maxDD")
        if uwmax > 200: bad.append("UW")
        if qmin < -15: bad.append("quy")
        if neg: bad.append("nam_am")
        print("  %-24s maxDD/yr=%.2f%% UW=%d qmin=%.1f%% neg_year=%s  %s" % (
            t, ddmax, uwmax, qmin, neg, "PASS" if not bad else "FAIL:" + ",".join(bad)))

    print("\n=== CO CHE: tap trung 1 coin (<= %.0f%% equity, TUYET DOI) ===" % PERCOIN_CAP)
    for t in tags:
        c = conc_max(t)
        print("  %-24s max1coin=%.2f%%  %s" % (t, c, "OK" if c <= PERCOIN_CAP + 0.5 else "VUOT"))

    print("\n=== CO CHE: tong margin DCA-grid DANG MO (<= %.0f%% equity) ===" % AGG_CAP)
    for t in tags:
        pr, pa = agg_dca_sweep(t)
        print("  %-24s peak_agg=%.2f%% (abs %.0f)  %s" % (t, pr, pa, "OK" if pr <= AGG_CAP + 0.5 else "VUOT"))

    print("\n=== CO CHE: guard binding (log [CONC-PC]) + leg counts ===")
    for t in tags:
        ls = log_summary(t)
        ndca, ntot = dca_leg_count(t)
        print("  %-24s DCAlegs=%d/%d  pc_mode=%s pc_blocked=%s pc_skip_logged=%s" % (
            t, ndca, ntot, ls["mode"], ls["blocked"], ls["skip_logged"]))

    print("\n=== EQUITY cuoi / CAGR (THAM CHIEU, KHONG phai tieu chi) ===")
    for t in tags:
        s = C.equity(t)
        years = (s.index[-1] - s.index[0]).days / 365.25
        cagr = ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100
        print("  %-24s equity=%.0f CAGR=%.2f%%" % (t, s.iloc[-1], cagr))


if __name__ == "__main__":
    main()
