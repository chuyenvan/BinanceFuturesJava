"""klite.py - loi mo phong DON VI LUOI tren nen 1m (Giai doan 1, PREREG_GRIDV2_S1).

Numpy thuan (khong numba, khong goi ngoai numpy) -> chay duoc tren Kaggle CPU va Oracle.
Kieu tinh "lockstep": moi buoc r xu ly dong thoi moi don vi con cho (vector), nen O(sum thoi gian song).

Quy uoc:
- Luoi phut LIEN TUC cua 1 symbol, chi so nguyen 0..n-1; phut khong hop le (lo / active=False) co gia NaN.
- Don vi dat tai dau phut t0 (gio tron UTC); m0 = close phut t0-1; lenh song tu phut t0.
- Hai mo hinh khop BAO nhau: "OPT" (K_OPT) va "PESS" (K_PESS). Dac ta day du: PREREG_GRIDV2_S1_DRAFT.md muc 4.
- Moi gia tri tra ve theo don vi; PnL tinh theo phan so notional luc vao (notional = 1), doi ra bps khi xuat.
"""
import numpy as np

MIN_MS = 60000
DAY_MIN = 1440
FEE_MAKER = {"OPT": 2e-4, "PESS": 4e-4}      # maker VIP0 0,02 %; stress 0,04 % cho PESS
FEE_TAKER = 5e-4                              # taker VIP0 0,05 %
DELIST_SLIP_PESS = 50e-4                      # delist: truot bao thu 50 bps (protocol 2.3)
SLIP_TIER_FLOOR = {1: 2e-4, 2: 5e-4, 3: 10e-4}  # san truot taker PESS theo tier (SLIP_MAJOR/ALT cu + T3 gap doi)
LONG_GAP_MIN = 60                             # lo > 60 phut trong doi don vi => loai don vi
MIN_D_TICKS = 4                               # d < 4 tick => khong dat (gia roi rac ap dao)
TOL_TICK = 0.01                               # dung sai so sanh gia = 1 % tick (chong nhieu float)
EX_NONE, EX_LIMIT, EX_TIMEOUT, EX_DELIST, EX_TAKER_BEYOND = 0, 1, 2, 3, 4
EXIT_NAMES = {0: "none", 1: "limit", 2: "timeout", 3: "delist", 4: "taker_beyond"}


def floor_tick(p, tick):
    return np.floor(np.asarray(p) / tick + 1e-7) * tick


def ceil_tick(p, tick):
    return np.ceil(np.asarray(p) / tick - 1e-7) * tick


def unit_T(c, k):
    """T (phut) = k x (d / sigma_1m)^2 voi sigma_1m := sigma_1d / sqrt(1440) => T = k c^2 1440, lam tron."""
    return int(round(k * c * c * DAY_MIN))


def prepare_grid(O, H, L, C, valid, delist_idx=-1):
    """Chuan bi luoi 1 symbol. delist_idx = chi so phut hop le CUOI neu symbol bi delist (lifecycle), -1 neu khong."""
    valid = np.asarray(valid, bool).copy()
    n = len(valid)
    if delist_idx >= 0:
        valid[delist_idx + 1:] = False
    arr = [np.where(valid, np.asarray(x, np.float64), np.nan) for x in (O, H, L, C)]
    idx = np.arange(n, dtype=np.int64)
    lv = np.maximum.accumulate(np.where(valid, idx, -1))
    nv = np.minimum.accumulate(np.where(valid, idx, n)[::-1])[::-1]
    inval = ~valid
    if delist_idx >= 0:
        inval[delist_idx + 1:] = False          # sau delist khong phai "lo"
    lg = np.zeros(n, bool)
    dd = np.diff(np.r_[0, inval.astype(np.int8), 0])
    st, en = np.nonzero(dd == 1)[0], np.nonzero(dd == -1)[0]
    for s, e in zip(st, en):
        if e - s > LONG_GAP_MIN:
            lg[s:e] = True
    lgc = np.r_[0, np.cumsum(lg)].astype(np.int64)
    return dict(O=arr[0], H=arr[1], L=arr[2], C=arr[3], valid=valid, lv=lv, nv=nv, lgc=lgc, n=n,
                delist=int(delist_idx))


