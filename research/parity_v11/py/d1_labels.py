#!/usr/bin/env python3
"""Nhan K1-K5 cho cac phut lech (PREREG_PARITY_V11_WINDOW §5) + bang tong hop.
ADDENDUM1 (audit OC1023 CRIT-2): K3 = |U_D| != nsym live gan nhat, HOAC U thay doi trong [M-1440', M]
(moc doi o TRUOC hoac bang M), moc doi = nen Vision dau tien cua symbol moi (ab5bbe44 gan K3 cho phut TRUOC
moc doi: t < first741 <= t+1440). Them: log 10-22 00:00-07:05 (+07); nguon phut lech du theo §5
(P1-F, P1, MD, FUND, NET, GV-O, S1-V); K2a (lo Vision), K2b ([TS-EXT] day n_min<1440), K2c ([FEAT-PIPE]).
argv: none. Doc work/*.json + join_gate + s1v_rows + log + cache Vision.
"""
import glob
import gzip
import io
import json
import os
import re
import zipfile
import datetime as dt

import numpy as np
import pandas as pd

W = os.path.expanduser("~/claude_master/parity_v11w")
VIS = W + "/vision/klines_1m"
MIN = 60000
T0, T1 = 1792543980000, 1792627140000
DAY_D, DAY_PREV = "2026-10-21", "2026-10-20"
LOGS = [W + "/live/raw/loglines_1021.gz", W + "/live/full_1022_0000_0705.log.gz"]


def f7(t):
    return dt.datetime.utcfromtimestamp(t / 1000 + 7 * 3600).strftime("%m-%d %H:%M")


def ms(s):
    """'10-21 11:59' +07 -> ms"""
    return int(dt.datetime.strptime("2026-" + s + " +0700", "%Y-%m-%d %H:%M %z").timestamp() * 1000)


def eq(a, b, tol=1e-6):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    return (np.abs(a - b) <= tol * (1 + np.abs(b))) | (np.isnan(a) & np.isnan(b))


lines = []
for p in LOGS:
    lines += gzip.open(p, "rt", errors="ignore").read().splitlines()
PAT = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d+)")


def lt(s):
    m = PAT.match(s)
    if not m:
        return None
    d, mo, y, hh, mi, ss, mss = m.groups()
    return int(dt.datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss),
                           tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp() * 1000)


# ---------------- phut lech theo tung chi so (§5)
feat = json.load(open(W + "/work/gate_d1.json"))
fund = json.load(open(W + "/work/fund_d1.json"))
net = json.load(open(W + "/work/net_d1.json"))
gv = json.load(open(W + "/work/gv_p2_d1.json"))
src = {"P1F": set(feat["P1F"]["bad_minutes"]), "FUND": set(fund["bad_minutes"]), "NET": set(net["bad_minutes"]),
       "GV_O": set(gv["GV_O"]["bad_minutes"])}
JG = pd.read_csv(W + "/work/join_gate.csv.gz")
rel = np.abs(JG.p15_out.values - JG.p15_off.values) / np.abs(JG.p15_off.values)
src["P1"] = set(JG["min"][rel > 1e-3].map(f7))
md_ok = np.ones(len(JG), bool)
for lc, bc in (("rateDownAvg", "r_down"), ("rateUpAvg", "r_up"), ("rateDown15MAvg", "r_down15")):
    md_ok &= eq(JG[lc], JG[bc])
src["MD"] = set(JG["min"][~md_ok].map(f7))
SV = pd.read_csv(W + "/work/s1v_rows.csv.gz", usecols=["ts"] + ["c%d" % i for i in range(7)] +
                 ["l%d" % i for i in range(7)] + ["score_live", "score_calc"])
sv_ok = eq(SV.score_calc, SV.score_live)
for i in range(7):
    sv_ok &= eq(SV["c%d" % i], SV["l%d" % i])
sv_bad = SV.ts[~sv_ok]
src["S1V"] = set(pd.Series(sv_bad.unique()).map(f7))
s1v_rows_bad_by_min = sv_bad.value_counts()
del SV
mins = sorted(set().union(*src.values()))

# ---------------- K1: [LIVE-KLINE] cua so 10' co ghi de
k1 = []   # (window_end, reread_overwritten, decided_on_unsettled, s1_close_rewritten)
for s in lines:
    if "[LIVE-KLINE] reread" not in s:
        continue
    t = lt(s)
    m = re.search(r"reread_overwritten=(\d+)", s)
    d = re.search(r"decided_on_unsettled=(\d+)/\d+", s)
    c = re.search(r"s1_close_rewritten=(\d+)", s)
    if t:
        k1.append((t, int(m.group(1)) if m else 0, int(d.group(1)) if d else 0, int(c.group(1)) if c else 0))

# ---------------- K2b: [TS-EXT] day D n_min (ngay UTC cua M)
k2b = {}
for s in lines:
    m = re.search(r"\[TS-EXT\] day (\d{4}-\d\d-\d\d) sum_ew=\S+ n_min=(\d+)", s)
    if m:
        k2b.setdefault(m.group(1), []).append(int(m.group(2)))

