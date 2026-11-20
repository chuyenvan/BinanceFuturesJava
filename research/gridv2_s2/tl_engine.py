"""tl_engine.py - engine MUC GIAO DICH cho GRIDV2 S2 (PREREG_GRIDV2_S2), vector hoa theo mang numpy.

Dau vao: aggTrades Binance Vision USDT-M (transact_time ms, agg_trade_id, price, is_buyer_maker) cua 1 symbol, da sap theo
(transact_time, agg_trade_id) va GOM THEO MILLISECOND (collapse_ms): moi ms giu gia dau / cuoi / min / max, min gia cua giao dich
is_buyer_maker = True (ben BAN chu dong), max gia cua giao dich is_buyer_maker = False (ben MUA chu dong), so giao dich.
Gom theo ms la KHONG MAT THONG TIN cho moi quy tac duoi day (moi quy tac chi hoi "co giao dich nao trong ms thoa X"
hoac "gia giao dich cuoi <= moc").

Don vi (giu NGUYEN S1): BUY = 1 lenh mua limit tai L, SELL = 1 lenh ban limit tai L, dat tai dau phut t0, song W phut
(cua so vao [t0, t0 + W phut)); khop -> lenh thoat limit tai X co hieu luc tu tf + 250 ms; het han tai te = tf + T phut.
Hai mo hinh:
  THROUGH (chinh, bao thu): BUY khop khi co giao dich gia <= L - 1 tick; SELL khi gia >= L + 1 tick. Thoat (lenh doi ung tai X)
    khi co giao dich XUYEN X >= 1 tick. Het han: TAKER tai gia giao dich cuoi <= te, phi taker 0,05 % + truot s (= max(san tier,
    s_hat/2), do kernel su kien tinh y nhu S1). Delist: gia giao dich cuoi truoc moc delist, taker + truot 50 bps.
  TOUCH (lac quan co trinh tu that): BUY khop khi co giao dich gia < L (moi ben) HOAC gia <= L voi is_buyer_maker = True; SELL khi
    gia > L HOAC gia >= L voi is_buyer_maker = False. Thoat tuong tu (cham, dung ben chu dong). Het han: gia giao dich cuoi,
    phi maker, khong truot. Delist: taker, khong truot.
  (Dieu kien "gia vuot han muc = khop moi ben" bao dam THROUGH khop => TOUCH khop: xem PREREG_GRIDV2_S2 muc 5, diem lech DL-1.)
Phi maker 0,02 % moi chan maker (them net_stress voi maker 0,04 %). PnL = phan so notional luc vao, xuat bps (nhu klite S1).
Lo du lieu: khoang khong co giao dich > 60 phut giao [t0, ket thuc don vi] -> LOAI (excl = 1). Bien du lieu da tai (dau ngay D,
cuoi du lieu) coi nhu co giao dich ao (diem lech DL-4).
Funding: moc s tinh khi tf < s <= tx; tien = -side x rate x (gia giao dich cuoi < s) / gia vao.
"""
import logging
import numpy as np

log = logging.getLogger("tl_engine")
MS_MIN = 60000
LAT_MS = 250
GAP_MS = 3600000
SEAL_MS = 1767225600000            # 2026-01-01: khong co du lieu nao >= moc nay
DATA_START_MS = 1619827200000      # 2021-05-01 = chi so phut 0 cua S1
FEE_MAKER = 2e-4
FEE_MAKER_STRESS = 4e-4
FEE_TAKER = 5e-4
DELIST_SLIP_THROUGH = 50e-4
TOL_TICK = 0.01
EX_NONE, EX_LIMIT, EX_TIMEOUT, EX_DELIST, EX_TAKER_BEYOND = 0, 1, 2, 3, 4
MODELS = ("THROUGH", "TOUCH")
DIAG_MODELS = ("THROUGH_LAT5S",)        # CHI BAO CAO (khong vao luat): THROUGH, lenh vao co hieu luc tu t0 + 5 s, thoat tu tf + 5 s
RULES = {"THROUGH": ("THROUGH", 0, LAT_MS), "TOUCH": ("TOUCH", 0, LAT_MS), "THROUGH_LAT5S": ("THROUGH", 5000, 5000)}
OUT_COLS = ("filled", "excl", "tf", "tx", "kind", "xpx", "gross", "fee", "fee_stress", "slip", "fund", "net", "net_stress",
            "n_maker")


