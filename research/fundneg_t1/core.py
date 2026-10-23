#!/usr/bin/env python3
"""FUNDNEG_T1 core library: panel/funding loading, universe, vol terciles, trade evaluation, funding accrual.
Prereg: docs/prereg/PREREG_FUNDNEG_T1.md (commit 66862db3). All ts int64 ms UTC.
"""
import glob
import numpy as np
import pandas as pd

WK = "/home/ubuntu/claude_master/fundneg_t1_wk"
PANEL = WK + "/panel"
FUND = "/home/ubuntu/vz/out/funding"
KS = "/home/ubuntu/kaggle_sim/out"
TAGS = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]
MMS, HMS, DMS = 60_000, 3_600_000, 86_400_000
HK = 10**7          # hourly key = code*HK + hr
FK = 10**13         # funding key = code*FK + tau_ms
COST1, COST2 = 0.0030, 0.0060   # round-trip (0.05% taker + 0.10% slip) x2 sides; x2 stress


def ms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 10**6)


T_DISC0, T_TEST0, T_END = ms("2022-01-01"), ms("2024-01-01"), ms("2026-01-01")
DATA_LAST = ms("2025-12-31 23:59")      # last 1m candle open ts available
DAY0 = ms("2021-12-01") // DMS          # day index origin of dense daily matrices


class Panel:
    def __init__(self):
        fs = sorted(glob.glob(PANEL + "/h-*.parquet"))
        H = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
        self.syms = np.array(sorted(H.sym.unique()))
        code = np.searchsorted(self.syms, H.sym.values).astype(np.int64)
        hr = H.hr.values.astype(np.int64)
        o = np.lexsort((hr, code))
        self.key = (code * HK + hr)[o]
        assert (np.diff(self.key) > 0).all(), "hourly key not unique"
        for c in ["c01", "c59", "hi_a", "lo_a", "hi_b", "lo_b", "last_close"]:
            setattr(self, c, H[c].values.astype(np.float64)[o])
        self.last_ts = H.last_ts.values.astype(np.int64)[o]
        assert H.last_ts.dtype == np.int64 and H.hr.dtype == np.int64
        code_s = code[o]
        del H
        n = len(self.syms)
        # per-symbol last data
        last_i = np.searchsorted(code_s, np.arange(n), side="right") - 1
        self.sym_last_ts = self.last_ts[last_i]
        self.sym_last_close = self.last_close[last_i]
        self.code_s = code_s
        # daily
        fs = sorted(glob.glob(PANEL + "/d-*.parquet"))
        D = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
        assert D.day.dtype == np.int64
        dc = np.searchsorted(self.syms, D.sym.values)
        ok = (dc < n) & (self.syms[np.minimum(dc, n - 1)] == D.sym.values)
        assert ok.all()
        nd = int(D.day.max()) - DAY0 + 1
        self.QV = np.full((nd, n), np.nan)
        self.DC = np.full((nd, n), np.nan)
        di = D.day.values - DAY0
        self.QV[di, dc] = D.qv.values
        self.DC[di, dc] = D.dclose.values
        assert len(D) == len(set(zip(di.tolist(), dc.tolist())))

    def code(self, sym):
        return int(np.searchsorted(self.syms, sym))

    def lookup(self, arr, codes, hrs):
        q = codes * HK + hrs
        i = np.searchsorted(self.key, q)
        i2 = np.minimum(i, len(self.key) - 1)
        ok = self.key[i2] == q
        return np.where(ok, arr[i2], np.nan)

    def last_close_before(self, codes, hrs):
        """close of last candle in latest hour < hrs for same symbol (gap fallback)."""
        q = codes * HK + hrs
        i = np.searchsorted(self.key, q) - 1
        i2 = np.maximum(i, 0)
        ok = (i >= 0) & (self.code_s[i2] == codes)
        return np.where(ok, self.last_close[i2], np.nan)


