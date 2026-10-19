#!/usr/bin/env python3
"""BOOK_HEDGE (PREREG_BOOK_HEDGE): overlay short BTC h*N_open tren equity MTM phut (Vision) cua 8 run OFF."""
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
log = logging.getLogger("bh")
D = "/home/ubuntu/claude_master/bookhedge_alt"
S = I.SEEDS
HS = [0.5, 1.0]
FEE = 0.0005
T995 = 3.499483
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
iso = json.load(open(I.D + "/iso_tab2.json"))["per_key"]

z = np.load("/home/ubuntu/claude_master/bookhedge_alt/zil_index.npz")
bt_g = (z["bt_ts"].astype(np.int64) - int(DAY0.value // 10 ** 6)) // 60000
log.info("bt_ts dau %s cuoi %s", pd.to_datetime(int(z["bt_ts"][0]), unit="ms"), pd.to_datetime(int(z["bt_ts"][-1]), unit="ms"))


def stats(M, E):
    """M: phut toan cuc, E: equity. Tra DD22 (2 kieu dinh), DD toan ky, CAGR22, UW22 (ngay), equity cuoi ngay."""
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


res = {}
for s, st in zip(S, REG):
    st.rec.sort()
    M = np.concatenate([m + np.arange(len(e)) for m, e in st.rec])
    E = np.concatenate([e for _, e in st.rec])
    Mtot = int(M.max()) + 1
    r = np.zeros(Mtot)
    ok = (bt_g >= 0) & (bt_g < Mtot)
    r[bt_g[ok]] = z["bt_r"][ok]
    have = np.zeros(Mtot, bool)
    have[bt_g[ok]] = True
    L = R.load_legs_minute(legs[s])
    diff = np.zeros(Mtot + 1)
    nq = (L["quantity"] * L["entry"]).to_numpy(float)
    np.add.at(diff, np.clip(L["m0"].to_numpy(), 0, Mtot), nq)
    np.add.at(diff, np.clip(L["m1"].to_numpy(), 0, Mtot), -nq)
    N = np.cumsum(diff)[:Mtot]
    Nprev = np.concatenate([[0.0], N[:-1]])
    miss = int(((Nprev > 0) & ~have).sum())
    base = stats(M, E)
    log.info("V1 %s dd22 reset %.4f carry %.4f | ISO %.4f | missBTC %d / %d phut co vi the", s, base["dd22"], base["dd22_carry"],
             iso["OFF_" + s]["dd_mtm22"], miss, int((Nprev > 0).sum()))
    out = {"base": base, "missBTC": miss, "minutes_open": int((Nprev > 0).sum())}
    ed = pd.Series(E, index=M)
    for h in HS:
        hp = -h * Nprev * (np.exp(r) - 1) - FEE * h * np.abs(N - Nprev)
        cum = np.cumsum(hp)
        Eh = E + cum[M]
        st_h = stats(M, Eh)
        days = pd.to_datetime(DAY0) + pd.to_timedelta(M // 1440, unit="D")
        hy = pd.Series(hp[M], index=days).groupby(days.year).sum().round(0).to_dict()
        st_h.update(luna=win_dd(M, Eh, "2022-05-01", "2022-07-01"), ftx=win_dd(M, Eh, "2022-11-01", "2022-12-01"),
                    hedge_pnl_year={int(k): float(v) for k, v in hy.items()}, fees=float((FEE * h * np.abs(N - Nprev)).sum()))
        out["h%.1f" % h] = st_h
    out["base"].update(luna=win_dd(M, E, "2022-05-01", "2022-07-01"), ftx=win_dd(M, E, "2022-11-01", "2022-12-01"))
    eod = ed.groupby(M // 1440).last()
    btc_d = pd.Series(r).groupby(np.arange(Mtot) // 1440).sum()
    rb = eod.pct_change().dropna()
    j = rb.index.intersection(btc_d.index)
    out["corr_book_btc_daily"] = float(np.corrcoef(rb.loc[j], np.expm1(btc_d.loc[j]))[0, 1])
    res[s] = out
    log.info("%s base %s", s, {k: round(v, 2) for k, v in base.items() if isinstance(v, float)})
    for h in HS:
        x = out["h%.1f" % h]
        log.info("%s h%.1f %s", s, h, {k: round(v, 2) for k, v in x.items() if isinstance(v, float)})

summary = {}
for h in HS:
    k = "h%.1f" % h
    ddd = np.array([res[s][k]["dd22"] - res[s]["base"]["dd22"] for s in S])
    dcal = np.array([res[s][k]["calmar22"] - res[s]["base"]["calmar22"] for s in S])
    dpnl = np.array([res[s][k]["pnl"] / res[s]["base"]["pnl"] - 1 for s in S])
    hw = T995 * dcal.std(ddof=1) / math.sqrt(8)
    go = bool((ddd >= 5.0).sum() >= 7 and dcal.mean() - hw > 0 and dpnl.mean() >= -0.5)
    agg = {f: float(np.mean([res[s][k][f] for s in S])) for f in ("cagr22", "dd22", "dd_all", "calmar22", "uw22", "pnl", "luna", "ftx")}
    summary[k] = dict(agg=agg, dDD_pos5=int((ddd >= 5.0).sum()), dDD_mean=float(ddd.mean()), dCal_mean=float(dcal.mean()),
                      dCal_ci99=[float(dcal.mean() - hw), float(dcal.mean() + hw)], dPnL_mean=float(dpnl.mean()), GO=go)
    log.info("ARM %s %s | dDD>=5: %d/8 dDD %.2f dCal %.3f CI99 [%.3f, %.3f] dPnL %.1f%% GO=%s", k,
             {a: round(b, 2) for a, b in agg.items()}, (ddd >= 5.0).sum(), ddd.mean(), dcal.mean(), dcal.mean() - hw,
             dcal.mean() + hw, 100 * dpnl.mean(), go)
bagg = {f: float(np.mean([res[s]["base"][f] for s in S])) for f in ("cagr22", "dd22", "dd_all", "calmar22", "uw22", "pnl", "luna", "ftx")}
log.info("BASE %s corr book-BTC ngay %.3f", {a: round(b, 2) for a, b in bagg.items()}, np.mean([res[s]["corr_book_btc_daily"] for s in S]))
gos = [k for k in summary if summary[k]["GO"]]
win = max(gos, key=lambda k: summary[k]["agg"]["calmar22"]) if gos else None
log.info("WINNER %s", win)
json.dump(dict(per_seed=res, summary=summary, base=bagg, winner=win), open(D + "/book_hedge_alt.json", "w"), indent=1)
