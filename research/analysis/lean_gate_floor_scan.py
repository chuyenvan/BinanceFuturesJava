"""LEAN_GATE_AUDIT muc 3 — floor AI_DYNAMIC_MIN co bao gio bind trong top-K khong.

Quet bins selector cua profile (`WFO_FUNDING_PRED_DIR`), voi moi moc 15m lay K coin co
`symbolPred` THAP nhat (= dung `chosenCands` cua SimulatorMarketLevelTicker1MStopLoss:336-337)
roi dem so slot ma:
  (a) `symbolPred < AI_DYNAMIC_MIN * RATE_MAX / MULT`  -> floor thang => gate KHONG rut ve K*sp;
  (b) `symbolPred < RATE_MAX / MULT`                   -> dyn_thr < thr_base => early-gate vung noi.
`symbolPred = 1 - p0`, quy uoc cua WfoDataset.java:245-249 (horizonIdx=0, "DAO DAU").
Khong print(); dung logging theo AGENT_RUNBOOK muc 0 diem 5.
"""
import argparse
import datetime
import glob
import logging
import os

import numpy as np

LOG = logging.getLogger("lean_gate_floor_scan")

DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"),
               ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
SEAL_MS = 1767200400000          # HoldoutSeal 2026-01-01 00:00 GMT+7
BINS_DEFAULT = "/home/ubuntu/predwf_map_s1a2_x1"

# Tham so gate — GIU DUNG gia tri hieu dung cua x1_c3_full + Configs.java (xem doc muc 2.3)
THR_BASE = 0.008        # SIM_MIN_MOMENTUM_15M (profile:32, 242 conf/env.sh)
DYN_MIN = 0.26787       # Configs.AI_DYNAMIC_MIN
DYN_MULT = 1.28760      # Configs.AI_DYNAMIC_MULTIPLIER
RATE_MAX = 0.15         # Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD
TOPK = 8                # SELECTOR_RANK_TOPK


def dyn_thr(sp):
    return THR_BASE * max(DYN_MIN, sp / RATE_MAX * DYN_MULT)


def year_of(ts_ms):
    return datetime.datetime.utcfromtimestamp(ts_ms / 1000 + 7 * 3600).year


def scan(bins_dir):
    floor_cut = DYN_MIN * RATE_MAX / DYN_MULT
    early_cut = RATE_MAX / DYN_MULT
    k_lin = THR_BASE * DYN_MULT / RATE_MAX
    LOG.info("K=%.7f floor_cut=%.6f early_cut=%.6f topk=%d", k_lin, floor_cut, early_cut, TOPK)
    per_year = {}
    g_min, g_ts = 1e9, None
    n_rec = n_tick = 0
    for f in sorted(glob.glob(os.path.join(bins_dir, "predict_wf_*.bin"))):
        a = np.fromfile(f, dtype=DT)
        a = a[~np.isnan(a["p0"])]
        a = a[a["ts"] < SEAL_MS]
        sp = 1.0 - a["p0"].astype(np.float64)
        ts = a["ts"]
        order = np.argsort(ts, kind="stable")
        ts, sp = ts[order], sp[order]
        n_rec += len(sp)
        cut = np.flatnonzero(np.diff(ts)) + 1
        for s, e in zip(np.concatenate(([0], cut)), np.concatenate((cut, [len(ts)]))):
            blk = sp[s:e]
            if not len(blk):
                continue
            k = min(TOPK, len(blk))
            top = np.partition(blk, k - 1)[:k]
            mn = float(top.min())
            rec = per_year.setdefault(year_of(ts[s]), [1e9, 0, 0, 0])
            rec[0] = min(rec[0], mn)
            rec[1] += 1
            rec[2] += int((top < floor_cut).sum())
            rec[3] += int((top < early_cut).sum())
            if mn < g_min:
                g_min, g_ts = mn, int(ts[s])
            n_tick += 1
    LOG.info("n_rec=%d n_tick=%d", n_rec, n_tick)
    LOG.info("min symbolPred trong top-%d tren toan bo = %.6f (tick ts=%s)", TOPK, g_min, g_ts)
    LOG.info("%-6s %10s %12s %13s %13s", "nam", "nTick", "minTop8", "nBelowFloor", "nBelowEarly")
    tot = [0, 0, 0]
    for y in sorted(per_year):
        r = per_year[y]
        LOG.info("%-6d %10d %12.6f %13d %13d", y, r[1], r[0], r[2], r[3])
        tot = [tot[0] + r[1], tot[1] + r[2], tot[2] + r[3]]
    LOG.info("%-6s %10d %12s %13d %13d", "TONG", tot[0], "-", tot[1], tot[2])


def show_tick(bins_dir, tick_ts):
    for f in sorted(glob.glob(os.path.join(bins_dir, "predict_wf_*.bin"))):
        a = np.fromfile(f, dtype=DT)
        b = a[a["ts"] == tick_ts]
        if not len(b):
            continue
        sp = 1.0 - b["p0"].astype(np.float64)
        LOG.info("file=%s pool=%d tick=%s GMT+7", os.path.basename(f), len(b),
                 datetime.datetime.utcfromtimestamp(tick_ts / 1000 + 7 * 3600))
        k_lin = THR_BASE * DYN_MULT / RATE_MAX
        for i, j in enumerate(np.argsort(sp)[:TOPK + 2]):
            s = float(sp[j])
            LOG.info("  rank%-2d symId=%-4d symbolPred=%.6f dyn_thr=%.7f K*sp=%.7f delta=%.7f",
                     i + 1, int(b["sym"][j]), s, dyn_thr(s), k_lin * s, dyn_thr(s) - k_lin * s)


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins", default=os.environ.get("WFO_FUNDING_PRED_DIR", BINS_DEFAULT))
    ap.add_argument("--tick", type=int, default=None, help="in chi tiet mot moc 15m (ms)")
    args = ap.parse_args()
    if args.tick:
        show_tick(args.bins, args.tick)
    else:
        scan(args.bins)


if __name__ == "__main__":
    main()