class Funding:
    def __init__(self, P, y0=2021, y1=2025):
        fs = [f for f in sorted(glob.glob(FUND + "/*/*.parquet"))
              if y0 <= int(f.split("/")[-1][:4]) <= y1]
        F = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
        assert F.ts.dtype == np.int64
        F["sym"] = F.sym.astype(str)
        F = F[F.ts >= ms("2021-12-01")]
        self.n_raw = len(F)
        c = np.searchsorted(P.syms, F.sym.values)
        c2 = np.minimum(c, len(P.syms) - 1)
        ok = P.syms[c2] == F.sym.values
        self.n_nokline = int((~ok).sum())
        F = F[ok].copy()
        F["code"] = c2[ok].astype(np.int64)
        F["tau"] = F.ts - F.ts % MMS
        assert (F.tau % HMS == 0).all()
        F.sort_values(["code", "tau"], inplace=True)
        assert not F.duplicated(["code", "tau"]).any(), "dup (sym,tau)"
        self.code = F.code.values
        self.tau = F.tau.values.astype(np.int64)
        self.rate = F.rate.values.astype(np.float64)
        self.interval_h = F.interval_h.values.astype(np.int64)
        self.f8 = self.rate * 8.0 / self.interval_h
        self.fkey = self.code * FK + self.tau
        assert (np.diff(self.fkey) > 0).all()
        # price at settlement = close of 1m candle open ts tau-60000 = c59 of hour tau/HMS - 1
        self.pset = P.lookup(P.c59, self.code, self.tau // HMS - 1)
        self.build_cs()

    def build_cs(self):
        # ADDENDUM 1: per-symbol inclusive cumsums (global cumsum lost ~1e-8 precision on low-price coins)
        fin = np.isfinite(self.pset)
        self.v_rp = np.where(fin, self.rate * np.where(fin, self.pset, 0.0), 0.0)
        self.v_rm = np.where(fin, 0.0, self.rate)
        g = pd.Series(self.code)
        self.cs_rp = pd.Series(self.v_rp).groupby(g.values).cumsum().values
        self.cs_rm = pd.Series(self.v_rm).groupby(g.values).cumsum().values


def accrue(F, codes, t_lo_excl, t_hi_incl, P0):
    """Long funding cashflow per unit of initial notional: -sum rate(t') * P(t')/P0 over settlements
    t_lo_excl < t' <= t_hi_incl (P missing -> P0). Returns (fund, n_settlements)."""
    lo = np.searchsorted(F.fkey, codes * FK + t_lo_excl, side="right")
    hi = np.searchsorted(F.fkey, codes * FK + t_hi_incl, side="right")
    has = hi > lo
    h1 = np.where(has, hi - 1, 0)
    l0 = np.where(has, lo, 0)
    srp = np.where(has, F.cs_rp[h1] - F.cs_rp[l0] + F.v_rp[l0], 0.0)
    srm = np.where(has, F.cs_rm[h1] - F.cs_rm[l0] + F.v_rm[l0], 0.0)
    fund = -(srp / P0 + srm)
    return fund, hi - lo


def evaluate(P, F, codes, taus, Hh, with_path=False):
    """Vectorised trade evaluation. Entry close of candle tau+1m, exit close of candle tau+H+1m."""
    codes = np.asarray(codes, dtype=np.int64)
    taus = np.asarray(taus, dtype=np.int64)
    th = taus // HMS
    xh = th + Hh
    P0 = P.lookup(P.c01, codes, th)
    P1 = P.lookup(P.c01, codes, xh)
    exit_open = xh * HMS + MMS
    delist = exit_open > P.sym_last_ts[codes]
    t_out = taus + Hh * HMS + 2 * MMS
    t_out = np.where(delist, P.sym_last_ts[codes] + MMS, t_out)
    P1 = np.where(delist, P.sym_last_close[codes], P1)
    gap = (~delist) & np.isnan(P1)
    P1 = np.where(gap, P.last_close_before(codes, xh), P1)
    t_in = taus + 2 * MMS
    f_hi = np.minimum(taus + Hh * HMS, t_out)
    fund, nset = accrue(F, codes, taus, f_hi, P0)
    gross = P1 / P0 - 1.0
    out = dict(P0=P0, P1=P1, t_in=t_in, t_out=t_out, delist=delist, gap=gap, fund=fund, nset=nset,
               gross=gross, net=gross + fund - COST1, net2=gross + fund - COST2)
    if with_path:
        mfe = np.full(len(codes), np.nan)
        mae = np.full(len(codes), np.nan)
        for j in range(len(codes)):
            if not np.isfinite(P0[j]):
                continue
            c = codes[j]
            a0 = np.searchsorted(P.key, c * HK + th[j])
            a1 = np.searchsorted(P.key, c * HK + xh[j] - 1, side="right")
            b0 = np.searchsorted(P.key, c * HK + th[j] + 1)
            b1 = np.searchsorted(P.key, c * HK + xh[j], side="right")
            hs = np.concatenate([P.hi_a[a0:a1], P.hi_b[b0:b1]])
            ls = np.concatenate([P.lo_a[a0:a1], P.lo_b[b0:b1]])
            if len(hs) and np.isfinite(hs).any():
                mfe[j] = np.nanmax(hs) / P0[j] - 1.0
                mae[j] = np.nanmin(ls) / P0[j] - 1.0
        out["mfe"], out["mae"] = mfe, mae
    return out


def universe(P):
    """U[month_idx, code] bool for months 2022-01..2025-12; top-100 by median 30d daily quote volume."""
    n = len(P.syms)
    U = np.zeros((48, n), dtype=bool)
    elig = np.array(["_" not in s for s in P.syms])
    for mi in range(48):
        y, m = 2022 + mi // 12, mi % 12 + 1
        d0 = ms("%04d-%02d-01" % (y, m)) // DMS - DAY0
        w = np.nan_to_num(P.QV[d0 - 30:d0], nan=0.0)
        assert w.shape[0] == 30
        med = np.median(w, axis=0)
        med = np.where(elig & (P.QV[d0 - 30:d0] > 0).any(axis=0), med, -1.0)
        order = np.lexsort((np.arange(n), -med))
        top = order[:100]
        top = top[med[top] > 0]
        U[mi, top] = True
    return U


def month_idx(taus):
    t = pd.to_datetime(taus, unit="ms")
    return ((t.year - 2022) * 12 + t.month - 1).values.astype(np.int64)


def vol_terciles(P, U):
    """TER[day_idx (since DAY0), code] in {0,1,2}, -1 = not in universe / no vol."""
    DCm = P.DC
    R = np.full_like(DCm, np.nan)
    R[1:] = np.log(DCm[1:] / DCm[:-1])
    vol = pd.DataFrame(R).rolling(30, min_periods=20).std().shift(1).values   # returns d-30..d-1
    TER = np.full(DCm.shape, -1, dtype=np.int8)
    for d in range(DCm.shape[0]):
        day_ms = (DAY0 + d) * DMS
        if day_ms < T_DISC0 or day_ms >= T_END:
            continue
        mi = month_idx(np.array([day_ms]))[0]
        u = U[mi] & np.isfinite(vol[d])
        v = vol[d, u]
        if len(v) < 3:
            continue
        q1, q2 = np.quantile(v, [1 / 3, 2 / 3])
        TER[d, np.nonzero(u)[0]] = ((v > q1).astype(np.int8) + (v > q2).astype(np.int8))
    return TER, vol


def x14_legs(P):
    fr = []
    for tag in TAGS:
        d = pd.read_csv("%s/tsx-x14-%s/storage/printDone.csv" % (KS, tag), index_col=False)
        d.columns = [c.strip() for c in d.columns]
        d["sym"] = d["sym"].astype(str).str.strip()
        d["sym"] = np.where(d["sym"].str.endswith("USDT"), d["sym"], d["sym"] + "USDT")
        st = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce") - pd.Timedelta(hours=7)
        en = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce") - pd.Timedelta(hours=7)
        fr.append(pd.DataFrame({"sym": d["sym"], "st": st, "en": en, "seed": tag}))
    L = pd.concat(fr, ignore_index=True)
    n_bad_start = int(L.st.isna().sum())
    L = L[L.st.notna()].copy()
    n_no_end = int(L.en.isna().sum())
    L["en"] = L.en.fillna(L.st + pd.Timedelta(hours=336))
    L["st_ms"] = (L.st.astype("int64") // 10**6).astype(np.int64)
    L["en_ms"] = (L.en.astype("int64") // 10**6).astype(np.int64)
    return L, dict(n_legs=len(L), n_bad_start=n_bad_start, n_no_end_filled336h=n_no_end,
                   first=str(L.st.min()), last=str(L.st.max()))


def overlap_flags(L, syms_str, taus):
    """(a) same sym X14 leg interval intersects [tau-24h, tau+24h]; (b) UTC day of tau has any X14 leg start."""
    W = 24 * HMS
    fa = np.zeros(len(taus), dtype=bool)
    g = {s: (x.st_ms.values, x.en_ms.values) for s, x in L.groupby("sym")}
    syms_str = np.asarray(syms_str)
    for s in np.unique(syms_str):
        if s not in g:
            continue
        idx = np.nonzero(syms_str == s)[0]
        st, en = g[s]
        t = taus[idx][:, None]
        fa[idx] = ((st[None, :] <= t + W) & (en[None, :] >= t - W)).any(axis=1)
    crash_days = set((L.st_ms.values // DMS).tolist())
    fb = np.array([d in crash_days for d in (taus // DMS).tolist()], dtype=bool)
    return fa, fb
