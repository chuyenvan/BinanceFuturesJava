"""TREND_T1 core: panel, indicators, PIT universe, funding, selection (V1-V6), accounting engine, control.
Theo docs/prereg/PREREG_TREND_T1.md (sha c9f29a4e...). Time: UTC, ts int64 ms.
"""
import os, glob
import numpy as np, pandas as pd

WK = os.path.expanduser("~/claude_master/trend_t1_wk")
DAY = 86400000
HOUR = 3600000
DAY0 = int(pd.Timestamp("2021-12-01").value // 10**6)
SIM_START = int(pd.Timestamp("2022-05-01").value // 10**6)
SIM_END = int(pd.Timestamp("2025-12-31").value // 10**6)
EXCL = {"USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT", "DAIUSDT", "USDEUSDT", "PAXGUSDT", "XAUUSDT", "XAGUSDT",
        "BTCDOMUSDT", "DEFIUSDT", "BLUEBIRDUSDT", "FOOTBALLUSDT"}
COST = 0.001  # 0.05% taker + 0.05% slippage per side
VARIANTS = ["V1", "V2", "V3", "V4", "V5", "V6"]


def load_daily():
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(WK + "/daily/*.parquet"))], ignore_index=True)
    assert d.day.dtype == np.int64 and d.ts_last.dtype == np.int64
    assert (d.n_rows <= 1440).all()
    assert not d.duplicated(["sym", "day"]).any()
    return d


