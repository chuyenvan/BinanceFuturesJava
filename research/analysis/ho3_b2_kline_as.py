#!/usr/bin/env python3
"""HO3 B2-K1: Aerospike kline_1m_opt (CHI DOC) vs ticker HO26 (Java-serialized) tren doan chong.
Chi in ty le khop / dem; KHONG in gia tri. Usage:
  ho3_b2_kline_as.py --cluster 242 --start 20260101 --end 20260630 --out k1_242.jsonl
  ho3_b2_kline_as.py --probe
"""
import argparse, datetime, gzip, json, logging, os, sys, time
import numpy as np
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import jbin
import devexport_202609 as dx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ho3k1")
TZ7 = dx.TZ7
TDIR = "/home/ubuntu/java/simulator/kaggle_data_hpo"
DAY = 86400000


def key7(ts):
    return datetime.datetime.fromtimestamp(ts / 1000, TZ7).strftime("%Y%m%d-%H%M")


def load_ticker(day):
    p = os.path.join(TDIR, "ticker_%s.bin.gz" % day)
    with gzip.open(p, "rb") as f:
        b = f.read()
    out = {}
    for ms, m in jbin.iter_minutes(b):
        # jbin tuple: (startTime, maxPrice, minPrice, priceClose, priceOpen, totalUsdt) -> o,h,l,c,v
        out[ms] = {s: (v[4], v[1], v[2], v[3], v[5]) for s, v in m.items()}
    return out


def fetch_as(store, day_utc_ms):
    """Tra ve {ms: {sym: (o,h,l,c,v)}} cho 1440 phut ngay UTC (key +07)."""
    keys = [key7(day_utc_ms + i * 60000) for i in range(1440)]
    cli, ns = store.client, store.kline_ns

    def one(k):
        try:
            r = cli.get((ns, "kline_1m_opt", k))
            return (k, r[2]["data"]) if r else (k, None)
        except Exception:
            return (k, None)
    out = {}
    for i, (k, v) in enumerate(store.pool.map(one, keys)):
        if v is None:
            continue
        syms, arr = dx.parse_minute(v)
        if not syms:
            continue
        out[day_utc_ms + i * 60000] = {s: tuple(float(x) for x in arr[j]) for j, s in enumerate(syms)}
    return out


def f32eq(a, b):
    a = np.float32(a); b = np.float32(b)
    if a == b:
        return True
    return abs(float(a) - float(b)) <= 1e-8 * max(abs(float(b)), 1e-30)


def compare(tk, az):
    r = dict(min_file=len(tk), min_as=len(az), ms_file=0, ms_as=0, ms_both=0, eq5=0, eq_ohlc=0,
             file_only=0, as_only=0, min_miss_as=0, min_miss_file=0)
    r["min_miss_as"] = sum(1 for m in tk if m not in az)
    r["min_miss_file"] = sum(1 for m in az if m not in tk)
    for m in set(tk) | set(az):
        a = tk.get(m, {}); b = az.get(m, {})
        r["ms_file"] += len(a); r["ms_as"] += len(b)
        for s, va in a.items():
            vb = b.get(s)
            if vb is None:
                r["file_only"] += 1; continue
            r["ms_both"] += 1
            e = [f32eq(va[i], vb[i]) for i in range(5)]
            if all(e[:4]):
                r["eq_ohlc"] += 1
                if e[4]:
                    r["eq5"] += 1
        r["as_only"] += sum(1 for s in b if s not in a)
    return r


def probe():
    res = {}
    for cl in ("local", "242"):
        st = dx.Store(cl, pool=8)
        ns = st.kline_ns
        last = None
        d = datetime.datetime(2026, 6, 25, 12, 0, tzinfo=TZ7)
        while d <= datetime.datetime(2026, 10, 10, 12, 0, tzinfo=TZ7):
            k = d.strftime("%Y%m%d-%H%M")
            try:
                r = st.client.get((ns, "kline_1m_opt", k))
                if r:
                    last = k
            except Exception:
                pass
            d += datetime.timedelta(days=1)
        res["kline_last_noon_" + cl] = last
        f = st.get_funding_map("BTCUSDT", prefer_local=(cl == "local"))
        res["funding_btc_last_" + cl] = None if f is None else key7(int(f[0][-1]))
        st.close()
    st = dx.Store("local", pool=8)
    d = datetime.datetime(2026, 7, 1, 12, 0, tzinfo=TZ7); last = None
    while d <= datetime.datetime(2026, 10, 10, 12, 0, tzinfo=TZ7):
        try:
            if st.client.get(("test", "market_data_object", d.strftime("%Y%m%d-%H%M"))):
                last = d.strftime("%Y%m%d-%H%M")
        except Exception:
            pass
        d += datetime.timedelta(days=1)
    res["market_data_object_last_noon_local"] = last
    res["mapper_n"] = len(st.get_symbol_mapper())
    st.close()
    print(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--cluster", default="242")
    ap.add_argument("--start", default="20260101")
    ap.add_argument("--end", default="20260630")
    ap.add_argument("--out", default="k1.jsonl")
    a = ap.parse_args()
    if a.probe:
        return probe()
    st = dx.Store(a.cluster, pool=40)
    d = datetime.datetime.strptime(a.start, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
    e = datetime.datetime.strptime(a.end, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
    tot = {}
    with open(a.out, "a") as fo:
        while d <= e:
            day = d.strftime("%Y%m%d"); t0 = time.time()
            tk = load_ticker(day)
            az = fetch_as(st, int(d.timestamp() * 1000))
            r = compare(tk, az); r["day"] = day
            fo.write(json.dumps(r) + "\n"); fo.flush()
            for k, v in r.items():
                if k != "day":
                    tot[k] = tot.get(k, 0) + v
            log.info("%s both=%d eq5=%d eqohlc=%d fonly=%d asonly=%d %.0fs", day, r["ms_both"], r["eq5"],
                     r["eq_ohlc"], r["file_only"], r["as_only"], time.time() - t0)
            d += datetime.timedelta(days=1)
    tot["eq5_rate_vs_file"] = tot["eq5"] / max(tot["ms_file"], 1)
    tot["eq_ohlc_rate_vs_file"] = tot["eq_ohlc"] / max(tot["ms_file"], 1)
    log.info("TOTAL %s", json.dumps(tot))
    st.close()


if __name__ == "__main__":
    main()
