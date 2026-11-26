#!/usr/bin/env python3
"""G3 simulator (prereg sec 4-6): overlapping tranches, daily MTM, spread cost, swap, broker margin.
- tranche per eligible ccy-week with signal != 0: w = dir * signal / (N_dt * H); opened at entry_date (FRED noon price),
  closed at first valid price date >= anchor + 7*H days (calendar). Missing report weeks leave that 1/H slot empty.
- fixed units u = w / P_entry (P = USD per ccy); daily PnL (fraction of constant capital, additive, no compounding):
  sum U[d-1]*(P[d]-P[d-1]) + W[d-1]*swap[d] - |W[d-1]|*margin[d]*cm - cost[d]*cm.
- swap: per CALENDAR day in (D[d-1], D[d]] (r_ccy - r_usd)/360 with OECD rate of month(day)-1; margin 1.0 %/yr per position.
- cost: half of round trip at open and half at close; round trip = max(pips/quote, 3 bp) (EURUSD 0.8 pip only) (ERRATA2 J1).
  DEFAULT netting=False: every tranche pays its own open and close (ERRATA2 J5). netting=True (descriptive only) charges
  |net weight change| per ccy per day.
- margin (ERRATA3 K2): 1 %/yr on SUM of |w| of open tranches (no offset between long and short tranches of one ccy).
- cm = cost multiplier (x2 scenario doubles spread AND margin).
LOCK: refuses real data unless unlocked with --real I_HAVE_A1_PASS.
"""
import argparse
import logging
import os

import numpy as np
import pandas as pd

import load_g3
import sig_g3

LOG = logging.getLogger("g3.sim")
REAL_TOKEN = "I_HAVE_A1_PASS"
_UNLOCK = {"real": False}
MARGIN = 0.01
SIM_START = pd.Timestamp("1986-01-01")


def unlock_real(token):
    if token != REAL_TOKEN:
        raise PermissionError("real-data simulation locked: needs --real %s (after A1 code audit)" % REAL_TOKEN)
    _UNLOCK["real"] = True


def _guard(data):
    if data.get("real", True) and not _UNLOCK["real"]:
        raise PermissionError("real-data simulation locked: needs --real %s" % REAL_TOKEN)


def prepare_market(data):
    if "_mkt" in data:
        return data["_mkt"]
    px = data["px"]
    px = px[px.index >= SIM_START]
    D = px.index
    ccys = list(px.columns)
    P = px.ffill().values
    Q = data["quote"].reindex(D).ffill().values
    pip = np.array([load_g3.CCY[c]["pip"] for c in ccys])
    rt = np.array([load_g3.CCY[c]["rt_pips"] for c in ccys])
    mn = np.array([load_g3.CCY[c]["rt_min_frac"] for c in ccys])
    with np.errstate(invalid="ignore", divide="ignore"):
        half = np.maximum(rt * pip / Q, mn) / 2.0  # ERRATA2 J1: max(pips, 3 bp) round trip; NaN quote stays NaN
    rates = data["rates"]
    cal = pd.date_range(D[0], D[-1], freq="D")
    m1 = (cal.to_period("M") - 1).to_timestamp()
    R = rates.reindex(m1)
    diff = np.zeros((len(cal), len(ccys)))
    miss = 0
    for j, c in enumerate(ccys):
        v = (R[c].values - R["USD"].values) / 100.0 / 360.0
        miss += int(np.isnan(v).sum())
        diff[:, j] = np.nan_to_num(v, nan=0.0)
    cdiff = np.vstack([np.zeros((1, len(ccys))), np.cumsum(diff, axis=0)])
    pos = cal.searchsorted(D, side="left")  # index of D[d] in cal
    cum_at = cdiff[pos + 1]  # cumulative through day D[d] inclusive
    sw = np.zeros_like(cum_at)
    sw[1:] = cum_at[1:] - cum_at[:-1]
    ndays = np.zeros(len(D))
    ndays[1:] = (D[1:] - D[:-1]).days
    mg = ndays * MARGIN / 360.0
    mkt = dict(D=D, ccys=ccys, P=P, half=half, sw=sw, mg=mg, cum_sw=np.cumsum(sw, axis=0), cum_mg=np.cumsum(mg),
               rate_missing_days=miss)
    data["_mkt"] = mkt
    return mkt


def first_valid_vec(data, ccys, ts):
    """Vectorised: first date >= ts with a valid FRED price for each ccy (NaT if none)."""
    px = data["px"]
    out = np.full(len(ts), np.datetime64("NaT"), dtype="datetime64[ns]")
    ccys = np.asarray(ccys)
    ts = pd.DatetimeIndex(ts).values
    for c in np.unique(ccys):
        v = px.index[px[c].notna().values].values
        m = ccys == c
        i = np.searchsorted(v, ts[m], side="left")
        o = np.full(m.sum(), np.datetime64("NaT"), dtype="datetime64[ns]")
        ok = i < len(v)
        o[ok] = v[i[ok]]
        out[m] = o
    return pd.DatetimeIndex(out)


def make_tranches(data, book, H, direction, start=None, end=None):
    """No returns: just positions. direction +1 = H_TD, -1 = H_ND."""
    b = book[book["eligible"] & (book["signal"] != 0)]
    if start is not None:
        b = b[b["entry_date"] >= pd.Timestamp(start)]
    if end is not None:
        b = b[b["entry_date"] <= pd.Timestamp(end)]
    ex = first_valid_vec(data, b["ccy"].values, pd.DatetimeIndex(b["anchor"].values) + pd.Timedelta(days=7 * H))
    sign = direction * b["signal"].values
    out = pd.DataFrame(dict(ccy=b["ccy"].values, report_date=b["date"].values, anchor=b["anchor"].values,
                            entry_date=b["entry_date"].values, exit_date=ex, w=sign / (b["N_dt"].values * H),
                            z=b["z"].values, sign=sign))
    return out.reset_index(drop=True)


