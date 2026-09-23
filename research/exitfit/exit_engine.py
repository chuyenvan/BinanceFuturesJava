"""EXIT FIT — engine replay thuan Python (khong JVM).

Tai hien duong THOAT cua profile `x1_gs_t170` (baseline T170) va cho phep thay HAM GAP:
  arm +7% / ratchet lien tuc / dinh HIGH (nen 1m) / loser time-stop 168h / SL luon > entry.

Nguon chan doan code (doc TRUOC khi viet, xem docs/PREREG_EXIT_FIT.md):
  SimulatorMarketLevelTicker1MStopLoss.startUpdateOldOrderTrading (~:930-1030)
  OrderTargetInfoTest.updateStatusNew (:178-215), updateTPSL (:245-266), trailRate (:367-383)
  TradeUtils.trailFromCap (:45-52), calRateMinWithPredReturn15MForTradingStop (:95-101)
  ClientSingleton.normalizePrice (:217-237)

Dung: xem parity.py / fit.py. Cache nen nam NGOAI repo: /home/ubuntu/exitfit/.
"""
import glob
import os
import pickle
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

import numpy as np

OUT = "/home/ubuntu/exitfit"
CACHE = os.path.join(OUT, "cache")
BARS_PKL = os.path.join(OUT, "bars.pkl")

F = np.float32
# --- hang so profile/Configs T170 ---
RATE_FEE = F(0.002)
SLIP_RATE = F(0.003)
ARM = F(0.07)
GIVEBACK = F(0.5)
CAP_WEAK = F(0.03)
CAP_STRONG = F(0.08)
PNOPUMP_THR = F(0.29)
STEP = F(0.005)
TS_MAX_GAP_LADDER_CAP = F(0.9)     # bat bien: gap <= peak*0.9 (SL > entry)
TIME_STOP_MS = 168 * 3600000
DAY_MS = 86400000
HOUR_MS = 3600000

# --- tick size (exchange_info_pin.json, cung file sim da dung) ---
PIN = "/home/ubuntu/java/exchange_info_pin.json"


def load_tick_sizes():
    import json
    d = json.load(open(PIN))
    out = {}
    for s in d["symbols"]:
        ts = None
        for grp in s["filters"]:
            for f in grp:
                if f.get("filterType") == "PRICE_FILTER":
                    ts = f["tickSize"]
        if ts:
            out[s["symbol"]] = F(float(ts))
    return out


def _java_repr(x):
    """Java Float.toString ~ chuoi thap phan NGAN NHAT round-trip dung float32."""
    return np.format_float_positional(np.float32(x), unique=True, trim="-")


def normalize_floor(price, tick):
    """ClientSingleton.normalizePrice: floor(price/tick)*tick, setScale(scale(tick), HALF_UP)."""
    if tick is None or tick <= 0:
        return F(price)
    bd_price = Decimal(_java_repr(price))
    bd_tick = Decimal(_java_repr(tick))
    normalized = (bd_price / bd_tick).to_integral_value(rounding=ROUND_FLOOR) * bd_tick
    scale = -bd_tick.normalize().as_tuple().exponent
    if scale < 0:
        scale = 0
    q = Decimal(1).scaleb(-scale)
    normalized = normalized.quantize(q, rounding=ROUND_HALF_UP)
    return F(float(normalized))


def load_bars(rebuild=False):
    """Doc cache/part_*.pkl (build_cache.py) -> dict cid -> (ts int64[n], ohlc float32[n,4])."""
    if os.path.exists(BARS_PKL) and not rebuild:
        with open(BARS_PKL, "rb") as f:
            return pickle.load(f)
    parts = sorted(glob.glob(os.path.join(CACHE, "part_*.pkl")))
    if not parts:
        raise SystemExit("chua co cache — chay build_cache.py truoc")
    acc = {}
    for p in parts:
        with open(p, "rb") as f:
            d = pickle.load(f)
        for cid, (ts, ohlc) in d["bars"].items():
            if cid in acc:
                a = acc[cid]
                a[0].append(ts)
                a[1].append(ohlc)
            else:
                acc[cid] = [[ts], [ohlc]]
    bars = {}
    for cid, (tsl, ohl) in acc.items():
        ts = np.concatenate(tsl)
        o = np.concatenate(ohl)
        idx = np.argsort(ts, kind="stable")
        bars[cid] = (ts[idx], o[idx])
    with open(BARS_PKL, "wb") as f:
        pickle.dump(bars, f, protocol=4)
    return bars


