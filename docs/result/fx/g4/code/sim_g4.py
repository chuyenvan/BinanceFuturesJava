#!/usr/bin/env python3
"""G4 trade simulator (prereg sec 3-4 + ERRATA2 J1 + CHOT MASTER). Prices are BID closes.
- entry at close of bar e (= event bar + 1); reference price ce = BID close; L pays half spread (ASK), S sells at BID; the
  round-trip cost C = max(3 pip, 3 bp) (EURUSD 0.8 pip) is charged half at entry and half at exit (L exits at BID, S at ASK).
- exits evaluated at every 1-min close: SL d <= -2.0 sig60; trailing armed when peak d >= 1.0 sig60, exit when d <= peak - 0.5 sig60
  (peak of closes); time-stop at the first bar with open time >= entry bar open + TS (exit at its close). d = side*(P/ce - 1).
- bar after a gap > 5 min: the conditions are first checked at its OPEN (gap fill at open, no interpolation), then at its close.
- exit cost x3 if the exit bar is in 16:55-17:15 NY or < 30 min after a gap > 60 min; +0.5 C slippage on SL / time-stop / end.
- swap per 17:00 NY rollover crossed (Friday x3): side*(r_base - r_quote)/360 (OECD month m-1) - 1 %/yr broker margin.
- cost_mult (x2 scenario) multiplies spread, slippage and margin. Sizing: each trade notional = 1/len(pairs) of capital.
LOCK: refuses real data unless unlock_real("I_HAVE_A1_PASS")."""
import logging

import numpy as np

import sig_g4

LOG = logging.getLogger("g4.sim")
REAL_TOKEN = "I_HAVE_A1_PASS"
_UNLOCK = {"real": False}
SL, ARM, GAP = 2.0, 1.0, 0.5
MARGIN = 0.01
REASONS = np.array(["SL", "TRAIL", "TS", "END"])


def unlock_real(token):
    if token != REAL_TOKEN:
        raise PermissionError("real-data simulation locked: needs --real %s" % REAL_TOKEN)
    _UNLOCK["real"] = True


def _guard(data):
    if data.get("real", True) and not _UNLOCK["real"]:
        raise PermissionError("real-data simulation locked: needs --real %s" % REAL_TOKEN)


