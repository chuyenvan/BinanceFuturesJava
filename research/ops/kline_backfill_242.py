#!/usr/bin/env python3
"""KFIX F5 — backfill `ticker.kline_1m_opt` (Aerospike 242) bang nen CHUAN cua san (Vision daily; REST cho phan Vision chua co).
Audit: docs/audit/KLINE_242_DIVERGENCE.md (242 sai 15,7% o tu 2026-04-25 09:31 +07). Runbook: docs/runbooks/KLINE_FIX_242.md.

Dinh dang record (doc tu code that, DataManagerAerospikeFloatSim.writeMinuteBatch): key "yyyyMMdd-HHmm" gio +07, bin "data" =
Snappy-raw(MinuteDataFinal proto: map<string, KlineObjectOptimized> tickers=1), ten symbol NGAN (BTC), value float32
priceOpen=1 maxPrice=2 minPrice=3 priceClose=4 totalUsdt=5 (fixed32; proto3 bo truong = +0.0).

Quy tac ghi: chi SUA o (phut, symbol) DA CO tren 242 va co tren nguon chuan; KHONG them symbol (giu universe live da thay;
--fill-missing de them); khac chi 1 ulp float32 (lam tron double->float) => KHONG ghi; khong dung phut >= now-10'.
--dry-run (mac dinh): chi doc, bao so o se doi theo ngay +07 (+ uoc luong dung luong backup).
--apply: TRUOC moi ghi, append o cu/moi + gen vao backup jsonl.gz theo ngay (--backup-dir); ghi bang put voi gen==gen da doc
  (record bi ingest ghi chen => doc lai, tinh lai); idempotent (chay lai: o da dung => 0 ghi). --restore FILE: tra o cu.
Vi du:
  python3 kline_backfill_242.py --days 20260528,20260604,20260915 --symbols-file ~/claude_master/1003/kdiv/kdiv_syms.json
  python3 kline_backfill_242.py --from 20260425-0900 --to now --apply --backup-dir /home/ubuntu/kline_backfill_bak
"""
import argparse, datetime, gzip, io, json, logging, os, struct, sys, time, urllib.error, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kline_backfill_242")
MN, D = 60000, 86400000
TZ7 = datetime.timezone(datetime.timedelta(hours=7))
VIS = "https://data.binance.vision/data/futures/um/daily/klines/%s/1m/%s-1m-%s.zip"
REST = "https://fapi.binance.com/fapi/v1/klines?symbol=%s&interval=1m&startTime=%d&limit=1000"   # weight 5
NS, SET = "ticker", "kline_1m_opt"
GUARD_MS = 10 * MN


def k7(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, TZ7).strftime("%Y%m%d-%H%M")


def p7(s):
    fmt = "%Y%m%d-%H%M" if "-" in s else "%Y%m%d"
    return int(datetime.datetime.strptime(s, fmt).replace(tzinfo=TZ7).timestamp() * 1000)


# ------------------------------ proto + snappy (khop Java) ------------------------------
def _rv(b, i):
    r = s = 0
    while True:
        x = b[i]; i += 1
        r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def _wv(n):
    out = bytearray()
    while True:
        x = n & 0x7F; n >>= 7
        if n:
            out.append(x | 0x80)
        else:
            out.append(x)
            return bytes(out)


def decode(raw):
    """bytes Snappy -> {short_sym: (o,h,l,c,q) float32 as python float}. Field-walk day du (proto3 bo truong 0)."""
    import cramjam
    b = bytes(cramjam.snappy.decompress_raw(raw))
    out, i, n = {}, 0, len(b)
    while i < n:
        tag, i = _rv(b, i)
        if tag != 0x0A:
            raise ValueError("tag la %d" % tag)
        ln, i = _rv(b, i); end = i + ln; key = None; v = [0.0] * 5
        while i < end:
            t, i = _rv(b, i)
            if t == 0x0A:
                kl, i = _rv(b, i); key = b[i:i + kl].decode(); i += kl
            elif t == 0x12:
                vl, i = _rv(b, i); ve = i + vl
                while i < ve:
                    ft, i = _rv(b, i)
                    if ft & 7 != 5:
                        raise ValueError("wire %d" % (ft & 7))
                    v[(ft >> 3) - 1] = struct.unpack_from("<f", b, i)[0]; i += 4
            else:
                raise ValueError("entry tag %d" % t)
        out[key] = tuple(v)
    return out


