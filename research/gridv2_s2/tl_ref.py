"""tl_ref.py - cai dat THAM CHIEU doc lap (python thuan, vong lap tung giao dich THO, khong gom ms, khong numpy) cho
PREREG_GRIDV2_S2 muc 5. Viet lai tu van ban prereg, KHONG dung ham nao cua tl_engine.py. Cham; chi dung cho test va W5.

trades: list (transact_time_ms, agg_trade_id, price, is_buyer_maker) cua 1 symbol, MOI giao dich da tai (thu tu bat ky; ham
tu sap theo (time, id)). unit: dict t0, side, L, X, tick, W, T, slip, dl_end. Tra dict cung khoa voi tl_engine.OUT_COLS.
"""
import bisect

ONE_MIN = 60 * 1000
LATENCY = 250
MAX_QUIET = 60 * ONE_MIN
MAKER, MAKER_STRESS, TAKER = 0.0002, 0.0004, 0.0005
DELIST_SLIP = 0.0050


def _resting_buy_filled(price, buyer_is_maker, level, tick, kind):
    """Lenh MUA nghi tai level co bi giao dich nay khop khong."""
    eps = tick / 100.0
    if kind == "THROUGH":
        return price <= (level - tick) + eps
    if price < level - eps:
        return True
    return buyer_is_maker and price <= level + eps


def _resting_sell_filled(price, buyer_is_maker, level, tick, kind):
    """Lenh BAN nghi tai level co bi giao dich nay khop khong."""
    eps = tick / 100.0
    if kind == "THROUGH":
        return price >= (level + tick) - eps
    if price > level + eps:
        return True
    return (not buyer_is_maker) and price >= level - eps


def prepare(trades):
    tr = sorted(trades, key=lambda r: (r[0], r[1]))
    return tr, [r[0] for r in tr]


def ref_unit(prep, unit, kind, data_start, data_end, fund=()):
    tr, times = prep
    delay_in, delay_out = 0, LATENCY
    if kind == "THROUGH_LAT5S":                 # bien the chi bao cao: tre 5 s ca lenh vao lan lenh thoat
        kind, delay_in, delay_out = "THROUGH", 5000, 5000
    t0, side = unit["t0"], unit["side"]
    L, X, tick = unit["L"], unit["X"], unit["tick"]
    w_end = t0 + unit["W"] * ONE_MIN
    stop = data_end
    if unit["dl_end"] >= 0 and unit["dl_end"] < stop:
        stop = unit["dl_end"]
    res = dict(filled=0, excl=0, tf=-1, tx=-1, kind=0, xpx=float("nan"), gross=float("nan"), fee=float("nan"),
               fee_stress=float("nan"), slip=float("nan"), fund=float("nan"), net=float("nan"), net_stress=float("nan"),
               n_maker=0)
    i = bisect.bisect_left(times, t0 + delay_in)
    tf = None
    while i < len(tr):
        tt, _, px, bm = tr[i]
        if tt >= w_end or tt >= stop:
            break
        hit = (_resting_buy_filled(px, bm, L, tick, kind) if side == 1 else _resting_sell_filled(px, bm, L, tick, kind))
        if hit:
            tf = tt
            break
        i += 1
    if tf is None:
        life_end = min(w_end, stop)
    else:
        expiry = tf + unit["T"] * ONE_MIN
        out_px, out_t, how = None, None, None
        last_px = None
        j = i
        if kind == "THROUGH" and tf + delay_out < stop:
            # R-11: gia giao dich cuoi truoc thoi diem lenh thoat bat dau co hieu luc da vuot X it nhat 1 tick?
            before = [x for x in tr[i:bisect.bisect_left(times, tf + delay_out)]]
            p_ref = before[-1][2]
            eps = tick / 100.0
            if (side == 1 and p_ref >= X + tick - eps) or (side == -1 and p_ref <= X - tick + eps):
                out_px, out_t, how = X, tf + delay_out, 4
        while how is None and j < len(tr):
            tt, _, px, bm = tr[j]
            if tt >= stop or tt > expiry:
                break
            last_px = px
            if tt >= tf + delay_out:
                ex = (_resting_sell_filled(px, bm, X, tick, kind) if side == 1 else _resting_buy_filled(px, bm, X, tick, kind))
                if ex:
                    out_px, out_t, how = X, tt, 1
                    break
            j += 1
        if how is None:
            if unit["dl_end"] >= 0 and unit["dl_end"] <= expiry:
                how, out_t, out_px = 3, unit["dl_end"], last_px
            else:
                how, out_t, out_px = 2, expiry, last_px
        life_end = out_t
        if how == 1:
            fe, fes, sl = MAKER, MAKER_STRESS, 0.0
        elif how == 4:
            fe, fes, sl = TAKER, TAKER, 0.0
        elif how == 2:
            if kind == "THROUGH":
                fe, fes, sl = TAKER, TAKER, unit["slip"]
            else:
                fe, fes, sl = MAKER, MAKER_STRESS, 0.0
        else:
            fe, fes, sl = TAKER, TAKER, (DELIST_SLIP if kind == "THROUGH" else 0.0)
        rel = out_px / L
        g = side * (out_px - L) / L
        fsum = 0.0
        for (ft, fr) in fund:
            if tf < ft <= out_t:
                m = bisect.bisect_left(times, ft) - 1
                fsum += -side * fr * tr[m][2] / L
        f1 = MAKER + fe * rel
        f2 = MAKER_STRESS + fes * rel
        res.update(filled=1, tf=tf, tx=out_t, kind=how, xpx=out_px, gross=g * 1e4, fee=f1 * 1e4, fee_stress=f2 * 1e4,
                   slip=sl * rel * 1e4, fund=fsum * 1e4, net=(g + fsum - f1 - sl * rel) * 1e4,
                   net_stress=(g + fsum - f2 - sl * rel) * 1e4, n_maker=2 if how == 1 else 1)
    # lo du lieu: khoang lang > 60 phut (bien du lieu = moc ao) cat [t0, life_end]
    k = bisect.bisect_left(times, t0)
    prev = times[k - 1] if k > 0 else data_start
    while k < len(times) and times[k] < stop:
        cur = times[k]
        if cur - prev > MAX_QUIET and prev < life_end and cur > t0:
            res["excl"] = 1
            break
        if prev >= life_end:
            break
        prev = cur
        k += 1
    else:
        if stop - prev > MAX_QUIET and prev < life_end and stop > t0:
            res["excl"] = 1
    return res