def run_units(G, t0, d, W, T, tick, slip, model, side_in, fund_s=None, fund_rate=None):
    """Mo phong cac don vi luoi MOT BEN (M1: BUY = 1 lenh mua tai L_b, SELL = 1 lenh ban tai L_s; doc lap).
    side_in: +1 BUY / -1 SELL theo don vi. t0, W, T: int (phut); d: buoc tuong doi; tick: tick tuyet doi;
    slip: truot taker PESS (phan so).
    fund_s: chi so phut cua moc funding (tang dan); fund_rate: rate tai moc.
    Tra dict cac mang theo don vi."""
    assert model in ("OPT", "PESS")
    pess = model == "PESS"
    O, H, L, C, n, dl = G["O"], G["H"], G["L"], G["C"], G["n"], G["delist"]
    t0 = np.asarray(t0, np.int64)
    nu = t0.size
    d = np.broadcast_to(np.asarray(d, np.float64), (nu,)).copy()
    W = np.broadcast_to(np.asarray(W, np.int64), (nu,)).copy()
    T = np.broadcast_to(np.asarray(T, np.int64), (nu,)).copy()
    tick = np.broadcast_to(np.asarray(tick, np.float64), (nu,)).copy()
    slip = np.broadcast_to(np.asarray(slip, np.float64), (nu,)).copy()
    assert np.all(t0 >= 1) and np.all(t0 + W + T + LONG_GAP_MIN + 1 < n + 1), "don vi vuot luoi"
    m0 = C[t0 - 1]
    assert np.all(np.isfinite(m0)), "m0 khong hop le"
    Lb = floor_tick(m0 * (1.0 - d), tick)
    Ls = ceil_tick(m0 * (1.0 + d), tick)
    tol = TOL_TICK * tick
    eps = tick if pess else np.zeros(nu)
    thr_b = Lb - eps + tol
    thr_s = Ls + eps - tol
    side_in = np.broadcast_to(np.asarray(side_in, np.int8), (nu,)).copy()
    assert np.all((side_in == 1) | (side_in == -1))
    f = np.full(nu, -1, np.int64)
    # ---- pha vao: 1 lenh cho (mot ben), song W phut
    pend = np.arange(nu)
    Wmax = int(W.max()) if nu else 0
    for r in range(Wmax):
        pend = pend[W[pend] > r]
        if pend.size == 0:
            break
        j = t0[pend] + r
        if dl >= 0:
            ok = j <= dl
            if not ok.all():
                pend, j = pend[ok], j[ok]
                if pend.size == 0:
                    break
        hit = np.where(side_in[pend] == 1, L[j] <= thr_b[pend], H[j] >= thr_s[pend])
        if hit.any():
            f[pend[hit]] = j[hit]
            pend = pend[~hit]
    side = np.where(f >= 0, side_in, 0).astype(np.int8)
    filled = f >= 0
    sidef = side.astype(np.float64)
    entry = np.where(side == 1, Lb, np.where(side == -1, Ls, np.nan))
    X = np.where(side == 1, ceil_tick(Lb * (1.0 + d), tick),
                 np.where(side == -1, floor_tick(Ls * (1.0 - d), tick), np.nan))
    x = np.full(nu, -1, np.int64)
    xpx = np.full(nu, np.nan)
    kind = np.zeros(nu, np.int8)
    fu = np.nonzero(filled)[0]
    r0 = 1 if pess else 0
    if pess and fu.size:
        # PESS: gia da vuot muc thoat ngay khi dong phut khop => thoat TAKER tai dung X o phut f+1
        cf = C[f[fu]]
        beyond = np.where(side[fu] == 1, cf >= X[fu] - tol[fu], cf <= X[fu] + tol[fu])
        ub = fu[beyond]
        x[ub], xpx[ub], kind[ub] = f[ub] + 1, X[ub], EX_TAKER_BEYOND
        if dl >= 0:
            e = ub[f[ub] >= dl]
            x[e], xpx[e], kind[e] = dl, C[dl], EX_DELIST
        fu = fu[~beyond]
    thr_x = np.where(side == 1, X + eps - tol, X - eps + tol)
    pend = fu
    Tmax = int(T[fu].max()) if fu.size else -1
    for r in range(r0, Tmax + 1):
        pend = pend[T[pend] >= r]
        if pend.size == 0:
            break
        j = f[pend] + r
        if dl >= 0:
            over = j > dl
            if over.any():
                ud = pend[over]
                x[ud], xpx[ud], kind[ud] = dl, C[dl], EX_DELIST
                pend, j = pend[~over], j[~over]
                if pend.size == 0:
                    break
        sb = side[pend] == 1
        ex = np.where(sb, H[j] >= thr_x[pend], L[j] <= thr_x[pend])
        if ex.any():
            ue = pend[ex]
            x[ue], xpx[ue], kind[ue] = j[ex], X[ue], EX_LIMIT
            pend = pend[~ex]
    excl = np.zeros(nu, np.int8)        # 0 ok, 1 lo dai, 2 khong co gia ket thuc
    if pend.size:
        jt = f[pend] + T[pend]
        jv = G["nv"][jt]
        if dl >= 0:
            dd_ = jv > dl
            ud = pend[dd_]
            x[ud], xpx[ud], kind[ud] = dl, C[dl], EX_DELIST
            pend, jv = pend[~dd_], jv[~dd_]
        bad = jv >= n
        excl[pend[bad]] = 2
        pend, jv = pend[~bad], jv[~bad]
        x[pend], xpx[pend], kind[pend] = jv, C[jv], EX_TIMEOUT
    # ---- loai don vi co lo dai trong doi song [t0-1, e]
    e_life = np.where(filled, x, t0 + W - 1)
    if dl >= 0:
        e_life = np.where(filled, e_life, np.minimum(e_life, dl))
    e_life = np.clip(e_life, 0, n - 1)
    lgc = G["lgc"]
    gap = (lgc[e_life + 1] - lgc[t0 - 1]) > 0
    excl[gap & (excl == 0)] = 1
    # ---- ke toan
    fm = FEE_MAKER[model]
    ratio = xpx / entry
    rate_exit = np.where(kind == EX_LIMIT, fm,
                         np.where(kind == EX_TIMEOUT, fm if not pess else FEE_TAKER, FEE_TAKER))
    fee = np.where(filled, fm + rate_exit * ratio, np.nan)
    if pess:
        srate = np.where(kind == EX_DELIST, DELIST_SLIP_PESS,
                         np.where((kind == EX_TIMEOUT) | (kind == EX_TAKER_BEYOND), slip, 0.0))
    else:
        srate = np.zeros(nu)
    slipc = np.where(filled, srate * ratio, np.nan)
    gross = np.where(filled, sidef * (xpx - entry) / entry, np.nan)
    fund = np.where(filled, 0.0, np.nan)
    if fund_s is not None and len(fund_s):
        fs = np.asarray(fund_s, np.int64)
        fr = np.asarray(fund_rate, np.float64)
        li = G["lv"][np.clip(fs - 1, 0, n - 1)]
        mk = np.where((fs >= 1) & (li >= 0), C[np.clip(li, 0, n - 1)], 0.0)
        v = np.where(np.isfinite(mk), fr * mk, 0.0)
        cs = np.r_[0.0, np.cumsum(v)]
        fi = np.nonzero(filled)[0]
        lo = np.searchsorted(fs, f[fi], side="right")
        hi = np.searchsorted(fs, x[fi], side="right")
        fund[fi] = -sidef[fi] * (cs[hi] - cs[lo]) / entry[fi]
    net = gross + fund - fee - slipc
    bp = 1e4
    return dict(t0=t0, m0=m0, Lb=Lb, Ls=Ls, filled=filled, side=side, side_in=side_in, f=f, entry=entry, X=X,
                x=x, xpx=xpx, kind=kind, excl=excl, gross=gross * bp, fee=fee * bp, slip=slipc * bp,
                fund=fund * bp, net=net * bp, n_maker=np.where(filled, 1 + (kind == EX_LIMIT), 0),
                dur=np.where(filled, x - f, -1))


