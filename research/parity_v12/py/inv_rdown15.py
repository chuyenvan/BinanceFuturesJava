#!/usr/bin/env python3
"""ADDENDUM1 dieu tra (mo ta, khong doi verdict): phut lech '15' reference' (momentum15M = rateDown15MAvg).
Tai lap DOC LAP rateDown15MAvg tu Vision 1m theo dung code jar (MarketDataInlineGenerator.update +
MarketBigChangeDetector.calMarketData, float32, TreeMap<Float> khu trung key, N=min(100, size*4/5), cua so
15 nen KHA DUNG gan nhat theo SO DEM) -> (1) kiem tai lap = r_down15 cua OFF-BT moi phut;
(2) gia thuyet 1 nhieu duy nhat tai cac phut lech: H1 bo 1 symbol khoi snapshot phut M; H2 bo 1 nen (s, X)
khoi buffer (live thieu/khong kha dung nen X) => so voi gia tri live bit-exact.
"""
import io, os, sys, zipfile, json, datetime as dt
import numpy as np, pandas as pd

W = os.path.expanduser("~/claude_master/parity_v11w")
VIS = W + "/vision/klines_1m"
MIN = 60000
DIED = {"BTCDOMUSDT", "USDCUSDT"}
F32 = np.float32


def f7(t):
    return dt.datetime.utcfromtimestamp(t / 1000 + 7 * 3600).strftime("%m-%d %H:%M")


def ms7(s):
    return int(dt.datetime.strptime("2026-" + s + " +0700", "%Y-%m-%d %H:%M %z").timestamp() * 1000)


def load(day, sym):
    p = "%s/%s/%s.zip" % (VIS, day, sym)
    if not os.path.exists(p):
        return None
    with zipfile.ZipFile(p) as z:
        raw = z.read(z.namelist()[0]).decode()
    hdr = 0 if raw.startswith("open_time") else None
    d = pd.read_csv(io.StringIO(raw), header=hdr, usecols=[0, 1, 2, 3, 4, 7], dtype=str)
    d.columns = ["t", "o", "h", "l", "c", "qv"]
    out = pd.DataFrame({"t": d.t.astype(np.int64)})
    for c in ["o", "h", "l", "c", "qv"]:
        out[c] = np.array([F32(x) for x in d[c].values], dtype=np.float32)   # ~ Float.valueOf(String)
    return out


U = sorted(f[:-4] for f in os.listdir(VIS + "/2026-10-21") if f.endswith(".zip"))
A = os.environ.get("RANGE", "10-21 15:30,10-21 18:00").split(",")
TA, TB = ms7(A[0]), ms7(A[1])
WARM = TA - int(os.environ.get("WARM_MIN", "40")) * MIN
data = {}
for s in U:
    parts = [x for x in (load("2026-10-20", s), load("2026-10-21", s)) if x is not None]
    d = pd.concat(parts)
    d = d[(d.t >= WARM) & (d.t <= TB)].set_index("t")
    data[s] = d
print("loaded", len(data), "symbols", f7(WARM), "->", f7(TB))


def rate(a, b):  # Utils.rateOf2Double(Float,Float) = (a-b)/b float
    return F32(F32(a - b) / b)


