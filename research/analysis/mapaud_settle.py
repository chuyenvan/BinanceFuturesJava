#!/usr/bin/env python3
"""MAPAUD M4: ra 130 symbol "duoi settle" (ho4p1_excl26.json / no_funding_union.json) bang nguon doc lap.
Nguon: Binance Vision kline 1d (monthly 2026-01..09 + daily 2026-10-01..10), Aerospike 242 kline_1m_opt mau 1 phut/ngay
(CHI DOC), 242 symbol_lifecycle (CHI DOC), exchange_info_pin.json (2026-09-03). Khong gia/loi nhuan sim.
Luat phan loai (co dinh truoc khi chay):
  nham   : co volume > 0 sau ngay bat dau duoi (Vision ngay >= from_day+1) HOAC 242 volume>0 sau from_ts o >= 2 ngay mau
  dung   : khong co volume sau from_day (Vision & 242) VA (pin != TRADING hoac lifecycle != LIVE hoac Vision het file)
  khong_ro: con lai
Usage: mapaud_settle.py <out_dir> [--denom]"""
import io, json, logging, re, sys, time, urllib.parse, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("settle")
OUT = sys.argv[1]
DENOM = "--denom" in sys.argv
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DV = "https://data.binance.vision/data/futures/um"
MONTHS = ["2026-%02d" % m for m in range(1, 10)]
OCT_DAYS = ["2026-10-%02d" % d for d in range(1, 11)]
TAIL = json.load(open("/home/ubuntu/claude_master/1011/ho4p1/no_funding_union.json"))["settle_tail"]
SYMS = sorted(TAIL)
TZ7 = timezone(timedelta(hours=7))


def http(u):
    for a in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "mapaud"}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 2 * a)
        except Exception:  # noqa: BLE001
            time.sleep(2 + 2 * a)
    raise IOError(u)


