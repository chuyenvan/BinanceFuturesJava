#!/usr/bin/env python3
"""BTC_BASE core (PREREG_BTC_BASE): equity MTM PHUT cua crash-buy K24+skipFull (chan lenh ECMEAS bucket DEV / HO4 ho4-k24-b)
+ sleeve BTC (spot, tai khoan tach, khong don bay). Gia chan crash-buy = close kline1m Binance Vision (DEV qua gvz_mtm.kp,
HO qua cache ecm_px cua ecm_mtm_h/ho4_score_a). Gia BTC/ETH = px_btceth.npz (Vision kline1m USDT-M, px_build.py).
Mo phong theo su kien (mo/dong chan, moc 00:00 UTC, funding) roi dung lai equity vector hoa.
Sizing crash-buy trong sim: budget = equityNow(MTM) x F_BASE x throttle / ladder (TradeUtils.managerBudget, FIX_B3=true,
leverage 1) => size ty le voi equity MTM => bien the scale chan theo rho = E_bien_the(m0) / E_B0(m0) (chan giu nguyen gia/thoi diem).
"""
import json
import logging
import os
import pickle
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402  nguon gia Vision - PHAI import truoc reset_rule_score
import reset_rule_score as RR  # noqa: E402
assert RR._work is MT._work_vision, "reset_rule_score chua bi patch sang Vision"

log = logging.getLogger("bbcore")
W = "/home/ubuntu/claude_master/btc_base"
MS = 60000
CAP = 35000.0
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
COST = 0.0004 + 0.0005          # phi + truot moi chieu
TOL = 1e-6