def build_panel(d):
    syms = np.array(sorted(d.sym.unique()))
    si = {s: i for i, s in enumerate(syms)}
    ND = int((d.day.max() - DAY0) // DAY + 1)
    NS = len(syms)
    di = ((d.day.values - DAY0) // DAY).astype(np.int64)
    sj = d.sym.map(si).values.astype(np.int64)
    P = dict(syms=syms, si=si, ND=ND, NS=NS)
    for c, fill, dt in [("close", np.nan, float), ("px01", np.nan, float), ("qv", 0.0, float), ("n_active", 0, np.int64), ("px01_min", -1, np.int64)]:
        a = np.full((ND, NS), fill, dtype=dt)
        a[di, sj] = d[c].values
        P[c] = a
    has = np.zeros((ND, NS), bool); has[di, sj] = True
    P["has"] = has
    P["close_ff"] = pd.DataFrame(P["close"]).ffill().values
    P["days"] = DAY0 + np.arange(ND, dtype=np.int64) * DAY
    first = np.where(has.any(0), has.argmax(0), ND)
    P["first_idx"] = first
    return P


def indicators(P):
    c = pd.DataFrame(P["close_ff"])
    I = {}
    I["sma100"] = c.rolling(100, min_periods=100).mean().values
    I["sma50"] = c.rolling(50, min_periods=50).mean().values
    I["max20"] = c.rolling(20, min_periods=20).max().shift(1).values
    I["min10"] = c.rolling(10, min_periods=10).min().shift(1).values
    I["max55"] = c.rolling(55, min_periods=55).max().shift(1).values
    I["min20"] = c.rolling(20, min_periods=20).min().shift(1).values
    lr = np.log(c / c.shift(1))
    I["sig20"] = lr.rolling(20, min_periods=20).std(ddof=1).values
    I["mom"] = (c.shift(1) / c.shift(29) - 1).values
    return I


def universe(P, force=None):
    """inU[i, s]: s in U for execution day i (month of day i)."""
    ND, NS = P["ND"], P["NS"]
    inU = np.zeros((ND, NS), bool)
    if force is not None:
        for s in force:
            inU[:, P["si"][s]] = True
        return inU, {}
    days = pd.to_datetime(P["days"], unit="ms")
    excl = np.array([s in EXCL for s in P["syms"]])
    members = {}
    for m1 in pd.date_range("2022-05-01", "2025-12-01", freq="MS"):
        i1 = int((m1.value // 10**6 - DAY0) // DAY)
        cand = (P["first_idx"] <= i1 - 120) & P["has"][i1 - 1] & ~excl
        med = np.median(P["qv"][i1 - 30:i1], axis=0)
        idx = np.flatnonzero(cand)
        order = sorted(idx, key=lambda s: (-med[s], P["syms"][s]))[:30]
        i2 = int(((m1 + pd.offsets.MonthBegin(1)).value // 10**6 - DAY0) // DAY)
        inU[i1:min(i2, ND), order] = True
        members[m1.strftime("%Y-%m")] = [P["syms"][s] for s in order]
    return inU, members


def funding(P, usyms):
    """F0[i,s]: sum rate*p(T) for T == 00:00 of day i; Fr[i,s]: T in (00:00, 24:00). Per unit quantity. Long pays F."""
    ND, NS = P["ND"], P["NS"]
    F0 = np.zeros((ND, NS)); Fr = np.zeros((ND, NS))
    fs = []
    for y in range(2022, 2026):
        fs += sorted(glob.glob("/home/ubuntu/vz/out/funding/%d/%d-*.parquet" % (y, y)))
    f = pd.concat([pd.read_parquet(x, columns=["ts", "sym", "rate"]) for x in fs], ignore_index=True)
    f["sym"] = f["sym"].astype(str)
    f = f[f.sym.isin(usyms)]
    assert f.ts.dtype == np.int64
    rem = f.ts.values % HOUR
    assert (rem < 60000).all()
    f["T"] = f.ts.values - rem
    f = f[(f["T"] >= SIM_START - DAY) & (f["T"] <= SIM_END + DAY)].drop_duplicates(["sym", "T"])
    f["src"] = "vision"
    # default for sym-months with data but no funding rows
    rep = {"symmonth_u_total": 0, "symmonth_u_default": 0, "default_list": []}
    fm = set(zip(f.sym, pd.to_datetime(f["T"], unit="ms").dt.strftime("%Y-%m")))
    extra = []
    for s in usyms:
        j = P["si"][s]
        hidx = np.flatnonzero(P["has"][:, j])
        for mo, g in pd.Series(hidx).groupby(pd.to_datetime(P["days"][hidx], unit="ms").strftime("%Y-%m")):
            if mo < "2022-05" or mo > "2025-12":
                continue
            if (s, mo) not in fm:
                for i in g.values:
                    for h in (0, 8, 16):
                        extra.append((s, int(P["days"][i] + h * HOUR), 0.0001))
                rep["default_list"].append((s, mo))
    if extra:
        e = pd.DataFrame(extra, columns=["sym", "T", "rate"]); e["src"] = "default"
        f = pd.concat([f[["sym", "T", "rate", "src"]], e], ignore_index=True)
    # price at T
    hs = []
    for x in sorted(glob.glob(WK + "/hourly/*.parquet")):
        h = pd.read_parquet(x); h = h[h.sym.isin(usyms)]; hs.append(h)
    h = pd.concat(hs, ignore_index=True).rename(columns={"t": "T"})
    assert h["T"].dtype == np.int64
    f = f.merge(h, on=["sym", "T"], how="left")
    di = ((f["T"].values - DAY0) // DAY).astype(np.int64)
    sj = f.sym.map(P["si"]).values.astype(np.int64)
    is0 = (f["T"].values % DAY) == 0
    miss = f.p.isna().values
    fb = np.where(is0, P["close_ff"][np.maximum(di - 1, 0), sj], P["close_ff"][np.minimum(di, ND - 1), sj])
    p = np.where(miss, fb, f.p.values)
    ok = (di >= 0) & (di < ND)
    amt = f.rate.values * p
    np.add.at(F0, (di[ok & is0], sj[ok & is0]), amt[ok & is0])
    np.add.at(Fr, (di[ok & ~is0], sj[ok & ~is0]), amt[ok & ~is0])
    rep.update(events=int(len(f)), events_default=int((f.src == "default").sum()), price_fallback=int(miss.sum()))
    return F0, Fr, f, rep


def _strength_sig(v, P, I, d):
    c = P["close_ff"][d]
    if v in ("V1", "V6"):
        sma = I["sma100"][d]; ent = c > sma; ext = c < sma; st = c / sma - 1
    elif v == "V2":
        sma = I["sma50"][d]; ent = c > sma; ext = c < sma; st = c / sma - 1
    elif v == "V3":
        ent = c > I["max20"][d]; ext = c < I["min10"][d]; st = c / I["max20"][d] - 1
    elif v == "V4":
        ent = c > I["max55"][d]; ext = c < I["min20"][d]; st = c / I["max55"][d] - 1
    return ent, ext, st


def btc_on(P, I, d):
    j = P["si"]["BTCUSDT"]
    return bool(P["close_ff"][d, j] > I["sma100"][d, j])


def select(v, P, I, inU, single=False, log=None):
    """Return list of trades: dict(s, din, dout, forced). din/dout = day index of execution (00:01); forced => exit at close of dout."""
    ND = P["ND"]
    d_first = int((SIM_START - DAY0) // DAY) - 1
    d_last = int((SIM_END - DAY0) // DAY) - 1  # last signal day (exec 2025-12-31)
    held = {}
    trades = []
    nact, has = P["n_active"], P["has"]
    cap = 5 if v == "V5" else 10
    for d in range(d_first, d_last + 1):
        ex = d + 1
        # forced exits on day d (no trading on d) for positions entered at or before d
        for s in list(held):
            t = held[s]
            if t["din"] <= d and (not has[d, s] or nact[d, s] == 0):
                t["dout"] = d; t["forced"] = True; trades.append(t); del held[s]
        dec = {"d": d, "exit": [], "enter": []}
        if v == "V5":
            if pd.Timestamp(P["days"][d], unit="ms").dayofweek != 6:
                if log is not None: log.append(dec)
                continue
            target = []
            if btc_on(P, I, d):
                mom = I["mom"][d]
                el = inU[ex] & has[d] & (nact[d] > 0) & ~np.isnan(mom) & ~np.isnan(I["sig20"][d]) & ~np.isnan(P["px01"][ex])
                idx = np.flatnonzero(el)
                target = sorted(idx, key=lambda s: (-mom[s], P["syms"][s]))[:cap]
            for s in list(held):
                if s not in target:
                    t = held.pop(s); t["dout"] = ex; t["forced"] = False; trades.append(t); dec["exit"].append(int(s))
            for s in target:
                if s not in held:
                    held[s] = dict(s=int(s), din=ex, dout=None, forced=False, strength=float(I["mom"][d][s])); dec["enter"].append((int(s), round(float(I["mom"][d][s]), 12)))
            if log is not None: log.append(dec)
            continue
        ent, ext, st = _strength_sig(v, P, I, d)
        reg = btc_on(P, I, d) if v == "V6" else True
        for s in list(held):
            if ext[s] or (not inU[ex, s]) or (not reg):
                t = held.pop(s); t["dout"] = ex; t["forced"] = False; trades.append(t); dec["exit"].append(int(s))
        if reg:
            free = cap - len(held)
            if free > 0:
                el = inU[ex] & has[d] & (nact[d] > 0) & ent & ~np.isnan(st) & ~np.isnan(I["sig20"][d]) & ~np.isnan(P["px01"][ex])
                for s in held: el[s] = False
                idx = np.flatnonzero(el)
                pick = sorted(idx, key=lambda s: (-st[s], P["syms"][s]))[:free]
                for s in pick:
                    held[s] = dict(s=int(s), din=ex, dout=None, forced=False, strength=float(st[s])); dec["enter"].append((int(s), round(float(st[s]), 12)))
        if log is not None: log.append(dec)
    for s, t in held.items():
        trades.append(t)
    trades.sort(key=lambda t: (t["din"], t["s"]))
    return trades


def run_engine(trades, P, I, F0, Fr, v, cost=COST):
    """Daily accounting. Returns dict(ret, days, gross, npos, traded, E) and fills per-trade pnl/fund/px_in/px_out/q."""
    i0 = int((SIM_START - DAY0) // DAY); i1 = int((SIM_END - DAY0) // DAY)
    c = P["close_ff"]; px = P["px01"]
    base = 0.2 if v == "V5" else 0.1
    reb = set()
    if v == "V5":
        reb = {i for i in range(i0, i1 + 1) if pd.Timestamp(P["days"][i], unit="ms").dayofweek == 0}
    by_in = {}; by_out = {}
    for k, t in enumerate(trades):
        t.update(pnl=0.0, fund=0.0, cost=0.0, q=0.0, px_in=np.nan, px_out=np.nan, k=k)
        by_in.setdefault(t["din"], []).append(t)
        if t["dout"] is not None:
            by_out.setdefault(t["dout"], []).append(t)
    E = 1.0
    live = {}
    n = i1 - i0 + 1
    ret = np.zeros(n); gross = np.zeros(n); npos = np.zeros(n, int); traded = np.zeros(n); Eser = np.zeros(n)
    for D in range(i0, i1 + 1):
        Eref = E; pnl = 0.0; tr = 0.0
        outs = by_out.get(D, [])
        # normal exits at 00:01
        for t in outs:
            if t["forced"] or t["k"] not in live:
                continue
            q = t["q"]; p = px[D, t["s"]]
            if np.isnan(p):
                p = c[D - 1, t["s"]]; t["px_fallback"] = True
            g = q * (p - c[D - 1, t["s"]]); f = q * F0[D, t["s"]]; k = cost * q * p
            pnl += g - f - k; tr += q * p
            t["pnl"] += g - f - k; t["fund"] += f; t["cost"] += k; t["px_out"] = p
            del live[t["k"]]
        # continuing
        for kk, t in list(live.items()):
            s = t["s"]; q = t["q"]
            if D in reb and not np.isnan(px[D, s]):
                p = px[D, s]
                w = base * min(1.0, 0.04 / I["sig20"][D - 1, s]) if not np.isnan(I["sig20"][D - 1, s]) else t["w"]
                g1 = q * (p - c[D - 1, s]); f1 = q * F0[D, s]
                qn = w * Eref / p; k = cost * abs(qn - q) * p
                g2 = qn * (c[D, s] - p); f2 = qn * Fr[D, s]
                pnl += g1 + g2 - f1 - f2 - k; tr += abs(qn - q) * p
                t["pnl"] += g1 + g2 - f1 - f2 - k; t["fund"] += f1 + f2; t["cost"] += k; t["q"] = qn; t["w"] = w
            else:
                g = q * (c[D, s] - c[D - 1, s]); f = q * (F0[D, s] + Fr[D, s])
                pnl += g - f; t["pnl"] += g - f; t["fund"] += f
        # entries
        ins = by_in.get(D, [])
        if ins:
            exist = sum(t["q"] * px[D, t["s"]] if not np.isnan(px[D, t["s"]]) else t["q"] * c[D - 1, t["s"]] for t in live.values())
            Ns = []
            for t in ins:
                s = t["s"]; sg = I["sig20"][D - 1, s]
                w = base * min(1.0, 0.04 / sg)
                t["w"] = w; Ns.append(w * Eref)
            tot = sum(Ns)
            scale = 1.0
            if exist + tot > Eref:
                scale = max(0.0, (Eref - exist) / tot)
            for t, N in zip(ins, Ns):
                s = t["s"]; p = px[D, s]; N = N * scale
                q = N / p; k = cost * N
                g = q * (c[D, s] - p); f = q * Fr[D, s]
                pnl += g - f - k; tr += N
                t.update(q=q, px_in=p, scale=scale)
                t["pnl"] += g - f - k; t["fund"] += f; t["cost"] += k
                live[t["k"]] = t
        # forced exits at close of D
        for t in outs:
            if not t["forced"] or t["k"] not in live:
                continue
            q = t["q"]; p = c[D, t["s"]]; k = cost * q * p
            pnl -= k; tr += q * p; t["pnl"] -= k; t["cost"] += k; t["px_out"] = p
            del live[t["k"]]
        E = Eref + pnl
        j = D - i0
        ret[j] = pnl / Eref; Eser[j] = E; traded[j] = tr
        npos[j] = len(live); gross[j] = sum(t["q"] * c[D, t["s"]] for t in live.values()) / E
    return dict(ret=ret, days=P["days"][i0:i1 + 1], gross=gross, npos=npos, traded=traded, E=Eser)


def control_trades(trades, P, I, inU, rng):
    """Random-coin replacement keeping din/dout (exposure + holding time matched)."""
    nact, has = P["n_active"], P["has"]
    i_end = int((SIM_END - DAY0) // DAY)
    busy = {}  # s -> list of (a, b) occupied day ranges (inclusive)
    out = []
    for t in sorted(trades, key=lambda t: (t["din"], t["s"])):
        a = t["din"]; sd = a - 1
        b_nom = t["dout"] if t["dout"] is not None else i_end
        el = inU[a] & has[sd] & (nact[sd] > 0) & ~np.isnan(I["sig20"][sd]) & ~np.isnan(P["px01"][a])
        idx = [s for s in np.flatnonzero(el) if all(b_nom < x or a > y for x, y in busy.get(s, []))]
        if not idx:
            continue
        s = int(rng.choice(idx))
        dout, forced = t["dout"], t["forced"]
        last = (dout if dout is not None else i_end + 1)
        # random coin dies during hold => forced exit that day
        for D in range(a, min(last, i_end + 1)):
            if not has[D, s] or nact[D, s] == 0:
                dout, forced = D, True; break
        busy.setdefault(s, []).append((a, dout if dout is not None else i_end))
        out.append(dict(s=s, din=a, dout=dout, forced=forced, strength=np.nan))
    return out


def stats(ret, days, a, b):
    m = (days >= int(pd.Timestamp(a).value // 10**6)) & (days <= int(pd.Timestamp(b).value // 10**6))
    r = ret[m]
    eq = np.concatenate([[1.0], np.cumprod(1 + r)])
    sd = r.std(ddof=1)
    return dict(n=int(m.sum()), sharpe=float(r.mean() / sd * np.sqrt(365)) if sd > 0 else 0.0,
                maxdd=float((eq / np.maximum.accumulate(eq) - 1).min()), cagr=float(eq[-1] ** (365 / len(r)) - 1))
