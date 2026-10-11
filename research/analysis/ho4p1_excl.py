#!/usr/bin/env python3
"""HO4-P1 (ADDENDUM-6 §6.2/§6.5, R24): liet ke symbol bi loai 2026 + ti trong quote volume loai theo thang (Vision kline 1d,
chi tong volume — khong gia/loi nhuan) + so lenh ho26 (48 run, start >= 2026-01-01, chi cot sym/start) cua nhom thieu funding.
Usage: ho4p1_excl.py <no_funding.json> <out.json>   (no_funding.json = {"no_funding_vision": [...], "settle_tail": {...}})"""
import csv, glob, io, json, logging, re, sys, time, urllib.parse, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("excl")
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
MONTHS = ["2026-%02d" % m for m in range(1, 10)]
MAPPER = set(pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv").symbol)
DIED = {"BTCDOMUSDT", "USDCUSDT"}


def http(u):
    for a in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ho4p1"}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 2 * a)
        except Exception:  # noqa: BLE001
            time.sleep(2 + 2 * a)
    raise IOError(u)


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


def cls(s):
    if not s.endswith("USDT"):
        return None
    if re.fullmatch(r"[A-Z0-9]+", s) is None:
        return "regex"
    if s in DIED:
        return "died"
    if s not in MAPPER:
        return "no_mapper"
    return "uni"


def vol(sym_m):
    s, m = sym_m
    b = http("https://data.binance.vision/data/futures/um/monthly/klines/%s/1d/%s-1d-%s.zip" % (urllib.parse.quote(s), urllib.parse.quote(s), m))
    if b is None:
        return s, m, None
    z = zipfile.ZipFile(io.BytesIO(b))
    v = 0.0
    for ln in z.read(z.namelist()[0]).decode().splitlines():
        p = ln.split(",")
        if p and p[0].strip().isdigit():
            v += float(p[7])
    return s, m, v


def ho26_trades(syms):
    """So lenh start >= 2026-01-01 cua tung symbol trong 48 run ho26 (chi doc cot sym/start)."""
    cnt, runs = {}, {}
    for p in sorted(glob.glob("/home/ubuntu/kaggle_sim/out/ho26-*-s*/storage/printDone.csv")):
        run = p.split("/")[-3]
        with open(p, newline="") as f:
            r = csv.reader(f)
            h = next(r)
            i_s, i_t = h.index("sym"), h.index("start")
            for row in r:
                if len(row) > max(i_s, i_t) and row[i_t].strip() >= "20260101 00:00":
                    s = row[i_s].strip()
                    s = s if s.endswith("USDT") else s + "USDT"
                    if s in syms:
                        cnt[s] = cnt.get(s, 0) + 1
                        runs.setdefault(s, set()).add(run)
    return {s: dict(n=cnt[s], runs=len(runs[s])) for s in sorted(cnt)}, len(glob.glob("/home/ubuntu/kaggle_sim/out/ho26-*-s*/storage/printDone.csv"))


def main():
    nf = json.load(open(sys.argv[1]))
    syms = list_syms("data/futures/um/monthly/klines/")
    C = {s: cls(s) for s in syms if cls(s)}
    jobs = [(s, m) for s in C for m in MONTHS]
    with ThreadPoolExecutor(24) as ex:
        R = list(ex.map(vol, jobs))
    V = {}
    for s, m, v in R:
        if v is not None:
            V.setdefault(m, {})[s] = v
    nof = set(nf.get("no_funding_vision", []))
    tail = set(nf.get("settle_tail", {}))
    by_month = {}
    for m in MONTHS:
        tot = sum(V.get(m, {}).values())
        g = {}
        for s, v in V.get(m, {}).items():
            k = C[s] if C[s] != "uni" else ("uni_no_funding" if s in nof else "uni")
            g[k] = g.get(k, 0.0) + v
        by_month[m] = {k: dict(share=round(g[k] / tot, 6), n_sym=sum(1 for s in V[m] if (C[s] if C[s] != "uni" else ("uni_no_funding" if s in nof else "uni")) == k)) for k in sorted(g)} if tot else {}
    present = {s for m in MONTHS for s in V.get(m, {})}
    tr, nruns = ho26_trades(nof)
    out = dict(prereg="ADDENDUM-6 af6d6c94", months=MONTHS,
               excluded_no_mapper=sorted(s for s in present if C[s] == "no_mapper"),
               excluded_died=sorted(s for s in present if C[s] == "died"), excluded_regex=sorted(s for s in present if C[s] == "regex"),
               no_funding_vision_trading_excluded=sorted(nof), settle_tail_symbols=sorted(tail),
               volume_share_by_month=by_month, ho26_trades_no_funding=tr, ho26_runs_scanned=nruns)
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    log.info("EXCL no_mapper=%d died=%d regex=%d no_funding=%d tail=%d ho26_trades=%s", len(out["excluded_no_mapper"]),
             len(out["excluded_died"]), len(out["excluded_regex"]), len(nof), len(tail), tr)


if __name__ == "__main__":
    main()