def umin(s):
    """'YYYY-MM-DD HH:MM' UTC -> phut UTC tuyet doi."""
    return int(pd.Timestamp(s).value // 10**6) // MS


WIN = {
    "D": dict(a0=umin("2021-06-30 17:00"), a1=umin("2025-12-31 17:00"), w22=umin("2021-12-31 17:00"),
              y22=(umin("2021-12-31 17:00"), umin("2022-12-31 17:00"))),
    "H": dict(a0=umin("2025-12-31 17:00"), a1=umin("2026-09-30 17:00"), w22=umin("2025-12-31 17:00"), y22=None),
}


# ----------------------------------------------------------------------------------------------------------- du lieu
def ffill_lim(a, fill, lim):
    s = pd.Series(a).ffill(limit=lim)
    nmiss = int(s.isna().sum())
    return s.fillna(fill).to_numpy(np.float64), nmiss


def dev_legs():
    d = pd.read_parquet("/home/ubuntu/claude_master/edge_attr/legs.parquet")
    d = d[d.win == "D"].copy()
    t0 = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    t1 = pd.to_datetime(d.end, format="%Y%m%d %H:%M", errors="coerce")
    d = d[(t0 >= "2021-07-01") & t1.notna() & (t1 < "2026-01-01")].copy()
    a0 = WIN["D"]["a0"]
    d["m0"] = (d.M // MS - a0).astype(np.int64)
    d["m1"] = (d.E // MS - a0).astype(np.int64)
    d["key"] = d.vs + "|" + d.m0.astype(str) + "|" + d.m1.astype(str)
    return d


def dev_closes(d):
    p = W + "/closes_D.pkl"
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    u = d.drop_duplicates("key")[["key", "vs", "m0", "m1"]]
    a0 = WIN["D"]["a0"]
    arrs = {k: np.full(max(m1 - m0, 0), np.nan, np.float32) for k, m0, m1 in zip(u.key, u.m0, u.m1)}
    for ym in pd.period_range("2021-06", "2025-12", freq="M").strftime("%Y-%m"):
        f = MT.kp(ym)
        b0 = umin(ym + "-01 00:00") - a0
        b1 = umin(str((pd.Timestamp(ym + "-01") + pd.offsets.MonthBegin(1)))[:16]) - a0
        live = u[(u.m0 < b1) & (u.m1 > b0)]
        if live.empty:
            continue
        t = pq.read_table(f, columns=["ts", "sym", "close"]).to_pandas()
        t["sym"] = t["sym"].astype(str)
        t = t[t["sym"].isin(set(live.vs))].drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"], kind="mergesort")
        g = {s: (x["ts"].to_numpy(np.int64) // MS - a0, x["close"].to_numpy(np.float32)) for s, x in t.groupby("sym", sort=False)}
        for k, vs, m0, m1 in zip(live.key, live.vs, live.m0, live.m1):
            if vs not in g:
                continue
            mi, cl = g[vs]
            lo, hi = np.searchsorted(mi, max(m0, b0)), np.searchsorted(mi, min(m1, b1))
            arrs[k][mi[lo:hi] - m0] = cl[lo:hi]
        log.info("closes D %s live=%d", ym, len(live))
    pickle.dump(arrs, open(p, "wb"), protocol=4)
    return arrs


def ho_legs(seed):
    import nsel_score_b as NB  # noqa: F401 (TZ)
    d = pd.read_csv("/home/ubuntu/kaggle_sim/out/ho4-k24-b-s%d/storage/printDone.csv" % seed, index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("entry", "margin", "pnl", "quantity"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["entry", "margin", "pnl"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    tz = 7 * 3600 * 1000
    ts = pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M").astype("int64") // 10**6 - tz
    te = pd.to_datetime(d["end"].astype(str).str.strip(), format="%Y%m%d %H:%M").astype("int64") // 10**6 - tz
    a0 = WIN["H"]["a0"]
    d["m0"] = (ts // MS - a0).astype(np.int64)
    d["m1"] = (te // MS - a0).astype(np.int64)
    d["vs"] = d["sym"] + "USDT"
    rj = json.load(open("/home/ubuntu/kaggle_sim/out/ho4-k24-b-s%d/result.json" % seed))
    return d.reset_index(drop=True), float(rj["equity_start"])


def ho_closes(d, nm):
    """gia close 1m Vision tu cache ecm_px (SYM_YYYY-MM.npz: ot ms, c). Tra list mang [a, b) moi chan (NaN neu thieu)."""
    px = "/home/ubuntu/claude_master/1013/ecm/ecm_px"
    a0 = WIN["H"]["a0"]
    cache, out = {}, []
    months = list(pd.period_range("2025-12", "2026-09", freq="M").strftime("%Y-%m"))
    for vs, m0, m1 in zip(d.vs, d.m0, d.m1):
        a, b = max(int(m0), 0), min(int(m1), nm)
        if b <= a:
            out.append(np.zeros(0))
            continue
        if vs not in cache:
            ot, c = [], []
            for ym in months:
                f = "%s/%s_%s.npz" % (px, vs, ym)
                if os.path.exists(f):
                    z = np.load(f)
                    ot.append(z["ot"])
                    c.append(z["c"])
            if ot:
                ot, c = np.concatenate(ot), np.concatenate(c)
                o = np.argsort(ot, kind="stable")
                cache[vs] = (ot[o] // MS - a0, c[o])
            else:
                cache[vs] = None
        arr = np.full(b - a, np.nan)
        if cache[vs] is not None:
            mi, cl = cache[vs]
            lo, hi = np.searchsorted(mi, a), np.searchsorted(mi, b)
            arr[mi[lo:hi] - a] = cl[lo:hi]
        out.append(arr)
    return out


def load_px(win):
    z = np.load(W + "/px_btceth.npz")
    t0 = int(z["t0"])
    a0, a1 = WIN[win]["a0"], WIN[win]["a1"]
    btc, eth = z["btc"], z["eth"]
    assert not np.isnan(btc[a0 - t0:a1 - t0]).any() and not np.isnan(eth[a0 - t0:a1 - t0]).any(), "BTC/ETH thieu phut"
    P = dict(btc=btc[a0 - t0:a1 - t0].astype(np.float64), eth=eth[a0 - t0:a1 - t0].astype(np.float64))
    # dong cua ngay UTC (phut 23:59) cho bo loc T, gom ca lich su truoc cua so
    full = btc.astype(np.float64)
    k_all = np.arange(len(full))
    dmask = ((t0 + k_all + 1) % 1440) == 0
    P["daily_btc_idx"] = k_all[dmask] - (a0 - t0)       # chi so tren truc cua so (am = truoc cua so)
    P["daily_btc"] = full[dmask]
    fund = {}
    for s in ("BTCUSDT", "ETHUSDT"):
        m = z["f_sym"] == s
        k = z["f_ts"][m] // MS - a0
        r = z["f_rate"][m]
        ok = (k >= 0) & (k < a1 - a0)
        fund[s] = (k[ok].astype(np.int64), r[ok])
    P["fund"] = fund
    return P


# ----------------------------------------------------------------------------------------------------------- seed
class Seed:
    """chan crash-buy tren truc phut cua so [0, NM): a=max(m0,0), b=min(m1,NM); pre = mo truoc cua so (rho co dinh 1)."""

    def __init__(self, d, carr, base, nm, lim=60):
        d = d[d.m0 < nm].copy()
        pre_closed = d.m1 < 0
        self.base = float(base) + float(d.loc[pre_closed, "pnl"].sum())
        keep = ~pre_closed.to_numpy()
        d = d[keep]
        carr = [c for c, k in zip(carr, keep) if k]
        o = np.argsort(d.m0.to_numpy(), kind="stable")
        d = d.iloc[o]
        carr = [carr[i] for i in o]
        self.nm = nm
        self.m0 = d.m0.to_numpy(np.int64)
        self.m1 = d.m1.to_numpy(np.int64)
        self.a = np.maximum(self.m0, 0)
        self.b = np.minimum(self.m1, nm)
        self.pre = self.m0 < 0
        self.mg = d.margin.to_numpy(float)
        self.en = d.entry.to_numpy(float)
        self.pnl = d.pnl.to_numpy(float)
        self.n = len(d)
        self.u = []
        self.miss_after_ffill = 0
        self.legs_noprice = 0
        for i in range(self.n):
            c = carr[i]
            L = int(self.b[i] - self.a[i])
            if L <= 0:
                self.u.append(np.zeros(0))
                continue
            assert len(c) == L, (i, len(c), L)
            if np.isnan(c).all():
                self.legs_noprice += 1
            cc, nmiss = ffill_lim(c, self.en[i], lim)
            self.miss_after_ffill += nmiss
            self.u.append((self.mg[i] / self.en[i]) * (cc - self.en[i]))
        self.legmin = int(sum(len(x) for x in self.u))
        # B0
        U, N, R = self.paths(np.ones(self.n))
        self.E0 = self.base + np.cumsum(R)[:nm] + U
        self.N0 = N
        adj = np.zeros(nm)
        for i in range(self.n):
            if not self.pre[i] and self.b[i] > self.a[i]:
                adj[self.a[i]] += self.u[i][0]
            elif not self.pre[i] and self.m1[i] == self.m0[i] and 0 <= self.m0[i] < nm:
                adj[self.m0[i]] += self.pnl[i]
        self.E0ex = self.E0 - adj          # E_B0 truoc khi tinh u cua chan mo ngay phut do

    def paths(self, rho):
        nm = self.nm
        U = np.zeros(nm)
        N = np.zeros(nm)
        R = np.zeros(nm + 2)
        for i in range(self.n):
            a, b = self.a[i], self.b[i]
            if b > a:
                U[a:b] += rho[i] * self.u[i]
                N[a:b] += rho[i] * (self.mg[i] + self.u[i])
            if self.m1[i] < nm:
                R[max(self.m1[i], 0)] += rho[i] * self.pnl[i]
        return U, N, R


# ----------------------------------------------------------------------------------------------------------- mo phong
def simulate(S, P, a0, var, rng_scramble=None):
    """var: kind in {B0,S,O}; w; G; trend; eth; fund; bh (S khong rebalance). Tra dict path + log su kien."""
    kind = var["kind"]
    w = float(var.get("w", 0.0))
    G = float(var.get("G", 1.0))
    eth = bool(var.get("eth", False))
    trend = bool(var.get("trend", False))
    fund = bool(var.get("fund", False))
    bh = bool(var.get("bh", False))
    nm = S.nm
    Pb, Pe = P["btc"], P["eth"]
    rho = np.ones(S.n)
    q = {"b": 0.0, "e": 0.0}
    cost_basis = {"b": 0.0, "e": 0.0}          # USD theo gia mua binh quan
    cash = 0.0
    Rcum = 0.0
    dq = {"b": np.zeros(nm), "e": np.zeros(nm)}
    dcash = np.zeros(nm)
    dfee = np.zeros(nm)
    ev = dict(ra_n=0, ra_usd=0.0, ra_pnl=0.0, ck_buy=0, ck_sell=0, trade_usd=0.0, fees=0.0, funding=0.0,
              v4_max_excess=0.0, trend_off_days=0, trend_switch=0, eq_check_max=0.0)
    opens_at = {}
    closes_at = {}
    for i in range(S.n):
        if not S.pre[i] and S.b[i] > S.a[i]:
            opens_at.setdefault(int(S.a[i]), []).append(i)
        elif not S.pre[i] and S.m1[i] <= S.m0[i] and 0 <= S.m0[i] < nm:
            opens_at.setdefault(int(S.m0[i]), []).append(i)
        if 0 <= S.m1[i] < nm:
            closes_at.setdefault(int(S.m1[i]), []).append(i)
    ck = np.nonzero(((a0 + np.arange(nm) + 1) % 1440) == 0)[0]
    ck_set = set(ck.tolist())
    month_ck = set(int(k) for k in ck if pd.Timestamp((a0 + k + 1) * MS, unit="ms").day == 1)
    fk = {}
    if fund:
        for s, key in (("BTCUSDT", "b"), ("ETHUSDT", "e")):
            for k, r in zip(*P["fund"][s]):
                fk.setdefault(int(k), []).append((key, float(r)))
    # bo loc T: dong cua ngay UTC
    di, dc = P["daily_btc_idx"], P["daily_btc"]
    dpos = {int(k): j for j, k in enumerate(di)}
    t_on = True
    open_set = set(i for i in range(S.n) if S.pre[i] and S.b[i] > S.a[i] and S.a[i] == 0)
    events = sorted(set(opens_at) | set(closes_at) | ck_set | set(fk))
    first_alloc_done = False

    def price(key, k):
        return Pb[k] if key == "b" else Pe[k]

    def Eat(k):
        u = 0.0
        for i in open_set:
            u += rho[i] * S.u[i][k - S.a[i]]
        return S.base + Rcum + u + cash + q["b"] * Pb[k] + q["e"] * Pe[k]

    def Nat(k):
        x = 0.0
        for i in open_set:
            x += rho[i] * (S.mg[i] + S.u[i][k - S.a[i]])
        return x

    def trade(key, k, usd):
        """usd > 0 mua, < 0 ban (notional)."""
        nonlocal cash
        if abs(usd) < 1e-9:
            return 0.0
        p = price(key, k)
        units = usd / p
        fee = COST * abs(usd)
        pnl = 0.0
        if usd > 0:
            cost_basis[key] += usd
        else:
            frac = min(1.0, -units / q[key]) if q[key] > 0 else 0.0
            cb = cost_basis[key] * frac
            pnl = -usd - cb - fee
            cost_basis[key] -= cb
        q[key] += units
        if abs(q[key]) < 1e-15:
            q[key] = 0.0
        dq[key][k] += units
        cash -= usd + fee
        dcash[k] -= usd + fee
        dfee[k] += fee
        ev["fees"] += fee
        ev["trade_usd"] += abs(usd)
        return pnl

    def vb(k):
        return q["b"] * Pb[k] + q["e"] * Pe[k]

    for k in events:
        # (1) dong chan
        zl = []
        for i in closes_at.get(k, ()):
            if not S.pre[i] and S.m0[i] == k:      # chan do dai 0: ghi nhan sau khi gan rho
                zl.append(i)
                continue
            Rcum += rho[i] * S.pnl[i]
            open_set.discard(i)
        # (2) mo chan
        new = opens_at.get(k, ())
        if new:
            Eex = Eat(k)
            if kind == "O":
                base_v = Eex
            elif kind == "S":
                base_v = Eex - vb(k)
            else:
                base_v = S.E0ex[k]
            r = base_v / S.E0ex[k]
            for i in new:
                rho[i] = r
                if S.b[i] > S.a[i]:
                    open_set.add(i)
            for i in zl:
                Rcum += rho[i] * S.pnl[i]
            if kind == "O" and (q["b"] > 0 or q["e"] > 0):
                E = Eat(k)
                n = Nat(k) / E
                bt = vb(k) / E
                if n + bt > G + 1e-12:
                    need = min((n + bt - G) * E, vb(k))
                    V = vb(k)
                    for key in ("b", "e"):
                        part = need * (q[key] * price(key, k)) / V if V > 0 else 0.0
                        if part > 0:
                            ev["ra_pnl"] += trade(key, k, -part)
                    ev["ra_n"] += 1
                    ev["ra_usd"] += need
                    E2 = Eat(k)
                    ev["v4_max_excess"] = max(ev["v4_max_excess"], Nat(k) / E2 + vb(k) / E2 - G)
        # (3) moc ngay 00:00 UTC (quyet dinh + khop o close phut 23:59)
        if k in ck_set:
            if trend and k in dpos:
                j = dpos[k]
                pc = dc[j]
                if t_on:
                    if pc <= 0.70 * dc[max(0, j - 179):j + 1].max():
                        t_on = False
                        ev["trend_switch"] += 1
                else:
                    if j >= 1 and pc > dc[max(0, j - 30):j].max():
                        t_on = True
                        ev["trend_switch"] += 1
                if not t_on:
                    ev["trend_off_days"] += 1
            E = Eat(k)
            tgt = None
            if kind == "O":
                n = Nat(k) / E
                tgt = (min(w, max(0.0, G - n)) * E) if t_on else 0.0
            elif kind == "S" and ((k in month_ck and not bh) or (bh and not first_alloc_done and k in month_ck)):
                tgt = w * E
                first_alloc_done = True
            if tgt is not None:
                if eth:
                    for key in ("b", "e"):
                        cur = q[key] * price(key, k)
                        d_ = tgt / 2 - cur
                        if abs(d_) > 1e-9:
                            if d_ > 0:
                                ev["ck_buy"] += 1
                            else:
                                ev["ck_sell"] += 1
                            trade(key, k, d_)
                else:
                    cur = q["b"] * Pb[k]
                    d_ = tgt - cur
                    if abs(d_) > 1e-9:
                        if d_ > 0:
                            ev["ck_buy"] += 1
                        else:
                            ev["ck_sell"] += 1
                        trade("b", k, d_)
        # (4) funding (perp): long tra rate x notional
        for key, r in fk.get(k, ()):
            if q[key] > 0:
                f = q[key] * price(key, k) * r
                cash -= f
                dcash[k] -= f
                dfee[k] += f
                ev["funding"] += f
    # dung path
    U, N, R = S.paths(rho)
    qb = np.cumsum(dq["b"])
    qe = np.cumsum(dq["e"])
    c = np.cumsum(dcash)
    V = qb * Pb + qe * Pe
    CB = S.base + np.cumsum(R)[:nm] + U
    E = CB + c + V
    # kiem noi bo: E tai cac moc su kien == E trong vong lap (lay mau)
    return dict(E=E, CB=CB, V=V, N=N, qb=qb, qe=qe, cash=c, fee=dfee, rho=rho, ev=ev)


# ----------------------------------------------------------------------------------------------------------- chi so
def dd_of(x):
    pk = np.maximum.accumulate(x)
    dd = x / pk - 1.0
    t = int(dd.argmin())
    p = int(np.argmax(x[:t + 1]))
    return 100 * float(dd[t]), p, t


def ts_of(a0, k):
    return str(pd.Timestamp((a0 + int(k)) * MS + 7 * 3600 * 1000, unit="ms"))[:16]


def sleeve_twr_dd(r, Pb, Pe):
    qb, qe = r["qb"], r["qe"]
    V = r["V"]
    dV = np.zeros_like(V)
    dV[1:] = qb[:-1] * np.diff(Pb) + qe[:-1] * np.diff(Pe)
    dV -= r["fee"]
    Vp = np.concatenate([[0.0], V[:-1]])
    ret = np.where(Vp > 1e-9, dV / np.where(Vp > 1e-9, Vp, 1.0), 0.0)
    idx = np.cumprod(1.0 + ret)
    return dd_of(idx[59::60])[0], float(idx[-1] - 1.0)


def metrics(r, S, P, win, B0E=None):
    w = WIN[win]
    a0 = w["a0"]
    E = r["E"]
    nm = len(E)
    i22 = w["w22"] - a0
    e22 = E[i22:]
    yrs22 = (nm - i22) / (1440 * 365.25)
    m = {}
    m["cagr22"] = 100 * ((e22[-1] / e22[0]) ** (1 / yrs22) - 1)
    yrs = nm / (1440 * 365.25)
    m["cagr_full"] = 100 * ((E[-1] / E[0]) ** (1 / yrs) - 1)
    m["roi"] = 100 * (E[-1] / E[0] - 1)
    d_min, p, t = dd_of(E)
    m["dd_min_full"], m["dd_peak"], m["dd_trough"] = d_min, ts_of(a0, p), ts_of(a0, t)
    m["dd_hour_full"] = dd_of(E[59::60])[0]
    m["dd_day_full"] = dd_of(E[1439::1440])[0]
    m["dd_rule"] = min(m["dd_hour_full"], m["dd_day_full"])
    m["dd_min_22"] = dd_of(e22)[0]
    m["dd_hour_22"] = dd_of(E[i22:][59::60])[0]
    m["calmar22"] = m["cagr22"] / abs(m["dd_min_22"]) if m["dd_min_22"] < 0 else float("nan")
    m["calmar_rule"] = m["cagr22"] / abs(m["dd_rule"]) if m["dd_rule"] < 0 else float("nan")
    Ed = E[1439::1440]
    days = pd.date_range(pd.Timestamp((a0 * MS) + 7 * 3600 * 1000, unit="ms").normalize(), periods=len(Ed), freq="D")
    me = np.nonzero(np.asarray(days.is_month_end))[0]
    Em = Ed[me]
    rm = 100 * (Em / np.concatenate([[E[0]], Em[:-1]]) - 1)
    jm = int(np.argmin(rm))
    m["worst_month"], m["worst_month_at"] = float(rm[jm]), str(days[me[jm]].date())[:7]
    m["util_mean"] = float(np.mean((r["N"] + r["V"]) / E))
    m["n_mean"] = float(np.mean(r["N"] / E))
    m["b_mean"] = float(np.mean(r["V"] / E))
    m["gross_max"] = float(np.max((r["N"] + r["V"]) / E))
    m["pnl_total"] = float(E[-1] - E[0])
    m["pnl_cb"] = float(r["CB"][-1] - r["CB"][0])
    m["pnl_btc"] = float((r["cash"][-1] + r["V"][-1]) - (r["cash"][0] + r["V"][0]))
    m["btc_sleeve_dd_twr_hour"], m["btc_sleeve_twr"] = sleeve_twr_dd(r, P["btc"], P["eth"])
    m.update({"ev_" + k: v for k, v in r["ev"].items()})
    if w["y22"] is not None:
        y0, y1 = w["y22"][0] - a0, w["y22"][1] - a0
        m["pnl22_total"] = float(E[y1 - 1] - E[y0 - 1])
        m["pnl22_cb"] = float(r["CB"][y1 - 1] - r["CB"][y0 - 1])
        m["pnl22_btc"] = m["pnl22_total"] - m["pnl22_cb"]
        m["dd22_min"] = dd_of(E[y0:y1])[0]
        m["dd22_hour"] = dd_of(E[y0:y1][59::60])[0]
    return m


def corr_info(S, P, a0):
    """tuong quan ngay (+07) BTC vs crash-buy B0: toan ky va ngay co lenh moi."""
    Ed = S.E0[1439::1440]
    Bd = P["btc"][1439::1440]
    rc = np.diff(Ed) / Ed[:-1]
    rb = np.diff(Bd) / Bd[:-1]
    nday = len(Ed)
    has = np.zeros(nday, bool)
    for i in range(S.n):
        if not S.pre[i] and 0 <= S.m0[i] < len(S.E0):
            has[S.m0[i] // 1440] = True
    hm = has[1:]
    return dict(corr_all=float(np.corrcoef(rc, rb)[0, 1]), corr_entry_days=float(np.corrcoef(rc[hm], rb[hm])[0, 1]),
                n_entry_days=int(hm.sum()), n_days=int(len(rc)))


def nt_stats(S):
    n = S.N0 / S.E0
    return dict(mean=float(n.mean()), p50=float(np.percentile(n, 50)), p90=float(np.percentile(n, 90)),
                p99=float(np.percentile(n, 99)), max=float(n.max()), pct_lt5=float(100 * (n < 0.05).mean()),
                pct_lt10=float(100 * (n < 0.10).mean()), pct_zero=float(100 * (n <= 1e-12).mean()),
                gross_max=float(n.max()), gross_gt1=bool(n.max() > 1.0))
