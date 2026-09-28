#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VISION_MICRO — spread TRICH DAN (bookTicker) + impact (aggTrades) tu Binance Vision MIEN PHI.

Pre-reg: docs/prereg/PREREG_BOOK_COST2.md (commit b8bcca9) — chot TRUOC khi do.

Nguyen tac:
  * MIEN PHI, khong API key: https://data.binance.vision/data/futures/um/daily/<ds>/<SYM>/<SYM>-<ds>-<d>.zip
  * TAI BOUNDED: HTTP Range (<= RANGE_MB nén/file) + raw-inflate streaming (zlib wbits=-15);
    DUNG doc ngay khi transaction_time vuot cua so  => khong ghi zip/csv ra dia.
  * Cua so [00:00:00, 00:30:00) UTC (moc rebalance 00:00 UTC).
  * Chi phi CO HUONG: e = sign*(p_trade - mid)/mid*100 ; h_g(S) = quantile_k(e | notional ~ S).
    C_g(S) = 2*fee + 2*h_g(S).  fee = 0,0491 %/chan (DO duoc).
Thuan Python, 0 train / 0 sim, khong cham 2026, DEV<=2025-12-31. Output: docs/result/book_cost2.json
"""
import json
import os
import struct
import sys
import time
import urllib.request
import zlib

import numpy as np

BASE = "https://data.binance.vision/data/futures/um/daily"
RANGE_MB = 8
WMIN = 30                                     # cua so do: 30 phut dau ngay
FEE_LEG = 0.04910                             # %/chan (991 chan that, RESULT_LIVE_FILLS_AUDIT)
SIZES = (700.0, 2000.0, 5000.0)
KQ = (0.5, 0.9)
# LUU Y (phat hien TRUOC khi do): bookTicker daily CHI duoc publish trong cua so ~2023-05-16..2024-03-30
# (moi ngay 2025 => 404). Theo luat prereg "404 => bo ngay do + ghi lai", chon lai 4 ngay CUNG VI TRI
# trong cua so co du lieu: 2023-06-14, 2023-09-13, 2023-12-13, 2024-03-13.
DAYS = ["2023-06-14", "2023-09-13", "2023-12-13", "2024-03-13"]
DAYS_PREREG = ["2025-02-12", "2025-05-14", "2025-08-13", "2025-11-12"]
SAMPLE_IDX = (1, 4, 7, 10, 13, 16)            # 0-based trong moi nhom
GROUP_RANK = {"G1": (1, 20), "G2": (21, 100), "G3": (101, 200)}
WGROUP = {"G1": 20.0 / 200, "G2": 80.0 / 200, "G3": 100.0 / 200}
BREAKEVEN = 0.414                             # %/vong (RESULT_TRACKB_STEP1)
OUT = "/home/ubuntu/src/BinanceFuturesJava/docs/result/book_cost2.json"
PANEL = "/tmp/trackb"


def log(*a):
    print(*a, flush=True)


def _open_range(url):
    req = urllib.request.Request(url, headers={"Range": "bytes=0-%d" % (RANGE_MB * 1024 * 1024 - 1)})
    return urllib.request.urlopen(req, timeout=90)


def stream_lines(url, t_hi):
    """Yield CSV lines (bytes) cua entry dau trong zip, dung khi kip ts > t_hi. Tra (nbytes, stopped)."""
    r = _open_range(url)
    d = zlib.decompressobj(-15)
    first = True
    buf = b""
    nbytes = 0
    stopped = False
    while True:
        raw = r.read(1 << 20)
        if not raw:
            break
        nbytes += len(raw)
        if first:
            sig = struct.unpack("<I", raw[:4])[0]
            if sig != 0x04034B50:
                r.close()
                raise RuntimeError("not a zip local header")
            _s, _v, _f, _m, _t, _d, _c, _cs, _us, nlen, xlen = struct.unpack("<IHHHHHIIIHH", raw[:30])
            raw = raw[30 + nlen + xlen:]
            first = False
        out = buf + d.decompress(raw)
        parts = out.split(b"\n")
        buf = parts.pop()
        for ln in parts:
            if ln:
                yield ln
        if stopped:
            break
    r.close()
    yield b"__EOF__"


def parse_window(url, t_lo, t_hi, kind):
    """Tra list rows (fields) trong [t_lo, t_hi). kind='book'|'agg'."""
    rows = []
    for ln in stream_lines(url, t_hi):
        if ln == b"__EOF__":
            break
        if ln[:1].isalpha():                       # header
            continue
        f = ln.split(b",")
        try:
            if kind == "book":
                ts = int(f[5])
                if ts < t_lo:
                    continue
                if ts >= t_hi:
                    break
                rows.append((ts, float(f[1]), float(f[2]), float(f[3]), float(f[4])))
            else:
                ts = int(f[5])
                if ts < t_lo:
                    continue
                if ts >= t_hi:
                    break
                rows.append((ts, float(f[1]), float(f[2]), f[6].strip() == b"true"))
        except (ValueError, IndexError):
            continue
    return rows


def measure(sym, day):
    t_lo = int(np.datetime64(day + "T00:00:00", "ms").astype(np.int64))
    t_hi = t_lo + WMIN * 60000
    b = parse_window("%s/bookTicker/%s/%s-bookTicker-%s.zip" % (BASE, sym, sym, day), t_lo, t_hi, "book")
    a = parse_window("%s/aggTrades/%s/%s-aggTrades-%s.zip" % (BASE, sym, sym, day), t_lo, t_hi, "agg")
    if len(b) < 10 or len(a) < 10:
        return None
    bt = np.array([r[0] for r in b], dtype=np.int64)
    bmid = np.array([(r[1] + r[3]) / 2.0 for r in b])
    bqs = np.array([(r[3] - r[1]) / ((r[3] + r[1]) / 2.0) * 100.0 for r in b])
    bbudq = np.array([r[1] * r[2] for r in b])       # bid notional L1
    baskq = np.array([r[3] * r[4] for r in b])       # ask notional L1
    at = np.array([r[0] for r in a], dtype=np.int64)
    ap = np.array([r[1] for r in a])
    aq = np.array([r[2] for r in a])
    amaker = np.array([r[3] for r in a])
    idx = np.searchsorted(bt, at, side="right") - 1
    ok = idx >= 0
    idx = idx[ok]
    at, ap, aq, amaker = at[ok], ap[ok], aq[ok], amaker[ok]
    mid = bmid[idx]
    sgn = np.where(amaker, -1.0, 1.0)
    e = sgn * (ap - mid) / mid * 100.0
    notion = ap * aq
    l1 = np.where(amaker, bbudq[idx], baskq[idx])
    exceed = notion > l1
    return dict(sym=sym, day=day, n_book=len(b), n_tr=len(at),
                qs=bqs, mid=float(np.median(bmid)), mid_med_notional=float(np.median(l1)),
                e=e, notion=notion, exceed=float(exceed.mean()) if len(exceed) else float("nan"))


def pick_symbols():
    z = np.load(PANEL + "/panel.npz")
    meta = json.load(open(PANEL + "/meta.json"))
    dv, dvn = z["dv_med"], z["dv_n"]
    names = meta["sym_names"]
    ok = np.isfinite(dv) & (dvn >= 12)
    cand = [i for i in range(len(names)) if ok[i] and names[i]]
    cand.sort(key=lambda i: -dv[i])
    top = cand[:200]
    out = {}
    for g, (lo, hi) in GROUP_RANK.items():
        seg = top[lo - 1:hi]
        out[g] = [names[seg[i]] for i in SAMPLE_IDX if i < len(seg)]
    return out, [names[i] for i in top]


def main():
    t0 = time.time()
    syms, top200 = pick_symbols()
    log("sample: %s" % json.dumps(syms))
    gk = {}
    for g, ss in syms.items():
        for s in ss:
            gk[s] = g
    data = {}
    nmiss = 0
    for g, ss in syms.items():
        for s in ss:
            for d in DAYS:
                try:
                    r = measure(s, d)
                except Exception as ex:
                    log("  MISS %s %s : %s" % (s, d, ex))
                    nmiss += 1
                    continue
                if r is None:
                    nmiss += 1
                    continue
                data.setdefault(g, []).append(r)
            log("done %s %s (%.0fs)" % (g, s, time.time() - t0))

    res = dict(prereg="docs/prereg/PREREG_BOOK_COST2.md", commit_prereg="b8bcca9",
               source="Binance Vision futures/um daily bookTicker + aggTrades (free, no key)",
               window="[00:00,00:30) UTC", days=DAYS, days_prereg=DAYS_PREREG,
               days_deviation="bookTicker daily chi publish ~2023-05-16..2024-03-30; 4 ngay prereg 2025 = 404; doi sang 4 ngay cung vi tri trong cua so co du lieu",
               fee_leg_pct=FEE_LEG,
               sizes=list(SIZES), quantiles=list(KQ), breakeven_pct=BREAKEVEN,
               n_missing=nmiss, groups={}, C_group={}, C={}, verdict=None, top200_head=top200[:20])
    for g, rs in data.items():
        e = np.concatenate([r["e"] for r in rs])
        no = np.concatenate([r["notion"] for r in rs])
        qs = np.concatenate([r["qs"] for r in rs])
        gg = dict(n_sym_days=len(rs), n_trades=int(len(e)),
                  syms=sorted(set(r["sym"] for r in rs)),
                  qs_med=float(np.median(qs)), qs_p90=float(np.percentile(qs, 90)),
                  qs_mean=float(qs.mean()),
                  l1_notional_med=float(np.median([r["mid_med_notional"] for r in rs])),
                  exceed_frac=float(np.mean([r["exceed"] for r in rs])),
                  h={}, n_bucket={}, imp={})
        for S in SIZES:
            m = (no >= S / np.sqrt(2.0)) & (no < S * np.sqrt(2.0))
            if m.sum() >= 20:
                hh = {("k%.1f" % k): float(np.quantile(e[m], k)) for k in KQ}
                gg["h"]["%d" % S] = hh
                gg["n_bucket"]["%d" % S] = int(m.sum())
                gg["imp"]["%d" % S] = {kk: vv - gg["qs_med"] / 2.0 for kk, vv in hh.items()}
            else:
                gg["h"]["%d" % S] = None
                gg["n_bucket"]["%d" % S] = int(m.sum())
        res["groups"][g] = gg
        for S in SIZES:
            if gg["h"].get("%d" % S):
                res["C_group"].setdefault("%d" % S, {})[g] = {
                    kk: 2 * FEE_LEG + 2 * vv for kk, vv in gg["h"]["%d" % S].items()}
    for S in SIZES:
        cg = res["C_group"].get("%d" % S)
        if not cg:
            res["C"]["%d" % S] = None
            continue
        res["C"]["%d" % S] = {kk: sum(WGROUP[g] * cg[g][kk] for g in cg) for kk in cg[list(cg)[0]]}
    c2000 = res["C"].get("2000")
    if c2000:
        cc = c2000["k0.5"]
        res["verdict"] = dict(central_pct=cc, breakeven=BREAKEVEN,
                             le_breakeven=bool(cc <= BREAKEVEN),
                             rule="MO LAI Track B (chay lai buoc 1 voi phi nay)" if cc <= BREAKEVEN
                             else "NULL vi CHI PHI (giu nguyen)")
    json.dump(res, open(OUT, "w"), ensure_ascii=False, indent=1, default=float)
    log("WROTE %s (%.0fs) keys=%s" % (OUT, time.time() - t0, list(res["C"].keys())))
    log(json.dumps({"C": res["C"], "verdict": res["verdict"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
