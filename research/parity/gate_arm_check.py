#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiem gate rolling G2 (B7): doc buffer GRR1 (GateRatioPersist, run/gate_ratio_live.bin) STRICT, tinh lai
  - firstTs, thoi diem arm = gio dau tien h voi (h - firstTs) >= 7 ngay (GateRatioBuffer.WARMUP_MS),
  - q_h = phan vi k=floor(pct*(m-1)) cua r trong cua so [h-days, h) (GateRatioBuffer.computeQ, causal),
  - so q_t trong log '[GATE-RATIO] q_t=' sau arm (--log) — phai khop q tinh lai (float32, +-1 ULP).
Chay duoc ngay hom nay (phan fallback: chua arm => q_t log = 0.008 = MIN_MOMENTUM_15M).
  python3 gate_arm_check.py <gate_ratio_live.bin> [--log full.log] [--pct 0.999950829] [--days 90]
Exit: 0 PASS / 2 FAIL / 3 MISSING (chua arm / khong co dong log sau arm).
"""
import argparse
import datetime as dt
import logging
import re
import struct
import sys
import zlib

import numpy as np

LOG = logging.getLogger("gate_arm_check")
TZ = dt.timezone(dt.timedelta(hours=7))
HOUR, DAY = 3600_000, 86_400_000
WARMUP = 7 * DAY


def read_grr1(path):
    raw = open(path, "rb").read()
    off, ts_l, r_l = 0, [], []
    while off < len(raw):
        if off + 12 > len(raw):
            raise ValueError("trailing header bytes %d" % (len(raw) - off))
        magic, ln, crc = struct.unpack(">iiI", raw[off:off + 12])
        off += 12
        if magic != 0x47525231:
            raise ValueError("bad magic at %d" % (off - 12))
        comp = raw[off:off + ln]
        off += ln
        if len(comp) != ln or (zlib.crc32(comp) & 0xffffffff) != crc:
            raise ValueError("crc/truncated chunk")
        import snappy
        u = snappy.uncompress(comp)
        a = np.frombuffer(u, dtype=np.dtype([("ts", ">i8"), ("r", ">f4")]))
        ts_l.append(a["ts"].astype(np.int64))
        r_l.append(a["r"].astype(np.float32))
    return np.concatenate(ts_l), np.concatenate(r_l)


def q_at(ts, r, h, pct, days):
    m_ = (ts >= h - days * DAY) & (ts < h)           # causal: chi r co ts < h
    a = np.sort(r[m_])
    m = len(a)
    if m == 0:
        return None, 0
    k = min(m - 1, max(0, int(np.floor(pct * (m - 1)))))
    return float(a[k]), m


def analyse(path, pct=0.999950829, days=90, now_ms=None):
    ts, r = read_grr1(path)
    now_ms = now_ms or int(dt.datetime.now(TZ).timestamp() * 1000)
    first = int(ts.min())
    arm = -(-(first + WARMUP) // HOUR) * HOUR       # gio dau tien h >= first+7d
    h_now = (now_ms // HOUR) * HOUR
    armed = h_now >= arm
    q_now, m_now = q_at(ts, r, h_now, pct, days)
    f = lambda t: dt.datetime.fromtimestamp(t / 1000, TZ).strftime("%Y-%m-%d %H:%M")
    return {"n": int(len(ts)), "ticks": int(len(np.unique(ts))), "first_ts": f(first), "last_ts": f(int(ts.max())), "arm_ts": f(arm),
            "armed": bool(armed), "q_now": q_now if q_now is not None else float("nan"), "m_window": m_now,
            "r_p50": float(np.median(r)), "r_p99": float(np.quantile(r, 0.99)), "r_max": float(r.max()),
            "hours_to_arm": max(0.0, (arm - now_ms) / HOUR)}


def check_log(path_bin, path_log, pct, days):
    """So q_t log sau arm voi q tinh lai tu buffer TAI THOI DIEM do (chi dung r ts<h, nen file bin phai la ban LUC do hoac moi hon)."""
    ts, r = read_grr1(path_bin)
    rx = re.compile(r"^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.\d+.*\[GATE-RATIO\] q_t=([\d.eE+-]+)")
    res = []
    for ln in open(path_log, errors="replace"):
        m = rx.match(ln)
        if not m:
            continue
        t = int(dt.datetime.strptime(m.group(1), "%d/%m/%Y %H:%M:%S").replace(tzinfo=TZ).timestamp() * 1000)
        h = (t // HOUR) * HOUR
        if h - int(ts.min()) < WARMUP:
            res.append((h, float(m.group(2)), None, "pre-arm"))
            continue
        q, _ = q_at(ts, r, h, pct, days)
        res.append((h, float(m.group(2)), q, "armed"))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bin")
    ap.add_argument("--log")
    ap.add_argument("--pct", type=float, default=0.999950829)
    ap.add_argument("--days", type=int, default=90)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    r = analyse(a.bin, a.pct, a.days)
    LOG.info("buffer n=%d ticks=%d  %s .. %s  r p50=%.6f p99=%.6f max=%.6f", r["n"], r["ticks"], r["first_ts"], r["last_ts"], r["r_p50"], r["r_p99"], r["r_max"])
    LOG.info("arm tu %s (con %.1f h) -> %s; q(0.99995, %dd) neu arm bay gio = %.6f (m=%d)", r["arm_ts"], r["hours_to_arm"],
             "DA ARM" if r["armed"] else "CHUA ARM (q_t log phai = 0.008 fallback)", a.days, r["q_now"], r["m_window"])
    if not a.log:
        return 0 if r["armed"] else 3
    rows = check_log(a.bin, a.log, a.pct, a.days)
    armed = [x for x in rows if x[3] == "armed"]
    pre = [x for x in rows if x[3] == "pre-arm"]
    bad_pre = [x for x in pre if abs(x[1] - 0.008) > 1e-9]
    LOG.info("log: %d dong q_t truoc arm (sai != 0.008: %d), %d dong sau arm", len(pre), len(bad_pre), len(armed))
    if bad_pre:
        return 2
    if not armed:
        return 3
    worst = max(abs(x[1] - x[2]) / max(1e-12, abs(x[2])) for x in armed)
    LOG.info("sau arm: max |q_log - q_tinh_lai|/q = %.2e (PASS <= 1e-6)", worst)
    return 0 if worst <= 1e-6 else 2


if __name__ == "__main__":
    sys.exit(main())
