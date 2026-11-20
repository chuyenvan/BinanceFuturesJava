"""kref.py - CAI DAT DOC LAP thu hai (python thuan, tung don vi, tung phut) cua don vi luoi Giai doan 1.
Viet lai tu van ban dac ta prereg (muc 4), KHONG dung code/ham cua klite. Dung de doi chieu tung don vi.
Bars: list O,H,L,C (None = phut khong hop le). Moi gia tri tra ve tinh bps notional luc vao.
"""
import math

MAKER = {"OPT": 0.0002, "PESS": 0.0004}
TAKER = 0.0005
DELIST_PEN = 0.005
GAP_MAX = 60


def fl(p, t):
    return math.floor(p / t + 1e-7) * t


def ce(p, t):
    return math.ceil(p / t - 1e-7) * t


def ok(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def simulate_unit(O, H, L, C, t0, d, W, T, tick, slip, model, side_in, funding=(), delist=-1):
    """Don vi MOT BEN: side_in = +1 (1 lenh mua tai L_b) hoac -1 (1 lenh ban tai L_s), khong OCO.
    funding: list (phut_moc, rate). delist: chi so phut hop le cuoi (neu delist) hoac -1.
    Tra dict hoac None neu don vi khong khop. Truong 'excluded' True neu lo > 60 phut trong doi don vi."""
    P = model == "PESS"
    n = len(C)

    def val(i):
        if delist >= 0 and i > delist:
            return False
        return ok(C[i])

    m0 = C[t0 - 1]
    lb = fl(m0 * (1 - d), tick)
    ls = ce(m0 * (1 + d), tick)
    tol = 0.01 * tick
    pen = tick if P else 0.0
    side = 0
    fmin = None
    for i in range(t0, t0 + W):
        if delist >= 0 and i > delist:
            break
        if not val(i):
            continue
        if side_in == 1 and L[i] <= lb - pen + tol:
            fmin, side = i, 1
            break
        if side_in == -1 and H[i] >= ls + pen - tol:
            fmin, side = i, -1
            break

    def has_long_gap(a, b):
        """Co phut khong hop le nao trong [a, b] thuoc mot chuoi lo lien tiep dai > 60 phut (khong tinh sau delist)."""
        for i in range(a, b + 1):
            if delist >= 0 and i > delist:
                break
            if val(i):
                continue
            lo = i
            while lo - 1 >= 0 and not val(lo - 1):
                lo -= 1
            hi = i
            while hi + 1 < n and not val(hi + 1) and not (delist >= 0 and hi + 1 > delist):
                hi += 1
            if hi - lo + 1 > GAP_MAX:
                return True
        return False

    if fmin is None:
        end = t0 + W - 1
        if delist >= 0:
            end = min(end, delist)
        return dict(filled=False, excluded=has_long_gap(t0 - 1, end))
    f = fmin
    entry = lb if side == 1 else ls
    X = ce(lb * (1 + d), tick) if side == 1 else fl(ls * (1 - d), tick)
    kind = None
    xi = None
    xp = None
    if P and ((side == 1 and C[f] >= X - tol) or (side == -1 and C[f] <= X + tol)):
        if delist >= 0 and f >= delist:
            kind, xi, xp = "delist", delist, C[delist]
        else:
            kind, xi, xp = "taker_beyond", f + 1, X
    else:
        start = f + 1 if P else f
        for i in range(start, f + T + 1):
            if delist >= 0 and i > delist:
                kind, xi, xp = "delist", delist, C[delist]
                break
            if not val(i):
                continue
            if side == 1 and H[i] >= X + pen - tol:
                kind, xi, xp = "limit", i, X
                break
            if side == -1 and L[i] <= X - pen + tol:
                kind, xi, xp = "limit", i, X
                break
        if kind is None:
            i = f + T
            while i < n and not val(i):
                if delist >= 0 and i > delist:
                    break
                i += 1
            if delist >= 0 and i > delist:
                kind, xi, xp = "delist", delist, C[delist]
            else:
                kind, xi, xp = "timeout", i, C[i]
    fm = MAKER[model]
    q = xp / entry
    if kind == "limit":
        fx = fm
    elif kind == "timeout":
        fx = TAKER if P else fm
    else:
        fx = TAKER
    fee = fm + fx * q
    if not P:
        sl = 0.0
    elif kind == "delist":
        sl = DELIST_PEN * q
    elif kind in ("timeout", "taker_beyond"):
        sl = slip * q
    else:
        sl = 0.0
    gross = side * (xp - entry) / entry
    fu = 0.0
    for (s, rate) in funding:
        if f < s <= xi:
            k = s - 1
            while k >= 0 and not val(k):
                k -= 1
            fu += -side * rate * C[k] / entry
    net = gross + fu - fee - sl
    return dict(filled=True, excluded=has_long_gap(t0 - 1, xi), side=side, f=f, x=xi, kind=kind, entry=entry, X=X,
                exit_px=xp, gross=gross * 1e4, fee=fee * 1e4, slip=sl * 1e4, fund=fu * 1e4, net=net * 1e4)


def ref_tick(prices):
    """Tick doc lap: thu {1,2,5}x10^k tu lon xuong nho (10^1 .. 10^-12), lay buoc lon nhat ma >= 99,9 % gia la boi so
    VA khong lon hon hieu nho nhat giua 2 gia khac nhau."""
    ps = sorted(set(p for p in prices if ok(p) and p > 0))
    if len(ps) < 20:
        return float("nan")
    dmin = min(b - a for a, b in zip(ps[:-1], ps[1:]))
    for e in range(1, -13, -1):
        for m in (5, 2, 1):
            t = m * 10.0 ** e
            if t > dmin * (1 + 1e-6):
                continue
            good = sum(1 for p in ps if abs(p / t - round(p / t)) < 1e-3)
            if good >= 0.999 * len(ps):
                return t
    return float("nan")


def ref_sigma(daily_close, D):
    rs = []
    for i in range(D - 30, D):
        a, b = daily_close[i - 1], daily_close[i]
        if ok(a) and ok(b) and i - 1 >= 0:
            rs.append(math.log(b / a))
    if len(rs) < 20:
        return float("nan")
    return math.sqrt(sum(r * r for r in rs) / len(rs))


# ------------------------------------------------------------------ feature M3 (python thuan, doc lap voi klite)
def ref_hourly_close(C, h):
    """close phut hop le cuoi cua gio h (C: list theo phut, None = khong hop le)."""
    for m in range(h * 60 + 59, h * 60 - 1, -1):
        if m < len(C) and ok(C[m]):
            return C[m]
    return None


def ref_er30(hourly, D):
    seq = [v for v in hourly[(D - 30) * 24: D * 24] if ok(v)]
    if D < 30 or len(seq) < 600:
        return float("nan")
    tot = sum(abs(b - a) for a, b in zip(seq[:-1], seq[1:]))
    if tot == 0:
        return float("nan")
    return abs(seq[-1] - seq[0]) / tot


def ref_sma20(dc, d):
    if d < 19:
        return float("nan")
    v = [x for x in dc[d - 19: d + 1] if ok(x)]
    return sum(v) / len(v) if len(v) >= 18 else float("nan")


def ref_updown(dc, D):
    if D < 7:
        return False, False
    c1, s1, s6 = dc[D - 1], ref_sma20(dc, D - 1), ref_sma20(dc, D - 6)
    if not (ok(c1) and ok(s1) and ok(s6)):
        return False, False
    return (c1 > s1 and s1 > s6), (c1 < s1 and s1 < s6)


def ref_beta(dc_s, dc_b, D):
    xs, ys = [], []
    for i in range(D - 30, D):
        if i < 1:
            continue
        a1, b1, a0, b0 = dc_s[i], dc_b[i], dc_s[i - 1], dc_b[i - 1]
        if ok(a1) and ok(b1) and ok(a0) and ok(b0):
            ys.append(math.log(a1 / a0))
            xs.append(math.log(b1 / b0))
    if D < 30 or len(xs) < 20:
        return 1.0
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    if vx <= 0:
        return 1.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / vx
    return min(max(b, 0.0), 3.0)


def ref_f3(events, day_start_ms):
    """events: list (ts_ms, rate, interval_h)."""
    v = [r * 8.0 / ih for (t, r, ih) in events if day_start_ms - 3 * 86400000 <= t < day_start_ms]
    return sum(v) / len(v) if v else float("nan")


def ref_adx14(dohlc, D, n=14):
    """dohlc: list (o,h,l,c) theo ngay (None neu khong co). ADX Wilder tai ngay hop le cuoi <= D-1."""
    bars = [(i, b) for i, b in enumerate(dohlc[:D]) if b is not None]
    if len(bars) < 2 * n:
        return float("nan")
    trs, pdms, mdms = [], [], []
    for (i0, p), (i1, q) in zip(bars[:-1], bars[1:]):
        trs.append(max(q[1] - q[2], abs(q[1] - p[3]), abs(q[2] - p[3])))
        up, dn = q[1] - p[1], p[2] - q[2]
        pdms.append(up if (up > dn and up > 0) else 0.0)
        mdms.append(dn if (dn > up and dn > 0) else 0.0)
    atr, sp, sm = sum(trs[:n]), sum(pdms[:n]), sum(mdms[:n])
    dxs = []

    def dx(a, p, m):
        pdi, mdi = 100 * p / a, 100 * m / a
        return 100 * abs(pdi - mdi) / (pdi + mdi) if (pdi + mdi) > 0 else float("nan")
    dxs.append(dx(atr, sp, sm))
    for i in range(n, len(trs)):
        atr = atr - atr / n + trs[i]
        sp = sp - sp / n + pdms[i]
        sm = sm - sm / n + mdms[i]
        dxs.append(dx(atr, sp, sm))
    if len(dxs) < n:
        return float("nan")
    first = [x for x in dxs[:n] if x == x]
    adx = sum(first) / len(first)
    for x in dxs[n:]:
        adx = (adx * (n - 1) + x) / n
    return adx


def ref_percentile(vals, q):
    """phan vi 'linear' (giong numpy mac dinh) - cai dat doc lap."""
    v = sorted(x for x in vals if ok(x))
    if not v:
        return float("nan")
    pos = (len(v) - 1) * q / 100.0
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def ref_masks(f, side, sym, mkt_sym):
    """f: dict feature cua don vi (er, er_p33, sig, sig_p10, sig_p90, age, tier, f3, up, dn, up_b, dn_b, condA, condB).
    Tra tap ten tap (set) don vi thuoc vao (khong gom G-N)."""
    out = set()
    fpass = (not ok(f["f3"])) or ((f["f3"] <= 0.0005) if side == 1 else (f["f3"] >= -0.0001))
    tl = 1e-9
    erlow = ok(f["er"]) and ok(f["er_p33"]) and f["er"] <= f["er_p33"] * (1 + tl)
    if erlow:
        out.add("ER_LOW")
        if (ok(f["sig"]) and f["sig_p10"] * (1 - tl) <= f["sig"] <= f["sig_p90"] * (1 + tl) and f["age"] >= 90
                and f["tier"] in (1, 2) and fpass):
            out.add("IDEAL_N")
    if f["condA"]:
        out.add("COND_A")
    if f["condB"]:
        out.add("COND_B")
    if sym != mkt_sym and f["age"] >= 90 and fpass:
        if side == 1 and f["up"] and f["up_b"]:
            out.add("TREND_BUY")
        if side == -1 and f["dn"] and f["dn_b"]:
            out.add("TREND_SELL")
    return out
