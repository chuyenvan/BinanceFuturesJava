"""FX G2 simulator (PREREG_FX_G2 sec 3-4): TSMOM {L1, L3, L12, C} x value filter {F0, V10, V20}; inverse-vol sizing
(63-day), gross 1; signal on the last business day T of month m, execution at the FRED price of the NEXT business day;
swap from OECD rates of month m-1, margin 1 %/yr; costs EURUSD 0.8 pip, others max(3 pip, 3 bp) (G1 audited engine).
PnL on real data is locked: real_token must be I_HAVE_A1_PASS.
"""
import argparse
import logging
import os

import numpy as np
import pandas as pd

import load_g2 as L2
import sim_g1 as S1   # audited G1 execution engine (run_sim), cost model, check_real

LOG = logging.getLogger("g2.sim")
REAL_TOKEN = S1.REAL_TOKEN
SIGNALS = ["L1", "L3", "L12", "C"]
FILTERS = [None, 0.10, 0.20]
VOL_N = 63
REER_N = 60
SIG_START = pd.Period("1974-12", "M")   # first signal end-1974-12 -> first execution 1975-01


def fname(x):
    return "F0" if x is None else "V%d" % round(x * 100)


def configs():
    return [dict(name="%s-%s" % (s, fname(f)), sig=s, X=f) for s in SIGNALS for f in FILTERS]


# ---------------------------------------------------------------- pure helpers (hand-testable)
def inv_vol_weights(s, vol):
    """w_i = s_i / vol_i normalised to sum |w| = 1; all-zero -> zeros."""
    s = np.asarray(s, dtype=float)
    vol = np.asarray(vol, dtype=float)
    raw = np.where(s != 0, s / vol, 0.0)
    g = np.abs(raw).sum()
    return raw / g if g > 0 else raw


def value_filter(s, reer_now, reer_mean, X):
    """No LONG if REER(m-1) > (1+X) mean; no SHORT if REER(m-1) < (1-X) mean. NaN REER/mean -> no filter."""
    if X is None or np.isnan(reer_now) or np.isnan(reer_mean):
        return s, False
    if s > 0 and reer_now > (1 + X) * reer_mean:
        return 0, True
    if s < 0 and reer_now < (1 - X) * reer_mean:
        return 0, True
    return s, False


def vol63(data):
    """Per ccy: std (ddof=1) of its last 63 valid daily log returns up to and including row t, x sqrt(252)."""
    if "vol63" in data._cache:
        return data._cache["vol63"]
    n, c = data.P.shape
    vol = np.full((n, c), np.nan)
    for j in range(c):
        s = pd.Series(data.P[:, j], index=np.arange(n)).dropna()
        rv = np.log(s).diff().rolling(VOL_N, min_periods=VOL_N).std() * np.sqrt(252.0)
        vol[:, j] = rv.reindex(np.arange(n)).ffill().to_numpy()
    data._cache["vol63"] = vol
    return vol


# ---------------------------------------------------------------- signal layer (no PnL)
def signal_table(data, start=SIG_START):
    """One record per signal month m >= start: T, exec row, universe, raw signs per L / C, vols, REER(m-1), REER mean
    (m-60..m-1), rates m-1. Uses only prices at rows <= T, REER months <= m-1, rates month m-1."""
    key = ("sigtab", str(start))
    if key in data._cache:
        return data._cache[key]
    months = L2.universe_g2(data)
    Tm = {mi.m: mi.T for mi in months}
    vol = vol63(data)
    reer = getattr(data, "reer", None)
    n = len(data.dates)
    recs = []
    for mi in months:
        if mi.m < start or mi.T is None or mi.T + 1 > n - 1:
            continue
        T = mi.T
        assert mi.rate_month == mi.m - 1 and data.month[T] == mi.m
        rec = dict(m=mi.m, T=T, x=T + 1, univ=list(mi.univ), r=dict(mi.r), r_usd=mi.r_usd, s={}, vol={}, reer={},
                   reer_mean={})
        for c in mi.univ:
            j = data.ccys.index(c)
            v = vol[T, j]
            sl = {}
            for L in (1, 3, 12):
                T0 = Tm.get(mi.m - L)
                p0 = data.Pf[T0, j] if T0 is not None else np.nan
                assert T0 is None or T0 < T
                sl[L] = float(np.sign(np.log(data.Pf[T, j] / p0))) if not np.isnan(p0) else np.nan
            if any(np.isnan(x) for x in sl.values()):
                sc = np.nan
            else:
                sc = float(np.sign(np.mean([sl[1], sl[3], sl[12]])))
            rec["s"][c] = {"L1": sl[1], "L3": sl[3], "L12": sl[12], "C": sc}
            rec["vol"][c] = float(v)
            if reer is not None and c in reer.columns:
                ser = reer[c]
                win = ser.reindex(pd.period_range(mi.m - REER_N, mi.m - 1, freq="M"))
                rec["reer"][c] = float(ser.get(mi.m - 1, np.nan))
                rec["reer_mean"][c] = float(win.mean()) if win.notna().all() else np.nan
            else:
                rec["reer"][c] = np.nan
                rec["reer_mean"][c] = np.nan
        recs.append(rec)
    data._cache[key] = recs
    return recs