# ---------------------------------------------------------------- dac trung theo ngay (ex-ante)
def infer_tick(prices):
    """tick = buoc lon nhat dang {1,2,5}x10^k <= hieu nho nhat giua cac gia khac nhau, sao cho >= 99,9 % gia la boi so.
    Tra NaN neu < 20 gia khac nhau."""
    p = np.asarray(prices, np.float64)
    p = p[np.isfinite(p) & (p > 0)]
    u = np.unique(p)
    if u.size < 20:
        return np.nan
    dmin = float(np.min(np.diff(u)))
    k = int(np.floor(np.log10(dmin)))
    cands = sorted({m * 10.0 ** kk for kk in range(k - 3, k + 2) for m in (1, 2, 5) if m * 10.0 ** kk <= dmin * (1 + 1e-6)},
                   reverse=True)
    for t in cands:
        q = u / t
        if np.mean(np.abs(q - np.round(q)) < 1e-3) >= 0.999:
            return float(t)
    return float(cands[-1])


def ar_spread(H, L, C):
    """Uoc spread tuong doi Abdi-Ranaldo (2017) tu nen 1m trong 1 ngay; cap phut lien tiep deu hop le."""
    lh, ll, lc = np.log(H), np.log(L), np.log(C)
    eta = 0.5 * (lh + ll)
    v = (lc[:-1] - eta[:-1]) * (lc[:-1] - eta[1:])
    v = v[np.isfinite(v)]
    if v.size < 100:
        return np.nan
    return float(np.sqrt(max(4.0 * v.mean(), 0.0)))


