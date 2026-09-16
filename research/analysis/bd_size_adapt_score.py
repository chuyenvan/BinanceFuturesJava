"""BD-SIZE-ADAPT (docs/PREREG_BD_SIZE_ADAPT.md) — cham diem §2.

Chay SAU khi da co parity + 3 bien the. So sanh TUNG bien the vs parity tren tap leg
level == BIG_DOWN: pnl/leg, meanP, TSloss%, win% + block-72h bootstrap CI (x1.21, 2000
rep, seed co dinh). Dem n leg BIG_DOWN (ky vong = parity). Concentration (max % equity
1 coin, theo conc_grid.py). Hard-constraint tu equity THAT sim.out (maxDD nam / nam am / UW).

Usage:
  python3 bd_size_adapt_score.py PARITY DOWN50 DOWN25 UP50
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

B = C.B
BLOCK_H = C.BLOCK_H          # 72
NREP = C.NREP                # 2000
CI_INFLATE = C.CI_INFLATE    # 1.21
SEED = C.SEED                # 20260905

# Tolerance hard-constraint (docs/PREREG_BD_SIZE_ADAPT.md muc 2)
DD_TOL = 3.0      # maxDD nam khong xau hon parity qua +3pp
UW_TOL = 30       # UW khong xau hon parity qua +30 ngay


def bd_trades(tag):
    d = C.trades(tag)
    return d[d.level == "BIG_DOWN"].reset_index(drop=True)


def rate_pnl_leg(d):
    return float(d.pnl.sum() / len(d)) if len(d) else float("nan")


def rate_meanP(d):
    return float(d.profit.mean()) if len(d) else float("nan")


def rate_tsloss(d):
    return 100.0 * float((d.status == "STOP_LOSS_DONE").mean()) if len(d) else float("nan")


def rate_win(d):
    return 100.0 * float((d.profit > 0).mean()) if len(d) else float("nan")


RATES = [("pnl_leg", rate_pnl_leg, "up"),
         ("meanP", rate_meanP, "up"),
         ("tsloss", rate_tsloss, "down"),
         ("win", rate_win, "up")]


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
    lo, hi = c - (c - lo) * CI_INFLATE, c + (hi - c) * CI_INFLATE
    return obs, lo, hi, not (lo <= 0.0 <= hi)


def equity_series(tag):
    return C.equity(tag)


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


def conc_max(tag):
    """max % equity 1 coin (tong margin cum / equity ngay mo), theo conc_grid.py."""
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["sym"].notna()].copy()
    d["start"] = d["start"].astype(str); d["end"] = d["end"].astype(str)
    for c in ("margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    eq = equity_series(tag)
    d["day"] = d["start"].str.slice(0, 8)
    d["eq"] = d["day"].map(eq)
    cm = d.groupby(["sym", "end"]).agg(tot=("margin", "sum"), eq0=("eq", "first")).reset_index()
    cm = cm.dropna(subset=["eq0"])
    cm["tot_pct"] = cm["tot"] / cm["eq0"] * 100
    return float(cm.tot_pct.max()) if len(cm) else float("nan")


def main():
    tags = sys.argv[1:]
    parity = tags[0]
    variants = tags[1:]

    bd = {t: bd_trades(t) for t in tags}
    print("=== n leg BIG_DOWN (ky vong BANG parity = %d) ===" % len(bd[parity]))
    for t in tags:
        print("  %-28s n=%d" % (t, len(bd[t])))

    print("\n=== RATE leg BIG_DOWN (variant vs parity) ===")
    hdr = "%-28s %8s %8s %8s %8s" % ("tag", "pnl_leg", "meanP", "tsloss", "win")
    print(hdr)
    for t in tags:
        d = bd[t]
        print("%-28s %8.2f %8.3f %8.2f %8.2f" % (
            t, rate_pnl_leg(d), rate_meanP(d), rate_tsloss(d), rate_win(d)))

    print("\n=== bootstrap CI khoi %dh x%.2f (%d rep, seed %d): variant - parity ===" % (
        BLOCK_H, CI_INFLATE, NREP, SEED))
    print("  (dir: up = cao hon la TOT cho pnl_leg/meanP/win; down = thap hon la TOT cho tsloss)")
    for v in variants:
        dv, dp = bd[v], bd[parity]
        print("\n--- %s - %s (n=%d vs n=%d) ---" % (v, parity, len(dv), len(dp)))
        for name, fn, direction in RATES:
            obs, lo, hi, out = ci_diff(dv, dp, fn)
            print("  %-8s hieu=%9.3f  CI=[%9.3f, %9.3f]  ngoaiCI=%s  dir=%s" % (
                name, obs, lo, hi, "YES" if out else "-", direction))

    print("\n=== CONCENTRATION: max %% equity 1 coin (KHONG tang so parity) ===")
    for t in tags:
        print("  %-28s max1coin=%.2f%%" % (t, conc_max(t)))

    print("\n=== HARD-CONSTRAINT tu equity THAT (sim.out) theo nam ===")
    print("  (maxDD nam khong xau hon parity qua %.1fpp; nam khong am; UW khong xau hon parity qua %d ngay)" % (
        DD_TOL, UW_TOL))
    hp = yearly_hard(parity)
    for t in tags:
        hv = yearly_hard(t)
        print("\n  %s:" % t)
        for y in sorted(hv):
            rv, rp = hv[y], hp.get(y)
            dd = "  n/a" if rp is None else "  dd_parity=%.2f" % rp["dd"]
            uw = "" if rp is None else "  uw_parity=%d" % rp["uw"]
            print("    %d: maxDD=%7.2f%% UW=%3d ret=%+7.2f%%%s%s" % (
                y, rv["dd"], rv["uw"], rv["ret"], dd, uw))


if __name__ == "__main__":
    main()