def encode(m):
    """{short: (o,h,l,c,q)} -> Snappy-raw MinuteDataFinal (bo truong +0.0 nhu proto3 Java; key luon ghi)."""
    import cramjam
    out = bytearray()
    for key in sorted(m):
        val = bytearray()
        for f, x in enumerate(m[key], 1):
            bx = struct.pack("<f", x)
            if bx != b"\x00\x00\x00\x00":
                val += bytes([(f << 3) | 5]) + bx
        kb = key.encode()
        ent = b"\x0a" + _wv(len(kb)) + kb + b"\x12" + _wv(len(val)) + bytes(val)
        out += b"\x0a" + _wv(len(ent)) + ent
    return bytes(cramjam.snappy.compress_raw(bytes(out)))


def f32(x):
    return struct.unpack("<f", struct.pack("<f", float(x)))[0]


def ulp_close(a, b):
    """True neu a,b float32 khac nhau toi da 1 ulp (sai so lam tron double->float, khong phai lech du lieu)."""
    ia = struct.unpack("<i", struct.pack("<f", a))[0]
    ib = struct.unpack("<i", struct.pack("<f", b))[0]
    return abs(ia - ib) <= 1 and (a >= 0) == (b >= 0)


def sr(v):
    """float32 -> so JSON ngan nhat ma doc lai (qua f32) ra DUNG bit (fallback repr day du)."""
    import numpy as _np
    t = _np.format_float_positional(_np.float32(v), unique=True, trim="-")
    x = float(t)
    return x if struct.pack("<f", x) == struct.pack("<f", v) else float(v)


def cells_json(ch):
    return {s: [None if o is None else [sr(x) for x in o], [sr(x) for x in n]] for s, (o, n) in ch.items()}


# ------------------------------ nguon chuan ------------------------------
def http(url, tries=4, timeout=60):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                if e.code == 400:
                    log.warning("http 400 (symbol khong hop le/da huy niem yet?) %s", url)
                return None
            log.warning("http %s %s", e.code, url)
        except Exception as e:
            log.warning("http loi %s %s", e, url)
        time.sleep(2 + 4 * i)
    raise RuntimeError("http FAIL " + url)


class RateLimitAbort(RuntimeError):
    """429/418 tu Binance => DUNG NGAY toan bo (khong retry: retry sau 429 la nguyen nhan bi ban IP 418)."""


import threading as _th
_REST_LOCK = _th.Lock()
_REST_STATE = {"min": 0, "w": 0, "max_w": 300}


