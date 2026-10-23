#!/usr/bin/env python3
"""FUNDNEG_T1 V3 — INDEPENDENT re-implementation (does not import core/run).
Variant thr f8 <= -0.0010, H = 24h, TEST period (2024-01-01 <= tau < 2026-01-01); ALL and NON-OVERLAP.
Reads raw kline 1m, funding parquet, printDone csv directly. Dict/loop logic + pyarrow group_by."""
import csv, datetime as dt, json
import numpy as np
import pyarrow as pa, pyarrow.parquet as pq, pyarrow.compute as pc

THR, HH = -0.0010, 24
KL = "/home/ubuntu/vz_e1/raw/kline1m-%s.parquet"
FD = "/home/ubuntu/vz/out/funding/%s/%s.parquet"
H1 = 3600 * 1000
D1 = 24 * H1
UTC = dt.timezone.utc
E0 = int(dt.datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
E1 = int(dt.datetime(2026, 1, 1, tzinfo=UTC).timestamp() * 1000)
S0 = int(dt.datetime(2023, 12, 1, tzinfo=UTC).timestamp() * 1000)   # scan earlier for one-position chain
LASTOPEN = E1 - 60000


def mlist(a, b):
    out, (y, m) = [], a
    while (y, m) <= b:
        out.append("%04d-%02d" % (y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def read(mo):
    t = pq.read_table(KL % mo, columns=["ts", "sym", "close", "quote_volume"])
    assert t.schema.field("ts").type == pa.int64()
    return t.set_column(1, "sym", pc.cast(t["sym"], pa.string()))


# pass 1: daily quote volume + last (ts, close) per symbol
dqv, last = {}, {}
for mo in mlist((2023, 11), (2025, 12)):
    t = read(mo)
    ts = t["ts"].to_numpy()
    g = pa.table({"sym": t["sym"], "day": pa.array(ts // D1), "qv": t["quote_volume"]}) \
        .group_by(["sym", "day"]).aggregate([("qv", "sum")])
    for s, d, q in zip(g["sym"].to_pylist(), g["day"].to_pylist(), g["qv_sum"].to_pylist()):
        dqv[(s, d)] = q
    gl = pa.table({"sym": t["sym"], "ts": t["ts"]}).group_by("sym").aggregate([("ts", "max")])
    mx = dict(zip(gl["sym"].to_pylist(), gl["ts_max"].to_pylist()))
    j = pa.table({"sym": t["sym"], "ts": t["ts"], "close": t["close"]}).join(
        gl.rename_columns(["sym", "ts"]), keys=["sym", "ts"], join_type="inner")
    for s, a, c in zip(j["sym"].to_pylist(), j["ts"].to_pylist(), j["close"].to_pylist()):
        assert mx[s] == a
        if s not in last or a > last[s][0]:
            last[s] = (int(a), float(c))
    print("p1", mo, len(j), len(mx), flush=True)
    del t, ts, j


def universe(y, m):
    d0 = int(dt.datetime(y, m, 1, tzinfo=UTC).timestamp() * 1000) // D1
    days = list(range(d0 - 30, d0))
    ds = set(days)
    syms = set(s for (s, d) in dqv if d in ds)
    med = []
    for s in syms:
        if "_" in s:
            continue
        v = sorted(dqv.get((s, d), 0.0) for d in days)
        med.append((-(v[14] + v[15]) / 2.0, s))
    med.sort()
    return set(s for mm, s in med[:100] if -mm > 0)


U = {mo: universe(int(mo[:4]), int(mo[5:])) for mo in mlist((2023, 12), (2025, 12))}

fund, ev = {}, []
for mo in mlist((2023, 12), (2025, 12)):
    t = pq.read_table(FD % (mo[:4], mo)).to_pydict()
    for ts, s, ih, r in zip(t["ts"], t["sym"], t["interval_h"], t["rate"]):
        tau = ts - ts % 60000
        fund.setdefault(s, []).append((tau, r))
        if r * 8.0 / ih <= THR and S0 <= tau < E1 and s in U[mo]:
            ev.append((s, tau))
for s in fund:
    fund[s].sort()
assert len(ev) == len(set(ev))

need = set()
for s, tau in ev:
    need.add((s, tau + 60000)); need.add((s, tau + HH * H1 + 60000))
    for tp, r in fund.get(s, []):
        if tau < tp <= tau + HH * H1:
            need.add((s, tp - 60000))
needsyms = set(s for s, _ in need)
px = {}
for mo in mlist((2023, 12), (2025, 12)):
    t = read(mo)
    t = t.filter(pc.is_in(t["sym"], value_set=pa.array(sorted(needsyms))))
    for s, a, c in zip(t["sym"].to_pylist(), t["ts"].to_pylist(), t["close"].to_pylist()):
        if (s, a) in need:
            px[(s, a)] = c
    print("p2", mo, flush=True)


def trade(s, tau):
    p0 = px.get((s, tau + 60000))
    if p0 is None:
        return None
    xo = tau + HH * H1 + 60000
    if xo > LASTOPEN:
        return None
    lt, lc = last[s]
    if xo > lt:
        p1, tout = lc, lt + 60000
    else:
        p1, tout = px.get((s, xo)), tau + HH * H1 + 120000
        if p1 is None:
            raise RuntimeError("gap exit %s %d" % (s, tau))
    hi = min(tau + HH * H1, tout)
    f = 0.0
    for tp, r in fund.get(s, []):
        if tau < tp <= hi:
            ps = px.get((s, tp - 60000))
            f += -r * ((ps / p0) if ps is not None else 1.0)
    return (tau + 120000, tout, p1 / p0 - 1.0 + f - 0.0015 - 0.0015)


ev.sort()
trades, lastout = [], {}
for s, tau in ev:
    r = trade(s, tau)
    if r is None:
        continue
    tin, tout, net = r
    if tin >= lastout.get(s, -1):
        lastout[s] = tout
        trades.append((s, tau, net))

legs, crash = {}, set()
for tag in ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]:
    with open("/home/ubuntu/kaggle_sim/out/tsx-x14-%s/storage/printDone.csv" % tag) as fh:
        rd = csv.reader(fh)
        hdr = [h.strip() for h in next(rd)]
        i_s, i_st, i_en = hdr.index("sym"), hdr.index("start"), hdr.index("end")
        for row in rd:
            try:
                st = dt.datetime.strptime(row[i_st].strip(), "%Y%m%d %H:%M").replace(tzinfo=UTC) - dt.timedelta(hours=7)
            except Exception:
                continue
            try:
                en = dt.datetime.strptime(row[i_en].strip(), "%Y%m%d %H:%M").replace(tzinfo=UTC) - dt.timedelta(hours=7)
            except Exception:
                en = st + dt.timedelta(hours=336)
            s = row[i_s].strip()
            s = s if s.endswith("USDT") else s + "USDT"
            a, b = int(st.timestamp() * 1000), int(en.timestamp() * 1000)
            legs.setdefault(s, []).append((a, b))
            crash.add(a // D1)

tt = [x for x in trades if E0 <= x[1] < E1]
non = [x for x in tt if not (x[1] // D1 in crash or any(a <= x[1] + D1 and b >= x[1] - D1 for a, b in legs.get(x[0], [])))]
out = {nm: {"n": len(xs), "mean_net": sum(x[2] for x in xs) / len(xs), "sum_net": sum(x[2] for x in xs)}
       for nm, xs in [("ALL", tt), ("NON", non)]}
out["trades_test"] = [[s, int(t), n] for s, t, n in tt]
json.dump(out, open("/home/ubuntu/claude_master/fundneg_t1_wk/out/v3_independent.json", "w"))
print(json.dumps({k: out[k] for k in ("ALL", "NON")}, indent=1))
