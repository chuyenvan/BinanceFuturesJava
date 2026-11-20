"""kref3.py - CAI DAT DOC LAP thu hai (python thuan, tung don vi, tung phut) cua don vi lenh sau MOT BEN S3.
Viet lai tu van ban dac ta (PREREG_GRIDV2_S3 muc 4-5; R3: mo hinh lac quan K_OPT3) theo kieu MAY TRANG THAI tren doi tuong Series (tien tinh do dai chuoi lo);
KHONG import klite3 / klite. Dung de doi chieu tung don vi (test) va V5 (du lieu doc lai tho).
Bars: list O,H,L,C (None / NaN = phut khong hop le). Gia tri tra ve: bps notional luc vao.
Gioi han doc lap (ghi nhan nhu S1 F11): dung chung quy uoc lam tron tick (+-1e-7) va dung sai 0,01 tick cua prereg.
"""
import math

MAKER = {"OPT": 0.0002, "PESS": 0.0004}
TAKER = 0.0005
DELIST_PEN = 0.005
GAP_MAX = 60
TOLF = 0.01


def _ok(v):
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def tick_floor(p, t):
    return math.floor(p / t + 1e-7) * t


def tick_ceil(p, t):
    return math.ceil(p / t - 1e-7) * t


class Series:
    """Chuoi phut 1 symbol: hop le = co close huu han VA (khong delist hoac phut <= phut hop le cuoi truoc delist).
    run_len[i] = do dai chuoi phut KHONG hop le lien tiep chua i (chi tinh phan <= delist); 0 neu i hop le / sau delist."""

    def __init__(self, O, H, L, C, delist=-1):
        self.O, self.H, self.L, self.C = O, H, L, C
        self.n = len(C)
        self.delist = delist
        self.valid = [(_ok(C[i]) and (delist < 0 or i <= delist)) for i in range(self.n)]
        lim = self.n if delist < 0 else min(self.n, delist + 1)
        self.run_len = [0] * self.n
        i = 0
        while i < lim:
            if self.valid[i]:
                i += 1
                continue
            j = i
            while j < lim and not self.valid[j]:
                j += 1
            for k in range(i, j):
                self.run_len[k] = j - i
            i = j

    def long_gap_between(self, a, b):
        """True neu co phut trong [a, b] thuoc chuoi lo > 60 phut."""
        a = max(a, 0)
        b = min(b, self.n - 1)
        for i in range(a, b + 1):
            if self.run_len[i] > GAP_MAX:
                return True
        return False

    def last_valid_before(self, s):
        k = s - 1
        while k >= 0 and not self.valid[k]:
            k -= 1
        return k