def trades_batch(d, e, side, sg, TS, cost_mult=1.0, want_path=False):
    """Independent trades entered at close of bars e (array). side +1/-1 (scalar or array), sg = sigma60 per trade."""
    import load_g4
    t, o, c, n = d["t"], d["o"], d["c"], len(d["t"])
    e = np.asarray(e, dtype=np.int64)
    m = len(e)
    side = np.broadcast_to(np.asarray(side, float), (m,)).copy()
    sg = np.asarray(sg, float)
    tlim = t[e] + TS
    Lb = np.searchsorted(t, tlim, side="left")  # first bar with open time >= limit
    end_ = np.minimum(Lb, n - 1)
    K = TS + 1
    out = {k: np.empty(m) for k in ("gross", "cost", "swap", "net")}
    xi = np.empty(m, np.int64)
    rs = np.empty(m, np.int64)
    at_open = np.empty(m, bool)
    paths = []
    ch = max(1, 3000000 // K)
    for s0 in range(0, m, ch):
        sl = slice(s0, min(m, s0 + ch))
        ee, ss, gg, en = e[sl], side[sl], sg[sl], end_[sl]
        idx = ee[:, None] + 1 + np.arange(K)[None, :]
        val = idx <= en[:, None]
        idx = np.minimum(idx, n - 1)
        ce = c[ee][:, None]
        dc = ss[:, None] * (c[idx] / ce - 1.0)
        dc = np.where(val, dc, 0.0)
        pk = np.maximum.accumulate(np.maximum(dc, 0.0), axis=1)
        pprev = np.concatenate([np.zeros((len(ee), 1)), pk[:, :-1]], axis=1)
        do = ss[:, None] * (o[idx] / ce - 1.0)
        gap = d["gap5"][idx]
        g = gg[:, None]
        tl = tlim[sl][:, None]
        sl_o = gap & (do <= -SL * g)
        tr_o = gap & (pprev >= ARM * g) & (do <= pprev - GAP * g)
        ts_o = gap & (t[idx] >= tl)
        trig_o = (sl_o | tr_o | ts_o) & val
        sl_c = dc <= -SL * g
        tr_c = (pk >= ARM * g) & (dc <= pk - GAP * g)
        last = idx == en[:, None]
        trig_c = (sl_c | tr_c | last) & val
        trig = trig_o | trig_c
        k = np.argmax(trig, axis=1)
        r = np.arange(len(ee))
        op = trig_o[r, k]
        reason = np.where(op, np.where(sl_o[r, k], 0, np.where(tr_o[r, k], 1, 2)),
                          np.where(sl_c[r, k], 0, np.where(tr_c[r, k], 1, np.where(Lb[sl] <= n - 1, 2, 3))))
        xb = idx[r, k]
        px = np.where(op, o[xb], c[xb])
        gross = ss * (px / c[ee] - 1.0)
        rte = load_g4.rt_cost(d["pair"], c[ee])
        rtx = load_g4.rt_cost(d["pair"], px)
        mx = np.where(d["roll"][xb] | d["after60"][xb], 3.0, 1.0)
        slip = np.where(reason != 1, 0.5 * rtx, 0.0)
        cost = cost_mult * (rte / 2 + rtx / 2 * mx + slip)
        rt = d["roll_tab"]
        t_in = t[ee] + 1
        t_out = np.where(op, t[xb], t[xb] + 1)
        lo = np.searchsorted(rt["t"], t_in, side="right")
        hi = np.searchsorted(rt["t"], t_out, side="right")
        swap = ss * (rt["cdiff"][hi] - rt["cdiff"][lo]) - cost_mult * (rt["cw"][hi] - rt["cw"][lo]) * MARGIN / 360.0
        out["gross"][sl], out["cost"][sl], out["swap"][sl] = gross, cost, swap
        out["net"][sl] = gross - cost + swap
        xi[sl], rs[sl], at_open[sl] = xb, reason, op
        if want_path:
            for q in range(len(ee)):
                kk = k[q]
                tt = t[idx[q, :kk]] + 1
                vv = dc[q, :kk] - cost_mult * rte[q] / 2
                paths.append((np.concatenate([[t[ee[q]] + 1], tt, [t_out[q]]]),
                              np.concatenate([[-cost_mult * rte[q] / 2], vv, [out["net"][sl][q]]])))
    res = dict(entry=e, exit=xi, reason=REASONS[rs], at_open=at_open, side=side, sg=sg, **out)
    if want_path:
        res["paths"] = paths
    return res


def run_config(data, cfg, cost_mult=1.0, want_path=False, start=None, end=None):
    """Sequential one-position-per-pair simulation of one config over all pairs. Returns per-pair trade dicts."""
    _guard(data)
    out = {}
    for p, d in data["pairs"].items():
        ev = sig_g4.events(d, cfg["side"], cfg["N"], cfg["T"])
        if start is not None:
            ev = ev[d["t"][ev] >= sig_g4.tmin(start)]
        if end is not None:
            ev = ev[d["t"][ev] < sig_g4.tmin(end) + 1440]
        sg60 = d["_sig1"] * np.sqrt(60)
        taken = []
        pos = 0
        x = -1
        while True:
            pos = np.searchsorted(ev, x, side="right") if x >= 0 else pos
            if pos >= len(ev):
                break
            i = ev[pos]
            r = trades_batch(d, [i + 1], sig_g4.SIDES[cfg["side"]], [sg60[i]], cfg["TS"], cost_mult)
            taken.append(i)
            x = int(r["exit"][0])
            if x <= i:
                x = i + 1
        taken = np.array(taken, dtype=np.int64)
        r = trades_batch(d, taken + 1, sig_g4.SIDES[cfg["side"]], sg60[taken], cfg["TS"], cost_mult, want_path)
        r["event"] = taken
        r["t_entry"] = d["t"][taken + 1] if len(taken) else np.array([], np.int64)
        out[p] = r
    return out
