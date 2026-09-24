"""BD-THRESHOLD-FRAGILITY (docs/prereg/PREREG_BD_THRESHOLD_FRAGILITY.md) — bang duong cong do nhay.

DESCRIPTIVE ONLY: khong chon nguong, khong de xuat nguong, khong xep hang winner.
Moi diem: n leg, n leg BIG_DOWN, PnL BIG_DOWN (USD), 5 rate chat luong TOAN BO leg + CI
bootstrap (block-72h x1.21, 2000 rep, seed 20260905), rang buoc cung (maxDD/yr<=30%, UW<=200,
quy>=-15%, khong nam am, tap trung 1 coin<=15%).

Usage: python3 bd_threshold_fragility_score.py <TAG_BASELINE> <TAG1> <TAG2> <TAG3> <TAG4>
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

B = C.B
BLOCK_H = C.BLOCK_H        # 72
NREP = C.NREP              # 2000
CI_INFLATE = C.CI_INFLATE  # 1.21
SEED = C.SEED              # 20260905
PERCOIN_CAP = 15.0

RATES = [("win", lambda d: 100.0 * (d.profit > 0).mean()),
         ("tsloss", lambda d: 100.0 * (d.status == "STOP_LOSS_DONE").mean()),
         ("mp_sm", lambda d: d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean()),
         ("mp_sl", lambda d: d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean()),
         ("meanP", lambda d: d.profit.mean())]


def ci_single(d, fn):
    """Block-72h bootstrap CI cua MOT rate (khong phai diff). Tra (obs, lo, hi)."""
    if len(d) == 0:
        return float("nan"), float("nan"), float("nan")
    blocks = d.blk.unique()
    g = {k: v for k, v in d.groupby("blk")}
    rng = np.random.default_rng(SEED)
    obs = fn(d)
    draws = []
    for _ in range(NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        s = pd.concat([g[b] for b in pick if b in g]) if any(b in g for b in pick) else d.iloc[:0]
        draws.append(fn(s))
    arr = np.asarray(draws, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return obs, float("nan"), float("nan")
    lo, hi = np.percentile(arr, [2.5, 97.5])
    c = (lo + hi) / 2.0
    lo, hi = c - (c - lo) * CI_INFLATE, c + (hi - c) * CI_INFLATE
    return obs, lo, hi


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
    d = read_done(tag)
    eq = C.equity(tag)
    d["day"] = d["start"].str.slice(0, 8)
    d["eq"] = d["day"].map(eq)
    cm = d.groupby(["sym", "end"]).agg(tot=("margin", "sum"), eq0=("eq", "first")).reset_index()
    cm = cm.dropna(subset=["eq0"])
    cm["tot_pct"] = cm["tot"] / cm["eq0"] * 100
    return float(cm.tot_pct.max()) if len(cm) else float("nan")


def read_done(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["sym"].notna()].copy()
    d["start"] = d["start"].astype(str)
    d["end"] = d["end"].astype(str)
    for c in ("margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d


def main():
    tags = sys.argv[1:]
    if len(tags) < 5:
        print("can: <baseline> <t1> <t2> <t3> <t4>")
        sys.exit(2)

    allt = {t: C.trades(t) for t in tags}
    alld = {t: read_done(t) for t in tags}

    print("=== BD THRESHOLD FRAGILITY — duong cong do nhay (DESCRIPTIVE, KHONG chon) ===")
    print("CI block-%dh x%.2f, %d rep, seed %d. KHONG co cot 'winner'.\n" % (
        BLOCK_H, CI_INFLATE, NREP, SEED))

    print("--- (1) so leg + PnL BIG_DOWN (USD) ---")
    print("%-14s %8s %10s %12s" % ("tag", "n_leg", "n_BIGDOWN", "PnL_BD_USD"))
    for t in tags:
        d = alld[t]
        nbd = int((d["level"] == "BIG_DOWN").sum())
        pnlbd = float(d.loc[d["level"] == "BIG_DOWN", "pnl"].sum())
        print("%-14s %8d %10d %12.1f" % (t, len(d), nbd, pnlbd))

    print("\n--- (2) 5 rate chat luong TOAN BO leg (profit/leg) + CI bootstrap ---")
    hdr = "%-14s" % "tag"
    for name, _ in RATES:
        hdr += " %20s" % name
    print(hdr)
    for t in tags:
        d = allt[t]
        row = "%-14s" % t
        for name, fn in RATES:
            obs, lo, hi = ci_single(d, fn)
            row += " %9.3f[%7.3f,%7.3f]" % (obs, lo, hi)
        print(row)

    print("\n--- (3) rang buoc cung (bar) ---")
    print("%-14s %12s %6s %8s %10s %12s %8s" % (
        "tag", "maxDD/yr%", "UW", "qmin%", "neg_year", "conc1coin%", "verdict"))
    for t in tags:
        hv = yearly_hard(t)
        qmin = worst_quarter(t)
        ddmax = min(r["dd"] for r in hv.values())
        uwmax = max(r["uw"] for r in hv.values())
        neg = [str(y) for y, r in hv.items() if r["ret"] < 0]
        c = conc_max(t)
        bad = []
        if ddmax < -30: bad.append("maxDD")
        if uwmax > 200: bad.append("UW")
        if qmin < -15: bad.append("quy")
        if neg: bad.append("nam_am")
        if c > PERCOIN_CAP + 0.5: bad.append("conc")
        print("%-14s %12.2f %6d %8.1f %10s %12.2f %8s" % (
            t, ddmax, uwmax, qmin, ",".join(neg) if neg else "-", c,
            "PASS" if not bad else "FAIL:" + ",".join(bad)))


if __name__ == "__main__":
    main()
