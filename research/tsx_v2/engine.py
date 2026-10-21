#!/usr/bin/env python3
"""TSX_V2 replay engine: so phan MOT cum (cac leg, gia von, qty tu printDone) theo phut Vision 1m, chep logic sim
SimulatorMarketLevelTicker1MStopLoss.startUpdateOldOrderTrading @a8690d46 (:1000-1110) + OrderTargetInfoTest
(updateStatusNew/updateTPSL/trailRate/accrueFundingMark) + TradeUtils.trailFromCap + Utils.calPriceTarget/normalizePrice.

Profile gqsf/tsx: RATE_PROFIT_STOP_MARKET 0.07, TS_GIVEBACK_RATIO 1.0, TS_MAX_GAP = TS_MAX_GAP_WEAK = 0.03, TS_PEAK=high,
BLOCK_INTRABAR_LOOKAHEAD=true, LOSER_TIME_STOP_HOURS 168, PRE_ARM_SL/COND_EXIT/TP tat, FUNDING_MARK=true (scale 1),
RATE_FEE 0.000982 + SLIPPAGE 0.000067 x2 tren notional vao.
Thu tu trong 1 tick (sim): cap nhat gia + funding -> time-stop (chi khi chua arm) -> arm/trailing; leg DCA tao SAU update
cung tick (merge: entry TB float32, priceSL=null, funding mang theo). Leg sau thoi diem thoat cua run nguon KHONG biet
=> sau do trang thai cum DONG BANG (khong DCA moi) - chi xay ra khi bien the giu LAU HON run nguon.
"""
from decimal import Decimal, ROUND_FLOOR

import numpy as np

f32 = np.float32
MARK = 168 * 60 + 1
ARM = f32(0.07)
ONE_ARM = f32(1) + ARM
GAP = f32(0.03)
STEP = f32(0.005)
FEE = 0.000982 + 2 * 0.000067


def jstr(x):
    return np.format_float_positional(f32(x), unique=True, trim="-")


def norm_price(p, tick):
    """ClientSingleton.normalizePrice: floor(price/tick)*tick bang BigDecimal tren chuoi float."""
    if tick is None:
        return f32(p)
    q = (Decimal(jstr(p)) / tick).to_integral_value(rounding=ROUND_FLOOR)
    return f32(float(q * tick))


def trail_rate(rate):
    """TradeUtils.trailFromCap (float32): rate - min(rate*1.0, 0.03), Math.round(rate/0.005)*0.005."""
    r = rate.astype(np.float32)
    g = np.minimum(r * f32(1.0), GAP).astype(np.float32)
    x = (r - g).astype(np.float32)
    k = np.floor((x / STEP).astype(np.float32) + f32(0.5)).astype(np.int64)
    return (k.astype(np.float32) * STEP).astype(np.float32)


def sl_price(E, rate, tick, cache):
    """priceSL = normalize(E - (-trail)*E)."""
    tr = trail_rate(rate)
    raw = (E - ((-tr).astype(np.float32) * E).astype(np.float32)).astype(np.float32)
    out = np.empty(len(raw), np.float32)
    for i, v in enumerate(raw):
        kv = float(v)
        if kv not in cache:
            cache[kv] = norm_price(v, tick)
        out[i] = cache[kv]
    return out


class Win:
    """du lieu 1 cua so (sym, t0): chi cac tick CO nen (sim chi update khi ticker != null)."""

    def __init__(self, arr, t0_ms, fund, tick):
        c = arr[:, 3]
        self.vj = np.nonzero(np.isfinite(c))[0]
        self.vj = self.vj[self.vj >= 1]
        self.O, self.H, self.L, self.C = (arr[self.vj, i].astype(np.float32) for i in range(4))
        self.t0 = int(t0_ms)
        self.day = (self.t0 + self.vj.astype(np.int64) * 60000) // 86400000
        self.tick = tick
        self.cut_px = np.minimum(self.O, self.C)
        # funding: moc settle k (ms) > t0 duoc cong o tick dau tien co t >= k
        fts, frt = fund
        tms = self.t0 + self.vj.astype(np.int64) * 60000
        if len(fts):
            pos = np.searchsorted(tms, fts, side="left")
            ok = pos < len(tms)
            self.f_pos, self.f_rate = pos[ok], frt[ok]
        else:
            self.f_pos, self.f_rate = np.zeros(0, np.int64), np.zeros(0)
        self.slc = {}


def merged(legs):
    m, q = f32(0), f32(0)
    for _, e, qq in legs:
        m = f32(m + f32(f32(e) * f32(qq)))
        q = f32(q + f32(qq))
    return f32(m / q), q


