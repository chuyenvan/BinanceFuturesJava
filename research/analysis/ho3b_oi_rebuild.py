#!/usr/bin/env python3
"""HO3b cong 3 (ADDENDUM-4 §4a, 62c0cd67): dung lai OI per-coin tu Vision daily metrics, TOAN lich su moi coin.
Port VisionMetricsClient.parseDay (+ quy uoc nhan theo (symbol, ngay-file)) + ExportFundingOiPerCoin.writeCoin.
Ghi ban ghi ts in [EMIT_LO, EMIT_HI) UTC, format file ghim (BE ts i64, sym i16, 5 x f32), 1 file/symbol trong OUTD.
Chi dem/kiem toan ven; KHONG in gia tri. Resume: bo qua symbol da co file .done.
Usage: python3 ho3b_oi_rebuild.py <outdir> [n_sym_workers=4] [threads_per_sym=12]"""
import io, json, logging, os, re, sys, time, urllib.request, urllib.parse, zipfile
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho3b_oi")
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
BASE = "https://data.binance.vision/"
PREF = "data/futures/um/daily/metrics/"
DAY, STALE, STEP = 86400000, 3600000, 300000
EMIT_LO = int(pd.Timestamp("2025-12-29", tz="UTC").value // 10**6)
EMIT_HI = int(pd.Timestamp("2026-10-01", tz="UTC").value // 10**6)
LAST_DATE = "2026-09-30"
ODT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
COLS = (3, 4, 6, 7)          # OI value, LS toptrader acc, LS global acc, taker (OiMetricSets col)
KEYRX = re.compile(r"<Key>(.*?)</Key>")
DRX = re.compile(r"-metrics-(\d{4}-\d{2}-\d{2})\.zip$")
NXT = re.compile(r"<NextMarker>(.*?)</NextMarker>")


def http(url, tries=4):
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "oi-backfill/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(0.7 * (a + 1))
    raise IOError("tai that bai %s: %s" % (url, last))


def list_dates(sym):
    out, marker, pages = set(), "", 0
    while True:
        url = S3 + "?prefix=" + PREF + sym + "/" + ("&marker=" + urllib.parse.quote(marker) if marker else "")
        x = (http(url) or b"").decode("utf-8", "ignore")
        pages += 1
        last = None
        for k in KEYRX.findall(x):
            last = k
            if k.endswith(".CHECKSUM"):
                continue
            m = DRX.search(k)
            if m:
                out.add(m.group(1))
        if "<IsTruncated>true</IsTruncated>" not in x or pages > 200:
            break
        m = NXT.search(x)
        marker = m.group(1) if (m and m.group(1)) else last
        if not marker:
            break
    return sorted(d for d in out if d <= LAST_DATE)


def fbits(s):
    s = s.strip()
    if not s:
        return np.nan
    try:
        v = np.float32(float(s))
    except ValueError:
        return np.nan
    return v if np.isfinite(v) else np.nan


_DC = {}


def parse_ct(s):
    """= VisionMetricsClient.parseCreateTime: epoch (s/ms) hoac 'yyyy-MM-dd HH:mm:ss' UTC; -1 neu hong (header)."""
    s = s.strip()
    if not s:
        return -1
    if s.isdigit() and len(s) >= 10:
        v = int(s)
        return v * 1000 if len(s) <= 11 else v
    if len(s) < 19 or s[4] != "-" or s[13] != ":":
        return -1
    try:
        b = _DC.get(s[:10])
        if b is None:
            b = _DC[s[:10]] = int(pd.Timestamp(s[:10], tz="UTC").value // 10**6)
        return b + int(s[11:13]) * 3600000 + int(s[14:16]) * 60000 + int(s[17:19]) * 1000
    except Exception:  # noqa: BLE001
        return -1


def parse_day(sym, d):
    """-> (ts np.int64 [n], vals f32 [n,4], conv) hoac None (404/rong). ts da normalize5m + dich theo quy uoc file."""
    b = http("%s%s%s/%s-metrics-%s.zip" % (BASE, PREF, sym, sym, d))
    if b is None:
        return None
    z = zipfile.ZipFile(io.BytesIO(b))
    txt = z.read(z.namelist()[0]).decode("utf-8", "ignore")
    T, V = [], []
    for ln in txt.split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        p = ln.split(",")
        if len(p) < 8:
            continue
        ct = parse_ct(p[0])
        if ct <= 0:
            continue
        T.append(((ct + STEP // 2) // STEP) * STEP)   # Math.round
        V.append([fbits(p[c]) if c < len(p) else np.nan for c in COLS])
    if not T:
        return None
    t = np.array(T, dtype=np.int64)
    day0 = int(pd.Timestamp(d, tz="UTC").value // 10**6)
    omin, omax = int(t.min() - day0), int(t.max() - day0)
    if omin == 0:
        conv = "NEW"
    elif omin == STEP:
        conv = "OLD"
    else:
        conv = "OLD_MID" if omax == DAY else "NEW_MID"
    if conv.startswith("NEW"):
        t = t + STEP
    return t, np.array(V, dtype=np.float32), conv


def write_coin(sym, sid, maps, fo):
    """maps: 4 x (ts sorted unique, val f32) theo COLS. Port writeCoin. Tra so dong emit + dem null."""
    oi_t, oi_v = maps[0]
    if len(oi_t) == 0:
        return 0, [0] * 5
    v64 = oi_v.astype(np.float64)
    s1 = np.cumsum(v64)                       # Java: sum += oiVal (tuan tu)
    s2 = np.cumsum(v64 * v64)
    n = np.arange(1, len(oi_t) + 1, dtype=np.float64)
    em = (oi_t >= EMIT_LO) & (oi_t < EMIT_HI)
    if not em.any():
        return 0, [0] * 5
    idx = np.nonzero(em)[0]
    t = oi_t[idx]
    cur = oi_v[idx]
    # oiDelta24h
    j = np.searchsorted(oi_t, t - DAY, side="right") - 1
    jj = np.clip(j, 0, None)
    ok = (j >= 0) & ((t - DAY - oi_t[jj]) <= STALE) & (oi_v[jj] != np.float32(0))
    with np.errstate(all="ignore"):
        dlt = np.where(ok, cur / np.where(ok, oi_v[jj], np.float32(1)) - np.float32(1), np.nan).astype(np.float32)
    # oiZ expanding
    nn, a, b = n[idx], s1[idx], s2[idx]
    with np.errstate(all="ignore"):
        mean = a / nn
        var = (b - (a * a) / nn) / (nn - 1)
        z = np.where((nn >= 2) & (var > 0), (cur.astype(np.float64) - mean) / np.sqrt(var), np.nan).astype(np.float32)

    def fs(k):
        mt, mv = maps[k]
        if len(mt) == 0:
            return np.full(len(t), np.nan, dtype=np.float32)
        q = np.searchsorted(mt, t, side="right") - 1
        qq = np.clip(q, 0, None)
        okq = (q >= 0) & ((t - mt[qq]) <= STALE)
        return np.where(okq, mv[qq], np.nan).astype(np.float32)
    lst, lsg, tk = fs(1), fs(2), fs(3)
    with np.errstate(all="ignore"):
        tb = np.where(tk >= 0, tk / (np.float32(1) + tk), np.nan).astype(np.float32)
    out = np.zeros(len(t), dtype=ODT)
    out["ts"] = t
    out["sym"] = sid
    out["oi"] = np.stack([dlt, z, lsg, lst, tb], axis=1)
    out.tofile(fo)
    nul = [int(np.isnan(x).sum()) for x in (dlt, z, lsg, lst, tb)]
    return len(t), nul


def do_symbol(sym, sid, outd, threads):
    p_out, p_done = os.path.join(outd, "%s.bin" % sym), os.path.join(outd, "%s.done" % sym)
    if os.path.exists(p_done):
        return json.load(open(p_done))
    t0 = time.time()
    dates = list_dates(sym)
    meta = dict(sym=sym, sid=int(sid), n_dates=len(dates), first=dates[0] if dates else None,
                last=dates[-1] if dates else None, conv={}, empty=0, fail=[], rows=0, null=[0] * 5)
    if not dates or dates[-1] < "2025-12-28":
        meta["skip"] = "khong co file trong cua so"
        json.dump(meta, open(p_done, "w"))
        return meta
    with ThreadPoolExecutor(threads) as ex:
        futs = [(d, ex.submit(parse_day, sym, d)) for d in dates]
        parts = []
        for d, f in futs:
            try:
                r = f.result()
            except Exception as e:  # noqa: BLE001
                meta["fail"].append([d, str(e)[:80]])
                continue
            if r is None:
                meta["empty"] += 1
                continue
            t, v, cv = r
            meta["conv"][cv] = meta["conv"].get(cv, 0) + 1
            parts.append((t, v))
    maps = []
    if parts:
        T = np.concatenate([p[0] for p in parts])
        V = np.concatenate([p[1] for p in parts])
        for k in range(4):
            ok = ~np.isnan(V[:, k])
            t, v = T[ok], V[ok, k]
            # dedup: ts trung => ban ghi SAU (file sau) ghi de (TreeMap.put theo thu tu ngay)
            rt, rv = t[::-1], v[::-1]
            u, i0 = np.unique(rt, return_index=True)
            maps.append((u, rv[i0]))
    else:
        maps = [(np.zeros(0, np.int64), np.zeros(0, np.float32))] * 4
    with open(p_out + ".tmp", "wb") as fo:
        meta["rows"], meta["null"] = write_coin(sym, sid, maps, fo)
    os.replace(p_out + ".tmp", p_out)
    meta["secs"] = round(time.time() - t0, 1)
    json.dump(meta, open(p_done, "w"))
    return meta


def _job(it):
    return do_symbol(*it)


def main():
    outd = sys.argv[1]
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    th = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    os.makedirs(outd, exist_ok=True)
    smap = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
    items = list(zip(smap.symbol.astype(str), smap.symId.astype(int)))
    if os.environ.get("HO3B_SYMS"):
        keep = set(os.environ["HO3B_SYMS"].split(","))
        items = [it for it in items if it[0] in keep]
    log.info("universe %d symbol, emit [%d,%d)", len(items), EMIT_LO, EMIT_HI)
    for rnd in (1, 2):
        if rnd == 2:
            for sym, _ in items:
                pd_ = os.path.join(outd, "%s.done" % sym)
                if os.path.exists(pd_) and json.load(open(pd_)).get("fail"):
                    os.remove(pd_)
                    log.info("retry %s", sym)
        done = 0
        with ProcessPoolExecutor(nw) as ex:
            for m in ex.map(_job, [(a, b, outd, th) for a, b in items]):
                done += 1
                if done % 25 == 0 or m.get("fail"):
                    log.info("r%d %d/%d %s rows=%d dates=%d fail=%d conv=%s", rnd, done, len(items), m["sym"],
                             m["rows"], m["n_dates"], len(m["fail"]), m["conv"])
    S = [json.load(open(os.path.join(outd, "%s.done" % s))) for s, _ in items]
    tot = dict(n_sym=len(S), n_skip=sum(1 for m in S if m.get("skip")), rows=sum(m["rows"] for m in S),
               n_fail_sym=sum(1 for m in S if m["fail"]), fail_sym=[m["sym"] for m in S if m["fail"]],
               conv={}, n_dates=sum(m["n_dates"] for m in S), empty=sum(m["empty"] for m in S),
               null=[sum(m["null"][k] for m in S) for k in range(5)])
    for m in S:
        for k, v in m["conv"].items():
            tot["conv"][k] = tot["conv"].get(k, 0) + v
    json.dump(dict(total=tot, per_sym=S), open(os.path.join(outd, "SUMMARY.json"), "w"), indent=0)
    log.info("XONG %s", json.dumps(tot))


if __name__ == "__main__":
    main()