def rest_get(url):
    """REST TUAN TU (1 luong), tran weight/phut tu dem + header X-MBX-USED-WEIGHT-1M (IP Oracle dung chung shadow)."""
    with _REST_LOCK:
        now = time.time()
        m = int(now // 60)
        if m != _REST_STATE["min"]:
            _REST_STATE["min"], _REST_STATE["w"] = m, 0
        if _REST_STATE["w"] + 5 > _REST_STATE["max_w"]:
            time.sleep(60 - now % 60 + 1)
            _REST_STATE["min"], _REST_STATE["w"] = int(time.time() // 60), 0
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                used = int(r.headers.get("X-MBX-USED-WEIGHT-1M") or 0)
                body = r.read()
        except urllib.error.HTTPError as e:
            if e.code in (418, 429):
                raise RateLimitAbort("HTTP %d Retry-After=%s — DUNG backfill" % (e.code, e.headers.get("Retry-After")))
            if e.code == 400:
                log.warning("REST 400 (symbol khong hop le/da huy?) %s", url)
                return None
            raise
        _REST_STATE["w"] += 5
        if used > _REST_STATE["max_w"] * 2:          # IP dang ban nhieu (shadow + minh) => nghi toi phut sau
            log.warning("X-MBX-USED-WEIGHT-1M=%d > %d => nghi toi phut sau", used, _REST_STATE["max_w"] * 2)
            time.sleep(60 - time.time() % 60 + 1)
        time.sleep(0.25)
        return body


def parse_rows(rows):
    """rows: list cot chuoi [openTime, o, h, l, c, v, closeTime, q, ...] -> {minute: (o,h,l,c,q) float32}."""
    out = {}
    for r in rows:
        if not str(r[0]).isdigit():
            continue
        out[int(r[0]) // MN * MN] = (f32(r[1]), f32(r[2]), f32(r[3]), f32(r[4]), f32(r[7]))
    return out


_VCACHE = {}


def vision_day(sym, utc_day):
    """-> dict hoac None (404 = Vision chua phat hanh / symbol khong co ngay do). Cache 1 ngay UTC (ngay +07 chong 2 ngay UTC)."""
    key = (sym, utc_day)
    if key in _VCACHE:
        return _VCACHE[key]
    for k in [k for k in list(_VCACHE) if k[1] < utc_day and k[0] == sym]:
        _VCACHE.pop(k, None)
    _VCACHE[key] = v = _vision_day(sym, utc_day)
    return v


def _vision_day(sym, utc_day):
    b = http(VIS % (sym, sym, utc_day))
    if b is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(b))
    txt = z.open(z.namelist()[0]).read().decode()
    return parse_rows([l.split(",") for l in txt.splitlines() if l])


def rest_range(sym, start_ms, end_ms):
    """REST klines [start,end) chi nen DA DONG (openTime+1' <= now-10'). Weight 10/call (limit 1500)."""
    out, t = {}, start_ms
    cutoff = int(time.time() * 1000) - GUARD_MS
    while t < end_ms:
        rows = json.loads(rest_get(REST % (sym, t)) or b"[]")
        if not rows:
            break
        for k, v in parse_rows(rows).items():
            if start_ms <= k < end_ms and k + MN <= cutoff:
                out[k] = v
        t = int(rows[-1][0]) + MN
        time.sleep(0.3)
    return out


# ------------------------------ Aerospike 242 ------------------------------
class AS:
    def __init__(self, host, port):
        import aerospike
        from aerospike_helpers import expressions as exp
        from aerospike_helpers.operations import expression_operations as eo, operations as op
        self.aerospike = aerospike
        self.c = aerospike.client({"hosts": [(host, port)], "policies": {"timeout": 8000, "max_retries": 2}}).connect()
        self.ops = [op.read("data"), eo.expression_read("lut", exp.LastUpdateTime().compile())]

    def get(self, ms):
        """-> (raw|None, gen, lut_ns). CHI DOC."""
        key = (NS, SET, k7(ms))
        for i in range(3):
            try:
                _, meta, b = self.c.operate(key, self.ops)
                return b.get("data"), int(meta.get("gen", 0)), int(b.get("lut") or 0)
            except self.aerospike.exception.RecordNotFound:
                return None, 0, 0
            except Exception as e:
                log.warning("as get %s loi %s", k7(ms), e)
                time.sleep(1 + i)
        raise RuntimeError("as get FAIL " + k7(ms))

    def put_gen(self, ms, raw, gen):
        """Ghi bin data CHI KHI gen hien tai == gen (record khong bi ghi chen). False neu gen doi."""
        a = self.aerospike
        try:
            self.c.put((NS, SET, k7(ms)), {"data": bytearray(raw)}, meta={"gen": gen, "ttl": a.TTL_DONT_UPDATE},
                       policy={"gen": a.POLICY_GEN_EQ})
            return True
        except a.exception.RecordGenerationError:
            return False


# ------------------------------ ke hoach theo phut ------------------------------
FIELDS = ["open", "high", "low", "close", "quoteVolume"]


def plan_minute(cur, src, minute, fill_missing, st):
    """cur {short: v5} (242), src {short: {minute: v5}} -> {short: (old|None, new)}; cap nhat thong ke st."""
    ch = {}
    for s, old in cur.items():
        sv = src.get(s)
        if sv is None:
            continue                                   # symbol ngoai mau / khong co nguon
        new = sv.get(minute)
        if new is None:
            st["a_only"] += 1
            continue
        st["cells"] += 1
        if all(struct.pack("<f", a) == struct.pack("<f", b) for a, b in zip(old, new)):
            st["same"] += 1
        elif all(ulp_close(a, b) for a, b in zip(old, new)):
            st["ulp_only"] += 1
        else:
            st["diff"] += 1
            for f in range(5):
                if not ulp_close(old[f], new[f]):
                    st["f_" + FIELDS[f]] += 1
            ch[s] = (old, new)
    for s, sv in src.items():
        if s not in cur and minute in sv:
            st["v_only"] += 1
            if fill_missing:
                ch[s] = (None, sv[minute])
    return ch


def new_stats():
    st = {k: 0 for k in ["minutes", "minutes_missing_242", "minutes_changed", "cells", "same", "diff", "ulp_only",
                         "a_only", "v_only", "written", "gen_retry", "backup_bytes"]}
    st.update({"f_" + f: 0 for f in FIELDS})
    return st


def load_sources(shorts, d0, lo, hi, pool):
    """Nguon chuan cho cac phut [lo,hi) cua ngay +07 bat dau d0: Vision daily (UTC) hoac REST neu Vision chua phat hanh."""
    utc_days = sorted({datetime.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d") for t in (lo, hi - MN)})
    recent = (datetime.datetime.utcnow() - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    used = {"vision": 0, "rest": 0, "none": 0}

    def one(s):
        sym = s + "USDT"
        m = {}
        for u in utc_days:
            v = vision_day(sym, u)
            if v is None and u >= recent:
                u0 = int(datetime.datetime.strptime(u, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
                v = rest_range(sym, max(u0, lo), min(u0 + D, hi))
                used["rest"] += 1
            elif v is None:
                used["none"] += 1
                continue
            else:
                used["vision"] += 1
            m.update({k: x for k, x in v.items() if lo <= k < hi})
        return s, m

    def safe(s):
        try:
            return one(s)
        except RateLimitAbort:
            raise
        except Exception as e:
            log.error("nguon %s loi, bo symbol nay trong ngay: %s", s, e)
            used["err"] = used.get("err", 0) + 1
            return s, {}

    src = dict(pool.map(safe, shorts))
    return {s: m for s, m in src.items() if m}, used


def process_day(a, db, d0, lo, hi, sym_filter, pool):
    st = new_stats()
    mins = list(range(max(d0, lo), min(d0 + D, hi), MN))
    st["minutes"] = len(mins)
    if not mins:
        return st
    recs = dict(zip(mins, pool.map(db.get, mins)))
    cur = {}
    for ms, (raw, gen, lut) in recs.items():
        if raw is None:
            st["minutes_missing_242"] += 1
            continue
        cur[ms] = decode(raw)
    shorts = sorted({s for m in cur.values() for s in m} if sym_filter is None else sym_filter)
    src, used = load_sources(shorts, d0, mins[0], mins[-1] + MN, pool)
    day = k7(d0)[:8]
    bak = None
    if a.apply:
        os.makedirs(a.backup_dir, exist_ok=True)
        bak = gzip.open(os.path.join(a.backup_dir, "kline_bak_%s.jsonl.gz" % day), "ab")
    est = io.BytesIO()
    est_gz = gzip.GzipFile(fileobj=est, mode="wb")
    for ms in mins:
        if ms not in cur:
            continue
        ch = plan_minute(cur[ms], src, ms, a.fill_missing, st)
        if not ch:
            continue
        st["minutes_changed"] += 1
        line = (json.dumps({"key": k7(ms), "gen": recs[ms][1], "lut": recs[ms][2],
                            "cells": cells_json(ch)}) + "\n").encode()
        est_gz.write(line)
        if a.apply:
            write_minute(db, ms, recs[ms], ch, src, a, bak, st)
    est_gz.close()
    st["backup_bytes"] = len(est.getvalue())
    if bak:
        bak.close()
    log.info("ngay %s: %s | nguon %s", day, json.dumps(st), used)
    return st


def write_minute(db, ms, rec, ch, src, a, bak, st):
    """Backup TRUOC, roi put voi gen==gen da doc; gen doi (ingest ghi chen) => doc lai + tinh lai (<= 5 lan)."""
    raw, gen, lut = rec
    for attempt in range(5):
        if ms + MN > int(time.time() * 1000) - GUARD_MS:
            log.warning("bo phut %s: qua gan hien tai (live dang doc/ghi)", k7(ms))
            return
        m = decode(raw)
        for s, (o, n) in ch.items():
            m[s] = n
        bak.write((json.dumps({"key": k7(ms), "gen": gen, "lut": lut,
                               "cells": cells_json(ch)}) + "\n").encode())
        bak.flush()
        if db.put_gen(ms, encode(m), gen):
            st["written"] += 1
            return
        st["gen_retry"] += 1
        raw, gen, lut = db.get(ms)
        if raw is None:
            return
        ch = plan_minute(decode(raw), src, ms, a.fill_missing, new_stats())
        if not ch:
            return
    log.error("phut %s: gen doi lien tuc 5 lan — BO QUA (chay lai sau)", k7(ms))


def restore(a, db):
    """Tra o cu tu file backup (chi o hien con dung gia tri 'new' do backfill ghi)."""
    n = 0
    with gzip.open(a.restore, "rt") as f:
        for line in f:
            r = json.loads(line)
            ms = p7(r["key"])
            for attempt in range(5):
                raw, gen, _ = db.get(ms)
                if raw is None:
                    break
                m = decode(raw)
                for s, (o, nw) in r["cells"].items():
                    if s in m and tuple(map(f32, nw)) == m[s]:
                        if o is None:
                            del m[s]
                        else:
                            m[s] = tuple(o)
                if db.put_gen(ms, encode(m), gen):
                    n += 1
                    break
    log.info("restore xong: %d record", n)


def self_test():
    """Roundtrip encode/decode + quy tac ulp (khong mang)."""
    m = {"BTC": (f32(100.1), f32(101.2), f32(99.5), f32(100.9), f32(12345.6)), "ZERO": (0.0, 0.0, 0.0, 0.0, 0.0),
         "NEG0": (-0.0, f32(1.5), f32(1.0), f32(1.2), 0.0)}
    d = decode(encode(m))
    assert d == m and struct.pack("<f", d["NEG0"][0]) == struct.pack("<f", -0.0), d
    assert ulp_close(f32(1.0), struct.unpack("<f", struct.pack("<i", struct.unpack("<i", struct.pack("<f", 1.0))[0] + 1))[0])
    assert not ulp_close(f32(1.0), f32(1.0001))
    for x in (f32(2493.96), f32(8.542e-05), f32(0.026279), f32(12345.6), 0.0):
        assert struct.pack("<f", f32(sr(x))) == struct.pack("<f", x), x
    log.info("self-test OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="lo", default="20260425-0900", help="yyyyMMdd[-HHmm] gio +07")
    ap.add_argument("--to", dest="hi", default="now", help="yyyyMMdd[-HHmm] +07 hoac now (luon cat o now-10')")
    ap.add_argument("--days", help="danh sach ngay +07 yyyyMMdd,... (mau dry-run) thay cho --from/--to")
    ap.add_argument("--symbols-file", help="json list symbol (BTCUSDT) hoac {'syms': [...]} — gioi han mau")
    ap.add_argument("--apply", action="store_true", help="GHI len 242 (mac dinh dry-run)")
    ap.add_argument("--backup-dir", default="/home/ubuntu/kline_backfill_bak")
    ap.add_argument("--fill-missing", action="store_true", help="them o symbol 242 thieu (mac dinh KHONG)")
    ap.add_argument("--restore", help="file kline_bak_<day>.jsonl.gz -> tra o cu")
    ap.add_argument("--report", help="ghi JSON tong hop")
    ap.add_argument("--host", default="103.157.218.242")
    ap.add_argument("--port", type=int, default=3222)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--rest-max-weight", type=int, default=300, help="tran weight REST/phut cua script (IP Oracle dung chung)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    self_test()
    if a.self_test:
        return
    _REST_STATE["max_w"] = a.rest_max_weight
    db = AS(a.host, a.port)
    if a.restore:
        restore(a, db)
        return
    now_cut = (int(time.time() * 1000) - GUARD_MS) // MN * MN
    if a.days:
        spans = [(p7(d), p7(d), min(p7(d) + D, now_cut)) for d in a.days.split(",")]
    else:
        lo = p7(a.lo)
        hi = now_cut if a.hi == "now" else min(p7(a.hi), now_cut)
        d0 = p7(k7(lo)[:8])
        spans = [(d, lo, hi) for d in range(d0, hi, D)]
    sym_filter = None
    if a.symbols_file:
        js = json.load(open(os.path.expanduser(a.symbols_file)))
        lst = (js.get("syms") or js.get("symbols") or js.get("all")) if isinstance(js, dict) else js
        sym_filter = sorted({s[:-4] if s.endswith("USDT") else s for s in lst})
        log.info("mau %d symbol tu %s", len(sym_filter), a.symbols_file)
    log.info("MODE=%s, %d ngay, cat o %s", "APPLY" if a.apply else "DRY-RUN", len(spans), k7(now_cut))
    rep = {"mode": "apply" if a.apply else "dry-run", "days": {}}
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for d0, lo, hi in spans:
            rep["days"][k7(d0)[:8]] = process_day(a, db, d0, lo, hi, sym_filter, pool)
    tot = new_stats()
    for st in rep["days"].values():
        for k in tot:
            tot[k] += st[k]
    tot["diff_pct"] = 100.0 * tot["diff"] / max(tot["cells"], 1)
    for f in FIELDS:
        tot["f_%s_pct" % f] = 100.0 * tot["f_" + f] / max(tot["cells"], 1)
    rep["total"] = tot
    log.info("TONG: %s", json.dumps(tot))
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)


if __name__ == "__main__":
    main()
