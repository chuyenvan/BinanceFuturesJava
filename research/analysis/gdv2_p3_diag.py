#!/usr/bin/env python3
"""GDV2_P3 DIAG — chan doan MO TA (KHONG cong) cho TASK GDV2_P3.

Thuc thi DUNG docs/prereg/PREREG_GDV2_P3.md muc 5:
  (a) bang quy DAY DU: n (sel/BD/DCA) + seen/pass/pass-rate theo quy tu log [GATE-RATIO]
      + win%/TSloss%/PnL/maxDD (qstat_r4.py chay rieng).
  (b) phan ra 2025Q2/Q3: pass-rate G0 (base hang 0.008) vs G2 (rolling ratio) => gate hay vacancy.
  (c) [SUY LUAN] proxy q_t: phan vi cuon cua p15 tai pct=0.99995083, W=90d, causal — tu pred.bin DEV
      (15' grid) lam minh hoa XU HUONG q_t (vì r = p15/(factor*gs), factor gần hằng cho top-K).

THUAN PYTHON OFFLINE. KHONG Java/sim. DEV <= 2025-12-31 (KHONG doc 2026).

Usage:
  python3 gdv2_p3_diag.py --json docs/result/gdv2_p3_diag.json
"""
import argparse
import json
import logging
import os
import re
import struct

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("gdv2diag")

KOUT = "/home/ubuntu/kaggle_sim/out"
PRED_BIN = "/home/ubuntu/wfo_ds_x1_2021/pred.bin"
HOUR = 3600000
GRID = 15 * 60000
PCT = 0.99995083
DAYS = 90
MIN_SAMPLES = 96 * 7          # 7 ngay (warm-up cua GateRollingRatio)
CONST = 0.008
DEV_END = 1767225600000       # 2026-01-01 00:00 UTC (ms); moc cuoi DEV = 2025-12-31

TAGS = ["gdv2-g0", "gdv2-g1", "gdv2-g2"]
RX_RHO = re.compile(r"GATE-RATIO\s+(\S+)\s+pct=(\S+)\s+days=(\d+)\s+seen=(\d+)\s+pass=(\d+)\s+rho=(\S+)")
RX_RHO_Q = re.compile(r"(\d{4}Q[1-4]):(\d+)/(\d+)")


def gate_quarterly(tag):
    """Parse [GATE-RATIO] -> (rho, OrderedDict quarter -> dict(seen, pass, rate))."""
    p = os.path.join(KOUT, tag, "logs", "sim.out")
    rho = float("nan")
    qq = {}
    with open(p, errors="ignore") as fh:
        for line in fh:
            if "GATE-RATIO" not in line or "pct=" not in line:
                continue
            m = RX_RHO.search(line)
            if m:
                rho = float(m.group(6))
            for mm in RX_RHO_Q.finditer(line):
                q = mm.group(1)
                seen = int(mm.group(3))
                passed = int(mm.group(2))
                qq[q] = dict(seen=seen, passed=passed, rate=(passed / seen if seen else None))
    return rho, qq


def load_pred(path):
    ts, val = [], []
    with open(path, "rb") as f:
        cnt = struct.unpack(">i", f.read(4))[0]
        for _ in range(cnt):
            t = struct.unpack(">q", f.read(8))[0]
            p15 = struct.unpack(">f", f.read(4))[0]
            f.read(4)
            if t % GRID == 0:
                ts.append(t)
                val.append(p15)
    return np.asarray(ts, dtype=np.int64), np.asarray(val, dtype=np.float32)


def build_rolling(ts, val, pct=PCT, days=DAYS):
    """Tai dung GateRollingRatio.computeQ (phan vi cuon causal tren W=90d) tren luoi 15'."""
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
        b = np.sort(val[lo:hi])
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


def week_of(ms):
    """ISO week 'YYYY-Www'."""
    d = ms.astype("datetime64[ms]").astype("datetime64[D]")
    return np.array([np.datetime64(x, "D").astype("datetime64[W]").astype(str) for x in d])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/gdv2_p3_diag.json")
    a = ap.parse_args()

    # (a/b) pass-rate theo quy
    gate = {}
    for t in TAGS:
        rho, qq = gate_quarterly(t)
        gate[t] = dict(rho=rho, quarterly=qq)
        log.info("%-10s rho=%.8f | quy co data=%d", t, rho, len(qq))

    # (b) phan ra 2025Q2/Q3
    log.info("")
    log.info("(b) PHAN RA 2025Q2/Q3 — pass-rate G0 (base 0.008) vs G2 (rolling ratio):")
    for q in ("2025Q2", "2025Q3"):
        g0 = gate["gdv2-g0"]["quarterly"].get(q)
        g2 = gate["gdv2-g2"]["quarterly"].get(q)
        log.info("  %s: G0 pass=%d seen=%d rate=%.3e | G2 pass=%d seen=%d rate=%.3e | G2/G0 rate=%.3f",
                 q, g0["passed"], g0["seen"], g0["rate"], g2["passed"], g2["seen"], g2["rate"],
                 g2["rate"] / g0["rate"] if g0["rate"] else float("nan"))

    # (c) proxy q_t tu pred.bin
    ts, val = load_pred(PRED_BIN)
    hours, thr = build_rolling(ts, val)
    m = hours < DEV_END
    hours, thr = hours[m], thr[m]
    log.info("")
    log.info("(c) [SUY LUAN] proxy q_t = phan vi cuon p15 (pct=%.8f, W=%dd) tu pred.bin DEV:",
             PCT, DAYS)
    log.info("  n_moc_gio=%d | min=%.5f max=%.5f median=%.5f | %d quy", len(hours),
             float(thr.min()), float(thr.max()), float(np.median(thr)), len(set(q_of(hours))))

    # (b) proxy q_t theo tuần 2025Q1-Q3
    qs = q_of(hours)
    weeks = week_of(hours)
    log.info("")
    log.info("  (b) [SUY LUAN] proxy q_t theo TUAN 2025Q1-Q3 (median %/tuan):")
    wq = {}
    for q in ("2025Q1", "2025Q2", "2025Q3"):
        sel = qs == q
        for wk in np.unique(weeks[sel]):
            v = thr[sel & (weeks == wk)]
            wq[str(wk)] = dict(q=q, median=float(np.median(v)), n=int(len(v)))
    for wk in sorted(wq):
        log.info("    %s  %s  q_t_proxy=%.5f (n=%d)", wk, wq[wk]["q"], wq[wk]["median"], wq[wk]["n"])

    # (c) q_t tai cuoi DEV 2025-12-31 vs median toan ky
    thr_end = float(thr[-1])
    thr_med = float(np.median(thr))
    log.info("")
    log.info("  (c) [SUY LUAN] proxy q_t tai 2025-12-31 = %.5f | median toan ky = %.5f | ty le = %.3fx",
             thr_end, thr_med, thr_end / thr_med)

    out = dict(prereg="docs/prereg/PREREG_GDV2_P3.md",
               gate={t: dict(rho=gate[t]["rho"],
                             quarterly={q: v for q, v in gate[t]["quarterly"].items()})
                     for t in TAGS},
               proxy=dict(pct=PCT, days=DAYS, n_moc=len(hours),
                          min=float(thr.min()), max=float(thr.max()),
                          median=float(np.median(thr)),
                          weekly_2025={wk: v for wk, v in wq.items()},
                          thr_at_dev_end=thr_end, thr_median=thr_med,
                          ratio_end_vs_median=thr_end / thr_med))
    with open(a.json, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", a.json)


if __name__ == "__main__":
    main()
