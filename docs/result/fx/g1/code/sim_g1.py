"""FX G1 simulator (PREREG_FX_G1 sec 5-6). Signal layer (build_schedule) is PnL-free; execution engine (run_sim)
holds constant foreign-currency units between trades (monthly rebalance, no hidden daily rebalancing).

Real-data run is locked: requires --real I_HAVE_A1_PASS.
"""
import argparse
import logging
import os

import numpy as np
import pandas as pd

import load_g1 as L

LOG = logging.getLogger("g1.sim")
REAL_TOKEN = "I_HAVE_A1_PASS"
MARGIN = 1.0          # broker margin, % per year, on EVERY leg (sec 6)
RT_BP_MIN = 3.0       # ERRATA2 J1: round trip (non-EURUSD) = max(3 pip, 3 bp of traded value)
GATES = [None, ("FXVOL", 0.80, 3), ("FXVOL", 0.90, 3), ("FXVOL", 0.80, 10), ("FXVOL", 0.90, 10), ("VIX", 0.90, 3)]
KS = [2, 3]
SIM_START = pd.Period("1993-12", "M")   # first rebalance end-1993-12 -> first PnL 1994-01


def gate_name(g):
    return "OFF" if g is None else "%s_q%d_N%d" % (g[0], round(g[1] * 100), g[2])


def configs():
    return [dict(name="k%d_%s" % (k, gate_name(g)), k=k, gate=g) for k in KS for g in GATES]


# ---------------------------------------------------------------- gate inputs (causal)
def fx_vol(data):
    """ERRATA2 J2: v_t = equal mean of 21-obs realized vol (std of daily log returns x sqrt(252)) over EVERY ccy with a
    valid FRED price on row t (EUR from 1999), independent of interest-rate availability. Each ccy vol uses its own last
    21 valid returns <= t. Rows with no valid price (US holidays) carry the previous v."""
    if "fxvol" in data._cache:
        return data._cache["fxvol"]
    n, c = data.P.shape
    vol = np.full((n, c), np.nan)
    for j in range(c):
        s = pd.Series(data.P[:, j], index=np.arange(n)).dropna()
        lr = np.log(s).diff()
        rv = lr.rolling(21, min_periods=21).std() * np.sqrt(252.0)
        vol[:, j] = rv.reindex(np.arange(n)).ffill().to_numpy()
    v = np.full(n, np.nan)
    for t in range(n):
        if not data.valid[t].any():
            v[t] = v[t - 1] if t > 0 else np.nan
            continue
        vals = vol[t, data.valid[t] & ~np.isnan(vol[t])]
        if len(vals):
            v[t] = vals.mean()
    data._cache["fxvol"] = v
    return v


def vix_lag(data):
    """VIX close is 16:15 ET, after the FRED noon fix: at row t use the last valid VIX of rows < t."""
    return pd.Series(data.vix).ffill().shift(1).to_numpy()


def rolling_quantile(dates, v, q, nyears):
    """q_t = quantile q of v over rows with date in [t - N years, t) (t excluded). NaN (gate off) if the v history does
    not reach back N years before t."""
    n = len(v)
    out = np.full(n, np.nan)
    ok = ~np.isnan(v)
    if not ok.any():
        return out
    first = dates[np.flatnonzero(ok)[0]]
    starts = dates - pd.DateOffset(years=nyears)
    lo = np.searchsorted(dates.values, starts.values, side="left")
    for t in range(n):
        if first > starts[t]:
            continue
        w = v[lo[t]:t]
        w = w[~np.isnan(w)]
        if len(w):
            out[t] = np.quantile(w, q)
    return out


def gate_arrays(data, gate):
    """Return (v, q, trig, active). trig[t] = gate active and v_t > q_t."""
    key = ("gate", gate)
    if key in data._cache:
        return data._cache[key]
    vtype, q, N = gate
    v = fx_vol(data) if vtype == "FXVOL" else vix_lag(data)
    qq = rolling_quantile(data.dates, v, q, N)
    active = ~np.isnan(qq)
    with np.errstate(invalid="ignore"):
        trig = active & ~np.isnan(v) & (v > qq)
    data._cache[key] = (v, qq, trig, active)
    return data._cache[key]


