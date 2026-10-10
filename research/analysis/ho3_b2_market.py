#!/usr/bin/env python3
"""HO3 B2-M: nguon moi cho market.bin doan Q3 tren doan chong H1.
 (a) INLINE (md_inline, port MarketDataInlineGenerator) tu ticker H1  vs  market.bin HO26 (H1)
 (b) STORE re-read: Aerospike local test.market_data_object (CHI DOC) vs market.bin HO26 (H1)
Chi in dem / ty le khop; KHONG in gia tri.
"""
import argparse, datetime, gzip, json, logging, os, struct, sys, time
import numpy as np
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import jbin, md_inline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ho3m")
TZ7 = datetime.timezone(datetime.timedelta(hours=7))
MKT = "/home/ubuntu/claude_master/1003/ho1/ds/market.bin"
T1 = "/home/ubuntu/java/simulator/kaggle_data_hpo"
H1A = int(datetime.datetime(2026, 1, 1, tzinfo=TZ7).timestamp() * 1000)
H1B = int(datetime.datetime(2026, 7, 1, tzinfo=TZ7).timestamp() * 1000)


def load_market():
    b = open(MKT, "rb").read()
    n = struct.unpack_from(">i", b, 0)[0]
    a = np.frombuffer(b, dtype=np.dtype([("ts", ">i8"), ("v", ">f4", 3)]), count=n, offset=4)
    m = (a["ts"] >= H1A) & (a["ts"] < H1B)
    return {int(t): tuple(float(x) for x in v) for t, v in zip(a["ts"][m], a["v"][m])}, n


def tpath(day):
    for p in (os.path.join(T1, "ticker_%s.bin.gz" % day), os.path.join(T1, "daily", "ticker_%s.bin.gz" % day)):
        if os.path.exists(p):
            return p
    raise FileNotFoundError(day)


def stats(ref, got):
    r = dict(n_ref=len(ref), n_got=len(got), both=0, le1e6=0, le1e3=0, ref_only=0, got_only=0, maxabs=0.0)
    for t, v in ref.items():
        g = got.get(t)
        if g is None:
            r["ref_only"] += 1; continue
        r["both"] += 1
        d = max(abs(np.float32(v[i]) - np.float32(g[i])) for i in range(3))
        r["maxabs"] = max(r["maxabs"], float(d))
        if d <= 1e-6:
            r["le1e6"] += 1
        if d <= 1e-3:
            r["le1e3"] += 1
    r["got_only"] = sum(1 for t in got if t not in ref)
    r["rate_le1e6_vs_ref"] = r["le1e6"] / max(r["n_ref"], 1)
    r["rate_le1e3_vs_ref"] = r["le1e3"] / max(r["n_ref"], 1)
    return r


def run_inline(ref):
    gen = md_inline.InlineMD({"BTCDOMUSDT", "USDCUSDT"})
    got = {}
    d = datetime.date(2025, 12, 31)
    while d <= datetime.date(2026, 6, 30):
        t0 = time.time()
        with gzip.open(tpath(d.strftime("%Y%m%d")), "rb") as f:
            b = f.read()
        for ms, m in jbin.iter_minutes(b):
            snap = {s: (v[4], v[1], v[2], v[3]) for s, v in m.items()}
            r = gen.update(snap)
            if r is not None and H1A <= ms < H1B:
                got[ms] = r
        if d.day == 1:
            log.info("inline %s got=%d %.1fs", d, len(got), time.time() - t0)
        d += datetime.timedelta(days=1)
    return got


def run_store(ref):
    import aerospike
    from concurrent.futures import ThreadPoolExecutor
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 4000}}).connect()
    keys = list(range(H1A, H1B, 60000))

    def one(t):
        k = datetime.datetime.fromtimestamp(t / 1000, TZ7).strftime("%Y%m%d-%H%M")
        try:
            r = cli.get(("test", "market_data_object", k))
            d = r[2].get("data") if r else None
            return (t, struct.unpack_from(">fff", d, 0)) if d and len(d) >= 12 else (t, None)
        except Exception:
            return (t, None)
    got = {}
    with ThreadPoolExecutor(32) as ex:
        for t, v in ex.map(one, keys):
            if v is not None:
                got[t] = v
    cli.close()
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["inline", "store"], required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ref, ntot = load_market()
    log.info("market.bin HO26 n=%d H1=%d", ntot, len(ref))
    got = run_inline(ref) if a.mode == "inline" else run_store(ref)
    r = stats(ref, got); r["mode"] = a.mode
    # theo thang (ty le <=1e-6 so voi ref)
    bym = {}
    for t in ref:
        mo = datetime.datetime.fromtimestamp(t / 1000, TZ7).strftime("%Y-%m")
        g = got.get(t)
        x = bym.setdefault(mo, [0, 0])
        x[0] += 1
        if g is not None and max(abs(np.float32(ref[t][i]) - np.float32(g[i])) for i in range(3)) <= 1e-6:
            x[1] += 1
    r["by_month_le1e6"] = {k: round(v[1] / v[0], 6) for k, v in sorted(bym.items())}
    json.dump(r, open(a.out, "w"), indent=1)
    log.info("RESULT %s", json.dumps(r))


if __name__ == "__main__":
    main()
