#!/usr/bin/env python3
"""E2E_REPLAY (docs/c3live/E2E_REPLAY.md §2) — dung fixture cho harness Java tu du lieu CO SAN tren Oracle (khong mang).

argv: <out_dir>. Doc: pull242/<D>/dumps/sel_dump_*, pull242/<D>/logs/full.log@*, pull242/2026-10-31/run/gate_ratio_live.bin.gz,
Vision klines_1m zip, fixture exchangeInfo 10-27, gst1030/shadow_events.txt. Ghi: sel.csv.gz, bigdown.csv, klines.csv.gz,
gate_ratio_live.bin, exinfo.json, shadow_events.txt, manifest.json.
"""
import csv
import glob
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime, timedelta, timezone

H = os.path.expanduser("~")
PULL = H + "/claude_master/pull242"
VIS = H + "/claude_master/parity_v11w/vision/klines_1m"
EXINFO = H + "/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz"
SHADOW_EV = H + "/claude_master/gst1030/shadow_events.txt"
START, END = 1793232000000, 1793491200000          # 2026-10-29 07:00 +07 .. 2026-11-01 07:00 +07
PDAYS = ["2026-10-28", "2026-10-29", "2026-10-30", "2026-10-31"]
VDAYS = ["2026-10-29", "2026-10-30", "2026-10-31"]
TZ7 = timezone(timedelta(hours=7))
RX = re.compile(r"\[SHADOW\] would-BUY BUY (\S+) entry: (\S+) quantity: (\S+) time:(\d{8} \d\d:\d\d) market level: (\S+)")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main(out):
    os.makedirs(out, exist_ok=True)
    man = {"START": START, "END": END, "inputs": {}}
    # 1. sel_dump: bo trung (ts,symbol) giu dong dau theo thu tu file (nhu R4h)
    files = sorted(set(sum([glob.glob(PULL + "/%s/dumps/sel_dump_*.csv.gz" % d) for d in PDAYS], [])),
                   key=lambda p: os.path.basename(p))
    seen, rows = set(), []
    for f in files:
        with gzip.open(f, "rt") as fh:
            r = csv.reader(fh)
            next(r, None)
            for a in r:
                if len(a) < 6:
                    continue
                ts = int(a[0])
                if ts < START or ts >= END:
                    continue
                k = (ts, a[1])
                if k in seen:
                    continue
                seen.add(k)
                rows.append([ts, a[1], a[2], int(a[3]), a[4], a[5]])
    rows.sort(key=lambda x: (x[0], x[3]))
    with gzip.open(out + "/sel.csv.gz", "wt") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ts", "symbol", "selectorScore", "rank", "gateValue", "p15"])
        w.writerows(rows)
    mins = sorted({r[0] for r in rows})
    man["sel"] = {"files": len(files), "rows": len(rows), "minutes": len(mins),
                  "first": mins[0] if mins else None, "last": mins[-1] if mins else None,
                  "missing_minutes": [t for t in range(START, END, 60000) if t not in set(mins)][:5000]}
    # 2. BIG_DOWN tu full.log (shadow v1.1 would-BUY); time = phut nen quyet dinh (+07)
    logs = sorted(set(sum([glob.glob(PULL + "/%s/logs/full.log@*.gz" % d) for d in PDAYS], [])))
    bd, seenb = [], set()
    lv = {}
    for f in logs:
        with gzip.open(f, "rt", errors="replace") as fh:
            for ln in fh:
                if "would-BUY" not in ln:
                    continue
                m = RX.search(ln)
                if not m:
                    continue
                lv[m.group(5)] = lv.get(m.group(5), 0) + 1
                ts = int(datetime.strptime(m.group(4), "%Y%m%d %H:%M").replace(tzinfo=TZ7).timestamp() * 1000)
                if m.group(5) != "BIG_DOWN" or ts < START or ts >= END:
                    continue
                k = (ts, m.group(1))
                if k in seenb:
                    continue
                seenb.add(k)
                bd.append([ts, m.group(1), m.group(2), m.group(3), m.group(5)])
    bd.sort()
    with open(out + "/bigdown.csv", "w") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ts", "symbol", "entry", "qty", "level"])
        w.writerows(bd)
    man["bigdown"] = {"logs": [os.path.basename(x) for x in logs], "rows": len(bd), "levels_all": lv}
    # 3. klines Vision
    syms = sorted({r[1] for r in rows} | {b[1] for b in bd} | {"BTCUSDT"})
    miss, nk = [], 0
    with gzip.open(out + "/klines.csv.gz", "wt") as fo:
        w = csv.writer(fo, lineterminator="\n")
        w.writerow(["symbol", "t", "o", "h", "l", "c"])
        for s in syms:
            for d in VDAYS:
                p = "%s/%s/%s.zip" % (VIS, d, s)
                if not os.path.exists(p):
                    miss.append(s + "@" + d)
                    continue
                with zipfile.ZipFile(p) as z:
                    with z.open(z.namelist()[0]) as fh:
                        for a in csv.reader(io.TextIOWrapper(fh)):
                            if not a or not a[0][:1].isdigit():
                                continue
                            w.writerow([s, int(a[0]), a[1], a[2], a[3], a[4]])
                            nk += 1
    man["klines"] = {"symbols": len(syms), "rows": nk, "missing": miss}
    # 4. buffer gate live (snapshot 11-01), exinfo, shadow events
    src = PULL + "/2026-10-31/run/gate_ratio_live.bin.gz"
    with gzip.open(src, "rb") as fi, open(out + "/gate_ratio_live.bin", "wb") as fo:
        shutil.copyfileobj(fi, fo)
    with gzip.open(EXINFO, "rb") as fi, open(out + "/exinfo.json", "wb") as fo:
        shutil.copyfileobj(fi, fo)
    shutil.copy(SHADOW_EV, out + "/shadow_events.txt")
    for k, p in (("buffer", src), ("exinfo", EXINFO), ("shadow_events", SHADOW_EV)):
        man["inputs"][k] = {"path": p, "sha256": sha(p)}
    for f in ("sel.csv.gz", "bigdown.csv", "klines.csv.gz", "gate_ratio_live.bin", "exinfo.json", "shadow_events.txt"):
        man.setdefault("outputs", {})[f] = sha(out + "/" + f)
    json.dump(man, open(out + "/manifest.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in man.items() if k not in ("inputs", "outputs")}, default=str)[:3000])


if __name__ == "__main__":
    main(sys.argv[1])
