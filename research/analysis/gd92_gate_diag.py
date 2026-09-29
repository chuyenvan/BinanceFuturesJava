#!/usr/bin/env python3
"""GD92 GATE DIAG — tai dung chuoi nguong cuon GD92 (92-phan-vi predReturn15M, W=90d, causal)
tu pred.bin DEV, roi bao (a) nguong hieu dung theo quy + % gio gate mo, (c) nguong tai 2025-12-31.

Thuc thi DUNG docs/prereg/PREREG_GD92_R4_P3.md muc 5 (chuan doan MO TA, KHONG phai cong).

THUAN PYTHON OFFLINE. KHONG Java/sim. DEV <= 2025-12-31 (KHONG doc 2026).

Tai dung CHINH XAC code Java `GateRollingThreshold.init` (branch gd92-recheck, commit 1db0613):
  - GRID = 15 phut; chi lay mau `ts % (15*60_000) == 0`.
  - cua so [h - W, h) voi W = 90 ngay = 90*24*3600000 ms.
  - hStart = ((ts[0] + W) / HOUR + 1) * HOUR ; hEnd = ts[n-1] (HOUR = 3600000).
  - phan vi NEAREST-RANK KHONG noi suy: sort tang, k = min(m-1, max(0, floor(pct*(m-1)))), thr = buf[k].
  - bo moc gio co m < MIN_SAMPLES = 96*7 = 672.

Sanity bat buoc: min/max chuoi nguong phai khop log `[GATE-ROLL]` (0,00456 / 0,01265).

Usage:
  python3 gd92_gate_diag.py --json /home/ubuntu/src/BinanceFuturesJava/docs/result/gd92_gate_diag.json
"""
import argparse
import json
import logging
import os
import struct

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gd92_gate_diag")

PRED_BIN = "/home/ubuntu/wfo_ds_x1_2021/pred.bin"
HOUR = 3600000
GRID = 15 * 60000
PCT = 0.92
DAYS = 90
MIN_SAMPLES = 96 * 7
CONST = 0.008          # SIM_MIN_MOMENTUM_15M (hanh vi D0 / fallback)
DEV_START = 1625068800000   # 2021-07-01 00:00 UTC (ms)
DEV_END = 1767225600000     # 2026-01-01 00:00 UTC (ms) — moc cuoi DEV la 2025-12-31
LOG_MIN, LOG_MAX = 0.00456, 0.01265


def load_pred(path):
    """tra (ts:int64[], p15:float32[]) tren luoi 15 phut, sort tang (TreeMap thu tu san)."""
    ts, val = [], []
    with open(path, "rb") as f:
        cnt = struct.unpack(">i", f.read(4))[0]
        for _ in range(cnt):
            t = struct.unpack(">q", f.read(8))[0]
            p15 = struct.unpack(">f", f.read(4))[0]
            f.read(4)          # predRisk4H (bo)
            if t % GRID == 0:
                ts.append(t)
                val.append(p15)
    return np.asarray(ts, dtype=np.int64), np.asarray(val, dtype=np.float32)


