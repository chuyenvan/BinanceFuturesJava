#!/usr/bin/env python3
"""BOOK_HEDGE_BIGCOIN: hard-pick 1 coin TO (SOL/BNB/XRP/DOGE/ADA/LINK) lam hedge.

Dung cache dyn_minute.npz (return phut 77 coin). Cung harness, cung luat GO.
Tra loi cau hoi: coin to co du on dinh de chon cung khong, va co qua noi GO khong.
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
log = logging.getLogger("bhbig")

D = "/home/ubuntu/claude_master/bookhedge_dyn"
COINS = ["SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", "LINKUSDT", "ZILUSDT"]
HS = [0.5, 1.0]
FEE = 0.0005
T995 = 3.499483
S = I.SEEDS
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
R.run_mtm(legs, workers=3, chunk=30)
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
    dd22 = float(ddw.min() * 100)
    under = ddw < -1e-9
    dif = np.diff(np.concatenate([[0], under.astype(np.int8), [0]]))
    st_, en_ = np.where(dif == 1)[0], np.where(dif == -1)[0]
    uw = float((en_ - st_).max() / 1440.0) if len(st_) else 0.0
    e0 = E[M < W22][-1] if (M < W22).any() else Ew[0]
    yrs = (Mw[-1] - W22) / (1440 * 365.25)
    cagr = ((Ew[-1] / e0) ** (1 / yrs) - 1) * 100
    return dict(dd22=dd22, dd_all=dd_all, cagr22=float(cagr), uw22=float(uw),
                calmar22=float(cagr / abs(dd22)), pnl=float(E[-1] - R.CAP0))


def win_dd(M, E, a, b):
    t0 = int((pd.Timestamp(a) - DAY0) // pd.Timedelta(minutes=1))
    t1 = int((pd.Timestamp(b) - DAY0) // pd.Timedelta(minutes=1))
    w = (M >= t0) & (M < t1)
    x = E[w]
    return float((x / np.maximum.accumulate(x) - 1).min() * 100)


mz = dict(np.load(f"{D}/dyn_minute.npz"))
Mmax = max(int(np.concatenate([m + np.arange(len(e)) for m, e in st.rec]).max()) for st in REG) + 1
R_MAX = max(Mmax, int(bt_g.max()) + 1)

# r_global cho tung coin
RG = {}
for c in COINS:
    if c not in mz:
        log.warning("khong co minute cho %s -> bo qua", c)
        continue
    v = (bt_g >= 0) & (bt_g < R_MAX)
    arr = np.zeros(R_MAX)
    arr[bt_g[v]] = mz[c][v]
    RG[c] = arr

res = {}
for s, st in zip(S, REG):
    st.rec.sort()
    M = np.concatenate([m + np.arange(len(e)) for m, e in st.rec])
    E = np.concatenate([e for _, e in st.rec])
    Mtot = int(M.max()) + 1
    L = R.load_legs_minute(legs[s])
    diff = np.zeros(Mtot + 1)
    nq = (L["quantity"] * L["entry"]).to_numpy(float)
    np.add.at(diff, np.clip(L["m0"].to_numpy(), 0, Mtot), nq)
    np.add.at(diff, np.clip(L["m1"].to_numpy(), 0, Mtot), -nq)
    N = np.cumsum(diff)[:Mtot]
    Nprev = np.concatenate([[0.0], N[:-1]])
    out = {"base": stats(M, E)}
    for c, arr in RG.items():
        rr = arr[:Mtot]
        for h in HS:
            hp = -h * Nprev * (np.exp(rr) - 1) - FEE * h * np.abs(N - Nprev)
            Eh = E + np.cumsum(hp)[M]
            x = stats(M, Eh)
            x.update(luna=win_dd(M, Eh, "2022-05-01", "2022-07-01"))
            out["%s|h%.1f" % (c, h)] = x
        log.info("%s %s dd22 %.2f cal %.2f pnl %.0f | base dd22 %.2f cal %.2f", s, c,
                 out["%s|h0.5" % c]["dd22"], out["%s|h0.5" % c]["calmar22"], out["%s|h0.5" % c]["pnl"],
                 out["base"]["dd22"], out["base"]["calmar22"])
    res[s] = out

summary = {}
for c in RG:
    for h in HS:
        k = "%s|h%.1f" % (c, h)
        ddd = np.array([res[s][k]["dd22"] - res[s]["base"]["dd22"] for s in S])
        dcal = np.array([res[s][k]["calmar22"] - res[s]["base"]["calmar22"] for s in S])
        dpnl = np.array([res[s][k]["pnl"] / res[s]["base"]["pnl"] - 1 for s in S])
        hw = T995 * dcal.std(ddof=1) / math.sqrt(len(S))
        go = bool((ddd >= 5.0).sum() >= 7 and dcal.mean() - hw > 0 and dpnl.mean() >= -0.5)
        agg = {f: float(np.mean([res[s][k][f] for s in S])) for f in ("cagr22", "dd22", "calmar22", "pnl")}
        summary[k] = dict(agg=agg, dDD_pos5=int((ddd >= 5.0).sum()), dDD_mean=float(ddd.mean()),
                          dCal_mean=float(dcal.mean()), dCal_ci99=[float(dcal.mean() - hw), float(dcal.mean() + hw)],
                          dPnL_mean=float(dpnl.mean()), GO=go)
        log.info("ARM %s | dDD>=5 %d/8 dDD %.2f dCal %.3f CI99 [%.3f, %.3f] dPnL %.1f%% GO=%s",
                 k, (ddd >= 5.0).sum(), ddd.mean(), dcal.mean(), dcal.mean() - hw, dcal.mean() + hw,
                 100 * dpnl.mean(), go)

json.dump(dict(per_seed=res, summary=summary), open(f"{D}/book_hedge_bigcoin.json", "w"), indent=1)
