#!/usr/bin/env python3
"""E2E_REPLAY_V12 - dung fixture tu du lieu CO SAN tren Oracle (khong mang). Tham so hoa cua so (prereg §2).

  Fixture dev 10-30 (da co, KHONG can chay lai): --start "2026-10-29 07:00" --end "2026-11-01 07:00" --buffer-day 2026-10-31
  Fixture CHINH THUC 11-05 (CHI chay sau khi A1 duyet harness + REF; xem tools/e2e/run_official_1105.sh):
      --start "2026-11-05 07:00" --end "2026-11-14 07:00" --buffer-day 2026-11-05 --dry-submits

Doc: pull242/<D>/dumps/sel_dump_*.csv.gz (D = ngay truoc START .. ngay END), pull242/<D>/logs/full.log@*.gz (BIG_DOWN would-BUY +
[C3-LIVE] SUBMIT cua dry that), pull242/<buffer-day>/run/gate_ratio_live.bin.gz, Vision klines_1m zip, exchangeInfo fixture gan nhat
<= START. Ghi: sel.csv.gz, bigdown.csv, klines.csv.gz, gate_ratio_live.bin, exinfo.json, [dry_submits.csv], manifest.json (sha256).
"""
import argparse
import csv
import glob
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import zipfile
from datetime import datetime, timedelta, timezone

H = os.path.expanduser("~")
PULL = H + "/claude_master/pull242"
VIS = H + "/claude_master/parity_v11w/vision/klines_1m"
FIXT = H + "/claude_master/v12/fixtures"
TZ7 = timezone(timedelta(hours=7))
RX = re.compile(r"\[SHADOW\] would-BUY BUY (\S+) entry: (\S+) quantity: (\S+) time:(\d{8} \d\d:\d\d) market level: (\S+)")
# dong dry that: "... [C3-LIVE] SUBMIT <SYM> <LEVEL> SUBMITTED cid=c3-<SYM>-<barMin>-<leg> qty=... budget=... legIdx=..."
RXS = re.compile(r"^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.\d+ .*\[C3-LIVE\] SUBMIT (\S+) (\S+) SUBMITTED cid=(\S+) qty=(\S+) budget=(\S+)")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ms7(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=TZ7).timestamp() * 1000)