def rows_1d(b):
    """zip kline 1d -> list (day_str_utc, quote_volume, n_trades)."""
    if b is None:
        return []
    z = zipfile.ZipFile(io.BytesIO(b))
    out = []
    for line in z.read(z.namelist()[0]).decode().splitlines():
        f = line.split(",")
        if not f or not f[0].strip().isdigit():
            continue  # header
        ts = int(f[0]); ts = ts // 1000 if ts > 10 ** 14 else ts
        out.append((datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%Y-%m-%d"), float(f[7]), int(float(f[8]))))
    return out


def vision_sym(s):
    q = urllib.parse.quote(s)
    rows = []
    for m in MONTHS:
        rows += rows_1d(http("%s/monthly/klines/%s/1d/%s-1d-%s.zip" % (DV, q, q, m)))
    for d in OCT_DAYS:
        rows += rows_1d(http("%s/daily/klines/%s/1d/%s-1d-%s.zip" % (DV, q, q, d)))
    return s, rows


def list_syms(pref):
    out, marker = set(), ""
    while True:
        x = http(S3 + "?delimiter=/&prefix=" + pref + ("&marker=" + urllib.parse.quote(marker) if marker else "")).decode()
        ps = re.findall(r"<Prefix>(.*?)</Prefix>", x)
        out |= {urllib.parse.unquote(p[len(pref):].strip("/")) for p in ps if p[len(pref):].strip("/")}
        if "<IsTruncated>true</IsTruncated>" not in x:
            break
        m = re.search(r"<NextMarker>(.*?)</NextMarker>", x)
        marker = m.group(1) if m else ps[-1]
    return sorted(out)


def month_qv(s):
    q = urllib.parse.quote(s); r = {}
    for m in MONTHS:
        r[m] = sum(v for _, v, _ in rows_1d(http("%s/monthly/klines/%s/1d/%s-1d-%s.zip" % (DV, q, q, m))))
    return s, r


def as242():
    """Mau 1 phut/ngay (12:00 +07) 2026-01-01..2026-10-10 tren 242 kline_1m_opt (CHI DOC) + lifecycle."""
    import aerospike, snappy
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import aprobe
    c = aerospike.client({"hosts": [("103.157.218.242", 3222)], "policies": {"read": {"total_timeout": 20000}}}).connect()
    seen = {s: [] for s in SYMS}
    d0 = datetime(2026, 1, 1, 12, 0, tzinfo=TZ7); n_rec = 0
    for i in range((datetime(2026, 10, 10, tzinfo=TZ7) - d0).days + 1):
        t = d0 + timedelta(days=i); k = t.strftime("%Y%m%d-%H%M")
        try:
            _, _, b = c.get(("ticker", "kline_1m_opt", k))
            mp = aprobe.parse_map(snappy.decompress(b["data"])); n_rec += 1
        except Exception as e:  # noqa: BLE001
            log.info("242 %s: %s", k, str(e)[:80]); continue
        for s in SYMS:
            v = mp.get(s) or mp.get(s[:-4])
            if v is not None:
                seen[s].append((t.strftime("%Y-%m-%d"), int(t.timestamp() * 1000), float(v[4] or 0.0)))
    lc = {}
    for s in SYMS:
        try:
            _, _, b = c.get(("ticker", "symbol_lifecycle", s))
            lc[s] = {k: b.get(k) for k in ("status", "first", "last", "delist") if k in b}
        except Exception as e:  # noqa: BLE001
            lc[s] = {"err": str(e)[:60]}
    c.close()
    return seen, lc, n_rec


def pin_status():
    d = json.load(open("/home/ubuntu/java/exchange_info_pin.json"))
    syms = d.get("symbols", d) if isinstance(d, dict) else d
    out = {}
    for x in syms:
        if isinstance(x, dict) and "symbol" in x:
            out[x["symbol"]] = {k: x.get(k) for k in ("status", "deliveryDate", "onboardDate", "contractType")}
    return out


def main():
    with ThreadPoolExecutor(8) as ex:
        vis = dict(ex.map(vision_sym, SYMS))
    log.info("vision xong %d", len(vis))
    seen, lc, n_rec = as242()
    log.info("242 xong: %d record mau", n_rec)
    pin = pin_status()
    res = {}
    for s in SYMS:
        t = TAIL[s]; fts = int(t["from_ts"])
        fday = datetime.fromtimestamp(fts / 1000, timezone.utc).strftime("%Y-%m-%d")
        nday = (datetime.fromtimestamp(fts / 1000, timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
        rows = vis[s]
        last_row = max((d for d, _, _ in rows), default=None)
        last_nz = max((d for d, v, _ in rows if v > 0), default=None)
        after = [(d, v) for d, v, _ in rows if d >= nday and v > 0]
        cut_qv = sum(v for d, v in after if d <= "2026-09-30")
        cut_by_m = {}
        for d, v in after:
            if d <= "2026-09-30":
                cut_by_m[d[:7]] = cut_by_m.get(d[:7], 0.0) + v
        a242 = [x for x in seen[s] if x[1] > fts]
        a242_nz = sorted({d for d, _, v in a242 if v > 0})
        last242 = max((d for d, _, _ in seen[s]), default=None)
        last242_nz = max((d for d, _, v in seen[s] if v > 0), default=None)
        p = pin.get(s, {}).get("status")
        l = lc[s].get("status")
        if after or len(a242_nz) >= 2:
            cls = "nham"
        elif (p != "TRADING") or (l not in (None, "LIVE")) or (last_row is not None and last_row < "2026-10-10"):
            cls = "dung"
        else:
            cls = "khong_ro"
        res[s] = dict(cls=cls, from_ts=fts, from_day=fday, last_trade_ts=t.get("last_trade_ts"), vision_last_row=last_row,
                      vision_last_nonzero=last_nz, vision_days_vol_after=len(after),
                      vision_first_vol_after=(after[0][0] if after else None), cut_qv_2026q1q3=cut_qv,
                      cut_qv_by_month=cut_by_m, a242_days_vol_after=len(a242_nz), a242_last_present=last242,
                      a242_last_nonzero=last242_nz, pin_status=p, lifecycle=lc[s])
    out = dict(n=len(res), n_rec_242=n_rec, rule=__doc__.split("Luat phan loai")[1].split("Usage")[0].strip(),
               counts={k: sum(1 for r in res.values() if r["cls"] == k) for k in ("dung", "nham", "khong_ro")}, syms=res)
    if DENOM:
        mp = set(pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv").symbol)
        uni = [s for s in list_syms("data/futures/um/monthly/klines/") if s.endswith("USDT") and re.fullmatch(r"[A-Z0-9]+", s)
               and s not in ("BTCDOMUSDT", "USDCUSDT") and s in mp]
        with ThreadPoolExecutor(8) as ex:
            mq = dict(ex.map(month_qv, uni))
        tot = {m: sum(r[m] for r in mq.values()) for m in MONTHS}
        out["universe_n"] = len(uni); out["universe_qv_by_month"] = tot
        nh = [s for s, r in res.items() if r["cls"] == "nham"]
        out["nham_cut_share_by_month"] = {m: (sum(res[s]["cut_qv_by_month"].get(m, 0.0) for s in nh) / tot[m] if tot[m] else None) for m in MONTHS}
    json.dump(out, open(OUT + "/mapaud_settle.json", "w"), indent=1, sort_keys=True)
    log.info("XONG counts=%s", out["counts"])


if __name__ == "__main__":
    main()