def build_rolling(ts, val, pct=PCT, days=DAYS):
    """Tai dung GateRollingThreshold.init -> (hours:int64[], thr:float32[])."""
    w = days * 24 * HOUR
    h_start = ((ts[0] + w) // HOUR + 1) * HOUR
    h_end = ts[-1]
    n = len(ts)
    out_h, out_t = [], []
    lo = hi = 0
    for h in range(h_start, h_end + 1, HOUR):
        while lo < n and ts[lo] < h - w:
            lo += 1
        while hi < n and ts[hi] < h:
            hi += 1
        m = hi - lo
        if m < MIN_SAMPLES:
            continue
        b = np.sort(val[lo:hi])          # copy (Java System.arraycopy + Arrays.sort)
        k = min(m - 1, max(0, int(np.floor(pct * (m - 1)))))
        out_h.append(h)
        out_t.append(float(b[k]))
    return np.asarray(out_h, dtype=np.int64), np.asarray(out_t, dtype=np.float32)


def q_of(ms):
    dt = ms.astype("datetime64[ms]").astype("datetime64[M]")
    y = dt.astype("datetime64[Y]").astype(int) + 1970
    mth = dt.astype("datetime64[M]").astype(int) % 12 + 1
    q = (mth - 1) // 3 + 1
    return np.char.add(np.char.add(y.astype(str), "Q"), q.astype(str))


def quarter_stats(hours, thr):
    """median/p10/p90 cua chuoi nguong theo quy (chi DEV)."""
    m = hours < DEV_END
    hours, thr = hours[m], thr[m]
    qs = q_of(hours)
    out = {}
    for q in np.unique(qs):
        v = thr[qs == q]
        out[str(q)] = dict(n=int(len(v)), p10=float(np.percentile(v, 10)),
                           p50=float(np.percentile(v, 50)), p90=float(np.percentile(v, 90)))
    return out


def gate_open_rate(ts, p15, hours, thr):
    """% gio gate mo theo quy: fraction mau 15' co predReturn15M >= nguong hieu dung.
    D0: nguong hang so CONST. D1: nguong cuon floorEntry(ts). Chi DEV (2021Q3..2025Q4)."""
    m = (ts >= DEV_START) & (ts < DEV_END)
    ts, p15 = ts[m], p15[m]
    # floorEntry(ts): index gio lon nhat <= ts
    idx = np.searchsorted(hours, ts, side="right") - 1
    thr1 = np.where(idx >= 0, thr[np.clip(idx, 0, len(thr) - 1)], CONST)
    open0 = (p15 >= CONST).astype(np.float64)
    open1 = (p15 >= thr1).astype(np.float64)
    qs = q_of(ts)
    out = {}
    for q in np.unique(qs):
        sel = qs == q
        out[str(q)] = dict(n=int(sel.sum()),
                           open_d0=float(open0[sel].mean() * 100.0),
                           open_d1=float(open1[sel].mean() * 100.0))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/gd92_gate_diag.json")
    a = ap.parse_args()

    ts, val = load_pred(PRED_BIN)
    log.info("pred.bin: %d mau tren luoi 15' (%.3f..%.3f, DEV>%s)",
             len(ts), float(val.min()), float(val.max()), "2021-07-01")
    hours, thr = build_rolling(ts, val)
    log.info("chuoi nguong cuon: %d moc gio (min=%.5f max=%.5f mean=%.5f)",
             len(hours), float(thr.min()), float(thr.max()), float(thr.mean()))

    # sanity bat buoc vs log [GATE-ROLL]
    ok_min = abs(float(thr.min()) - LOG_MIN) < 5e-5
    ok_max = abs(float(thr.max()) - LOG_MAX) < 5e-5
    log.info("SANITY [GATE-ROLL] min %.5f==%.5f %s | max %.5f==%.5f %s",
             float(thr.min()), LOG_MIN, "PASS" if ok_min else "*** FAIL ***",
             float(thr.max()), LOG_MAX, "PASS" if ok_max else "*** FAIL ***")

    # (a) nguong theo quy
    qs_thr = quarter_stats(hours, thr)
    log.info("")
    log.info("(a) NGUONG GD92 HIEU DUNG THEO QUY (so hang 0.008):")
    log.info("  %-8s %6s %8s %8s %8s" % ("quy", "n", "p10", "p50", "p90"))
    for q, v in qs_thr.items():
        log.info("  %-8s %6d %8.5f %8.5f %8.5f" % (q, v["n"], v["p10"], v["p50"], v["p90"]))

    # (a) % gio gate mo theo quy (D0 vs D1)
    go = gate_open_rate(ts, val, hours, thr)
    log.info("")
    log.info("(a) %% GIO GATE MO THEO QUY (D0 hang 0.008 vs D1 nguong cuon):")
    log.info("  %-8s %8s %9s %9s %9s" % ("quy", "n15m", "openD0%", "openD1%", "D1-D0pp"))
    for q, v in go.items():
        log.info("  %-8s %8d %9.3f %9.3f %+9.3f" % (q, v["n"], v["open_d0"], v["open_d1"],
                                                   v["open_d1"] - v["open_d0"]))

    # (c) nguong tai cuoi DEV 2025-12-31
    thr_end = float(thr[hours <= DEV_END][-1]) if (hours <= DEV_END).any() else float("nan")
    log.info("")
    log.info("(c) NGUONG GD92 tai cuoi DEV 2025-12-31 = %.5f  (hang 0.008; ty le %.3fx)",
             thr_end, thr_end / CONST)

    out = dict(pred_n=len(ts), thr_n=len(hours), thr_min=float(thr.min()), thr_max=float(thr.max()),
               sanity_min=ok_min, sanity_max=ok_max,
               quarter_thr=qs_thr, gate_open=go, thr_at_dev_end=thr_end, const=CONST)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)


if __name__ == "__main__":
    main()