def daily_features(G, nday):
    """Luoi bat dau dung 00:00 UTC, n = nday*1440. Tra close cuoi ngay, so phut hop le, tick, spread AR."""
    C = G["C"][: nday * DAY_MIN].reshape(nday, DAY_MIN)
    H = G["H"][: nday * DAY_MIN].reshape(nday, DAY_MIN)
    L = G["L"][: nday * DAY_MIN].reshape(nday, DAY_MIN)
    O = G["O"][: nday * DAY_MIN].reshape(nday, DAY_MIN)
    nvalid = np.isfinite(C).sum(1)
    close = np.full(nday, np.nan)
    tick = np.full(nday, np.nan)
    spr = np.full(nday, np.nan)
    for i in range(nday):
        if nvalid[i] == 0:
            continue
        ci = C[i]
        fv = np.nonzero(np.isfinite(ci))[0]
        close[i] = ci[fv[-1]]
        tick[i] = infer_tick(np.concatenate([O[i], H[i], L[i], ci]))
        spr[i] = ar_spread(H[i], L[i], ci)
    return dict(close=close, nvalid=nvalid, tick=tick, spread=spr)


def sigma_exante(close, nwin=30, nmin=20):
    """sigma_1d cho ngay D = RMS (khong tru TB) cua log-return ngay cac ngay D-30..D-1; can >= 20 return hop le."""
    nday = close.size
    lr = np.r_[np.nan, np.diff(np.log(close))]
    ok = np.isfinite(lr)
    s2 = np.r_[0.0, np.cumsum(np.where(ok, lr * lr, 0.0))]
    cn = np.r_[0, np.cumsum(ok)]
    out = np.full(nday, np.nan)
    D = np.arange(nday)
    a = np.clip(D - nwin, 0, nday)
    cnt = cn[D] - cn[a]
    val = (s2[D] - s2[a]) / np.maximum(cnt, 1)
    good = (D >= nwin) & (cnt >= nmin)
    out[good] = np.sqrt(val[good])
    return out


# ---------------------------------------------------------------- feature ex-ante M3 (vector; ngay D chi dung du lieu <= cuoi D-1)
HOUR_MIN = 60


def hourly_close(G, nday):
    """close phut hop le cuoi cua moi gio UTC (NaN neu gio khong co phut hop le). Do dai nday*24."""
    C = G["C"][: nday * DAY_MIN]
    lv = G["lv"][: nday * DAY_MIN]
    end = np.arange(1, nday * 24 + 1) * HOUR_MIN - 1
    li = lv[end]
    start = end - HOUR_MIN + 1
    ok = li >= start
    return np.where(ok, C[np.clip(li, 0, None)], np.nan)


