"""BD-SEL (docs/prereg/PREREG_SEL_BIGDOWN.md) — cham diem muc 2.

So sanh TUNG bien the (drop/mix/drop_top8) vs parity tren tap leg level == BIG_DOWN.
PRIMARY (3 rate): pnl/leg, meanP, TSloss%. Thang khi >=2/3 rate NGOAI CI (khoi 72h x1.21,
2000 rep, seed co dinh 20260905) CUNG HUONG TOT. CHAN: n leg BIG_DOWN == 248; tap trung
max % equity 1 coin KHONG tang; hard-constraint equity THAT sim.out (maxDD nam <= parity+3pp,
khong nam am, UW <= parity+30 ngay); rate TOAN BO leg khong XAU ngoai CI.

Usage:
  python3 bd_sel_score.py PARITY DROP MIX DROP_TOP8
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


# PRIMARY (3 rate, muc 2): pnl_leg(up), meanP(up), tsloss(down)
PRIMARY = [("pnl_leg", rate_pnl_leg, "up"),
           ("meanP", rate_meanP, "up"),
           ("tsloss", rate_tsloss, "down")]
INFO = PRIMARY + [("win", rate_win, "up")]


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


def all_leg_rates(tag):
    return C.trades(tag)


def _rate_all_win(d):
    return 100.0 * (d.profit > 0).mean() if len(d) else float("nan")


def _rate_all_tsloss(d):
    return 100.0 * (d.status == "STOP_LOSS_DONE").mean() if len(d) else float("nan")


def _rate_all_meanP(d):
    return d.profit.mean() if len(d) else float("nan")


ALL_RATES = [("win", _rate_all_win, "up"),
             ("tsloss", _rate_all_tsloss, "down"),
             ("meanP", _rate_all_meanP, "up")]


def main():
    tags = sys.argv[1:]
    parity = tags[0]
    variants = tags[1:]

    bd = {t: bd_trades(t) for t in tags}
    print("=== n leg BIG_DOWN (ky vong BANG parity = %d) ===" % len(bd[parity]))
    for t in tags:
        print("  %-30s n=%d" % (t, len(bd[t])))

    print("\n=== PRIMARY (3 rate) leg BIG_DOWN — variant vs parity ===")
    hdr = "%-30s %10s %10s %10s %10s" % ("tag", "pnl_leg", "meanP", "tsloss", "win")
    print(hdr)
    for t in tags:
        d = bd[t]
        print("%-30s %10.2f %10.3f %10.2f %10.2f" % (
            t, rate_pnl_leg(d), rate_meanP(d), rate_tsloss(d), rate_win(d)))

    print("\n=== bootstrap CI khoi %dh x%.2f (%d rep, seed %d): variant - parity ===" % (
        BLOCK_H, CI_INFLATE, NREP, SEED))
    print("  (PRIMARY dir: pnl_leg/meanP UP=good, tsloss DOWN=good)")
    for v in variants:
        dv, dp = bd[v], bd[parity]
        print("\n--- %s - %s (n=%d vs n=%d) ---" % (v, parity, len(dv), len(dp)))
        n_primary_out = 0
        for name, fn, direction in PRIMARY:
            obs, lo, hi, out = ci_diff(dv, dp, fn)
            good = out and ((direction == "up" and obs > 0) or (direction == "down" and obs < 0))
            n_primary_out += int(good)
            print("  %-8s hieu=%9.3f  CI=[%9.3f, %9.3f]  ngoaiCI=%s  dir=%s  GOOD=%s" % (
                name, obs, lo, hi, "YES" if out else "-", direction, "YES" if good else "-"))
        print("  >>> PRIMARY rate NGOAI CI CUNG HUONG TOT = %d/3 (can >=2 de THANG)" % n_primary_out)
        for name, fn, direction in [("win", rate_win, "up")]:
            obs, lo, hi, out = ci_diff(dv, dp, fn)
            print("  %-8s hieu=%9.3f  CI=[%9.3f, %9.3f]  ngoaiCI=%s  dir=%s" % (
                name, obs, lo, hi, "YES" if out else "-", direction))

    print("\n=== CONCENTRATION: max %% equity 1 coin (KHONG tang so parity) ===")
    for t in tags:
        print("  %-30s max1coin=%.2f%%" % (t, conc_max(t)))

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

    print("\n=== CHAN #4: rate TOAN BO leg (khong rate XAU ngoai CI) ===")
    allr = {t: all_leg_rates(t) for t in tags}
    for t in tags:
        d = allr[t]
        print("  %-30s n=%d win=%.2f tsloss=%.2f meanP=%.3f" % (
            t, len(d), _rate_all_win(d), _rate_all_tsloss(d), _rate_all_meanP(d)))
    print("  (CI variant - parity, khoi %dh x%.2f, %d rep, seed %d; XAU = ngoai CI nguoc huong tot)" % (
        BLOCK_H, CI_INFLATE, NREP, SEED))
    for v in variants:
        dv, dp = allr[v], allr[parity]
        print("\n  --- %s - %s (toan bo leg) ---" % (v, parity))
        for name, fn, direction in ALL_RATES:
            obs, lo, hi, out = ci_diff(dv, dp, fn)
            good = (direction == "up" and obs > 0) or (direction == "down" and obs < 0)
            bad = out and not good
            print("    %-8s hieu=%9.3f  CI=[%9.3f, %9.3f]  ngoaiCI=%s  dir=%s  XAU=%s" % (
                name, obs, lo, hi, "YES" if out else "-", direction, "YES" if bad else "-"))


if __name__ == "__main__":
    main()
