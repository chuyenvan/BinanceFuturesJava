#!/usr/bin/env python3
"""BOOK_HEDGE_AUDIT (PREREG_BOOK_HEDGE_AUDIT): cham lai ho BOOK_HEDGE bang harness sua (giu so luong giua su kien)."""
import json
import logging
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402  (patch R -> Vision) PHAI truoc
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import iso_risk_driver as I  # noqa: E402
import reset_rule_score as R  # noqa: E402

assert R._work is MT._work_vision
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("hx")
OUT = "/home/ubuntu/claude_master/hedge_audit"
S = I.SEEDS
HS = [0.5, 1.0]
FEE = 0.0005
T995 = 3.499483
DAY0 = pd.Timestamp(R.DAY0)
D0MS = int(DAY0.value // 10 ** 6)


def mi(ts):
    return int((pd.Timestamp(ts) - DAY0) // pd.Timedelta(minutes=1))


W22, W23 = mi("2022-01-01"), mi("2023-01-01")
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
R.run_mtm(legs, workers=3, chunk=30)
ME = {}
for s, st in zip(S, REG):
    st.rec.sort()
    ME[s] = (np.concatenate([m + np.arange(len(e)) for m, e in st.rec]), np.concatenate([e for _, e in st.rec]))
RMAX = max(int(M.max()) for M, _ in ME.values()) + 1

# ---- return phut tung cong cu tren luoi phut-since-DAY0 ----
zb = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
bt_g = (zb["bt_ts"].astype(np.int64) - D0MS) // 60000
vb = (bt_g >= 0) & (bt_g < RMAX)


def grid_from(ts, r):
    g = (ts.astype(np.int64) - D0MS) // 60000
    a = np.zeros(RMAX)
    ok = (g >= 0) & (g < RMAX)
    a[g[ok]] = r[ok]
    return a


RET = {"BTCUSDT": grid_from(zb["bt_ts"], zb["bt_r"])}
ze = np.load("/home/ubuntu/claude_master/bookhedge_eth/eth_index.npz")
RET["ETHUSDT"] = grid_from(ze["bt_ts"], ze["bt_r"])
zz = np.load("/home/ubuntu/claude_master/bookhedge_alt/zil_index.npz")
RET["ZILUSDT"] = grid_from(zz["bt_ts"], zz["bt_r"])
mz = np.load("/home/ubuntu/claude_master/bookhedge_dyn/dyn_minute.npz")
for c in mz.files:
    a = np.zeros(RMAX)
    a[bt_g[vb]] = mz[c][vb]
    RET[c] = a
log.info("cong cu co return: %d", len(RET))

sel = json.load(open("/home/ubuntu/claude_master/bookhedge_dyn/dyn_sel.json"))


def dyn_segments(drop_luna=False):
    seg = []
    for ym in sorted(sel):
        coins = [c for c in sel[ym] if c in RET and not (drop_luna and ym == "2022-05" and c == "LUNAUSDT")]
        y, m = int(ym[:4]), int(ym[5:])
        t0 = mi(pd.Timestamp(year=y, month=m, day=1))
        t1 = mi(pd.Timestamp(year=y, month=m, day=1) + pd.offsets.MonthBegin(1))
        seg.append((t0, t1, {c: 1.0 / len(coins) for c in coins} if coins else {}))
    return seg


ARMS = {c.replace("USDT", ""): [(0, RMAX, {c: 1.0})] for c in
        ["BTCUSDT", "ETHUSDT", "ZILUSDT", "LINKUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT"]}
ARMS["DYN"] = dyn_segments()
ARMS["DYN_noLUNA"] = dyn_segments(True)
ADV = dict(BTC=16239, ETH=7492, ZIL=11.9, LINK=219, ADA=208, DOGE=655, XRP=514, BNB=446, SOL=2704, DYN=None, DYN_noLUNA=None)


def stats(M, E, w0):
    w = M >= w0
    Ew, Mw = E[w], M[w]
    ddw = Ew / np.maximum.accumulate(Ew) - 1
    dif = np.diff(np.concatenate([[0], (ddw < -1e-9).astype(np.int8), [0]]))
    st_, en_ = np.where(dif == 1)[0], np.where(dif == -1)[0]
    e0 = E[M < w0][-1] if (M < w0).any() else Ew[0]
    yrs = (Mw[-1] - w0) / (1440 * 365.25)
    cagr = ((Ew[-1] / e0) ** (1 / yrs) - 1) * 100
    dd = float(ddw.min() * 100)
    return dict(dd=dd, cagr=float(cagr), calmar=float(cagr / abs(dd)), uw=float((en_ - st_).max() / 1440.0) if len(st_) else 0.0,
                pnl=float(E[-1] - R.CAP0))


def open_notional(s, Mtot):
    L = R.load_legs_minute(legs[s])
    diff = np.zeros(Mtot + 1)
    nq = (L["quantity"] * L["entry"]).to_numpy(float)
    np.add.at(diff, np.clip(L["m0"].to_numpy(), 0, Mtot), nq)
    np.add.at(diff, np.clip(L["m1"].to_numpy(), 0, Mtot), -nq)
    return np.cumsum(diff)[:Mtot]


PC = {}


def price(c):
    if c not in PC:
        lp = np.cumsum(RET[c])
        PC[c] = np.exp(lp - lp.max())                     # chi so gia, chuan hoa tranh tran so
    return PC[c]


def seg_weight(seg, c, pts):
    """trong so coin c tai cac phut pts theo segment [t0,t1)."""
    st_ = np.array([a for a, _, _ in seg])
    en_ = np.array([b for _, b, _ in seg])
    wv = np.array([w.get(c, 0.0) for _, _, w in seg])
    si = np.searchsorted(st_, pts, side="right") - 1
    ok = (si >= 0) & (pts < en_[np.clip(si, 0, None)])
    return np.where(ok, wv[np.clip(si, 0, None)], 0.0)


def hedge_new(N, seg, h, extra_bps, bounds):
    """giu SO LUONG giua su kien (N doi hoac doi trong so); phi tren luong thuc giao dich."""
    Mtot = len(N)
    ev = np.nonzero(np.diff(N, prepend=0.0))[0]
    ev = np.unique(np.concatenate([ev, [b for b in bounds if 0 <= b < Mtot]])).astype(np.int64)
    m = np.arange(Mtot)
    k = np.searchsorted(ev, m - 1, side="right") - 1  # su kien cuoi <= m-1
    has = k >= 0
    pnl = np.zeros(Mtot)
    fee = np.zeros(Mtot)
    rate = FEE + extra_bps / 1e4
    for c in sorted({c for _, _, w in seg for c in w}):
        wev = seg_weight(seg, c, ev)
        if not wev.any():
            continue
        P = price(c)[:Mtot]
        T = h * wev * N[ev]                               # notional muc tieu tai su kien
        q = T / P[ev]
        qm = np.where(has, q[np.clip(k, 0, None)], 0.0)
        dP = np.diff(P, prepend=P[0])
        pnl -= qm * dP
        qprev = np.concatenate([[0.0], q[:-1]])
        traded = np.abs(T - qprev * P[ev])
        np.add.at(fee, ev, rate * traded)
    return pnl - fee


def hedge_old(N, seg, h):
    Mtot = len(N)
    rmix = np.zeros(Mtot)
    pts = np.arange(Mtot)
    for c in sorted({c for _, _, w in seg for c in w}):
        rmix += seg_weight(seg, c, pts) * RET[c][:Mtot]
    Np = np.concatenate([[0.0], N[:-1]])
    return -h * Np * (np.exp(rmix) - 1) - FEE * h * np.abs(N - Np)


def boot(eb, eh, nb=2000, blk=20, seed=7):
    rb, rh = np.diff(eb) / eb[:-1], np.diff(eh) / eh[:-1]
    T = len(rb)
    rng = np.random.default_rng(seed)
    nblk = int(math.ceil(T / blk))
    out = np.zeros((nb, 2))
    for i in range(nb):
        st_ = rng.integers(0, T - blk + 1, nblk)
        idx = (st_[:, None] + np.arange(blk)[None, :]).ravel()[:T]

        def cm(r):
            e = np.cumprod(1 + r[idx])
            dd = (e / np.maximum.accumulate(e) - 1).min()
            cg = e[-1] ** (365.25 / T) - 1
            return cg / abs(dd), dd
        cb, db = cm(rb)
        ch, dh = cm(rh)
        out[i] = (ch - cb, (dh - db) * 100)
    return out


res = {"V0": {}, "arms": {}}
NS = {s: open_notional(s, int(ME[s][0].max()) + 1) for s in S}
for name, seg in ARMS.items():
    bounds = [t0 for t0, _, _ in seg]
    for h in HS:
        key = "%s_h%.1f" % (name, h)
        per, eod_b, eod_h = {}, [], []
        for s in S:
            M, E = ME[s]
            N = NS[s]
            base22, base23 = stats(M, E, W22), stats(M, E, W23)
            old = stats(M, E + np.cumsum(hedge_old(N, seg, h))[M], W22)
            if s == S[0]:
                res["V0"][key] = old["dd"]
            hp = hedge_new(N, seg, h, 0.0, bounds)
            ch = np.cumsum(hp)
            Eh = E + ch[M]
            hp25 = hedge_new(N, seg, h, 25.0, bounds)
            Eh25 = E + np.cumsum(hp25)[M]
            days = (M // 1440)
            yr = (DAY0 + pd.to_timedelta(days, unit="D")).year
            hy = pd.Series(hp[M]).groupby(np.asarray(yr)).sum().round(0).to_dict()
            per[s] = dict(base22=base22, base23=base23, h22=stats(M, Eh, W22), h23=stats(M, Eh, W23), old22=old,
                          h22_25=stats(M, Eh25, W22), hedge_pnl_year={int(a): float(b) for a, b in hy.items()})
            ser_b = pd.Series(E).groupby(days).last()
            ser_h = pd.Series(Eh).groupby(days).last()
            eod_b.append(ser_b)
            eod_h.append(ser_h)
        # C1 / C4
        def rule(tag):
            ddd = np.array([per[s][tag]["dd"] - per[s]["base22"]["dd"] for s in S])
            dc = np.array([per[s][tag]["calmar"] - per[s]["base22"]["calmar"] for s in S])
            dp = np.array([per[s][tag]["pnl"] / per[s]["base22"]["pnl"] - 1 for s in S])
            hw = T995 * dc.std(ddof=1) / math.sqrt(8)
            return dict(pos5=int((ddd >= 5).sum()), dDD=float(ddd.mean()), dCal=float(dc.mean()),
                        ci99=[float(dc.mean() - hw), float(dc.mean() + hw)], dPnL=float(dp.mean()),
                        GO=bool((ddd >= 5).sum() >= 7 and dc.mean() - hw > 0 and dp.mean() >= -0.5))
        c1, c4 = rule("h22"), rule("h22_25")
        # C2 bootstrap tren equity ngay trung binh seed tu 2022-01-01
        d0 = W22 // 1440
        B = pd.concat(eod_b, axis=1).mean(axis=1)
        H = pd.concat(eod_h, axis=1).mean(axis=1)
        B, H = B[B.index >= d0 - 1].to_numpy(), H[H.index >= d0 - 1].to_numpy()
        bs = boot(B, H)
        c2 = dict(p_dCal=float((bs[:, 0] > 0).mean()), p_dDD=float((bs[:, 1] > 0).mean()),
                  med_dCal=float(np.median(bs[:, 0])), med_dDD=float(np.median(bs[:, 1])))
        c2["PASS"] = bool(c2["p_dCal"] >= 0.9 and c2["p_dDD"] >= 0.9)
        dd23 = float(np.mean([per[s]["h23"]["dd"] - per[s]["base23"]["dd"] for s in S]))
        cal23 = float(np.mean([per[s]["h23"]["calmar"] - per[s]["base23"]["calmar"] for s in S]))
        c3 = dict(dDD23=dd23, dCal23=cal23, PASS=bool(dd23 >= -2.0))
        agg = {f: float(np.mean([per[s]["h22"][f] for s in S])) for f in ("cagr", "dd", "calmar", "uw", "pnl")}
        agg_old = {f: float(np.mean([per[s]["old22"][f] for s in S])) for f in ("cagr", "dd", "calmar", "pnl")}
        log.info("OLD %-14s (harness cu) CAGR %.2f DD %.2f Cal %.2f PnL %.0f", key, agg_old["cagr"], agg_old["dd"],
                 agg_old["calmar"], agg_old["pnl"])
        hyr = {y: float(np.mean([per[s]["hedge_pnl_year"].get(y, 0.0) for s in S])) for y in range(2021, 2026)}
        tiem = bool(c1["GO"] and c2["PASS"] and c3["PASS"] and c4["GO"])
        res["arms"][key] = dict(agg=agg, agg_old=agg_old, C1=c1, C2=c2, C3=c3, C4=c4, TIEM_NANG=tiem, hedge_pnl_year=hyr,
                                adv=ADV.get(name), per_seed=per)
        log.info("ARM %-14s CAGR %.2f DD %.2f Cal %.2f UW %.0f PnL %.0f | C1 %d/8 dCal %.3f [%.3f,%.3f] dPnL %.1f%% GO=%s | "
                 "C2 P(dCal>0) %.2f P(dDD>0) %.2f med %.3f/%.2f | C3 dDD23 %.2f dCal23 %.3f | C4 GO25=%s | TIEM=%s | hedge/yr %s",
                 key, agg["cagr"], agg["dd"], agg["calmar"], agg["uw"], agg["pnl"], c1["pos5"], c1["dCal"], c1["ci99"][0],
                 c1["ci99"][1], 100 * c1["dPnL"], c1["GO"], c2["p_dCal"], c2["p_dDD"], c2["med_dCal"], c2["med_dDD"],
                 dd23, cal23, c4["GO"], tiem, {k: round(v) for k, v in hyr.items()})
bb = {f: float(np.mean([stats(*ME[s], W22)[f] for s in S])) for f in ("cagr", "dd", "calmar", "uw", "pnl")}
b23 = {f: float(np.mean([stats(*ME[s], W23)[f] for s in S])) for f in ("cagr", "dd", "calmar")}
log.info("BASE22 %s BASE23 %s", {k: round(v, 2) for k, v in bb.items()}, {k: round(v, 2) for k, v in b23.items()})
log.info("V0 (harness cu, seed %s, h0.5): %s  (cong bo: BTC -17.81 la TB 8 seed; seed A1 BTC = -17.23)", S[0], res["V0"])
res["base22"], res["base23"] = bb, b23
json.dump(res, open(OUT + "/hedge_audit.json", "w"), indent=1, default=float)