def avg_tree(vals):
    """TreeMap<Float,String> khu trung key, tang dan; N = min(100, size*4/5); tong float32."""
    keys = np.unique(np.asarray(vals, np.float32))
    n = min(100, len(keys) * 4 // 5)
    tot = F32(0)
    cnt = 0
    for k in keys:
        cnt += 1
        tot = F32(tot + k)
        if cnt >= n:
            break
    return F32(tot / F32(cnt)) if len(keys) else F32(0)


def simulate(drop_sym_at=None, drop_candle=None, upto=None):
    """Tra {minute: rateDown15MAvg}. drop_sym_at=(s, M): bo s khoi snapshot phut M (khong nuoi buffer, khong tinh).
    drop_candle=(s, X): nen X cua s coi nhu khong kha dung (khong vao buffer, khong vao rateMax o phut X)."""
    buf = {s: [] for s in U}
    out = {}
    for M in range(WARM, (upto or TB) + MIN, MIN):
        downs, maxs = [], []
        btc = data["BTCUSDT"]
        rb = rate(btc.at[M, "c"], btc.at[M, "o"]) if M in btc.index else F32(0)
        for s in U:
            d = data[s]
            if M not in d.index or s in DIED:
                continue
            if drop_sym_at and drop_sym_at == (s, M):
                continue
            o, h, l, c, qv = d.at[M, "o"], d.at[M, "h"], d.at[M, "l"], d.at[M, "c"], d.at[M, "qv"]
            avail = (l != h) or (qv != 0)
            if drop_candle and drop_candle == (s, M):
                avail = False
            pmax = None
            if avail:
                b = buf[s]
                b.append(h)
                if len(b) > 100:
                    del b[:5]
                pmax = max(b[-15:])
            rc = rate(c, o)
            if rb > -0.004 and rc < -0.15:
                continue
            if rc > 0.3:
                continue
            downs.append(rc)
            if pmax is not None:
                maxs.append(rate(c, F32(pmax)))
        if M >= TA:
            out[M] = (avg_tree(downs), avg_tree(maxs))
    return out


JG = pd.read_csv(W + "/work/join_gate.csv.gz")
JG = JG[(JG["min"] >= TA) & (JG["min"] <= TB)].set_index("min")
base = simulate()
ok_bt = ok_live = n = 0
bad_bt = []
for M, (rd, r15) in base.items():
    if M not in JG.index:
        continue
    n += 1
    if F32(JG.at[M, "r_down15"]) == r15 and F32(JG.at[M, "r_down"]) == rd:
        ok_bt += 1
    else:
        bad_bt.append((f7(M), float(r15), float(JG.at[M, "r_down15"])))
    if F32(JG.at[M, "rateDown15MAvg"]) == r15:
        ok_live += 1
print("tai lap vs OFF-BT (r_down & r_down15 bit-exact): %d/%d ; vs live rateDown15MAvg: %d/%d" % (ok_bt, n, ok_live, n))
print("lech BT (toi da 10):", bad_bt[:10])
targets = [ms7(x) for x in os.environ.get("TARGETS", "10-21 17:37,10-21 17:38,10-21 17:40").split(",")]
live_mis = [M for M in base if M in JG.index and F32(JG.at[M, "rateDown15MAvg"]) != base[M][1]]
print("phut live != tai lap:", [f7(M) for M in live_mis])
# Thuc thi H1/H2 hieu qua: chup buffer tai M-1 cho moi target
def snapshot_state(Mstop):
    buf = {s: [] for s in U}
    for M in range(WARM, Mstop + MIN, MIN):
        for s in U:
            d = data[s]
            if M not in d.index or s in DIED:
                continue
            o, h, l, c, qv = d.at[M, "o"], d.at[M, "h"], d.at[M, "l"], d.at[M, "c"], d.at[M, "qv"]
            if (l != h) or (qv != 0):
                b = buf[s]
                b.append(h)
                if len(b) > 100:
                    del b[:5]
    return buf


for M in targets:
    lv = F32(JG.at[M, "rateDown15MAvg"])
    buf = snapshot_state(M)   # buffer SAU khi nuoi phut M
    btc = data["BTCUSDT"]
    rb = rate(btc.at[M, "c"], btc.at[M, "o"])
    per = {}
    for s in U:
        d = data[s]
        if M not in d.index or s in DIED:
            continue
        o, c = d.at[M, "o"], d.at[M, "c"]
        rc = rate(c, o)
        if (rb > -0.004 and rc < -0.15) or rc > 0.3:
            continue
        b = buf[s]
        avail = (d.at[M, "l"] != d.at[M, "h"]) or (d.at[M, "qv"] != 0)
        per[s] = (rc, rate(c, F32(max(b[-15:]))) if avail and b else None, b, c, avail)
    maxs = {s: v[1] for s, v in per.items() if v[1] is not None}
    h1 = [s for s in maxs if avg_tree([v for k, v in maxs.items() if k != s]) == lv]
    # H2: bo 1 nen X trong 15 nen cuoi cua s (cua so dich lui 1 nen)
    h2 = []
    for s, v in per.items():
        b = v[2]
        if v[1] is None or len(b) < 2:
            continue
        for j in range(1, min(16, len(b)) + 1):
            nb = b[:len(b) - j] + b[len(b) - j + 1:]
            if not nb:
                continue
            alt = dict(maxs)
            alt[s] = rate(v[3], F32(max(nb[-15:])))
            if alt[s] != maxs[s] and avg_tree(list(alt.values())) == lv:
                h2.append((s, f7(M - (j - 1) * MIN) + "~nen thu %d tu cuoi" % j))
    # H3 (mo ta): symbol nao trong tap day-100 co the giai thich bang 1 gia tri r khac (khong dinh danh)
    srt = sorted(set(maxs.values()))
    n = min(100, len(srt) * 4 // 5)
    print(f7(M), "live", float(lv), "| H1 bo 1 symbol khop:", h1[:10], "| H2 bo 1 nen khop:", h2[:10],
          "| N", n, "size", len(srt), "| delta*N", float((lv - base[M][1]) * n))
    for s in ("BACUSDT", "CEGUSDT", "IBKRUSDT"):
        if s in per:
            print("   ", s, "r15=", per[s][1], "rank", (srt.index(per[s][1]) + 1) if per[s][1] in srt else None,
                  "n_buf", len(per[s][2]))
