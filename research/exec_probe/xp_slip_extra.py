#!/usr/bin/env python3
"""Mo ta BO SUNG cho EXEC-PROBE (ngoai xp_score.py, KHONG doi verdict/nguong):
p50/p90/p99 slip theo gio (+07), theo quintile thanh khoan L24, va doi chieu gia dinh sim.

L24 = quote volume cua NGAY UTC TRUOC ngay cua t_dec, lay tu Vision daily kline 1d (file tinh
data.binance.vision, khong API). Day la xap xi 24h gan nhat (lech 0-24h tuy gio vao lenh), ghi ro.

argv: --log <file>... [--kline-dir DIR] [--out-json F] [--out-md F]
Chi doc file; tai them 1d kline neu thieu vao --kline-dir (mac dinh /tmp/xp1030/k1d).
"""
import argparse
import datetime as dt
import glob
import io
import json
import os
import statistics
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

HEADER = ("v,ev,sym,side,lvl,leg,reason,qty,notional,sim_px,bar_open,bar_ret,bucket,t_bar_close,t_dec,t_snap,lat_dec_ms,"
          "lat_snap_ms,ex_lag_ms,bid,ask,mid,spread_bps,l1_bid_ntl,l1_ask_ntl,n_lvl,side_ntl,walk_vwap,fill_frac,walk_lvls,"
          "slip_bps,drift_bps,impact_bps,slip_x025,slip_x4,trig_px,status,src").split(",")
COLS = {"NC": 7.0, "C1": 18.0, "C2": 19.0, "C4": 32.0}
PAPER_EQUITY = 35000.0


def rows(paths):
    out = []
    for p in paths:
        for line in open(p, encoding="utf-8", errors="replace"):
            i = line.find("[EXEC-PROBE] ")
            s = line[i + 13:].rstrip("\n") if i >= 0 else line.rstrip("\n")
            if s.startswith("#hdr") or not s.startswith("1,"):
                continue
            v = s.split(",")
            if len(v) == len(HEADER):
                out.append(dict(zip(HEADER, v)))
    return out


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (k - lo), 3)


def desc(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "p50": pct(xs, .5), "p90": pct(xs, .9), "p99": pct(xs, .99),
            "mean": round(statistics.fmean(xs), 3), "max": round(max(xs), 3)}


def day_of(ms):
    return dt.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")


def prev_day(d):
    return (dt.date.fromisoformat(d) - dt.timedelta(days=1)).isoformat()


def fetch_1d(sym, day, kdir):
    os.makedirs(kdir, exist_ok=True)
    p = os.path.join(kdir, "%s-1d-%s.csv" % (sym, day))
    if os.path.exists(p):
        return p
    url = "https://data.binance.vision/data/futures/um/daily/klines/%s/1d/%s-1d-%s.zip" % (sym, sym, day)
    try:
        b = urllib.request.urlopen(url, timeout=30).read()
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            txt = z.read(z.namelist()[0]).decode()
        open(p, "w").write(txt)
        return p
    except Exception:
        open(p + ".404", "w").write("404")
        return None


def l24(m):
    """quote volume 1d cua ngay UTC truoc t_dec."""
    sym, day = m
    p = fetch_1d(sym, prev_day(day), KDIR)
    if not p:
        return None
    last = open(p).read().strip().splitlines()[-1].split(",")
    return float(last[7])


def quintiles(vals, k=5):
    s = sorted(vals)
    cuts = [pct(s, i / k) for i in range(1, k)]
    def q(v):
        for i, c in enumerate(cuts):
            if v <= c:
                return i + 1
        return k
    return q, cuts


ap = argparse.ArgumentParser()
ap.add_argument("--log", action="append", required=True)
ap.add_argument("--kline-dir", default="/tmp/xp1030/k1d")
ap.add_argument("--out-json", default="/tmp/xp1030/xp_extra.json")
ap.add_argument("--out-md", default="/tmp/xp1030/xp_extra.md")
a = ap.parse_args()
KDIR = a.kline_dir
R = rows(a.log)
col = "slip_x025" if PAPER_EQUITY >= 20000 else "slip_bps"
E = [r for r in R if r["ev"] in ("ENTRY", "DCA") and r["status"] in ("ok", "short") and f(r[col]) is not None]
X = [r for r in R if r["ev"] == "EXIT" and r["status"] in ("ok", "short") and f(r["slip_bps"]) is not None]