# ------------------------------------------------------------------ policies
class Policy:
    """peak_mode='high'|'close'; gap_fn(peak, atr, pred) -> gap (float32)."""

    def __init__(self, name, gap_fn, peak_mode="high", atr_k=0, desc=""):
        self.name = name
        self.gap_fn = gap_fn
        self.peak_mode = peak_mode
        self.atr_k = atr_k
        self.desc = desc


def gap_p0(peak, atr, pred):
    cap = CAP_WEAK if (pred is None or F(pred) > PNOPUMP_THR) else CAP_STRONG
    return np.minimum(F(peak) * GIVEBACK, cap)


def make_p0():
    return Policy("P0", gap_p0, "high", 0, "baseline: min(peak*0.5, 0.03 weak/0.08 strong)")


def make_f1(a, b):
    a, b = F(a), F(b)

    def g(peak, atr, pred):
        return np.minimum(F(peak) * GIVEBACK, a + b * F(peak))
    return Policy("F1_%g_%g" % (float(a), float(b)), g, "high", 0,
                  "gap=min(peak*0.5, %.4g + %.4g*peak)" % (float(a), float(b)))


def make_f2(c, k):
    c = F(c)

    def g(peak, atr, pred):
        return np.minimum(F(peak) * TS_MAX_GAP_LADDER_CAP, c * F(atr))
    return Policy("F2_%g_%d" % (float(c), k), g, "high", k,
                  "gap=min(peak*0.9, %.4g*ATR_%d)" % (float(c), k))


def make_f3():
    return Policy("F3", gap_p0, "close", 0, "P0 nhung dinh = CLOSE (arm cung theo close)")


# ------------------------------------------------------------------ simulate
def trail_rate(peak, atr, pred, policy):
    """trailFromCap/ladder: rate = peak - gap, lam tron buoc 0.005 (Java Math.round(x/0.005)*0.005)."""
    gap = policy.gap_fn(peak, atr, pred)
    gap = np.minimum(gap, F(peak) * TS_MAX_GAP_LADDER_CAP)
    if gap < 0:
        gap = F(0)
    rate = F(F(peak) - gap)
    # Math.round(float) = floor(x+0.5) tren float32; int*float -> float32
    q = F(np.floor(F(F(rate) / STEP) + F(0.5)))
    return F(q * STEP)


def sl_price(entry, rate_sl, tick):
    """Utils.calPriceTarget(SELL, -rateSL): pc = (-rateSL)*entry; res = entry - pc; normalize."""
    pc = F(F(-rate_sl) * entry)
    return normalize_floor(F(entry - pc), tick)