# ---------------- K2c: [FEAT-PIPE] partial/gap_minutes/no_snap tang trong khoi 60 tick
fp = []
for s in lines:
    if "[FEAT-PIPE] ticks=" in s:
        t = lt(s)
        g = {k: int(v) for k, v in re.findall(r"(ticks|partial|gap_minutes|no_snap|nsym)=(\d+)", s)}
        fp.append((t, g))
k2c_blocks = []
prev = None
for t, g in fp:
    base = prev if (prev is not None and g["ticks"] > prev["ticks"]) else {"partial": 0, "gap_minutes": 0, "no_snap": 0}
    if any(g[k] > base[k] for k in ("partial", "gap_minutes", "no_snap")):
        k2c_blocks.append((t - 60 * MIN, t))
    prev = g

# ---------------- Vision: moc doi U (nen dau tien cua symbol moi) + lo Vision (K2a)
def vis_times(day, sym):
    p = "%s/%s/%s.zip" % (VIS, day, sym)
    if not os.path.exists(p):
        return None
    with zipfile.ZipFile(p) as z:
        raw = z.read(z.namelist()[0]).decode()
    first = raw.split("\n", 1)[0]
    d = pd.read_csv(io.StringIO(raw), header=0 if first.startswith("open_time") else None, usecols=[0])
    return np.asarray(d.iloc[:, 0].values, np.int64)


days = sorted(os.listdir(VIS))
syms = {d: set(f[:-4] for f in os.listdir(VIS + "/" + d) if f.endswith(".zip")) for d in days}
U_D = syms[DAY_D]
marks = []
for d in (DAY_PREV, DAY_D):
    dprev = days[days.index(d) - 1]
    for s in sorted(syms[d] - syms[dprev]):
        tt = vis_times(d, s)
        marks.append({"symbol": s, "day": d, "first_candle": int(tt.min()), "first_candle_p07": f7(int(tt.min()))})
holes = []
for s in sorted(U_D):
    parts = [x for x in (vis_times(DAY_PREV, s), vis_times(DAY_D, s)) if x is not None]
    tt = np.unique(np.concatenate(parts))
    exp = np.arange(tt.min(), tt.max() + MIN, MIN, dtype=np.int64)
    miss = np.setdiff1d(exp, tt)
    for h in miss:
        holes.append((s, int(h)))
nsym_marks = sorted((t, g["nsym"]) for t, g in fp if t and "nsym" in g)


def nsym_at(t):
    v = None
    for tt, n in nsym_marks:
        if tt <= t:
            v = n
    return v


rows = []
for s in mins:
    t = ms(s)
    k = []
    in_s1v = s in src["S1V"]
    for te, ro, du, cr in k1:
        if t - 20 * MIN <= te <= t + 10 * MIN and (ro > 0 or du > 0 or (in_s1v and cr > 0)):
            k.append("K1")
            break
    if any(sym for sym, h in holes if t - 20 * MIN <= h <= t):
        k.append("K2a")
    dM = dt.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d")
    if any(n < 1440 for n in k2b.get(dM, [])):
        k.append("K2b")
    if any(a < t <= b for a, b in k2c_blocks):
        k.append("K2c")
    ns = nsym_at(t)
    if ns is not None and ns != len(U_D):
        k.append("K3")
    if any(t - 1440 * MIN <= mk["first_candle"] <= t for mk in marks):
        k.append("K3")
    rows.append({"min": s, "labels": sorted(set(k)) or ["K5"], "nsym_log": ns,
                 "sources": sorted(n for n, v in src.items() if s in v),
                 "s1v_rows_bad": int(s1v_rows_bad_by_min.get(t, 0))})

# phu cua K3 tren TOAN cua so (mo ta: nhan K3 co con phan biet duoc khong)
allm = range(T0, T1 + MIN, MIN)
k3_all = sum(1 for t in allm if (nsym_at(t) is not None and nsym_at(t) != len(U_D))
             or any(t - 1440 * MIN <= mk["first_candle"] <= t for mk in marks))
out = {"n_bad_minutes": len(rows), "bad_minutes": rows,
       "K5": [r["min"] for r in rows if r["labels"] == ["K5"]],
       "counts": {x: sum(1 for r in rows if x in r["labels"]) for x in ("K1", "K2a", "K2b", "K2c", "K3", "K5")},
       "bad_by_source": {k: len(v) for k, v in src.items()},
       "U_D": len(U_D), "universe_change_marks": marks,
       "vision_holes_U_D_prev_and_D": {"n": len(holes), "first": [(a, f7(b)) for a, b in holes[:10]]},
       "ts_ext_day_n_min": k2b, "feat_pipe_blocks_flagged": [(f7(a), f7(b)) for a, b in k2c_blocks],
       "nsym_marks": [(f7(t), n) for t, n in nsym_marks],
       "K3_cover_window": {"minutes": len(allm), "K3": k3_all},
       "live_kline_windows_with_issues": [{"end": f7(t), "reread_overwritten": a, "decided_on_unsettled": b,
                                           "s1_close_rewritten": c} for t, a, b, c in k1 if a or b or c][:60]}
json.dump(out, open(W + "/work/labels_d1.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k != "bad_minutes"}, indent=1, default=str)[:5000])
for r in rows:
    print(r)
