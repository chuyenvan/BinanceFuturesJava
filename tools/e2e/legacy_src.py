#!/usr/bin/env python3
"""E2E_REPLAY_V12 ERRATA3 E9 - danh sach LEGACY cua NGAY fixture cho luot R-OLD (CHI R-OLD; cac luot khac
C3_EXCLUDE_LEGACY_HELD=false nhu prereg muc 1).

Nguon (thu tu uu tien), D = ngay (+07) cua START fixture (11-05 -> pull242/2026-11-05; dev 10-30 START 10-29 07:00 ->
pull242/2026-10-29), co the ep bang --day:
  1. pull242/<D>/run/legacy_symbols.csv (file LegacySymbols.save cua 242) neu co;
  2. dong log "[LEGACY] managed N: A,B,..." trong pull242/<D>/logs/full.log@*.gz (gio log = +07, dd/mm/yyyy HH:MM:SS.mmm).
Danh sach dung = dong log CUOI CUNG co thoi diem <= START (= trang thai LegacySymbols luc mo cua so). Moi lan danh sach
DOI trong [START, END) duoc ghi vao json (doi_trong_cua_so: ms, file, so dong, them/bot) - de nhan LEGACY-11-05 (ERRATA3
E9) tro duoc toi dong log; KHONG tu dong ap vao replay (jar nap 1 lan tu file nhu production khi khong co vi the that).
Ra: --out-csv (dinh dang LegacySymbols.save: comment + 1 symbol/dong; jar doc qua run/legacy_symbols.csv cua cwd) va
--out-json (nguon, md5 nguon, dong, danh sach, md5 csv). Khong co nguon / khong co dong truoc START => exit 2 (TU CHOI).
Chi doc pull242 (du lieu da keo ve, khong bi mat); khong Java.
"""
import argparse
import datetime
import glob
import gzip
import hashlib
import json
import os
import re
import sys

TZ7 = datetime.timezone(datetime.timedelta(hours=7))
PAT = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d{3}) .*\[LEGACY\] managed (\d+): ?(.*)$")


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_line(ln):
    m = PAT.match(ln.rstrip("\n"))
    if not m:
        return None
    dd, mm, yy, hh, mi, ss, ms, n, lst = m.groups()
    t = datetime.datetime(int(yy), int(mm), int(dd), int(hh), int(mi), int(ss), int(ms) * 1000, TZ7)
    syms = tuple(sorted(x.strip() for x in lst.split(",") if x.strip()))
    return int(t.timestamp() * 1000), int(n), syms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--pull", default=os.path.expanduser("~/claude_master/pull242"))
    ap.add_argument("--day", default="")
    ap.add_argument("--out-csv", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args()
    day = a.day or datetime.datetime.fromtimestamp(a.start / 1000, TZ7).strftime("%Y-%m-%d")
    d = os.path.join(a.pull, day)
    info = {"errata": "ERRATA3 E9 (409e1144)", "day": day, "pull_dir": d, "START": a.start, "END": a.end}
    runf = os.path.join(d, "run", "legacy_symbols.csv")
    changes = []
    if os.path.isfile(runf):
        syms = tuple(sorted({ln.strip() for ln in open(runf) if ln.strip() and not ln.lstrip().startswith("#")}))
        info.update(nguon="run/legacy_symbols.csv", source=runf, source_md5=md5(runf), line=None, line_ms=None)
    else:
        logs = sorted(glob.glob(os.path.join(d, "logs", "full.log@*.gz")))
        if not logs:
            print("TU CHOI: khong co nguon LEGACY trong %s (run/legacy_symbols.csv | logs/full.log@*.gz)" % d)
            sys.exit(2)
        best, prev, bad, last = None, None, [], None
        for lg in logs:
            with gzip.open(lg, "rt", errors="replace") as fh:
                for i, ln in enumerate(fh, 1):
                    if "[LEGACY] managed" not in ln:
                        continue
                    p = parse_line(ln)
                    if p is None:
                        continue
                    t, n, cur = p
                    last = t
                    if n != len(cur):
                        bad.append((os.path.basename(lg), i, n, len(cur)))
                    if t <= a.start:
                        best = (lg, i, t, cur)
                        prev = cur
                    elif t < a.end:
                        if prev is not None and cur != prev:
                            changes.append({"ms": t, "file": os.path.basename(lg), "dong": i, "n": len(cur),
                                            "them": sorted(set(cur) - set(prev)), "bot": sorted(set(prev) - set(cur))})
                        prev = cur
        if best is None:
            print("TU CHOI: khong co dong [LEGACY] managed truoc START=%d trong %s" % (a.start, logs))
            sys.exit(2)
        lg, i, t, syms = best
        info.update(nguon="log [LEGACY] managed", source=lg, source_md5=md5(lg), line=i, line_ms=t,
                    sources_all=[{"file": x, "md5": md5(x)} for x in logs], dong_n_lech=bad[:10],
                    log_dong_cuoi_ms=last, log_phu_het_cua_so=(last is not None and last >= a.end - 60000))
    os.makedirs(os.path.dirname(os.path.abspath(a.out_csv)), exist_ok=True)
    with open(a.out_csv, "w") as w:
        w.write("# LEGACY symbols: vi the THAT cu, dong theo duong HEAD, so giay C3 KHONG cham.\n")
        w.write("# [E2E_V12 ERRATA3 E9] sinh boi tools/e2e/legacy_src.py tu %s dong %s (md5 %s)\n"
                % (info["source"], info["line"], info["source_md5"]))
        for s in syms:
            w.write(s + "\n")
    info.update(n=len(syms), symbols=list(syms), out_csv=os.path.abspath(a.out_csv), out_csv_md5=md5(a.out_csv),
                doi_trong_cua_so=changes, n_doi_trong_cua_so=len(changes))
    json.dump(info, open(a.out_json, "w"), indent=1)
    print("LEGACY day=%s n=%d nguon=%s dong=%s doi_trong_cua_so=%d" % (day, len(syms), info["source"], info["line"], len(changes)))


if __name__ == "__main__":
    main()