def simulate_unit(O, H, L, C, t0, d, W, T, tick, slip, model, side_in, funding=(), delist=-1, xfrac=0.5, series=None):
    """Don vi S3 MOT BEN. Tra dict: filled, excl (0 ok / 1 lo dai / 2 khong co gia ket thuc), va neu khop: side, f, x, kind,
    entry, X, exit_px, gross, fee, slip, fund, net (bps)."""
    S = series if series is not None else Series(O, H, L, C, delist)
    P = model == "PESS"
    m0 = S.C[t0 - 1]
    tol = TOLF * tick
    gap = tick if P else 0.0
    if side_in == 1:
        lvl = tick_floor(m0 * (1 - d), tick)
        tgt = tick_ceil(lvl * (1.0 + xfrac * d), tick)
    else:
        lvl = tick_ceil(m0 * (1 + d), tick)
        tgt = tick_floor(lvl * (1.0 - xfrac * d), tick)
    # ---- trang thai 1: CHO KHOP (phut t0 .. t0+W-1, dung o delist)
    f = None
    for i in range(t0, t0 + W):
        if delist >= 0 and i > delist:
            break
        if not S.valid[i]:
            continue
        crossed = (S.L[i] <= lvl - gap + tol) if side_in == 1 else (S.H[i] >= lvl + gap - tol)
        if crossed:
            f = i
            break
    if f is None:
        end = t0 + W - 1
        if delist >= 0:
            end = min(end, delist)
        return dict(filled=False, excl=1 if S.long_gap_between(t0 - 1, end) else 0)
    # ---- trang thai 2: DANG GIU
    state, xi, xp = None, None, None
    beyond = P and ((side_in == 1 and S.C[f] >= tgt - tol) or (side_in == -1 and S.C[f] <= tgt + tol))
    if beyond:
        if delist >= 0 and f >= delist:
            state, xi, xp = "delist", delist, S.C[delist]
        else:
            state, xi, xp = "taker_beyond", f + 1, tgt
    elif (not P) and ((side_in == 1 and S.C[f] >= tgt - tol) or (side_in == -1 and S.C[f] <= tgt + tol)):
        state, xi, xp = "limit", f, tgt                     # K_OPT3 (R3-1): close phut khop da vuot X -> thoat cung phut
    else:
        i = f + 1                                           # K_OPT3 va K_PESS: lenh thoat xet tu phut f+1
        while i <= f + T:
            if delist >= 0 and i > delist:
                state, xi, xp = "delist", delist, S.C[delist]
                break
            if S.valid[i]:
                hitx = (S.H[i] >= tgt + gap - tol) if side_in == 1 else (S.L[i] <= tgt - gap + tol)
                if hitx:
                    state, xi, xp = "limit", i, tgt
                    break
            i += 1
        if state is None:
            j = f + T
            while j < S.n and not S.valid[j] and not (delist >= 0 and j > delist):
                j += 1
            if delist >= 0 and j > delist:
                state, xi, xp = "delist", delist, S.C[delist]
            elif j >= S.n:
                return dict(filled=True, excl=2, side=side_in, f=f)
            else:
                state, xi, xp = "timeout", j, S.C[j]
    # ---- trang thai 3: KE TOAN
    fm = MAKER[model]
    q = xp / lvl
    exit_fee = {"limit": fm, "timeout": (TAKER if P else fm)}.get(state, TAKER)
    fee = fm + exit_fee * q
    sl = 0.0
    if P:
        if state == "delist":
            sl = DELIST_PEN * q
        elif state in ("timeout", "taker_beyond"):
            sl = slip * q
    gross = side_in * (xp - lvl) / lvl
    fu = 0.0
    for (s, rate) in funding:
        if f < s <= xi:
            k = S.last_valid_before(s)
            fu += -side_in * rate * S.C[k] / lvl
    net = gross + fu - fee - sl
    return dict(filled=True, excl=1 if S.long_gap_between(t0 - 1, xi) else 0, side=side_in, f=f, x=xi, kind=state,
                entry=lvl, X=tgt, exit_px=xp, gross=gross * 1e4, fee=fee * 1e4, slip=sl * 1e4, fund=fu * 1e4,
                net=net * 1e4)


# ------------------------------------------------------------------ feature (python thuan, doc lap voi klite3) - nhu kref S1
def ref_tick(prices):
    """Tick doc lap: thu {1,2,5}x10^k tu lon xuong nho (10^1 .. 10^-12), lay buoc lon nhat ma >= 99,9 % gia la boi so
    VA khong lon hon hieu nho nhat giua 2 gia khac nhau."""
    ps = sorted(set(p for p in prices if _ok(p) and p > 0))
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
        if _ok(a) and _ok(b) and i - 1 >= 0:
            rs.append(math.log(b / a))
    if len(rs) < 20:
        return float("nan")
    return math.sqrt(sum(r * r for r in rs) / len(rs))


def ref_beta(dc_s, dc_b, D):
    xs, ys = [], []
    for i in range(D - 30, D):
        if i < 1:
            continue
        a1, b1, a0, b0 = dc_s[i], dc_b[i], dc_s[i - 1], dc_b[i - 1]
        if _ok(a1) and _ok(b1) and _ok(a0) and _ok(b0):
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