# ---------------------------------------------------------------- signal layer (no PnL)
def rank_carry(univ, r, r_usd, k):
    d = {c: r[c] - r_usd for c in univ}
    order = sorted(univ, key=lambda c: (-d[c], c))     # tie-break: ccy code
    return order[:k], order[-k:], d


def build_schedule(data, k, gate, mode="carry", rng=None, start=SIM_START, end=None):
    """List of events (dict): kind 'rebal' or 'gate_close', row, targets {ccy: weight}, gate flag, info.
    Uses for month m only rates of month m-1 and data rows <= T(m)."""
    end_row = len(data.dates) - 1 if end is None else int(np.searchsorted(data.dates.values, np.datetime64(end), "right") - 1)
    trig = gate_arrays(data, gate)[2] if gate is not None else None
    months = [mi for mi in data.months() if mi.m >= start and mi.T is not None and mi.T < end_row]
    ev = []
    for i, mi in enumerate(months):
        assert mi.rate_month == mi.m - 1 and data.month[mi.T] == mi.m
        T = mi.T
        nxt = months[i + 1].T if i + 1 < len(months) else end_row + 1
        tgt = {c: 0.0 for c in data.ccys}
        info = dict(month=str(mi.m), univ=",".join(mi.univ), n_univ=len(mi.univ), longs="", shorts="", d="", note="")
        if mode == "buyhold":
            need = 1
        else:
            need = 2 * k
        traded = False
        if len(mi.univ) < need:
            info["note"] = "n_univ<%d no trade" % need
        else:
            if mode == "carry":
                lo, sh, d = rank_carry(mi.univ, mi.r, mi.r_usd, k)
                info["d"] = ";".join("%s:%.4f" % (c, d[c]) for c in mi.univ)
            elif mode == "random":
                pick = rng.choice(len(mi.univ), size=2 * k, replace=False)
                lo = [mi.univ[x] for x in pick[:k]]
                sh = [mi.univ[x] for x in pick[k:]]
            elif mode == "buyhold":
                lo, sh = list(mi.univ), []
            else:
                raise ValueError(mode)
            if mode == "buyhold":
                for c in lo:
                    tgt[c] = 1.0 / len(lo)
            else:
                for c in lo:
                    tgt[c] = 1.0 / (2 * k)
                for c in sh:
                    tgt[c] = -1.0 / (2 * k)
            info["longs"], info["shorts"] = ",".join(lo), ",".join(sh)
            traded = True
        gflag = False
        if traded and trig is not None and trig[T]:
            tgt = {c: 0.0 for c in data.ccys}
            gflag = True
            info["note"] = "gate closed at rebalance"
            traded = False
        rates = dict(mi.r)
        ev.append(dict(kind="rebal", row=T, targets=tgt, gate=gflag, rates=rates, r_usd=mi.r_usd, info=info))
        if traded and trig is not None:
            hits = np.flatnonzero(trig[T + 1:min(nxt, end_row + 1)])
            if len(hits):
                g = T + 1 + int(hits[0])
                ev.append(dict(kind="gate_close", row=g, targets={c: 0.0 for c in data.ccys}, gate=True, rates=None,
                               r_usd=None, info=dict(month=str(mi.m), note="gate close")))
    return ev, end_row


# ---------------------------------------------------------------- execution engine
def _next_valid(valid):
    n, c = valid.shape
    nv = np.full((n + 1, c), n, dtype=np.int64)
    for t in range(n - 1, -1, -1):
        nv[t] = np.where(valid[t], t, nv[t + 1])
    return nv


def oneway_cost_frac(data, j, row):
    """Half of the round-trip spread+commission as a fraction of notional. EUR: 0.8 pip; others (ERRATA2 J1):
    max(3 pip / market quote, 3 bp)."""
    c = data.ccys[j]
    rt = data.rt_pips[c] * data.pip[c] / data.raw[row, j]
    if c != "EUR":
        rt = max(rt, RT_BP_MIN * 1e-4)
    return 0.5 * rt


