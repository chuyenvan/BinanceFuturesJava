"""MM_Q1 core: one symbol-hour -> book replay (diff from EMPTY), quality, passive-quote fill sim, markout aggregates.
All timestamps int64 ms. Prices exact int (price * 10^d from decimal strings). Book clock = event_time (E)."""
import io, sys, time, heapq
import numpy as np, pyarrow as pa, pyarrow.parquet as pq, pyarrow.compute as pc
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/chd")
import chd_lib as L

HMS = 3600000
LATS = (0, 100, 300)          # ms
HS = (1, 10, 60, 300)         # s
K0, K1 = 300, 3300            # quote seconds k in [K0, K1): t = h0 + k*1000
FEE = 0.0002                  # maker fee per fill (fraction)


def key(sym, h0, t):
    g = time.gmtime(h0 // 1000)
    return f"binance_futures/{g.tm_year:04d}-{g.tm_mon:02d}-{g.tm_mday:02d}/{g.tm_hour:02d}/{sym}_{t}.parquet.zst"


def fetch(sym, h0, t, cols=None):
    b, n = L.get_bytes(key(sym, h0, t))
    if b is None:
        return None, 0
    return pq.read_table(io.BytesIO(b), columns=cols), n


def kline_r(sym, h0):
    """1h return = close(bar h0+59m)/open(bar h0) - 1 from chd 1m kline; None if not exactly 60 bars."""
    tb, _ = fetch(sym, h0, "kline", ["received_time", "kline_start_time", "kline_open_price", "kline_close_price"])
    if tb is None:
        return None, "kline_missing"
    st = tb.column("kline_start_time").to_numpy()
    assert st.dtype == np.int64
    rc = tb.column("received_time").to_numpy()
    o = tb.column("kline_open_price").cast(pa.float64()).to_numpy(); c = tb.column("kline_close_price").cast(pa.float64()).to_numpy()
    m = (st >= h0) & (st < h0 + HMS)
    st, rc, o, c = st[m], rc[m], o[m], c[m]
    order = np.lexsort((rc, st)); st, o, c = st[order], o[order], c[order]
    last = np.r_[st[1:] != st[:-1], True]
    st, o, c = st[last], o[last], c[last]
    if len(st) != 60 or not np.array_equal(st, h0 + np.arange(60, dtype=np.int64) * 60000):
        return None, f"kline_bars_{len(st)}"
    return float(c[-1] / o[0] - 1.0), "ok"


def _dec(strs):
    """unique decimal strings -> (scale d, int values at that scale)"""
    fr = [len(s.split(".")[1]) if "." in s else 0 for s in strs]
    return fr


def to_int(dict_strs, d):
    out = np.empty(len(dict_strs), dtype=np.int64)
    for i, s in enumerate(dict_strs):
        if "." in s:
            a, b = s.split(".")
            out[i] = int(a + b) * 10 ** (d - len(b))
        else:
            out[i] = int(s) * 10 ** d
    return out


def load(sym, h0):
    ob, nob = fetch(sym, h0, "orderbook", ["event_time", "first_update_id", "final_update_id", "prev_final_update_id", "side", "price", "quantity", "event_type"])
    tr, ntr = fetch(sym, h0, "trades", ["trade_id", "price", "quantity", "trade_time", "is_buyer_maker", "order_type"])
    return ob, tr, nob, ntr


def trades_r(sym, h0):
    """ADDENDUM1 bug 2: 1h return = last/first valid trade price in [h0, h0+1h) - 1 (dedupe id, drop price/qty 0)."""
    tb, _ = fetch(sym, h0, "trades", ["trade_id", "price", "quantity", "trade_time"])
    if tb is None:
        return None
    tt = tb.column("trade_time").to_numpy(); assert tt.dtype == np.int64
    tid = tb.column("trade_id").to_numpy()
    p = tb.column("price").cast(pa.float64()).to_numpy(); q = tb.column("quantity").cast(pa.float64()).to_numpy()
    _, fi = np.unique(tid, return_index=True)
    tt, tid, p, q = tt[fi], tid[fi], p[fi], q[fi]
    m = (tt >= h0) & (tt < h0 + HMS) & (p > 0) & (q > 0)
    if m.sum() < 2:
        return None
    o = np.lexsort((tid[m], tt[m])); pp = p[m][o]
    return float(pp[-1] / pp[0] - 1.0)


def load_d(sym, h0):
    ob, tr, nob, ntr = load(sym, h0)
    return {"ob": ob, "tr": tr, "nob": nob, "ntr": ntr}


def replay(D):
    """D = load_d(...) (ob/tr popped so the table can be freed). returns info + book state arrays + trades arrays (ints)."""
    ob = D.pop("ob"); tr = D.pop("tr")
    info = {}
    et = ob.column("event_type")
    info["n_nonupdate_rows"] = int(pc.sum(pc.not_equal(et, "update")).as_py() or 0)
    E = ob.column("event_time").to_numpy(); assert E.dtype == np.int64
    U = ob.column("final_update_id").to_numpy(zero_copy_only=False)
    PU = ob.column("prev_final_update_id").to_numpy(zero_copy_only=False)
    side = ob.column("side").to_numpy(zero_copy_only=False)
    pdict = pc.dictionary_encode(ob.column("price")).combine_chunks()
    tdict = pc.dictionary_encode(tr.column("price")).combine_chunks()
    ps = pdict.dictionary.to_pylist(); ts_ = tdict.dictionary.to_pylist()
    d = max(_dec(ps) + _dec(ts_))
    pint_u = to_int(ps, d); tint_u = to_int(ts_, d)
    P = pint_u[pdict.indices.to_numpy()]
    Q = ob.column("quantity").cast(pa.float64()).to_numpy()
    isbid = side == "bid"
    info["n_side_other"] = int((~isbid & (side != "ask")).sum())
    up = np.sort(np.unique(pint_u)); tick = int(np.gcd.reduce(np.diff(up))) if len(up) > 1 else 0
    info.update(d=d, tick=tick, rows=int(len(P)))
    # message groups (contiguous rows with same final_update_id)
    st = np.r_[0, np.flatnonzero(U[1:] != U[:-1]) + 1]; en = np.r_[st[1:], len(U)]
    gid = np.repeat(np.arange(len(st)), en - st)
    info["E_inconsistent_rows"] = int((E != E[st][gid]).sum())
    gu = U[st]
    _, first = np.unique(gu, return_index=True)
    keep = np.zeros(len(st), bool); keep[first] = True
    info["dup_msgs"] = int((~keep).sum())
    st, en, gu = st[keep], en[keep], gu[keep]
    gpu = PU[st]; gE = E[st]
    info["n_msgs"] = int(len(st))
    info["u_nonmono"] = int((np.diff(gu) <= 0).sum())
    info["pu_breaks"] = int((gpu[1:] != gu[:-1]).sum())
    info["E_nonmono"] = int((np.diff(gE) < 0).sum())
    # replay (row lists built per chunk of ~1M rows to cap memory)
    del U, PU, side, et, pdict, E, gid
    ob = None
    bids = {}; asks = {}; bh = []; ah = []
    nm = len(st)
    bb = np.full(nm, -1, np.int64); ba = np.full(nm, -1, np.int64)
    bbq = np.zeros(nm); baq = np.zeros(nm); qbd = np.zeros(nm); qad = np.zeros(nm)
    push = heapq.heappush; pop = heapq.heappop
    stl = st.tolist(); enl = en.tolist()
    c_end = -1; base = 0
    for m in range(nm):
        if enl[m] > c_end:
            base = stl[m]; c_end = min(len(P), base + 1000000)
            c_end = max(c_end, enl[m])
            Pl = P[base:c_end].tolist(); Ql = Q[base:c_end].tolist(); Bl = isbid[base:c_end].tolist()
        for r in range(stl[m] - base, enl[m] - base):
            p = Pl[r]; q = Ql[r]
            if Bl[r]:
                if q == 0.0:
                    bids.pop(p, None)
                else:
                    if p not in bids:
                        push(bh, -p)
                    bids[p] = q
            else:
                if q == 0.0:
                    asks.pop(p, None)
                else:
                    if p not in asks:
                        push(ah, p)
                    asks[p] = q
        while bh and (-bh[0]) not in bids:
            pop(bh)
        while ah and ah[0] not in asks:
            pop(ah)
        if bh:
            b = -bh[0]; bb[m] = b; bbq[m] = bids[b]; qbd[m] = bids.get(b - tick, 0.0)
        if ah:
            a = ah[0]; ba[m] = a; baq[m] = asks[a]; qad[m] = asks.get(a + tick, 0.0)
    info["final_levels"] = (len(bids), len(asks))
    # trades
    tid = tr.column("trade_id").to_numpy(); tt = tr.column("trade_time").to_numpy()
    assert tid.dtype == np.int64 and tt.dtype == np.int64
    tp = tint_u[tdict.indices.to_numpy()]; tq = tr.column("quantity").cast(pa.float64()).to_numpy()
    ibm = tr.column("is_buyer_maker").to_numpy(zero_copy_only=False).astype(bool)
    otp = tr.column("order_type").to_numpy(zero_copy_only=False)
    _, fi = np.unique(tid, return_index=True)
    info["trade_dup"] = int(len(tid) - len(fi))
    tid, tt, tp, tq, ibm, otp = tid[fi], tt[fi], tp[fi], tq[fi], ibm[fi], otp[fi]
    # ADDENDUM1 bug 1: drop zero-price / zero-qty prints (order_type NA)
    good = (tp > 0) & (tq > 0)
    info["trade_zero_dropped"] = int((~good).sum()); info["trade_na"] = int((otp == "NA").sum())
    info["trade_na_nonzero"] = int(((otp == "NA") & good).sum()); info["trade_nonmarket_types"] = sorted(set(otp.tolist()) - {"MARKET"})
    tid, tt, tp, tq, ibm = tid[good], tt[good], tp[good], tq[good], ibm[good]
    o = np.lexsort((tid, tt)); tid, tt, tp, tq, ibm = tid[o], tt[o], tp[o], tq[o], ibm[o]
    info["trade_off_tick"] = int((tp % tick != 0).sum()) if tick else -1
    return info, dict(E=gE, bb=bb, ba=ba, bbq=bbq, baq=baq, qbd=qbd, qad=qad, tid=tid, tt=tt, tp=tp, tq=tq, ibm=ibm)


def state_idx(E, t):
    return np.searchsorted(E, t, side="right") - 1


def quality(h0, info, S):
    E, bb, ba = S["E"], S["bb"], S["ba"]
    tg = h0 + np.arange(K0, 3600, dtype=np.int64) * 1000
    i = state_idx(E, tg)
    okb = i >= 0
    b = np.where(okb, bb[np.maximum(i, 0)], -1); a = np.where(okb, ba[np.maximum(i, 0)], -1)
    valid = (b > 0) & (a > 0) & (b < a)
    q = {"crossed_frac": float(1 - valid.mean())}
    mid = (a + b) / 2.0
    q["spread_bps_med"] = float(np.median(((a - b) / mid * 1e4)[valid])) if valid.any() else float("nan")
    q["spread_ticks_med"] = float(np.median(((a - b) / info["tick"])[valid])) if valid.any() and info["tick"] else float("nan")
    # V1: trades vs ToB (pre = last msg with E<=tt, post = next msg)
    tt, tp, ibm = S["tt"], S["tp"], S["ibm"]
    m = (tt >= h0 + K0 * 1000) & (tt < h0 + HMS)
    tt, tp, ibm = tt[m], tp[m], ibm[m]
    ip = state_idx(E, tt); ipo = np.minimum(ip + 1, len(E) - 1)
    tick = info["tick"]
    def ok_side(idx):
        idx2 = np.maximum(idx, 0)
        bA = ba[idx2]; bB = bb[idx2]
        buy_ok = (~ibm) & (bA > 0) & (tp >= bA - tick) & (idx >= 0)
        sell_ok = ibm & (bB > 0) & (tp <= bB + tick) & (idx >= 0)
        return buy_ok, sell_ok
    b1, s1 = ok_side(ip); b2, s2 = ok_side(ipo)
    q["v1_n_buy"] = int((~ibm).sum()); q["v1_ok_buy"] = int(((b1 | b2) & ~ibm).sum())
    q["v1_n_sell"] = int(ibm.sum()); q["v1_ok_sell"] = int(((s1 | s2) & ibm).sum())
    q["n_trades_hour"] = int(((S["tt"] >= h0) & (S["tt"] < h0 + HMS)).sum())
    return q


def simulate(h0, info, S, dump=False):
    E, bb, ba, bbq, baq, qbd, qad = S["E"], S["bb"], S["ba"], S["bbq"], S["baq"], S["qbd"], S["qad"]
    tt, tp, tq, ibm, tid = S["tt"], S["tp"], S["tq"], S["ibm"], S["tid"]
    tick = info["tick"]
    ks = np.arange(K0, K1, dtype=np.int64); tq0 = h0 + ks * 1000
    lo = np.searchsorted(tt, tq0, "left"); hi = np.searchsorted(tt, tq0 + 1000, "left")
    nE = len(E)
    def mid_at(tf):
        j = state_idx(E, tf)
        if j < 0:
            return float("nan")
        b = bb[j]; a = ba[j]
        if b <= 0 or a <= 0 or b >= a:
            return float("nan")
        return (a + b) / 2.0
    res = {}; fills_dump = []
    for Lm in LATS:
        i = state_idx(E, tq0 - Lm)
        for dep in (0, 1):
            acc = {}
            for rule in ("cons", "opt"):
                for sd in ("bid", "ask"):
                    acc[(rule, sd)] = [0, np.zeros(len(HS)), np.zeros(len(HS), np.int64)]
            nq = 0
            for n in range(len(ks)):
                j = i[n]
                if j < 0:
                    continue
                b = bb[j]; a = ba[j]
                if b <= 0 or a <= 0 or b >= a:
                    continue
                nq += 1
                l, h = lo[n], hi[n]
                if h <= l:
                    continue
                wp = tp[l:h]; wb = ibm[l:h]; wq = tq[l:h]
                for sd in ("bid", "ask"):
                    if sd == "bid":
                        qp = b - dep * tick; qa = bbq[j] if dep == 0 else qbd[j]
                        thr = wb & (wp < qp); eq = wb & (wp == qp); sgn = 1.0
                    else:
                        qp = a + dep * tick; qa = baq[j] if dep == 0 else qad[j]
                        thr = (~wb) & (wp > qp); eq = (~wb) & (wp == qp); sgn = -1.0
                    jt = np.flatnonzero(thr)
                    jc = jt[0] if len(jt) else -1
                    cq = np.cumsum(np.where(eq, wq, 0.0))
                    je = np.flatnonzero(eq & (cq >= qa))
                    jo = min([x for x in (jc, je[0] if len(je) else -1) if x >= 0], default=-1)
                    for rule, jj in (("cons", jc), ("opt", jo)):
                        if jj < 0:
                            continue
                        tf = int(tt[l + jj]); A = acc[(rule, sd)]; A[0] += 1
                        for hk, hh in enumerate(HS):
                            mm = mid_at(tf + hh * 1000)
                            if mm == mm:
                                A[1][hk] += sgn * (mm - qp) / qp; A[2][hk] += 1
                        if dump and rule == "cons" and Lm == 300 and dep == 0 and len(fills_dump) < 5:
                            fills_dump.append(dict(t_quote=int(tq0[n]), side=sd, book_idx=int(j), book_E=int(E[j]), bb=int(b), ba=int(a), qp=int(qp), trig_tid=int(tid[l + jj]), trig_tt=tf, trig_p=int(tp[l + jj]), mid60=mid_at(tf + 60000), mk60=sgn * (mid_at(tf + 60000) - qp) / qp))
            for (rule, sd), A in acc.items():
                pre = f"L{Lm}_d{dep}_{rule}_{sd}"
                res[pre + "_n"] = A[0]
                for hk, hh in enumerate(HS):
                    res[f"{pre}_h{hh}_sum"] = float(A[1][hk]); res[f"{pre}_h{hh}_nv"] = int(A[2][hk])
            res[f"L{Lm}_d{dep}_nquote"] = nq
    # V5: quote at mid (L=0), trade-through fill; AS0 = side*(p_trade - m)/m ; hs = half spread / m
    i = state_idx(E, tq0)
    v5 = dict(n=0, as0=0.0, hs=0.0, mk60=0.0, nv60=0)
    for n in range(len(ks)):
        j = i[n]
        if j < 0:
            continue
        b = bb[j]; a = ba[j]
        if b <= 0 or a <= 0 or b >= a:
            continue
        l, h = lo[n], hi[n]
        if h <= l:
            continue
        m = (a + b) / 2.0; wp = tp[l:h]; wb = ibm[l:h]
        for sd, mask, sgn in (("bid", wb & (wp < m), 1.0), ("ask", (~wb) & (wp > m), -1.0)):
            jt = np.flatnonzero(mask)
            if not len(jt):
                continue
            jj = jt[0]
            v5["n"] += 1; v5["as0"] += sgn * (wp[jj] - m) / m; v5["hs"] += (a - b) / 2.0 / m
            mm = mid_at(int(tt[l + jj]) + 60000)
            if mm == mm:
                v5["mk60"] += sgn * (mm - m) / m; v5["nv60"] += 1
    res.update({f"v5_{k}": v for k, v in v5.items()})
    return res, fills_dump
