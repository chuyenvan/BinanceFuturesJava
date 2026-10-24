"""FEE0_RESCORE common: data (int64 ms ts), funding, cost models C_M0/C_M1/C_M2, stats, DSR.
Prereg: docs/prereg/PREREG_FEE0_RESCORE.md."""
import glob, io, json, os, zipfile
import numpy as np, pandas as pd
from scipy.stats import norm

WK = os.path.expanduser("~/claude_master/fee0_wk")
SCR = os.path.expanduser("~/claude_master/1016/screen")
CARRY = os.path.expanduser("~/claude_master/1016/carry")
MIN = 60_000
DAY = 86_400_000
E0, E1, C0, C1 = "2021-01-01", "2023-12-31", "2024-01-01", "2026-09-30"
AS_BPS = 2.0          # adverse selection penalty per maker fill (MM_Q1 tier lon)
TAKER = 0.0004        # USDC-M taker
HS = json.load(open(WK + "/half_spread.json")) if os.path.exists(WK + "/half_spread.json") else {}
KCOLS = ["ot", "open", "high", "low", "close", "vol", "ct", "qv", "n", "tbv", "tbqv", "ig"]


def ms(ts):
    return int(pd.Timestamp(ts).value // 1_000_000)


def read_kzip(p):
    with zipfile.ZipFile(p) as z:
        b = z.read(z.namelist()[0])
    x = pd.read_csv(io.BytesIO(b), header=None, dtype=str)
    if not x.iloc[0, 0].strip().isdigit():
        x = x.iloc[1:]
    x.columns = KCOLS[: x.shape[1]]
    o = pd.DataFrame({"ts": x.ot.astype(np.int64).to_numpy()})
    for c in ("open", "high", "low", "close", "vol", "qv", "tbv", "tbqv"):
        o[c] = x[c].astype(np.float64).to_numpy()
    return o


def load_usdt_m1(a):
    M = pd.read_parquet(f"{SCR}/m1_{a}USDT.parquet")
    ts = M.index.values.astype("datetime64[ms]").astype(np.int64)
    o = pd.DataFrame({"ts": ts, "open": M.open.values, "high": M.high.values, "low": M.low.values,
                      "close": M.close.values, "vol": M.vol.values, "tbv": M.tbv.values})
    assert o.ts.dtype == np.int64 and o.ts.is_unique and (o.ts % MIN == 0).all()
    return o


def load_usdc_m1(sym, d=None):
    d = d or f"{WK}/k1m/{sym}"
    M = pd.concat([read_kzip(p) for p in sorted(glob.glob(d + "/*.zip"))], ignore_index=True)
    M = M.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    assert M.ts.dtype == np.int64 and (M.ts % MIN == 0).all()
    return M


def exec_frame(a):
    """1m grid: USDT-M before USDC-M first bar, USDC-M after. returns df ts, open, high, low, close, src."""
    T = load_usdt_m1(a)
    U = load_usdc_m1(a + "USDC")
    t_usdc = int(U.ts.iloc[0])
    X = pd.concat([T[T.ts < t_usdc][["ts", "high", "low", "close"]].assign(src=0),
                   U[["ts", "high", "low", "close"]].assign(src=1)], ignore_index=True)
    X = X.sort_values("ts").reset_index(drop=True)
    exp = (X.ts.iloc[-1] - X.ts.iloc[0]) // MIN + 1
    assert X.ts.is_unique and len(X) == exp, (len(X), exp)
    return X, T, t_usdc


def load_funding(sym_usdt, sym_usdc, t_usdc):
    """settlement ts (int64 ms) + rate; USDC-M rates from t_usdc on (if file), else USDT-M (proxy)."""
    f = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(CARRY + "/fund/funding-*.parquet"))])
    f = f[f.sym == sym_usdt][["ts", "rate"]].astype({"ts": np.int64})
    g = []
    for p in sorted(glob.glob(f"{WK}/fund/{sym_usdc}/*.zip")):
        x = pd.read_csv(p)
        g.append(pd.DataFrame({"ts": x.calc_time.astype(np.int64), "rate": x.last_funding_rate.astype(float)}))
    if g and t_usdc is not None:
        g = pd.concat(g)
        F = pd.concat([f[f.ts < t_usdc], g[g.ts >= t_usdc]])
    else:
        F = f
    F = F.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return F.ts.to_numpy(np.int64), F.rate.to_numpy(np.float64)