def check_real(data, real_token):
    """ERRATA3 NHO-7: PnL on data loaded from files needs the A1 token (not only at the CLI)."""
    if getattr(data, "is_real", False) and real_token != REAL_TOKEN:
        raise PermissionError("PnL on real data locked: real_token=%s required" % REAL_TOKEN)


def _holding_diff(data):
    """ERRATA3 K5 (descriptive): r_ccy - r_USD of the calendar month of each row (NaN if missing)."""
    if "hold_diff" not in data._cache:
        rm = data.rates.reindex(data.month)
        usd = rm["USD"].to_numpy(dtype=float)
        data._cache["hold_diff"] = np.column_stack(
            [(rm[c].to_numpy(dtype=float) - usd) if c in rm else np.full(len(usd), np.nan) for c in data.ccys])
    return data._cache["hold_diff"]


def run_sim(data, events, end_row, cost_mult=1.0, carry_rates="signal"):
    n, nc = data.P.shape
    hd = _holding_diff(data) if carry_rates == "holding" else None
    if "nextvalid" not in data._cache:
        data._cache["nextvalid"] = _next_valid(data.valid)
    nv = data._cache["nextvalid"]
    Pf = data.Pf
    cal = np.zeros(n)
    cal[1:] = (data.dates[1:] - data.dates[:-1]).days
    ret = np.full(n, np.nan)
    eqa = np.full(n, np.nan)
    gross = np.full(n, np.nan)
    state = np.array([""] * n, dtype=object)
    units = np.zeros(nc)
    diff = np.full(nc, np.nan)       # r_c - r_usd (% per yr) of the latest rebalance
    equity = 1.0
    pending = {}                      # j -> (target_w, gate_flag, exec_row, src)
    trades = []
    if not events:
        return dict(ret=ret, equity=eqa, gross=gross, state=state, trades=pd.DataFrame(), events=pd.DataFrame())
    start = events[0]["row"]
    eqa[start] = equity
    gross[start] = 0.0
    cur_state = "flat"
    last = start - 1  # rows <= last have been processed; start row processed at first event (no PnL yet)
    ei = 0
    first = True
    while True:
        nr_evt = events[ei]["row"] if ei < len(events) else n + 1
        nr_exe = min([p[2] for p in pending.values()], default=n + 1)
        nr = min(nr_evt, nr_exe)
        if nr > end_row:
            nr = end_row
            stop = True
        else:
            stop = False
        # ---- advance PnL rows (last, nr]
        if not first and nr > last:
            a, b = last, nr
            P0 = Pf[a:b]
            P1 = Pf[a + 1:b + 1]
            pp = np.nan_to_num((P1 - P0) * units).sum(axis=1)
            held = units != 0
            if held.any():
                if np.isnan(diff[held]).any():
                    raise RuntimeError("held ccy without carry rate")
                if hd is None:
                    leg = np.where(held, np.sign(units) * np.nan_to_num(diff) - MARGIN * cost_mult, 0.0)
                else:   # K5: holding-month rate, fallback to signal rate if missing
                    dh = hd[a + 1:b + 1]
                    dm = np.where(np.isnan(dh), np.nan_to_num(diff), dh)
                    leg = np.where(held, np.sign(units) * dm - MARGIN * cost_mult, 0.0)
                notional = np.abs(np.nan_to_num(P0 * units))
                cp = (notional * leg).sum(axis=1) * cal[a + 1:b + 1] / 360.0 / 100.0
            else:
                cp = np.zeros(b - a)
            pnl = pp + cp
            eq = equity + np.cumsum(pnl)
            eprev = np.concatenate([[equity], eq[:-1]])
            ret[a + 1:b + 1] = pnl / eprev
            eqa[a + 1:b + 1] = eq
            gross[a + 1:b + 1] = np.abs(np.nan_to_num(P1 * units)).sum(axis=1) / eq
            state[a + 1:b + 1] = cur_state
            equity = eq[-1]
            last = nr
        if first:
            last = nr
            first = False
        if stop:
            break
        # ---- events at nr
        while ei < len(events) and events[ei]["row"] == nr:
            e = events[ei]
            if e["kind"] == "rebal":
                for j, c in enumerate(data.ccys):
                    if c in e["rates"]:
                        diff[j] = e["rates"][c] - e["r_usd"]
            any_open = any(abs(units[j]) > 0 for j in range(nc)) or bool(pending)
            if e["kind"] == "gate_close" and not any_open:
                ei += 1
                continue
            for j, c in enumerate(data.ccys):
                w = e["targets"][c]
                if w == 0.0 and units[j] == 0.0 and j not in pending:
                    continue
                pending[j] = (w, e["gate"], int(nv[nr, j]), e["kind"])
            if e["kind"] == "gate_close" or e["gate"]:
                cur_state = "gate"
            elif all(v == 0.0 for v in e["targets"].values()):
                cur_state = "flat"
            else:
                cur_state = "open"
            ei += 1
        # ---- executions at nr
        cost = 0.0
        e_pre = equity
        for j in sorted(pending):
            w, gf, xr, src = pending[j]
            if xr != nr:
                continue
            nu = w * e_pre / Pf[nr, j]
            tn = abs(nu - units[j]) * Pf[nr, j]
            cst = tn * oneway_cost_frac(data, j, nr) * cost_mult * (2.0 if gf else 1.0)
            trades.append(dict(row=nr, date=data.dates[nr].date().isoformat(), ccy=data.ccys[j], src=src, gate=gf,
                               w=w, traded_frac=tn / e_pre, cost_frac=cst / e_pre))
            cost += cst
            units[j] = nu
            del pending[j]
        if cost:
            pnl_row = (eqa[nr] - (eqa[nr - 1] if nr > start else 1.0)) if nr > start else 0.0
            eprev = eqa[nr - 1] if nr > start else 1.0
            equity -= cost
            eqa[nr] = equity
            ret[nr] = (pnl_row - cost) / eprev if nr > start else -cost / 1.0
        gross[nr] = np.abs(np.nan_to_num(Pf[nr] * units)).sum() / equity   # end-of-row (post-trade) exposure
        if nr == start:
            state[nr] = cur_state
    evdf = pd.DataFrame([dict(row=e["row"], date=data.dates[e["row"]].date().isoformat(), kind=e["kind"],
                              gate=e["gate"], **e["info"]) for e in events])
    return dict(ret=ret, equity=eqa, gross=gross, state=state, trades=pd.DataFrame(trades), events=evdf)


