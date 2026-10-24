#!/usr/bin/env python3
"""ADDENDUM2 muc 4: kiem lai S1-I cua D1 (10-21 07:53 -> 10-22 06:59 +07) voi tap LEGACY DUNG doc tu log
('[LEGACY] managed N: ...', full.log pull242/2026-10-21, dong gan nhat co thoi diem <= ts+2'). D1 goc dung tap rong
(file ts_ext_legacy.txt thuc chat la ts_ext_daily.csv). Ghi json ra argv[1]."""
import datetime as dt
import glob
import gzip
import json
import re
import sys

import numpy as np
import pandas as pd

T0, T1 = 1792543980000, 1792627140000
LIVE = "/home/ubuntu/claude_master/parity_v11w/live"
LOG = sorted(glob.glob("/home/ubuntu/claude_master/pull242/2026-10-22/logs/full.log@*"))[-1]
pat = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)")
leg = []
for s in gzip.open(LOG, "rt", errors="ignore"):
    if "[LEGACY] managed" in s:
        m = pat.match(s)
        d, mo, y, hh, mi, ss = map(int, m.groups())
        t = int(dt.datetime(y, mo, d, hh, mi, ss, tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp() * 1000)
        mm = re.search(r"managed (\d+): (\S*)", s)
        S = set(x for x in mm.group(2).split(",") if x)
        if len(S) == int(mm.group(1)):
            leg.append((t, S))
leg.sort(key=lambda x: x[0])
lt = np.array([a for a, _ in leg], np.int64)


def legacy_at(ts):
    i = int(np.searchsorted(lt, ts + 120000, "right")) - 1
    return leg[i][1] if i >= 0 else None


def rd(ps):
    out = []
    for p in sorted(glob.glob(ps)):
        try:
            out.append(pd.read_csv(p))
        except Exception:  # noqa: BLE001
            pass
    return pd.concat(out, ignore_index=True)


S = rd(LIVE + "/s1/s1_dump_2026102[12]_*.csv.gz")
S = S[(S.ts >= T0) & (S.ts <= T1)].drop_duplicates(["ts", "symbol"], keep="last")
sel = rd(LIVE + "/dumps/sel_dump_2026102[12]_*.csv.gz")
sel = sel[(sel.ts >= T0) & (sel.ts <= T1)].drop_duplicates(["ts", "symbol"], keep="last")
ok = tot = nolog = 0
bad = []
for ts, g in sel.groupby("ts"):
    sg = S[S.ts == ts]
    if len(sg) == 0:
        continue
    L = legacy_at(int(ts))
    if L is None:
        nolog += 1
        L = set()
    top = list(sg[~sg.symbol.isin(L)].sort_values(["score", "symbol"]).symbol.head(24))
    want = list(g.sort_values("rank").symbol)
    tot += 1
    if top == want:
        ok += 1
    else:
        bad.append(dt.datetime.utcfromtimestamp(ts / 1000 + 7 * 3600).strftime("%m-%d %H:%M"))
raw_leg_top = 0
for ts, sg in S.groupby("ts"):
    L = legacy_at(int(ts)) or set()
    raw_leg_top += int(sg.sort_values(["score", "symbol"]).symbol.head(24).isin(L).any())
res = {"log": LOG, "legacy_lines": len(leg), "legacy_n": len(leg[0][1]) if leg else 0, "minutes": tot, "exact_order": ok,
       "frac": ok / max(1, tot), "minutes_without_legacy_line": nolog, "bad": bad[:20],
       "minutes_legacy_in_raw_top24": raw_leg_top}
json.dump(res, open(sys.argv[1], "w"), indent=1)
print(json.dumps(res, indent=1))