def collapse_ms(t, aid, p, ibm):
    """Sap (t, aid) roi gom theo ms. Tra dict mang theo ms (t tang ngat)."""
    t = np.asarray(t, np.int64)
    aid = np.asarray(aid, np.int64)
    p = np.asarray(p, np.float64)
    ibm = np.asarray(ibm, bool)
    if t.size == 0:
        z = np.zeros(0)
        return dict(t=np.zeros(0, np.int64), pf=z, pl=z, pmin=z, pmax=z, pmin_bm=z, pmax_nbm=z, n=np.zeros(0, np.int64))
    if int(t.max()) >= SEAL_MS:
        raise RuntimeError("giao dich >= 2026-01-01 - NIEM PHONG, DUNG")
    o = np.lexsort((aid, t))
    t, p, ibm = t[o], p[o], ibm[o]
    if not np.all(np.isfinite(p) & (p > 0)):
        raise RuntimeError("gia khong hop le trong aggTrades")
    st = np.r_[True, t[1:] != t[:-1]]
    gi = np.flatnonzero(st)
    en = np.r_[gi[1:], t.size]
    pmin_bm = np.minimum.reduceat(np.where(ibm, p, np.inf), gi)
    pmax_nbm = np.maximum.reduceat(np.where(~ibm, p, -np.inf), gi)
    return dict(t=t[gi], pf=p[gi], pl=p[en - 1], pmin=np.minimum.reduceat(p, gi), pmax=np.maximum.reduceat(p, gi),
                pmin_bm=np.where(np.isfinite(pmin_bm), pmin_bm, np.nan),
                pmax_nbm=np.where(np.isfinite(pmax_nbm), pmax_nbm, np.nan), n=(en - gi).astype(np.int64))


def slice_ms(MS, lo, hi):
    """Giu cac ms trong [lo, hi)."""
    a, b = np.searchsorted(MS["t"], [lo, hi], "left")
    return {k: v[a:b] for k, v in MS.items()}


def minute_bars(MS):
    """Nen 1 phut dung lai tu giao dich (phut = floor(transact_time / 60000) - chi so phut theo moc S1). Chi phut CO giao dich."""
    if MS["t"].size == 0:
        return dict(mi=np.zeros(0, np.int64), o=np.zeros(0), h=np.zeros(0), l=np.zeros(0), c=np.zeros(0), n=np.zeros(0, np.int64))
    m = (MS["t"] - DATA_START_MS) // MS_MIN
    st = np.r_[True, m[1:] != m[:-1]]
    gi = np.flatnonzero(st)
    en = np.r_[gi[1:], m.size]
    return dict(mi=m[gi], o=MS["pf"][gi], h=np.maximum.reduceat(MS["pmax"], gi), l=np.minimum.reduceat(MS["pmin"], gi),
                c=MS["pl"][en - 1], n=np.add.reduceat(MS["n"], gi))


def _hit_down(MS, a, b, level, tick, model):
    """Chi so dau tien trong [a, b) ma lenh MUA nghi tai 'level' bi khop. -1 neu khong."""
    if b <= a:
        return -1
    tol = TOL_TICK * tick
    if model == "THROUGH":
        m = MS["pmin"][a:b] <= level - tick + tol
    else:
        with np.errstate(invalid="ignore"):
            m = (MS["pmin"][a:b] < level - tol) | (MS["pmin_bm"][a:b] <= level + tol)
    k = np.flatnonzero(m)
    return int(a + k[0]) if k.size else -1


def _hit_up(MS, a, b, level, tick, model):
    """Chi so dau tien trong [a, b) ma lenh BAN nghi tai 'level' bi khop. -1 neu khong."""
    if b <= a:
        return -1
    tol = TOL_TICK * tick
    if model == "THROUGH":
        m = MS["pmax"][a:b] >= level + tick - tol
    else:
        with np.errstate(invalid="ignore"):
            m = (MS["pmax"][a:b] > level + tol) | (MS["pmax_nbm"][a:b] >= level - tol)
    k = np.flatnonzero(m)
    return int(a + k[0]) if k.size else -1


def gap_intervals(MS, data_start, lim_end):
    """Khoang khong co giao dich > 60 phut (bien du lieu = giao dich ao). Tra (a, b) mang."""
    tt = np.r_[np.int64(data_start), MS["t"][MS["t"] < lim_end], np.int64(lim_end)]
    dd = np.diff(tt)
    k = np.flatnonzero(dd > GAP_MS)
    return tt[k], tt[k + 1]


