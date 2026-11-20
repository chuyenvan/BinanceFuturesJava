"""synth_trades.py - bo sinh aggTrades TONG HOP co dap an biet truoc (cho test_tl.py). Khong dung du lieu that.

- gen_trades: buoc ngau nhien tren luoi tick (gia = so nguyen tick x tick), thoi diem Poisson (co the trung ms), is_buyer_maker
  theo huong buoc (xuong -> True = ben ban chu dong; len -> False), nhieu tuy chon: nhay nhieu tick, lat ibm ngau nhien,
  khoang lang (lo), dung giao dich (delist), khoang cach toi thieu giua 2 giao dich.
- write_vision_zip: ghi file zip dung dinh dang Binance Vision (CSV agg_trade_id,price,quantity,first_trade_id,last_trade_id,
  transact_time,is_buyer_maker; co / khong co dong tieu de) + file .CHECKSUM ("<sha256>  <ten zip>").
- units_from_bars: don vi theo dung quy tac S1 (m0 = close phut t0-1 cua nen dung lai; L = floor/ceil tick; X).
"""
import hashlib
import io
import os
import zipfile
import numpy as np

MS_MIN = 60000


def gen_trades(rng, start_ms, dur_ms, k0, tick, mean_gap_ms=2000.0, same_ms_p=0.15, p_up=0.4, p_dn=0.4, jump_p=0.0,
               jump_max=4, ibm_flip=0.0, quiet=(), stop_ms=None, min_gap_ms=0, aid0=1000):
    n = int(dur_ms / max(mean_gap_ms, 1.0) * 1.3) + 50
    g = rng.exponential(mean_gap_ms, n)
    g = np.floor(g).astype(np.int64)
    if same_ms_p > 0:
        g[rng.random(n) < same_ms_p] = 0
    if min_gap_ms > 0:
        g = np.maximum(g, min_gap_ms)
    t = start_ms + np.cumsum(g)
    keep = t < start_ms + dur_ms
    for a, b in quiet:
        keep &= ~((t >= a) & (t < b))
    if stop_ms is not None:
        keep &= t < stop_ms
    t = t[keep]
    m = t.size
    u = rng.random(m)
    st = np.where(u < p_dn, -1, np.where(u < p_dn + p_up, 1, 0)).astype(np.int64)
    if jump_p > 0:
        jj = rng.random(m) < jump_p
        st[jj] = np.sign(rng.random(jj.sum()) - 0.5).astype(np.int64) * rng.integers(2, jump_max + 1, jj.sum())
    k = k0 + np.cumsum(st)
    k = np.maximum(k, 10)
    p = np.round(k * tick, 10)
    ibm = np.where(st < 0, True, np.where(st > 0, False, rng.random(m) < 0.5))
    if ibm_flip > 0:
        fl = rng.random(m) < ibm_flip
        ibm = np.where(fl, ~ibm, ibm)
    aid = aid0 + np.arange(m, dtype=np.int64)
    q = np.round(rng.exponential(10.0, m) + 0.001, 3)
    return dict(t=t, aid=aid, p=p, q=q, ibm=ibm)


def concat(*parts):
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


def csv_bytes(tr, header=True, bool_style="lower"):
    out = io.StringIO()
    if header:
        out.write("agg_trade_id,price,quantity,first_trade_id,last_trade_id,transact_time,is_buyer_maker\n")
    tv = "true" if bool_style == "lower" else "True"
    fv = "false" if bool_style == "lower" else "False"
    for i in range(tr["t"].size):
        a = int(tr["aid"][i])
        out.write("%d,%s,%s,%d,%d,%d,%s\n" % (a, repr(float(tr["p"][i])), repr(float(tr["q"][i])), 3 * a, 3 * a + 2,
                                             int(tr["t"][i]), tv if tr["ibm"][i] else fv))
    return out.getvalue().encode("ascii")


def write_vision_zip(root, sym, date, tr, header=True, bad_checksum=False, bool_style="lower"):
    d = os.path.join(root, "data", "futures", "um", "daily", "aggTrades", sym)
    os.makedirs(d, exist_ok=True)
    name = "%s-aggTrades-%s" % (sym, date)
    zp = os.path.join(d, name + ".zip")
    with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name + ".csv", csv_bytes(tr, header, bool_style))
    h = hashlib.sha256(open(zp, "rb").read()).hexdigest()
    if bad_checksum:
        h = ("0" if h[0] != "0" else "1") + h[1:]
    with open(zp + ".CHECKSUM", "w") as f:
        f.write("%s  %s.zip\n" % (h, name))
    return zp


def units_from_bars(bars_close, mi_index, t0_list, d_list, tick, W, T, slip, dl_end=-1, data_start_ms=1619827200000):
    """bars_close: dict phut -> close (chi phut co giao dich). Don vi BUY + SELL cho moi (t0, d) co close phut t0-1."""
    import math
    rows = []
    for t0, d in zip(t0_list, d_list):
        m = (t0 - data_start_ms) // MS_MIN
        if (m - 1) not in bars_close:
            continue
        m0 = bars_close[m - 1]
        Lb = math.floor(m0 * (1 - d) / tick + 1e-7) * tick
        Ls = math.ceil(m0 * (1 + d) / tick - 1e-7) * tick
        Xb = math.ceil(Lb * (1 + d) / tick - 1e-7) * tick
        Xs = math.floor(Ls * (1 - d) / tick + 1e-7) * tick
        for s, L, X in ((1, Lb, Xb), (-1, Ls, Xs)):
            rows.append(dict(t0=int(t0), side=s, L=L, X=X, tick=tick, W=W, T=T, slip=slip, dl_end=int(dl_end), m0=m0, d=d,
                             t0_min=int(m)))
    return rows
