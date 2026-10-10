#!/usr/bin/env python3
"""KFIX F1 probe: REST fapi/v1/klines limit=2 o nhieu do tre sau khi nen M dong, so voi nen final va voi 242 (CHI DOC).
Stage: run --minutes N  -> probe.json ; cmp -> so voi final REST + 242 Aerospike (operate read + LUT)."""
import argparse, json, logging, os, random, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kfix_probe")
WD = "/home/ubuntu/claude_master/1010/kfix_probe"
FAPI = "https://fapi.binance.com"
OFFS = [1, 2, 3, 4, 5, 6, 8, 10, 15, 25, 40]
MN = 60000


def get(path, timeout=5):
    t0 = time.time()
    with urllib.request.urlopen(FAPI + path, timeout=timeout) as r:
        b = r.read()
        w = r.headers.get("X-MBX-USED-WEIGHT-1M")
    return json.loads(b), t0, time.time(), w


def server_offset():
    best = None
    for _ in range(5):
        d, t0, t1, _w = get("/fapi/v1/time")
        rtt = t1 - t0
        off = d["serverTime"] / 1000.0 - (t0 + t1) / 2
        if best is None or rtt < best[0]:
            best = (rtt, off)
    log.info("server offset %.3fs rtt %.3fs", best[1], best[0])
    return best[1]


def pick_symbols(n_top, n_rand, seed):
    d, *_ = get("/fapi/v1/ticker/24hr", timeout=15)
    d = [x for x in d if x["symbol"].endswith("USDT") and x["symbol"].isascii() and x["symbol"].isalnum()]
    d.sort(key=lambda x: -float(x["quoteVolume"]))
    top = [x["symbol"] for x in d[:n_top]]
    rnd = random.Random(seed).sample([x["symbol"] for x in d[n_top:300]], n_rand)
    return top + rnd


def one_kl(sym, srv_off):
    try:
        d, t0, t1, w = get("/fapi/v1/klines?symbol=%s&interval=1m&limit=2" % sym, timeout=4)
        return sym, d, t0 + srv_off, t1 + srv_off, w
    except Exception as e:
        return sym, "ERR:%s" % e, None, None, None


def run(args):
    os.makedirs(WD, exist_ok=True)
    syms = pick_symbols(15, 15, 20261010)
    off = server_offset()
    pool = ThreadPoolExecutor(max_workers=30)
    out = {"syms": syms, "srv_off": off, "obs": []}
    now = time.time() + off
    m_first = (int(now * 1000) // MN + 1) * MN          # nen M dau tien = phut KE TIEP (dong o m_first+MN)
    maxw = 0
    for k in range(args.minutes):
        M = m_first + k * MN
        for s in OFFS:
            target = (M + MN) / 1000.0 + s                 # gio server
            dt = target - (time.time() + off)
            if dt > 0:
                time.sleep(dt)
            for sym, d, t0, t1, w in pool.map(lambda x: one_kl(x, off), syms):
                if w:
                    maxw = max(maxw, int(w))
                rec = {"M": M, "off": s, "sym": sym, "t0": t0, "t1": t1}
                if isinstance(d, str):
                    rec["err"] = d
                else:
                    rec["n"] = len(d)
                    rec["starts"] = [int(x[0]) for x in d]
                    km = [x for x in d if int(x[0]) == M]
                    if km:
                        x = km[0]
                        rec["k"] = [float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[7]), int(x[8])]
                out["obs"].append(rec)
        log.info("minute %d/%d M=%s done, max weight seen %d", k + 1, args.minutes, time.strftime("%H:%M", time.localtime(M / 1000)), maxw)
    out["max_weight"] = maxw
    with open(os.path.join(WD, "probe.json"), "w") as f:
        json.dump(out, f)
    log.info("saved %d obs", len(out["obs"]))


def f32(x):
    import struct
    return struct.unpack("<f", struct.pack("<f", x))[0]


def eq5(a, b):
    return all(f32(x) == f32(y) for x, y in zip(a[:5], b[:5]))


