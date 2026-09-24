#!/usr/bin/env python3
"""BIGUP_MEDIUPDOWN — sinh tin hieu BIG_UP / MEDIUM_UP / MEDIUM_DOWN (logic code cu 157cf4d)
va do edge + MOM15 overlap. Pre-reg: docs/prereg/PREREG_BIGUP_MEDIUPDOWN.md (commit TRUOC khi chay).

Thuan Python, 0-sim, khong Java, khong push. Doc 1M closes causal tu raw/<sym>.f32
(Aerospike kline_1m_opt da extract san). Chi doc funding tu Aerospike (khong ghi).

Output: /tmp/bigup_mediumdown/{signals.csv, bu_arrays.npz, SIGNALS_DONE}. Tam, xoa sau.
"""
import os
import glob
import json
import logging
import time
from datetime import datetime, timezone

import numpy as np

import aerospike
import cramjam

RAW = "/home/ubuntu/claudedata/rvb_1m/raw"
OUT = "/tmp/bigup_mediumdown"
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bud")

# ---- LOCKED params (PREREG) ----
HOLD = 1440
TAKER = 0.0005
FEE = TAKER * 2
SLIP = 0.5
KTOP = 100
KFRAC = 4 / 5
MIN_SYM = 50
NUMBER_ORDER = 2

UTC = timezone.utc
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

BASE = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() // 60)
DEV_START = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp() // 60)
DEV_END = int(datetime(2024, 7, 1, tzinfo=UTC).timestamp() // 60)
SAMPLE_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)
NMIN = SAMPLE_END - BASE


def load_sym(path):
    a = np.fromfile(path, dtype=DT)
    if len(a) < 30:
        return None
    ts = a["ts"].astype(np.int64)
    order = np.argsort(ts, kind="stable")
    ts = ts[order]
    a = a[order]
    _, idx = np.unique(ts, return_index=True)
    ts = ts[idx]
    o = a["o"][idx].astype(np.float32)
    h = a["h"][idx].astype(np.float32)
    l = a["l"][idx].astype(np.float32)
    c = a["c"][idx].astype(np.float32)
    m = (ts >= BASE) & (ts < SAMPLE_END)
    ts, o, h, l, c = ts[m], o[m], h[m], l[m], c[m]
    if len(ts) < 30:
        return None
    return ts, o, h, l, c