def fund_sum(fts, frate, t0, t1):
    """sum of rates with settlement in (t0, t1]; vectorised over arrays t0,t1."""
    cs = np.r_[0.0, np.cumsum(frate)]
    i0 = np.searchsorted(fts, t0, side="right"); i1 = np.searchsorted(fts, t1, side="right")
    return cs[i1] - cs[i0]


def px_at(X, T):
    """price at time T = close of bar opened at T-1m (index by ts)."""
    idx = pd.Index(X.ts.to_numpy())
    pos = idx.get_indexer(np.asarray(T, np.int64) - MIN)
    out = np.full(len(pos), np.nan); ok = pos >= 0
    out[ok] = X.close.to_numpy()[pos[ok]]
    return out


def through(X, T, side, W):
    """limit at P(T): long fills iff min(low) over bars opened in [T, T+W) < P(T); short iff max(high) > P(T)."""
    ts = X.ts.to_numpy(); lo = X.low.to_numpy(); hi = X.high.to_numpy()
    i0 = np.searchsorted(ts, np.asarray(T, np.int64)); P = px_at(X, T)
    fill = np.zeros(len(i0), bool); tfill = np.full(len(i0), -1, np.int64)
    for k in range(len(i0)):
        a = i0[k]; b = a + W
        if a >= len(ts) or not np.isfinite(P[k]):
            continue
        seg = lo[a:b] < P[k] if side[k] > 0 else hi[a:b] > P[k]
        assert ts[min(b, len(ts)) - 1] - ts[a] <= (W - 1) * MIN
        if seg.any():
            fill[k] = True; tfill[k] = ts[a + int(np.argmax(seg))]
    return fill, tfill


def costs(tr, X, fts, frate, hs, W=15):
    """tr: DataFrame t_in, t_out, side, day. returns dict model -> per-trade r (nan = not filled)."""
    side = tr.side.to_numpy(np.float64)
    a = px_at(X, tr.t_in.to_numpy()); b = px_at(X, tr.t_out.to_numpy())
    g = side * (b / a - 1)
    fu = side * fund_sum(fts, frate, tr.t_in.to_numpy(np.int64), tr.t_out.to_numpy(np.int64))
    out = {"M0": g - fu, "M2": g - 2 * (TAKER + hs) - fu}
    for w in (5, 15, 30):
        f, _ = through(X, tr.t_in.to_numpy(np.int64), side, w)
        r = g - AS_BPS * 1e-4 - (TAKER + hs) - fu
        r[~f] = np.nan
        out[f"M1_W{w}"] = r; out[f"fill_W{w}"] = f
    out["gross"] = g; out["fund"] = fu
    return out


def daily(day_ms, r, days):
    s = pd.Series(r, index=pd.to_datetime(day_ms, unit="ms")).dropna()
    return s.groupby(level=0).sum().reindex(days, fill_value=0.0)


def stats(r, ann=365):
    r = r.dropna()
    if len(r) < 10 or r.std() == 0:
        return {"sharpe": 0.0, "ann": 0.0, "maxdd": 0.0, "n": int(len(r))}
    eq = (1 + r).cumprod()
    return {"sharpe": float(r.mean() / r.std() * np.sqrt(ann)), "ann": float(r.mean() * ann),
            "maxdd": float((eq / eq.cummax() - 1).min()), "n": int(len(r))}


def split(r, ann=365):
    return {"E": stats(r[(r.index >= E0) & (r.index <= E1)], ann), "C": stats(r[(r.index >= C0) & (r.index <= C1)], ann)}


def dsr(r, N):
    """same formula as research/mom/t2_mom.py dsr()."""
    x = r.dropna().values; T = len(x); sr = x.mean() / x.std(ddof=1)
    g3 = float(pd.Series(x).skew()); g4 = float(pd.Series(x).kurt()) + 3
    em = 0.5772156649
    sr0 = np.sqrt(1.0 / T) * ((1 - em) * norm.ppf(1 - 1.0 / N) + em * norm.ppf(1 - 1.0 / (N * np.e)))
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return {"sr_d": float(sr), "sr0_d": float(sr0), "dsr": float(norm.cdf(z)), "T": T, "N": N}