def replay(w, legs, dayset=None, cap_j=None, eligible=True, all_days=False, want_path=False):
    """legs: [(j, entry, qty)] (j phut tu t0, leg 0 j=0). Luat time-stop:
       P0: dayset None & not all_days -> cat o tick dau tien tuoi > 168h.
       Bien the: hoan khi eligible & j <= cap_j & (all_days | ngay UTC thuoc dayset).
    Tra dict(st, j, tp, pnl, fund, deferred, armed_pre, open, [path])."""
    vj = w.vj
    n = len(vj)
    if n == 0:
        return dict(st="NODATA", j=-1, tp=np.nan, pnl=np.nan, fund=np.nan, deferred=False, armed_pre=False, open=True)
    pend = sorted(legs[1:], key=lambda x: x[0])
    cur_legs = [legs[0]]
    E, Q = merged(cur_legs)
    if dayset is None and not all_days:
        dmask = np.zeros(n, bool)
    elif all_days:
        dmask = np.ones(n, bool)
    else:
        dmask = np.isin(w.day, dayset)
    if cap_j is None:
        cap_j = 0
    defer = dmask & (vj <= cap_j) & bool(eligible)
    cutm = (vj >= MARK) & ~defer
    mark_i = int(np.searchsorted(vj, MARK))
    # Q theo tick (cho funding): bac thang theo leg
    qcur = np.empty(n, np.float32)
    ecur = np.empty(n, np.float32)
    i0 = 0
    st = None
    ex = None
    tp = None
    armed_i = None
    seg_q = []
    while True:
        if pend:
            jd = pend[0][0]
            i1 = int(np.searchsorted(vj, jd, side="right"))  # cac tick <= jd xu ly voi trang thai cu
        else:
            i1 = n
        if i1 > i0:
            qcur[i0:i1] = Q
            ecur[i0:i1] = E
            H = w.H[i0:i1]
            thr = f32(E * ONE_ARM)
            arm = (H >= thr) & (((H - E).astype(np.float32) / E).astype(np.float32) > ARM)
            ev = cutm[i0:i1] | arm
            k = int(np.argmax(ev)) if ev.any() else -1
            if k >= 0:
                i = i0 + k
                if cutm[i]:
                    st, ex, tp = "STOP_LOSS_DONE", i, f32(w.cut_px[i])
                else:
                    armed_i = i
                break
        if not pend:
            break
        cur_legs.append(pend.pop(0))
        E, Q = merged(cur_legs)
        i0 = max(i1, i0)
    if armed_i is not None:
        i = armed_i
        H = w.H[i:]
        rate = ((H - E).astype(np.float32) / E).astype(np.float32)
        cand = np.full(len(H), -np.inf, np.float32)
        okm = rate >= ARM
        okm[0] = True
        cand[okm] = sl_price(E, rate[okm], w.tick, w.slc)
        slc = np.maximum.accumulate(cand)
        reset = np.zeros(len(H), bool)
        reset[0] = True
        reset[1:] = cand[1:] > slc[:-1]
        Lw, Cw = w.L[i:], w.C[i:]
        trig = np.zeros(len(H), bool)
        trig[1:] = (Lw[1:] <= slc[:-1]) | (reset[:-1] & (Cw[:-1] <= slc[:-1]))
        if trig.any():
            p = int(np.argmax(trig))
            ex = i + p
            sl = slc[p - 1]
            tp = f32(min(sl, w.O[ex]))
            st = "STOP_MARKET_DONE" if sl > E else "STOP_LOSS_DONE"
        qcur[i:] = Q
        ecur[i:] = E
    leg_after_arm = bool(armed_i is not None and any(lg[0] < (vj[ex] if ex is not None else 10 ** 9) for lg in pend))
    if ex is None:
        res = dict(st="OPEN", j=int(vj[-1]), tp=np.nan, pnl=np.nan, fund=np.nan, open=True)
    else:
        fm = w.f_pos <= ex
        fund = float(np.sum(w.f_rate[fm] * qcur[w.f_pos[fm]].astype(np.float64) * w.C[w.f_pos[fm]].astype(np.float64)))
        used = [lg for lg in legs if lg[0] < vj[ex]]
        pnl = sum(q * (float(tp) - e) - FEE * q * e for _, e, q in used) - fund
        res = dict(st=st, j=int(vj[ex]), tp=float(tp), pnl=float(pnl), fund=fund, open=False, n_legs=len(used))
    armed_pre = armed_i is not None and armed_i < mark_i
    res["armed_pre"] = bool(armed_pre)
    res["deferred"] = bool((not armed_pre) and mark_i < n and (ex is None or ex > mark_i) and defer[mark_i]
                           and (armed_i is None or armed_i >= mark_i))
    res["leg_after_arm"] = leg_after_arm
    res["mark_i"] = mark_i
    if want_path:
        res["qcur"], res["ecur"] = qcur, ecur
        res["ex_i"] = ex
    return res


def cut_values(w, legs, res, i_from, i_to):
    """gia tri PnL neu CAT tai tung tick i in [i_from, i_to] (gia min(open, close), funding tich luy toi tick)."""
    idx = np.arange(i_from, i_to + 1)
    if len(idx) == 0:
        return idx, np.zeros(0)
    qc = res["qcur"]
    fz = np.zeros(len(w.vj))
    if len(w.f_pos):
        np.add.at(fz, w.f_pos, w.f_rate * qc[w.f_pos].astype(np.float64) * w.C[w.f_pos].astype(np.float64))
    fc = np.cumsum(fz)
    px = w.cut_px[idx].astype(np.float64)
    val = np.zeros(len(idx))
    vjj = w.vj[idx]
    for j, e, q in legs:
        inc = vjj > j
        val += np.where(inc, q * (px - e) - FEE * q * e, 0.0)
    return idx, val - fc[idx]
