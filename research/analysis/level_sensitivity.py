#!/usr/bin/env python3
"""LEVEL_SENSITIVITY — sinh 3 pool do cho BIG_UP / MEDIUM_UP / MEDIUM_DOWN (code cu 157cf4d)
+ MOM15 (reference), do forward return tai 3 HOLD {240,1440,4320} phut.

Pre-reg: docs/prereg/PREREG_LEVEL_SENSITIVITY.md (commit TRUOC khi chay; khong sua thiet ke).

Pool:
  M-LEVEL : dung luat vong truoc (d15 tang dan, bo symbol lock, lay NUMBER_ORDER coin, lock HOLD)
  P-COIN  : moi coin trong cross-section hop le tai phut fire (tap ung vien ma getTopSymbol duyet)

Thuan Python, 0-sim, khong Java, khong push. Doc raw/<sym>.f32 + Aerospike funding_data (chi doc).
Output: /tmp/level_sens/pools.npz + log.
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

RAW = os.environ.get("LVL_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
OUT = os.environ.get("LVL_OUT", "/tmp/level_sens")
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("lvl")

# ---- LOCKED params (PREREG) ----
HOLDS = (240, 1440, 4320)          # 4h / 24h / 72h
FEE_GRID = (0.0005, 0.0010, 0.0015)  # 0.05% / 0.10% / 0.15% (round-trip)
SLIP = 0.5
KTOP = 100
KFRAC = 4 / 5
MIN_SYM = int(os.environ.get("LVL_MIN_SYM", "50"))
NUMBER_ORDER = 2                   # code cu: BIG_UP / MEDIUM_UP / MEDIUM_DOWN giu 2 coin
ORDER_MOM15 = 1                    # SMALL_DOWN_15M live: NUMBER_ENTRY_EACH_SIGNAL/2 = 1

UTC = timezone.utc
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

BASE = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() // 60)
SAMPLE_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)
NMIN = SAMPLE_END - BASE

LABELS = {1: "BIG_UP", 3: "MEDIUM_UP", 4: "MEDIUM_DOWN", 2: "BIG_DOWN_OLD", 8: "MOM15"}
DECISION = (1, 3, 4)


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
    """rc = C/O-1, d15 = C/max(H,15)-1 (15 nen gom m)."""
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
    """bottom-k mean va top-k mean cua tung phut (dung calRateChangeAvg k=min(100, floor(n*4/5)))."""
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
        lo2 = np.full(B, np.nan, dtype=np.float32)
        if ok.any():
            r = np.where(ok)[0]
            lo[r] = cs[r, idxk[r]] / kk[r]
            hh = cb[r] - 1
            hstart = np.clip(hh - kk[r], 0, maxc - 1)
            base_sum = np.where(hstart > 0, cs[r, hstart - 1], 0.0)
            lo2[r] = (cs[r, hh] - base_sum) / kk[r]
        lo_arr[b0:b1] = lo
        hi_arr[b0:b1] = lo2
    return lo_arr, hi_arr


def level_mask(rd, ru, rd15, btcrc, ok):
    """Nhan 1 level/phut theo dung thu tu if-else code cu (loai tru nhau)."""
    lab = np.zeros(len(rd), dtype=np.int8)
    m = ok.copy()
    for code, cond in (
        (1, ru > 0.025),
        (2, (rd < -0.032) & (btcrc < -0.01)),
        (3, ru > 0.015),
        (4, (rd < -0.030) | ((rd < -0.014) & (rd15 < -0.07))),
        (5, (ru > 0.008) & (rd > 0)),
        (6, (rd < -0.006) & (ru < 0) & (rd15 < -0.025)),
        (7, rd15 < -0.045),
        (8, rd15 < -0.028),
    ):
        c = m & cond
        lab[c] = code
        m = m & ~c
    return lab


def build_counts(files):
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
    return cnt, valid


def scatter(files, valid, offsets, total):
    rc_s = np.empty(total, dtype=np.float32)
    d15_s = np.empty(total, dtype=np.float32)
    sym_s = np.empty(total, dtype=np.int16)
    cur = np.zeros(NMIN, dtype=np.int64)
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
        if len(rel) == 0:
            continue
        dest = offsets[rel] + cur[rel]
        cur[rel] += 1
        rc_s[dest] = rc[use]
        d15_s[dest] = d15[use]
        sym_s[dest] = i
        if i % 100 == 0:
            log.info("pass2 %d/%d el=%.0fs", i, len(files), time.time() - t0)
    return rc_s, d15_s, sym_s


def build_mlevel(offsets, sym_s, d15_s, lab, fire_mins, n_sym):
    """M-LEVEL — TAI TAO DUNG luat vong truoc:
    (a) nhom quyet dinh (BIG_UP/MEDIUM_UP/MEDIUM_DOWN + dong BIG_DOWN_OLD tham chieu): MOT lan duyet
        theo THOI GIAN tang dan tren nhan {1,2,3,4}, lock CHUNG, k = NUMBER_ORDER = 2;
    (b) MOM15 (reference): vong rieng, lock rieng, k = ORDER_MOM15 = 1 (= A-PRIMARY harness control).
    """
    rows = []
    unlock = np.full(n_sym, -1, dtype=np.int64)
    F = np.where((lab >= 1) & (lab <= 4))[0]
    for n, m in enumerate(F):
        a, b = offsets[m], offsets[m + 1]
        if b - a < 1:
            continue
        syms = sym_s[a:b]
        order = np.argsort(d15_s[a:b], kind="stable")
        picked = 0
        for oi in order:
            s = int(syms[oi])
            if unlock[s] > m:
                continue
            unlock[s] = m + 1440
            rows.append((m, s, int(lab[m])))
            picked += 1
            if picked >= NUMBER_ORDER:
                break
    if not rows:
        z = np.empty(0, dtype=np.int64)
        return z, z.astype(np.int16), z.astype(np.int8)
    arr = np.array(rows, dtype=np.int64)
    main = (arr[:, 0], arr[:, 1].astype(np.int16), arr[:, 2].astype(np.int8))

    rows = []
    unlock = np.full(n_sym, -1, dtype=np.int64)
    for m in fire_mins[8]:
        a, b = offsets[m], offsets[m + 1]
        if b - a < 1:
            continue
        syms = sym_s[a:b]
        order = np.argsort(d15_s[a:b], kind="stable")
        picked = 0
        for oi in order:
            s = int(syms[oi])
            if unlock[s] > m:
                continue
            unlock[s] = m + 1440
            rows.append((m, s, 8))
            picked += 1
            if picked >= ORDER_MOM15:
                break
    arr2 = np.array(rows, dtype=np.int64)
    mom = (arr2[:, 0], arr2[:, 1].astype(np.int16), arr2[:, 2].astype(np.int8))
    out = [np.concatenate([main[i], mom[i]]) for i in range(3)]
    return out[0], out[1].astype(np.int16), out[2].astype(np.int8)


def funding_loader(cli):
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
            cum = np.concatenate(([0.0], np.cumsum(fr)))
            fcache[sym] = (ft, cum)
            return fcache[sym]
        except Exception:
            fcache[sym] = None
            return None

    return load_funding


def main():
    files = sorted(glob.glob(RAW + "/*.f32"))
    log.info("symbols=%d BASE=%d NMIN=%d HOLDS=%s", len(files), BASE, NMIN, HOLDS)

    cnt, valid = build_counts(files)
    offsets = np.zeros(NMIN + 1, dtype=np.int64)
    np.cumsum(cnt, out=offsets[1:])
    total = int(offsets[-1])
    log.info("pass1 done total_rows=%d", total)

    rc_s, d15_s, sym_s = scatter(files, valid, offsets, total)
    log.info("pass2 done rows=%d", total)

    t0 = time.time()
    rd, ru = per_minute_stats(rc_s, offsets, cnt, NMIN)
    del rc_s
    log.info("rateDown/UpAvg done el=%.0fs", time.time() - t0)
    t0 = time.time()
    rd15, _ = per_minute_stats(d15_s, offsets, cnt, NMIN)
    log.info("rateDown15MAvg done el=%.0fs", time.time() - t0)

    btu = load_sym(RAW + "/BTCUSDT.f32")
    bts, bo, bh, bl, bc = btu
    with np.errstate(invalid="ignore", divide="ignore"):
        btrc = np.where(bo > 0, bc / bo - 1.0, np.nan).astype(np.float32)
    btcrc = np.full(NMIN, np.nan, dtype=np.float32)
    brel = (bts - BASE).astype(np.int64)
    mm = (brel >= 0) & (brel < NMIN)
    btcrc[brel[mm]] = btrc[mm]

    ok = (cnt >= MIN_SYM) & np.isfinite(rd) & np.isfinite(ru) & np.isfinite(rd15) & np.isfinite(btcrc)
    lab = level_mask(rd, ru, rd15, btcrc, ok)
    mom15_map = ok & np.isfinite(rd15) & (rd15 < -0.028)
    log.info("label counts: %s", {LABELS[k]: int((lab == k).sum()) for k in (1, 2, 3, 4, 8)})
    log.info("MOM15 plain (rd15<-0.028, ok): %d phut", int(mom15_map.sum()))

    fire_mins = {lv: np.where(lab == lv)[0] for lv in DECISION}
    fire_mins[8] = np.where(mom15_map)[0]
    log.info("fire minutes: %s", {LABELS[k]: int(len(v)) for k, v in fire_mins.items()})

    # ---- P-COIN ----
    t0 = time.time()
    m_pc, s_pc, l_pc = [], [], []
    for lv in DECISION + (8,):
        F = fire_mins[lv]
        c = (offsets[F + 1] - offsets[F]).astype(np.int64)
        m_pc.append(np.repeat(F, c))
        l_pc.append(np.full(int(c.sum()), lv, dtype=np.int8))
        s_pc.append(np.concatenate([sym_s[offsets[m]:offsets[m + 1]] for m in F]).astype(np.int16))
    pc_min = np.concatenate(m_pc)
    pc_sym = np.concatenate(s_pc)
    pc_lvl = np.concatenate(l_pc)
    log.info("P-COIN rows=%d el=%.0fs  by-level=%s", len(pc_min), time.time() - t0, {
        LABELS[lv]: int((pc_lvl == lv).sum()) for lv in DECISION + (8,)})

    # ---- M-LEVEL ----
    t0 = time.time()
    ml_min, ml_sym, ml_lvl = build_mlevel(offsets, sym_s, d15_s, lab, fire_mins, len(files))
    log.info("M-LEVEL rows=%d el=%.0fs by-level=%s", len(ml_min), time.time() - t0, {
        LABELS[lv]: int((ml_lvl == lv).sum()) for lv in DECISION + (8,)})
    del d15_s, sym_s

    # ---- map M-LEVEL rows -> index trong P-COIN (M-LEVEL subset cua P-COIN) ----
    key_pc = pc_min.astype(np.int64) * 100000 + pc_sym.astype(np.int64)
    order = np.argsort(key_pc, kind="stable")
    key_sorted = key_pc[order]
    key_ml = ml_min.astype(np.int64) * 100000 + ml_sym.astype(np.int64)
    pos = np.searchsorted(key_sorted, key_ml)
    pos = np.clip(pos, 0, len(key_sorted) - 1)
    good = key_sorted[pos] == key_ml
    log.info("M-LEVEL in P-COIN: %d/%d", int(good.sum()), len(key_ml))
    ml_idx = order[pos[good]]
    ml_min2, ml_sym2, ml_lvl2 = ml_min[good], ml_sym[good], ml_lvl[good]
    del key_pc, key_sorted, order, key_ml

    # ---- forward returns cho P-COIN rows ----
    n_hold = len(HOLDS)
    N = len(pc_min)
    slot_by_sym = np.argsort(pc_sym, kind="stable")
    raw_out = np.full((n_hold, N), np.nan, dtype=np.float32)
    slip_out = np.full(N, np.nan, dtype=np.float32)
    fund_out = np.full((n_hold, N), np.nan, dtype=np.float32)
    valid_out = np.zeros(N, dtype=np.int8)

    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    load_funding = funding_loader(cli)

    bounds = np.searchsorted(pc_sym[slot_by_sym], np.arange(len(files) + 1))
    t0 = time.time()
    for s in range(len(files)):
        i0, i1 = bounds[s], bounds[s + 1]
        if i1 <= i0:
            continue
        r = load_sym(files[s])
        if r is None:
            continue
        ts, o, h, l, c = r
        base = (ts - BASE).astype(np.int64)
        rows = slot_by_sym[i0:i1]
        mins = pc_min[rows].astype(np.int64)
        epos = np.searchsorted(base, mins)
        inside = (epos < len(base)) & (base[np.clip(epos, 0, len(base) - 1)] == mins)
        rows, epos, mins = rows[inside], epos[inside], mins[inside]
        if len(rows) == 0:
            continue
        entry = c[epos].astype(np.float64)
        keep = entry > 0
        rows, epos, mins, entry = rows[keep], epos[keep], mins[keep], entry[keep]
        if len(rows) == 0:
            continue
        slip_out[rows] = SLIP * (h[epos].astype(np.float64) - l[epos].astype(np.float64)) / entry
        fnd = load_funding(os.path.basename(files[s])[:-4])
        for j, hd in enumerate(HOLDS):
            endm = mins + hd
            censored = endm > (NMIN - 1)
            epos_end = np.searchsorted(base, endm, side="right") - 1
            epos_end = np.clip(epos_end, 0, len(base) - 1)
            exitp = c[epos_end].astype(np.float64)
            ok_ev = (~censored) & (epos_end > epos)
            rr = rows[ok_ev]
            raw_out[j, rr] = exitp[ok_ev] / entry[ok_ev] - 1.0
            fr = np.zeros(len(rr), dtype=np.float64)
            if fnd is not None:
                ft, cum = fnd
                t_lo = (BASE + mins[ok_ev]) * 60000
                t_hi = (BASE + base[epos_end[ok_ev]]) * 60000
                lo_i = np.searchsorted(ft, t_lo, side="right")
                hi_i = np.searchsorted(ft, t_hi, side="right")
                fr = cum[hi_i] - cum[lo_i]
            fund_out[j, rr] = fr
            valid_out[rr] |= (1 << j)
        if s % 100 == 0:
            log.info("returns sym %d/%d el=%.0fs", s, len(files), time.time() - t0)
    cli.close()
    log.info("returns done el=%.0fs", time.time() - t0)

    np.savez_compressed(
        OUT + "/pools.npz",
        pc_min=(pc_min + BASE).astype(np.int32), pc_sym=pc_sym.astype(np.int16), pc_lvl=pc_lvl.astype(np.int8),
        pc_raw=raw_out, pc_slip=slip_out, pc_fund=fund_out, pc_valid=valid_out,
        ml_idx=ml_idx.astype(np.int64), ml_min=(ml_min2 + BASE).astype(np.int32),
        ml_sym=ml_sym2.astype(np.int16), ml_lvl=ml_lvl2.astype(np.int8),
        holds=np.array(HOLDS), fee_grid=np.array(FEE_GRID),
        n_sym=np.array(len(files)), base=np.array(BASE), sample_end=np.array(SAMPLE_END),
    )
    np.savez_compressed(OUT + "/agg.npz", rd15=rd15, rd=rd, ru=ru, cnt=cnt.astype(np.int32),
                        ok=ok, lab=lab, mom15=mom15_map,
                        fire1=fire_mins[1], fire3=fire_mins[3], fire4=fire_mins[4], fire8=fire_mins[8])
    log.info("saved %s", OUT + "/agg.npz")
    log.info("saved %s", OUT + "/pools.npz")
    open(OUT + "/POOLS_DONE", "w").write("ok rows=%d mlevel=%d\n" % (N, len(ml_min2)))


if __name__ == "__main__":
    main()
