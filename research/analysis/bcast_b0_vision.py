#!/usr/bin/env python3
"""BCAST B0 — kha thi Vision futures/um cho kho backcast 2019-12..2021-06 (chi LIET KE file, khong tai du lieu gia).
Ra: so symbol/thang co klines 1m monthly, fundingRate monthly, aggTrades monthly; metrics daily tu khi nao; doi chieu mapper 863.
Usage: bcast_b0_vision.py <cfg_mapper.json> <out.json>"""
import json, logging, re, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bcast_b0")
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DIED = {"BTCDOMUSDT", "USDCUSDT"}
LO, HI = "2019-09", "2021-12"


def http(u):
    for a in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "bcast"}), timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * a)
        except Exception:
            time.sleep(2 + 3 * a)
    raise IOError("HTTP_FAIL " + u)


def listing(pref, dirs):
    out, marker = [], ""
    while True:
        x = http(S3 + "?delimiter=/&prefix=" + urllib.parse.quote(pref) + ("&marker=" + urllib.parse.quote(marker) if marker else "")).decode()
        if dirs:
            ps = re.findall(r"<Prefix>(.*?)</Prefix>", x)
            out += [urllib.parse.unquote(p[len(pref):].strip("/")) for p in ps if p[len(pref):].strip("/")]
        else:
            ps = re.findall(r"<Key>(.*?)</Key>", x)
            out += [urllib.parse.unquote(p) for p in ps]
        if "<IsTruncated>true</IsTruncated>" not in x:
            break
        m = re.search(r"<NextMarker>(.*?)</NextMarker>", x)
        marker = m.group(1) if m else (ps[-1] if ps else "")
        if not marker:
            break
    return out


def months_of(keys, pat):
    ms = set()
    for k in keys:
        m = re.search(pat, k)
        if m and not k.endswith(".CHECKSUM"):
            ms.add(m.group(1))
    return sorted(ms)


def one(s):
    kl = months_of(listing("data/futures/um/monthly/klines/%s/1m/" % s, False), r"-1m-(\d{4}-\d{2})\.zip")
    if not kl or kl[0] > HI:
        return s, dict(kl=kl)
    fr = months_of(listing("data/futures/um/monthly/fundingRate/%s/" % s, False), r"-fundingRate-(\d{4}-\d{2})\.zip")
    ag = months_of(listing("data/futures/um/monthly/aggTrades/%s/" % s, False), r"-aggTrades-(\d{4}-\d{2})\.zip")
    mt = []
    for y in ("2020", "2021"):
        mt += listing("data/futures/um/daily/metrics/%s/%s-metrics-%s" % (s, s, y), False)
    mtd = sorted(set(re.search(r"-metrics-(\d{4}-\d{2}-\d{2})\.zip", k).group(1) for k in mt if k.endswith(".zip")))
    return s, dict(kl=kl, fr=fr, ag=ag, metrics_first=(mtd[0] if mtd else None), metrics_n_2020_21=len(mtd))


def main():
    mapper = set(json.load(open(sys.argv[1]))["mapper"])
    t0 = time.time()
    allk = listing("data/futures/um/monthly/klines/", True)
    uni = sorted(s for s in allk if s.endswith("USDT") and re.fullmatch(r"[A-Z0-9]+", s) and s not in DIED)
    log.info("klines dirs %d, USDT-universe-filter %d (%.0fs)", len(allk), len(uni), time.time() - t0)
    with ThreadPoolExecutor(12) as ex:
        res = dict(ex.map(one, uni))
    log.info("listing xong (%.0fs)", time.time() - t0)
    months = []
    y, m = 2019, 9
    while "%04d-%02d" % (y, m) <= HI:
        months.append("%04d-%02d" % (y, m)); m += 1
        if m == 13:
            y, m = y + 1, 1
    per = {}
    for mo in months:
        ks = [s for s, r in res.items() if mo in r["kl"]]
        per[mo] = dict(n_kl=len(ks), n_kl_in_mapper=sum(s in mapper for s in ks),
                       n_fr=sum(mo in res[s].get("fr", []) for s in ks), n_ag=sum(mo in res[s].get("ag", []) for s in ks),
                       not_in_mapper=sorted(s for s in ks if s not in mapper))
        log.info("%s kl=%d inmap=%d fr=%d ag=%d", mo, per[mo]["n_kl"], per[mo]["n_kl_in_mapper"], per[mo]["n_fr"], per[mo]["n_ag"])
    early = {s: r for s, r in res.items() if r["kl"] and r["kl"][0] <= "2021-06"}
    mf = sorted((r.get("metrics_first") or "none") for r in early.values())
    out = dict(n_dirs=len(allk), n_uni=len(uni), per_month=per, early_syms=early,
               metrics_first_min=(min([x for x in mf if x != "none"]) if any(x != "none" for x in mf) else None),
               metrics_none=sorted(s for s, r in early.items() if not r.get("metrics_first")),
               mapper_n=len(mapper), elapsed=time.time() - t0)
    json.dump(out, open(sys.argv[2], "w"), indent=1, sort_keys=True)
    log.info("XONG early=%d metrics_first_min=%s metrics_none=%d", len(early), out["metrics_first_min"], len(out["metrics_none"]))


if __name__ == "__main__":
    main()