def cmp(args):
    import datetime
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import devexport_202609 as dx
    import aerospike
    from aerospike_helpers import expressions as exp
    from aerospike_helpers.operations import expression_operations as eo, operations as op
    P = json.load(open(os.path.join(WD, "probe.json")))
    Ms = sorted({o["M"] for o in P["obs"]})
    fin = {}
    for sym in P["syms"]:
        if not sym.isascii():
            continue
        d, *_ = get("/fapi/v1/klines?symbol=%s&interval=1m&startTime=%d&limit=%d" % (sym, Ms[0], len(Ms)), timeout=10)
        for x in d:
            fin[(int(x[0]), sym)] = [float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[7]), int(x[8])]
    st = dx.Store("242", pool=4)
    ops = [op.read("data"), eo.expression_read("lut", exp.LastUpdateTime().compile())]
    a242 = {}
    meta242 = {}
    tz7 = datetime.timezone(datetime.timedelta(hours=7))
    for M in Ms:
        key = ("ticker", "kline_1m_opt", datetime.datetime.fromtimestamp(M / 1000, tz7).strftime("%Y%m%d-%H%M"))
        _, meta, b = st.client.operate(key, ops)
        s2, arr = dx.parse_minute(b["data"])
        meta242[M] = (int(meta.get("gen", 0)), int(b.get("lut") or 0) / 1e9)
        for j, s in enumerate(s2):
            a242[(M, s)] = [float(v) for v in arr[j]]
    snaps = {}
    for o in P["obs"]:
        if "k" in o:
            snaps.setdefault((o["M"], o["sym"]), []).append(o)
    rows = []
    for (M, sym), lst in sorted(snaps.items()):
        F = fin.get((M, sym))
        A = a242.get((M, sym))
        if F is None:
            continue
        settle = None
        for o in sorted(lst, key=lambda z: z["off"]):
            if eq5(o["k"], F) and o["k"][5] == F[5]:
                settle = o["off"] if settle is None else settle
            elif settle is not None:
                settle = None   # doi lai sau khi da bang final (khong mong doi)
        eqA = [o["off"] for o in lst if A is not None and eq5(o["k"], A)]
        rows.append({"M": M, "sym": sym, "F": F, "A": A, "a_eq_f": A is not None and eq5(A, F), "settle_off": settle,
                     "a_eq_snap_offs": eqA, "lut_off": meta242[M][1] - (M + MN) / 1000.0 - P["srv_off"] * 0,
                     "gen": meta242[M][0], "snap": {o["off"]: o["k"] for o in lst},
                     "t1": {o["off"]: o["t1"] - (M + MN) / 1000.0 for o in lst}})
    json.dump({"rows": rows, "meta242": {str(k): v for k, v in meta242.items()}}, open(os.path.join(WD, "cmp.json"), "w"))
    summarize(rows)


def summarize(rows):
    import collections
    n = len(rows)
    ok = sum(r["a_eq_f"] for r in rows)
    log.info("cells=%d  242==final %d (%.1f%%)", n, ok, 100.0 * ok / max(n, 1))
    for s in OFFS:
        have = [r for r in rows if str(s) in r["snap"] or s in r["snap"]]
        m = sum(eq5(r["snap"].get(s) or r["snap"].get(str(s)), r["F"]) for r in have)
        lat = sorted((r["t1"].get(s) or r["t1"].get(str(s)) or 0) for r in have)
        log.info("off=%2ds snapshot==final %5.1f%% (n=%d) recv_p50=%.2fs", s, 100.0 * m / max(len(have), 1), len(have), lat[len(lat) // 2] if lat else -1)
    bad = [r for r in rows if not r["a_eq_f"] and r["A"] is not None]
    hit = [r for r in bad if r["a_eq_snap_offs"]]
    log.info("242!=final: %d ; trong do 242 == 1 snapshot REST som: %d (%.1f%%)", len(bad), len(hit), 100.0 * len(hit) / max(len(bad), 1))
    c = collections.Counter(min(int(x) for x in r["a_eq_snap_offs"]) for r in hit)
    log.info("offset snapshot som nhat bang 242: %s", sorted(c.items()))
    qr = sorted(r["A"][4] / r["F"][4] for r in bad if r["F"][4] > 0)
    if qr:
        log.info("Q242/Qfinal tren o lech: min %.4f p50 %.4f max %.4f ; >1: %d", qr[0], qr[len(qr) // 2], qr[-1], sum(q > 1.0000001 for q in qr))
    oeq = sum(f32(r["A"][0]) == f32(r["F"][0]) for r in bad)
    log.info("open dung tren o lech: %d/%d", oeq, len(bad))
    lo = sorted(r["lut_off"] for r in rows)
    log.info("LUT-(M+60s) 242: p0 %.2f p50 %.2f p100 %.2f", lo[0], lo[len(lo) // 2], lo[-1])
    st = collections.Counter(r["settle_off"] for r in rows)
    log.info("settle offset (snapshot dau tien == final va giu nguyen): %s", sorted(st.items(), key=lambda z: (z[0] is None, z[0] or 0)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "cmp"])
    ap.add_argument("--minutes", type=int, default=15)
    a = ap.parse_args()
    run(a) if a.stage == "run" else cmp(a)