def daily_ohlc(G, nday):
    a = {k: G[k][: nday * DAY_MIN].reshape(nday, DAY_MIN) for k in ("O", "H", "L", "C")}
    fin = np.isfinite(a["C"])
    has = fin.any(1)
    fi = np.argmax(fin, 1)
    la = DAY_MIN - 1 - np.argmax(fin[:, ::-1], 1)
    r = np.arange(nday)
    with np.errstate(all="ignore"):
        o = np.where(has, a["O"][r, fi], np.nan)
        c = np.where(has, a["C"][r, la], np.nan)
        h = np.where(has, np.nanmax(np.where(fin, a["H"], -np.inf), 1), np.nan)
        lo = np.where(has, np.nanmin(np.where(fin, a["L"], np.inf), 1), np.nan)
    return o, h, lo, c


def er30(hc, nday, nwin=30, nmin=600):
    """ER30(D) = |C_cuoi - C_dau| / tong |C_h - C_{h-1}| tren close gio hop le trong [D-30 00:00, D 00:00);
    can >= 600 close gio hop le; tong = 0 -> NaN."""
    vi = np.nonzero(np.isfinite(hc))[0]
    vals = hc[vi]
    out = np.full(nday, np.nan)
    if vi.size < 2:
        return out
    absd = np.r_[0.0, np.abs(np.diff(vals))]
    cs = np.cumsum(absd)
    D = np.arange(nday)
    a = np.searchsorted(vi, (D - nwin) * 24)
    b = np.searchsorted(vi, D * 24)
    cnt = b - a
    good = (D >= nwin) & (cnt >= nmin)
    a2, b2 = a[good], b[good] - 1
    tot = cs[b2] - cs[a2]
    num = np.abs(vals[b2] - vals[a2])
    with np.errstate(all="ignore"):
        out[good] = np.where(tot > 0, num / tot, np.nan)
    return out


def sma20(dc, n=20, nmin=18):
    ok = np.isfinite(dc)
    cs = np.r_[0.0, np.cumsum(np.where(ok, dc, 0.0))]
    cn = np.r_[0, np.cumsum(ok)]
    d = np.arange(dc.size)
    a = np.clip(d - n + 1, 0, None)
    cnt = cn[d + 1] - cn[a]
    out = np.full(dc.size, np.nan)
    g = (d >= n - 1) & (cnt >= nmin)
    out[g] = (cs[d + 1] - cs[a])[g] / cnt[g]
    return out


def up_down(dc):
    """UP(D) = C(D-1) > SMA20(D-1) VA SMA20(D-1) > SMA20(D-6); DOWN doi xung. Tra (UP, DOWN) bool theo D."""
    s = sma20(dc)
    n = dc.size
    up = np.zeros(n, bool)
    dn = np.zeros(n, bool)
    D = np.arange(7, n)
    c1, s1, s6 = dc[D - 1], s[D - 1], s[D - 6]
    with np.errstate(invalid="ignore"):
        up[D] = (c1 > s1) & (s1 > s6)
        dn[D] = (c1 < s1) & (s1 < s6)
    return up, dn


def beta_btc(dc_sym, dc_btc, nwin=30, nmin=20):
    """beta(D) = he so OLS (co intercept) log-return ngay sym theo BTC tren cac ngay D-30..D-1 (cap ca hai huu han),
    can >= 20 cap; kep [0, 3]; thieu -> 1."""
    ry = np.r_[np.nan, np.diff(np.log(dc_sym))]
    rx = np.r_[np.nan, np.diff(np.log(dc_btc))]
    ok = np.isfinite(rx) & np.isfinite(ry)
    x, y = np.where(ok, rx, 0.0), np.where(ok, ry, 0.0)
    c = [np.r_[0.0, np.cumsum(v)] for v in (ok.astype(float), x, y, x * x, x * y)]
    n = dc_sym.size
    D = np.arange(n)
    a = np.clip(D - nwin, 0, None)
    s = [cc[D] - cc[a] for cc in c]
    cnt, sx, sy, sxx, sxy = s
    with np.errstate(all="ignore"):
        vx = sxx - sx * sx / np.maximum(cnt, 1)
        cv = sxy - sx * sy / np.maximum(cnt, 1)
        b = np.where((cnt >= nmin) & (D >= nwin) & (vx > 0), cv / vx, 1.0)
    return np.clip(b, 0.0, 3.0)


