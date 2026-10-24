"""MM_Q1 V3/V4 — INDEPENDENT minimal re-implementation (does NOT import mm_core/mm_run).
Decimal price parsing, bisect-sorted-list book, pure-Python fill loop. Compares with pipeline JSON.
usage: python3 mm_v3.py SYM PERIOD H [--v4]"""
import io, sys, json, bisect
from decimal import Decimal
import pyarrow.parquet as pq
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/chd")
import chd_lib  # raw data access only

sym, per, H = sys.argv[1], sys.argv[2], int(sys.argv[3])
import time as _t
g = _t.gmtime(H // 1000)
pref = f"binance_futures/{g.tm_year:04d}-{g.tm_mon:02d}-{g.tm_mday:02d}/{g.tm_hour:02d}/{sym}_"
def table(t, cols):
    b, _ = chd_lib.get_bytes(pref + t + ".parquet.zst")
    return pq.read_table(io.BytesIO(b), columns=cols)
ob = table("orderbook", ["event_time", "final_update_id", "side", "price", "quantity"])
tr = table("trades", ["trade_id", "price", "quantity", "trade_time", "is_buyer_maker"])
E = ob.column("event_time").to_pylist(); U = ob.column("final_update_id").to_pylist()
SIDE = ob.column("side").to_pylist(); PS = ob.column("price").to_pylist(); QS = ob.column("quantity").to_pylist()
del ob
TID = tr.column("trade_id").to_pylist(); TP = tr.column("price").to_pylist(); TQ = tr.column("quantity").to_pylist()
TT = tr.column("trade_time").to_pylist(); IBM = tr.column("is_buyer_maker").to_pylist()
del tr
assert all(isinstance(x, int) for x in E[:1000]) and all(isinstance(x, int) for x in TT[:1000])
uniq = set(PS) | set(TP)
d = max(-Decimal(s).as_tuple().exponent for s in uniq)
conv = {s: int(Decimal(s).scaleb(d)) for s in uniq}
bp = sorted({conv[s] for s in set(PS)})
tick = min(b - a for a, b in zip(bp, bp[1:]))
print("d", d, "tick(min diff)", tick)
# replay
bq = {}; aq = {}; bl = []; al = []
snapE = []; snap = []
seen = set(); prev_u = None; skip = False
def snapshot(e):
    bb = bl[-1] if bl else None; ba = al[0] if al else None
    snapE.append(e)
    snap.append((bb, ba, bq.get(bb, 0.0) if bb is not None else 0.0, aq.get(ba, 0.0) if ba is not None else 0.0,
                 bq.get(bb - tick, 0.0) if bb is not None else 0.0, aq.get(ba + tick, 0.0) if ba is not None else 0.0))
cur_e = None
for i in range(len(U)):
    if U[i] != prev_u:
        if prev_u is not None and not skip:
            snapshot(cur_e)
        prev_u = U[i]; skip = U[i] in seen; seen.add(U[i]); cur_e = E[i]
    if skip:
        continue
    p = conv[PS[i]]; q = float(QS[i])
    book, lst = (bq, bl) if SIDE[i] == "bid" else (aq, al)
    if q == 0.0:
        if p in book:
            del book[p]; lst.pop(bisect.bisect_left(lst, p))
    else:
        if p not in book:
            bisect.insort(lst, p)
        book[p] = q
if not skip:
    snapshot(cur_e)
print("msgs", len(snapE))
def st(tau):
    j = bisect.bisect_right(snapE, tau) - 1
    return snap[j] if j >= 0 else None
def midv(tau):
    s = st(tau)
    if s is None or s[0] is None or s[1] is None or s[0] >= s[1]:
        return None
    return (s[0] + s[1]) / 2.0
# trades: dedupe by id, sort by (time,id)
td = {}
for i in range(len(TID)):
    if TID[i] not in td:
        td[TID[i]] = (TT[i], TID[i], conv[TP[i]], float(TQ[i]), bool(IBM[i]), TP[i])
nz0 = len(td)
td = {k: v for k, v in td.items() if v[2] != 0 and v[3] != 0.0}   # ADDENDUM1: drop zero-price/zero-qty prints
print("trades zero-dropped (indep)", nz0 - len(td))
trs = sorted(td.values())
ttl = [x[0] for x in trs]
out = {}
for L in (0, 100, 300):
    for dep in (0, 1):
        acc = {}
        for k in range(300, 3300):
            t = H + k * 1000
            s = st(t - L)
            if s is None or s[0] is None or s[1] is None or s[0] >= s[1]:
                continue
            lo = bisect.bisect_left(ttl, t); hi = bisect.bisect_left(ttl, t + 1000)
            for side in ("bid", "ask"):
                if side == "bid":
                    qp = s[0] - dep * tick; qa = s[2] if dep == 0 else s[4]; sg = 1.0
                else:
                    qp = s[1] + dep * tick; qa = s[3] if dep == 0 else s[5]; sg = -1.0
                fc = None; fo = None; cum = 0.0
                for j in range(lo, hi):
                    tt_, _, p, q, ibm, _s = trs[j]
                    seller = ibm
                    if side == "bid":
                        through = seller and p < qp; at = seller and p == qp
                    else:
                        through = (not seller) and p > qp; at = (not seller) and p == qp
                    if at:
                        cum += q
                    if fo is None and (through or (at and cum >= qa)):
                        fo = tt_
                    if through:
                        fc = tt_; break
                for rule, tf in (("cons", fc), ("opt", fo)):
                    if tf is None:
                        continue
                    key = f"L{L}_d{dep}_{rule}_{side}"
                    a = acc.setdefault(key, {"n": 0, "s": {}, "nv": {}})
                    a["n"] += 1
                    for h in (1, 10, 60, 300):
                        m = midv(tf + h * 1000)
                        if m is not None:
                            a["s"][h] = a["s"].get(h, 0.0) + sg * (m - qp) / qp; a["nv"][h] = a["nv"].get(h, 0) + 1
        for key, a in acc.items():
            out[key + "_n"] = a["n"]
            for h in (1, 10, 60, 300):
                out[f"{key}_h{h}_sum"] = a["s"].get(h, 0.0); out[f"{key}_h{h}_nv"] = a["nv"].get(h, 0)
RESDIR = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--res=")), "/home/ubuntu/claude_master/mm_wk/res2")
with open(f"{RESDIR}/{sym}/{per}_{H}.json") as f:
    P = json.load(f)
R = P["res"]
mx = {"cons": 0.0, "opt": 0.0}; mism = {"cons": 0, "opt": 0}; ncmp = {"cons": 0, "opt": 0}
for k, v in R.items():
    if not k.startswith("L") or k.endswith("nquote"):
        continue
    rule = "cons" if "_cons_" in k else "opt"
    w = out.get(k, 0)
    ncmp[rule] += 1
    if k.endswith("_sum"):
        mx[rule] = max(mx[rule], abs(v - w))
        if abs(v - w) >= 1e-9: mism[rule] += 1
    elif v != w:
        mism[rule] += 1
print(json.dumps({"sym": sym, "H": H, "ncompared": ncmp, "max_abs_diff_sum": mx, "mismatches": mism,
                  "example": {k: (R[k], out.get(k)) for k in ("L300_d0_cons_bid_n", "L300_d0_cons_ask_n", "L300_d0_cons_bid_h60_sum", "L300_d0_cons_ask_h60_sum")}}))
if "--v4" in sys.argv and "dump" in P:
    for f in P["dump"]:
        tid = f["trig_tid"]; row = td[tid]
        s = st(f["t_quote"] - 300); m60 = midv(row[0] + 60000)
        qp = f["qp"]; sg = 1.0 if f["side"] == "bid" else -1.0
        print(json.dumps({"pipeline": f, "raw_trade": {"trade_id": tid, "time": row[0], "price_str": row[5], "qty": row[3], "is_buyer_maker": row[4]},
                          "indep_book_t-300ms": {"bb": s[0], "ba": s[1]}, "indep_mid60": m60, "indep_mk60": sg * (m60 - qp) / qp,
                          "check": {"through": (row[4] and row[2] < qp) if sg > 0 else ((not row[4]) and row[2] > qp), "in_window": f["t_quote"] <= row[0] < f["t_quote"] + 1000,
                                    "qp_is_touch": qp == (s[0] if sg > 0 else s[1])}}))
