"""klite3.py - loi mo phong DON VI LENH SAU MOT BEN tren nen 1m (Giai doan S3 "WICK", PREREG_GRIDV2_S3).

Copy tu klite.py cua S1 (sha 196f4584...) roi tham so hoa theo S3_MASTER_DECISIONS_1120 muc S3-2:
- lenh vao song W = 60 phut (KHONG phai W = T), muc d = c x sigma_1d voi c in {1,0; 1,5; 2,5};
- thoat limit khi hoi NUA quang duong: BUY khop L -> X = ceil_tick(L(1 + 0,5 d)); SELL khop L -> X = floor_tick(L(1 - 0,5 d));
- het han T in {240, 1440} phut sau phut khop (T co dinh theo phut, khong phu thuoc c).
Hai mo hinh khop: K_PESS GIONG HET S1; mo hinh lac quan = K_OPT3 (R3-1, audit A1 F1; khoa code "OPT"): vao bang CHAM nhu S1,
thoat CUNG PHUT khop CHI KHI close phut khop da vuot X (BUY close >= X, SELL close <= X), con lai thoat bang CHAM tu phut f+1;
het han close phut f+T phi maker. BO quy tac vong tron cung phut O->L->H cua K_OPT S1. Phi, truot, funding, delist, lo: nhu S1.
Numpy thuan. Kieu "lockstep": moi buoc r xu ly dong thoi moi don vi con cho.
Quy uoc: luoi phut LIEN TUC 1 symbol (chi so 0..n-1), phut khong hop le co gia NaN; don vi dat dau phut t0, m0 = close t0-1.
PnL theo phan so notional luc vao, xuat bps.
"""
import numpy as np

MIN_MS = 60000
DAY_MIN = 1440
FEE_MAKER = {"OPT": 2e-4, "PESS": 4e-4}      # maker VIP0 0,02 %; stress 0,04 % cho PESS
FEE_TAKER = 5e-4                              # taker VIP0 0,05 %
DELIST_SLIP_PESS = 50e-4                      # delist: truot bao thu 50 bps
SLIP_TIER_FLOOR = {1: 2e-4, 2: 5e-4, 3: 10e-4}  # san truot taker PESS theo tier
LONG_GAP_MIN = 60                             # lo > 60 phut trong doi don vi => loai don vi
MIN_D_TICKS = 4                               # d x m0 < 4 tick => khong dat
TOL_TICK = 0.01                               # dung sai so sanh gia = 1 % tick
# ---- hang so S3 (S3-2); runner3 assert bang gia tri prereg
W_ENTRY = 60                                  # lenh vao song 60 phut
EXIT_FRAC = 0.5                               # thoat limit tai nua quang duong d
C_LIST = (1.0, 1.5, 2.5)                      # d = c x sigma_1d
T_LIST = (240, 1440)                          # het han T phut sau phut khop
EX_NONE, EX_LIMIT, EX_TIMEOUT, EX_DELIST, EX_TAKER_BEYOND = 0, 1, 2, 3, 4
EXIT_NAMES = {0: "none", 1: "limit", 2: "timeout", 3: "delist", 4: "taker_beyond"}


def floor_tick(p, tick):
    return np.floor(np.asarray(p) / tick + 1e-7) * tick


def ceil_tick(p, tick):
    return np.ceil(np.asarray(p) / tick - 1e-7) * tick


def levels(m0, d, tick, xfrac=EXIT_FRAC):
    """Muc vao / thoat ex-ante cua 2 ben: (Lb, Xb, Ls, Xs). Dung chung cho runner (loc gia <= 0) va run_units."""
    m0 = np.asarray(m0, np.float64)
    d = np.asarray(d, np.float64)
    Lb = floor_tick(m0 * (1.0 - d), tick)
    Ls = ceil_tick(m0 * (1.0 + d), tick)
    Xb = ceil_tick(Lb * (1.0 + xfrac * d), tick)
    Xs = floor_tick(Ls * (1.0 - xfrac * d), tick)
    return Lb, Xb, Ls, Xs


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


def run_units(G, t0, d, W, T, tick, slip, model, side_in, fund_s=None, fund_rate=None, xfrac=EXIT_FRAC):
    """Mo phong don vi MOT BEN S3: BUY = 1 lenh mua tai L_b = floor_tick(m0(1-d)), SELL = 1 lenh ban tai L_s = ceil_tick(m0(1+d)),
    song W phut (phut t0..t0+W-1); khop -> lenh thoat limit X (nua quang duong, xfrac), het han close phut f+T.
    side_in: +1 / -1 theo don vi. t0, W, T: int (phut). d: buoc tuong doi. tick: tick tuyet doi. slip: truot taker PESS.
    fund_s: chi so phut moc funding (tang dan); fund_rate: rate tai moc. Tra dict mang theo don vi."""
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
    Lb, Xb, Ls, Xs = levels(m0, d, tick, xfrac)
    side_in = np.broadcast_to(np.asarray(side_in, np.int8), (nu,)).copy()
    assert np.all((side_in == 1) | (side_in == -1))
    assert np.all(np.where(side_in == 1, (Lb > 0) & (Xb > Lb), (Xs > 0) & (Xs < Ls))), "muc gia <= 0 (runner phai loc)"
    tol = TOL_TICK * tick
    eps = tick if pess else np.zeros(nu)
    thr_b = Lb - eps + tol
    thr_s = Ls + eps - tol
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
    X = np.where(side == 1, Xb, np.where(side == -1, Xs, np.nan))
    x = np.full(nu, -1, np.int64)
    xpx = np.full(nu, np.nan)
    kind = np.zeros(nu, np.int8)
    fu = np.nonzero(filled)[0]
    r0 = 1                                       # R3-1: ca K_OPT3 va K_PESS xet lenh thoat tu phut f+1 (sau buoc cung phut)
    if (not pess) and fu.size:
        # K_OPT3: close phut khop da vuot X ve phia co loi => duong gia tu muc khop toi close chac chan qua X: thoat X tai phut f
        cf = C[f[fu]]
        same = np.where(side[fu] == 1, cf >= X[fu] - tol[fu], cf <= X[fu] + tol[fu])
        us = fu[same]
        x[us], xpx[us], kind[us] = f[us], X[us], EX_LIMIT
        fu = fu[~same]
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


# ---------------------------------------------------------------- dac trung theo ngay (ex-ante) - GIONG HET klite.py S1
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


def er30(hc, nday, nwin=30, nmin=600):
    """ER30(D) (chi dung cho doi chieu pass1 = pass2 o V3; S3 khong dung ER lam mat na)."""
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


def beta_btc(dc_sym, dc_btc, nwin=30, nmin=20):
    """beta(D) = he so OLS (co intercept) log-return ngay sym theo BTC tren cac ngay D-30..D-1 (cap ca hai huu han),
    can >= 20 cap; kep [0, 3]; thieu -> 1. (S3: chi dung cho net_h bao cao.)"""
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
