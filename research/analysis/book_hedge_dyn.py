#!/usr/bin/env python3
"""BOOK_HEDGE_DYN - hedge basket chon DONG hang thang (point-in-time).

Moi thang: xep hang coin trong universe[thang] theo corr return ngay voi return NGAY CUA BOOK
(trung binh 8 seed) tren 90 ngay TRUOC ngay 1; chon top-5, weight 1/5; giu trong thang.
Khong dung thong tin tuong lai. Luat GO y nguyen BOOK_HEDGE.
"""
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import iso_risk_driver as I  # noqa: E402
import reset_rule_score as R  # noqa: E402

assert R._work is MT._work_vision
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("bhd")

D = "/home/ubuntu/claude_master/bookhedge_dyn"
S = I.SEEDS
HS = [0.5, 1.0]
FEE = 0.0005
T995 = 3.499483
K = 5
WIN = 90
DAY0 = pd.Timestamp(R.DAY0)
W22 = int((pd.Timestamp("2022-01-01") - DAY0) // pd.Timedelta(minutes=1))
REG = []


class Cap(MT.MTMStateD):
    def __init__(self):
        super().__init__()
        self.rec = []
        REG.append(self)

    def feed(self, m_global, eq):
        super().feed(m_global, eq)
        self.rec.append((int(m_global), np.asarray(eq["legacy"], np.float64).copy()))


R.MTMState = Cap
legs = {s: R.load_legs(I.OFF[s]) for s in S}
mtm = R.run_mtm(legs, workers=3, chunk=30)
assert len(REG) == len(S)

z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
bt_g = (z["bt_ts"].astype(np.int64) - int(DAY0.value // 10 ** 6)) // 60000


def stats(M, E):
    pk = np.maximum.accumulate(E)
    dd_all = float((E / pk - 1).min() * 100)
    w = M >= W22
    Ew, Mw = E[w], M[w]
    pkw = np.maximum.accumulate(Ew)
    ddw = Ew / pkw - 1
    dd22_reset = float(ddw.min() * 100)
    dd22_carry = float((E[w] / pk[w] - 1).min() * 100)
    under = ddw < -1e-9
    dif = np.diff(np.concatenate([[0], under.astype(np.int8), [0]]))
    st_, en_ = np.where(dif == 1)[0], np.where(dif == -1)[0]
    uw = float((en_ - st_).max() / 1440.0) if len(st_) else 0.0
    e0 = E[M < W22][-1] if (M < W22).any() else Ew[0]
    yrs = (Mw[-1] - W22) / (1440 * 365.25)
    cagr = ((Ew[-1] / e0) ** (1 / yrs) - 1) * 100
    return dict(dd22=dd22_reset, dd22_carry=dd22_carry, dd_all=dd_all, cagr22=float(cagr), uw22=float(uw),
                calmar22=float(cagr / abs(dd22_reset)), pnl=float(E[-1] - R.CAP0))


def win_dd(M, E, a, b):
    t0 = int((pd.Timestamp(a) - DAY0) // pd.Timedelta(minutes=1))
    t1 = int((pd.Timestamp(b) - DAY0) // pd.Timedelta(minutes=1))
    w = (M >= t0) & (M < t1)
    x = E[w]
    return float((x / np.maximum.accumulate(x) - 1).min() * 100)


# ---------- 1) return ngay cua book (trung binh 8 seed) ----------
per = []
for s, st in zip(S, REG):
    st.rec.sort()
    M = np.concatenate([m + np.arange(len(e)) for m, e in st.rec])
    E = np.concatenate([e for _, e in st.rec])
    eod = pd.Series(E).groupby(M // 1440).last()
    per.append(eod.pct_change())
alld = sorted(set().union(*[set(x.index) for x in per]))
book_ret = pd.DataFrame({i: x for i, x in enumerate(per)}).reindex(alld).mean(axis=1)
# index cua book_ret la NGAY-SINCE-DAY0; doi sang NGAY-SINCE-EPOCH de khop rcoin.index
book_ret.index = book_ret.index + int(DAY0.value // 10 ** 6 // 86400000)
log.info("book_ret index %s..%s (epoch day)", int(book_ret.index.min()), int(book_ret.index.max()))
log.info("book daily returns: %d ngay", len(book_ret))

# ---------- 2) chon dong theo thang ----------
day = pd.read_parquet(f"{D}/daily.parquet")
close = day.pivot_table(index="day", columns="sym", values="close", aggfunc="last")
rcoin = np.log(close).diff()
uni = json.load(open(f"{D}/universe.json"))
sel, hist = {}, {}
for ym in sorted(uni):
    y, m = int(ym[:4]), int(ym[5:])
    start = int(pd.Timestamp(year=y, month=m, day=1).value // 10 ** 6 // 86400000)
    idx = [d for d in rcoin.index if start - WIN <= d < start]
    bk = book_ret.reindex(idx)
    sc = []
    for c in uni[ym]:
        if c not in rcoin.columns:
            continue
        x = rcoin.loc[idx, c]
        ok = x.notna() & bk.notna()
        if int(ok.sum()) < 60:
            continue
        xs, bs = x[ok].to_numpy(), bk[ok].to_numpy()
        if xs.std() == 0 or bs.std() == 0:
            continue
        sc.append((float(np.corrcoef(xs, bs)[0, 1]), c))
    sc.sort(reverse=True)
    sel[ym] = [c for _, c in sc[:K]]
    for c in sel[ym]:
        hist[c] = hist.get(c, 0) + 1
    log.info("SEL %s k=%d %s | corr %s", ym, len(sel[ym]), sel[ym],
             [round(v, 3) for v, _ in sc[:K]])

# ---------- 3) minute returns CHI cho coin duoc chon (CO CACHE) ----------
pool_sel = sorted({c for v in sel.values() for c in v})
log.info("pool duoc chon: %d coin", len(pool_sel))
if not pool_sel:
    raise SystemExit("POOL RONG: selection tra ve 0 coin")
json.dump(sel, open(f"{D}/dyn_sel.json", "w"), indent=1)
MONTHS = list(pd.period_range("2021-07", "2025-12", freq="M").strftime("%Y-%m"))
NPZ = f"{D}/dyn_minute.npz"
pos = {int(t): i for i, t in enumerate(z["bt_ts"].astype(np.int64))}
Mlen = len(pos)
if os.path.exists(NPZ):
    zz = np.load(NPZ)
    mz = {c: zz[c] for c in zz.files}
    log.info("nap minute cache: %d coin", len(mz))
else:
    lastpx = {c: np.full(Mlen, np.nan, np.float32) for c in pool_sel}
    for ym in MONTHS:
        d = pd.read_parquet(MT.kp(ym), columns=["ts", "sym", "close"])
        d = d[d["sym"].astype(str).isin(set(pool_sel))]
        d["ts"] = d["ts"].astype(np.int64)
        d["sym"] = d["sym"].astype(str)
        d = d.drop_duplicates(["sym", "ts"], keep="last")
        for c, grp in d.groupby("sym", sort=False, observed=True):
            idx = grp["ts"].map(pos)
            ok = idx.notna().to_numpy()
            if ok.any():
                lastpx[c][idx[ok].to_numpy(np.int64)] = grp["close"].to_numpy(np.float64)[ok]
        log.info("minute %s done", ym)
        del d
    mz = {}
    for c in pool_sel:
        p = lastpx[c]
        r = np.zeros(Mlen, np.float32)
        v = ~np.isnan(p)
        idx = np.where(v)[0]
        if len(idx) > 1:
            rr = np.log(p[idx[1:]] / p[idx[:-1]]).astype(np.float32)
            rr[np.diff(idx) != 1] = 0.0
            r[idx[1:]] = rr
        mz[c] = r
    del lastpx
    np.savez_compressed(NPZ, **mz)
    log.info("luu minute cache %s", NPZ)


def seed_ME(st):
    st.rec.sort()
    M = np.concatenate([m + np.arange(len(e)) for m, e in st.rec])
    E = np.concatenate([e for _, e in st.rec])
    return M, E


Mmax = max(int(seed_ME(st)[0].max()) for st in REG) + 1
R_MAX = int(max(Mmax, int(bt_g.max()) + 1))   # bt_g co the cham dung len(grid)
r_dyn = np.zeros(R_MAX)
for ym in sorted(sel):
    coins = [c for c in sel[ym] if c in mz]
    if not coins:
        continue
    y, m = int(ym[:4]), int(ym[5:])
    t0 = int((pd.Timestamp(year=y, month=m, day=1) - DAY0) // pd.Timedelta(minutes=1))
    t1 = int((pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthBegin(1) - DAY0) // pd.Timedelta(minutes=1))
    w = 1.0 / len(coins)
    for c in coins:
        v = (bt_g >= t0) & (bt_g < t1) & (bt_g < R_MAX)
        r_dyn[bt_g[v]] += w * mz[c][v]
log.info("r_dyn: %d phut khac 0 tren %d", int((r_dyn != 0).sum()), Mmax)

# ---------- 4) ap hedge ----------
res = {}
for s, st in zip(S, REG):
    M, E = seed_ME(st)
    Mtot = int(M.max()) + 1
    rr = np.zeros(Mtot)
    nn = min(Mtot, len(r_dyn))
    rr[:nn] = r_dyn[:nn]
    L = R.load_legs_minute(legs[s])
    diff = np.zeros(Mtot + 1)
    nq = (L["quantity"] * L["entry"]).to_numpy(float)
    np.add.at(diff, np.clip(L["m0"].to_numpy(), 0, Mtot), nq)
    np.add.at(diff, np.clip(L["m1"].to_numpy(), 0, Mtot), -nq)
    N = np.cumsum(diff)[:Mtot]
    Nprev = np.concatenate([[0.0], N[:-1]])
    base = stats(M, E)
    out = {"base": base}
    for h in HS:
        hp = -h * Nprev * (np.exp(rr) - 1) - FEE * h * np.abs(N - Nprev)
        Eh = E + np.cumsum(hp)[M]
        s_h = stats(M, Eh)
        days = pd.to_datetime(DAY0) + pd.to_timedelta(M // 1440, unit="D")
        s_h.update(hedge_pnl_year={int(k): float(v) for k, v in
                                   pd.Series(hp[M], index=days).groupby(days.year).sum().round(0).items()})
        s_h.update(luna=win_dd(M, Eh, "2022-05-01", "2022-07-01"),
                   ftx=win_dd(M, Eh, "2022-11-01", "2022-12-01"))
        out["h%.1f" % h] = s_h
    out["base"].update(luna=win_dd(M, E, "2022-05-01", "2022-07-01"), ftx=win_dd(M, E, "2022-11-01", "2022-12-01"))
    res[s] = out
    log.info("%s base dd22 %.2f cal %.2f pnl %.0f", s, base["dd22"], base["calmar22"], base["pnl"])
    for h in HS:
        x = out["h%.1f" % h]
        log.info("%s h%.1f dd22 %.2f cal %.2f pnl %.0f luna %.2f", s, h, x["dd22"], x["calmar22"], x["pnl"], x["luna"])

summary = {}
for h in HS:
    k = "h%.1f" % h
    ddd = np.array([res[s][k]["dd22"] - res[s]["base"]["dd22"] for s in S])
    dcal = np.array([res[s][k]["calmar22"] - res[s]["base"]["calmar22"] for s in S])
    dpnl = np.array([res[s][k]["pnl"] / res[s]["base"]["pnl"] - 1 for s in S])
    hw = T995 * dcal.std(ddof=1) / math.sqrt(len(S))
    go = bool((ddd >= 5.0).sum() >= 7 and dcal.mean() - hw > 0 and dpnl.mean() >= -0.5)
    agg = {f: float(np.mean([res[s][k][f] for s in S])) for f in ("cagr22", "dd22", "dd_all", "calmar22", "uw22", "pnl", "luna", "ftx")}
    summary[k] = dict(agg=agg, dDD_pos5=int((ddd >= 5.0).sum()), dDD_mean=float(ddd.mean()),
                      dCal_mean=float(dcal.mean()), dCal_ci99=[float(dcal.mean() - hw), float(dcal.mean() + hw)],
                      dPnL_mean=float(dpnl.mean()), GO=go)
    log.info("ARM %s %s | dDD>=5 %d/%d dDD %.2f dCal %.3f CI99 [%.3f, %.3f] dPnL %.1f%% GO=%s", k,
             {a: round(b, 2) for a, b in agg.items()}, (ddd >= 5.0).sum(), len(S), ddd.mean(), dcal.mean(),
             dcal.mean() - hw, dcal.mean() + hw, 100 * dpnl.mean(), go)

bagg = {f: float(np.mean([res[s]["base"][f] for s in S])) for f in ("cagr22", "dd22", "dd_all", "calmar22", "uw22", "pnl", "luna", "ftx")}
log.info("BASE %s", {a: round(b, 2) for a, b in bagg.items()})
gos = [k for k in summary if summary[k]["GO"]]
win = max(gos, key=lambda k: summary[k]["agg"]["calmar22"]) if gos else None
log.info("WINNER %s", win)
log.info("TOP coin xuat hien: %s", sorted(hist.items(), key=lambda x: -x[1])[:10])
json.dump(dict(per_seed=res, summary=summary, base=bagg, winner=win, selections=sel,
               coin_months=hist, k=K, window=WIN), open(f"{D}/book_hedge_dyn.json", "w"), indent=1)