def f3_funding(ts_ms, rate, interval_h, nday, t_start_ms):
    """F3(D) = TB rate x (8/interval_h) cac moc ts trong [D - 3 ngay, D). Khong co moc -> NaN (coi nhu qua loc)."""
    out = np.full(nday, np.nan)
    if ts_ms is None or len(ts_ms) == 0:
        return out
    ts = np.asarray(ts_ms, np.int64)
    v = np.asarray(rate, float) * 8.0 / np.asarray(interval_h, float)
    o = np.argsort(ts, kind="stable")
    ts, v = ts[o], v[o]
    cs = np.r_[0.0, np.cumsum(v)]
    D = np.arange(nday)
    dstart = t_start_ms + D * 86400000
    a = np.searchsorted(ts, dstart - 3 * 86400000, "left")
    b = np.searchsorted(ts, dstart, "left")
    cnt = b - a
    with np.errstate(all="ignore"):
        out = np.where(cnt > 0, (cs[b] - cs[a]) / np.maximum(cnt, 1), np.nan)
    return out


def adx14(o, h, l_, c, n=14):
    """ADX14 Wilder tren nen ngay (bo ngay khong co du lieu, noi ngay hop le ke nhau). Tra ADX tai ngay D = gia tri tai
    ngay hop le cuoi <= D-1 (NaN neu chua du)."""
    nday = c.size
    vi = np.nonzero(np.isfinite(c) & np.isfinite(h) & np.isfinite(l_))[0]
    adx_at = np.full(nday, np.nan)
    if vi.size < 2 * n:
        return np.full(nday, np.nan)
    H, Lo, Cc = h[vi], l_[vi], c[vi]
    tr = np.maximum(H[1:] - Lo[1:], np.maximum(np.abs(H[1:] - Cc[:-1]), np.abs(Lo[1:] - Cc[:-1])))
    up = H[1:] - H[:-1]
    dn = Lo[:-1] - Lo[1:]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    m = tr.size
    atr = np.full(m, np.nan); sp = atr.copy(); sm = atr.copy()
    atr[n - 1], sp[n - 1], sm[n - 1] = tr[:n].sum(), pdm[:n].sum(), mdm[:n].sum()
    for i in range(n, m):
        atr[i] = atr[i - 1] - atr[i - 1] / n + tr[i]
        sp[i] = sp[i - 1] - sp[i - 1] / n + pdm[i]
        sm[i] = sm[i - 1] - sm[i - 1] / n + mdm[i]
    with np.errstate(all="ignore"):
        pdi, mdi = 100 * sp / atr, 100 * sm / atr
        dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    adx = np.full(m, np.nan)
    if m >= 2 * n - 1:
        adx[2 * n - 2] = np.nanmean(dx[n - 1:2 * n - 1])
        for i in range(2 * n - 1, m):
            adx[i] = (adx[i - 1] * (n - 1) + dx[i]) / n
    val_day = vi[1:]                      # adx[i] thuoc ngay vi[i+1]
    arr = np.full(nday, np.nan)
    arr[val_day] = adx
    # ADX tai D = gia tri cua ngay hop le cuoi <= D-1
    last = np.maximum.accumulate(np.where(np.isfinite(arr), np.arange(nday), -1))
    D = np.arange(1, nday)
    li = last[D - 1]
    adx_at[D] = np.where(li >= 0, arr[np.clip(li, 0, None)], np.nan)
    return adx_at


def xs_percentile(values_by_sym, elig_by_sym, q):
    """Phan vi cat ngang theo ngay (numpy 'linear') tren cac symbol hop le co gia tri huu han. Tra mang theo ngay."""
    syms = sorted(values_by_sym)
    V = np.stack([values_by_sym[s] for s in syms])
    E = np.stack([elig_by_sym[s] for s in syms])
    M = np.where(E & np.isfinite(V), V, np.nan)
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return np.nanpercentile(M, q, axis=0)