def simulate(data, tr, cost_mult=1.0, netting=False, close_at=None):
    """close_at: tranches still open after this date are force-closed there WITH closing cost (ERRATA3 K3); default =
    last data date (open positions at data end pay the closing cost too)."""
    _guard(data)
    m = prepare_market(data)
    D, P, n, k = m["D"], m["P"], len(m["D"]), len(m["ccys"])
    cix = {c: j for j, c in enumerate(m["ccys"])}
    dU = np.zeros((n + 1, k))
    dW = np.zeros((n + 1, k))
    gross_ev = np.zeros((n + 1, k))
    dG = np.zeros((n + 1, k))
    last = n - 1 if close_at is None else int(D.searchsorted(pd.Timestamp(close_at), side="right") - 1)
    if len(tr):
        j = np.array([cix[c] for c in tr["ccy"].values])
        ed = pd.DatetimeIndex(tr["entry_date"].values)
        a = D.searchsorted(ed)
        if (a >= n).any() or (D[np.minimum(a, n - 1)] != ed).any():
            raise ValueError("entry date not in calendar")
        xd = pd.DatetimeIndex(tr["exit_date"].values)
        b = np.where(xd.isna(), n, D.searchsorted(xd.fillna(D[-1])))
        if (a > last).any():
            raise ValueError("tranche entered after close_at")
        b = np.minimum(b, last)  # force close at close_at / data end, cost charged (K3)
        w = tr["w"].values.astype(float)
        s = tr["sign"].values.astype(float)
        u = w / P[a, j]
        np.add.at(dU, (a, j), u)
        np.add.at(dU, (b, j), -u)
        np.add.at(dW, (a, j), w)
        np.add.at(dW, (b, j), -w)
        np.add.at(gross_ev, (a, j), np.abs(w))
        np.add.at(dG, (a, j), np.abs(w))
        np.add.at(dG, (b, j), -np.abs(w))
        np.add.at(gross_ev, (b, j), np.abs(w))
        bb = np.minimum(b, n - 1)
        hb = np.where(b < n, m["half"][bb, j], 0.0)
        net = (s * (P[bb, j] / P[a, j] - 1.0) + s * (m["cum_sw"][bb, j] - m["cum_sw"][a, j])
               - cost_mult * (m["cum_mg"][bb] - m["cum_mg"][a]) - cost_mult * (m["half"][a, j] + hb))
        trades = pd.DataFrame(dict(ccy=tr["ccy"].values, entry_date=ed, exit_or_last=D[bb], open_at_end=b >= n, w=w,
                                   sign=s, net_ret_unit=net))
    else:
        trades = pd.DataFrame(columns=["ccy", "entry_date", "exit_or_last", "open_at_end", "w", "sign", "net_ret_unit"])
    U = np.cumsum(dU[:n], axis=0)
    Wt = np.cumsum(dW[:n], axis=0)
    ev = np.abs(dW[:n]) if netting else gross_ev[:n]
    price = np.zeros((n, k))
    price[1:] = U[:-1] * (P[1:] - P[:-1])
    price = np.nan_to_num(price, nan=0.0)
    swap = np.zeros((n, k))
    swap[1:] = Wt[:-1] * m["sw"][1:]
    marg = np.zeros((n, k))
    Gt = np.cumsum(dG[:n], axis=0)  # sum of |w| of open tranches (ERRATA3 K2: margin per tranche, not net)
    marg[1:] = -cost_mult * Gt[:-1] * m["mg"][1:, None]
    cost = -cost_mult * ev * np.nan_to_num(m["half"], nan=0.0)
    tot = price + swap + marg + cost
    daily = pd.DataFrame(dict(ret=tot.sum(1), price=price.sum(1), swap=swap.sum(1), margin=marg.sum(1), cost=cost.sum(1),
                              turnover=np.abs(dW[:n]).sum(1), gross=np.abs(Wt).sum(1)), index=D)
    per_ccy = pd.DataFrame(tot, index=D, columns=m["ccys"])
    return dict(daily=daily, per_ccy=per_ccy, trades=trades, net_pos=pd.DataFrame(Wt, index=D, columns=m["ccys"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", default=None)
    ap.add_argument("--group", default="NonComm_LEG", choices=load_g3.GROUPS)
    ap.add_argument("--W", type=int, default=52, choices=sig_g3.WS)
    ap.add_argument("--H", type=int, default=4, choices=(1, 4))
    ap.add_argument("--dir", type=int, default=1, choices=(1, -1))
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g3/out"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    unlock_real(a.real)  # raises before any data is loaded
    data = load_g3.load()
    book = sig_g3.build_book(data, a.group, a.W)
    tr = make_tranches(data, book, a.H, a.dir, start=sig_g3.PERIODS[a.group]["train"][0])
    res = simulate(data, tr)
    f = os.path.join(a.out, "sim_%s_W%d_H%d_d%d.csv" % (a.group, a.W, a.H, a.dir))
    res["daily"].to_csv(f)
    LOG.info("wrote %s (%d tranches)", f, len(tr))


if __name__ == "__main__":
    main()