pairs = sorted({(r["sym"], day_of(int(r["t_dec"]))) for r in E})
with ThreadPoolExecutor(max_workers=12) as ex:
    lmap = dict(zip(pairs, ex.map(l24, pairs)))
for r in E:
    r["l24"] = lmap.get((r["sym"], day_of(int(r["t_dec"]))))

known = [r for r in E if r["l24"]]
qfn, cuts = quintiles([r["l24"] for r in known]) if known else (None, [])
for r in E:
    r["l24_q"] = qfn(r["l24"]) if r["l24"] else None

by_hour = {}
for r in E:
    h = dt.datetime.fromtimestamp(int(r["t_dec"]) / 1000, dt.timezone(dt.timedelta(hours=7))).hour
    by_hour.setdefault(h, []).append(f(r[col]))
by_q = {}
for r in known:
    by_q.setdefault("Q%d" % r["l24_q"], []).append(f(r[col]))
by_bucket = {}
for r in E:
    by_bucket.setdefault(r["bucket"], []).append(f(r[col]))
by_bucket_x = {}
for r in X:
    by_bucket_x.setdefault(r["bucket"], []).append(f(r["slip_bps"]))

excess = [f(r[col]) - COLS.get(r["bucket"], COLS["NC"]) for r in E]
out = {
    "n_E": len(E), "n_X": len(X), "col": col,
    "e_by_reason": {k: sum(1 for r in E if r["reason"] == k) for k in sorted({r["reason"] for r in E})},
    "x_by_reason": {k: sum(1 for r in X if r["reason"] == k) for k in sorted({r["reason"] for r in X})},
    "entry_all": desc([f(r[col]) for r in E]),
    "entry_excess_vs_ecmeas": desc(excess),
    "exit_all": desc([f(r["slip_bps"]) for r in X]),
    "exit_assume_sim_bps": 0.67,
    "by_hour_local": {str(h): desc(v) for h, v in sorted(by_hour.items())},
    "by_l24_quintile": {q: desc(v) for q, v in sorted(by_q.items())},
    "l24_cuts_usd": [round(c) for c in cuts],
    "l24_events_known": len(known), "l24_pairs": len(pairs), "l24_missing_pairs": sum(1 for v in lmap.values() if not v),
    "by_bucket_entry": {q: desc(v) for q, v in sorted(by_bucket.items())},
    "by_bucket_exit": {q: desc(v) for q, v in sorted(by_bucket_x.items())},
    "n_symbols": len({r["sym"] for r in E}),
}
json.dump(out, open(a.out_json, "w"), indent=1)

L = ["# EXEC-PROBE slip — mo ta bo sung", "",
     "n_E=%d n_X=%d cot=%s; L24 = quote volume ngay UTC truoc (Vision 1d), %d/%d event co L24" %
     (len(E), len(X), col, len(known), len(E)), "",
     "| nhom | n | p50 | p90 | p99 | mean | max |", "|---|---|---|---|---|---|---|"]
L.append("| vao tat ca | %d | %s | %s | %s | %s | %s |" % (out["entry_all"]["n"], out["entry_all"]["p50"], out["entry_all"]["p90"], out["entry_all"]["p99"], out["entry_all"]["mean"], out["entry_all"]["max"]))
for q, d in out["by_l24_quintile"].items():
    L.append("| L24 %s | %d | %s | %s | %s | %s | %s |" % (q, d["n"], d["p50"], d["p90"], d["p99"], d["mean"], d["max"]))
for q, d in out["by_bucket_entry"].items():
    L.append("| bucket %s | %d | %s | %s | %s | %s | %s |" % (q, d["n"], d["p50"], d["p90"], d["p99"], d["mean"], d["max"]))
L.append("| ra (EXIT) | %d | %s | %s | %s | %s | %s |" % (out["exit_all"]["n"], out["exit_all"]["p50"], out["exit_all"]["p90"], out["exit_all"]["p99"], out["exit_all"]["mean"], out["exit_all"]["max"]))
L += ["", "Theo gio (+07): " + ", ".join("%sh n=%d p50=%s p90=%s" % (h, d["n"], d["p50"], d["p90"]) for h, d in out["by_hour_local"].items())]
open(a.out_md, "w").write("\n".join(L) + "\n")
print(json.dumps(out, indent=1)[:4000])