def simulate(MS, U, model, data_start, data_end, fund_t=None, fund_r=None):
    """Mo phong don vi cua 1 symbol. MS: collapse_ms (tat ca giao dich da tai cua symbol, [data_start, data_end)).
    U: dict mang theo don vi: t0 (ms), side (+1/-1), L, X, tick, W, T (phut), slip (phan so), dl_end (ms; -1 = khong delist).
    fund_t / fund_r: moc funding (ms, tang dan) va rate cua symbol. Tra dict mang theo don vi (OUT_COLS)."""
    assert model in RULES
    model, lat_in, lat_out = RULES[model]
    thr = model == "THROUGH"
    t = MS["t"]
    nu = len(U["t0"])
    out = {k: np.zeros(nu, np.float64) for k in OUT_COLS}
    for k in ("filled", "excl", "kind", "n_maker"):
        out[k] = np.zeros(nu, np.int64)
    out["tf"] = np.full(nu, -1, np.int64)
    out["tx"] = np.full(nu, -1, np.int64)
    for k in ("xpx", "gross", "fee", "fee_stress", "slip", "fund", "net", "net_stress"):
        out[k][:] = np.nan
    fund_t = np.zeros(0, np.int64) if fund_t is None else np.asarray(fund_t, np.int64)
    fund_r = np.zeros(0) if fund_r is None else np.asarray(fund_r, np.float64)
    gcache = {}
    for i in range(nu):
        t0 = int(U["t0"][i])
        s = int(U["side"][i])
        L, X, tick = float(U["L"][i]), float(U["X"][i]), float(U["tick"][i])
        W, T = int(U["W"][i]), int(U["T"][i])
        dl = int(U["dl_end"][i])
        assert s in (1, -1) and t0 % MS_MIN == 0 and t0 >= data_start
        lim_end = data_end if dl < 0 else min(data_end, dl)
        need = t0 + (W + T) * MS_MIN + GAP_MS + MS_MIN
        if not (data_end >= need or (dl >= 0 and dl <= data_end)):
            raise RuntimeError("du lieu tai khong du phu cua so don vi (thieu file ngay ke tiep?)")
        a = int(np.searchsorted(t, t0 + lat_in, "left"))
        b = int(np.searchsorted(t, min(t0 + W * MS_MIN, lim_end), "left"))
        j = _hit_down(MS, a, b, L, tick, model) if s == 1 else _hit_up(MS, a, b, L, tick, model)
        if j < 0:
            e_life = min(t0 + W * MS_MIN, lim_end)
        else:
            tf = int(t[j])
            te = tf + T * MS_MIN
            c = int(np.searchsorted(t, tf + lat_out, "left"))
            e_ = int(np.searchsorted(t, min(te, lim_end - 1), "right"))
            tol = TOL_TICK * tick
            pact = float(MS["pl"][c - 1])          # gia giao dich gan nhat TRUOC luc lenh thoat co hieu luc (c - 1 >= hang khop)
            beyond = thr and tf + lat_out < lim_end and (pact >= X + tick - tol if s == 1 else pact <= X - tick + tol)
            k = -1 if beyond else (_hit_up(MS, c, e_, X, tick, model) if s == 1 else _hit_down(MS, c, e_, X, tick, model))
            if beyond:
                tx, xpx, kind = tf + lat_out, X, EX_TAKER_BEYOND
            elif k >= 0:
                tx, xpx, kind = int(t[k]), X, EX_LIMIT
            elif dl >= 0 and dl <= te:
                kk = int(np.searchsorted(t, dl, "left")) - 1
                tx, xpx, kind = dl, float(MS["pl"][kk]), EX_DELIST
            else:
                kk = int(np.searchsorted(t, te, "right")) - 1
                tx, xpx, kind = te, float(MS["pl"][kk]), EX_TIMEOUT
            e_life = tx
            ratio = xpx / L
            if kind == EX_LIMIT:
                r_exit, r_exit_s, srate = FEE_MAKER, FEE_MAKER_STRESS, 0.0
            elif kind == EX_TIMEOUT:
                if thr:
                    r_exit, r_exit_s, srate = FEE_TAKER, FEE_TAKER, float(U["slip"][i])
                else:
                    r_exit, r_exit_s, srate = FEE_MAKER, FEE_MAKER_STRESS, 0.0
            elif kind == EX_TAKER_BEYOND:
                r_exit, r_exit_s, srate = FEE_TAKER, FEE_TAKER, 0.0
            else:
                r_exit, r_exit_s, srate = FEE_TAKER, FEE_TAKER, (DELIST_SLIP_THROUGH if thr else 0.0)
            gross = s * (xpx - L) / L
            fee = FEE_MAKER + r_exit * ratio
            fee_s = FEE_MAKER_STRESS + r_exit_s * ratio
            slipc = srate * ratio
            fu = 0.0
            if fund_t.size:
                lo_, hi_ = np.searchsorted(fund_t, [tf, tx], "right")
                for q in range(lo_, hi_):
                    km = int(np.searchsorted(t, fund_t[q], "left")) - 1
                    fu += -s * fund_r[q] * float(MS["pl"][km]) / L
            net = gross + fu - fee - slipc
            out["filled"][i], out["tf"][i], out["tx"][i], out["kind"][i], out["xpx"][i] = 1, tf, tx, kind, xpx
            out["gross"][i], out["fee"][i], out["fee_stress"][i], out["slip"][i], out["fund"][i] = (
                gross * 1e4, fee * 1e4, fee_s * 1e4, slipc * 1e4, fu * 1e4)
            out["net"][i], out["net_stress"][i] = net * 1e4, (gross + fu - fee_s - slipc) * 1e4
            out["n_maker"][i] = 1 + int(kind == EX_LIMIT)
        key = lim_end
        if key not in gcache:
            gcache[key] = gap_intervals(MS, data_start, lim_end)
        ga, gb = gcache[key]
        if ga.size and np.any((ga < e_life) & (gb > t0)):
            out["excl"][i] = 1
    return out
