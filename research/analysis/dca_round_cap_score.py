"""DCA-ROUND-CAP (docs/PREREG_DCA_ROUND_CAP.md) — cham diem muc 4.

PRIMARY = khong rate nao XAU ngoai CI (5 rate chat luong TOAN BO leg: win/tsloss/mp_sm/mp_sl/meanP).
CI bootstrap block-72h x(1.21 * B4) , B4 = sqrt(2 ln 3) = 1.4823 (k=3 variants), 2000 rep, seed 20260905.
CHAN: maxDD nam <=30%, UW <=200 ngay, quy >= -15%, khong nam am; tap trung 1 coin khong tang.
CO CHE: tong margin moi moi luot DCA <= 10% equity (tu printDone.csv + log SUMMARY).

Usage: python3 dca_round_cap_score.py PARITY CAP10 CAP10_LOOSE LOOSE
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

B = C.B
BLOCK_H = C.BLOCK_H          # 72
NREP = C.NREP                # 2000
CI_BASE = C.CI_INFLATE       # 1.21
B4 = float(np.sqrt(2 * np.log(3)))   # 1.4823 (k=3 variants, multiplicity)
CI_TOTAL = CI_BASE * B4
SEED = C.SEED

# 5 rate chat luong (TOAN BO leg). direction: "up" = lon hon la tot, "down" = nho hon la tot.
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
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["sym"].notna()].copy()
    d["start"] = d["start"].astype(str); d["end"] = d["end"].astype(str)
    for c in ("margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    eq = C.equity(tag)
    d["day"] = d["start"].str.slice(0, 8)
    d["eq"] = d["day"].map(eq)
    cm = d.groupby(["sym", "end"]).agg(tot=("margin", "sum"), eq0=("eq", "first")).reset_index()
    cm = cm.dropna(subset=["eq0"])
    cm["tot_pct"] = cm["tot"] / cm["eq0"] * 100
    return float(cm.tot_pct.max()) if len(cm) else float("nan")


def dca_round_margin_check(tag):
    """Nhom leg DCA_LEVEL1 theo cot start (phut) = 1 luot; tong margin moi moi luot vs equity (ngay)."""
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["sym"].notna()].copy()
    d["start"] = d["start"].astype(str)
    d["margin"] = pd.to_numeric(d["margin"], errors="coerce")
    dca = d[d["level"] == "DCA_LEVEL1"].copy()
    eq = C.equity(tag)
    dca["day"] = dca["start"].str.slice(0, 8)
    dca["eq"] = dca["day"].map(eq)
    if len(dca) == 0:
        return dict(n_rounds=0, max_sum=0.0, max_pct=0.0)
    g = dca.groupby("start").agg(n=("margin", "size"), sum_margin=("margin", "sum"),
                                 eq0=("eq", "first")).reset_index()
    g = g.dropna(subset=["eq0"])
    g["pct"] = g["sum_margin"] / g["eq0"] * 100
    return dict(n_rounds=len(g), max_sum=float(g.sum_margin.max()),
                max_pct=float(g.pct.max()), max_round=g.sort_values("pct").iloc[-1]["start"])


def dca_leg_count(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["sym"].notna()].copy()
    n_dca = int((d["level"] == "DCA_LEVEL1").sum())
    return n_dca, len(d)


def main():
    tags = sys.argv[1:]
    parity = tags[0]
    variants = tags[1:]

    print("=== CI B4 multiplicity: base=%.3f B4=%.4f total=%.4f (%d rep seed %d) ===" % (
        CI_BASE, B4, CI_TOTAL, NREP, SEED))
    print("PRIMARY = khong rate nao XAU ngoai CI (XAU = ngoai CI + nguoc huong tot)\n")

    allr = {t: C.trades(t) for t in tags}
    for t in tags:
        d = allr[t]
        print("  %-30s n=%d win=%.2f tsloss=%.2f mp_sm=%.3f mp_sl=%.3f meanP=%.3f" % (
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
    hp = yearly_hard(parity)
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
        print("  %-28s maxDD/yr=%.2f%% UW=%d qmin=%.1f%% neg_year=%s  %s" % (
            t, ddmax, uwmax, qmin, neg, "PASS" if not bad else "FAIL:" + ",".join(bad)))

    print("\n=== CONCENTRATION: max %% equity 1 coin (KHONG tang so parity) ===")
    cp = conc_max(parity)
    for t in tags:
        c = conc_max(t)
        print("  %-28s max1coin=%.2f%%  %s" % (t, c, "OK" if c <= cp + 1e-9 else "TANG"))

    print("\n=== CO CHE: tong margin moi moi luot DCA (<= 10%% equity) ===")
    for t in tags:
        r = dca_round_margin_check(t)
        ndca, ntot = dca_leg_count(t)
        print("  %-28s DCAlegs=%d/%d rounds=%d max_round_margin=%.0f max_pct=%.2f%%  %s" % (
            t, ndca, ntot, r["n_rounds"], r["max_sum"], r["max_pct"],
            "OK" if r["max_pct"] <= 10.0 + 0.5 else "VUOT"))


if __name__ == "__main__":
    main()
