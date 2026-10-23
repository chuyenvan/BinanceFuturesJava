#!/usr/bin/env python3
"""Nhan K1-K5 cho cac phut lech (PREREG_PARITY_V11_WINDOW §5) + bang tong hop.
argv: none. Doc work/*.json + loglines.
"""
import gzip
import json
import os
import re
import datetime as dt

W = os.path.expanduser("~/claude_master/parity_v11w")
MIN = 60000


def f7(t):
    return dt.datetime.utcfromtimestamp(t / 1000 + 7 * 3600).strftime("%m-%d %H:%M")


def ms(s):
    """'10-21 11:59' +07 -> ms"""
    return int(dt.datetime.strptime("2026-" + s + " +0700", "%Y-%m-%d %H:%M %z").timestamp() * 1000)


lines = gzip.open(W + "/live/raw/loglines_1021.gz", "rt", errors="ignore").read().splitlines()
PAT = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d+)")


def lt(s):
    m = PAT.match(s)
    if not m:
        return None
    d, mo, y, hh, mi, ss, mss = m.groups()
    return int(dt.datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss),
                           tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp() * 1000)


k1 = []   # (window_end, reread_overwritten, decided_on_unsettled)
for s in lines:
    if "[LIVE-KLINE] reread" not in s:
        continue
    t = lt(s)
    m = re.search(r"reread_overwritten=(\d+)", s)
    d = re.search(r"decided_on_unsettled=(\d+)/\d+", s)
    if t:
        k1.append((t, int(m.group(1)) if m else 0, int(d.group(1)) if d else 0))
feat = json.load(open(W + "/work/gate_d1.json"))
fund = json.load(open(W + "/work/fund_d1.json"))
net = json.load(open(W + "/work/net_d1.json"))
gv = json.load(open(W + "/work/gv_p2_d1.json"))
mins = sorted(set(feat["P1F"]["bad_minutes"]) | set(fund["bad_minutes"]) | set(net["bad_minutes"]))

# nsym theo phut: tu log [FEAT-PIPE] (nsym) gan cho cac phut sau moc do; va moc niem yet
nsym_marks = []
for s in lines:
    if "[FEAT-PIPE]" in s and "nsym=" in s:
        t = lt(s)
        m = re.search(r"nsym=(\d+)", s)
        if t and m:
            nsym_marks.append((t, int(m.group(1))))
nsym_marks.sort()
first741 = next((t for t, n in nsym_marks if n == 741), None)


def nsym_at(t):
    v = 738
    for tt, n in nsym_marks:
        if tt <= t:
            v = n
    return v


rows = []
for s in mins:
    t = ms(s)
    k = []
    for te, ro, du in k1:
        if t - 20 * MIN <= te <= t + 10 * MIN and (ro > 0 or du > 0):
            k.append("K1")
            break
    if first741 is not None and nsym_at(t) != 741:
        k.append("K3")
    if t < first741 <= t + 1440 * MIN:
        k.append("K3")
    rows.append({"min": s, "labels": sorted(set(k)) or ["K5"], "nsym_log": nsym_at(t)})
out = {"bad_minutes": rows,
       "K5": [r["min"] for r in rows if r["labels"] == ["K5"]],
       "counts": {x: sum(1 for r in rows if x in r["labels"]) for x in ("K1", "K3", "K5")},
       "first_nsym741": f7(first741) if first741 else None,
       "live_kline_windows_with_issues": [{"end": f7(t), "reread_overwritten": a, "decided_on_unsettled": b}
                                          for t, a, b in k1 if a or b][:40]}
json.dump(out, open(W + "/work/labels_d1.json", "w"), indent=1)
print(json.dumps(out, indent=1)[:4000])
