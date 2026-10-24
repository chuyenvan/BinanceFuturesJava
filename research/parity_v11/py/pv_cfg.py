#!/usr/bin/env python3
"""PARITY_V11_WINDOW — cau hinh theo NGAY UTC D cho code cham (thay hard-code T0/T1, glob, DAY_D, danh sach log cua D1).

Chon ngay: bien moi truong PV_DAY=YYYY-MM-DD (bat buoc). PV_WORK (tuy chon) = thu muc ghi ket qua trung gian.
- D = 2026-10-21 (luot D1) dung bo cuc du lieu CU (~/claude_master/parity_v11w/{live,runs/d21}) de chay lai bit-identical
  (regression test). PV_D1_LAYOUT=pull242 => dung bo cuc moi nhu moi ngay khac.
- Ngay khac: du lieu live tu ~/claude_master/pull242/<D>/ (keo 242 chi doc, COMPLETE), da chuan hoa boi py/day_prep.py vao
  ~/claude_master/parity_v11w/d/<D>/live (log gop + loc cua so, buffer giai nen, psym giai ma).
Khong doc/ghi 242. Timestamp int64 ms.
"""
import datetime as dt
import glob
import os

ROOT = os.path.expanduser("~/claude_master/parity_v11w")
PULL = os.path.expanduser("~/claude_master/pull242")
MOD = os.path.expanduser("~/claude_master/parity_1020/raw242/models")
VIS = ROOT + "/vision/klines_1m"
WINDOW_START = 1792543980000          # nen quyet dinh dau tien cua cua so promotion (prereg)
MIN, H, DAYMS = 60000, 3600000, 86400000


def day_ms(day):
    return int(dt.datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def ms_day(t):
    return dt.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d")


def shift(day, k):
    return ms_day(day_ms(day) + k * DAYMS)


def cfg(day=None):
    day = day or os.environ["PV_DAY"]
    d0 = day_ms(day)
    c = {"day": day, "day_prev": shift(day, -1), "day_next": shift(day, 1),
         "T0": max(WINDOW_START, d0), "T1": d0 + DAYMS - MIN, "VIS": VIS, "MOD": MOD, "ROOT": ROOT,
         "s1v_days": [shift(day, k) for k in range(-15, 1)]}
    legacy = day == "2026-10-21" and os.environ.get("PV_D1_LAYOUT", "legacy") == "legacy"
    if legacy:
        live = ROOT + "/live"
        c.update(layout="legacy-d1", LIVE=live, RUN=ROOT + "/runs/d21", WORK=os.environ.get("PV_WORK", ROOT + "/work"),
                 # gia tri D1 (ADDENDUM1, 5f8e7291) giu nguyen de regression bit-identical
                 T0=1792543980000, T1=1792627140000,
                 feat_globs=[live + "/dumps/feat_dump_*.csv.gz"],
                 sel_globs=[live + "/dumps/sel_dump_2026102[12]_*.csv.gz"],
                 s1_globs=[live + "/s1/s1_dump_2026102[12]_*.csv.gz"],
                 feat45=[live + "/feat45_live.csv.gz", live + "/feat45_live_b.csv.gz", live + "/feat45_live_c.csv.gz"],
                 logs=[live + "/raw/loglines_1021.gz", live + "/full_1022_0000_0705.log.gz"],
                 buffer=live + "/raw/gate_ratio_live.bin",
                 # D1: file nay thuc chat la ts_ext_daily.csv (moi dong co dau phay) => tap LEGACY RONG. Giu nguyen de
                 # bit-identical; ngay khac doc '[LEGACY] managed' tu log (xem PARITY_V11_WINDOW_D2.md).
                 legacy=("file", live + "/raw/ts_ext_legacy.txt"),
                 U=ROOT + "/univ/u_d21.txt", tsx_univ=[ROOT + "/univ/u_d21.txt"], tag="d1")
    else:
        base = ROOT + "/d/" + day
        live = base + "/live"
        pd_ = PULL + "/" + day
        c.update(layout="pull242", LIVE=live, RUN=base + "/runs", WORK=os.environ.get("PV_WORK", base + "/work"),
                 PULLD=pd_, PULLN=PULL + "/" + shift(day, 1),
                 feat_globs=[pd_ + "/dumps/feat_dump_*.csv.gz"],
                 sel_globs=[pd_ + "/dumps/sel_dump_*.csv.gz"],
                 s1_globs=[pd_ + "/s1/s1_dump_*.csv.gz"],
                 feat45=[live + "/feat45_live.csv.gz"],
                 logs=[live + "/log_window.gz"],
                 buffer=live + "/gate_ratio_live.bin",
                 legacy=("log", None),
                 U=ROOT + "/univ/u_" + day.replace("-", "") + ".txt",
                 tsx_univ=sorted(set(glob.glob(ROOT + "/univ/u_2026*.txt") + [ROOT + "/univ/u_d21.txt"])),
                 tag=day.replace("-", ""),
                 log_from=d0 - H,                   # D 06:00 (+07)
                 log_to=d0 + DAYMS + 10 * MIN)      # D+1 07:10 (+07)
    return c


def globs(pats):
    out = []
    for p in pats:
        out += glob.glob(p)
    return sorted(set(out))


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(cfg(sys.argv[1] if len(sys.argv) > 1 else None), indent=1))