def simulate(data, k, gate, mode="carry", rng=None, cost_mult=1.0, end=None, carry_rates="signal", real_token=None):
    check_real(data, real_token)
    ev, end_row = build_schedule(data, k, gate, mode=mode, rng=rng, end=end)
    return run_sim(data, ev, end_row, cost_mult=cost_mult, carry_rates=carry_rates)


def daily_frame(data, res):
    return pd.DataFrame(dict(date=data.dates.date, ret=res["ret"], equity=res["equity"], gross=res["gross"],
                             state=res["state"])).dropna(subset=["ret"])


def main():
    ap = argparse.ArgumentParser(description="G1 sim: 12 configs, daily returns + ledgers")
    ap.add_argument("--real", default=None, help="must be %s (after A1 audit)" % REAL_TOKEN)
    ap.add_argument("--data", default=L.DEFAULT_DATA)
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g1/out"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if a.real != REAL_TOKEN:
        LOG.error("real-data run locked: pass --real %s only after A1 audit PASS", REAL_TOKEN)
        raise SystemExit(2)
    data = L.load(a.data)
    os.makedirs(a.out, exist_ok=True)
    for cfg in configs():
        res = simulate(data, cfg["k"], cfg["gate"], real_token=a.real)
        daily_frame(data, res).to_csv(os.path.join(a.out, "daily_%s.csv" % cfg["name"]), index=False)
        res["events"].to_csv(os.path.join(a.out, "ledger_events_%s.csv" % cfg["name"]), index=False)
        res["trades"].to_csv(os.path.join(a.out, "ledger_trades_%s.csv" % cfg["name"]), index=False)
        LOG.info("wrote %s", cfg["name"])


if __name__ == "__main__":
    main()
