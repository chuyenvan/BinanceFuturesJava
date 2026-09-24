#!/usr/bin/env python3
"""FUNDING_FACTOR — sinh mau do cho funding nhu (a) factor cross-section + (b) thanh phan chi phi.

Pre-reg: docs/prereg/PREREG_FUNDING_FACTOR.md (commit 17d600a, chot TRUOC khi chay; KHONG sua thiet ke).

Grid A (chinh): mau = (symbol, event funding cua chinh symbol do) trong [2021-01-01, 2026-01-01).
  f_entry = rate cua event do (rate DA BIET tai luc vao lenh) — predictor, KHONG nam trong f_cum.
  f_cum   = tong rate cac event co ts in (m_e*60000, m_x*60000].
  net     = raw - phi - slip - f_cum   (long: funding duong = tra).
MOM15 (neo, §5.4): rd15 = bottom-k mean cua d15 (k=min(100, floor(n*4/5)), n>=50), fire rd15<-0.028,
  chon k=1 coin d15 thap nhat + lock 1440'.
  -> M-LEVEL MOM15 (k=1) rows  +  P-COIN MOM15 rows (moi coin trong cross-section tai phut fire).

Thuan Python, 0-sim, khong Java, khong push. Doc raw/<sym>.f32 + Aerospike funding_data (chi DOC).
Output trung gian: $FF_OUT/pools.npz (resume: partial.npz ghi moi 100 symbol).
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

RAW = os.environ.get("FF_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
OUT = os.environ.get("FF_OUT", "/tmp/funding_factor")
AERO_NS = os.environ.get("AERO_NS", "test")
AERO_SET = "funding_data"
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(OUT + "/factor.log")])
log = logging.getLogger("ff")

# ---- LOCKED params (PREREG) ----
HOLDS = (240, 1440, 4320)
FEE_GRID = (0.0005, 0.0010, 0.0015)
SLIP = 0.5
MIN_SYM = 50
KTOP = 100
KFRAC = 4 / 5
MOM15_THR = -0.028
ORDER_MOM15 = 1
LOCK_MIN = 1440
FUND_MS_MIN = 1609459200000          # 2021-01-01 00:00:00 UTC
FUND_MS_MAX = 1767225600000          # 2026-01-01 00:00:00 UTC

UTC = timezone.utc
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

BASE = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() // 60)
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
    """bottom-k mean cua tung phut (calRateChangeAvg k=min(100, floor(n*4/5)))."""
    maxc = int(cnt.max())
    out = np.full(nmin, np.nan, dtype=np.float32)
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
        if ok.any():
            r = np.where(ok)[0]
            lo[r] = cs[r, idxk[r]] / kk[r]
        out[b0:b1] = lo
    return out


def load_funding(cli, sym, cache):
    if sym in cache:
        return cache[sym]
    try:
        kkey = cli.get((AERO_NS, AERO_SET, sym))
        bd = kkey[2]
        if not bd or "f_data" not in bd:
            cache[sym] = None
            return None
        d = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(bd["f_data"]))))
        arr = sorted((int(t), float(r)) for t, r in d.items() if int(t) >= FUND_MS_MIN)
        ts = np.array([x[0] for x in arr], dtype=np.int64)
        fr = np.array([x[1] for x in arr], dtype=np.float64)
        keep = (ts < FUND_MS_MAX)
        ts, fr = ts[keep], fr[keep]
        cum = np.concatenate(([0.0], np.cumsum(fr)))
        cache[sym] = (ts, fr, cum)
        return cache[sym]
    except Exception as e:
        log.warning("funding load fail %s: %s", sym, type(e).__name__)
        cache[sym] = None
        return None


def returns_for(ts, o, h, l, c, epos, m_e, ft, fr, cum):
    """raw/slip/fund cho cac entry epos tai phut m_e (mang). Tra ve (raw[H,n], slip, fund[H,n], valid, sd)."""
    n = len(m_e)
    H = len(HOLDS)
    raw = np.full((H, n), np.nan, dtype=np.float32)
    fund = np.full((H, n), np.nan, dtype=np.float32)
    slip = np.full(n, np.nan, dtype=np.float32)
    valid = np.zeros(n, dtype=np.int8)
    sd = np.zeros(n, dtype=np.int8)
    if n == 0 or ft is None:
        return raw, slip, fund, valid, sd
    entry = c[epos].astype(np.float64)
    keep = entry > 0
    slip[keep] = SLIP * (h[epos[keep]].astype(np.float64) - l[epos[keep]].astype(np.float64)) / entry[keep]
    t_e = (BASE + m_e) * 60000
    lo = np.searchsorted(ft, t_e, side="right")
    for j, hd in enumerate(HOLDS):
        m_x = m_e + hd
        cens = m_x > (NMIN - 1)
        ep_end = np.searchsorted(ts, BASE + m_x, side="right") - 1
        ep_end = np.clip(ep_end, 0, len(ts) - 1)
        end = c[ep_end].astype(np.float64)
        rr = keep & (~cens) & (entry > 0)
        raw[j, rr] = end[rr] / entry[rr] - 1.0
        hi = np.searchsorted(ft, (BASE + m_x[rr]) * 60000, side="right")
        fund[j, rr] = cum[hi] - cum[lo[rr]]
        valid[rr] |= (1 << j)
        sd[rr] |= ((ep_end[rr] <= epos[rr]).astype(np.int8))
    return raw, slip, fund, valid, sd


def prev_rate(ft, fr, m_e):
    """f_entry = rate cua event cuoi cung co ts <= m_e*60000 (rate DA BIET tai luc vao lenh)."""
    if ft is None:
        return np.full(len(m_e), np.nan, dtype=np.float32)
    idx = np.searchsorted(ft, (BASE + m_e) * 60000, side="right") - 1
    out = np.full(len(m_e), np.nan, dtype=np.float32)
    good = idx >= 0
    out[good] = fr[idx[good]]
    return out


def main():
    files = sorted(glob.glob(RAW + "/*.f32"))
    log.info("symbols=%d BASE=%d NMIN=%d HOLDS=%s", len(files), BASE, NMIN, HOLDS)
    cache = OUT + "/cache2.npz"
    if os.path.exists(cache) and os.environ.get("FF_RECOMPUTE") != "1":
        z = np.load(cache)
        offsets, fire8 = z["offsets"], z["fire8"]
        ml_min, ml_sym = z["ml_min"], z["ml_sym"]
        pc_min, pc_sym = z["pc_min"], z["pc_sym"]
        total_rows, n_fire8 = int(z["total_rows"]), int(z["n_fire8"])
        log.info("cache2 loaded: total_rows=%d fire8=%d pc=%d ml=%d", total_rows, n_fire8, len(pc_min), len(ml_min))
        return pass3(files, offsets, fire8, ml_min, ml_sym, pc_min, pc_sym, total_rows, n_fire8)

    # ---------------- pass 1: counts ----------------
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
            log.info("pass1 %d/%d el=%.0fs", i, len(files), time.time() - t0)
    offsets = np.zeros(NMIN + 1, dtype=np.int64)
    np.cumsum(cnt, out=offsets[1:])
    total_rows = int(offsets[-1])
    log.info("pass1 done total_rows=%d", total_rows)

    # ---------------- pass 2: scatter + returns ----------------
    rc_s = np.empty(total_rows, dtype=np.float32)
    d15_s = np.empty(total_rows, dtype=np.float32)
    sym_s = np.empty(total_rows, dtype=np.int16)
    cur = np.zeros(NMIN, dtype=np.int64)
    for i, p in enumerate(files):
        if not valid[i]:
            continue
        ts, o, h, l, c = r = load_sym(p)
        rc, d15 = derive(o, h, c)
        rel = (ts - BASE).astype(np.int64)
        use = np.isfinite(rc) & np.isfinite(d15)
        rel = rel[use]
        dest = offsets[rel] + cur[rel]
        cur[rel] += 1
        rc_s[dest] = rc[use]
        d15_s[dest] = d15[use]
        sym_s[dest] = i
        if i % 100 == 0:
            log.info("pass2 %d/%d el=%.0fs", i, len(files), time.time() - t0)
    log.info("pass2 done el=%.0fs", time.time() - t0)

    rd15 = per_minute_stats(d15_s, offsets, cnt, NMIN)
    log.info("rd15 done el=%.0fs", time.time() - t0)

    btu = load_sym(RAW + "/BTCUSDT.f32")
    bts, bo, bh, bl, bc = btu
    with np.errstate(invalid="ignore", divide="ignore"):
        btrc = np.where(bo > 0, bc / bo - 1.0, np.nan).astype(np.float32)
    btcrc = np.full(NMIN, np.nan, dtype=np.float32)
    brel = (bts - BASE).astype(np.int64)
    mm = (brel >= 0) & (brel < NMIN)
    btcrc[brel[mm]] = btrc[mm]

    ok = (cnt >= MIN_SYM) & np.isfinite(rd15) & np.isfinite(btcrc)
    fire8 = np.where(ok & (rd15 < MOM15_THR))[0]
    log.info("MOM15 plain minutes=%d", len(fire8))

    # ---- MOM15 selection k=1, lock 1440' (live SMALL_DOWN_15M) ----
    unlock = np.full(len(files), -1, dtype=np.int64)
    ml_min, ml_sym = [], []
    for m in fire8:
        a, b = offsets[m], offsets[m + 1]
        if b - a < 1:
            continue
        syms = sym_s[a:b]
        order = np.argsort(d15_s[a:b], kind="stable")
        for oi in order:
            s = int(syms[oi])
            if int(valid[s]) == 0 or unlock[s] > m:
                continue
            unlock[s] = m + LOCK_MIN
            ml_min.append(m)
            ml_sym.append(s)
            break
    ml_min = np.array(ml_min, dtype=np.int64)
    ml_sym = np.array(ml_sym, dtype=np.int16)
    log.info("M-LEVEL MOM15 k=1 events=%d", len(ml_min))

    # ---- P-COIN MOM15 rows ----
    cF = (offsets[fire8 + 1] - offsets[fire8]).astype(np.int64)
    pc_min = np.repeat(fire8, cF)
    pc_sym = np.concatenate([sym_s[offsets[m]:offsets[m + 1]] for m in fire8]).astype(np.int16)
    log.info("P-COIN MOM15 rows=%d", len(pc_min))

    np.savez(cache,
             offsets=offsets, fire8=fire8, ml_min=ml_min, ml_sym=ml_sym,
             pc_min=pc_min, pc_sym=pc_sym, total_rows=np.array(total_rows),
             n_fire8=np.array(len(fire8)))
    log.info("cache2 saved el=%.0fs", time.time() - t0)
    return pass3(files, offsets, fire8, ml_min, ml_sym, pc_min, pc_sym, total_rows, len(fire8))


def pass3(files, offsets, fire8, ml_min, ml_sym, pc_min, pc_sym, total_rows, n_fire8):
        # ---------------- pass 3: grid A + MOM15 returns ----------------
        cli = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 60000}}).connect()
        fcache = {}

        # map P-COIN rows theo symbol
        slot = np.argsort(pc_sym, kind="stable")
        bounds_pc = np.searchsorted(pc_sym[slot], np.arange(len(files) + 1))
        log.info("dbg pc_sym: n=%d min=%d max=%d uniq=%d | bounds_pc[:5]=%s tail=%s",
                 len(pc_sym), int(pc_sym.min()), int(pc_sym.max()), len(np.unique(pc_sym)),
                 bounds_pc[:5].tolist(), bounds_pc[-3:].tolist())
        log.info("dbg ml_sym: n=%d min=%d max=%d uniq=%d", len(ml_sym), int(ml_sym.min()),
                 int(ml_sym.max()), len(np.unique(ml_sym)))
        # map M-LEVEL rows theo symbol
        slot_m = np.argsort(ml_sym, kind="stable")
        bounds_m = np.searchsorted(ml_sym[slot_m], np.arange(len(files) + 1))

        A_min, A_sym, A_f = [], [], []
        A_raw, A_slip, A_fund, A_valid, A_sd = [], [], [], [], []
        P_raw, P_slip, P_fund, P_valid, P_sd, P_f = [], [], [], [], [], []
        P_min_s, P_sym_s = [], []
        M_raw, M_slip, M_fund, M_valid, M_sd, M_f = [], [], [], [], [], []
        M_min_s, M_sym_s = [], []
        nfund_ok = 0
        t1 = time.time()
        for i, p in enumerate(files):
            sym = os.path.basename(p)[:-4]
            r = load_sym(p)
            if r is None:
                continue
            ts, o, h, l, c = r
            tsr = (ts - BASE).astype(np.int64)   # nhan vao: raw ts = EPOCH minute; fire minutes = RELATIVE
            fnd = load_funding(cli, sym, fcache)
            if fnd is not None:
                nfund_ok += 1
            ft, fr, cum = (fnd if fnd is not None else (None, None, None))

            # ---- grid A: event funding cua chinh symbol ----
            if ft is not None:
                m_all = ft // 60000
                pos = np.searchsorted(ts, m_all)
                posc = np.clip(pos, 0, len(ts) - 1)
                inside = (pos < len(ts)) & (ts[posc] == m_all)
                epos = pos[inside]
                m_e = (m_all[inside] - BASE).astype(np.int64)
                f_e = fr[inside].astype(np.float32)
                if len(m_e):
                    raw, slip, fund, val, sd = returns_for(ts, o, h, l, c, epos, m_e, ft, fr, cum)
                    A_min.append(m_e.astype(np.int32))
                    A_sym.append(np.full(len(m_e), i, dtype=np.int16))
                    A_f.append(f_e)
                    A_raw.append(raw)
                    A_slip.append(slip)
                    A_fund.append(fund)
                    A_valid.append(val)
                    A_sd.append(sd)

            # ---- M-LEVEL MOM15 rows (k=1) ----
            i0, i1 = bounds_m[i], bounds_m[i + 1]
            if i1 > i0:
                rows = slot_m[i0:i1]
                m_e = ml_min[rows]
                epos = np.searchsorted(tsr, m_e)
                okk = (epos < len(tsr)) & (tsr[np.clip(epos, 0, len(tsr) - 1)] == m_e)
                rows, m_e, epos = rows[okk], m_e[okk], epos[okk]
                if len(rows):
                    raw, slip, fund, val, sd = returns_for(ts, o, h, l, c, epos, m_e, ft, fr, cum)
                    M_raw.append(raw)
                    M_slip.append(slip)
                    M_fund.append(fund)
                    M_valid.append(val)
                    M_sd.append(sd)
                    M_f.append(prev_rate(ft, fr, m_e))
                    M_min_s.append(ml_min[rows].astype(np.int32))
                    M_sym_s.append(np.full(len(rows), i, dtype=np.int16))

            # ---- P-COIN MOM15 rows ----
            j0, j1 = bounds_pc[i], bounds_pc[i + 1]
            if j1 > j0:
                rows = slot[j0:j1]
                m_e = pc_min[rows]
                epos = np.searchsorted(tsr, m_e)
                okk = (epos < len(tsr)) & (tsr[np.clip(epos, 0, len(tsr) - 1)] == m_e)
                rows, m_e, epos = rows[okk], m_e[okk], epos[okk]
                if len(rows):
                    raw, slip, fund, val, sd = returns_for(ts, o, h, l, c, epos, m_e, ft, fr, cum)
                    P_raw.append(raw)
                    P_slip.append(slip)
                    P_fund.append(fund)
                    P_valid.append(val)
                    P_sd.append(sd)
                    P_f.append(prev_rate(ft, fr, m_e))
                    P_min_s.append(pc_min[rows].astype(np.int32))
                    P_sym_s.append(np.full(len(rows), i, dtype=np.int16))
            if i % 50 == 0:
                log.info("pass3 %d/%d el=%.0fs", i, len(files), time.time() - t1)
            if i % 150 == 0 and len(A_min):
                # checkpoint (resume duoc neu loi): ghi tam khong nen
                np.savez(OUT + "/partial.npz",
                         a_min=np.concatenate(A_min), a_sym=np.concatenate(A_sym),
                         a_f=np.concatenate(A_f), a_raw=np.concatenate(A_raw, axis=1),
                         a_slip=np.concatenate(A_slip), a_fund=np.concatenate(A_fund, axis=1),
                         a_valid=np.concatenate(A_valid), a_sd=np.concatenate(A_sd), upto=np.array(i))
        cli.close()
        log.info("pass3 done el=%.0fs funding_ok=%d/%d", time.time() - t1, nfund_ok, len(files))
        n_pc = int(sum(x.shape[1] for x in P_raw)); n_ml = int(sum(x.shape[1] for x in M_raw))
        log.info("pass3 coverage: gridA=%d/%d P-COIN=%d/%d M-LEVEL=%d/%d",
                 int(sum(len(x) for x in A_min)), total_rows,
                 n_pc, len(pc_min), n_ml, len(ml_min))

        A_min = np.concatenate(A_min)
        A_sym = np.concatenate(A_sym)
        A_f = np.concatenate(A_f)
        A_raw = np.concatenate(A_raw, axis=1)
        A_slip = np.concatenate(A_slip)
        A_fund = np.concatenate(A_fund, axis=1)
        A_valid = np.concatenate(A_valid)
        A_sd = np.concatenate(A_sd)
        P_raw = np.concatenate(P_raw, axis=1)
        P_slip = np.concatenate(P_slip)
        P_fund = np.concatenate(P_fund, axis=1)
        P_valid = np.concatenate(P_valid)
        P_sd = np.concatenate(P_sd)
        P_f = np.concatenate(P_f)
        M_raw = np.concatenate(M_raw, axis=1)
        M_slip = np.concatenate(M_slip)
        M_fund = np.concatenate(M_fund, axis=1)
        M_valid = np.concatenate(M_valid)
        M_sd = np.concatenate(M_sd)
        M_f = np.concatenate(M_f)

        np.savez_compressed(
            OUT + "/pools.npz",
            a_min=(A_min + BASE).astype(np.int32), a_sym=A_sym, a_f=A_f,
            a_raw=A_raw, a_slip=A_slip, a_fund=A_fund, a_valid=A_valid, a_sd=A_sd,
            p_min=(np.concatenate(P_min_s) + BASE).astype(np.int32), p_sym=np.concatenate(P_sym_s), p_f=P_f,
            p_raw=P_raw, p_slip=P_slip, p_fund=P_fund, p_valid=P_valid, p_sd=P_sd,
            m_min=(np.concatenate(M_min_s) + BASE).astype(np.int32), m_sym=np.concatenate(M_sym_s), m_f=M_f,
            m_raw=M_raw, m_slip=M_slip, m_fund=M_fund, m_valid=M_valid, m_sd=M_sd,
            holds=np.array(HOLDS), fee_grid=np.array(FEE_GRID), n_sym=np.array(len(files)),
            base=np.array(BASE), sample_end=np.array(SAMPLE_END), total_rows=np.array(total_rows),
            n_fire8=np.array(len(fire8)),
        )
        assert len(np.concatenate(P_min_s)) == P_raw.shape[1], "P alignment"
        assert len(np.concatenate(M_min_s)) == M_raw.shape[1], "M alignment"
        log.info("saved %s  gridA=%d pc15=%d ml15=%d", OUT + "/pools.npz", len(A_min), len(pc_min), len(ml_min))
        open(OUT + "/FACTOR_DONE", "w").write("ok total_rows=%d gridA=%d\n" % (total_rows, len(A_min)))


if __name__ == "__main__":
    main()
