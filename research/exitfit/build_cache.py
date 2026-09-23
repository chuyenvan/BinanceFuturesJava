"""EXIT FIT — BUOC 1a: build bar-cache ngoai repo (resume duoc).

Doc printDone.csv (leg) cua T170 -> gom thanh CUM (sym, end) -> xac dinh cua so nen 1m can thiet
[firstLegStart - 300', firstLegStart + 169h] -> doc ticker_YYYYMMDD.bin.gz (nguon y het sim:
TICKER_SOURCE=file) -> ghi cache/part_<YYYYMMDD>.pkl (cluster_id -> ts[], OHLC[float32]).

Chay:  python3 build_cache.py            # resume: part nao co roi thi bo qua
Output: /home/ubuntu/exitfit/cache/part_*.pkl ; /home/ubuntu/exitfit/clusters.json
"""
import csv
import gzip
import json
import os
import pickle
import struct
import sys
import time
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "research", "analysis"))
import jbin  # noqa: E402

PRINT_DONE = "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv"
TICKER_DIR = "/home/ubuntu/java/simulator/kaggle_data_hpo/daily"
OUT = "/home/ubuntu/exitfit"
CACHE = os.path.join(OUT, "cache")
DAY = 86400000
GMT7 = 7 * 3600000
PRE_MIN = 300          # so phut nen TRUOC leg dau (cho ATR/rolling cua policy)
POST_H = 169           # gio nen SAU leg dau (time-stop 168h + 1)


def parse_t(s):
    # 'YYYYMMDD HH:MM' gio GMT+7 (sim ep Asia/Ho_Chi_Minh)
    y, mo, d = int(s[0:4]), int(s[4:6]), int(s[6:8])
    hh, mm = int(s[9:11]), int(s[12:14])
    import datetime as dt
    return int(dt.datetime(y, mo, d, hh, mm, tzinfo=dt.timezone.utc).timestamp()) * 1000 - GMT7


def load_clusters():
    rows = list(csv.DictReader(open(PRINT_DONE)))
    for r in rows:
        r["_ts"] = parse_t(r["start"])
        r["_end"] = parse_t(r["end"])
        r["_entry"] = float(r["entry"])
        r["_qty"] = float(r["quantity"])
        r["_pnl"] = float(r["pnl"])
        r["_funding"] = float(r["funding"])
        r["_pred"] = None if r["symbolPred"] in ("null", "") else float(r["symbolPred"])
    clusters = {}
    for r in rows:
        key = (r["sym"], r["_end"])
        clusters.setdefault(key, []).append(r)
    out = []
    for i, (key, legs) in enumerate(clusters.items()):
        legs.sort(key=lambda x: x["_ts"])
        out.append({
            "cid": i,
            # printDone ghi sym = symbol.replace("USDT","") => khoi phuc lai ten day du cho ticker
            "sym": key[0] + "USDT",
            "end": key[1],
            "legs": [{"ts": l["_ts"], "entry": l["_entry"], "qty": l["_qty"], "pnl": l["_pnl"],
                      "funding": l["_funding"], "pred": l["_pred"], "status": l["status"],
                      "tp": float(l["tp"]), "profit": float(l["profit"]), "level": l["level"]}
                     for l in legs],
        })
    return out


def t_day(ms):
    return ms // DAY


def day_file(day):
    import datetime as dt
    s = dt.datetime.utcfromtimestamp(day * 86400).strftime("%Y%m%d")
    p = os.path.join(TICKER_DIR, "ticker_%s.bin.gz" % s)
    return p if os.path.exists(p) else None


def work(day):
    part = os.path.join(CACHE, "part_%d.pkl" % day)
    if os.path.exists(part):
        return ("skip", day)
    need_path = os.path.join(OUT, "need_%d.json" % day)
    if not os.path.exists(need_path):
        return ("none", day)
    need = json.load(open(need_path))          # sym -> [cid,...]
    p = day_file(day)
    if p is None:
        json.dump({}, open(part + ".missing", "w"))
        return ("nofile", day)
    with gzip.open(p, "rb") as g:
        b = g.read()
    acc = {cid: [[], [], [], [], []] for cids in need.values() for cid in cids}
    nmin = 0
    for k, v in jbin.iter_minutes(b):
        nmin += 1
        for sym, cids in need.items():
            t = v.get(sym)
            if t is None:
                continue
            st, hi, lo, cl, op, _vol = t
            for cid in cids:
                a = acc[cid]
                a[0].append(k)
                a[1].append(op)
                a[2].append(hi)
                a[3].append(lo)
                a[4].append(cl)
    res = {}
    for cid, a in acc.items():
        if a[0]:
            res[cid] = (np.asarray(a[0], dtype=np.int64),
                        np.asarray(a[1:], dtype=np.float32).T)   # (n,4) = o,h,l,c
    with open(part, "wb") as f:
        pickle.dump({"day": day, "nmin": nmin, "bars": res}, f, protocol=4)
    return ("ok", day, nmin, len(res))


def main():
    os.makedirs(CACHE, exist_ok=True)
    clusters = load_clusters()
    json.dump(clusters, open(os.path.join(OUT, "clusters.json"), "w"))
    print("clusters=%d legs=%d" % (len(clusters), sum(len(c["legs"]) for c in clusters)))
    days = {}
    for c in clusters:
        t0 = c["legs"][0]["ts"]
        d0 = t_day(t0 - PRE_MIN * 60000)
        d1 = t_day(t0 + POST_H * 3600000)
        for d in range(d0, d1 + 1):
            days.setdefault(d, {}).setdefault(c["sym"], []).append(c["cid"])
    print("days=%d" % len(days))
    for d, m in days.items():
        json.dump(m, open(os.path.join(OUT, "need_%d.json" % d), "w"))
    t0 = time.time()
    todo = [d for d in sorted(days)]
    with Pool(4) as pool:
        for i, r in enumerate(pool.imap_unordered(work, todo, chunksize=4)):
            if r[0] == "ok" and i % 100 == 0:
                print("  [%d/%d] %s %.0fs" % (i, len(todo), r, time.time() - t0), flush=True)
    print("DONE %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