def derive(o, h, c):
    """rc = C/O-1, d15 = C/max(H,15)-1. Tra (rc, d15) float32; d15 NaN khi <15 nen."""
    with np.errstate(invalid="ignore", divide="ignore"):
        rc = np.where(o > 0, c / o - 1.0, np.nan).astype(np.float32)
    n = len(h)
    d15 = np.full(n, np.nan, dtype=np.float32)
    if n >= 15:
        win = np.lib.stride_tricks.sliding_window_view(h, 15)
        mx = win.max(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            d15[14:] = np.where(mx > 0, c[14:] / mx - 1.0, np.nan).astype(np.float32)
    return rc, d15


def per_minute_stats(sorted_vals, offsets, cnt, nmin, block=40000):
    """bottom-100 mean va top-100 mean cua tung phut, tu mang compact da sap theo phut."""
    maxc = int(cnt.max())
    lo_arr = np.full(nmin, np.nan, dtype=np.float32)
    hi_arr = np.full(nmin, np.nan, dtype=np.float32)
    dense = np.empty((block, maxc), dtype=np.float32)
    for b0 in range(0, nmin, block):
        b1 = min(b0 + block, nmin)
        B = b1 - b0
        cb = cnt[b0:b1]
        tot = int(cb.sum())
        dens = dense[:B]
        dens[:] = np.nan
        if tot:
            rows = np.repeat(np.arange(B), cb)
            cols = np.arange(tot) - np.repeat(offsets[b0:b1] - offsets[b0], cb)
            dens[rows, cols] = sorted_vals[offsets[b0]:offsets[b0] + tot]
        dens.sort(axis=1)
        cs = np.cumsum(dens, axis=1, dtype=np.float32)
        kk = np.minimum(KTOP, (cb * KFRAC).astype(np.int64))
        ok = kk >= 1
        idxk = np.clip(kk - 1, 0, maxc - 1)
        lo = np.full(B, np.nan, dtype=np.float32)
        hidx = cb - 1
        lo2 = np.full(B, np.nan, dtype=np.float32)
        if ok.any():
            r = np.where(ok)[0]
            lo[r] = cs[r, idxk[r]] / kk[r]
            hh = hidx[r]
            hstart = np.clip(hh - kk[r], 0, maxc - 1)
            base_sum = np.where(hstart > 0, cs[r, hstart - 1], 0.0)
            lo2[r] = (cs[r, hh] - base_sum) / kk[r]
        lo_arr[b0:b1] = lo
        hi_arr[b0:b1] = lo2
    return lo_arr, hi_arr


def level_mask(rd, ru, rd15, btcrc, ok):
    """Nhan 1 level/phut theo dung thu tu if-else code cu (loai tru nhau)."""
    lab = np.zeros(len(rd), dtype=np.int8)  # 0 null
    # thu tu uu tien: BIG_UP, BIG_DOWN, MEDIUM_UP, MEDIUM_DOWN, SMALL_UP, SMALL_DOWN,
    #                  MEDIUM_DOWN_15M, SMALL_DOWN_15M
    m = ok.copy()
    c1 = m & (ru > 0.025)
    lab[c1] = 1
    m = m & ~c1
    c2 = m & (rd < -0.032) & (btcrc < -0.01)
    lab[c2] = 2
    m = m & ~c2
    c3 = m & (ru > 0.015)
    lab[c3] = 3
    m = m & ~c3
    c4 = m & ((rd < -0.030) | ((rd < -0.014) & (rd15 < -0.07)))
    lab[c4] = 4
    m = m & ~c4
    c5 = m & (ru > 0.008) & (rd > 0)
    lab[c5] = 5
    m = m & ~c5
    c6 = m & (rd < -0.006) & (ru < 0) & (rd15 < -0.025)
    lab[c6] = 6
    m = m & ~c6
    c7 = m & (rd15 < -0.045)
    lab[c7] = 7
    m = m & ~c7
    c8 = m & (rd15 < -0.028)
    lab[c8] = 8
    return lab


LABELS = {1: "BIG_UP", 3: "MEDIUM_UP", 4: "MEDIUM_DOWN", 2: "BIG_DOWN_OLD"}
DECISION = {1, 3, 4}


def main():
    files = sorted(glob.glob(RAW + "/*.f32"))
    log.info("symbols=%d BASE=%d NMIN=%d", len(files), BASE, NMIN)
    nz = OUT + "/bu_arrays.npz"

    # ---- pass 1: counts ----
    cnt = np.zeros(NMIN, dtype=np.int64)
    valid = []
    t0 = time.time()
    for i, p in enumerate(files):
        r = load_sym(p)
        if r is None:
            valid.append(False)
            continue
        ts, o, h, l, c = r
        rc, d15 = derive(o, h, c)
        rel = (ts - BASE).astype(np.int64)
        use = np.isfinite(rc) & np.isfinite(d15)
        cnt += np.bincount(rel[use], minlength=NMIN)
        valid.append(True)
        if i % 100 == 0:
            log.info("pass1 %d/%d %s el=%.0fs", i, len(files), os.path.basename(p), time.time() - t0)
    offsets = np.zeros(NMIN + 1, dtype=np.int64)
    np.cumsum(cnt, out=offsets[1:])
    total = int(offsets[-1])
    log.info("pass1 done total_rows=%d (%.1fGB x3) el=%.0fs", total, total * 4 / 1e9, time.time() - t0)

    # ---- pass 2: scatter ----
    rc_s = np.empty(total, dtype=np.float32)
    d15_s = np.empty(total, dtype=np.float32)
    sym_s = np.empty(total, dtype=np.int16)
    cur = np.zeros(NMIN, dtype=np.int64)  # cursor: layout minute-major, slot = offsets[j] + cur[j]
    t0 = time.time()
    for i, p in enumerate(files):
        if not valid[i]:
            continue
        r = load_sym(p)
        ts, o, h, l, c = r
        rc, d15 = derive(o, h, c)
        rel = (ts - BASE).astype(np.int64)
        use = np.isfinite(rc) & np.isfinite(d15)
        rel = rel[use]
        rcv = rc[use]
        d15v = d15[use]
        if len(rel) == 0:
            continue
        cntm = np.bincount(rel, minlength=NMIN)
        dest = offsets[rel] + cur[rel]
        cur[rel] += 1
        rc_s[dest] = rcv
        d15_s[dest] = d15v
        sym_s[dest] = i
        if i % 100 == 0:
            log.info("pass2 %d/%d el=%.0fs", i, len(files), time.time() - t0)
    log.info("pass2 done el=%.0fs", time.time() - t0)

    # ---- per-minute aggregates ----
    t0 = time.time()
    rd, ru = per_minute_stats(rc_s, offsets, cnt, NMIN)
    log.info("rateDownAvg/rateUpAvg done el=%.0fs", time.time() - t0)
    t0 = time.time()
    rd15, _ = per_minute_stats(d15_s, offsets, cnt, NMIN)
    log.info("rateDown15MAvg done el=%.0fs", time.time() - t0)
    del rc_s
    np.savez_compressed(nz, rd=rd, ru=ru, rd15=rd15, cnt=cnt.astype(np.int32))
    open(OUT + "/_agg_ok", "w").write("ok")
    return _post(files, rd, ru, rd15, cnt, offsets, d15_s, sym_s)


def _post(files, rd, ru, rd15, cnt, offsets, d15_s, sym_s):
    # ---- btc rate ----
    btu = load_sym(RAW + "/BTCUSDT.f32")
    bts, bo, bh, bl, bc = btu
    with np.errstate(invalid="ignore", divide="ignore"):
        btrc = np.where(bo > 0, bc / bo - 1.0, np.nan).astype(np.float32)
    btcrc = np.full(NMIN, np.nan, dtype=np.float32)
    brel = (bts - BASE).astype(np.int64)
    m = (brel >= 0) & (brel < NMIN)
    btcrc[brel[m]] = btrc[m]

    ok = (cnt >= MIN_SYM) & np.isfinite(rd) & np.isfinite(ru) & np.isfinite(rd15) & np.isfinite(btcrc)
    lab = level_mask(rd, ru, rd15, btcrc, ok)
    log.info("label counts: %s", {LABELS[k]: int((lab == k).sum()) for k in LABELS})

    # ---- fires (per-minute, symbol lock during HOLD) ----
    unlock = np.full(len(files), -1, dtype=np.int64)
    rows = []
    fire_min = np.where((lab == 1) | (lab == 2) | (lab == 3) | (lab == 4))[0]
    log.info("fire minutes (4 series) = %d", len(fire_min))
    t0 = time.time()
    for n, m in enumerate(fire_min):
        lv = int(lab[m])
        a = offsets[m]
        b = offsets[m + 1]
        if b - a < 1:
            continue
        cand = d15_s[a:b]
        syms = sym_s[a:b]
        order = np.argsort(cand, kind="stable")
        picked = 0
        for oi in order:
            s = int(syms[oi])
            if unlock[s] > m:
                continue
            unlock[s] = m + HOLD
            rows.append((m, s, lv))
            picked += 1
            if picked >= NUMBER_ORDER:
                break
        if n % 20000 == 0:
            log.info("fires %d/%d events=%d el=%.0fs", n, len(fire_min), len(rows), time.time() - t0)
    log.info("events=%d el=%.0fs", len(rows), time.time() - t0)

    # ---- returns + costs ----
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    fcache = {}

    def load_funding(sym):
        if sym in fcache:
            return fcache[sym]
        try:
            k = cli.get(("test", "funding_data", sym))
            bd = k[2]
            if not bd or "f_data" not in bd:
                fcache[sym] = None
                return None
            d = json.loads(bytes(cramjam.snappy.decompress_raw(bd["f_data"])))
            arr = sorted((int(t), float(r)) for t, r in d.items())
            ft = np.array([x[0] for x in arr], dtype=np.int64)
            fr = np.array([x[1] for x in arr], dtype=np.float64)
            fcache[sym] = (ft, fr)
            return fcache[sym]
        except Exception:
            fcache[sym] = None
            return None

    # group events by symbol -> moi symbol chi nap 1 lan (tranh cache 627x1M gay tran RAM)
    by_sym = {}
    for (m, s, lv) in rows:
        by_sym.setdefault(s, []).append((m, lv))

    fh = open(OUT + "/signals.csv", "w")
    fh.write("level,level_name,sym,entry_ts,entry_utc,year,entry,exit,hold,delist,raw_ret,slip,funding,net_ret\n")
    nw = 0
    nsym_done = 0
    for s, evs in by_sym.items():
        r = load_sym(files[s])
        if r is None:
            continue
        ts, o, h, l, c = r
        base = (ts - BASE).astype(np.int64)
        name = os.path.basename(files[s])[:-4]
        fnd = load_funding(name)
        for (m, lv) in evs:
            epos = int(np.searchsorted(base, m))
            if epos >= len(base) or base[epos] != m:
                continue
            if m + HOLD > NMIN - 1:
                continue  # edge-censored
            epos_end = int(np.searchsorted(base, m + HOLD, side="right")) - 1
            if epos_end <= epos:
                continue
            exit_min = int(base[epos_end])
            hold = exit_min - m
            delist = 1 if hold < HOLD else 0
            entry = float(c[epos])
            exitp = float(c[epos_end])
            if entry <= 0:
                continue
            raw = exitp / entry - 1.0
            slip = SLIP * (float(h[epos]) - float(l[epos])) / entry
            fund = 0.0
            if fnd is not None:
                ft, fr = fnd
                mmk = (ft > (BASE + m) * 60000) & (ft <= (BASE + exit_min) * 60000)
                if mmk.any():
                    fund = float(fr[mmk].sum())
            net = raw - FEE - slip - fund
            ets = BASE + m
            eu = datetime.utcfromtimestamp(ets * 60).strftime("%Y-%m-%d %H:%M")
            fh.write("%s,%s,%s,%d,%s,%d,%.8g,%.8g,%d,%d,%.6f,%.6f,%.6f,%.6f\n" % (
                lv, LABELS[lv], name, ets, eu, int(eu[:4]),
                entry, exitp, hold, delist, raw, slip, fund, net))
            nw += 1
        nsym_done += 1
        if nsym_done % 100 == 0:
            log.info("returns %d/%d syms written=%d el=%.0fs", nsym_done, len(by_sym), nw, time.time() - t0)
    fh.close()
    cli.close()
    log.info("written signals=%d", nw)
    open(OUT + "/SIGNALS_DONE", "w").write("events=%d written=%d\n" % (len(rows), nw))


if __name__ == "__main__":
    main()