def config_signs(data, cfg, recs=None):
    """Matrix (months x ccys) of filtered signs (0 = no position / out of universe), vol matrix, universe mask,
    and filter counts (raw nonzero, filtered)."""
    recs = signal_table(data) if recs is None else recs
    nm, nc = len(recs), len(data.ccys)
    S = np.zeros((nm, nc))
    V = np.full((nm, nc), np.nan)
    U = np.zeros((nm, nc), dtype=bool)
    nraw = np.zeros(nm, dtype=int)
    nfilt = np.zeros(nm, dtype=int)
    if cfg["X"] is not None and getattr(data, "reer", None) is None:
        raise RuntimeError("value filter requested but REER not loaded")
    for i, rec in enumerate(recs):
        for c in rec["univ"]:
            j = data.ccys.index(c)
            v = rec["vol"][c]
            s = rec["s"][c][cfg["sig"]]
            if np.isnan(v) or np.isnan(s) or v <= 0:
                continue
            U[i, j] = True
            V[i, j] = v
            if s != 0:
                nraw[i] += 1
            s2, f = value_filter(s, rec["reer"][c], rec["reer_mean"][c], cfg["X"])
            nfilt[i] += int(f)
            S[i, j] = s2
    return S, V, U, nraw, nfilt


def events_from(data, recs, S, V, U, equal_weight=False):
    ev = []
    for i, rec in enumerate(recs):
        if equal_weight:
            nu = U[i].sum()
            w = np.where(U[i], 1.0 / nu, 0.0) if nu else np.zeros(len(data.ccys))
        else:
            w = inv_vol_weights(np.where(U[i], S[i], 0.0), np.where(U[i], V[i], 1.0))
        tgt = {c: float(w[j]) for j, c in enumerate(data.ccys)}
        info = dict(month=str(rec["m"]), signal_date=data.dates[rec["T"]].date().isoformat(), univ=",".join(rec["univ"]),
                    n_univ=int(U[i].sum()), n_pos=int(np.sum(w != 0)), note="")
        ev.append(dict(kind="rebal", row=rec["x"], targets=tgt, gate=False, rates=rec["r"], r_usd=rec["r_usd"], info=info))
    return ev


def simulate(data, cfg, cost_mult=1.0, real_token=None, start=SIG_START, S_override=None, equal_weight=False,
             end=None):
    S1.check_real(data, real_token)
    recs = signal_table(data)
    S, V, U, nraw, nfilt = config_signs(data, cfg, recs)
    keep = [i for i, r in enumerate(recs) if r["m"] >= start]
    recs_k = [recs[i] for i in keep]
    S, V, U = S[keep], V[keep], U[keep]
    if S_override is not None:
        S = S_override
    end_row = len(data.dates) - 1 if end is None else int(np.searchsorted(data.dates.values, np.datetime64(end), "right") - 1)
    recs_k2 = [(i, r) for i, r in enumerate(recs_k) if r["x"] <= end_row - 1]
    idx = [i for i, _ in recs_k2]
    ev = events_from(data, [r for _, r in recs_k2], S[idx], V[idx], U[idx], equal_weight=equal_weight)
    res = S1.run_sim(data, ev, end_row, cost_mult=cost_mult)
    res["filter"] = dict(months=[str(r["m"]) for r in recs_k], nraw=nraw[keep], nfilt=nfilt[keep])
    return res


def daily_frame(data, res):
    return pd.DataFrame(dict(date=data.dates.date, ret=res["ret"], equity=res["equity"], gross=res["gross"])).dropna(
        subset=["ret"])


def main():
    ap = argparse.ArgumentParser(description="G2 sim: 12 configs, daily returns + ledgers")
    ap.add_argument("--real", default=None, help="must be %s (after A1 audit)" % REAL_TOKEN)
    ap.add_argument("--data", default=L2.DEFAULT_DATA)
    ap.add_argument("--reer", default=None)
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g2/out"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if a.real != REAL_TOKEN:
        LOG.error("real-data run locked: pass --real %s only after A1 audit PASS", REAL_TOKEN)
        raise SystemExit(2)
    data = L2.load(a.data, reer_path=a.reer)
    os.makedirs(a.out, exist_ok=True)
    for cfg in configs():
        if cfg["X"] is not None and data.reer is None:
            continue
        res = simulate(data, cfg, real_token=a.real)
        daily_frame(data, res).to_csv(os.path.join(a.out, "daily_%s.csv" % cfg["name"]), index=False)
        res["events"].to_csv(os.path.join(a.out, "ledger_events_%s.csv" % cfg["name"]), index=False)
        res["trades"].to_csv(os.path.join(a.out, "ledger_trades_%s.csv" % cfg["name"]), index=False)
        LOG.info("wrote %s", cfg["name"])


if __name__ == "__main__":
    main()