def simulate(cl, ticks, policy, keep_trace=False):
    """Tra 1 ket qua cho CA CUM: (status, exit_ts, priceTP, diag) + per-leg rows."""
    legs = cl["legs"]
    ts, ohlc = ticks[cl["cid"]]
    t0 = legs[0]["ts"]
    i0 = int(np.searchsorted(ts, t0))
    if i0 >= len(ts) or ts[i0] != t0:
        return {"cid": cl["cid"], "sym": cl["sym"], "ok": False, "why": "no_entry_bar"}
    tick = TICKS.get(cl["sym"])
    entry = F(legs[0]["entry"])
    qty = F(legs[0]["qty"])
    pred = legs[0]["pred"]
    for lg in legs[1:]:          # FIX_B1: symbolPred = leg dau (theo thoi gian) khac null
        if pred is None and lg["pred"] is not None:
            pred = lg["pred"]
    anchor = t0
    minp = F(ohlc[i0, 2])        # minPrice = close luc tao cum (mergeOrder)
    sl = None
    status = None
    reason = None
    exit_ts = None
    price_tp = None
    next_leg = 1
    prev_t = t0
    n_arm = 0
    peak_used = F(-1)
    entry0 = F(legs[0]["entry"])
    peak_high = F(ohlc[i0, 1])
    peak_close = F(ohlc[i0, 3])
    n = len(ts)

    def gap_for(i, use_bar):
        if policy.atr_k == 0:
            return F(0), policy.peak_mode
        lo = max(0, i - policy.atr_k)
        if i - lo < 1:
            return F(0), policy.peak_mode
        seg = ohlc[lo:i]
        atr = np.mean((seg[:, 1] - seg[:, 2]) / seg[:, 3])
        return F(atr), policy.peak_mode

    for i in range(i0, n):
        t = int(ts[i])
        o, h, l, c = F(ohlc[i, 0]), F(ohlc[i, 1]), F(ohlc[i, 2]), F(ohlc[i, 3])
        if i > i0:
            # --- updatePriceByKlineSimple
            if l < minp:
                minp = l
            if h > peak_high:
                peak_high = h
            if c > peak_close:
                peak_close = c
            # --- delist guard (moi 60'): cum khong duoc cap nhat > 2 ngay => dong tai lastPrice
            if t % HOUR_MS == 0 and (t - prev_t) > 2 * DAY_MS:
                status, exit_ts, price_tp = "STOP_LOSS_DONE", t, F(c)
                reason = "DELIST"
                break
            # --- LOSER TIME-STOP (truoc cong arm)
            if sl is None and (t - anchor) > TIME_STOP_MS:
                status, exit_ts, price_tp = "STOP_LOSS_DONE", t, F(min(o, c))
                reason = "TS168"
                break
            # --- cong arm
            peak = c if policy.peak_mode == "close" else h
            if peak >= entry * (F(1) + ARM) or sl is not None:
                if sl is None:
                    rate = F((peak - entry) / entry)
                    if rate > ARM:
                        atr, _ = gap_for(i, True)
                        r = trail_rate(rate, atr, pred, policy)
                        sl = sl_price(entry, r, tick)
                        minp = c
                        n_arm += 1
                        # BLOCK_INTRABAR_LOOKAHEAD: khong khop noi nen (return)
                    else:
                        pass                     # updateTPSL: priceSL==null -> khong lam gi
                else:
                    if minp <= sl:
                        status = "STOP_MARKET_DONE" if sl > entry else "STOP_LOSS_DONE"
                        reason = "TRAIL" if sl > entry else "SL_BELOW"
                        price_tp = F(min(sl, o))
                        exit_ts = t
                        break
                    rate = F((peak - entry) / entry)
                    if rate >= ARM:
                        atr, _ = gap_for(i, True)
                        r = trail_rate(rate, atr, pred, policy)
                        sl_new = sl_price(entry, r, tick)
                        if sl_new > sl and sl_new > entry:
                            sl = sl_new
                            minp = c
                            n_arm += 1
        # --- merge leg tiep theo (xay ra CUOI nen: cum moi, priceSL reset null)
        while next_leg < len(legs) and legs[next_leg]["ts"] == t:
            lg = legs[next_leg]
            # mergeOrder: margin/qty CONG DON theo thu tu leg (float32), entry = margin/quantity
            m = F(0)
            qsum = F(0)
            for k in range(next_leg + 1):
                m = F(m + F(F(legs[k]["entry"]) * F(legs[k]["qty"])))
                qsum = F(qsum + F(legs[k]["qty"]))
            entry = F(m / qsum)
            qty = qsum
            minp = c
            sl = None
            anchor = legs[0]["ts"]
            if pred is None and lg["pred"] is not None:
                pred = lg["pred"]
            next_leg += 1
        prev_t = t
    diag = {"n_arm": n_arm, "peak_used": float(peak_used)}
    peak_rate = float((peak_high - entry0) / entry0)
    close_peak_rate = float((peak_close - entry0) / entry0)
    if exit_ts is None:
        # cum con mo cuoi ky: sim dump tai lastPrice (priceTP = lastPrice)
        status = "OPEN_AT_END"
        reason = "OPEN_AT_END"
        exit_ts = int(ts[n - 1])
        price_tp = F(ohlc[n - 1, 3])
    rows = []
    for lg in legs:
        e, q = F(lg["entry"]), F(lg["qty"])
        base = F(F(q * (price_tp - e)) - F(q * e * RATE_FEE) - F(q * e * SLIP_RATE * F(2)))
        rows.append({"cid": cl["cid"], "sym": cl["sym"], "ts": lg["ts"], "entry": float(e), "qty": float(q),
                     "status": status, "end": exit_ts, "tp": float(price_tp), "pnl_nofund": float(base),
                     "csv_pnl": lg["pnl"], "csv_funding": lg["funding"], "csv_status": lg["status"],
                     "csv_end": cl["end"], "csv_end_ts": cl["end"], "csv_tp": lg["tp"], "level": lg["level"],
                     "pred": pred, "n_arm": n_arm, "reason": reason})
    return {"cid": cl["cid"], "sym": cl["sym"], "ok": True, "rows": rows,
            "status": status, "exit_ts": exit_ts, "price_tp": float(price_tp),
            "reason": reason, "peak_rate": float(peak_rate), "close_peak_rate": float(close_peak_rate),
            "n_legs": len(legs), "t0": t0, "entry0": float(entry0), "entry_exit": float(entry),
            "pnl": float(sum(r["pnl_nofund"] for r in rows))}


TICKS = load_tick_sizes()


def load_clusters():
    import json
    return json.load(open(os.path.join(OUT, "clusters.json")))
