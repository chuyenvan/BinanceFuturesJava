"""TREND_T1 INDEPENDENT checks (does NOT import t1_core / pipeline). Reads raw 1m parquet + raw funding parquet directly.
V3: single-coin re-implementation of V1 (SMA100) and V3 (Donchian 20/10) for BTC/ETH/SOL; compare daily equity with pipeline output.
V4: funding sign/amount by hand for 3 trades of V1.
V5: entry/exit price of 10 random trades == close of the 1m bar opened 00:01 UTC.
"""
import os, glob, json, math
import numpy as np, pandas as pd, pyarrow.parquet as pq

WK = os.path.expanduser("~/claude_master/trend_t1_wk")
RUN = WK + "/run"; VAL = WK + "/valid"
MS_DAY = 86400000; MS_H = 3600000; MS_M = 60000
D_START = int(pd.Timestamp("2021-12-01").value // 10**6)
S_START = int(pd.Timestamp("2022-05-01").value // 10**6)
S_END = int(pd.Timestamp("2025-12-31").value // 10**6)

rng = np.random.default_rng(7)
# pick V5 trades + V4 trades first (pipeline outputs are just data here)
picks = []
for v in ["V1", "V2", "V3", "V4", "V5", "V6"]:
    T = pd.read_csv("%s/trades_%s.csv" % (RUN, v)); T["v"] = v; picks.append(T)
ALL = pd.concat(picks, ignore_index=True)
cand = ALL[(~ALL.forced) & ALL.dout.notna()].reset_index(drop=True)
v5 = cand.iloc[rng.choice(len(cand), 10, replace=False)].copy()
T1 = pd.read_csv(RUN + "/trades_V1.csv"); T1 = T1[(~T1.forced) & T1.dout.notna()]
T1 = T1.assign(hold=(T1.dout - T1.din) / MS_DAY)
v4 = pd.concat([T1.sort_values("fund").tail(1), T1.sort_values("fund").head(1), T1[T1.hold >= 5].sample(1, random_state=3)])
need = set(["BTCUSDT", "ETHUSDT", "SOLUSDT"]) | set(v5.sym) | set(v4.sym)

# ---- read raw 1m (filtered by symbol)
raw = {s: [] for s in need}
for f in sorted(glob.glob("/home/ubuntu/vz_e1/raw/kline1m-*.parquet")):
    t = pq.read_table(f, columns=["ts", "sym", "close", "active"], filters=[("sym", "in", sorted(need))]).to_pandas()
    t["sym"] = t["sym"].astype(str)
    assert t.ts.dtype == np.int64
    for s, g in t.groupby("sym"):
        raw[s].append(g[["ts", "close", "active"]])
raw = {s: pd.concat(v, ignore_index=True).sort_values("ts").reset_index(drop=True) for s, v in raw.items() if v}
fund = {}
for f in sorted(glob.glob("/home/ubuntu/vz/out/funding/202[2-5]/*.parquet")):
    t = pd.read_parquet(f, columns=["ts", "sym", "rate"]); t["sym"] = t["sym"].astype(str)
    t = t[t.sym.isin(need)]
    for s, g in t.groupby("sym"):
        fund.setdefault(s, []).append(g[["ts", "rate"]])
fund = {s: pd.concat(v).sort_values("ts").reset_index(drop=True) for s, v in fund.items()}

def price_at(s, T):
    """price at time T = close of 1m bar opened at T-60s (asof fallback to last bar before)."""
    r = raw[s]; i = np.searchsorted(r.ts.values, T - MS_M, side="right") - 1
    return float(r.close.values[i])

def fund_sum(s, q, t_in, t_out):
    """long pays q*p(T)*rate for t_in < T < t_out; T = ts floored to hour."""
    f = fund[s]; T = f.ts.values - f.ts.values % MS_H
    m = (T > t_in) & (T < t_out)
    tot = 0.0; ev = []
    for TT, rt in zip(T[m], f.rate.values[m]):
        p = price_at(s, int(TT)); tot += q * p * rt; ev.append((int(TT), float(rt), p, q * p * rt))
    return tot, ev

out = {}
# ---- V5 price check
chk = []
for _, t in v5.iterrows():
    r = raw[t.sym].set_index("ts").close
    pin = float(r.get(int(t.din) + MS_M, np.nan)); pout = float(r.get(int(t.dout) + MS_M, np.nan))
    chk.append(dict(v=t.v, sym=t.sym, t_in=str(pd.to_datetime(int(t.din) + MS_M, unit="ms")), px_in_pipe=t.px_in, px_in_raw=pin,
                    t_out=str(pd.to_datetime(int(t.dout) + MS_M, unit="ms")), px_out_pipe=t.px_out, px_out_raw=pout,
                    ok=bool(abs(pin - t.px_in) < 1e-12 and abs(pout - t.px_out) < 1e-12)))
out["V5"] = dict(trades=chk, pass_=all(c["ok"] for c in chk))
print("V5", out["V5"]["pass_"], [(c["sym"], c["t_in"], c["px_in_pipe"], c["px_in_raw"], c["px_out_pipe"], c["px_out_raw"]) for c in chk], flush=True)
# ---- V4 funding
fz = []
for _, t in v4.iterrows():
    tot, ev = fund_sum(t.sym, t.q, int(t.din) + MS_M, int(t.dout) + MS_M)
    npos = sum(1 for e in ev if e[1] > 0); nneg = sum(1 for e in ev if e[1] < 0)
    fz.append(dict(sym=t.sym, din=str(pd.to_datetime(int(t.din), unit="ms").date()), dout=str(pd.to_datetime(int(t.dout), unit="ms").date()), q=t.q,
                   fund_pipe=t.fund, fund_indep=tot, n_events=len(ev), n_rate_pos=npos, n_rate_neg=nneg,
                   sample=[dict(T=str(pd.to_datetime(e[0], unit="ms")), rate=e[1], price=e[2], paid_by_long=e[3]) for e in ev[:2] + ev[-1:]],
                   sign_ok=all((e[1] > 0) == (e[3] > 0) for e in ev if e[1] != 0), rel_diff=abs(tot - t.fund) / max(abs(tot), 1e-12)))
out["V4"] = dict(trades=fz, pass_=all(x["sign_ok"] and x["rel_diff"] < 1e-9 for x in fz))
print("V4", out["V4"]["pass_"], [(x["sym"], x["din"], x["dout"], x["fund_pipe"], x["fund_indep"], x["n_rate_pos"], x["n_rate_neg"]) for x in fz], flush=True)

# ---- V3 single-coin re-implementation
def daily(s):
    r = raw[s]
    day = r.ts.values // MS_DAY * MS_DAY
    days = np.arange(D_START, S_END + MS_DAY, MS_DAY)
    close = {}; px01 = {}; act = {}
    df = pd.DataFrame(dict(day=day, ts=r.ts.values, c=r.close.values, a=r.active.values))
    for dd, g in df.groupby("day"):
        close[dd] = g.c.values[-1]
        g1 = g[(g.ts - dd) >= MS_M]
        px01[dd] = g1.c.values[0] if len(g1) else np.nan
        act[dd] = int(g.a.sum())
    C = []; last = np.nan
    for dd in days:
        if dd in close: last = close[dd]
        C.append(last)
    return days, np.array(C), np.array([px01.get(dd, np.nan) for dd in days]), np.array([act.get(dd, 0) for dd in days]), np.array([dd in close for dd in days])

def run_single(s, kind):
    days, C, PX, ACT, HAS = daily(s)
    n = len(days)
    def sma(i, w):
        if i - w + 1 < 0: return np.nan
        x = C[i - w + 1:i + 1]; return np.nan if np.isnan(x).any() else float(sum(x) / w)
    def mx(i, w):
        if i - w < 0: return np.nan
        x = C[i - w:i]; return np.nan if np.isnan(x).any() else float(max(x))
    def mn(i, w):
        if i - w < 0: return np.nan
        x = C[i - w:i]; return np.nan if np.isnan(x).any() else float(min(x))
    def sig(i):
        if i - 20 < 0: return np.nan
        lr = [math.log(C[k] / C[k - 1]) for k in range(i - 19, i + 1)]
        return float(np.std(lr, ddof=1))
    f = fund[s]; FT = f.ts.values - f.ts.values % MS_H; FR = f.rate.values
    def fsum(q, a, b):  # T in (a, b)
        m = (FT > a) & (FT < b); return sum(q * price_at(s, int(TT)) * rt for TT, rt in zip(FT[m], FR[m]))
    i_s = (S_START - D_START) // MS_DAY; i_e = (S_END - D_START) // MS_DAY
    E = 1.0; pos = None; eq = []
    pending = None  # ('in', w) or ('out',) decided at signal day i-1
    # decide at signal day i_s-1
    for D in range(i_s, i_e + 1):
        sd = D - 1
        # decision at close of sd (done here at start of D for D's execution)
        act = None
        if pos is not None:
            if pos["din"] <= sd and (not HAS[sd] or ACT[sd] == 0):
                act = "forced"  # not expected for BTC/ETH/SOL
            else:
                c = C[sd]
                ex = (c < sma(sd, 100)) if kind == "V1" else (c < mn(sd, 10))
                if ex: act = "out"
        else:
            c = C[sd]
            en = (c > sma(sd, 100)) if kind == "V1" else (c > mx(sd, 20))
            sg = sig(sd)
            if en and HAS[sd] and ACT[sd] > 0 and not np.isnan(sg) and not np.isnan(PX[D]):
                act = ("in", 0.1 * min(1.0, 0.04 / sg))
        assert act != "forced"
        pnl = 0.0; t0 = days[D]
        if act == "out":
            q = pos["q"]; p = PX[D]
            pnl += q * (p - C[D - 1]) - 0.001 * q * p - fsum(q, t0 - 1, t0 + 1)  # only T == 00:00 of D
            pos = None
        elif pos is not None:
            q = pos["q"]; pnl += q * (C[D] - C[D - 1]) - fsum(q, t0 - 1, t0 + MS_DAY)  # T in [00:00, 24:00)
        if isinstance(act, tuple):
            w = act[1]; p = PX[D]; q = w * E / p
            pnl += q * (C[D] - p) - 0.001 * w * E - fsum(q, t0 + MS_M, t0 + MS_DAY)
            pos = dict(q=q, din=D)
        E = E + pnl; eq.append((int(days[D]), E))
    return pd.DataFrame(eq, columns=["day", "E"])

v3 = {}
for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
    for kind in ["V1", "V3"]:
        a = run_single(s, kind)
        b = pd.read_parquet("%s/single_%s_%s.parquet" % (VAL, kind, s))
        m = a.merge(b[["day", "E"]], on="day", suffixes=("_ind", "_pipe"))
        dmax = float((m.E_ind - m.E_pipe).abs().max())
        v3["%s_%s" % (kind, s)] = dict(n=len(m), n_pipe=len(b), E_end_ind=float(a.E.iloc[-1]), E_end_pipe=float(b.E.iloc[-1]), max_abs_diff=dmax, ok=bool(dmax < 1e-6 and len(m) == len(b)))
        print("V3", kind, s, v3["%s_%s" % (kind, s)], flush=True)
out["V3"] = dict(cases=v3, pass_=all(x["ok"] for x in v3.values()))
json.dump(out, open(VAL + "/valid_indep.json", "w"), indent=1, default=str)
print("PASS V3", out["V3"]["pass_"], "V4", out["V4"]["pass_"], "V5", out["V5"]["pass_"])