def days(a, b):
    out, d = [], a
    while d <= b:
        out.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", required=True, help="+07, 'YYYY-MM-DD HH:MM'")
    ap.add_argument("--end", required=True)
    ap.add_argument("--buffer-day", required=True, help="pull242/<ngay>/run/gate_ratio_live.bin.gz (chi ban ghi < START duoc dung)")
    ap.add_argument("--exinfo", default="", help="mac dinh: fixture exchangeInfo moi nhat <= ngay START")
    ap.add_argument("--dry-submits", action="store_true", help="trich [C3-LIVE] SUBMIT dry that trong cua so -> dry_submits.csv (E2)")
    a = ap.parse_args()
    out = a.out
    if os.path.exists(out + "/manifest.json"):
        raise SystemExit("TU CHOI: %s da co fixture (khong ghi de)" % out)
    os.makedirs(out, exist_ok=True)
    START, END = ms7(a.start), ms7(a.end)
    d0 = datetime.fromtimestamp(START / 1000, TZ7).date()
    d1 = datetime.fromtimestamp((END - 1) / 1000, TZ7).date()
    PDAYS = days(d0 - timedelta(days=1), d1)
    u0 = datetime.fromtimestamp(START / 1000, timezone.utc).date()
    u1 = datetime.fromtimestamp((END - 1) / 1000, timezone.utc).date()
    VDAYS = days(u0, u1)
    exinfo = a.exinfo
    if not exinfo:
        cands = sorted(glob.glob(FIXT + "/exchangeInfo_*.json.gz"))
        cands = [c for c in cands if os.path.basename(c)[13:21] <= d0.strftime("%Y%m%d")]
        exinfo = cands[-1]
    man = {"START": START, "END": END, "args": vars(a), "pdays": PDAYS, "vdays": VDAYS, "inputs": {}}
    # 1. sel_dump: bo trung (ts,symbol) giu dong dau theo thu tu file
    files = sorted(set(sum([glob.glob(PULL + "/%s/dumps/sel_dump_*.csv.gz" % d) for d in PDAYS], [])), key=os.path.basename)
    seen, rows = set(), []
    for f in files:
        with gzip.open(f, "rt") as fh:
            r = csv.reader(fh)
            next(r, None)
            for x in r:
                if len(x) < 6:
                    continue
                ts = int(x[0])
                if ts < START or ts >= END or (ts, x[1]) in seen:
                    continue
                seen.add((ts, x[1]))
                rows.append([ts, x[1], x[2], int(x[3]), x[4], x[5]])
    rows.sort(key=lambda z: (z[0], z[3]))
    with gzip.open(out + "/sel.csv.gz", "wt") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ts", "symbol", "selectorScore", "rank", "gateValue", "p15"])
        w.writerows(rows)
    mins = sorted({z[0] for z in rows})
    sm = set(mins)
    man["sel"] = {"files": len(files), "rows": len(rows), "minutes": len(mins), "first": mins[0] if mins else None,
                  "last": mins[-1] if mins else None, "missing_minutes_n": sum(1 for t in range(START, END, 60000) if t not in sm)}
    # 2. log: BIG_DOWN (would-BUY) + SUBMIT dry that
    logs = sorted(set(sum([glob.glob(PULL + "/%s/logs/full.log@*.gz" % d) for d in PDAYS], [])))
    bd, seenb, lv, sub = [], set(), {}, []
    for f in logs:
        with gzip.open(f, "rt", errors="replace") as fh:
            for ln in fh:
                if "would-BUY" in ln:
                    m = RX.search(ln)
                    if not m:
                        continue
                    lv[m.group(5)] = lv.get(m.group(5), 0) + 1
                    ts = int(datetime.strptime(m.group(4), "%Y%m%d %H:%M").replace(tzinfo=TZ7).timestamp() * 1000)
                    if m.group(5) == "BIG_DOWN" and START <= ts < END and (ts, m.group(1)) not in seenb:
                        seenb.add((ts, m.group(1)))
                        bd.append([ts, m.group(1), m.group(2), m.group(3), m.group(5)])
                elif a.dry_submits and "[C3-LIVE] SUBMIT" in ln:
                    m = RXS.search(ln)
                    if not m:
                        continue
                    t = int(datetime.strptime(m.group(1), "%d/%m/%Y %H:%M:%S").replace(tzinfo=TZ7).timestamp() * 1000)
                    parts = m.group(4).split("-")
                    dec = int(parts[-2]) * 60000 if len(parts) >= 4 and parts[-2].isdigit() and int(parts[-2]) > 20_000_000 \
                        else (t // 60000 - 1) * 60000
                    if START <= t < END:
                        sub.append([m.group(2), dec, m.group(3), m.group(4), m.group(5), m.group(6), t])
    bd.sort()
    with open(out + "/bigdown.csv", "w") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ts", "symbol", "entry", "qty", "level"])
        w.writerows(bd)
    man["bigdown"] = {"logs": [os.path.basename(x) for x in logs], "rows": len(bd), "levels_all": lv}
    if a.dry_submits:
        with open(out + "/dry_submits.csv", "w") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["symbol", "decision_ts", "level", "cid", "qty", "budget", "log_ms"])
            w.writerows(sub)
        man["dry_submits"] = len(sub)
    # 3. Vision 1m
    syms = sorted({z[1] for z in rows} | {z[1] for z in bd} | {"BTCUSDT"})
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
                        for x in csv.reader(io.TextIOWrapper(fh)):
                            if not x or not x[0][:1].isdigit():
                                continue
                            w.writerow([s, int(x[0]), x[1], x[2], x[3], x[4]])
                            nk += 1
    man["klines"] = {"symbols": len(syms), "rows": nk, "missing": miss}
    # 4. buffer gate + exinfo
    src = PULL + "/%s/run/gate_ratio_live.bin.gz" % a.buffer_day
    with gzip.open(src, "rb") as fi, open(out + "/gate_ratio_live.bin", "wb") as fo:
        shutil.copyfileobj(fi, fo)
    with gzip.open(exinfo, "rb") as fi, open(out + "/exinfo.json", "wb") as fo:
        shutil.copyfileobj(fi, fo)
    for k, p in (("buffer", src), ("exinfo", exinfo)):
        man["inputs"][k] = {"path": p, "sha256": sha(p)}
    for f in sorted(os.listdir(out)):
        if f != "manifest.json":
            man.setdefault("outputs", {})[f] = sha(out + "/" + f)
    json.dump(man, open(out + "/manifest.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in man.items() if k not in ("inputs", "outputs")}, default=str)[:3000])


if __name__ == "__main__":
    main()
